"""
Content extractor implementations following Open-Closed Principle.
Each extractor is a single-responsibility class that can be extended independently.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from ..interfaces.news_source_interface import IContentExtractor


class BaseContentExtractor(IContentExtractor):
    """Base extractor with common functionality."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.selectors = config.get('selectors', {})

    async def extract_content(self, url: str, session: aiohttp.ClientSession, **kwargs) -> Optional[str]:
        """Template method - subclasses implement _do_extract."""
        try:
            async with session.get(url, timeout=30) as response:
                if response.status != 200:
                    return None
                content = await response.text()
                return await self._do_extract(content, url, **kwargs)
        except Exception as e:
            print(f"Extraction failed for {url}: {e}")
            return None
    
    @abstractmethod
    async def _do_extract(self, content: str, url: str, **kwargs) -> Optional[str]:
        """Subclasses implement specific extraction logic."""
        pass


class HTMLContentExtractor(BaseContentExtractor):
    """Generic HTML content extractor - works for most sites."""
    
    async def _do_extract(self, content: str, url: str, **kwargs) -> Optional[str]:
        """Extract content using smart defaults and configured selectors."""
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove unwanted elements
        for unwanted in soup(['script', 'style', 'nav', 'header', 'footer', '.ads']):
            unwanted.decompose()
        
        # Try configured selectors first
        if isinstance(self.selectors, dict) and 'content' in self.selectors:
            for selector in self.selectors['content']:
                element = soup.select_one(selector)
                if element:
                    return element.get_text(separator=' ', strip=True)
        elif isinstance(self.selectors, str):
            # Simple string selector
            element = soup.select_one(self.selectors)
            if element:
                return element.get_text(separator=' ', strip=True)
        
        # Smart fallback selectors
        smart_selectors = [
            'article', '.content', '.post-content', '.article-body', 
            '.entry-content', '.story-body', 'main', '.article-text'
        ]
        
        for selector in smart_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(separator=' ', strip=True)
                if len(text) > 100:  # Only substantial content
                    return text
        
        return soup.get_text(separator=' ', strip=True)[:2000]  # Last resort


class YouTubeContentExtractor(BaseContentExtractor):
    """YouTube extractor - content already extracted in discovery phase."""
    
    async def _do_extract(self, content: str, url: str, **kwargs) -> Optional[str]:
        """
        For YouTube, content (transcript) is already extracted during discovery.
        This method just passes it through.
        """
        # Content is already in the metadata from YouTubeExtractor
        # Just return it as-is (it was passed via kwargs or already fetched)
        return kwargs.get('extracted_content', content)


class TwitterContentExtractor(BaseContentExtractor):
    """Twitter extractor - content already extracted in discovery phase."""
    
    async def _do_extract(self, content: str, url: str, **kwargs) -> Optional[str]:
        """
        For Twitter, tweet text is already extracted during discovery.
        This method just passes it through.
        """
        # Content is already in the metadata from TwitterExtractor
        # Just return it as-is
        return kwargs.get('extracted_content', content)


class RedditContentExtractor(BaseContentExtractor):
    """Reddit extractor - ready for API integration."""
    
    async def _do_extract(self, content: str, url: str, **kwargs) -> Optional[str]:
        """Extract Reddit content. Override this method to add API integration."""
        # Tomorrow someone can extend this with Reddit API
        return f"Reddit content from: {url}"


# Registry for easy extension - Open-Closed Principle in action
EXTRACTOR_REGISTRY = {
    'rss': HTMLContentExtractor,  # RSS can use HTML extraction for full content
    'html_scraping': HTMLContentExtractor,
    'youtube': YouTubeContentExtractor,
    'twitter': TwitterContentExtractor, 
    'reddit': RedditContentExtractor,
}


def create_content_extractor(source_type: str, config: Dict[str, Any]) -> IContentExtractor:
    """Factory function - to add new extractors, just add to registry above."""
    extractor_class = EXTRACTOR_REGISTRY.get(source_type, HTMLContentExtractor)
    return extractor_class(config)
