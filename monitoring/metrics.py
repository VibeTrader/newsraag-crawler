"""
Metrics collection and monitoring for NewsRagnarok Crawler.
"""
import time
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from loguru import logger

class CrawlerMetrics:
    """Collects and manages metrics for the crawler system."""
    
    def __init__(self, metrics_dir: str = None):
        """Initialize the metrics collector.
        
        Args:
            metrics_dir: Directory to store metrics files
        """
        self.metrics_dir = metrics_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 
            'metrics'
        )
        self._ensure_metrics_dir()
        
        # In-memory metrics storage
        self.current_cycle_metrics = {}
        self.current_cycle_start = None
        self.current_cycle_id = None
        
        # Running metrics (reset on application restart)
        self.running_metrics = {
            "app_start_time": datetime.now().isoformat(),
            "cycles_completed": 0,
            "cycles_failed": 0,
            "total_articles_discovered": 0,
            "total_articles_processed": 0,
            "total_duplicates_detected": 0,
            "total_extraction_failures": 0,
            "last_deletion_time": None,
            "last_deletion_count": 0,
            "memory_usage_mb": 0
        }
        
        logger.info(f"Metrics collection initialized. Storing in: {self.metrics_dir}")
    
    def _ensure_metrics_dir(self):
        """Ensure metrics directory exists."""
        os.makedirs(self.metrics_dir, exist_ok=True)
        
        # Create subdirectories
        os.makedirs(os.path.join(self.metrics_dir, 'cycles'), exist_ok=True)
        os.makedirs(os.path.join(self.metrics_dir, 'deletions'), exist_ok=True)
        os.makedirs(os.path.join(self.metrics_dir, 'daily'), exist_ok=True)
    
    def start_cycle(self, cycle_id: Optional[str] = None) -> str:
        """Start tracking a new crawl cycle.
        
        Args:
            cycle_id: Optional ID for the cycle, or generate timestamp-based ID
            
        Returns:
            The cycle ID
        """
        # Generate cycle ID if not provided
        if not cycle_id:
            cycle_id = f"cycle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_cycle_id = cycle_id
        self.current_cycle_start = time.monotonic()
        self.current_cycle_metrics = {
            "cycle_id": cycle_id,
            "start_time": datetime.now().isoformat(),
            "status": "running",
            "articles_discovered": 0,
            "articles_processed": 0,
            "articles_failed": 0,
            "duplicates_detected": 0,
            "sources": {},
            "errors": [],
            "duration_seconds": 0
        }
        
        logger.info(f"Started metrics collection for cycle: {cycle_id}")
        return cycle_id
    
    def record_article_discovered(self, source: str):
        """Record that an article was discovered from RSS feed.
        
        Args:
            source: Source name (e.g., "babypips")
        """
        if not self.current_cycle_metrics:
            return
            
        self.current_cycle_metrics["articles_discovered"] += 1
        self.running_metrics["total_articles_discovered"] += 1
        
        # Initialize source if not seen before
        if source not in self.current_cycle_metrics["sources"]:
            self.current_cycle_metrics["sources"][source] = {
                "discovered": 0,
                "processed": 0,
                "failed": 0,
                "duplicates": 0
            }
        
        self.current_cycle_metrics["sources"][source]["discovered"] += 1
    
    def record_duplicate_detected(self, source: str, url: str, duplicate_type: str):
        """Record that an article was detected as a duplicate.
        
        Args:
            source: Source name
            url: Article URL
            duplicate_type: Type of duplication (e.g., "url", "content")
        """
        if not self.current_cycle_metrics:
            return
            
        self.current_cycle_metrics["duplicates_detected"] += 1
        self.running_metrics["total_duplicates_detected"] += 1
        
        # Initialize source if not seen before
        if source not in self.current_cycle_metrics["sources"]:
            self.current_cycle_metrics["sources"][source] = {
                "discovered": 0,
                "processed": 0,
                "failed": 0,
                "duplicates": 0
            }
        
        self.current_cycle_metrics["sources"][source]["duplicates"] += 1
        
        # Add to error log with low severity
        self.current_cycle_metrics["errors"].append({
            "type": "duplicate_detected",
            "severity": "info",
            "source": source,
            "url": url,
            "duplicate_type": duplicate_type,
            "timestamp": datetime.now().isoformat()
        })
    
    def record_article_processed(self, source: str, url: str, success: bool, error: Optional[str] = None):
        """Record that an article was processed.
        
        Args:
            source: Source name
            url: Article URL
            success: Whether processing succeeded
            error: Optional error message if failed
        """
        if not self.current_cycle_metrics:
            return
            
        if success:
            self.current_cycle_metrics["articles_processed"] += 1
            self.running_metrics["total_articles_processed"] += 1
            
            # Update source metrics
            if source in self.current_cycle_metrics["sources"]:
                self.current_cycle_metrics["sources"][source]["processed"] += 1
        else:
            self.current_cycle_metrics["articles_failed"] += 1
            self.running_metrics["total_extraction_failures"] += 1
            
            # Update source metrics
            if source in self.current_cycle_metrics["sources"]:
                self.current_cycle_metrics["sources"][source]["failed"] += 1
            
            # Add to error log
            self.current_cycle_metrics["errors"].append({
                "type": "article_processing_failed",
                "severity": "warning",
                "source": source,
                "url": url,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })
    
    def record_cycle_error(self, error_type: str, error_message: str, severity: str = "error"):
        """Record an error that occurred during the cycle.
        
        Args:
            error_type: Type of error
            error_message: Error message
            severity: Error severity ("info", "warning", "error", "critical")
        """
        if not self.current_cycle_metrics:
            return
            
        self.current_cycle_metrics["errors"].append({
            "type": error_type,
            "severity": severity,
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Log the error
        if severity == "critical":
            logger.critical(f"METRICS: {error_type} - {error_message}")
        elif severity == "error":
            logger.error(f"METRICS: {error_type} - {error_message}")
        elif severity == "warning":
            logger.warning(f"METRICS: {error_type} - {error_message}")
        else:
            logger.info(f"METRICS: {error_type} - {error_message}")
    
    def end_cycle(self, success: bool = True):
        """End the current crawl cycle and save metrics.
        
        Args:
            success: Whether the cycle completed successfully
        """
        if not self.current_cycle_metrics or not self.current_cycle_start:
            logger.warning("Attempted to end cycle but no cycle was started")
            return
            
        # Calculate duration
        duration = time.monotonic() - self.current_cycle_start
        self.current_cycle_metrics["duration_seconds"] = round(duration, 2)
        self.current_cycle_metrics["end_time"] = datetime.now().isoformat()
        
        # Set final status
        if success:
            self.current_cycle_metrics["status"] = "completed"
            self.running_metrics["cycles_completed"] += 1
        else:
            self.current_cycle_metrics["status"] = "failed"
            self.running_metrics["cycles_failed"] += 1
        
        # Calculate success rate
        discovered = self.current_cycle_metrics["articles_discovered"]
        processed = self.current_cycle_metrics["articles_processed"]
        duplicates = self.current_cycle_metrics["duplicates_detected"]
        
        if discovered > 0:
            self.current_cycle_metrics["success_rate"] = round(
                processed / (discovered - duplicates) * 100 if (discovered - duplicates) > 0 else 0, 
                2
            )
        else:
            self.current_cycle_metrics["success_rate"] = 100  # No articles to process
        
        # Save cycle metrics to file
        self._save_cycle_metrics()
        
        # Log cycle completion
        success_rate = self.current_cycle_metrics["success_rate"]
        logger.info(
            f"Cycle {self.current_cycle_id} completed in {duration:.2f}s with "
            f"{processed}/{discovered} articles processed ({success_rate}% success rate)"
        )
        
        # Reset for next cycle
        self.current_cycle_id = None
        self.current_cycle_start = None
        self.current_cycle_metrics = {}
    
    def start_deletion_process(self) -> str:
        """Start tracking a deletion process.
        
        Returns:
            The deletion ID
        """
        deletion_id = f"deletion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_deletion = {
            "deletion_id": deletion_id,
            "start_time": datetime.now().isoformat(),
            "status": "running",
            "documents_deleted": 0,
            "errors": [],
            "duration_seconds": 0
        }
        
        self.deletion_start_time = time.monotonic()
        logger.info(f"Started metrics collection for deletion process: {deletion_id}")
        return deletion_id
    
    def record_documents_deleted(self, count: int, source: str = "qdrant"):
        """Record number of documents deleted.
        
        Args:
            count: Number of documents deleted
            source: Source of deletion (e.g., "qdrant", "azure")
        """
        if not hasattr(self, 'current_deletion'):
            return
            
        self.current_deletion["documents_deleted"] += count
        
        # Track by source
        if "sources" not in self.current_deletion:
            self.current_deletion["sources"] = {}
            
        if source not in self.current_deletion["sources"]:
            self.current_deletion["sources"][source] = 0
            
        self.current_deletion["sources"][source] += count
    
    def record_deletion_error(self, error_type: str, error_message: str, severity: str = "error"):
        """Record an error that occurred during deletion.
        
        Args:
            error_type: Type of error
            error_message: Error message
            severity: Error severity ("info", "warning", "error", "critical")
        """
        if not hasattr(self, 'current_deletion'):
            return
            
        self.current_deletion["errors"].append({
            "type": error_type,
            "severity": severity,
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Log the error
        if severity == "critical":
            logger.critical(f"DELETION METRICS: {error_type} - {error_message}")
        elif severity == "error":
            logger.error(f"DELETION METRICS: {error_type} - {error_message}")
        elif severity == "warning":
            logger.warning(f"DELETION METRICS: {error_type} - {error_message}")
        else:
            logger.info(f"DELETION METRICS: {error_type} - {error_message}")
    
    def end_deletion_process(self, success: bool = True):
        """End the current deletion process and save metrics.
        
        Args:
            success: Whether the deletion completed successfully
        """
        if not hasattr(self, 'current_deletion') or not hasattr(self, 'deletion_start_time'):
            logger.warning("Attempted to end deletion but no deletion was started")
            return
            
        # Calculate duration
        duration = time.monotonic() - self.deletion_start_time
        self.current_deletion["duration_seconds"] = round(duration, 2)
        self.current_deletion["end_time"] = datetime.now().isoformat()
        
        # Set final status
        if success:
            self.current_deletion["status"] = "completed"
        else:
            self.current_deletion["status"] = "failed"
        
        # Update running metrics
        self.running_metrics["last_deletion_time"] = self.current_deletion["end_time"]
        self.running_metrics["last_deletion_count"] = self.current_deletion["documents_deleted"]
        
        # Save deletion metrics to file
        self._save_deletion_metrics()
        
        # Log deletion completion
        deleted_count = self.current_deletion["documents_deleted"]
        logger.info(
            f"Deletion {self.current_deletion['deletion_id']} completed in {duration:.2f}s with "
            f"{deleted_count} documents deleted"
        )
        
        # Reset for next deletion
        delattr(self, 'current_deletion')
        delattr(self, 'deletion_start_time')
    
    def update_memory_usage(self, memory_mb: float):
        """Update current memory usage.
        
        Args:
            memory_mb: Memory usage in MB
        """
        self.running_metrics["memory_usage_mb"] = round(memory_mb, 2)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current running metrics.
        
        Returns:
            Dictionary of current metrics
        """
        metrics = self.running_metrics.copy()
        
        # Add current cycle if available
        if self.current_cycle_metrics:
            metrics["current_cycle"] = self.current_cycle_metrics
        
        # Add current deletion if available
        if hasattr(self, 'current_deletion'):
            metrics["current_deletion"] = self.current_deletion
        
        return metrics
    
    def _save_cycle_metrics(self):
        """Save current cycle metrics to file."""
        if not self.current_cycle_metrics:
            return
            
        # Create filename based on cycle ID
        filename = f"{self.current_cycle_id}.json"
        filepath = os.path.join(self.metrics_dir, 'cycles', filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(self.current_cycle_metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cycle metrics: {e}")
    
    def _save_deletion_metrics(self):
        """Save current deletion metrics to file."""
        if not hasattr(self, 'current_deletion'):
            return
            
        # Create filename based on deletion ID
        filename = f"{self.current_deletion['deletion_id']}.json"
        filepath = os.path.join(self.metrics_dir, 'deletions', filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(self.current_deletion, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save deletion metrics: {e}")
    
    def save_daily_metrics(self):
        """Save daily aggregated metrics."""
        today = datetime.now().strftime('%Y%m%d')
        filename = f"daily_{today}.json"
        filepath = os.path.join(self.metrics_dir, 'daily', filename)
        
        daily_metrics = self.running_metrics.copy()
        daily_metrics["timestamp"] = datetime.now().isoformat()
        
        try:
            with open(filepath, 'w') as f:
                json.dump(daily_metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save daily metrics: {e}")

# Global metrics instance
_metrics_instance = None

def get_metrics() -> CrawlerMetrics:
    """Get the singleton metrics instance.
    
    Returns:
        CrawlerMetrics instance
    """
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = CrawlerMetrics()
    return _metrics_instance
