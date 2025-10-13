#!/usr/bin/env python3
"""
Crawler Cycle Monitor for NewsRaag Crawler.

Monitors if the crawler cycle is running and sends alerts to App Insights when:
1. Crawler cycle is not running (error alert)
2. App is restarted (demo alert to verify alerting works)
3. Crawler cycle resumes (recovery alert)
"""
import asyncio
import time
import threading
from datetime import datetime, timedelta
from loguru import logger
from typing import Optional, Dict, Any
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from monitoring.app_insights import get_app_insights
from monitoring.alerts import get_alert_manager
from monitoring.metrics import get_metrics
from monitoring.health_check import get_health_check


class CrawlerCycleMonitor:
    """
    Monitor crawler cycle activity and send alerts for various states.
    
    Features:
    - Detects when crawler cycle stops running
    - Sends demo alert on app restart (to verify alerting works)
    - Tracks crawler performance and health
    - Integrates with existing App Insights and alert system
    """
    
    def __init__(self, check_interval: int = 300, max_idle_time: int = 1800):
        """
        Initialize crawler cycle monitor.
        
        Args:
            check_interval: How often to check crawler status (seconds)
            max_idle_time: Max time before considering crawler inactive (seconds)
        """
        self.check_interval = check_interval  # 5 minutes
        self.max_idle_time = max_idle_time    # 30 minutes
        self.last_activity_time = datetime.now()
        self.is_monitoring = False
        self.monitor_thread = None
        self.restart_detected = True  # True on first start to send demo alert
        
        # Initialize monitoring components
        self.app_insights = get_app_insights()
        self.alert_manager = get_alert_manager()
        self.metrics = get_metrics()
        self.health_check = get_health_check()
        
        logger.info("🔄 Crawler Cycle Monitor initialized")
        logger.info(f"   Check interval: {check_interval}s")
        logger.info(f"   Max idle time: {max_idle_time}s")
    
    def record_crawler_activity(self, activity_type: str = "crawl_cycle", details: Dict[str, Any] = None):
        """
        Record that crawler activity occurred.
        
        Args:
            activity_type: Type of activity (crawl_cycle, rss_fetch, article_process, etc.)
            details: Additional details about the activity
        """
        self.last_activity_time = datetime.now()
        
        # Track activity in App Insights
        self.app_insights.track_event("crawler_activity", {
            "activity_type": activity_type,
            "timestamp": self.last_activity_time.isoformat(),
            **(details or {})
        })
        
        # Update health check
        self.health_check.update_dependency_status("crawler_cycle", True, 
                                                  f"Active: {activity_type}")
        
        logger.debug(f"🔄 Crawler activity recorded: {activity_type}")
    
    def start_monitoring(self):
        """Start the crawler cycle monitoring in background thread."""
        if self.is_monitoring:
            logger.warning("Crawler cycle monitor already running")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("🚀 Crawler cycle monitoring started")
        
        # Send demo alert on startup to verify alerting works
        if self.restart_detected:
            asyncio.run(self._send_restart_demo_alert())
            self.restart_detected = False
    
    def stop_monitoring(self):
        """Stop the crawler cycle monitoring."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("🛑 Crawler cycle monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop (runs in background thread)."""
        logger.info("🔍 Crawler cycle monitor loop started")
        
        crawler_was_active = True  # Assume active at start
        
        while self.is_monitoring:
            try:
                current_time = datetime.now()
                time_since_activity = (current_time - self.last_activity_time).total_seconds()
                
                # Check if crawler has been idle too long
                if time_since_activity > self.max_idle_time:
                    if crawler_was_active:
                        # Crawler just became inactive
                        logger.warning(f"⚠️ Crawler cycle inactive for {time_since_activity:.0f}s")
                        asyncio.run(self._send_inactive_alert(time_since_activity))
                        crawler_was_active = False
                        
                        # Update health check
                        self.health_check.update_dependency_status("crawler_cycle", False, 
                                                                  f"Inactive for {time_since_activity:.0f}s")
                else:
                    if not crawler_was_active:
                        # Crawler became active again
                        logger.info("✅ Crawler cycle resumed activity")
                        asyncio.run(self._send_recovery_alert())
                        crawler_was_active = True
                        
                        # Update health check
                        self.health_check.update_dependency_status("crawler_cycle", True, 
                                                                  "Resumed activity")
                
                # Track monitoring metrics
                self.app_insights.track_metric("crawler_idle_time_seconds", time_since_activity)
                self.app_insights.track_metric("crawler_cycle_active", 1 if crawler_was_active else 0)
                
                # Sleep until next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"💥 Error in crawler monitor loop: {e}")
                
                # Track monitoring error in App Insights
                self.app_insights.track_exception(e, {
                    "operation": "crawler_cycle_monitoring",
                    "error_type": type(e).__name__
                })
                
                time.sleep(self.check_interval)  # Continue monitoring despite errors
        
        logger.info("🔍 Crawler cycle monitor loop ended")
    
    async def _send_restart_demo_alert(self):
        """Send demo alert on app restart to verify alerting works."""
        try:
            restart_time = datetime.now().isoformat()
            
            # Track restart event in App Insights
            self.app_insights.track_event("crawler_app_restarted", {
                "restart_time": restart_time,
                "demo_alert": True,
                "purpose": "verify_alerting_system"
            })
            
            # Send demo alert through alert system
            self.alert_manager.send_alert(
                "crawler_demo_alert",
                f"🚀 DEMO: NewsRaag Crawler Restarted - Alert System Test",
                {
                    "alert_type": "demo",
                    "restart_time": restart_time,
                    "purpose": "Verify that alerting system is working correctly",
                    "severity": "info",
                    "next_check": (datetime.now() + timedelta(seconds=self.check_interval)).isoformat()
                }
            )
            
            logger.info("📢 Demo restart alert sent to verify alerting system")
            
        except Exception as e:
            logger.error(f"Failed to send restart demo alert: {e}")
            self.app_insights.track_exception(e, {"operation": "send_restart_demo_alert"})
    
    async def _send_inactive_alert(self, idle_time: float):
        """Send alert when crawler cycle becomes inactive."""
        try:
            # Track inactivity event in App Insights
            self.app_insights.track_event("crawler_cycle_inactive", {
                "idle_time_seconds": idle_time,
                "idle_time_minutes": idle_time / 60,
                "max_allowed_idle": self.max_idle_time,
                "last_activity": self.last_activity_time.isoformat(),
                "severity": "warning"
            })
            
            # Send critical alert
            self.alert_manager.send_alert(
                "crawler_cycle_inactive",
                f"⚠️ ALERT: Crawler Cycle Inactive for {idle_time/60:.1f} minutes",
                {
                    "alert_type": "crawler_inactive",
                    "idle_time_seconds": idle_time,
                    "idle_time_minutes": round(idle_time / 60, 1),
                    "last_activity": self.last_activity_time.isoformat(),
                    "severity": "warning",
                    "action_required": "Check crawler health and restart if needed"
                }
            )
            
            logger.warning(f"⚠️ Inactive alert sent: {idle_time/60:.1f} minutes idle")
            
        except Exception as e:
            logger.error(f"Failed to send inactive alert: {e}")
            self.app_insights.track_exception(e, {"operation": "send_inactive_alert"})
    
    async def _send_recovery_alert(self):
        """Send alert when crawler cycle recovers from inactive state."""
        try:
            recovery_time = datetime.now().isoformat()
            
            # Track recovery event in App Insights
            self.app_insights.track_event("crawler_cycle_recovered", {
                "recovery_time": recovery_time,
                "severity": "info"
            })
            
            # Send recovery notification
            self.alert_manager.send_alert(
                "crawler_cycle_recovered",
                f"✅ RECOVERY: Crawler Cycle Activity Resumed",
                {
                    "alert_type": "crawler_recovery",
                    "recovery_time": recovery_time,
                    "severity": "info",
                    "status": "Crawler cycle is now active again"
                }
            )
            
            logger.info("✅ Recovery alert sent: Crawler cycle resumed")
            
        except Exception as e:
            logger.error(f"Failed to send recovery alert: {e}")
            self.app_insights.track_exception(e, {"operation": "send_recovery_alert"})
    
    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        current_time = datetime.now()
        idle_time = (current_time - self.last_activity_time).total_seconds()
        is_active = idle_time <= self.max_idle_time
        
        return {
            "is_monitoring": self.is_monitoring,
            "is_crawler_active": is_active,
            "last_activity": self.last_activity_time.isoformat(),
            "idle_time_seconds": idle_time,
            "idle_time_minutes": idle_time / 60,
            "max_idle_time": self.max_idle_time,
            "check_interval": self.check_interval,
            "status": "active" if is_active else "inactive"
        }


