"""
Integration helpers for adding Crawler Cycle Monitor to existing crawler.

This module provides easy integration functions to add cycle monitoring
to your existing crawler without major code changes.
"""
from loguru import logger
from crawler_cycle_monitor import (
    start_crawler_monitoring, 
    record_crawler_activity, 
    stop_crawler_monitoring,
    get_crawler_status
)


def initialize_crawler_monitoring():
    """
    Initialize crawler cycle monitoring.
    Call this once when your application starts.
    """
    try:
        start_crawler_monitoring()
        logger.info("✅ Crawler cycle monitoring initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize crawler monitoring: {e}")
        return False


def track_crawl_cycle_start(source_name: str = None, **kwargs):
    """
    Track the start of a crawl cycle.
    Call this when your crawler begins a new cycle.
    
    Args:
        source_name: Name of source being crawled
        **kwargs: Additional details to track
    """
    try:
        details = {
            "phase": "cycle_start",
            "source": source_name,
            **kwargs
        }
        record_crawler_activity("crawl_cycle_start", **details)
        logger.debug(f"🔄 Tracked crawl cycle start: {source_name}")
    except Exception as e:
        logger.error(f"Failed to track crawl cycle start: {e}")


def track_rss_fetch(source_name: str, article_count: int = 0, **kwargs):
    """
    Track RSS feed fetching activity.
    
    Args:
        source_name: Name of RSS source
        article_count: Number of articles fetched
        **kwargs: Additional details
    """
    try:
        details = {
            "phase": "rss_fetch",
            "source": source_name,
            "article_count": article_count,
            **kwargs
        }
        record_crawler_activity("rss_fetch", **details)
        logger.debug(f"📡 Tracked RSS fetch: {source_name} ({article_count} articles)")
    except Exception as e:
        logger.error(f"Failed to track RSS fetch: {e}")


def track_article_processing(source_name: str, processed_count: int = 0, failed_count: int = 0, **kwargs):
    """
    Track article processing activity.
    
    Args:
        source_name: Name of source
        processed_count: Number of articles processed successfully
        failed_count: Number of articles that failed processing
        **kwargs: Additional details
    """
    try:
        details = {
            "phase": "article_processing",
            "source": source_name,
            "processed_count": processed_count,
            "failed_count": failed_count,
            "total_articles": processed_count + failed_count,
            **kwargs
        }
        record_crawler_activity("article_processing", **details)
        logger.debug(f"📝 Tracked article processing: {source_name} ({processed_count} processed, {failed_count} failed)")
    except Exception as e:
        logger.error(f"Failed to track article processing: {e}")


def track_crawl_cycle_complete(total_sources: int = 0, total_articles: int = 0, duration_seconds: float = 0, **kwargs):
    """
    Track completion of a full crawl cycle.
    
    Args:
        total_sources: Number of sources crawled
        total_articles: Total articles processed
        duration_seconds: Time taken for the cycle
        **kwargs: Additional details
    """
    try:
        details = {
            "phase": "cycle_complete",
            "total_sources": total_sources,
            "total_articles": total_articles,
            "duration_seconds": duration_seconds,
            **kwargs
        }
        record_crawler_activity("crawl_cycle_complete", **details)
        logger.info(f"✅ Tracked crawl cycle complete: {total_sources} sources, {total_articles} articles in {duration_seconds:.1f}s")
    except Exception as e:
        logger.error(f"Failed to track crawl cycle complete: {e}")


def track_error(error_type: str, error_message: str, source_name: str = None, **kwargs):
    """
    Track errors during crawling (still counts as activity).
    
    Args:
        error_type: Type of error
        error_message: Error message
        source_name: Source where error occurred
        **kwargs: Additional details
    """
    try:
        details = {
            "phase": "error",
            "error_type": error_type,
            "error_message": error_message,
            "source": source_name,
            **kwargs
        }
        record_crawler_activity("crawler_error", **details)
        logger.debug(f"⚠️ Tracked crawler error: {error_type} on {source_name}")
    except Exception as e:
        logger.error(f"Failed to track crawler error: {e}")


def shutdown_crawler_monitoring():
    """
    Shutdown crawler cycle monitoring.
    Call this when your application is shutting down.
    """
    try:
        stop_crawler_monitoring()
        logger.info("🛑 Crawler cycle monitoring shutdown")
    except Exception as e:
        logger.error(f"Failed to shutdown crawler monitoring: {e}")


# Context manager for easy crawl cycle tracking
class CrawlCycleTracker:
    """
    Context manager to automatically track crawl cycles.
    
    Usage:
        with CrawlCycleTracker() as tracker:
            # Your crawl logic here
            tracker.track_source("example.com", articles=10)
    """
    
    def __init__(self):
        self.start_time = None
        self.total_sources = 0
        self.total_articles = 0
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        track_crawl_cycle_start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time if self.start_time else 0
        
        if exc_type:
            # Error occurred during crawl cycle
            track_error(
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                duration_seconds=duration
            )
        else:
            # Successful completion
            track_crawl_cycle_complete(
                total_sources=self.total_sources,
                total_articles=self.total_articles,
                duration_seconds=duration
            )
    
    def track_source(self, source_name: str, articles: int = 0, **kwargs):
        """Track processing of a source within the cycle."""
        self.total_sources += 1
        self.total_articles += articles
        track_rss_fetch(source_name, articles, **kwargs)


# Example integration patterns for existing code
def integrate_with_existing_crawler():
    """
    Example of how to integrate with existing crawler code.
    
    Add these calls to your existing crawler:
    """
    example_integration = """
    # At application startup:
    from crawler_integration import initialize_crawler_monitoring
    initialize_crawler_monitoring()
    
    # At the beginning of each crawl cycle:
    from crawler_integration import track_crawl_cycle_start
    track_crawl_cycle_start()
    
    # When fetching RSS feeds:
    from crawler_integration import track_rss_fetch
    track_rss_fetch(source_name="example.com", article_count=15)
    
    # When processing articles:
    from crawler_integration import track_article_processing
    track_article_processing("example.com", processed_count=12, failed_count=3)
    
    # At the end of crawl cycle:
    from crawler_integration import track_crawl_cycle_complete
    track_crawl_cycle_complete(total_sources=5, total_articles=50, duration_seconds=120.5)
    
    # When errors occur:
    from crawler_integration import track_error
    track_error("ConnectionError", "Failed to connect to RSS feed", "example.com")
    
    # Or use the context manager approach:
    from crawler_integration import CrawlCycleTracker
    with CrawlCycleTracker() as tracker:
        # Your crawl logic
        for source in sources:
            articles = fetch_rss(source)
            tracker.track_source(source.name, len(articles))
    """
    
    logger.info("Integration example:")
    print(example_integration)


if __name__ == "__main__":
    integrate_with_existing_crawler()
