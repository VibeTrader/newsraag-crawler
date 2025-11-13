"""
Persistent tracking of seen articles for fast duplicate detection.
Adapted from YoutubeRagnarok's seen_videos tracking pattern.
"""
from pathlib import Path
import json
from typing import Set, Optional
from loguru import logger
from datetime import datetime


class SeenArticleTracker:
    """
    Fast persistent tracking of seen articles using JSON file cache.
    
    This provides:
    - Fast duplicate detection without database queries
    - Offline capability (works even if Qdrant is down)
    - Persistent state across crawler restarts
    - Similar pattern to YoutubeRagnarok's seen_videos.json
    """
    
    def __init__(self, cache_file: str = 'data/seen_articles.json'):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.seen: Set[str] = self._load_cache()
        self.last_save = datetime.now()
        logger.info(f"📋 SeenArticleTracker initialized with {len(self.seen)} cached articles")
    
    def _load_cache(self) -> Set[str]:
        """Load seen article IDs from JSON file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"✅ Loaded {len(data)} seen articles from cache")
                    return set(data)
            except Exception as e:
                logger.error(f"❌ Failed to load seen articles cache: {e}")
                return set()
        
        logger.info("📝 No existing cache found, starting fresh")
        return set()
    
    def mark_seen(self, article_id: str) -> None:
        """Mark an article as seen."""
        self.seen.add(article_id)
    
    def is_seen(self, article_id: str) -> bool:
        """Check if article has been seen before."""
        return article_id in self.seen
    
    def save(self) -> bool:
        """Save seen articles to JSON file."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.seen), f, indent=2)
            
            self.last_save = datetime.now()
            logger.debug(f"💾 Saved {len(self.seen)} seen articles to cache")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save seen articles cache: {e}")
            return False
    
    def auto_save(self, interval_minutes: int = 5) -> bool:
        """
        Automatically save if enough time has passed since last save.
        
        Args:
            interval_minutes: Save interval in minutes
            
        Returns:
            True if save was triggered, False otherwise
        """
        minutes_since_save = (datetime.now() - self.last_save).total_seconds() / 60
        
        if minutes_since_save >= interval_minutes:
            return self.save()
        
        return False
    
    def get_stats(self) -> dict:
        """Get tracker statistics."""
        return {
            'total_seen': len(self.seen),
            'cache_file': str(self.cache_file),
            'last_save': self.last_save.isoformat(),
            'cache_exists': self.cache_file.exists()
        }
    
    def clear_cache(self) -> bool:
        """Clear all seen articles (use with caution!)."""
        try:
            self.seen.clear()
            if self.cache_file.exists():
                self.cache_file.unlink()
            logger.warning("⚠️ Cleared all seen articles cache")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to clear cache: {e}")
            return False
