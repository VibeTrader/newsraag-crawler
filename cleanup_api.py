"""
Cleanup API Endpoint for Azure App Service
------------------------------------------
This module provides HTTP endpoints to trigger cleanup operations.
Designed to be called by Azure Logic Apps for scheduled execution.

Endpoints:
  POST /api/cleanup - Trigger cleanup operation
  GET /api/cleanup/status - Get last cleanup status
"""

import asyncio
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from loguru import logger
import traceback
import pytz

# Import cleanup components
from clients.vector_client import VectorClient
from monitoring.app_insights import get_app_insights
from monitoring.alerts import get_alert_manager
from monitoring.metrics import get_metrics

# Create Blueprint
cleanup_bp = Blueprint('cleanup', __name__, url_prefix='/api/cleanup')

# Store last cleanup result (in-memory)
last_cleanup_result = {
    "timestamp": None,
    "status": "never_run",
    "message": "Cleanup has not been executed yet"
}


async def run_cleanup_operation(retention_hours: int = 24) -> dict:
    """
    Execute cleanup operation with full monitoring.
    
    Args:
        retention_hours: Data retention period in hours (default: 24)
        
    Returns:
        dict: Cleanup results with status, counts, and timing
    """
    global last_cleanup_result
    
    cleanup_start = datetime.utcnow()
    operation_id = None
    
    try:
        logger.info("="*70)
        logger.info("🧹 API TRIGGERED CLEANUP STARTING")
        logger.info(f"⏰ Timestamp: {cleanup_start.isoformat()}")
        logger.info(f"📅 Retention: {retention_hours} hours")
        logger.info("="*70)
        
        # Initialize monitoring
        app_insights = get_app_insights()
        alert_manager = get_alert_manager()
        metrics = get_metrics()
        
        # Start tracking
        if app_insights.enabled:
            operation_id = app_insights.start_operation("api_cleanup")
            logger.info(f"📊 App Insights operation started: {operation_id}")
        
        deletion_id = metrics.start_deletion_process()
        logger.info(f"📈 Metrics tracking started: {deletion_id}")
        
        # Calculate cutoff time
        pst = pytz.timezone('US/Pacific')
        cutoff_time = datetime.now(pst) - timedelta(hours=retention_hours)
        
        # Get statistics BEFORE cleanup
        vector_client = VectorClient()
        
        try:
            logger.info("\n📊 BEFORE CLEANUP:")
            before_stats = await vector_client.get_collection_stats()
            
            if before_stats:
                before_count = before_stats.get('points_count', 0)
                collection_name = before_stats.get('collection_name', 'unknown')
                segments_count = before_stats.get('segments_count', 0)
                
                logger.info(f"   📦 Collection: {collection_name}")
                logger.info(f"   📄 Documents: {before_count:,}")
                logger.info(f"   🗂️  Segments: {segments_count}")
            else:
                logger.warning("   ⚠️  Could not retrieve collection stats")
                before_count = 0
            
            # Perform cleanup using the proven cleanup function
            logger.info(f"\n🗑️  DELETING documents older than {retention_hours} hours...")
            logger.info(f"   Cutoff time: {cutoff_time.isoformat()}")
            
            # Use the cleanup_old_data function that works in manual_cleanup.py
            from crawler.utils.cleanup import cleanup_old_data
            success = await cleanup_old_data(retention_hours)
            
            if not success:
                raise Exception("Cleanup operation failed - check logs for details")
            
            # Get statistics AFTER cleanup
            logger.info("\n📊 AFTER CLEANUP:")
            after_stats = await vector_client.get_collection_stats()
            
            if after_stats:
                after_count = after_stats.get('points_count', 0)
                logger.info(f"   📄 Documents: {after_count:,}")
                
                # Calculate deletion statistics
                deleted_count = before_count - after_count
                percentage = (deleted_count / before_count * 100) if before_count > 0 else 0
                duration = (datetime.utcnow() - cleanup_start).total_seconds()
                
                logger.info(f"\n✅ CLEANUP RESULTS:")
                logger.info(f"   🗑️  Deleted: {deleted_count:,} documents")
                logger.info(f"   📊 Percentage: {percentage:.2f}%")
                logger.info(f"   ⏱️  Duration: {duration:.2f}s")
                
                # Record metrics
                metrics.record_documents_deleted(deleted_count, "qdrant")
                metrics.end_deletion_process(success=True)
                
                # Track in App Insights
                if app_insights.enabled:
                    app_insights.track_documents_deleted(deleted_count, "qdrant")
                    app_insights.track_deletion_duration(duration)
                    app_insights.track_event("api_cleanup_success", {
                        "deleted_count": str(deleted_count),
                        "retention_hours": str(retention_hours),
                        "before_count": str(before_count),
                        "after_count": str(after_count),
                        "percentage": f"{percentage:.2f}%",
                        "duration_seconds": f"{duration:.2f}",
                        "trigger": "api"
                    })
                
                # Send SUCCESS alert to Slack
                success_message = (
                    f"✅ API cleanup completed successfully\n"
                    f"🗑️ Deleted: {deleted_count:,} documents ({percentage:.2f}%)\n"
                    f"📊 Before: {before_count:,} | After: {after_count:,}\n"
                    f"⏱️ Duration: {duration:.2f}s\n"
                    f"📅 Retention: {retention_hours} hours\n"
                    f"🎯 Trigger: Azure Logic App"
                )
                
                alert_manager._send_alert(
                    alert_type="api_cleanup_success",
                    message=success_message,
                    data={
                        "deleted_count": deleted_count,
                        "before_count": before_count,
                        "after_count": after_count,
                        "percentage": f"{percentage:.2f}%",
                        "duration_seconds": f"{duration:.2f}",
                        "retention_hours": retention_hours,
                        "trigger": "api",
                        "timestamp": cleanup_start.isoformat()
                    }
                )
                
                logger.info("✅ Success alert sent to Slack")
                
                # Update last result
                last_cleanup_result = {
                    "timestamp": cleanup_start.isoformat(),
                    "status": "success",
                    "deleted_count": deleted_count,
                    "before_count": before_count,
                    "after_count": after_count,
                    "percentage": f"{percentage:.2f}%",
                    "duration_seconds": f"{duration:.2f}",
                    "retention_hours": retention_hours,
                    "message": f"Successfully deleted {deleted_count} documents"
                }
                
                logger.info("\n" + "="*70)
                logger.info("✅ API CLEANUP COMPLETED SUCCESSFULLY")
                logger.info("="*70)
                
                return {
                    "status": "success",
                    "deleted_count": deleted_count,
                    "before_count": before_count,
                    "after_count": after_count,
                    "percentage": percentage,
                    "duration_seconds": duration,
                    "retention_hours": retention_hours,
                    "timestamp": cleanup_start.isoformat(),
                    "message": "Cleanup completed successfully"
                }
                
            else:
                logger.error("   ❌ Could not retrieve collection stats after cleanup")
                raise Exception("Failed to verify cleanup results")
                
        finally:
            # Always close vector client
            await vector_client.close()
            logger.info("🔒 Vector client closed")
            
    except Exception as e:
        error_message = str(e)
        error_traceback = traceback.format_exc()
        duration = (datetime.utcnow() - cleanup_start).total_seconds()
        
        logger.error(f"\n❌ CLEANUP FAILED:")
        logger.error(f"   Error: {error_message}")
        logger.error(f"   Traceback:\n{error_traceback}")
        
        # Record failure in metrics
        metrics.record_deletion_error(
            "api_cleanup_failed",
            error_message,
            severity="critical"
        )
        metrics.end_deletion_process(success=False)
        
        # Track failure in App Insights
        if app_insights.enabled:
            app_insights.track_exception(e, {
                "operation": "api_cleanup",
                "retention_hours": str(retention_hours),
                "trigger": "api"
            })
            app_insights.track_event("api_cleanup_failed", {
                "error": error_message,
                "retention_hours": str(retention_hours),
                "trigger": "api"
            })
        
        # Send FAILURE alert to Slack
        failure_message = (
            f"❌ API cleanup FAILED\n"
            f"🚨 Error: {error_message}\n"
            f"⏱️ Duration: {duration:.2f}s\n"
            f"📅 Retention: {retention_hours} hours\n"
            f"🎯 Trigger: Azure Logic App"
        )
        
        alert_manager._send_alert(
            alert_type="api_cleanup_failure",
            message=failure_message,
            data={
                "error": error_message,
                "traceback": error_traceback[:500],  # Truncate for Slack
                "duration_seconds": f"{duration:.2f}",
                "retention_hours": retention_hours,
                "trigger": "api",
                "timestamp": cleanup_start.isoformat()
            }
        )
        
        logger.info("⚠️ Failure alert sent to Slack")
        
        # Update last result
        last_cleanup_result = {
            "timestamp": cleanup_start.isoformat(),
            "status": "failed",
            "error": error_message,
            "duration_seconds": f"{duration:.2f}",
            "retention_hours": retention_hours,
            "message": f"Cleanup failed: {error_message}"
        }
        
        logger.info("\n" + "="*70)
        logger.info("❌ API CLEANUP FAILED")
        logger.info("="*70)
        
        return {
            "status": "failed",
            "error": error_message,
            "duration_seconds": duration,
            "retention_hours": retention_hours,
            "timestamp": cleanup_start.isoformat(),
            "message": "Cleanup operation failed"
        }
        
    finally:
        # Flush App Insights
        if app_insights.enabled and operation_id:
            app_insights.flush()
            logger.info("📊 App Insights telemetry flushed")


