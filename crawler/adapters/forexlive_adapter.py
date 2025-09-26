# crawler/adapters/forexlive_adapter.py
"""
Adapter to integrate existing ForexLive crawler with new template system.
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


class ForexLiveArticleDiscovery(IArticleDiscovery):
    """Adapter for ForexLive article discovery using existing crawler."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialize_forexlive_crawler()
    
    def _initialize_forexlive_crawler(self):
        """Initialize existing ForexLive crawler."""
        try:
            from crawler.forexlive import ForexLiveCrawler
            self.forexlive_crawler = ForexLiveCrawler(self.config.rss_url)
            print(f"ForexLive crawler initialized for {self.config.name}")
        except Exception as e:
            print(f"Failed to initialize ForexLive crawler: {e}")
            self.forexlive_crawler = None
    
    async def discover_articles(self) -> AsyncGenerator[ArticleMetadata, None]:
        """Discover articles using existing ForexLive RSS parsing logic."""
        if not self.forexlive_crawler:
            print("ForexLive crawler not available")
            return
        
        try:
            # Use existing ForexLive method to get URL data
            url_data_list = await self.forexlive_crawler._get_urls_to_crawl()
            
            print(f"ForexLive discovered {len(url_data_list)} articles")
            
            articles_yielded = 0
            max_articles = self.config.max_articles_per_run
            
            for url_data in url_data_list:
                if articles_yielded >= max_articles:
                    break
                
                try:
                    article_meta = self._convert_forexlive_data(url_data)
                    if article_meta:
                        articles_yielded += 1
                        yield article_meta
                        
                except Exception as e:
                    print(f"Failed to convert ForexLive data to metadata: {e}")
                    continue
            
            print(f"ForexLive yielded {articles_yielded} articles")
            
        except Exception as e:
            print(f"ForexLive discovery failed: {e}")
            raise
    
    def _convert_forexlive_data(self, url_data) -> Optional[ArticleMetadata]:
        """Convert ForexLive URL data to ArticleMetadata."""
        try:
            url, title, pub_date, creator, category = url_data
            
            article_id = hashlib.md5(f"forexlive:{title}:{url}".encode()).hexdigest()
            
            return ArticleMetadata(
                title=title.strip(),
                url=url.strip(),
                published_date=pub_date if isinstance(pub_date, datetime) else datetime.now(timezone.utc),
                source_name="forexlive",
                article_id=article_id,
                author=creator,
                category=category,
                language="en"
            )
            
        except Exception as e:
            print(f"Failed to convert ForexLive data: {e}")
            return None


class ForexLiveContentExtractor(IContentExtractor):
    """Adapter for ForexLive content extraction using existing crawler."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialize_forexlive_crawler()
    
    def _initialize_forexlive_crawler(self):
        """Initialize existing ForexLive crawler."""
        try:
            from crawler.forexlive import ForexLiveCrawler
            self.forexlive_crawler = ForexLiveCrawler(self.config.rss_url)
        except Exception as e:
            print(f"Failed to initialize ForexLive crawler: {e}")
            self.forexlive_crawler = None
    
    async def extract_content(self, article_meta: ArticleMetadata) -> ProcessingResult:
        """Extract content using existing ForexLive extraction logic."""
        if not self.forexlive_crawler:
            return ProcessingResult(
                success=False,
                error="ForexLive crawler not available"
            )
        
        try:
            print(f"Extracting ForexLive content from: {article_meta.url}")
            
            # Use existing ForexLive crawl_url method
            content = await self.forexlive_crawler.crawl_url(article_meta.url)
            
            if not content or len(content.strip()) < 100:
                return ProcessingResult(
                    success=False,
                    error="Extracted content is too short or empty"
                )
            
            print(f"ForexLive extracted {len(content)} characters")
            
            return ProcessingResult(
                success=True,
                content=content,
                metadata={
                    'extraction_method': 'forexlive_crawler',
                    'content_length': len(content),
                    'url': article_meta.url
                }
            )
            
        except Exception as e:
            print(f"ForexLive content extraction failed for {article_meta.url}: {e}")
            return ProcessingResult(
                success=False,
                error=str(e)
            )


class ForexLiveSourceAdapter(BaseNewsSourceTemplate):
    """Adapter for existing ForexLive crawler."""
    
    def __init__(self, rss_url: str):
        """Initialize with ForexLive-specific configuration."""
        source_config = SourceConfig(
            name="forexlive",
            source_type=SourceType.RSS,
            content_type=ContentType.FOREX,
            base_url="https://www.forexlive.com",
            rss_url=rss_url,
            rate_limit_seconds=1,
            max_articles_per_run=50,
            timeout_seconds=30,
            custom_processing=True
        )
        
        super().__init__(source_config)
        print("ForexLive adapter initialized successfully")
    
    def _create_discovery_service(self) -> IArticleDiscovery:
        return ForexLiveArticleDiscovery(self.config)
    
    def _create_extractor_service(self) -> IContentExtractor:
        return ForexLiveContentExtractor(self.config)
    
    def _create_processor_service(self):
        return BaseContentProcessor(self.config)
    
    def _create_duplicate_checker(self):
        return BaseDuplicateChecker(self.config)
    
    def _create_storage_service(self):
        return BaseContentStorage(self.config)


def create_forexlive_adapter(rss_url: str) -> ForexLiveSourceAdapter:
    """Create ForexLive source adapter."""
    return ForexLiveSourceAdapter(rss_url)
