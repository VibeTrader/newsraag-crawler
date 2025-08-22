"""
PoundSterlingLive crawler module.
"""
import re
from datetime import datetime
from typing import List, Tuple
from loguru import logger

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from models.output import OutputModel
from utils.clean_markdown import clean_markdown
from crawler.base import BaseCrawlerModule 
from utils.dir_utils import get_output_dir, generate_id, get_timestamp
from utils.azure_utils import upload_json_to_azure, check_azure_connection
from utils.time_utils import convert_to_pst, get_current_pst_time 
from clients.vector_client import VectorClient

# Define the URL data type for PoundSterlingLive
PoundSterlingLiveUrlData = Tuple[str, str, datetime]  # url, title, pubDate

class PoundSterlingLiveCrawler(BaseCrawlerModule[PoundSterlingLiveUrlData]):
    """Crawler for PoundSterlingLive website."""
    
    def __init__(self, base_url: str = "https://www.poundsterlinglive.com/markets", max_concurrent: int = 3):
        """Initialize the PoundSterlingLive crawler.
        
        Args:
            base_url: The base URL for the news list page.
            max_concurrent: Maximum number of concurrent crawling tasks
        """
        super().__init__("poundsterlinglive", max_concurrent)
        self.base_url = base_url
        self.browser_config = BrowserConfig(
            headless=True,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )
        self.crawler = None # Initialize crawler instance variable
    
    async def initialize_crawler(self):
        """Initializes the shared AsyncWebCrawler instance."""
        if not self.crawler:
            try:
                logger.info(f"[{self.name}] Initializing shared AsyncWebCrawler...")
                self.crawler = AsyncWebCrawler(config=self.browser_config)
                await self.crawler.start()
                logger.info(f"[{self.name}] Shared AsyncWebCrawler initialized successfully.")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to initialize shared AsyncWebCrawler: {e}", exc_info=True)
                self.crawler = None # Ensure crawler is None if init fails
                raise # Re-raise the exception to signal failure

    async def close_crawler(self):
        """Closes the shared AsyncWebCrawler instance."""
        if self.crawler:
            try:
                logger.info(f"[{self.name}] Closing shared AsyncWebCrawler...")
                await self.crawler.close()
                logger.info(f"[{self.name}] Shared AsyncWebCrawler closed.")
            except Exception as e:
                logger.error(f"[{self.name}] Error closing shared AsyncWebCrawler: {e}", exc_info=True)
            finally:
                self.crawler = None # Reset crawler instance

    async def get_urls(self) -> List[PoundSterlingLiveUrlData]:
        """Get URLs from the PoundSterlingLive news list page.
        
        Returns:
            A list of tuples (url, title, pubDate)
        """
        # Implementation based on PRD 5.4
        logger.info(f"[{self.name}] Fetching URLs from {self.base_url}...")
        # TODO: Implement HTML scraping (requests+bs4) for list page, 
        #       fetching individual article pages for dates, and date filtering logic.
        return []
    
    async def process_url(self, url_data: PoundSterlingLiveUrlData) -> bool:
        """Process a single URL from PoundSterlingLive.
        
        Args:
            url_data: A tuple (url, title, pubDate)
        
        Returns:
            True if the URL was processed successfully, False otherwise
        """
        url, title, pubDate_datetime_obj = url_data
        
        # Check if this URL has already been processed
        if self.url_cache.is_processed(url):
            logger.info(f"[{self.name}] Skipping already processed URL: {url}")
            return True
        
        # Ensure crawler is initialized before processing
        if not self.crawler:
            logger.error(f"[{self.name}] Crawler not initialized. Cannot process URL: {url}")
            return False

        logger.info(f"[{self.name}] Processing URL: {url}")
        # TODO: Implement crawling, content extraction, cleaning, Azure upload, Qdrant indexing logic.
        
        # Mark this URL as processed (even if processing fails for now)
        self.url_cache.mark_processed(url)
        return False # Return False until fully implemented 