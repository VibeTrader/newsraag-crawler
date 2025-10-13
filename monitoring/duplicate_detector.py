"""
Simple LRU-based duplicate detection for NewsRagnarok Crawler.
Replaces both Redis and manual cleanup with efficient LRU cache.
"""
from functools import lru_cache
from typing import Dict, Any, Optional, Tuple
from loguru import logger
import os

class LRUDuplicateDetector:
    """Fast duplicate detector using Python's built-in LRU cache."""
    
    def __init__(self, max_urls: int = None):
        """
        Initialize LRU duplicate detector.
        
        Args:
            max_urls: Maximum URLs to remember (default: 50000)
        """
        self.max_urls = max_urls or int(os.getenv('URL_CACHE_SIZE', '50000'))
        
        # Use functools.lru_cache for maximum performance
        self._url_check = lru_cache(maxsize=self.max_urls)(self._mark_url_seen)
        
        # Statistics
        self.total_checks = 0
        self.duplicates_found = 0
        
        logger.info(f"LRU Duplicate Detector initialized (max URLs: {self.max_urls})")
    
    def _mark_url_seen(self, url: str) -> bool:
        """Internal cached function - if called, URL is now cached."""
        return True
    
    def is_duplicate(self, article_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Check if article URL is duplicate using LRU cache.
        
        Args:
            article_data: Article data containing 'url' field
            
        Returns:
            Tuple of (is_duplicate, duplicate_type)
        """
        url = article_data.get('url', '').strip()
        if not url:
            return False, None
        
        self.total_checks += 1
        
        # Get cache info before check
        cache_info = self._url_check.cache_info()
        old_hits = cache_info.hits
        
        # This call will hit cache if URL exists (duplicate), miss if new
        self._url_check(url)
        
        # Check if it was a cache hit (duplicate found)
        new_cache_info = self._url_check.cache_info()
        if new_cache_info.hits > old_hits:
            self.duplicates_found += 1
            logger.debug(f"Duplicate URL detected: {url[:100]}...")
            return True, "url"
        
        # New URL, automatically added to LRU cache
        return False, None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        cache_info = self._url_check.cache_info()
        hit_rate = (cache_info.hits / (cache_info.hits + cache_info.misses) * 100) if (cache_info.hits + cache_info.misses) > 0 else 0
        duplicate_rate = (self.duplicates_found / self.total_checks * 100) if self.total_checks > 0 else 0
        
        return {
            'cache_type': 'LRU',
            'cached_urls': cache_info.currsize,
            'max_cache_size': cache_info.maxsize,
            'cache_hits': cache_info.hits,
            'cache_misses': cache_info.misses,
            'hit_rate_percent': f"{hit_rate:.1f}%",
            'total_checks': self.total_checks,
            'duplicates_found': self.duplicates_found,
            'duplicate_rate_percent': f"{duplicate_rate:.1f}%",
            'memory_efficient': True,
            'redis_removed': True
        }
    
    def log_statistics(self) -> None:
        """Log current cache statistics."""
        stats = self.get_statistics()
        logger.info("🔍 LRU Duplicate Detector Statistics:")
        logger.info(f"  🔗 URLs cached: {stats['cached_urls']}/{stats['max_cache_size']}")
        logger.info(f"  🎯 Cache hit rate: {stats['hit_rate_percent']}")
        logger.info(f"  📊 Total checks: {stats['total_checks']}")
        logger.info(f"  ⏭️ Duplicates found: {stats['duplicates_found']} ({stats['duplicate_rate_percent']})")
        logger.info(f"  💾 Memory efficient: {stats['memory_efficient']}")
        logger.info(f"  🚫 Redis removed: {stats['redis_removed']}")
    
    def clear_cache(self) -> None:
        """Clear all cached URLs."""
        self._url_check.cache_clear()
        self.total_checks = 0
        self.duplicates_found = 0
        logger.info("LRU cache cleared")


# Global duplicate detector instance (backward compatibility)
_duplicate_detector = None

def get_duplicate_detector() -> LRUDuplicateDetector:
    """
    Get the singleton LRU duplicate detector instance.
    
    Returns:
        LRUDuplicateDetector instance
    """
    global _duplicate_detector
    if _duplicate_detector is None:
        _duplicate_detector = LRUDuplicateDetector()
    return _duplicate_detector

# Backward compatibility alias
DuplicateDetector = LRUDuplicateDetector
