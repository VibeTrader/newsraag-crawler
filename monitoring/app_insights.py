"""
Azure Application Insights integration for NewsRagnarok Crawler.
"""
import os
import logging
import time
from datetime import datetime
from loguru import logger
from applicationinsights import TelemetryClient
from applicationinsights.logging import LoggingHandler

class AppInsightsMonitoring:
    """Azure Application Insights integration for monitoring."""
    
    def __init__(self, instrumentation_key=None):
        """Initialize Application Insights monitoring.
        
        Args:
            instrumentation_key: Application Insights instrumentation key.
                If None, loads from APPINSIGHTS_INSTRUMENTATIONKEY environment variable.
        """
        # Try to get instrumentation key from environment variable
        self.instrumentation_key = instrumentation_key or os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY")
        
        if not self.instrumentation_key:
            logger.warning("Application Insights instrumentation key not set. Monitoring disabled.")
            self.enabled = False
            return
            
        self.enabled = True
        self.client = TelemetryClient(self.instrumentation_key)
        
        # Enable live metrics
        self.client.channel.sender.send_interval = 5.0  # send data every 5 seconds
        
        # Set common properties for all telemetry
        self.client.context.properties['service'] = 'newsraag-crawler'
        self.client.context.properties['environment'] = os.getenv('ENVIRONMENT', 'development')
        
        # Configure logging integration
        self._configure_logging()
        
        logger.info(f"Azure Application Insights monitoring initialized with key: {self.instrumentation_key[:8]}...")
    
    def _configure_logging(self):
        """Configure logging integration with Application Insights."""
        # Add Azure Log Handler to Python logging
        handler = LoggingHandler(self.instrumentation_key)
        handler.setLevel(logging.INFO)
        
        # Configure handler
        logging.getLogger().addHandler(handler)
        
        # Keep a reference
        self.log_handler = handler
        
        # Configure loguru integration
        class InterceptHandler(logging.Handler):
            def emit(self, record):
                # Get corresponding Loguru level if it exists
                try:
                    level = logger.level(record.levelname).name
                except ValueError:
                    level = record.levelno
                
                # Find caller from where originated the logged message
                frame, depth = logging.currentframe(), 2
                while frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1
                
                logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
        
        # Add the InterceptHandler to the standard library's root logger
        logging.getLogger().addHandler(InterceptHandler())
    
    def track_metric(self, name, value, properties=None):
        """Track a custom metric.
        
        Args:
            name: Metric name
            value: Metric value
            properties: Optional properties dictionary
        """
        if not self.enabled:
            return
            
        properties = properties or {}
        self.client.track_metric(name, value, properties=properties)
        
    def track_event(self, name, properties=None):
        """Track a custom event.
        
        Args:
            name: Event name
            properties: Optional properties dictionary
        """
        if not self.enabled:
            return
            
        properties = properties or {}
        self.client.track_event(name, properties=properties)
    
    def track_exception(self, exception, properties=None):
        """Track an exception.
        
        Args:
            exception: The exception object
            properties: Optional properties dictionary
        """
        if not self.enabled:
            return
            
        properties = properties or {}
        self.client.track_exception(type=type(exception), value=exception, properties=properties)
    
    def track_trace(self, message, severity=logging.INFO, properties=None):
        """Track a trace message.
        
        Args:
            message: The trace message
            severity: Severity level (from logging module)
            properties: Optional properties dictionary
        """
        if not self.enabled:
            return
            
        properties = properties or {}
        self.client.track_trace(message, severity=severity, properties=properties)
    
    def track_request(self, name, url, success, duration_ms, properties=None):
        """Track a request.
        
        Args:
            name: Request name
            url: Request URL
            success: Whether the request was successful
            duration_ms: Duration in milliseconds
            properties: Optional properties dictionary
        """
        if not self.enabled:
            return
            
        properties = properties or {}
        self.client.track_request(name, url, success, duration_ms, properties=properties)
    
    def track_dependency(self, name, data, type_name, target, success, duration_ms, properties=None):
        """Track a dependency call.
        
        Args:
            name: Dependency name
            data: Command or query executed
            type_name: Dependency type
            target: Dependency target
            success: Whether the dependency call was successful
            duration_ms: Duration in milliseconds
            properties: Optional properties dictionary
        """
        if not self.enabled:
            return
            
        properties = properties or {}
        self.client.track_dependency(name, data, type_name, target, success, duration_ms, properties=properties)
    
    def start_operation(self, name):
        """Start a new operation for tracking.
        
        This is a simplified version as the official SDK doesn't have full
        operation context support. For advanced scenarios, consider using
        OpenCensus.
        
        Args:
            name: Operation name
            
        Returns:
            A simple context manager for timing
        """
        if not self.enabled:
            from contextlib import nullcontext
            return nullcontext()
            
        class OperationContext:
            def __init__(self, client, name):
                self.client = client
                self.name = name
                self.properties = {'operation_name': name}
                self.start_time = None
                
            def __enter__(self):
                self.start_time = time.time()
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type:
                    self.client.track_exception(type=exc_type, value=exc_val, properties=self.properties)
                
                duration_ms = (time.time() - self.start_time) * 1000
                self.client.track_request(self.name, url="operation://crawler", 
                                          success=exc_type is None, 
                                          duration=duration_ms,
                                          properties=self.properties)
        
        return OperationContext(self.client, name)
    
    def flush(self):
        """Flush all telemetry in the buffer."""
        if not self.enabled:
            return
            
        self.client.flush()
    
    # Crawler-specific convenience methods
    
    def track_articles_discovered(self, count=1, source=None):
        """Track articles discovered metric.
        
        Args:
            count: Number of articles discovered
            source: Source name
        """
        props = {"source": source} if source else None
        self.track_metric("articles_discovered", count, props)
        self.track_event("articles_discovered", {
            "count": str(count),
            "source": source or "unknown"
        })
    
    def track_articles_processed(self, count=1, source=None, success=True):
        """Track articles processed metrics.
        
        Args:
            count: Number of articles processed
            source: Source name
            success: Whether processing was successful
        """
        props = {"source": source} if source else None
        
        if success:
            self.track_metric("articles_processed", count, props)
            self.track_event("articles_processed", {
                "count": str(count),
                "source": source or "unknown",
                "success": "true"
            })
        else:
            self.track_metric("articles_failed", count, props)
            self.track_event("articles_failed", {
                "count": str(count),
                "source": source or "unknown"
            })
    
    def track_duplicates_detected(self, count=1, source=None, duplicate_type=None):
        """Track duplicates detected metric.
        
        Args:
            count: Number of duplicates detected
            source: Source name
            duplicate_type: Type of duplication (e.g., "url", "title")
        """
        props = {}
        if source:
            props["source"] = source
        if duplicate_type:
            props["duplicate_type"] = duplicate_type
            
        self.track_metric("duplicates_detected", count, props or None)
        self.track_event("duplicates_detected", {
            "count": str(count),
            "source": source or "unknown",
            "type": duplicate_type or "unknown"
        })
    
    def track_documents_deleted(self, count, storage_type=None):
        """Track documents deleted metric.
        
        Args:
            count: Number of documents deleted
            storage_type: Storage type (e.g., "qdrant", "azure")
        """
        props = {"storage_type": storage_type} if storage_type else None
        self.track_metric("documents_deleted", count, props)
        self.track_event("documents_deleted", {
            "count": str(count),
            "storage_type": storage_type or "unknown"
        })
    
    def track_cycle_duration(self, duration_seconds):
        """Track cycle duration metric.
        
        Args:
            duration_seconds: Duration in seconds
        """
        self.track_metric("cycle_duration", duration_seconds)
    
    def track_deletion_duration(self, duration_seconds):
        """Track deletion duration metric.
        
        Args:
            duration_seconds: Duration in seconds
        """
        self.track_metric("deletion_duration", duration_seconds)
    
    def track_memory_usage(self, memory_mb):
        """Track memory usage metric.
        
        Args:
            memory_mb: Memory usage in MB
        """
        self.track_metric("memory_usage", memory_mb)
    
    def track_dependency_status(self, dependency_name, success, duration_ms=None, properties=None):
        """Track dependency status.
        
        Args:
            dependency_name: Name of the dependency
            success: Whether the dependency check was successful
            duration_ms: Optional duration in milliseconds
            properties: Optional additional properties
        """
        if not self.enabled:
            return
            
        props = properties or {}
        if duration_ms is None:
            duration_ms = 0
            
        # Track as both dependency and event for flexibility in querying
        self.track_dependency(
            name=dependency_name,
            data="check_connection", 
            type_name="dependency",
            target=dependency_name,
            success=success,
            duration_ms=duration_ms,
            properties=props
        )
        
        self.track_event("dependency_check", {
            "dependency_name": dependency_name,
            "success": "true" if success else "false",
            "duration_ms": str(duration_ms)
        })

# Global instance
_app_insights = None

def get_app_insights():
    """Get the singleton AppInsightsMonitoring instance.
    
    Returns:
        AppInsightsMonitoring instance
    """
    global _app_insights
    if _app_insights is None:
        _app_insights = AppInsightsMonitoring()
    return _app_insights