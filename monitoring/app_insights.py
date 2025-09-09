"""
Azure Application Insights integration for NewsRagnarok Crawler.
"""
import os
import time
from datetime import datetime
from loguru import logger
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.metrics_exporter import AzureMetricsExporter
from opencensus.stats import aggregation as aggregation_module
from opencensus.stats import measure as measure_module
from opencensus.stats import stats as stats_module
from opencensus.stats import view as view_module
from opencensus.tags import tag_map as tag_map_module
from opencensus.trace import config_integration
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer
import logging

class AppInsightsMonitoring:
    """Azure Application Insights integration for monitoring."""
    
    def __init__(self, connection_string=None):
        """Initialize Application Insights monitoring.
        
        Args:
            connection_string: Application Insights connection string.
                If None, loads from APPLICATIONINSIGHTS_CONNECTION_STRING environment variable.
        """
        self.connection_string = connection_string or os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        self.instrumentation_key = os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY")
        
        if not self.connection_string and not self.instrumentation_key:
            logger.warning("Application Insights connection string or instrumentation key not set. Monitoring disabled.")
            self.enabled = False
            return
            
        self.enabled = True
        self.initialize_monitoring()
        logger.info("Azure Application Insights monitoring initialized.")
    
    def initialize_monitoring(self):
        """Initialize all monitoring components."""
        # Configure logging integration
        self._configure_logging()
        
        # Configure metrics
        self._configure_metrics()
        
        # Configure distributed tracing
        self._configure_tracing()
        
        # Set up tag map
        self.tag_map = tag_map_module.TagMap()
        self.tag_map.insert("service", "newsraag-crawler")
    
    def _configure_logging(self):
        """Configure logging integration with Application Insights."""
        # Add Azure Log Handler to Python logging
        if self.connection_string:
            handler = AzureLogHandler(connection_string=self.connection_string)
        else:
            handler = AzureLogHandler(instrumentation_key=self.instrumentation_key)
            
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
    
    def _configure_metrics(self):
        """Configure metrics integration with Application Insights."""
        if self.connection_string:
            self.metrics_exporter = AzureMetricsExporter(connection_string=self.connection_string)
        else:
            self.metrics_exporter = AzureMetricsExporter(instrumentation_key=self.instrumentation_key)
            
        self.stats = stats_module.stats
        
        # Define measures
        self.measure_articles_discovered = measure_module.MeasureInt(
            "articles_discovered", "Number of articles discovered from sources", "articles")
        self.measure_articles_processed = measure_module.MeasureInt(
            "articles_processed", "Number of articles successfully processed", "articles")
        self.measure_articles_failed = measure_module.MeasureInt(
            "articles_failed", "Number of articles that failed processing", "articles")
        self.measure_duplicates_detected = measure_module.MeasureInt(
            "duplicates_detected", "Number of duplicate articles detected", "articles")
        self.measure_documents_deleted = measure_module.MeasureInt(
            "documents_deleted", "Number of documents deleted during cleanup", "documents")
        self.measure_cycle_duration = measure_module.MeasureFloat(
            "cycle_duration", "Duration of crawl cycle in seconds", "s")
        self.measure_deletion_duration = measure_module.MeasureFloat(
            "deletion_duration", "Duration of deletion process in seconds", "s")
        self.measure_memory_usage = measure_module.MeasureFloat(
            "memory_usage", "Memory usage in MB", "MB")
        
        # Define views for each measure
        articles_discovered_view = view_module.View(
            "articles_discovered", "Number of articles discovered from sources",
            [], self.measure_articles_discovered, aggregation_module.SumAggregation())
        articles_processed_view = view_module.View(
            "articles_processed", "Number of articles successfully processed",
            [], self.measure_articles_processed, aggregation_module.SumAggregation())
        articles_failed_view = view_module.View(
            "articles_failed", "Number of articles that failed processing",
            [], self.measure_articles_failed, aggregation_module.SumAggregation())
        duplicates_detected_view = view_module.View(
            "duplicates_detected", "Number of duplicate articles detected",
            [], self.measure_duplicates_detected, aggregation_module.SumAggregation())
        documents_deleted_view = view_module.View(
            "documents_deleted", "Number of documents deleted during cleanup",
            [], self.measure_documents_deleted, aggregation_module.SumAggregation())
        cycle_duration_view = view_module.View(
            "cycle_duration", "Duration of crawl cycle in seconds",
            [], self.measure_cycle_duration, aggregation_module.LastValueAggregation())
        deletion_duration_view = view_module.View(
            "deletion_duration", "Duration of deletion process in seconds",
            [], self.measure_deletion_duration, aggregation_module.LastValueAggregation())
        memory_usage_view = view_module.View(
            "memory_usage", "Memory usage in MB",
            [], self.measure_memory_usage, aggregation_module.LastValueAggregation())
        
        # Register views
        self.stats.view_manager.register_view(articles_discovered_view)
        self.stats.view_manager.register_view(articles_processed_view)
        self.stats.view_manager.register_view(articles_failed_view)
        self.stats.view_manager.register_view(duplicates_detected_view)
        self.stats.view_manager.register_view(documents_deleted_view)
        self.stats.view_manager.register_view(cycle_duration_view)
        self.stats.view_manager.register_view(deletion_duration_view)
        self.stats.view_manager.register_view(memory_usage_view)
        
        # Register exporter
        self.stats.view_manager.register_exporter(self.metrics_exporter)
    
    def _configure_tracing(self):
        """Configure distributed tracing with Application Insights."""
        # Set up the exporter
        if self.connection_string:
            self.exporter = AzureExporter(connection_string=self.connection_string)
        else:
            self.exporter = AzureExporter(instrumentation_key=self.instrumentation_key)
            
        # Configure the sampler - 100% of traces collected
        self.sampler = ProbabilitySampler(1.0)
        
        # Create a tracer
        self.tracer = Tracer(exporter=self.exporter, sampler=self.sampler)
        
        # Configure integration with popular packages
        config_integration.trace_integrations(['requests'])
    
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
        
        # Convert metric name to measure if available
        if hasattr(self, f"measure_{name}"):
            measure = getattr(self, f"measure_{name}")
            mmap = self.stats.stats_recorder.new_measurement_map()
            mmap.measure_int_put(measure, int(value) if isinstance(measure, measure_module.MeasureInt) else value)
            mmap.record(self.tag_map)
        else:
            # Use logging if no specific measure exists
            properties["metric_name"] = name
            properties["metric_value"] = value
            logging.getLogger().info(f"Custom metric: {name}={value}", extra={"custom_dimensions": properties})
    
    def track_event(self, name, properties=None):
        """Track a custom event.
        
        Args:
            name: Event name
            properties: Optional properties dictionary
        """
        if not self.enabled:
            return
            
        properties = properties or {}
        logging.getLogger().info(f"Event: {name}", extra={"custom_dimensions": properties})
    
    def track_exception(self, exception, properties=None):
        """Track an exception.
        
        Args:
            exception: The exception object
            properties: Optional properties dictionary
        """
        if not self.enabled:
            return
            
        properties = properties or {}
        logging.getLogger().exception(f"Exception: {str(exception)}", extra={"custom_dimensions": properties})
    
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
        logging.getLogger().log(severity, message, extra={"custom_dimensions": properties})
    
    def start_operation(self, name):
        """Start a new operation for distributed tracing.
        
        Args:
            name: Operation name
            
        Returns:
            Span context manager
        """
        if not self.enabled:
            return None
            
        return self.tracer.span(name)
    
    def track_articles_discovered(self, count=1, source=None):
        """Track articles discovered metric.
        
        Args:
            count: Number of articles discovered
            source: Source name
        """
        self.track_metric("articles_discovered", count, {"source": source} if source else None)
    
    def track_articles_processed(self, count=1, source=None, success=True):
        """Track articles processed metrics.
        
        Args:
            count: Number of articles processed
            source: Source name
            success: Whether processing was successful
        """
        if success:
            self.track_metric("articles_processed", count, {"source": source} if source else None)
        else:
            self.track_metric("articles_failed", count, {"source": source} if source else None)
    
    def track_duplicates_detected(self, count=1, source=None, duplicate_type=None):
        """Track duplicates detected metric.
        
        Args:
            count: Number of duplicates detected
            source: Source name
            duplicate_type: Type of duplication (e.g., "url", "title")
        """
        properties = {}
        if source:
            properties["source"] = source
        if duplicate_type:
            properties["duplicate_type"] = duplicate_type
            
        self.track_metric("duplicates_detected", count, properties or None)
    
    def track_documents_deleted(self, count, storage_type=None):
        """Track documents deleted metric.
        
        Args:
            count: Number of documents deleted
            storage_type: Storage type (e.g., "qdrant", "azure")
        """
        self.track_metric("documents_deleted", count, {"storage_type": storage_type} if storage_type else None)
    
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
        props["dependency_name"] = dependency_name
        props["success"] = "true" if success else "false"
        if duration_ms is not None:
            props["duration_ms"] = str(duration_ms)
            
        self.track_event("dependency_check", props)

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