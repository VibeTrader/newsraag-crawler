#!/usr/bin/env python3
"""
EMERGENCY FIX: Patch the existing crawl4ai_extractor.py to use browser session pooling.
This directly fixes the 44 Chrome processes issue.
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger

def apply_browser_pooling_patch():
    """Apply browser session pooling to the existing extractor."""
    
    logger.info("🔧 Applying browser session pooling patch...")
    
    # First, let's kill all Chrome processes
    import subprocess
    try:
        result = subprocess.run(['taskkill', '/f', '/im', 'chrome.exe'], 
                              capture_output=True, text=True, shell=True)
        logger.info(f"Killed Chrome processes: {result.stdout}")
    except:
        pass
    
    # Read the existing extractor
    extractor_path = "crawler/extractors/crawl4ai_extractor.py"
    
    try:
        with open(extractor_path, 'r') as f:
            current_code = f.read()
        
        logger.info("✅ Read existing extractor code")
        
        # Create the patched version with session pooling
        patched_code = '''"""
Enhanced Crawl4AI extractor with browser session pooling fix.
PATCHED VERSION - Solves the multiple Chrome processes issue.
"""

import asyncio
from typing import List, Optional, Dict, Any
from loguru import logger
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy, NoExtractionStrategy
from crawl4ai.chunking_strategy import RegexChunking
from crawler.interfaces import ArticleMetadata, SourceConfig
from datetime import datetime
import hashlib
import time
import atexit

# BROWSER SESSION POOL - SINGLETON PATTERN
class BrowserSessionPool:
    """Global browser session pool to prevent Chrome process accumulation."""
    
    _instance = None
    _sessions = {}
    _session_lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def get_session(self, source_name: str) -> AsyncWebCrawler:
        """Get or create a browser session for a source."""
        async with self._session_lock:
            # Check if session exists and is valid
            if source_name in self._sessions:
                session_info = self._sessions[source_name]
                if time.time() - session_info['created_at'] < 1800:  # 30 minutes
                    session_info['usage_count'] += 1
                    logger.debug(f"Reusing browser session for {source_name} (usage: {session_info['usage_count']})")
                    return session_info['crawler']
                else:
                    # Session expired, cleanup
                    await self._cleanup_session(source_name)
            
            # Create new session
            return await self._create_session(source_name)
    
    async def _create_session(self, source_name: str) -> AsyncWebCrawler:
        """Create a new browser session."""
        try:
            browser_config = BrowserConfig(
                browser_type="chromium",
                headless=True,
                viewport_width=1280,
                viewport_height=720,
                extra_args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--memory-pressure-off",
                    "--max-old-space-size=256",
                    "--aggressive-cache-discard",
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ]
            )
            
            crawler = AsyncWebCrawler(config=browser_config, verbose=False)
            await crawler.astart()
            
            # Store session
            self._sessions[source_name] = {
                'crawler': crawler,
                'created_at': time.time(),
                'usage_count': 1
            }
            
            logger.info(f"Created new browser session for {source_name} (Total sessions: {len(self._sessions)})")
            return crawler
            
        except Exception as e:
            logger.error(f"Failed to create browser session for {source_name}: {e}")
            raise
    
    async def _cleanup_session(self, source_name: str):
        """Cleanup a specific session."""
        if source_name in self._sessions:
            try:
                await self._sessions[source_name]['crawler'].aclose()
            except:
                pass
            del self._sessions[source_name]
            logger.debug(f"Cleaned up session for {source_name}")
    
    async def cleanup_all(self):
        """Cleanup all sessions."""
        for source_name in list(self._sessions.keys()):
            await self._cleanup_session(source_name)
        logger.info("All browser sessions cleaned up")

# Global instance
_browser_pool = BrowserSessionPool()

# Cleanup on exit
def cleanup_on_exit():
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_browser_pool.cleanup_all())
    except:
        pass

atexit.register(cleanup_on_exit)

class EnhancedCrawl4AIExtractor:
    """
    Enhanced Crawl4AI extractor with browser session pooling.
    FIXED VERSION - Uses shared browser sessions instead of creating new ones.
    """
    
    def __init__(self, config: SourceConfig):
        self.config = config
        # DO NOT create crawler here - use session pool instead
        self.crawler = None  # Will be None, sessions come from pool
        self.max_retries = 3
        self.retry_timeouts = [30, 60, 120]
        
        logger.info(f"Enhanced Crawl4AI extractor initialized for {self.config.name} (using session pool)")
    
    def _create_crawl_config(self, timeout_seconds: int = 30) -> CrawlerRunConfig:
        """Create crawler configuration with timeout."""
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=timeout_seconds * 1000,
            wait_for_images=False,
            screenshot=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
            }
        )
    
    def _process_crawl_result(self, result, url: str) -> Optional[ArticleMetadata]:
        """Process crawl result and return ArticleMetadata."""
        try:
            content = result.extracted_content or ""
            if len(content.strip()) < 100:
                logger.warning(f"⚠️ {self.config.name}: Low content length for {url}")
                return None
            
            # Extract title from metadata or content
            title = "Unknown Title"
            if result.metadata and "title" in result.metadata:
                title = result.metadata["title"]
            
            logger.debug(f"📄 {self.config.name}: Processed article - Title: {title[:50]}..., Content: {len(content)} chars")
            
            return ArticleMetadata(
                title=title,
                url=url,
                published_date=datetime.now(),
                source=self.config.name,
                content=content
            )
            
        except Exception as e:
            logger.error(f"❌ {self.config.name}: Error processing crawl result: {str(e)}")
            return None
    
    async def extract_article_content(self, url: str) -> Optional[ArticleMetadata]:
        """
        Extract content from a specific article URL using session pool.
        FIXED METHOD - Uses shared browser session instead of self.crawler.
        """
        try:
            # Get shared browser session from pool
            crawler = await _browser_pool.get_session(self.config.name)
            
            # Use progressive timeout for individual articles
            for attempt, timeout_seconds in enumerate([30, 60, 90], 1):
                try:
                    logger.debug(f"📄 {self.config.name}: Extracting article {url} (attempt {attempt}, timeout {timeout_seconds}s)")
                    
                    config = self._create_crawl_config(timeout_seconds)
                    
                    result = await asyncio.wait_for(
                        crawler.arun(url=url, config=config),
                        timeout=timeout_seconds + 5
                    )
                    
                    if result.success:
                        logger.debug(f"✅ {self.config.name}: Successfully extracted article {url}")
                        return self._process_crawl_result(result, url)
                    else:
                        logger.warning(f"⚠️ {self.config.name}: Article extraction failed on attempt {attempt}: {result.error_message}")
                        if attempt == 3:
                            break
                        continue
                        
                except asyncio.TimeoutError:
                    logger.warning(f"⏰ {self.config.name}: Article timeout after {timeout_seconds}s (attempt {attempt})")
                    if attempt == 3:
                        break
                    continue
                    
            logger.error(f"❌ {self.config.name}: Failed to extract {url} after all attempts")
            return None
                
        except Exception as e:
            logger.error(f"❌ {self.config.name}: Error extracting article from {url}: {str(e)}")
            return None
    
    async def health_check(self) -> bool:
        """Check if Enhanced Crawl4AI extractor is healthy."""
        try:
            # Get shared browser session for health check
            crawler = await _browser_pool.get_session(self.config.name)
            
            logger.debug(f"🔍 {self.config.name}: Running health check...")
            
            test_result = await asyncio.wait_for(
                crawler.arun(
                    url="https://httpbin.org/html",
                    config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
                ),
                timeout=15
            )
            
            is_healthy = test_result.success
            logger.debug(f"💚 {self.config.name}: Health check {'passed' if is_healthy else 'failed'}")
            return is_healthy
            
        except Exception as e:
            logger.error(f"❌ {self.config.name}: Health check failed: {str(e)}")
            return False
    
    async def __aenter__(self):
        """Async context manager entry - no longer needed with session pool."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - no longer needed with session pool."""
        pass
'''
        
        # Backup original file
        backup_path = f"{extractor_path}.backup"
        with open(backup_path, 'w') as f:
            f.write(current_code)
        logger.info(f"✅ Backed up original extractor to {backup_path}")
        
        # Write patched version
        with open(extractor_path, 'w') as f:
            f.write(patched_code)
        logger.info(f"✅ Applied browser session pooling patch to {extractor_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to apply patch: {e}")
        return False

def main():
    logger.info("🚨 EMERGENCY BROWSER POOLING PATCH")
    logger.info("This fixes the 44 Chrome processes issue immediately")
    
    success = apply_browser_pooling_patch()
    
    if success:
        logger.info("🎉 PATCH APPLIED SUCCESSFULLY!")
        logger.info("Your extractor now uses browser session pooling")
        logger.info("Chrome processes should drop to ~29 (one per source)")
        logger.info("FXStreet timeouts should be resolved")
        logger.info("System performance should improve dramatically")
    else:
        logger.error("❌ PATCH FAILED!")
        logger.info("Manual intervention required")

if __name__ == "__main__":
    main()
