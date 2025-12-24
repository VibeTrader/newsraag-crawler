"""
Memory optimization utilities for NewsRagnarok Crawler.
Provides intelligent memory management without disrupting operations.
"""
import gc
import os
import psutil
import threading
import time
from typing import Dict, Any, Optional, Callable, List
from loguru import logger
from datetime import datetime, timedelta
from collections import deque
import weakref
import sys

class MemoryOptimizer:
    """
    Intelligent memory optimizer that monitors and manages memory usage
    without disrupting crawler operations.
    """
    
    def __init__(self, 
                 memory_threshold_mb: int = 400,
                 aggressive_threshold_mb: int = 600,
                 check_interval_seconds: int = 30):
        """
        Initialize memory optimizer.
        
        Args:
            memory_threshold_mb: Soft memory limit for optimizations (MB)
            aggressive_threshold_mb: Hard limit for aggressive cleanup (MB)
            check_interval_seconds: How often to check memory usage
        """
        self.memory_threshold = memory_threshold_mb * 1024 * 1024
        self.aggressive_threshold = aggressive_threshold_mb * 1024 * 1024
        self.check_interval = check_interval_seconds
        
        # Memory tracking
        self.last_check = datetime.now()
        self.memory_history = deque(maxlen=20)  # Keep last 20 readings
        self.cleanup_count = 0
        self.aggressive_cleanup_count = 0
        
        # Cleanup callbacks for different components
        self.cleanup_callbacks = []
        
        # Thread for background monitoring
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()
        
        logger.info(f"Memory optimizer initialized: {memory_threshold_mb}MB soft, "
                   f"{aggressive_threshold_mb}MB hard limits")
    
    def register_cleanup_callback(self, callback: Callable, name: str, priority: int = 1):
        """
        Register a cleanup callback for memory optimization.
        
        Args:
            callback: Function to call for cleanup
            name: Name of the cleanup operation
            priority: Priority (1=high, 2=medium, 3=low)
        """
        self.cleanup_callbacks.append({
            'callback': callback,
            'name': name,
            'priority': priority
        })
        
        # Sort by priority
        self.cleanup_callbacks.sort(key=lambda x: x['priority'])
        logger.info(f"Registered cleanup callback: {name} (priority {priority})")
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get detailed memory information."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            # System memory info
            system_memory = psutil.virtual_memory()
            
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'process_percent': memory_percent,
                'system_available_mb': system_memory.available / 1024 / 1024,
                'system_used_percent': system_memory.percent,
                'is_over_threshold': memory_info.rss > self.memory_threshold,
                'is_critical': memory_info.rss > self.aggressive_threshold
            }
        except Exception as e:
            logger.warning(f"Failed to get memory info: {e}")
            return {'error': str(e)}
    
    def should_optimize(self) -> tuple[bool, str]:
        """Check if memory optimization is needed."""
        memory_info = self.get_memory_info()
        
        if 'error' in memory_info:
            return False, "Memory info unavailable"
        
        current_mb = memory_info['rss_mb']
        self.memory_history.append(current_mb)
        
        # Check if over threshold
        if memory_info['is_critical']:
            return True, "critical"
        elif memory_info['is_over_threshold']:
            return True, "soft"
        
        # Check if memory is growing rapidly
        if len(self.memory_history) >= 5:
            recent_avg = sum(list(self.memory_history)[-5:]) / 5
            older_avg = sum(list(self.memory_history)[-10:-5]) / 5 if len(self.memory_history) >= 10 else recent_avg
            
            growth_rate = (recent_avg - older_avg) / older_avg if older_avg > 0 else 0
            if growth_rate > 0.2:  # 20% growth
                return True, "rapid_growth"
        
        return False, "normal"
    
    def optimize_memory(self, level: str = "soft") -> Dict[str, Any]:
        """
        Perform memory optimization based on level.
        
        Args:
            level: "soft", "critical", or "rapid_growth"
        
        Returns:
            Results of optimization
        """
        start_time = time.time()
        memory_before = self.get_memory_info()
        
        logger.info(f"Starting {level} memory optimization...")
        logger.info(f"Memory before: {memory_before['rss_mb']:.2f} MB")
        
        results = {
            'level': level,
            'memory_before_mb': memory_before['rss_mb'],
            'cleanup_results': []
        }
        
        # Determine which cleanups to run based on level
        if level == "critical":
            max_priority = 3  # Run all cleanups
            self.aggressive_cleanup_count += 1
        elif level == "rapid_growth":
            max_priority = 2  # Run high and medium priority
        else:  # soft
            max_priority = 1  # Run only high priority
            
        self.cleanup_count += 1
        
        # Run cleanup callbacks
        for cleanup in self.cleanup_callbacks:
            if cleanup['priority'] <= max_priority:
                try:
                    start_cleanup = time.time()
                    cleanup['callback']()
                    cleanup_time = time.time() - start_cleanup
                    
                    results['cleanup_results'].append({
                        'name': cleanup['name'],
                        'priority': cleanup['priority'],
                        'duration': cleanup_time,
                        'success': True
                    })
                    
                    logger.info(f"Completed cleanup: {cleanup['name']} ({cleanup_time:.3f}s)")
                    
                except Exception as e:
                    logger.error(f"Cleanup failed: {cleanup['name']} - {e}")
                    results['cleanup_results'].append({
                        'name': cleanup['name'],
                        'priority': cleanup['priority'],
                        'error': str(e),
                        'success': False
                    })
        
        # Force garbage collection
        logger.info("Forcing garbage collection...")
        collected = gc.collect()
        logger.info(f"Garbage collection freed {collected} objects")
        
        # Get memory after optimization
        memory_after = self.get_memory_info()
        optimization_time = time.time() - start_time
        
        results.update({
            'memory_after_mb': memory_after['rss_mb'],
            'memory_saved_mb': memory_before['rss_mb'] - memory_after['rss_mb'],
            'optimization_time': optimization_time,
            'gc_objects_freed': collected
        })
        
        logger.info(f"Memory optimization completed in {optimization_time:.3f}s")
        logger.info(f"Memory after: {memory_after['rss_mb']:.2f} MB "
                   f"(saved {results['memory_saved_mb']:.2f} MB)")
        
        return results
    
    def start_background_monitoring(self):
        """Start background memory monitoring thread."""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("Background monitoring already running")
            return
        
        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(
            target=self._background_monitor,
            name="MemoryOptimizer",
            daemon=True
        )
        self.monitoring_thread.start()
        logger.info("Background memory monitoring started")
    
    def stop_background_monitoring(self):
        """Stop background memory monitoring."""
        if self.monitoring_thread:
            self.stop_monitoring.set()
            self.monitoring_thread.join(timeout=5)
            logger.info("Background memory monitoring stopped")
    
    def _background_monitor(self):
        """Background monitoring loop."""
        while not self.stop_monitoring.wait(self.check_interval):
            try:
                should_optimize, level = self.should_optimize()
                if should_optimize:
                    logger.info(f"Background memory optimization triggered: {level}")
                    self.optimize_memory(level)
                    
            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory optimizer statistics."""
        memory_info = self.get_memory_info()
        
        return {
            'current_memory_mb': memory_info.get('rss_mb', 0),
            'memory_threshold_mb': self.memory_threshold / 1024 / 1024,
            'aggressive_threshold_mb': self.aggressive_threshold / 1024 / 1024,
            'cleanup_count': self.cleanup_count,
            'aggressive_cleanup_count': self.aggressive_cleanup_count,
            'registered_callbacks': len(self.cleanup_callbacks),
            'memory_history': list(self.memory_history)
        }


class ContentSizeOptimizer:
    """Optimize content sizes to reduce memory usage."""
    
    @staticmethod
    def truncate_content(content: str, max_size: int = 50000) -> str:
        """Truncate content to maximum size."""
        if not content or len(content) <= max_size:
            return content
        
        # Try to truncate at sentence boundary
        truncated = content[:max_size]
        last_period = truncated.rfind('.')
        if last_period > max_size * 0.8:  # If we can save 20% of content
            truncated = truncated[:last_period + 1]
        
        return truncated + "\n\n[Content truncated for memory optimization]"
    
    @staticmethod
    def compress_article_data(article_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress article data by removing/truncating large fields."""
        if not isinstance(article_data, dict):
            return article_data
        
        optimized = article_data.copy()
        
        # Truncate large text fields
        text_fields = ['content', 'raw_content', 'description', 'summary']
        for field in text_fields:
            if field in optimized and isinstance(optimized[field], str):
                if len(optimized[field]) > 50000:
                    optimized[field] = ContentSizeOptimizer.truncate_content(
                        optimized[field], 50000
                    )
        
        # Remove unnecessary fields
        unnecessary_fields = ['raw_html', 'debug_info', 'full_response']
        for field in unnecessary_fields:
            optimized.pop(field, None)
        
        return optimized


