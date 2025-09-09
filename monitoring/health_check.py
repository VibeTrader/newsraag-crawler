"""
Health check utilities for NewsRagnarok Crawler.
"""
import os
import json
import time
from typing import Dict, Any, List, Tuple
from loguru import logger
import psutil
from datetime import datetime, timedelta

from monitoring.metrics import get_metrics

class HealthCheck:
    """Manages health checks for the crawler system."""
    
    def __init__(self):
        """Initialize the health check manager."""
        self.start_time = datetime.now()
        self.dependencies_status = {
            "qdrant": {"status": "unknown", "last_check": None, "error": None},
            "azure": {"status": "unknown", "last_check": None, "error": None},
            "openai": {"status": "unknown", "last_check": None, "error": None},
            "redis": {"status": "unknown", "last_check": None, "error": None}
        }
        
        self.last_memory_check = None
        self.last_memory_usage = 0
        
        logger.info("Health check system initialized")
    
    def get_uptime(self) -> str:
        """Get the application uptime as a formatted string.
        
        Returns:
            Formatted uptime string (e.g., "3d 4h 12m 30s")
        """
        delta = datetime.now() - self.start_time
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m {seconds}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """Check current memory usage.
        
        Returns:
            Dictionary with memory metrics
        """
        try:
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            memory_mb = mem_info.rss / (1024 * 1024)
            
            # Update metrics
            metrics = get_metrics()
            metrics.update_memory_usage(memory_mb)
            
            # Check if memory usage is high
            high_memory = memory_mb > 800  # 800MB threshold
            
            self.last_memory_check = datetime.now()
            self.last_memory_usage = memory_mb
            
            return {
                "memory_mb": round(memory_mb, 2),
                "high_memory": high_memory,
                "check_time": self.last_memory_check.isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to check memory usage: {e}")
            return {
                "memory_mb": 0,
                "high_memory": False,
                "error": str(e),
                "check_time": datetime.now().isoformat()
            }
    
    def update_dependency_status(self, dependency: str, status: bool, error: str = None):
        """Update the status of a dependency.
        
        Args:
            dependency: Name of dependency ("qdrant", "azure", "openai", "redis")
            status: Whether the dependency is healthy
            error: Optional error message if unhealthy
        """
        if dependency not in self.dependencies_status:
            logger.warning(f"Unknown dependency: {dependency}")
            return
            
        self.dependencies_status[dependency] = {
            "status": "healthy" if status else "unhealthy",
            "last_check": datetime.now().isoformat(),
            "error": error
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status.
        
        Returns:
            Dictionary with all health metrics
        """
        # Check memory if it hasn't been checked recently
        if not self.last_memory_check or (datetime.now() - self.last_memory_check).total_seconds() > 60:
            memory_status = self.check_memory_usage()
        else:
            memory_status = {
                "memory_mb": round(self.last_memory_usage, 2),
                "check_time": self.last_memory_check.isoformat() if self.last_memory_check else None
            }
        
        # Get metrics
        metrics = get_metrics()
        current_metrics = metrics.get_current_metrics()
        
        # Determine overall status
        unhealthy_dependencies = [
            dep for dep, status in self.dependencies_status.items() 
            if status["status"] == "unhealthy"
        ]
        
        overall_status = "healthy"
        if unhealthy_dependencies:
            overall_status = "degraded"
            
        if memory_status.get("high_memory", False):
            overall_status = "warning"
        
        # Build response
        return {
            "status": overall_status,
            "uptime": self.get_uptime(),
            "dependencies": self.dependencies_status,
            "memory": memory_status,
            "metrics": {
                "cycles_completed": current_metrics.get("cycles_completed", 0),
                "cycles_failed": current_metrics.get("cycles_failed", 0),
                "total_articles_processed": current_metrics.get("total_articles_processed", 0),
                "total_duplicates_detected": current_metrics.get("total_duplicates_detected", 0),
                "last_deletion_time": current_metrics.get("last_deletion_time"),
                "last_deletion_count": current_metrics.get("last_deletion_count", 0)
            },
            "current_cycle": current_metrics.get("current_cycle"),
            "timestamp": datetime.now().isoformat()
        }

# Global health check instance
_health_check = None

def get_health_check() -> HealthCheck:
    """Get the singleton health check instance.
    
    Returns:
        HealthCheck instance
    """
    global _health_check
    if _health_check is None:
        _health_check = HealthCheck()
    return _health_check