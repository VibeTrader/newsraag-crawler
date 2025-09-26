# crawler/adapters/fxstreet_adapter.py
"""
Adapter to integrate existing FXStreet crawler with new template system.
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


class FXStreetArticleDiscovery(IArticleDiscovery):
    """Adapter for FXStreet article discovery using existing crawler."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialize_fxstreet_crawler()
    
    def _initialize_fxstreet_crawler(self):
        """Initialize existing FXStreet crawler."""
        try:
            from crawler.fxstreet import FXStreetCrawler
            self.fxstreet_crawler = FXStreetCrawler(self.config.rss_url)
            print(f"FXStreet crawler initialized for {self.config.name}")
        except Exception as e:
            print(f"Failed to initialize FXStreet crawler: {e}")
            self.fxstreet_crawler = None
    
    async def discover_articles(self) -> AsyncGenerator[ArticleMetadata, None]:
        """Discover articles using existing FXStreet RSS parsing logic."""
        if not self.fxstreet_crawler:
            print("FXStreet crawler not available")
            return
        
        try:
            # Use existing FXStreet method to get URL data
            url_data_list = await self.fxstreet_crawler._get_urls_to_crawl()
            
            print(f"FXStreet discovered {len(url_data_list)} articles")
            
            articles_yielded = 0
            max_articles = self.config.max_articles_per_run
            
            for url_data in url_data_list:
                if articles_yielded >= max_articles:
                    break
                
                try:
                    article_meta = self._convert_fxstreet_data(url_data)
                    if article_meta:
                        articles_yielded += 1
                        yield article_meta
                        
                except Exception as e:
                    print(f"Failed to convert FXStreet data to metadata: {e}")
                    continue
            
            print(f"FXStreet yielded {articles_yielded} articles")
            
        except Exception as e:
            print(f"FXStreet discovery failed: {e}")
            raise
    
    def _convert_fxstreet_data(self, url_data) -> Optional[ArticleMetadata]:
        """Convert FXStreet URL data to ArticleMetadata."""
        try:
            # Assuming similar format to BabyPips
            url, title, pub_date, creator, category = url_data
            
            article_id = hashlib.md5(f"fxstreet:{title}:{url}".encode()).hexdigest()
            
            return ArticleMetadata(
                title=title.strip(),
                url=url.strip(),
                published_date=pub_date if isinstance(pub_date, datetime) else datetime.now(timezone.utc),
                source_name="fxstreet",
                article_id=article_id,
                author=creator,
                category=category,
                language="en"
            )
            
        except Exception as e:
            print(f"Failed to convert FXStreet data: {e}")
            return None


class FXStreetContentExtractor(IContentExtractor):
    """Adapter for FXStreet content extraction using existing crawler."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialize_fxstreet_crawler()
    
    def _initialize_fxstreet_crawler(self):
        """Initialize existing FXStreet crawler."""
        try:
            from crawler.fxstreet import FXStreetCrawler
            self.fxstreet_crawler = FXStreetCrawler(self.config.rss_url)
        except Exception as e:
            print(f"Failed to initialize FXStreet crawler: {e}")
            self.fxstreet_crawler = None
    
    async def extract_content(self, article_meta: ArticleMetadata) -> ProcessingResult:
        """Extract content using existing FXStreet extraction logic."""
        if not self.fxstreet_crawler:
            return ProcessingResult(
                success=False,
                error="FXStreet crawler not available"
            )
        
        try:
            print(f"Extracting FXStreet content from: {article_meta.url}")
            
            # Use existing FXStreet crawl_url method
            content = await self.fxstreet_crawler.crawl_url(article_meta.url)
            
            if not content or len(content.strip()) < 100:
                return ProcessingResult(
                    success=False,
                    error="Extracted content is too short or empty"
                )
            
            print(f"FXStreet extracted {len(content)} characters")
            
            return ProcessingResult(
                success=True,
                content=content,
                metadata={
                    'extraction_method': 'fxstreet_crawler',
                    'content_length': len(content),
                    'url': article_meta.url
                }
            )
            
        except Exception as e:
            print(f"FXStreet content extraction failed for {article_meta.url}: {e}")
            return ProcessingResult(
                success=False,
                error=str(e)
            )


class FXStreetSourceAdapter(BaseNewsSourceTemplate):
    """Adapter for existing FXStreet crawler."""
    
    def __init__(self, rss_url: str):
        """Initialize with FXStreet-specific configuration."""
        source_config = SourceConfig(
            name="fxstreet",
            source_type=SourceType.RSS,
            content_type=ContentType.FOREX,
            base_url="https://www.fxstreet.com",
            rss_url=rss_url,
            rate_limit_seconds=1,
            max_articles_per_run=50,
            timeout_seconds=30,
            custom_processing=True
        )
        
        super().__init__(source_config)
        print("FXStreet adapter initialized successfully")
    
    def _create_discovery_service(self) -> IArticleDiscovery:
        return FXStreetArticleDiscovery(self.config)
    
    def _create_extractor_service(self) -> IContentExtractor:
        return FXStreetContentExtractor(self.config)
    
    def _create_processor_service(self):
        return BaseContentProcessor(self.config)
    
    def _create_duplicate_checker(self):
        return BaseDuplicateChecker(self.config)
    
    def _create_storage_service(self):
        return BaseContentStorage(self.config)


def create_fxstreet_adapter(rss_url: str) -> FXStreetSourceAdapter:
    """Create FXStreet source adapter."""
    return FXStreetSourceAdapter(rss_url)
