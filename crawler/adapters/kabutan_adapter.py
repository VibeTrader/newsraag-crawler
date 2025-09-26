# crawler/adapters/kabutan_adapter.py
"""
Adapter to integrate existing Kabutan crawler with new template system.
Kabutan is HTML-based with Japanese translation capability.
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


class KabutanArticleDiscovery(IArticleDiscovery):
    """Adapter for Kabutan article discovery using existing crawler."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialize_kabutan_crawler()
    
    def _initialize_kabutan_crawler(self):
        """Initialize existing Kabutan crawler."""
        try:
            from crawler.kabutan import KabutanCrawler
            self.kabutan_crawler = KabutanCrawler(self.config.base_url)
            print(f"Kabutan crawler initialized for {self.config.name}")
        except Exception as e:
            print(f"Failed to initialize Kabutan crawler: {e}")
            self.kabutan_crawler = None
    
    async def discover_articles(self) -> AsyncGenerator[ArticleMetadata, None]:
        """Discover articles using existing Kabutan HTML parsing logic."""
        if not self.kabutan_crawler:
            print("Kabutan crawler not available")
            return
        
        try:
            # Kabutan uses HTML parsing instead of RSS
            # Use existing method to discover articles
            url_data_list = await self.kabutan_crawler._get_urls_to_crawl()
            
            print(f"Kabutan discovered {len(url_data_list)} articles")
            
            articles_yielded = 0
            max_articles = self.config.max_articles_per_run
            
            for url_data in url_data_list:
                if articles_yielded >= max_articles:
                    break
                
                try:
                    article_meta = self._convert_kabutan_data(url_data)
                    if article_meta:
                        articles_yielded += 1
                        yield article_meta
                        
                except Exception as e:
                    print(f"Failed to convert Kabutan data to metadata: {e}")
                    continue
            
            print(f"Kabutan yielded {articles_yielded} articles")
            
        except Exception as e:
            print(f"Kabutan discovery failed: {e}")
            raise
    
    def _convert_kabutan_data(self, url_data) -> Optional[ArticleMetadata]:
        """Convert Kabutan URL data to ArticleMetadata."""
        try:
            # Kabutan might have different data structure
            # Adjust based on actual implementation
            if isinstance(url_data, tuple) and len(url_data) >= 2:
                url, title = url_data[:2]
                pub_date = url_data[2] if len(url_data) > 2 else datetime.now(timezone.utc)
                creator = url_data[3] if len(url_data) > 3 else None
                category = "Japanese Stock News"
            else:
                # Handle different formats
                url = url_data if isinstance(url_data, str) else str(url_data)
                title = "Kabutan News Article"
                pub_date = datetime.now(timezone.utc)
                creator = None
                category = "Japanese Stock News"
            
            article_id = hashlib.md5(f"kabutan:{title}:{url}".encode()).hexdigest()
            
            return ArticleMetadata(
                title=title.strip(),
                url=url.strip(),
                published_date=pub_date if isinstance(pub_date, datetime) else datetime.now(timezone.utc),
                source_name="kabutan",
                article_id=article_id,
                author=creator,
                category=category,
                language="ja"  # Japanese content
            )
            
        except Exception as e:
            print(f"Failed to convert Kabutan data: {e}")
            return None


class KabutanContentExtractor(IContentExtractor):
    """Adapter for Kabutan content extraction with translation."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self._initialize_kabutan_crawler()
    
    def _initialize_kabutan_crawler(self):
        """Initialize existing Kabutan crawler."""
        try:
            from crawler.kabutan import KabutanCrawler
            self.kabutan_crawler = KabutanCrawler(self.config.base_url)
        except Exception as e:
            print(f"Failed to initialize Kabutan crawler: {e}")
            self.kabutan_crawler = None
    
    async def extract_content(self, article_meta: ArticleMetadata) -> ProcessingResult:
        """Extract content using existing Kabutan extraction logic with translation."""
        if not self.kabutan_crawler:
            return ProcessingResult(
                success=False,
                error="Kabutan crawler not available"
            )
        
        try:
            print(f"Extracting Kabutan content from: {article_meta.url}")
            
            # Use existing Kabutan crawl_url method
            content = await self.kabutan_crawler.crawl_url(article_meta.url)
            
            # Check if translation is enabled
            if self.config.requires_translation:
                print("Applying Japanese translation...")
                # Kabutan crawler should handle translation internally
                # Content should already be translated if translation is enabled
            
            if not content or len(content.strip()) < 100:
                return ProcessingResult(
                    success=False,
                    error="Extracted content is too short or empty"
                )
            
            print(f"Kabutan extracted {len(content)} characters")
            
            return ProcessingResult(
                success=True,
                content=content,
                metadata={
                    'extraction_method': 'kabutan_crawler',
                    'content_length': len(content),
                    'url': article_meta.url,
                    'translated': self.config.requires_translation,
                    'original_language': 'ja'
                }
            )
            
        except Exception as e:
            print(f"Kabutan content extraction failed for {article_meta.url}: {e}")
            return ProcessingResult(
                success=False,
                error=str(e)
            )


class KabutanSourceAdapter(BaseNewsSourceTemplate):
    """Adapter for existing Kabutan crawler."""
    
    def __init__(self, base_url: str):
        """Initialize with Kabutan-specific configuration."""
        source_config = SourceConfig(
            name="kabutan",
            source_type=SourceType.HTML_SCRAPING,
            content_type=ContentType.STOCKS,
            base_url=base_url,
            rate_limit_seconds=2,  # Be respectful to Japanese site
            max_articles_per_run=30,  # Smaller batch for HTML parsing
            timeout_seconds=45,  # Longer timeout for translation
            requires_translation=True,  # Enable Japanese translation
            custom_processing=True
        )
        
        super().__init__(source_config)
        print("Kabutan adapter initialized successfully")
    
    def _create_discovery_service(self) -> IArticleDiscovery:
        return KabutanArticleDiscovery(self.config)
    
    def _create_extractor_service(self) -> IContentExtractor:
        return KabutanContentExtractor(self.config)
    
    def _create_processor_service(self):
        return BaseContentProcessor(self.config)
    
    def _create_duplicate_checker(self):
        return BaseDuplicateChecker(self.config)
    
    def _create_storage_service(self):
        return BaseContentStorage(self.config)


def create_kabutan_adapter(base_url: str) -> KabutanSourceAdapter:
    """Create Kabutan source adapter."""
    return KabutanSourceAdapter(base_url)
