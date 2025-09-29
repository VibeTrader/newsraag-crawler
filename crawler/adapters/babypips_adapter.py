# crawler/adapters/babypips_adapter.py
"""
Adapter to integrate existing BabyPips crawler with new template system.
"""
from typing import AsyncGenerator, Optional
import hashlib
from datetime import datetime, timezone

from crawler.interfaces.news_source_interface import (
    SourceConfig, ArticleMetadata, ProcessingResult,
    IArticleDiscovery, IContentExtractor, SourceType, ContentType
)
from crawler.templates.base_template import (
    BaseNewsSourceTemplate, BaseContentProcessor, 
    BaseDuplicateChecker, BaseContentStorage
)


class BabyPipsArticleDiscovery(IArticleDiscovery):
    """Adapter for BabyPips article discovery using existing crawler."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialize_babypips_crawler()
    
    def _initialize_babypips_crawler(self):
        """Initialize existing BabyPips crawler."""
        try:
            from crawler.babypips import BabyPipsCrawler
            self.babypips_crawler = BabyPipsCrawler(self.config.rss_url)
            print(f"BabyPips crawler initialized for {self.config.name}")
        except Exception as e:
            print(f"Failed to initialize BabyPips crawler: {e}")
            self.babypips_crawler = None
    
    async def discover_articles(self) -> AsyncGenerator[ArticleMetadata, None]:
        """Discover articles using existing BabyPips RSS parsing logic."""
        if not self.babypips_crawler:
            print("BabyPips crawler not available")
            return
        
        try:
            # Use existing BabyPips method to get URL data
            url_data_list = await self.babypips_crawler._get_urls_to_crawl()
            
            print(f"BabyPips discovered {len(url_data_list)} articles")
            
            articles_yielded = 0
            max_articles = self.config.max_articles_per_run
            
            for url_data in url_data_list:
                if articles_yielded >= max_articles:
                    break
                
                try:
                    # Convert BabyPips URL data to ArticleMetadata
                    article_meta = self._convert_babypips_data(url_data)
                    if article_meta:
                        articles_yielded += 1
                        yield article_meta
                        
                except Exception as e:
                    print(f"Failed to convert BabyPips data to metadata: {e}")
                    continue
            
            print(f"BabyPips yielded {articles_yielded} articles")
            
        except Exception as e:
            print(f"BabyPips discovery failed: {e}")
            raise
    
    def _convert_babypips_data(self, url_data) -> Optional[ArticleMetadata]:
        """Convert BabyPips URL data tuple to ArticleMetadata."""
        try:
            # BabyPips URL data format: (url, title, pubDate, creator, category)
            url, title, pub_date, creator, category = url_data
            
            # Generate article ID
            article_id = hashlib.md5(f"babypips:{title}:{url}".encode()).hexdigest()
            
            return ArticleMetadata(
                title=title.strip(),
                url=url.strip(),
                published_date=pub_date if isinstance(pub_date, datetime) else datetime.now(timezone.utc),
                source_name="babypips",
                article_id=article_id,
                author=creator,
                category=category,
                language="en"
            )
            
        except Exception as e:
            print(f"Failed to convert BabyPips data: {e}")
            return None


class BabyPipsContentExtractor(IContentExtractor):
    """Adapter for BabyPips content extraction using existing crawler."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialize_babypips_crawler()
    
    def _initialize_babypips_crawler(self):
        """Initialize existing BabyPips crawler."""
        try:
            from crawler.babypips import BabyPipsCrawler
            self.babypips_crawler = BabyPipsCrawler(self.config.rss_url)
        except Exception as e:
            print(f"Failed to initialize BabyPips crawler: {e}")
            self.babypips_crawler = None
    
    async def extract_content(self, article_meta: ArticleMetadata) -> ProcessingResult:
        """Extract content using existing BabyPips extraction logic."""
        if not self.babypips_crawler:
            return ProcessingResult(
                success=False,
                error="BabyPips crawler not available"
            )
        
        try:
            print(f"Extracting BabyPips content from: {article_meta.url}")
            
            # Use existing BabyPips crawl_url method
            content = await self.babypips_crawler.crawl_url(article_meta.url)
            
            if not content or len(content.strip()) < 100:
                return ProcessingResult(
                    success=False,
                    error="Extracted content is too short or empty"
                )
            
            print(f"BabyPips extracted {len(content)} characters")
            
            return ProcessingResult(
                success=True,
                content=content,
                metadata={
                    'extraction_method': 'babypips_crawler',
                    'content_length': len(content),
                    'url': article_meta.url
                }
            )
            
        except Exception as e:
            print(f"BabyPips content extraction failed for {article_meta.url}: {e}")
            return ProcessingResult(
                success=False,
                error=str(e)
            )


class BabyPipsSourceAdapter(BaseNewsSourceTemplate):
    """Adapter that wraps existing BabyPips crawler to work with new interface."""
    
    def __init__(self, rss_url: str):
        """Initialize with BabyPips-specific configuration."""
        source_config = SourceConfig(
            name="babypips",
            source_type=SourceType.RSS,
            content_type=ContentType.FOREX,
            base_url="https://www.babypips.com",
            rss_url=rss_url,
            rate_limit_seconds=2,
            max_articles_per_run=50,
            timeout_seconds=30,
            custom_processing=True
        )
        
        super().__init__(source_config)
        print("BabyPips adapter initialized successfully")
    
    def _create_discovery_service(self) -> IArticleDiscovery:
        """Create BabyPips article discovery service."""
        return BabyPipsArticleDiscovery(self.config)
    
    def _create_extractor_service(self) -> IContentExtractor:
        """Create BabyPips content extraction service."""
        return BabyPipsContentExtractor(self.config)
    
    def _create_processor_service(self):
        """Create content processing service (reuse base implementation)."""
        return BaseContentProcessor(self.config)
    
    def _create_duplicate_checker(self):
        """Create duplicate checking service (reuse base implementation)."""
        return BaseDuplicateChecker(self.config)
    
    def _create_storage_service(self):
        """Create storage service (reuse base implementation)."""
        return BaseContentStorage(self.config)


# Factory function
def create_babypips_adapter(rss_url: str) -> BabyPipsSourceAdapter:
    """Create BabyPips source adapter."""
    return BabyPipsSourceAdapter(rss_url)