@cleanup_bp.route('', methods=['POST'])
def trigger_cleanup():
    """
    Trigger cleanup operation via HTTP POST.
    
    Request body (optional JSON):
    {
        "retention_hours": 24  // Optional, defaults to 24
    }
    
    Returns:
        JSON response with cleanup results
    """
    try:
        # Get retention hours from request
        retention_hours = 24  # Default
        
        if request.is_json:
            data = request.get_json()
            retention_hours = data.get('retention_hours', 24)
        
        # Validate retention hours
        if not isinstance(retention_hours, (int, float)) or retention_hours <= 0:
            return jsonify({
                "status": "error",
                "message": "Invalid retention_hours: must be a positive number"
            }), 400
        
        logger.info(f"Received cleanup request (retention: {retention_hours} hours)")
        
        # Run cleanup asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_cleanup_operation(retention_hours))
        loop.close()
        
        # Return appropriate status code
        if result["status"] == "success":
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Error in cleanup endpoint: {e}")
        logger.error(traceback.format_exc())
        
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@cleanup_bp.route('/status', methods=['GET'])
def get_cleanup_status():
    """
    Get the status of the last cleanup operation.
    
    Returns:
        JSON response with last cleanup result
    """
    return jsonify(last_cleanup_result), 200


@cleanup_bp.route('/health', methods=['GET'])
def cleanup_health():
    """
    Health check endpoint for cleanup service.
    
    Returns:
        JSON response indicating service health
    """
    return jsonify({
        "status": "healthy",
        "service": "cleanup_api",
        "timestamp": datetime.utcnow().isoformat(),
        "last_cleanup": last_cleanup_result.get("timestamp", "never")
    }), 200


# Export blueprint
def register_cleanup_routes(app):
    """
    Register cleanup routes with Flask app.
    
    Args:
        app: Flask application instance
    """
    app.register_blueprint(cleanup_bp)
    logger.info("✅ Cleanup API routes registered")
    logger.info("   POST /api/cleanup - Trigger cleanup")
    logger.info("   GET /api/cleanup/status - Get status")
    logger.info("   GET /api/cleanup/health - Health check")
