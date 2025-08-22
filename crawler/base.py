from typing import Callable, Awaitable, TypeVar, Generic, List
from crawler.redis_cache import RedisUrlCache
import asyncio
# Import AsyncWebCrawler for type hinting
from crawl4ai import AsyncWebCrawler 



# Type definitions for better type hints
T = TypeVar('T')  # Generic type for URL data tuples
CrawlerFunc = Callable[[T], Awaitable[bool]]  # Type for crawler functions

# Base directory for all outputs


class BaseCrawlerModule(Generic[T]):
    """Base class for crawler modules.
    
    This class provides the common structure and functionality for all crawler modules.
    Each specific crawler (like BabyPips, FXStreet) should inherit from this class.
    
    Manages URL caching via Redis. Browser lifecycle (AsyncWebCrawler) is handled externally.
    """
    
    def __init__(self, name: str):
        """Initialize the crawler module.
        
        Args:
            name: The name of the crawler module (e.g., 'babypips', 'fxstreet')
        """
        self.name = name
        # self.max_concurrent = max_concurrent # Concurrency handled externally
        self.url_cache = RedisUrlCache(name)
    
    async def get_urls(self) -> List[T]:
        """Get URLs to crawl.
        
        This method should be implemented by subclasses to fetch URLs
        from the specific source (e.g., RSS feed, API).
        
        Returns:
            A list of URL data tuples (format depends on the crawler implementation)
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    async def process_url(self, url_data: T, crawler_instance: AsyncWebCrawler) -> bool:
        """Process a single URL.
        
        This method should be implemented by subclasses to process a single URL 
        using the provided shared AsyncWebCrawler instance.
        
        Args:
            url_data: URL data tuple (format depends on the crawler implementation)
            crawler_instance: The shared AsyncWebCrawler instance to use for crawling.
            
        Returns:
            True if the URL was processed successfully, False otherwise
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def _get_url_from_data(self, url_data: T) -> str:
        """Extract the URL from the URL data tuple.
        
        This method should be overridden by subclasses if the URL is not the first element
        in the URL data tuple.
        
        Args:
            url_data: URL data tuple (format depends on the crawler implementation)
            
        Returns:
            The URL as a string
        """
        # Default implementation assumes the URL is the first element in the tuple
        if isinstance(url_data, tuple) and len(url_data) > 0:
             return str(url_data[0]) # Ensure it's a string
        elif isinstance(url_data, str):
             return url_data
        else:
             # Raise an error or log if the format is unexpected
             raise TypeError(f"Cannot extract URL from url_data of type {type(url_data)}")