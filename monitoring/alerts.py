"""
Advanced alerting system for NewsRagnarok Crawler.
This module provides proactive monitoring and Slack alerts for issues in the crawler.
"""
import os
import time
import json
import asyncio
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import psutil
import requests

from monitoring.metrics import get_metrics
from monitoring.health_check import get_health_check

# Load environment variables
SLACK_WEBHOOK_RAW = os.getenv("ALERT_SLACK_WEBHOOK", "")
# Clean webhook URL to avoid any issues
SLACK_WEBHOOK = SLACK_WEBHOOK_RAW.strip() if SLACK_WEBHOOK_RAW else ""
SLACK_ENABLED = os.getenv("ALERT_SLACK_ENABLED", "false").lower() == "true"
SLACK_CHANNEL_RAW = os.getenv("ALERT_SLACK_CHANNEL", "monitoring-alerts")
# Format channel name properly - add # if missing
SLACK_CHANNEL = SLACK_CHANNEL_RAW if SLACK_CHANNEL_RAW.startswith('#') else f"#{SLACK_CHANNEL_RAW}"

# Alert thresholds
MEMORY_THRESHOLD_MB = float(os.getenv("ALERT_MEMORY_THRESHOLD_MB", "800"))
CYCLE_FAILURE_THRESHOLD = int(os.getenv("ALERT_CYCLE_FAILURE_THRESHOLD", "3"))
EXTRACTION_FAILURE_RATE_THRESHOLD = float(os.getenv("ALERT_EXTRACTION_FAILURE_RATE", "0.5"))  # 50%
CONSECUTIVE_FAILURE_THRESHOLD = int(os.getenv("ALERT_CONSECUTIVE_FAILURE_THRESHOLD", "5"))

# Alert cooldowns (in seconds) to prevent alert storms
ALERT_COOLDOWNS = {
    "memory": 3600,  # 1 hour
    "extraction_failure": 1800,  # 30 minutes
    "cycle_failure": 3600,  # 1 hour
    "dependency": 1800,  # 30 minutes
    "consecutive_failure": 1800,  # 30 minutes
}

