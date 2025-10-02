"""
Hierarchical Content Extraction Template
========================================

This template implements a multi-layered content extraction system with fallback mechanisms:

1. PRIMARY: Crawl4AI (Playwright) - Modern JavaScript-heavy sites
2. SECONDARY: BeautifulSoup HTML scraping - Traditional HTML parsing  
3. TERTIARY: RSS feeds - Backup content source

The system automatically tries each method in order and reports which method succeeded.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from loguru import logger
from enum import Enum

# Import base template
from .base_template import BaseNewsSourceTemplate

# Import various extraction methods
from crawler.extractors.crawl4ai_extractor import Crawl4AIExtractor
from crawler.extractors.beautifulsoup_extractor import BeautifulSoupExtractor  
from crawler.extractors.rss_extractor import RSSExtractor

# Import other services  
from crawler.templates.base_template import BaseDuplicateChecker, BaseContentProcessor, BaseContentStorage
from crawler.interfaces import ArticleMetadata, ProcessingResult, SourceConfig


class ExtractionMethod(Enum):
    """Enumeration of content extraction methods."""
    CRAWL4AI = "crawl4ai"
    BEAUTIFULSOUP = "beautifulsoup"
    RSS = "rss"
    FAILED = "failed"


class HierarchicalTemplate(BaseNewsSourceTemplate):
    """
    Hierarchical content extraction template with intelligent fallback system.
    
    This template tries multiple extraction methods in order:
    1. Crawl4AI (Playwright) for modern sites with JavaScript
    2. BeautifulSoup for traditional HTML parsing
    3. RSS feeds as final fallback
    
    Reports which method was successful for monitoring and optimization.
    """
    
    def __init__(self, source_config: SourceConfig):
        """Initialize hierarchical extraction template."""
        super().__init__(source_config)
        self.extraction_stats = {
            ExtractionMethod.CRAWL4AI.value: {"attempts": 0, "successes": 0},
            ExtractionMethod.BEAUTIFULSOUP.value: {"attempts": 0, "successes": 0}, 
            ExtractionMethod.RSS.value: {"attempts": 0, "successes": 0},
            ExtractionMethod.FAILED.value: {"attempts": 0, "successes": 0}
        }
        
        logger.info(f"Initialized hierarchical extraction for {source_config.name}")
        
    def _create_discovery_service(self):
        """Create hierarchical discovery service."""
        return HierarchicalDiscoveryService(self.config)
        
    def _create_extractor_service(self):
        """Create hierarchical extractor service."""
        return HierarchicalExtractorService(self.config)
        
    def _create_processor_service(self):
        """Create content processor service.""" 
        return BaseContentProcessor(self.config)
        
    def _create_duplicate_checker(self):
        """Create duplicate checker service."""
        return BaseDuplicateChecker(self.config)
        
    def _create_storage_service(self):
        """Create storage service."""
        return BaseContentStorage(self.config)
        
    async def fetch_articles(self, max_articles: Optional[int] = None) -> List[ArticleMetadata]:
        """
        Fetch articles using hierarchical extraction methods.
        
        Tries each extraction method in order until one succeeds.
        Reports which method was used for transparency.
        """
        max_articles = max_articles or self.config.max_articles_per_run
        logger.info(f"Starting hierarchical extraction for {self.config.name} (max: {max_articles})")
        
        # Try each extraction method in order
        extraction_methods = [
            (ExtractionMethod.CRAWL4AI, self._try_crawl4ai_extraction),
            (ExtractionMethod.BEAUTIFULSOUP, self._try_beautifulsoup_extraction),
            (ExtractionMethod.RSS, self._try_rss_extraction)
        ]
        
        for method, extractor_func in extraction_methods:
            try:
                logger.info(f"🔄 Trying {method.value} extraction for {self.config.name}")
                self.extraction_stats[method.value]["attempts"] += 1
                
                articles = await extractor_func(max_articles)
                
                if articles and len(articles) > 0:
                    self.extraction_stats[method.value]["successes"] += 1
                    logger.success(f"✅ {method.value} extraction succeeded for {self.config.name} - found {len(articles)} articles")
                    
                    # Store extraction method info for reporting (can't modify frozen dataclass)
                    # The extraction method will be tracked in the template's statistics instead
                    
                    return articles
                else:
                    logger.warning(f"⚠️ {method.value} extraction returned no articles for {self.config.name}")
                    
            except Exception as e:
                logger.error(f"❌ {method.value} extraction failed for {self.config.name}: {str(e)}")
                continue
        
        # All methods failed
        self.extraction_stats[ExtractionMethod.FAILED.value]["attempts"] += 1
        logger.error(f"🚨 All extraction methods failed for {self.config.name}")
        return []    
    async def _try_crawl4ai_extraction(self, max_articles: int) -> List[ArticleMetadata]:
        """Try extracting articles using Crawl4AI (Playwright)."""
        try:
            extractor = Crawl4AIExtractor(self.config)
            
            # For RSS-configured sources, first discover article URLs
            if hasattr(self.config, 'rss_url') and self.config.rss_url:
                # Use RSS to find article URLs, then crawl with Crawl4AI
                rss_extractor = RSSExtractor(self.config)
                article_urls = await rss_extractor.discover_article_urls(max_articles)
                
                articles = []
                for url in article_urls[:max_articles]:
                    try:
                        article = await extractor.extract_article_content(url)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.warning(f"Failed to extract {url} with Crawl4AI: {str(e)}")
                        continue
                        
                return articles
            else:
                # Direct website crawling
                return await extractor.crawl_website(self.config.base_url, max_articles)
                
        except Exception as e:
            logger.error(f"Crawl4AI extraction error: {str(e)}")
            raise    
    async def _try_beautifulsoup_extraction(self, max_articles: int) -> List[ArticleMetadata]:
        """Try extracting articles using BeautifulSoup."""
        try:
            extractor = BeautifulSoupExtractor(self.config)
            
            # Similar approach - use RSS for URL discovery if available
            if hasattr(self.config, 'rss_url') and self.config.rss_url:
                rss_extractor = RSSExtractor(self.config)
                article_urls = await rss_extractor.discover_article_urls(max_articles)
                
                articles = []
                for url in article_urls[:max_articles]:
                    try:
                        article = await extractor.extract_article_content(url)
                        if article:
                            articles.append(article)
                    except Exception as e:
                        logger.warning(f"Failed to extract {url} with BeautifulSoup: {str(e)}")
                        continue
                        
                return articles
            else:
                # Direct website scraping
                return await extractor.scrape_website(self.config.base_url, max_articles)
                
        except Exception as e:
            logger.error(f"BeautifulSoup extraction error: {str(e)}")
            raise    
    async def _try_rss_extraction(self, max_articles: int) -> List[ArticleMetadata]:
        """Try extracting articles using RSS feeds."""
        try:
            if not (hasattr(self.config, 'rss_url') and self.config.rss_url):
                # Try to discover RSS feed automatically
                rss_url = await self._discover_rss_feed()
                if not rss_url:
                    raise Exception("No RSS feed configured or discovered")
            else:
                rss_url = self.config.rss_url
            
            extractor = RSSExtractor(self.config, rss_url)
            return await extractor.extract_from_rss(max_articles)
            
        except Exception as e:
            logger.error(f"RSS extraction error: {str(e)}")
            raise
    
    async def _discover_rss_feed(self) -> Optional[str]:
        """Try to discover RSS feed URLs automatically."""
        try:
            common_rss_paths = ["/feed/", "/rss/", "/feed.xml", "/rss.xml", "/feed.rss", "/atom.xml"]
            base_url = self.config.base_url.rstrip('/')
            
            # Simple HTTP check for common RSS paths
            import aiohttp
            async with aiohttp.ClientSession() as session:
                for path in common_rss_paths:
                    test_url = f"{base_url}{path}"
                    try:
                        async with session.get(test_url, timeout=10) as response:
                            if response.status == 200:
                                content_type = response.headers.get('content-type', '').lower()
                                if any(t in content_type for t in ['xml', 'rss', 'atom']):
                                    logger.info(f"Discovered RSS feed: {test_url}")
                                    return test_url
                    except:
                        continue
        except Exception as e:
            logger.warning(f"RSS discovery failed: {str(e)}")
        return None    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get statistics about extraction method usage."""
        stats = {}
        total_attempts = sum(method["attempts"] for method in self.extraction_stats.values())
        
        for method, data in self.extraction_stats.items():
            attempts = data["attempts"]
            successes = data["successes"] 
            
            stats[method] = {
                "attempts": attempts,
                "successes": successes,
                "success_rate": (successes / attempts * 100) if attempts > 0 else 0,
                "usage_percent": (attempts / total_attempts * 100) if total_attempts > 0 else 0
            }
            
        return stats


class HierarchicalDiscoveryService:
    """Article discovery service for hierarchical template."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        
    async def discover_articles(self, max_articles: int = 50) -> List[str]:
        """Discover article URLs using the best available method."""
        return []


class HierarchicalExtractorService: 
    """Content extraction service for hierarchical template."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        
    async def extract_content(self, url: str) -> Optional[str]:
        """Extract content using the best available method."""
        return None