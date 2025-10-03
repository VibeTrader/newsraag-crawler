"""
Enhanced Crawl4AI extractor with robust timeout handling and fallback strategies.
Fixes FXStreet timeout issues and provides better reliability for financial news sites.
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


class EnhancedCrawl4AIExtractor:
    """
    Enhanced content extractor using Crawl4AI with intelligent timeout handling.
    
    Features:
    - Configurable timeouts per source
    - Multiple retry strategies  
    - Fallback to lighter extraction modes
    - Anti-bot detection countermeasures
    """
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self.crawler = None
        self.max_retries = 3
        self.retry_timeouts = [30, 60, 120]  # Progressive timeout increase
        self._initialize_crawler()
    
    def _initialize_crawler(self):
        """Initialize the Crawl4AI crawler with enhanced configuration."""
        try:
            # Enhanced browser configuration for financial sites
            browser_config = BrowserConfig(
                browser_type="chromium",
                headless=True,
                viewport_width=1920,
                viewport_height=1080,
                # Anti-detection measures
                extra_args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage", 
                    "--disable-gpu",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-web-security",
                    "--disable-blink-features=AutomationControlled",
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ]
            )
            
            # Initialize crawler
            self.crawler = AsyncWebCrawler(config=browser_config)
            logger.info(f"Enhanced Crawl4AI extractor initialized for {self.config.name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Enhanced Crawl4AI for {self.config.name}: {str(e)}")
            self.crawler = None
    
    async def crawl_website(self, base_url: str, max_articles: int) -> List[ArticleMetadata]:
        """Crawl website to discover and extract articles with enhanced error handling."""
        if not self.crawler:
            raise Exception(f"Crawler not initialized for {self.config.name}")
            
        articles = []
        
        try:
            logger.info(f"🚀 Starting enhanced crawl of {base_url} for {self.config.name}")
            
            # Try progressive timeout strategy
            for attempt, timeout_seconds in enumerate(self.retry_timeouts, 1):
                try:
                    logger.info(f"📡 Attempt {attempt}/{len(self.retry_timeouts)} with {timeout_seconds}s timeout for {self.config.name}")
                    
                    # Configure crawl settings with timeout
                    config = self._create_crawl_config(timeout_seconds)
                    
                    # Perform the crawl with timeout
                    result = await asyncio.wait_for(
                        self.crawler.arun(url=base_url, config=config),
                        timeout=timeout_seconds + 10  # Add 10s buffer for cleanup
                    )
                    
                    if result.success:
                        logger.success(f"✅ {self.config.name}: Successfully crawled {base_url} on attempt {attempt}")
                        
                        # Extract article information
                        article = self._process_crawl_result(result, base_url)
                        if article:
                            articles.append(article)
                            
                        # Try to find additional article links
                        if hasattr(result, 'links') and result.links:
                            article_links = self._filter_article_links(result.links, base_url)
                            
                            for link_url in article_links[:max_articles-1]:  # -1 because we already have the main page
                                try:
                                    # Use shorter timeout for individual articles
                                    article_timeout = min(timeout_seconds, 45)
                                    link_result = await asyncio.wait_for(
                                        self.crawler.arun(url=link_url, config=config),
                                        timeout=article_timeout
                                    )
                                    
                                    if link_result.success:
                                        article = self._process_crawl_result(link_result, link_url)
                                        if article:
                                            articles.append(article)
                                except asyncio.TimeoutError:
                                    logger.warning(f"⏰ {self.config.name}: Article timeout for {link_url}")
                                    continue
                                except Exception as e:
                                    logger.warning(f"⚠️ {self.config.name}: Failed to crawl article {link_url}: {str(e)}")
                                    continue
                        
                        # Success - break retry loop
                        break
                        
                    else:
                        logger.warning(f"⚠️ {self.config.name}: Crawl failed on attempt {attempt}: {result.error_message}")
                        if attempt == len(self.retry_timeouts):
                            raise Exception(f"All crawl attempts failed. Last error: {result.error_message}")
                        continue
                        
                except asyncio.TimeoutError:
                    logger.warning(f"⏰ {self.config.name}: Timeout after {timeout_seconds}s on attempt {attempt}")
                    if attempt == len(self.retry_timeouts):
                        logger.error(f"❌ {self.config.name}: All timeout attempts exhausted for {base_url}")
                        raise Exception(f"Crawl timeout after all retry attempts ({self.retry_timeouts})")
                    continue
                    
                except Exception as e:
                    logger.error(f"❌ {self.config.name}: Crawl error on attempt {attempt}: {str(e)}")
                    if attempt == len(self.retry_timeouts):
                        raise
                    continue
                
        except Exception as e:
            logger.error(f"❌ {self.config.name}: Enhanced crawl extraction error: {str(e)}")
            raise
            
        logger.info(f"✅ {self.config.name}: Enhanced crawl extracted {len(articles)} articles from {base_url}")
        return articles
    
    def _create_crawl_config(self, timeout_seconds: int) -> CrawlerRunConfig:
        """Create crawl configuration with timeout and extraction strategy."""
        # Use lighter extraction for faster loading
        extraction_strategy = NoExtractionStrategy()  
        chunking_strategy = RegexChunking()
        
        return CrawlerRunConfig(
            word_count_threshold=50,
            extraction_strategy=extraction_strategy,
            chunking_strategy=chunking_strategy,
            cache_mode=CacheMode.BYPASS,
            # Timeout configuration
            page_timeout=timeout_seconds * 1000,  # Convert to milliseconds
            # Anti-detection
            simulate_user=True,
            override_navigator=True
        )
    
    def _process_crawl_result(self, result, url: str) -> Optional[ArticleMetadata]:
        """Process crawl result into ArticleMetadata with enhanced validation."""
        try:
            # Extract content with multiple fallback strategies
            content = ""
            
            if hasattr(result, 'markdown') and result.markdown:
                content = result.markdown
            elif hasattr(result, 'cleaned_html') and result.cleaned_html:
                content = result.cleaned_html  
            elif hasattr(result, 'html') and result.html:
                # Basic HTML cleanup
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(result.html, 'html.parser')
                content = soup.get_text(separator=' ', strip=True)
            
            if not content or len(content.strip()) < 100:
                logger.warning(f"⚠️ {self.config.name}: Content too short from {url}: {len(content)} chars")
                return None
            
            # Extract metadata with fallbacks
            title = ""
            if hasattr(result, 'metadata') and result.metadata:
                title = result.metadata.get('title', '')
            
            if not title and hasattr(result, 'title'):
                title = result.title
                
            # Extract from HTML if still no title
            if not title and hasattr(result, 'html'):
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(result.html, 'html.parser')
                    title_tag = soup.find('title') or soup.find('h1') or soup.find('h2')
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                except:
                    pass
                    
            # Generate article ID
            article_id = hashlib.md5(f"{url}_{title}".encode()).hexdigest()
            
            logger.debug(f"📄 {self.config.name}: Processed article - Title: {title[:50]}..., Content: {len(content)} chars")
            
            return ArticleMetadata(
                title=title or f"Article from {url}",
                url=url,
                published_date=datetime.now(),
                source_name=self.config.name,
                article_id=article_id
            )
            
        except Exception as e:
            logger.error(f"❌ {self.config.name}: Error processing crawl result for {url}: {str(e)}")
            return None
    
    def _filter_article_links(self, links: List[str], base_url: str) -> List[str]:
        """Filter and prioritize article links with enhanced patterns."""
        article_links = []
        
        # Enhanced article URL patterns for financial sites
        article_patterns = [
            '/article/', '/news/', '/post/', '/blog/', '/story/',
            '/analysis/', '/market/', '/forex/', '/stock/', '/trading/',
            '/research/', '/insight/', '/commentary/', '/opinion/',
            '/technical-analysis/', '/fundamental-analysis/',
            # FXStreet specific patterns
            '/usd-', '/eur-', '/gbp-', '/jpy-', '/cad-', '/aud-', '/chf-', '/nzd-'
        ]
        
        # Skip patterns (ads, social, etc.)
        skip_patterns = [
            '/tag/', '/category/', '/author/', '/advertorial/',
            'facebook.com', 'twitter.com', 'linkedin.com', 'youtube.com',
            '/subscribe', '/newsletter', '/contact', '/about'
        ]
        
        for link in links:
            try:
                # Skip external links
                if not link.startswith(base_url) and not link.startswith('/'):
                    continue
                
                # Skip unwanted patterns
                if any(pattern in link.lower() for pattern in skip_patterns):
                    continue
                
                # Check if URL looks like an article
                if any(pattern in link.lower() for pattern in article_patterns):
                    # Make URL absolute
                    if link.startswith('/'):
                        link = base_url.rstrip('/') + link
                    article_links.append(link)
                    
            except Exception as e:
                logger.warning(f"⚠️ {self.config.name}: Error filtering link {link}: {str(e)}")
                continue
                
        # Remove duplicates and limit
        unique_links = list(dict.fromkeys(article_links))  # Preserves order
        logger.debug(f"🔗 {self.config.name}: Filtered {len(unique_links)} article links from {len(links)} total links")
        
        return unique_links[:20]  # Limit to avoid too many requests
    
    async def extract_article_content(self, url: str) -> Optional[ArticleMetadata]:
        """Extract content from a specific article URL with timeout handling."""
        if not self.crawler:
            raise Exception(f"Crawler not initialized for {self.config.name}")
            
        try:
            # Use progressive timeout for individual articles
            for attempt, timeout_seconds in enumerate([30, 60, 90], 1):
                try:
                    logger.debug(f"📄 {self.config.name}: Extracting article {url} (attempt {attempt}, timeout {timeout_seconds}s)")
                    
                    config = self._create_crawl_config(timeout_seconds)
                    
                    result = await asyncio.wait_for(
                        self.crawler.arun(url=url, config=config),
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
            if not self.crawler:
                logger.warning(f"⚠️ {self.config.name}: Crawler not initialized for health check")
                return False
                
            # Try a simple crawl test with short timeout
            logger.debug(f"🔍 {self.config.name}: Running health check...")
            
            test_result = await asyncio.wait_for(
                self.crawler.arun(
                    url="https://httpbin.org/html",
                    config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
                ),
                timeout=15  # Short timeout for health check
            )
            
            is_healthy = test_result.success
            logger.debug(f"💚 {self.config.name}: Health check {'passed' if is_healthy else 'failed'}")
            return is_healthy
            
        except asyncio.TimeoutError:
            logger.warning(f"⏰ {self.config.name}: Health check timeout")
            return False
        except Exception as e:
            logger.error(f"❌ {self.config.name}: Health check failed: {str(e)}")
            return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        if self.crawler:
            await self.crawler.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.crawler:
            await self.crawler.__aexit__(exc_type, exc_val, exc_tb)
    
    def __del__(self):
        """Clean up crawler resources."""
        if self.crawler:
            try:
                asyncio.create_task(self.crawler.aclose())
            except:
                pass
            try:
                asyncio.create_task(self.crawler.aclose())
            except:
                pass

# Backward compatibility - provide the old class name as an alias
Crawl4AIExtractor = EnhancedCrawl4AIExtractor
