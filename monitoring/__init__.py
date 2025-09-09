"""
Initialization module for NewsRagnarok monitoring.
"""
from loguru import logger
from monitoring.metrics import get_metrics
from monitoring.health_check import get_health_check
from monitoring.duplicate_detector import get_duplicate_detector
from monitoring.app_insights import get_app_insights

def init_monitoring():
    """Initialize all monitoring components."""
    logger.info("Initializing monitoring system...")
    
    # Initialize metrics collector
    metrics = get_metrics()
    logger.info("Metrics collector initialized")
    
    # Initialize health check system
    health_check = get_health_check()
    logger.info("Health check system initialized")
    
    # Initialize duplicate detector
    duplicate_detector = get_duplicate_detector()
    logger.info("Duplicate detector initialized")
    
    # Initialize Application Insights
    app_insights = get_app_insights()
    if app_insights.enabled:
        logger.info("Azure Application Insights initialized")
    else:
        logger.warning("Azure Application Insights not configured - skipping cloud monitoring")
    
    return metrics, health_check, duplicate_detector, app_insights