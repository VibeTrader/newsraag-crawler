"""
Initialize the monitoring system for NewsRagnarok Crawler.
"""
from loguru import logger
from typing import Tuple

from monitoring.metrics import get_metrics
from monitoring.health_check import get_health_check
from monitoring.duplicate_detector import get_duplicate_detector
from monitoring.app_insights import get_app_insights
from monitoring.alerts import get_alert_manager

def init_monitoring() -> Tuple:
    """Initialize all monitoring components.
    
    Returns:
        Tuple of (metrics, health_check, duplicate_detector, app_insights, alert_manager)
    """
    logger.info("Initializing monitoring system...")
    
    # Get or initialize components
    metrics = get_metrics()
    health_check = get_health_check()
    duplicate_detector = get_duplicate_detector()
    app_insights = get_app_insights()
    alert_manager = get_alert_manager()
    
    logger.info("Monitoring system initialized successfully")
    
    return metrics, health_check, duplicate_detector, app_insights, alert_manager
