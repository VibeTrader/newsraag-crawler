"""
Duplicate detection utilities for NewsRagnarok Crawler.
"""
import hashlib
from typing import Dict, Any, Optional, Tuple
from loguru import logger
import redis
import os
from datetime import datetime, timedelta
import json

class DuplicateDetector:
    """Detects duplicate articles using various methods."""
    
    def __init__(self, cache_expiry_hours: int = 24):
        """Initialize the duplicate detector.
        
        Args:
            cache_expiry_hours: How long to keep URLs in cache (hours)
        """
        self.cache_expiry_seconds = cache_expiry_hours * 3600
        self.use_redis = os.environ.get('REDIS_URL') is not None
        
        # Use Redis if available, otherwise use in-memory cache
        if self.use_redis:
            try:
                redis_url = os.environ.get('REDIS_URL')
                self.redis = redis.from_url(redis_url)
                logger.info(f"DuplicateDetector using Redis cache at {redis_url}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.use_redis = False
                self.url_cache = {}
                self.title_cache = {}
        else:
            logger.info("DuplicateDetector using in-memory cache (Redis not configured)")
            self.url_cache = {}
            self.title_cache = {}
    
    def is_duplicate(self, article_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check if an article is a duplicate.
        
        Args:
            article_data: Article data including URL and title
            
        Returns:
            Tuple of (is_duplicate, duplicate_type)
        """
        url = article_data.get('url', '')
        title = article_data.get('title', '')
        
        if not url:
            return False, None
        
        # Check URL first (exact match)
        if self._is_url_duplicate(url):
            return True, "url"
        
        # Check title similarity (if title available)
        if title and self._is_title_duplicate(title):
            return True, "title"
        
        # Not a duplicate, add to cache
        self._add_to_cache(url, title)
        return False, None
    
    def _is_url_duplicate(self, url: str) -> bool:
        """Check if URL is in the cache."""
        if self.use_redis:
            return bool(self.redis.exists(f"url:{url}"))
        else:
            return url in self.url_cache
    
    def _is_title_duplicate(self, title: str) -> bool:
        """Check if title is similar to any in cache."""
        # Simple implementation: exact title match
        # Could be enhanced with fuzzy matching or embeddings
        title_key = self._normalize_title(title)
        
        if self.use_redis:
            return bool(self.redis.exists(f"title:{title_key}"))
        else:
            return title_key in self.title_cache
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        # Convert to lowercase and remove punctuation
        normalized = ''.join(c.lower() for c in title if c.isalnum() or c.isspace())
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        return normalized
    
    def _add_to_cache(self, url: str, title: str):
        """Add URL and title to cache."""
        if self.use_redis:
            # Add URL to Redis with expiry
            self.redis.setex(f"url:{url}", self.cache_expiry_seconds, "1")
            
            # Add normalized title to Redis with expiry
            if title:
                title_key = self._normalize_title(title)
                self.redis.setex(f"title:{title_key}", self.cache_expiry_seconds, "1")
        else:
            # Add to in-memory cache with expiry time
            expiry = datetime.now() + timedelta(seconds=self.cache_expiry_seconds)
            self.url_cache[url] = expiry
            
            if title:
                title_key = self._normalize_title(title)
                self.title_cache[title_key] = expiry
            
            # Clean expired entries periodically
            self._clean_expired_cache()
    
    def _clean_expired_cache(self):
        """Remove expired entries from in-memory cache."""
        if self.use_redis:
            return  # Redis handles expiry automatically
        
        now = datetime.now()
        
        # Clean URL cache
        expired_urls = [url for url, expiry in self.url_cache.items() if expiry < now]
        for url in expired_urls:
            del self.url_cache[url]
        
        # Clean title cache
        expired_titles = [title for title, expiry in self.title_cache.items() if expiry < now]
        for title in expired_titles:
            del self.title_cache[title]
        
        if expired_urls or expired_titles:
            logger.debug(f"Cleaned {len(expired_urls)} URLs and {len(expired_titles)} titles from cache")

# Global duplicate detector instance
_duplicate_detector = None

def get_duplicate_detector() -> DuplicateDetector:
    """Get the singleton duplicate detector instance.
    
    Returns:
        DuplicateDetector instance
    """
    global _duplicate_detector
    if _duplicate_detector is None:
        _duplicate_detector = DuplicateDetector()
    return _duplicate_detector