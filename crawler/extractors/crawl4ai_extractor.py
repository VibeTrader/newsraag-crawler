"""
Crawl4AI extractor for JavaScript-heavy websites.

Uses Playwright to render JavaScript and extract content from modern websites.
"""

import asyncio
from typing import List, Optional, Dict, Any
from loguru import logger
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawler.interfaces import ArticleMetadata, SourceConfig
from datetime import datetime
import hashlib


class Crawl4AIExtractor:
    """Content extractor using Crawl4AI with Playwright."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self.crawler = None
        self._initialize_crawler()
    
    def _initialize_crawler(self):
        """Initialize the Crawl4AI crawler."""
        try:
            # Configure browser settings
            browser_config = BrowserConfig(
                browser_type="chromium",
                headless=True,
                viewport_width=1920,
                viewport_height=1080
            )
            
            # Initialize crawler
            self.crawler = AsyncWebCrawler()
            logger.info("Crawl4AI extractor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Crawl4AI: {str(e)}")
            self.crawler = None
    
    async def crawl_website(self, base_url: str, max_articles: int) -> List[ArticleMetadata]:
        """Crawl website to discover and extract articles."""
        if not self.crawler:
            raise Exception("Crawler not initialized")
            
        articles = []
        
        try:
            # Configure crawl settings
            config = CrawlerRunConfig(
                word_count_threshold=50,
                extraction_strategy="LLMExtractionStrategy",
                chunking_strategy="RegexChunking",
                bypass_cache=True
            )
            
            logger.info(f"🚀 Crawling {base_url} with Crawl4AI")
            
            # Perform the crawl
            result = await self.crawler.arun(
                url=base_url,
                config=config
            )
            
            if result.success:
                # Extract article information
                article = self._process_crawl_result(result, base_url)
                if article:
                    articles.append(article)
                    
                # Try to find additional article links
                if hasattr(result, 'links') and result.links:
                    article_links = self._filter_article_links(result.links, base_url)
                    
                    for link_url in article_links[:max_articles-1]:  # -1 because we already have the main page
                        try:
                            link_result = await self.crawler.arun(url=link_url, config=config)
                            if link_result.success:
                                article = self._process_crawl_result(link_result, link_url)
                                if article:
                                    articles.append(article)
                        except Exception as e:
                            logger.warning(f"Failed to crawl {link_url}: {str(e)}")
                            continue
            else:
                logger.error(f"Crawl4AI failed for {base_url}: {result.error_message}")
                
        except Exception as e:
            logger.error(f"Crawl4AI extraction error: {str(e)}")
            raise
            
        logger.info(f"✅ Crawl4AI extracted {len(articles)} articles from {base_url}")
        return articles
    
    def _process_crawl_result(self, result, url: str) -> Optional[ArticleMetadata]:
        """Process crawl result into ArticleMetadata."""
        try:
            # Extract content
            content = result.markdown if hasattr(result, 'markdown') else ""
            if not content or len(content.strip()) < 100:
                logger.warning(f"Content too short from {url}: {len(content)} chars")
                return None
            
            # Extract metadata
            title = ""
            if hasattr(result, 'metadata') and result.metadata:
                title = result.metadata.get('title', '')
            
            if not title and hasattr(result, 'title'):
                title = result.title
                
            # Generate article ID
            article_id = hashlib.md5(f"{url}_{title}".encode()).hexdigest()
            
            return ArticleMetadata(
                title=title or f"Article from {url}",
                url=url,
                published_date=datetime.now(),
                source_name=self.config.name,
                article_id=article_id
            )
            
        except Exception as e:
            logger.error(f"Error processing crawl result for {url}: {str(e)}")
            return None
    
    def _filter_article_links(self, links: List[str], base_url: str) -> List[str]:
        """Filter and prioritize article links."""
        article_links = []
        
        # Common article URL patterns
        article_patterns = [
            '/article/', '/news/', '/post/', '/blog/', '/story/',
            '/analysis/', '/market/', '/forex/', '/stock/', '/trading/'
        ]
        
        for link in links:
            # Skip external links
            if not link.startswith(base_url):
                continue
                
            # Check if URL looks like an article
            if any(pattern in link.lower() for pattern in article_patterns):
                article_links.append(link)
                
        return article_links[:20]  # Limit to avoid too many requests
    
    async def extract_article_content(self, url: str) -> Optional[ArticleMetadata]:
        """Extract content from a specific article URL."""
        if not self.crawler:
            raise Exception("Crawler not initialized")
            
        try:
            config = CrawlerRunConfig(
                word_count_threshold=50,
                extraction_strategy="LLMExtractionStrategy",
                bypass_cache=True
            )
            
            result = await self.crawler.arun(url=url, config=config)
            
            if result.success:
                return self._process_crawl_result(result, url)
            else:
                logger.error(f"Failed to extract {url}: {result.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting article from {url}: {str(e)}")
            return None
    
    async def health_check(self) -> bool:
        """Check if Crawl4AI extractor is healthy."""
        try:
            if not self.crawler:
                return False
                
            # Try a simple crawl test
            test_result = await self.crawler.arun(
                url="https://httpbin.org/html",
                config=CrawlerRunConfig(bypass_cache=True)
            )
            
            return test_result.success
            
        except Exception as e:
            logger.error(f"Crawl4AI health check failed: {str(e)}")
            return False
    
    def __del__(self):
        """Clean up crawler resources."""
        if self.crawler:
            try:
                asyncio.create_task(self.crawler.aclose())
            except:
                pass