class AlertManager:
    """Advanced alert management system for crawler monitoring."""
    
    def __init__(self):
        """Initialize the alert manager."""
        self.last_alerts = {}  # Track when alerts were last sent
        self.consecutive_failures = 0  # Track consecutive failures
        self.monitored_cycles = []  # Track recent cycles for trend analysis
        
        # Load previous state if exists
        self._load_state()
        
        # Start background monitoring thread
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("Alert manager initialized")
        
    def _load_state(self):
        """Load previous alert state from disk if available."""
        try:
            state_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'data',
                'monitoring',
                'alert_state.json'
            )
            if os.path.exists(state_path):
                with open(state_path, 'r') as f:
                    state = json.load(f)
                    self.last_alerts = {k: datetime.fromisoformat(v) if v else None 
                                       for k, v in state.get('last_alerts', {}).items()}
                    self.consecutive_failures = state.get('consecutive_failures', 0)
                    logger.info(f"Loaded alert state: {len(self.last_alerts)} previous alerts")
        except Exception as e:
            logger.error(f"Error loading alert state: {e}")
            self.last_alerts = {}
            self.consecutive_failures = 0
            
    def _save_state(self):
        """Save current alert state to disk."""
        try:
            state_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'data',
                'monitoring'
            )
            os.makedirs(state_dir, exist_ok=True)
            
            state_path = os.path.join(state_dir, 'alert_state.json')
            
            state = {
                'last_alerts': {k: v.isoformat() if v else None for k, v in self.last_alerts.items()},
                'consecutive_failures': self.consecutive_failures
            }
            
            with open(state_path, 'w') as f:
                json.dump(state, f, indent=2)
                
            logger.debug("Saved alert state")
        except Exception as e:
            logger.error(f"Error saving alert state: {e}")
            
    def _monitoring_loop(self):
        """Background thread for continuous monitoring."""
        while self.is_running:
            try:
                # Check system health
                self._check_health()
                
                # Save state after checks
                self._save_state()
                
                # Sleep for next check
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Sleep and retry
                
    def _check_health(self):
        """Check system health and trigger alerts if needed."""
        try:
            # Get current metrics and health
            metrics = get_metrics().get_current_metrics()
            health = get_health_check().get_health_status()
            
            # Check memory usage
            self._check_memory(health)
            
            # Check cycle failures
            self._check_cycle_failures(metrics)
            
            # Check extraction failures
            self._check_extraction_failures(metrics)
            
            # Check dependencies
            self._check_dependencies(health)
            
            # Reset consecutive failures if everything is ok
            if health['status'] == 'healthy':
                if self.consecutive_failures > 0:
                    logger.info(f"Resetting consecutive failures from {self.consecutive_failures} to 0")
                    self.consecutive_failures = 0
            else:
                # Increment consecutive failures for unhealthy state
                self.consecutive_failures += 1
                logger.warning(f"Incremented consecutive failures to {self.consecutive_failures}")
                
                # Alert if threshold reached
                if self.consecutive_failures >= CONSECUTIVE_FAILURE_THRESHOLD:
                    self._send_alert(
                        "consecutive_failure",
                        f"System has been unhealthy for {self.consecutive_failures} consecutive checks",
                        {
                            "consecutive_failures": self.consecutive_failures,
                            "health": health
                        }
                    )
                    
        except Exception as e:
            logger.error(f"Error checking health: {e}")
            
    def _check_memory(self, health: Dict[str, Any]):
        """Check memory usage and alert if high."""
        try:
            memory = health.get('memory', {})
            memory_mb = memory.get('memory_mb', 0)
            
            if memory_mb > MEMORY_THRESHOLD_MB:
                self._send_alert(
                    "memory",
                    f"High memory usage detected: {memory_mb:.2f} MB (threshold: {MEMORY_THRESHOLD_MB} MB)",
                    {
                        "memory_mb": memory_mb,
                        "threshold_mb": MEMORY_THRESHOLD_MB,
                        "process_info": self._get_process_info()
                    }
                )
        except Exception as e:
            logger.error(f"Error checking memory: {e}")
            
    def _check_cycle_failures(self, metrics: Dict[str, Any]):
        """Check cycle failures and alert if above threshold."""
        try:
            cycles_completed = metrics.get('cycles_completed', 0)
            cycles_failed = metrics.get('cycles_failed', 0)
            
            if cycles_failed >= CYCLE_FAILURE_THRESHOLD:
                failure_rate = cycles_failed / max(1, cycles_completed + cycles_failed)
                
                self._send_alert(
                    "cycle_failure",
                    f"High cycle failure rate: {failure_rate:.2%} ({cycles_failed}/{cycles_completed+cycles_failed})",
                    {
                        "cycles_completed": cycles_completed,
                        "cycles_failed": cycles_failed,
                        "failure_rate": failure_rate
                    }
                )
        except Exception as e:
            logger.error(f"Error checking cycle failures: {e}")
            
    def _check_extraction_failures(self, metrics: Dict[str, Any]):
        """Check extraction failures and alert if above threshold."""
        try:
            # Check current cycle if available
            current_cycle = metrics.get('current_cycle', {})
            if current_cycle:
                articles_discovered = current_cycle.get('articles_discovered', 0)
                articles_processed = current_cycle.get('articles_processed', 0)
                articles_failed = current_cycle.get('articles_failed', 0)
                
                if articles_discovered > 5:  # Only check if we have enough articles
                    failure_rate = articles_failed / max(1, articles_discovered)
                    
                    if failure_rate > EXTRACTION_FAILURE_RATE_THRESHOLD:
                        self._send_alert(
                            "extraction_failure",
                            f"High extraction failure rate: {failure_rate:.2%} ({articles_failed}/{articles_discovered})",
                            {
                                "articles_discovered": articles_discovered,
                                "articles_processed": articles_processed,
                                "articles_failed": articles_failed,
                                "failure_rate": failure_rate,
                                "cycle_id": current_cycle.get('cycle_id', 'unknown')
                            }
                        )
        except Exception as e:
            logger.error(f"Error checking extraction failures: {e}")
            
    def _check_dependencies(self, health: Dict[str, Any]):
        """Check dependencies and alert if any are unhealthy."""
        try:
            dependencies = health.get('dependencies', {})
            
            for dep_name, dep_status in dependencies.items():
                if dep_status.get('status') == 'unhealthy':
                    self._send_alert(
                        f"dependency_{dep_name}",
                        f"Dependency '{dep_name}' is unhealthy",
                        {
                            "dependency": dep_name,
                            "error": dep_status.get('error'),
                            "last_check": dep_status.get('last_check')
                        }
                    )
        except Exception as e:
            logger.error(f"Error checking dependencies: {e}")
            
    def _get_process_info(self) -> Dict[str, Any]:
        """Get detailed process information for debugging."""
        try:
            process = psutil.Process(os.getpid())
            
            return {
                "pid": process.pid,
                "memory_info": {
                    "rss_mb": process.memory_info().rss / (1024 * 1024),
                    "vms_mb": process.memory_info().vms / (1024 * 1024)
                },
                "cpu_percent": process.cpu_percent(interval=1),
                "threads": len(process.threads()),
                "open_files": len(process.open_files()),
                "connections": len(process.connections()),
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting process info: {e}")
            return {"error": str(e)}
            
    def _send_alert(self, alert_type: str, message: str, data: Dict[str, Any] = None):
        """Send an alert if cooldown period has passed."""
        now = datetime.now()
        
        # Check if cooldown has passed
        last_sent = self.last_alerts.get(alert_type)
        cooldown = ALERT_COOLDOWNS.get(alert_type, 3600)  # Default 1 hour
        
        if last_sent and (now - last_sent).total_seconds() < cooldown:
            logger.info(f"Alert '{alert_type}' in cooldown ({cooldown}s). Last sent: {last_sent}")
            return
            
        # Update last alert time
        self.last_alerts[alert_type] = now
        
        # Prepare alert data
        alert_data = {
            "type": alert_type,
            "message": message,
            "timestamp": now.isoformat(),
            "host": os.getenv("COMPUTERNAME") or os.getenv("HOSTNAME") or "unknown",
            "environment": os.getenv("ENVIRONMENT", "unknown"),
            "app": "NewsRagnarok Crawler"
        }
        
        if data:
            alert_data["data"] = data
            
        # Log the alert
        logger.warning(f"ALERT: {message}")
        
        # Send to Slack if enabled
        if SLACK_ENABLED:
            self._send_slack_alert(alert_data)
        else:
            logger.info("Slack alerts not enabled. Alert logged only.")
            
    def _send_slack_alert(self, alert_data: Dict[str, Any]):
        """Send an alert to Slack via webhook."""
        if not SLACK_ENABLED:
            logger.warning("Slack alerts not enabled in configuration")
            return
            
        if not SLACK_WEBHOOK:
            logger.warning("Slack alerts enabled but webhook URL not configured")
            return
            
        # Log configuration for debugging
        webhook_preview = SLACK_WEBHOOK[:20] + "..." if SLACK_WEBHOOK else "None"
        logger.info(f"Slack configuration: enabled={SLACK_ENABLED}, channel={SLACK_CHANNEL}, webhook={webhook_preview}")
            
        try:
            # Create alert severity color
            if alert_data['type'].startswith('memory') or alert_data['type'].startswith('consecutive'):
                color = "#FF0000"  # Red for critical
            elif alert_data['type'].startswith('dependency'):
                color = "#FFA500"  # Orange for warnings
            else:
                color = "#36C5F0"  # Blue for info
            
            # Format data details
            data_details = json.dumps(alert_data.get('data', {}), indent=2)
            
            # Create Slack message
            slack_message = {
                "channel": SLACK_CHANNEL,
                "username": "NewsRagnarok Monitor",
                "icon_emoji": ":robot_face:",
                "attachments": [
                    {
                        "fallback": alert_data['message'],
                        "color": color,
                        "title": f"🚨 Alert: {alert_data['type']}",
                        "text": alert_data['message'],
                        "fields": [
                            {
                                "title": "Environment",
                                "value": alert_data['environment'],
                                "short": True
                            },
                            {
                                "title": "Host",
                                "value": alert_data['host'],
                                "short": True
                            },
                            {
                                "title": "Time",
                                "value": alert_data['timestamp'],
                                "short": False
                            }
                        ],
                        "footer": f"{alert_data['app']} | Crawler Alert System",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            # Add data details if available
            if alert_data.get('data'):
                slack_message["attachments"][0]["fields"].append({
                    "title": "Details",
                    "value": f"```{data_details}```",
                    "short": False
                })
            
            # Log the outgoing message
            logger.info(f"Sending Slack alert: type={alert_data['type']}, message={alert_data['message']}")
            
            # Send to Slack webhook
            response = requests.post(
                SLACK_WEBHOOK,
                json=slack_message,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code < 200 or response.status_code >= 300:
                logger.error(f"Slack webhook error: {response.status_code} - {response.text}")
            else:
                logger.info(f"Slack alert sent successfully to {SLACK_CHANNEL}")
                
        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
    def stop(self):
        """Stop the alert manager and background monitoring."""
        self.is_running = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        self._save_state()
        logger.info("Alert manager stopped")

# Global alert manager instance
_alert_manager = None

def get_alert_manager() -> AlertManager:
    """Get the singleton alert manager instance.
    
    Returns:
        AlertManager instance
    """
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager

def trigger_test_alert(message: str = "Test alert", alert_type: str = "test"):
    """Trigger a test alert for testing notification channels.
    
    Args:
        message: Custom message for the test alert
        alert_type: Type of alert to test
    """
    alert_manager = get_alert_manager()
    alert_manager._send_alert(
        alert_type,
        message,
        {
            "test": True,
            "timestamp": datetime.now().isoformat()
        }
    )
    return {"status": "success", "message": "Test alert triggered"}
