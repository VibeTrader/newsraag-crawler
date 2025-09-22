"""
Main entry point for NewsRagnarok Crawler.
"""
import time
import asyncio
import os
import sys
import argparse
from loguru import logger
import threading
from datetime import datetime, timedelta
import gc
import psutil
from contextlib import nullcontext

# Import monitoring components
from monitoring import init_monitoring
from monitoring.metrics import get_metrics
from monitoring.health_check import get_health_check
from monitoring.duplicate_detector import get_duplicate_detector
from monitoring.alerts import get_alert_manager, trigger_test_alert
from monitoring.app_insights import get_app_insights

# Import crawler modules
from crawler.utils.config_loader import load_sources_config
from crawler.utils.dependency_checker import check_dependencies
from crawler.utils.memory_monitor import log_memory_usage
from crawler.utils.cleanup import cleanup_old_data, clear_qdrant_collection, recreate_qdrant_collection
from crawler.core.source_crawler import crawl_source
from crawler.health.health_server import start_health_server

# Define path to config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'sources.yaml')

# Constants
CRAWL_INTERVAL_SECONDS = 3600  # Check sources every hour (was 600)
CLEANUP_INTERVAL_SECONDS = 86400  # Run cleanup every day

async def main_loop():
    """Main loop to periodically crawl sources."""
    logger.info("Starting NewsRagnarok main loop...")
    sources = load_sources_config(CONFIG_PATH)
    if not sources:
        logger.error("No valid sources loaded. Exiting.")
        return
    
    last_cleanup_time = datetime.now()
    
    # Create heartbeat directory
    heartbeat_dir = os.path.join(os.path.dirname(__file__), 'data', 'heartbeat')
    os.makedirs(heartbeat_dir, exist_ok=True)
    heartbeat_file = os.path.join(heartbeat_dir, 'crawler_heartbeat.txt')
    
    # Update heartbeat file at startup
    with open(heartbeat_file, 'w') as f:
        f.write(f"Crawler started at: {datetime.now().isoformat()}\n")
    
    # Add memory tracking
    try:
        process = psutil.Process(os.getpid())
        logger.info(f"Initial memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
    except ImportError:
        logger.warning("psutil not available, memory tracking disabled")
        process = None
    
    try:
        while True:
            start_time = time.monotonic()
            logger.info("--- Starting New Cycle ---")
            logger.info(f"Current time: {datetime.now()}")
            
            # Start cycle metrics tracking
            metrics = get_metrics()
            cycle_id = metrics.start_cycle()
            
            # Get App Insights for cloud monitoring
            app_insights = get_app_insights()
            
            # Track cycle start in App Insights
            if app_insights.enabled:
                app_insights.track_event("cycle_start", {"cycle_id": cycle_id})
            
            # Log memory usage at cycle start if available
            if process:
                mem_info = process.memory_info()
                memory_mb = mem_info.rss / 1024 / 1024
                logger.info(f"Memory usage at cycle start: {memory_mb:.2f} MB")
                
                # Update memory usage in metrics
                metrics.update_memory_usage(memory_mb)
                
                # Track in App Insights
                if app_insights.enabled:
                    app_insights.track_memory_usage(memory_mb)
                
                # Update health check
                health_check = get_health_check()
                health_check.check_memory_usage()
            
            # Check if cleanup is needed (every 24 hours)
            current_time = datetime.now()
            if (current_time - last_cleanup_time).total_seconds() >= CLEANUP_INTERVAL_SECONDS:
                logger.info("Running scheduled cleanup...")
                await cleanup_old_data()
                last_cleanup_time = current_time
                logger.info("Cleanup completed, continuing with crawl cycle...")
                
                # Force garbage collection after cleanup
                if gc:
                    logger.info("Forcing garbage collection after cleanup...")
                    gc.collect()
                    if process:
                        logger.info(f"Memory after cleanup: {process.memory_info().rss / 1024 / 1024:.2f} MB")
            
            # Check dependencies
            if not await check_dependencies():
                logger.error("Dependency check failed. Skipping cycle.")
                
                # Record error in metrics
                metrics.record_cycle_error("dependency_check_failed", "Dependency check failed, skipping cycle", "critical")
                metrics.end_cycle(success=False)
                
                elapsed_time = time.monotonic() - start_time
                sleep_duration = max(0, CRAWL_INTERVAL_SECONDS - elapsed_time)
                logger.info(f"Sleeping for {sleep_duration:.2f} seconds...")
                await asyncio.sleep(sleep_duration)
                continue
            
            # Crawl sources (run every hour)
            logger.info(f"Starting crawl cycle for {len(sources)} sources...")
            crawl_results = []
            
            for i, source in enumerate(sources):
                try:
                    logger.info(f"Processing source {i+1}/{len(sources)}: {source.get('name', 'Unknown')}")
                    result = await crawl_source(source)
                    crawl_results.append(result)
                    
                    # Small delay between sources to manage memory
                    await asyncio.sleep(5)
                    
                    # Garbage collect after each source
                    if gc and i % 2 == 1:  # Every 2 sources
                        logger.info(f"Performing garbage collection after source {i+1}/{len(sources)}")
                        gc.collect()
                        if process:
                            logger.info(f"Memory after source {i+1}: {process.memory_info().rss / 1024 / 1024:.2f} MB")
                            
                    # Check for excessive memory usage and reduce pressure if needed
                    if process and process.memory_info().rss > 800 * 1024 * 1024:  # Over 800MB
                        logger.warning("Memory usage high, performing emergency cleanup")
                        gc.collect()
                        # You could also implement a more aggressive cleanup here
                        await asyncio.sleep(10)  # Give system time to reclaim memory
                        
                except Exception as e:
                    logger.error(f"Error crawling source {source.get('name', 'Unknown')}: {e}")
                    crawl_results.append((source.get('name', 'Unknown'), 0, 1))  # Count as failed
            
            # Summary
            logger.info("--- Crawl Cycle Summary ---")
            total_processed = 0
            total_failed = 0
            for source_name, processed_count, failure_count in crawl_results:
                logger.info(f"- Source '{source_name}': {processed_count} processed, {failure_count} failed.")
                total_processed += processed_count
                total_failed += failure_count
            
            # Calculate success rate
            success_rate = (total_processed/(total_processed+total_failed)*100) if (total_processed + total_failed) > 0 else 0
            logger.info(f"Total items processed: {total_processed}")
            logger.info(f"Total items failed: {total_failed}")
            logger.info(f"Success rate: {success_rate:.2f}%")
            
            # Calculate time until next cleanup
            time_until_cleanup = CLEANUP_INTERVAL_SECONDS - (datetime.now() - last_cleanup_time).total_seconds()
            logger.info(f"Next cleanup in: {time_until_cleanup/3600:.2f} hours")
            
            # Final garbage collection at end of cycle
            if gc:
                logger.info("Forcing final garbage collection at end of cycle...")
                gc.collect()
                if process:
                    logger.info(f"Memory after cycle end: {process.memory_info().rss / 1024 / 1024:.2f} MB")
            
            # Calculate next run time
            cycle_duration = time.monotonic() - start_time
            sleep_duration = max(0, CRAWL_INTERVAL_SECONDS - cycle_duration)
            next_run_time = datetime.now() + timedelta(seconds=sleep_duration)
            
            logger.info(f"Cycle finished in {cycle_duration:.2f} seconds")
            logger.info(f"Next crawl cycle scheduled for: {next_run_time}")
            logger.info(f"===============================================")
            logger.info(f"SLEEPING for {sleep_duration:.2f} seconds...")
            logger.info(f"Will wake up at {next_run_time}")
            logger.info(f"===============================================")
            
            # End cycle metrics tracking
            metrics.end_cycle(success=True)
            
            # Track cycle completion in App Insights
            if app_insights.enabled:
                app_insights.track_cycle_duration(cycle_duration)
                app_insights.track_event("cycle_completed", {
                    "cycle_id": cycle_id,
                    "duration_seconds": str(round(cycle_duration, 2)),
                    "articles_processed": str(total_processed),
                    "articles_failed": str(total_failed),
                    "success_rate": str(round(success_rate, 2))
                })
            
            # Save daily metrics
            metrics.save_daily_metrics()
            
            # Optional: log system resources before sleep
            if process:
                try:
                    cpu_percent = psutil.cpu_percent(interval=1)
                    mem_percent = psutil.virtual_memory().percent
                    logger.info(f"System resources: CPU {cpu_percent}%, Memory {mem_percent}%")
                except:
                    pass
                    
            # Update heartbeat file before sleep
            try:
                with open(heartbeat_file, 'a') as f:
                    f.write(f"Cycle completed at: {datetime.now().isoformat()}, next cycle at: {next_run_time.isoformat()}\n")
            except Exception as heartbeat_err:
                logger.warning(f"Failed to update heartbeat file: {str(heartbeat_err)}")
                
            # Sleep until next cycle - with additional wake-up logging
            try:
                logger.info(f"Starting sleep at: {datetime.now()}")
                await asyncio.sleep(sleep_duration)
                logger.info(f"Woke up from sleep at: {datetime.now()}")
                logger.info(f"===============================================")
                logger.info(f"STARTING NEXT CYCLE after sleeping")
                logger.info(f"===============================================")
            except Exception as sleep_err:
                logger.error(f"Error during sleep: {str(sleep_err)}")
                # Continue to next cycle anyway
                await asyncio.sleep(5)  # Short delay before retry
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal. Shutting down...")
        
        # Flush App Insights telemetry before exit
        if app_insights.enabled:
            app_insights.track_event("application_shutdown", {"reason": "keyboard_interrupt"})
            app_insights.flush()
            
        await cleanup_old_data()
        logger.info("Final cleanup completed. Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
        import traceback
        logger.error(f"Stack trace:\n{traceback.format_exc()}")
        
        # Try to recover - perform cleanup and restart the loop
        try:
            logger.info("Attempting recovery...")
            if gc:
                gc.collect()
            await asyncio.sleep(60)  # Wait a minute before restarting
            await main_loop()  # Recursive call to restart the loop
        except Exception as recover_error:
            logger.critical(f"Recovery failed: {recover_error}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NewsRagnarok Crawler (Simplified)")
    parser.add_argument("--clear-collection", action="store_true", help="Clear all documents from the Qdrant collection")
    parser.add_argument("--recreate-collection", action="store_true", help="Delete and recreate the Qdrant collection")
    args = parser.parse_args()
    
    # Initialize monitoring system
    logger.info("🔍 Initializing monitoring system...")
    metrics, health_check, duplicate_detector, app_insights, alert_manager = init_monitoring()
    logger.info("✅ Monitoring system initialized successfully")
    
    # Test Slack alerts on startup to verify configuration
    if os.getenv("ALERT_SLACK_ENABLED", "false").lower() == "true":
        logger.info("🔔 Testing Slack alerts...")
        try:
            # Send a test alert to confirm Slack integration is working
            trigger_test_alert(
                message=f"NewsRagnarok startup test alert from {os.environ.get('COMPUTERNAME') or os.environ.get('HOSTNAME') or 'unknown'}",
                alert_type="startup_test"
            )
            logger.info("✅ Slack test alert triggered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to send Slack test alert: {str(e)}")
    else:
        logger.info("⚠️ Slack alerts are disabled. Set ALERT_SLACK_ENABLED=true to enable.")
    
    # Check if we need to perform collection cleanup or recreation
    if args.clear_collection or args.recreate_collection:
        if args.recreate_collection:
            logger.info("Recreate collection flag detected, recreating Qdrant collection...")
            success = asyncio.run(recreate_qdrant_collection())
            if success:
                logger.info("✅ Qdrant collection recreation completed successfully")
            else:
                logger.error("❌ Qdrant collection recreation failed")
        elif args.clear_collection:
            logger.info("Clear collection flag detected, clearing Qdrant collection...")
            success = asyncio.run(clear_qdrant_collection())
            if success:
                logger.info("✅ Qdrant collection cleanup completed successfully")
            else:
                logger.error("❌ Qdrant collection cleanup failed")
        
        # Exit after cleanup operations if requested
        if not (args.clear_collection and not args.recreate_collection):
            logger.info("Cleanup/recreation operations completed, exiting...")
            sys.exit(0)
    
    # Track application start event in App Insights
    if app_insights.enabled:
        app_insights.track_event("application_start", {
            "version": "1.0.0",  # Update with your version
            "environment": os.environ.get("ENVIRONMENT", "development")
        })
    
    # Ensure data directories exist
    os.makedirs(os.path.join(os.path.dirname(__file__), 'data', 'metrics'), exist_ok=True)
    
    # Log Azure App Service configuration
    port = os.environ.get('PORT', '8000')
    logger.info(f"🌐 Azure App Service Configuration:")
    logger.info(f"   📡 PORT environment variable: {port}")
    logger.info(f"   🚀 Starting enhanced health check server on port {port}")
    
    # Start health check server IMMEDIATELY in a separate thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Give health server a moment to start
    import time
    time.sleep(2)
    
    # Run the main crawler loop
    asyncio.run(main_loop())