# Global memory optimizer instance
_memory_optimizer = None

def get_memory_optimizer() -> MemoryOptimizer:
    """Get global memory optimizer instance."""
    global _memory_optimizer
    if _memory_optimizer is None:
        # Get configuration from environment
        threshold_mb = int(os.getenv('MEMORY_THRESHOLD_MB', '400'))
        aggressive_mb = int(os.getenv('MEMORY_AGGRESSIVE_MB', '600'))
        check_interval = int(os.getenv('MEMORY_CHECK_INTERVAL', '30'))
        
        _memory_optimizer = MemoryOptimizer(threshold_mb, aggressive_mb, check_interval)
    
    return _memory_optimizer


def setup_crawler_memory_optimization():
    """Setup memory optimization for the crawler with default cleanup callbacks."""
    optimizer = get_memory_optimizer()
    
    # Register cleanup callbacks for different components
    
    # High priority cleanups (always run)
    def cleanup_duplicate_detector():
        """Clear duplicate detector cache."""
        try:
            from monitoring.duplicate_detector import get_duplicate_detector
            detector = get_duplicate_detector()
            if hasattr(detector, 'clear_cache'):
                detector.clear_cache()
                logger.info("Cleared duplicate detector cache")
        except Exception as e:
            logger.warning(f"Failed to clear duplicate detector: {e}")
    
    def cleanup_gc_aggressive():
        """Aggressive garbage collection."""
        # Set more aggressive GC thresholds temporarily
        old_thresholds = gc.get_threshold()
        gc.set_threshold(50, 5, 5)
        collected = gc.collect()
        gc.set_threshold(*old_thresholds)
        logger.info(f"Aggressive GC collected {collected} objects")
    
    # Medium priority cleanups
    def cleanup_import_cache():
        """Clear Python import cache."""
        try:
            # Clear module cache for non-essential modules
            modules_to_remove = []
            for module_name in sys.modules:
                if any(skip in module_name for skip in ['test', 'debug', 'unused']):
                    modules_to_remove.append(module_name)
            
            for module_name in modules_to_remove:
                del sys.modules[module_name]
            
            if modules_to_remove:
                logger.info(f"Removed {len(modules_to_remove)} cached modules")
        except Exception as e:
            logger.warning(f"Failed to clear import cache: {e}")
    
    # Low priority cleanups (only during critical situations)
    def cleanup_logger_handlers():
        """Optimize logger memory usage."""
        try:
            # This is a placeholder - loguru handles its own memory
            logger.info("Logger memory optimization completed")
        except Exception as e:
            logger.warning(f"Failed to optimize logger: {e}")
    
    # Register all cleanup callbacks
    optimizer.register_cleanup_callback(cleanup_duplicate_detector, "duplicate_detector", 1)
    optimizer.register_cleanup_callback(cleanup_gc_aggressive, "aggressive_gc", 1)
    optimizer.register_cleanup_callback(cleanup_import_cache, "import_cache", 2)
    optimizer.register_cleanup_callback(cleanup_logger_handlers, "logger_optimization", 3)
    
    # Start background monitoring
    optimizer.start_background_monitoring()
    
    logger.info("Crawler memory optimization setup completed")
    return optimizer
