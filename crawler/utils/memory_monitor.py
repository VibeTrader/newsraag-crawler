"""
Memory monitoring utilities for NewsRagnarok Crawler.
"""
import os
import psutil
from loguru import logger

from monitoring.metrics import get_metrics

def log_memory_usage():
    """
    Log current memory usage and record metrics.
    """
    try:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        rss_mb = mem_info.rss / 1024 / 1024
        virtual_mb = process.memory_info().vms / 1024 / 1024
        
        # Log to console
        logger.info(f"Memory usage: {rss_mb:.2f} MB (RSS), {virtual_mb:.2f} MB (Virtual)")
        
        # Record in metrics
        metrics = get_metrics()
        metrics.record_memory_usage(rss_mb, virtual_mb)
        
        return {
            "rss_mb": rss_mb,
            "virtual_mb": virtual_mb
        }
    except Exception as e:
        logger.error(f"Error monitoring memory usage: {e}")
        return None
