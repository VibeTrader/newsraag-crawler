# crawler/adapters/poundsterlinglive_adapter.py
"""
Adapter to integrate existing PoundSterlingLive crawler with new template system.
PoundSterlingLive is HTML-based financial news source.
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


class PoundSterlingLiveArticleDiscovery(IArticleDiscovery):
    """Adapter for PoundSterlingLive article discovery using existing crawler."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialize_poundsterlinglive_crawler()
    
    def _initialize_poundsterlinglive_crawler(self):
        """Initialize existing PoundSterlingLive crawler."""
        try:
            from crawler.poundsterlinglive import PoundSterlingLiveCrawler
            self.psl_crawler = PoundSterlingLiveCrawler(self.config.base_url)
            print(f"PoundSterlingLive crawler initialized for {self.config.name}")
        except Exception as e:
            print(f"Failed to initialize PoundSterlingLive crawler: {e}")
            self.psl_crawler = None
    
    async def discover_articles(self) -> AsyncGenerator[ArticleMetadata, None]:
        """Discover articles using existing PoundSterlingLive HTML parsing logic."""
        if not self.psl_crawler:
            print("PoundSterlingLive crawler not available")
            return
        
        try:
            # PoundSterlingLive uses HTML parsing
            url_data_list = await self.psl_crawler._get_urls_to_crawl()
            
            print(f"PoundSterlingLive discovered {len(url_data_list)} articles")
            
            articles_yielded = 0
            max_articles = self.config.max_articles_per_run
            
            for url_data in url_data_list:
                if articles_yielded >= max_articles:
                    break
                
                try:
                    article_meta = self._convert_psl_data(url_data)
                    if article_meta:
                        articles_yielded += 1
                        yield article_meta
                        
                except Exception as e:
                    print(f"Failed to convert PoundSterlingLive data to metadata: {e}")
                    continue
            
            print(f"PoundSterlingLive yielded {articles_yielded} articles")
            
        except Exception as e:
            print(f"PoundSterlingLive discovery failed: {e}")
            raise
    
    def _convert_psl_data(self, url_data) -> Optional[ArticleMetadata]:
        """Convert PoundSterlingLive URL data to ArticleMetadata."""
        try:
            # Handle different data formats from PoundSterlingLive
            if isinstance(url_data, tuple) and len(url_data) >= 2:
                url, title = url_data[:2]
                pub_date = url_data[2] if len(url_data) > 2 else datetime.now(timezone.utc)
                creator = url_data[3] if len(url_data) > 3 else None
                category = "GBP/Forex News"
            else:
                url = url_data if isinstance(url_data, str) else str(url_data)
                title = "PoundSterlingLive News Article"
                pub_date = datetime.now(timezone.utc)
                creator = None
                category = "GBP/Forex News"
            
            article_id = hashlib.md5(f"poundsterlinglive:{title}:{url}".encode()).hexdigest()
            
            return ArticleMetadata(
                title=title.strip(),
                url=url.strip(),
                published_date=pub_date if isinstance(pub_date, datetime) else datetime.now(timezone.utc),
                source_name="poundsterlinglive",
                article_id=article_id,
                author=creator,
                category=category,
                language="en"
            )
            
        except Exception as e:
            print(f"Failed to convert PoundSterlingLive data: {e}")
            return None


class PoundSterlingLiveContentExtractor(IContentExtractor):
    """Adapter for PoundSterlingLive content extraction."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialize_poundsterlinglive_crawler()
    
    def _initialize_poundsterlinglive_crawler(self):
        """Initialize existing PoundSterlingLive crawler."""
        try:
            from crawler.poundsterlinglive import PoundSterlingLiveCrawler
            self.psl_crawler = PoundSterlingLiveCrawler(self.config.base_url)
        except Exception as e:
            print(f"Failed to initialize PoundSterlingLive crawler: {e}")
            self.psl_crawler = None
    
    async def extract_content(self, article_meta: ArticleMetadata) -> ProcessingResult:
        """Extract content using existing PoundSterlingLive extraction logic."""
        if not self.psl_crawler:
            return ProcessingResult(
                success=False,
                error="PoundSterlingLive crawler not available"
            )
        
        try:
            print(f"Extracting PoundSterlingLive content from: {article_meta.url}")
            
            # Use existing PoundSterlingLive crawl_url method
            content = await self.psl_crawler.crawl_url(article_meta.url)
            
            if not content or len(content.strip()) < 100:
                return ProcessingResult(
                    success=False,
                    error="Extracted content is too short or empty"
                )
            
            print(f"PoundSterlingLive extracted {len(content)} characters")
            
            return ProcessingResult(
                success=True,
                content=content,
                metadata={
                    'extraction_method': 'poundsterlinglive_crawler',
                    'content_length': len(content),
                    'url': article_meta.url,
                    'source_type': 'html_scraping'
                }
            )
            
        except Exception as e:
            print(f"PoundSterlingLive content extraction failed for {article_meta.url}: {e}")
            return ProcessingResult(
                success=False,
                error=str(e)
            )


class PoundSterlingLiveSourceAdapter(BaseNewsSourceTemplate):
    """Adapter for existing PoundSterlingLive crawler."""
    
    def __init__(self, base_url: str):
        """Initialize with PoundSterlingLive-specific configuration."""
        source_config = SourceConfig(
            name="poundsterlinglive",
            source_type=SourceType.HTML_SCRAPING,
            content_type=ContentType.FOREX,
            base_url=base_url,
            rate_limit_seconds=2,  # Respectful rate limiting
            max_articles_per_run=40,
            timeout_seconds=30,
            custom_processing=True
        )
        
        super().__init__(source_config)
        print("PoundSterlingLive adapter initialized successfully")
    
    def _create_discovery_service(self) -> IArticleDiscovery:
        return PoundSterlingLiveArticleDiscovery(self.config)
    
    def _create_extractor_service(self) -> IContentExtractor:
        return PoundSterlingLiveContentExtractor(self.config)
    
    def _create_processor_service(self):
        return BaseContentProcessor(self.config)
    
    def _create_duplicate_checker(self):
        return BaseDuplicateChecker(self.config)
    
    def _create_storage_service(self):
        return BaseContentStorage(self.config)


def create_poundsterlinglive_adapter(base_url: str) -> PoundSterlingLiveSourceAdapter:
    """Create PoundSterlingLive source adapter."""
    return PoundSterlingLiveSourceAdapter(base_url)
