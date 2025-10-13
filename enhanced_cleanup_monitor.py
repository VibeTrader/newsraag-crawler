#!/usr/bin/env python3
"""
Enhanced cleanup monitoring script for NewsRaag Crawler.

Integrates with existing App Insights and error handling system to provide
comprehensive cleanup monitoring with proper error tracking and alerts.
"""
import asyncio
import sys
import traceback
from datetime import datetime, timedelta
from loguru import logger
from typing import Dict, Any, Optional

# Add project root to path
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import existing monitoring infrastructure
from monitoring import init_monitoring
from monitoring.app_insights import get_app_insights
from monitoring.alerts import get_alert_manager
from monitoring.metrics import get_metrics
from monitoring.health_check import get_health_check
from crawler.utils.cleanup import cleanup_old_data, clear_qdrant_collection
from clients.vector_client import create_vector_client


class CleanupMonitor:
    """Enhanced cleanup monitor that integrates with existing error tracking."""
    
    def __init__(self):
        """Initialize cleanup monitor with existing monitoring infrastructure."""
        self.app_insights = get_app_insights()
        self.metrics = get_metrics() 
        self.health_check = get_health_check()
        self.alert_manager = get_alert_manager()
        
        logger.info("🧹 Cleanup Monitor initialized with existing monitoring infrastructure")
    
    async def send_demo_alert_on_startup(self) -> bool:
        """
        Send a demo alert on app startup to verify alert system is working.
        
        Returns:
            True if demo alert was sent successfully
        """
        try:
            startup_time = datetime.now().isoformat()
            
            logger.info("📢 Sending demo alert to verify alert system...")
            
            # Track startup in App Insights
            self.app_insights.track_event("cleanup_monitor_startup", {
                "startup_time": startup_time,
                "demo_alert": True,
                "purpose": "verify_alert_system"
            })
            
            # Send demo alert through existing alert system
            demo_message = (
                "🚀 NewsRaag Cleanup Monitor Started Successfully!\n\n"
                f"📅 Startup Time: {startup_time}\n"
                "✅ Alert system is working correctly\n"
                "🔔 This is a demo alert to verify monitoring"
            )
            
            self.alert_manager.send_alert(
                "cleanup_monitor_demo_alert",
                demo_message,
                {
                    "alert_type": "demo",
                    "startup_time": startup_time,
                    "system": "cleanup_monitor",
                    "purpose": "verify_alert_system",
                    "severity": "info"
                }
            )
            
            logger.info("✅ Demo alert sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send demo alert: {e}")
            
            # Track demo alert failure in App Insights
            self.app_insights.track_exception(e, {
                "operation": "demo_alert_startup",
                "error": "demo_alert_failed",
                "startup_time": startup_time
            })
            
            return False
    
    async def check_crawler_cycle_status(self) -> Dict[str, Any]:
        """
        Check if the crawler cycle is currently running.
        
        Returns:
            Dict with crawler cycle status and details
        """
        try:
            logger.info("🔍 Checking crawler cycle status...")
            
            crawler_status = {
                "is_running": False,
                "last_activity": None,
                "error": None,
                "check_time": datetime.now().isoformat()
            }
            
            # Check metrics for recent crawler activity
            try:
                current_stats = self.metrics.get_current_stats()
                
                # Look for recent crawler activity indicators
                if current_stats:
                    # Check for recent cycle activity
                    last_cycle_time = current_stats.get("last_cycle_completed")
                    if last_cycle_time:
                        # Parse the time and check if it's recent (within last hour)
                        try:
                            if isinstance(last_cycle_time, str):
                                last_time = datetime.fromisoformat(last_cycle_time.replace('Z', '+00:00'))
                            else:
                                last_time = last_cycle_time
                            
                            time_diff = datetime.now() - last_time.replace(tzinfo=None)
                            crawler_status["last_activity"] = last_cycle_time
                            
                            # Consider crawler running if activity within last hour
                            if time_diff.total_seconds() < 3600:  # 1 hour
                                crawler_status["is_running"] = True
                                logger.info(f"✅ Crawler cycle active (last activity: {last_cycle_time})")
                            else:
                                logger.warning(f"⚠️ Crawler cycle inactive (last activity: {last_cycle_time}, {time_diff} ago)")
                                
                        except Exception as time_parse_error:
                            logger.warning(f"Could not parse last cycle time: {time_parse_error}")
                    
                    # Check for active operations
                    if self.metrics.is_operation_running("crawl_cycle"):
                        crawler_status["is_running"] = True
                        logger.info("✅ Crawler cycle operation currently running")
                    
                    # Check crawling metrics
                    crawl_stats = current_stats.get("crawling", {})
                    if crawl_stats.get("active_sources", 0) > 0:
                        crawler_status["is_running"] = True
                        logger.info(f"✅ Crawler has {crawl_stats['active_sources']} active sources")
                        
            except Exception as metrics_error:
                logger.warning(f"Could not check metrics for crawler status: {metrics_error}")
                crawler_status["error"] = f"metrics_check_failed: {str(metrics_error)}"
            
            # Check health status for crawler components
            try:
                health_status = self.health_check.get_status()
                crawler_health = health_status.get("components", {}).get("crawler", {})
                
                if crawler_health.get("status") == "healthy":
                    logger.info("✅ Crawler component reports healthy")
                else:
                    logger.warning(f"⚠️ Crawler component health: {crawler_health}")
                    
            except Exception as health_error:
                logger.warning(f"Could not check health status: {health_error}")
            
            # Log final status
            if not crawler_status["is_running"]:
                logger.warning("❌ Crawler cycle appears to be not running")
                
                # Track in App Insights
                self.app_insights.track_event("crawler_cycle_not_running", {
                    "check_time": crawler_status["check_time"],
                    "last_activity": crawler_status["last_activity"],
                    "error": crawler_status["error"],
                    "severity": "warning"
                })
                
                # Send alert about inactive crawler
                await self._send_crawler_inactive_alert(crawler_status)
            else:
                logger.info("✅ Crawler cycle is running normally")
                
                # Track successful status in App Insights
                self.app_insights.track_event("crawler_cycle_running", {
                    "check_time": crawler_status["check_time"],
                    "last_activity": crawler_status["last_activity"]
                })
            
            return crawler_status
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"💥 Error checking crawler cycle status: {error_msg}")
            
            # Track exception in App Insights
            self.app_insights.track_exception(e, {
                "operation": "check_crawler_cycle_status",
                "error": error_msg
            })
            
            return {
                "is_running": False,
                "last_activity": None,
                "error": error_msg,
                "check_time": datetime.now().isoformat(),
                "check_failed": True
            }
    async def _send_crawler_inactive_alert(self, crawler_status: Dict[str, Any]):
        """Send alert when crawler cycle is not running."""
        try:
            last_activity = crawler_status.get("last_activity", "Unknown")
            error_details = crawler_status.get("error", "No specific error")
            
            alert_message = (
                "⚠️ CRAWLER CYCLE NOT RUNNING\n\n"
                f"🕐 Check Time: {crawler_status['check_time']}\n"
                f"📅 Last Activity: {last_activity}\n"
                f"🔍 Details: {error_details}\n\n"
                "🚨 This may affect news crawling operations.\n"
                "Please check crawler health and restart if needed."
            )
            
            self.alert_manager.send_alert(
                "crawler_cycle_inactive",
                alert_message,
                {
                    "alert_type": "crawler_status",
                    "severity": "warning",
                    "last_activity": last_activity,
                    "error": error_details,
                    "check_time": crawler_status["check_time"],
                    "system": "cleanup_monitor"
                }
            )
            
            logger.info("📢 Sent crawler inactive alert")
            
        except Exception as e:
            logger.error(f"Failed to send crawler inactive alert: {e}")

    async def run_monitored_cleanup(self, hours: int = 24, force: bool = False, check_crawler: bool = True) -> Dict[str, Any]:
        """
        Run cleanup with comprehensive monitoring and error handling.
        
        Args:
            hours: Hours of data to keep (delete older)
            force: Force cleanup even if health checks fail
            check_crawler: Check if crawler cycle is running before cleanup
            
        Returns:
            Dict with cleanup results and monitoring data
        """
        
        # Start App Insights operation tracking
        with self.app_insights.start_operation(f"cleanup_operation_{cleanup_id}"):
            try:
                return await self._execute_cleanup_with_monitoring(cleanup_id, hours, force, check_crawler)
            except Exception as e:
                logger.error(f"💥 Critical error in cleanup monitor: {e}")
                
                # Track exception in App Insights with context
                self.app_insights.track_exception(e, {
                    "operation": "cleanup_monitor",
                    "cleanup_id": cleanup_id,
                    "hours": hours,
                    "force": force,
                    "error_type": type(e).__name__
                })
                
                # Send critical alert
                await self._send_critical_alert(cleanup_id, e, {"hours": hours, "force": force})
                
                return {
                    "success": False,
                    "cleanup_id": cleanup_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
    
    async def _execute_cleanup_with_monitoring(self, cleanup_id: str, hours: int, force: bool, check_crawler: bool = True) -> Dict[str, Any]:
        """Execute cleanup with detailed monitoring."""
        start_time = datetime.now()
        
        logger.info(f"🚀 Starting monitored cleanup: {cleanup_id}")
        logger.info(f"📊 Parameters: hours={hours}, force={force}, check_crawler={check_crawler}")
        
        # Track cleanup start in App Insights
        self.app_insights.track_event("cleanup_started", {
            "cleanup_id": cleanup_id,
            "hours": hours,
            "force": force,
            "check_crawler": check_crawler,
            "start_time": start_time.isoformat()
        })
        
        # Check crawler cycle status if requested
        crawler_status = None
        if check_crawler:
            logger.info("🔍 Checking crawler cycle status before cleanup...")
            crawler_status = await self.check_crawler_cycle_status()
            
            if not crawler_status["is_running"] and not force:
                error_msg = f"Crawler cycle not running - cleanup may be unsafe: {crawler_status.get('error', 'No activity detected')}"
                logger.warning(f"⚠️ {error_msg}")
                
                # Track in App Insights
                self.app_insights.track_event("cleanup_aborted_crawler_inactive", {
                    "cleanup_id": cleanup_id,
                    "crawler_status": crawler_status,
                    "force": force
                })
                
                return {
                    "success": False,
                    "cleanup_id": cleanup_id,
                    "reason": "crawler_inactive",
                    "crawler_status": crawler_status,
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                }
            elif not crawler_status["is_running"] and force:
                logger.warning("⚠️ Crawler cycle not running, but FORCE mode enabled - proceeding")
        
        # Pre-cleanup health check
        health_status = await self._check_system_health()
        if not health_status["healthy"] and not force:
            error_msg = f"System unhealthy - skipping cleanup: {health_status['issues']}"
            logger.warning(f"⚠️ {error_msg}")
            
            # Track in App Insights
            self.app_insights.track_event("cleanup_skipped_unhealthy", {
                "cleanup_id": cleanup_id,
                "health_issues": health_status["issues"],
                "force": force
            })
            
            return {
                "success": False,
                "cleanup_id": cleanup_id,
                "reason": "system_unhealthy",
                "health_issues": health_status["issues"],
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            }
        
        # Get pre-cleanup metrics
        pre_cleanup_stats = await self._get_system_stats()
        logger.info(f"📊 Pre-cleanup stats: {pre_cleanup_stats}")
        
        # Execute cleanup with error handling
        try:
            cleanup_result = await cleanup_old_data(hours)
            
            # Get post-cleanup metrics
            post_cleanup_stats = await self._get_system_stats()
            
            # Calculate cleanup impact
            cleanup_impact = self._calculate_cleanup_impact(pre_cleanup_stats, post_cleanup_stats)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if cleanup_result:
                logger.info(f"✅ Cleanup completed successfully in {duration:.2f}s")
                logger.info(f"📊 Cleanup impact: {cleanup_impact}")
                
                # Track success in App Insights
                self.app_insights.track_event("cleanup_completed", {
                    "cleanup_id": cleanup_id,
                    "success": True,
                    "duration_seconds": duration,
                    "documents_before": pre_cleanup_stats.get("document_count", 0),
                    "documents_after": post_cleanup_stats.get("document_count", 0),
                    "documents_deleted": cleanup_impact.get("documents_deleted", 0),
                    "space_freed_mb": cleanup_impact.get("space_freed_mb", 0)
                })
                
                # Track cleanup metrics
                self.app_insights.track_metric("cleanup_duration_seconds", duration)
                self.app_insights.track_metric("documents_deleted", cleanup_impact.get("documents_deleted", 0))
                
                # Send success notification
                await self._send_success_notification(cleanup_id, cleanup_impact, duration)
                
                return {
                    "success": True,
                    "cleanup_id": cleanup_id,
                    "duration_seconds": duration,
                    "pre_cleanup_stats": pre_cleanup_stats,
                    "post_cleanup_stats": post_cleanup_stats,
                    "cleanup_impact": cleanup_impact,
                    "health_status": health_status
                }
            else:
                # Cleanup failed
                error_msg = "Cleanup function returned False"
                logger.error(f"❌ {error_msg}")
                
                # Track failure in App Insights
                self.app_insights.track_event("cleanup_failed", {
                    "cleanup_id": cleanup_id,
                    "error": error_msg,
                    "duration_seconds": duration,
                    "pre_cleanup_stats": pre_cleanup_stats
                })
                
                # Send failure alert
                await self._send_failure_alert(cleanup_id, error_msg, {
                    "hours": hours,
                    "duration": duration,
                    "pre_cleanup_stats": pre_cleanup_stats
                })
                
                return {
                    "success": False,
                    "cleanup_id": cleanup_id,
                    "error": error_msg,
                    "duration_seconds": duration,
                    "pre_cleanup_stats": pre_cleanup_stats
                }
                
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = str(e)
            error_type = type(e).__name__
            stack_trace = traceback.format_exc()
            
            logger.error(f"💥 Cleanup failed with exception: {error_msg}")
            logger.error(f"🔍 Stack trace: {stack_trace}")
            
            # Track exception in App Insights with full context
            self.app_insights.track_exception(e, {
                "cleanup_id": cleanup_id,
                "operation": "cleanup_execution", 
                "hours": hours,
                "duration_seconds": duration,
                "pre_cleanup_stats": pre_cleanup_stats,
                "stack_trace": stack_trace
            })
            
            # Track failure event
            self.app_insights.track_event("cleanup_exception", {
                "cleanup_id": cleanup_id,
                "error": error_msg,
                "error_type": error_type,
                "duration_seconds": duration
            })
            
            # Update health check
            self.health_check.update_dependency_status("cleanup_system", False, error_msg)
            
            # Send critical alert
            await self._send_critical_alert(cleanup_id, e, {
                "hours": hours,
                "duration": duration,
                "pre_cleanup_stats": pre_cleanup_stats,
                "stack_trace": stack_trace
            })
            
            return {
                "success": False,
                "cleanup_id": cleanup_id,
                "error": error_msg,
                "error_type": error_type,
                "duration_seconds": duration,
                "pre_cleanup_stats": pre_cleanup_stats,
                "stack_trace": stack_trace
            }
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """Check system health before cleanup."""
        try:
            health_status = self.health_check.get_status()
            issues = []
            
            # Check key dependencies
            if not health_status.get("dependencies", {}).get("qdrant", {}).get("status"):
                issues.append("Qdrant unavailable")
            
            if not health_status.get("dependencies", {}).get("azure", {}).get("status"):
                issues.append("Azure Storage unavailable")
            
            # Check if cleanup is already running
            if self.metrics.is_operation_running("cleanup"):
                issues.append("Another cleanup operation is running")
            
            return {
                "healthy": len(issues) == 0,
                "issues": issues,
                "full_status": health_status
            }
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return {
                "healthy": False,
                "issues": [f"Health check failed: {str(e)}"],
                "error": str(e)
            }
    
    async def _get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics."""
        try:
            stats = {}
            
            # Get vector database stats
            vector_client = None
            try:
                vector_client = create_vector_client()
                collection_info = await vector_client.get_collection_info()
                if collection_info:
                    stats["document_count"] = collection_info.get("vectors_count", 0)
                    stats["collection_size_bytes"] = collection_info.get("size_bytes", 0)
            except Exception as e:
                logger.warning(f"Could not get vector stats: {e}")
                stats["vector_error"] = str(e)
            finally:
                if vector_client:
                    await vector_client.close()
            
            # Get metrics stats
            try:
                metrics_stats = self.metrics.get_current_stats()
                stats.update(metrics_stats)
            except Exception as e:
                logger.warning(f"Could not get metrics stats: {e}")
                stats["metrics_error"] = str(e)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {"error": str(e)}
    
    def _calculate_cleanup_impact(self, pre_stats: Dict, post_stats: Dict) -> Dict[str, Any]:
        """Calculate the impact of cleanup operation."""
        impact = {}
        
        try:
            # Document count impact
            pre_docs = pre_stats.get("document_count", 0)
            post_docs = post_stats.get("document_count", 0)
            impact["documents_deleted"] = max(0, pre_docs - post_docs)
            
            # Storage impact
            pre_size = pre_stats.get("collection_size_bytes", 0)
            post_size = post_stats.get("collection_size_bytes", 0)
            impact["bytes_freed"] = max(0, pre_size - post_size)
            impact["space_freed_mb"] = impact["bytes_freed"] / (1024 * 1024)
            
            # Calculate percentage impact
            if pre_docs > 0:
                impact["documents_deleted_percent"] = (impact["documents_deleted"] / pre_docs) * 100
            
            if pre_size > 0:
                impact["space_freed_percent"] = (impact["bytes_freed"] / pre_size) * 100
            
        except Exception as e:
            logger.error(f"Error calculating cleanup impact: {e}")
            impact["calculation_error"] = str(e)
        
        return impact
    
    async def _send_success_notification(self, cleanup_id: str, impact: Dict, duration: float):
        """Send success notification through existing alert system."""
        try:
            self.alert_manager.send_alert(
                "cleanup_success",
                f"✅ Cleanup completed successfully: {cleanup_id}",
                {
                    "cleanup_id": cleanup_id,
                    "duration_seconds": duration,
                    "documents_deleted": impact.get("documents_deleted", 0),
                    "space_freed_mb": round(impact.get("space_freed_mb", 0), 2),
                    "success": True
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send success notification: {e}")
    
    async def _send_failure_alert(self, cleanup_id: str, error_msg: str, context: Dict):
        """Send failure alert through existing alert system."""
        try:
            self.alert_manager.send_alert(
                "cleanup_failure",
                f"❌ Cleanup failed: {cleanup_id} - {error_msg}",
                {
                    "cleanup_id": cleanup_id,
                    "error": error_msg,
                    "severity": "warning",
                    **context
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send failure alert: {e}")
    
    async def _send_critical_alert(self, cleanup_id: str, exception: Exception, context: Dict):
        """Send critical alert for exceptions."""
        try:
            self.alert_manager.send_alert(
                "cleanup_critical_error",
                f"💥 CRITICAL: Cleanup system error: {cleanup_id} - {str(exception)}",
                {
                    "cleanup_id": cleanup_id,
                    "error": str(exception),
                    "error_type": type(exception).__name__,
                    "severity": "critical",
                    **context
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send critical alert: {e}")


async def main():
    """Main function to run enhanced cleanup monitoring."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Cleanup Monitor for NewsRaag Crawler")
    parser.add_argument("--hours", type=int, default=24, help="Hours of data to keep (default: 24)")
    parser.add_argument("--force", action="store_true", help="Force cleanup even if system is unhealthy")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be cleaned without actually doing it")
    parser.add_argument("--demo-alert", action="store_true", help="Send demo alert to test alert system")
    parser.add_argument("--no-crawler-check", action="store_true", help="Skip crawler cycle status check")
    parser.add_argument("--startup", action="store_true", help="Run startup checks and demo alert")
    
    args = parser.parse_args()
    
    # Initialize monitoring infrastructure
    logger.info("🔧 Initializing monitoring infrastructure...")
    init_monitoring()
    
    # Create cleanup monitor
    cleanup_monitor = CleanupMonitor()
    
    # Handle startup mode
    if args.startup or args.demo_alert:
        logger.info("🚀 Running in startup mode...")
        
        # Send demo alert
        demo_success = await cleanup_monitor.send_demo_alert_on_startup()
        if demo_success:
            logger.info("✅ Demo alert sent successfully")
        else:
            logger.error("❌ Failed to send demo alert")
        
        # Check crawler status
        logger.info("🔍 Checking crawler cycle status...")
        crawler_status = await cleanup_monitor.check_crawler_cycle_status()
        
        if crawler_status["is_running"]:
            logger.info("✅ Crawler cycle is running normally")
        else:
            logger.warning("⚠️ Crawler cycle is not running!")
            logger.info(f"📊 Crawler Status: {crawler_status}")
        
        # If only demo alert was requested, exit here
        if args.demo_alert and not args.startup:
            return
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No actual cleanup will be performed")
        
        # In dry-run, show what would be checked/cleaned
        logger.info("📋 Dry run would perform:")
        logger.info(f"  - Health check of system components")
        if not args.no_crawler_check:
            logger.info(f"  - Crawler cycle status verification")
        logger.info(f"  - Cleanup simulation for data older than {args.hours} hours")
        logger.info(f"  - Force mode: {'Enabled' if args.force else 'Disabled'}")
        return
    
    # Run monitored cleanup
    logger.info(f"🧹 Starting cleanup with monitoring")
    logger.info(f"📊 Parameters: hours={args.hours}, force={args.force}, check_crawler={not args.no_crawler_check}")
    
    result = await cleanup_monitor.run_monitored_cleanup(
        hours=args.hours,
        force=args.force,
        check_crawler=not args.no_crawler_check
    )
    
    # Print results
    logger.info("📊 Cleanup Results:")
    logger.info(f"  Success: {result['success']}")
    logger.info(f"  Cleanup ID: {result['cleanup_id']}")
    logger.info(f"  Duration: {result.get('duration_seconds', 0):.2f}s")
    
    # Show crawler status if it was checked
    if result.get('crawler_status'):
        crawler_status = result['crawler_status']
        logger.info(f"  Crawler Running: {crawler_status['is_running']}")
        if crawler_status.get('last_activity'):
            logger.info(f"  Last Activity: {crawler_status['last_activity']}")
    
    if result['success']:
        impact = result.get('cleanup_impact', {})
        logger.info(f"  Documents deleted: {impact.get('documents_deleted', 0)}")
        logger.info(f"  Space freed: {impact.get('space_freed_mb', 0):.2f} MB")
    else:
        logger.error(f"  Error: {result.get('error', 'Unknown error')}")
        if result.get('reason') == 'crawler_inactive':
            logger.error("  Reason: Crawler cycle is not running (use --force to override)")
    
    # Exit with appropriate code
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    asyncio.run(main())
