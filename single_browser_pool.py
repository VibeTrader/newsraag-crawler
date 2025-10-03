"""
SINGLE BROWSER SOLUTION - Only one Chrome process for all sources.
This modifies the browser session pool to use truly global single browser.
"""

import asyncio
import time
from loguru import logger
from crawl4ai import AsyncWebCrawler, BrowserConfig
import atexit

class SingleBrowserPool:
    """
    Single browser instance shared across ALL sources.
    Maximum efficiency - only 1 Chrome process total.
    """
    
    _instance = None
    _crawler = None
    _initialized = False
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        atexit.register(self.cleanup_sync)
        logger.info("Single browser pool initialized")
    
    async def get_global_browser(self) -> AsyncWebCrawler:
        """Get the single global browser instance."""
        async with self._lock:
            if self._crawler is None:
                await self._create_single_browser()
            return self._crawler
    
    async def _create_single_browser(self):
        """Create the single browser instance for all sources."""
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
                    "--memory-pressure-off",
                    "--max-old-space-size=512",  # Higher for single browser
                    "--aggressive-cache-discard",
                    "--disable-background-timer-throttling",
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                ]
            )
            
            self._crawler = AsyncWebCrawler(config=browser_config, verbose=False)
            await self._crawler.astart()
            
            logger.info("Created SINGLE global browser for all sources")
            
        except Exception as e:
            logger.error(f"Failed to create single browser: {e}")
            raise
    
    def cleanup_sync(self):
        """Cleanup single browser on exit."""
        try:
            if self._crawler:
                import asyncio
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self._crawler.aclose())
                logger.info("Single browser cleaned up")
        except:
            pass

# Global single browser instance
_single_browser_pool = SingleBrowserPool()