# Global instance
_crawler_monitor = None

def get_crawler_monitor() -> CrawlerCycleMonitor:
    """Get or create global crawler monitor instance."""
    global _crawler_monitor
    if _crawler_monitor is None:
        # Get configuration from environment variables
        check_interval = int(os.getenv("CRAWLER_MONITOR_CHECK_INTERVAL", "300"))  # 5 minutes
        max_idle_time = int(os.getenv("CRAWLER_MONITOR_MAX_IDLE", "1800"))        # 30 minutes
        
        _crawler_monitor = CrawlerCycleMonitor(check_interval, max_idle_time)
    
    return _crawler_monitor


# Convenience functions for easy integration
def start_crawler_monitoring():
    """Start crawler cycle monitoring."""
    monitor = get_crawler_monitor()
    monitor.start_monitoring()

def record_crawler_activity(activity_type: str = "crawl_cycle", **details):
    """Record crawler activity (convenience function)."""
    monitor = get_crawler_monitor()
    monitor.record_crawler_activity(activity_type, details)

def stop_crawler_monitoring():
    """Stop crawler cycle monitoring."""
    monitor = get_crawler_monitor()
    monitor.stop_monitoring()

def get_crawler_status():
    """Get crawler monitoring status."""
    monitor = get_crawler_monitor()
    return monitor.get_status()


async def main():
    """Test the crawler cycle monitor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Crawler Cycle Monitor")
    parser.add_argument("--test", action="store_true", help="Run test scenario")
    parser.add_argument("--status", action="store_true", help="Show current status")
    
    args = parser.parse_args()
    
    if args.status:
        monitor = get_crawler_monitor()
        status = monitor.get_status()
        print("Crawler Monitor Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        return
    
    if args.test:
        print("🧪 Testing Crawler Cycle Monitor...")
        
        # Initialize monitor
        monitor = get_crawler_monitor()
        
        # Start monitoring
        monitor.start_monitoring()
        
        print("✅ Demo restart alert sent")
        print("⏳ Waiting 10 seconds...")
        await asyncio.sleep(10)
        
        # Simulate crawler activity
        print("🔄 Simulating crawler activity...")
        monitor.record_crawler_activity("test_crawl", {"test": True, "articles": 5})
        
        print("📊 Current status:")
        status = monitor.get_status()
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        print("\n🎉 Test completed! Check your App Insights for events and alerts.")
        
        # Stop monitoring
        monitor.stop_monitoring()
        return
    
    parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
