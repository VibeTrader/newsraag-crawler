"""
Integration utilities for SeenArticleTracker with the main crawler system.
"""
from typing import Dict, Any
from loguru import logger
from crawler.utils.seen_tracker import SeenArticleTracker


class TrackerIntegration:
    """Helper class to integrate SeenArticleTracker with existing duplicate detection."""
    
    def __init__(self, seen_tracker: SeenArticleTracker):
        self.seen_tracker = seen_tracker
        self.stats = {
            'fast_skips': 0,  # Articles skipped via cache
            'db_checks': 0,   # Articles that passed cache but needed DB check
            'cache_saves': 0  # Number of times cache was saved
        }
    
    def is_seen_fast(self, article_id: str) -> bool:
        """
        Fast duplicate check using local cache.
        
        Returns:
            True if definitely seen (fast skip), False if needs full check
        """
        if self.seen_tracker.is_seen(article_id):
            self.stats['fast_skips'] += 1
            logger.debug(f"⚡ Fast skip (cached): {article_id}")
            return True
        
        self.stats['db_checks'] += 1
        return False
    
    def mark_processed(self, article_id: str):
        """Mark article as processed and save to cache."""
        self.seen_tracker.mark_seen(article_id)
    
    def auto_save_cache(self) -> bool:
        """Auto-save cache every 5 minutes."""
        if self.seen_tracker.auto_save(interval_minutes=5):
            self.stats['cache_saves'] += 1
            logger.info(f"💾 Auto-saved seen articles cache ({len(self.seen_tracker.seen)} total)")
            return True
        return False
    
    def force_save_cache(self):
        """Force save the cache now."""
        if self.seen_tracker.save():
            self.stats['cache_saves'] += 1
            logger.info(f"💾 Force-saved seen articles cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            **self.stats,
            'total_cached': len(self.seen_tracker.seen),
            'cache_file': str(self.seen_tracker.cache_file)
        }
    
    def log_stats(self):
        """Log current statistics."""
        stats = self.get_stats()
        logger.info(f"📊 SeenTracker Stats: {stats['fast_skips']} fast skips, "
                   f"{stats['db_checks']} DB checks, {stats['total_cached']} cached")


# Global instance (initialized in main.py)
_tracker_integration = None


def init_tracker_integration(seen_tracker: SeenArticleTracker):
    """Initialize the global tracker integration."""
    global _tracker_integration
    _tracker_integration = TrackerIntegration(seen_tracker)
    return _tracker_integration


def get_tracker_integration() -> TrackerIntegration:
    """Get the global tracker integration instance."""
    return _tracker_integration
