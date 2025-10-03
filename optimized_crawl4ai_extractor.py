#!/usr/bin/env python3
"""
Optimized Crawl4AI extractor with browser session pooling.
Industry-standard implementation for production web scraping.
"""
import asyncio
from typing import Optional, Dict, Any
from loguru import logger
from crawl4ai import CrawlerRunConfig, CacheMode
from crawler.interfaces import ArticleMetadata, SourceConfig
from datetime import datetime
import time

# Import our browser session pool
from browser_session_pool import browser_session, get_browser_pool, start_browser_pool

class OptimizedCrawl4AIExtractor:
    """
    Production-ready Crawl4AI extractor with session pooling.
    Solves the "one browser per article" problem.
    """
    
    def __init__(self, config: SourceConfig):
        self.config = config
        
        # Start browser pool if not already started
        try:
            start_browser_pool()
        except:
            pass  # Already started
        
        # Source-specific configurations
        self.timeouts = self._get_progressive_timeouts()
        self.max_retries = 3
        
        logger.info(f"Optimized extractor initialized for {config.name}")
    
    def _get_progressive_timeouts(self) -> list:
        """Get progressive timeout values based on source type."""
        base_timeout = getattr(self.config, 'timeout_seconds', 30)
        
        # Progressive timeouts for retries
        return [
            base_timeout,
            base_timeout * 2,
            base_timeout * 3
        ]
    
    async def extract_content(self, article_meta: ArticleMetadata) -> Dict[str, Any]:
        """
        Extract content using shared browser session.
        This is the key method that prevents browser proliferation.
        """
        start_time = time.time()
        
        # Use shared browser session
        async with browser_session(self.config.name) as crawler:
            for attempt in range(self.max_retries):
                try:
                    timeout = self.timeouts[attempt]
                    
                    logger.debug(
                        f"Extracting {article_meta.url} "
                        f"(attempt {attempt + 1}, timeout {timeout}s) "
                        f"using shared session"
                    )
                    
                    result = await self._extract_with_timeout(
                        crawler, article_meta, timeout
                    )
                    
                    if result["success"]:
                        duration = time.time() - start_time
                        logger.debug(
                            f"Successfully extracted {article_meta.url} "
                            f"in {duration:.2f}s using shared session"
                        )
                        return result
                    
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Timeout after {timeout}s for {article_meta.url} "
                        f"(attempt {attempt + 1})"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"Error extracting {article_meta.url} "
                        f"(attempt {attempt + 1}): {e}"
                    )
                
                # Small delay between retries
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2)
        
        # All attempts failed
        logger.error(f"Failed to extract {article_meta.url} after all attempts")
        return {
            "success": False,
            "error": "All extraction attempts failed"
        }
    
    async def _extract_with_timeout(
        self, 
        crawler, 
        article_meta: ArticleMetadata, 
        timeout: int
    ) -> Dict[str, Any]:
        """Extract content with timeout using shared crawler."""
        
        # Configure crawler for this request
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=timeout * 1000,  # Convert to milliseconds
            wait_for_images=False,
            screenshot=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
            }
        )
        
        # Add source-specific headers if configured
        if hasattr(self.config, 'headers') and self.config.headers:
            run_config.headers.update(self.config.headers)
        
        # Extract with timeout
        result = await asyncio.wait_for(
            crawler.arun(url=article_meta.url, config=run_config),
            timeout=timeout
        )
        
        if result.success and result.extracted_content:
            return {
                "success": True,
                "content": result.extracted_content,
                "title": result.metadata.get("title", article_meta.title),
                "extraction_method": "crawl4ai_pooled",
                "session_reused": True  # Indicate session was reused
            }
        else:
            return {
                "success": False,
                "error": f"Extraction failed: {result.error_message}"
            }
    
    async def health_check(self) -> bool:
        """Check if the extractor and browser pool are healthy."""
        try:
            pool = get_browser_pool()
            stats = pool.get_stats()
            
            logger.debug(f"Browser pool stats for {self.config.name}: {stats}")
            
            # Basic health check - can we get a session?
            async with browser_session(self.config.name) as crawler:
                return crawler is not None
                
        except Exception as e:
            logger.error(f"Health check failed for {self.config.name}: {e}")
            return False
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get browser session statistics."""
        pool = get_browser_pool()
        return pool.get_stats()

# Convenience function for backward compatibility
async def extract_with_pooled_browser(
    url: str, 
    source_name: str, 
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Extract content using the browser pool.
    Convenience function for quick extractions.
    """
    # Create minimal article metadata
    article_meta = ArticleMetadata(
        title="Quick Extract",
        url=url,
        published_date=datetime.now(),
        source=source_name
    )
    
    # Create minimal config
    from crawler.interfaces import SourceConfig, SourceType, ContentType
    config = SourceConfig(
        name=source_name,
        source_type=SourceType.RSS,
        content_type=ContentType.FOREX,
        base_url="",
        timeout_seconds=timeout
    )
    
    extractor = OptimizedCrawl4AIExtractor(config)
    return await extractor.extract_content(article_meta)

# Example usage
async def example_usage():
    """Example of how to use the optimized extractor."""
    from crawler.interfaces import SourceConfig, SourceType, ContentType
    
    # Create config
    config = SourceConfig(
        name="example_source",
        source_type=SourceType.RSS,
        content_type=ContentType.FOREX,
        base_url="https://example.com",
        timeout_seconds=30
    )
    
    # Create extractor
    extractor = OptimizedCrawl4AIExtractor(config)
    
    # Extract multiple articles - all will reuse the same browser session
    urls = [
        "https://example.com/article1",
        "https://example.com/article2", 
        "https://example.com/article3"
    ]
    
    for url in urls:
        article_meta = ArticleMetadata(
            title="Test Article",
            url=url,
            published_date=datetime.now(),
            source="example_source"
        )
        
        result = await extractor.extract_content(article_meta)
        print(f"Extracted {url}: {result['success']}")
    
    # Check session stats
    stats = extractor.get_session_stats()
    print(f"Session stats: {stats}")

if __name__ == "__main__":
    asyncio.run(example_usage())
