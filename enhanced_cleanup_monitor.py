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
    
    async def run_monitored_cleanup(self, hours: int = 24, force: bool = False) -> Dict[str, Any]:
        """
        Run cleanup with comprehensive monitoring and error handling.
        
        Args:
            hours: Hours of data to keep (delete older)
            force: Force cleanup even if health checks fail
            
        Returns:
            Dict with cleanup results and monitoring data
        """
        cleanup_id = f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Start App Insights operation tracking
        with self.app_insights.start_operation(f"cleanup_operation_{cleanup_id}"):
            try:
                return await self._execute_cleanup_with_monitoring(cleanup_id, hours, force)
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
    
    async def _execute_cleanup_with_monitoring(self, cleanup_id: str, hours: int, force: bool) -> Dict[str, Any]:
        """Execute cleanup with detailed monitoring."""
        start_time = datetime.now()
        
        logger.info(f"🚀 Starting monitored cleanup: {cleanup_id}")
        logger.info(f"📊 Parameters: hours={hours}, force={force}")
        
        # Track cleanup start in App Insights
        self.app_insights.track_event("cleanup_started", {
            "cleanup_id": cleanup_id,
            "hours": hours,
            "force": force,
            "start_time": start_time.isoformat()
        })
        
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
    
    args = parser.parse_args()
    
    # Initialize monitoring infrastructure
    logger.info("🔧 Initializing monitoring infrastructure...")
    init_monitoring()
    
    # Create cleanup monitor
    cleanup_monitor = CleanupMonitor()
    
    if args.dry_run:
        logger.info("🔍 DRY RUN MODE - No actual cleanup will be performed")
        # You could add dry-run logic here
        return
    
    # Run monitored cleanup
    logger.info(f"🧹 Starting cleanup with monitoring (hours={args.hours}, force={args.force})")
    
    result = await cleanup_monitor.run_monitored_cleanup(
        hours=args.hours,
        force=args.force
    )
    
    # Print results
    logger.info("📊 Cleanup Results:")
    logger.info(f"  Success: {result['success']}")
    logger.info(f"  Cleanup ID: {result['cleanup_id']}")
    logger.info(f"  Duration: {result.get('duration_seconds', 0):.2f}s")
    
    if result['success']:
        impact = result.get('cleanup_impact', {})
        logger.info(f"  Documents deleted: {impact.get('documents_deleted', 0)}")
        logger.info(f"  Space freed: {impact.get('space_freed_mb', 0):.2f} MB")
    else:
        logger.error(f"  Error: {result.get('error', 'Unknown error')}")
    
    # Exit with appropriate code
    sys.exit(0 if result['success'] else 1)


if __name__ == "__main__":
    asyncio.run(main())
