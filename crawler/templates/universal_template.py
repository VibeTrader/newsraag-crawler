"""
Universal template that works with all source types using the extractor registry.
This is Open-Closed: add new extractors to registry without modifying this class.
"""

from typing import Dict, Any, List, Optional
import asyncio
import time
from loguru import logger
from ..templates.base_template import BaseNewsSourceTemplate
from ..interfaces.news_source_interface import (
    IArticleDiscovery, IContentExtractor, IContentProcessor, 
    IDuplicateChecker, IContentStorage, SourceConfig, ArticleMetadata
)
from ..extractors.article_discovery import create_article_discovery
from ..extractors.content_extractors import create_content_extractor


class UniversalTemplate(BaseNewsSourceTemplate):
    """
    Universal template that handles all source types through registry pattern.
    Following Open-Closed Principle: extensible without modification.
    """
    
    def _create_discovery_service(self) -> IArticleDiscovery:
        """Create discovery service based on source type."""
        config_dict = {
            'name': self.config.name,
            'url': self.config.base_url or self.config.rss_url,
            'selectors': getattr(self.config, 'selectors', {}),
        }
        return create_article_discovery(self.config.source_type.value, config_dict)
    
    def _create_extractor_service(self) -> IContentExtractor:
        """Create extractor service based on source type."""
        # For YouTube, use the specialized content extractor
        if self.config.source_type.value == 'youtube':
            from crawler.extractors.youtube_content_extractor import BaseContentExtractor
            return BaseContentExtractor(self.config)
        
        # For other sources, use the factory
        config_dict = {
            'name': self.config.name,
            'url': self.config.base_url or self.config.rss_url,
            'selectors': getattr(self.config, 'selectors', {}),
        }
        return create_content_extractor(self.config.source_type.value, config_dict)
    
    def _create_processor_service(self) -> IContentProcessor:
        """Create processor service - reuse existing implementation."""
        from ..templates.base_template import BaseContentProcessor
        return BaseContentProcessor(self.config)
    
    def _create_duplicate_checker(self) -> IDuplicateChecker:
        """Create duplicate checker - reuse existing implementation."""
        from ..templates.base_template import BaseDuplicateChecker
        return BaseDuplicateChecker(self.config)
    
    def _create_storage_service(self) -> IContentStorage:
        """Create storage service - reuse existing implementation."""
        from ..templates.base_template import BaseContentStorage
        return BaseContentStorage(self.config)
    
    async def fetch_articles(self, max_articles: Optional[int] = None) -> List[ArticleMetadata]:
        """
        Fetch articles using the discovery service.
        For Twitter/YouTube, articles already have content from discovery phase.
        """
        max_articles = max_articles or self.config.max_articles_per_run
        logger.info(f"Fetching articles from {self.config.name} (max: {max_articles})")
        
        try:
            # Use discovery service (which calls TwitterExtractor or YouTubeExtractor)
            import aiohttp
            async with aiohttp.ClientSession() as session:
                articles = await self._discovery_service.discover_articles(session, max_articles)
            
            if articles:
                logger.success(f"✅ Discovered {len(articles)} articles from {self.config.name}")
            else:
                logger.warning(f"⚠️ No articles discovered from {self.config.name}")
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching articles from {self.config.name}: {e}")
            return []
    
    async def _perform_health_check(self) -> bool:
        """
        Health check for UniversalTemplate.
        Simply checks if we can create the discovery service successfully.
        """
        try:
            # For Twitter/YouTube, just verify the discovery service was created
            if self._discovery_service:
                logger.info(f"✅ Health check passed for {self.config.name}")
                return True
            logger.warning(f"⚠️ Health check failed: discovery service not initialized for {self.config.name}")
            return False
        except Exception as e:
            logger.error(f"Health check failed for {self.config.name}: {e}")
            return False
    
    async def process_articles(self) -> Dict[str, Any]:
        """
        Process articles for UniversalTemplate (Twitter/YouTube).
        Overrides base template to handle list-based discovery instead of async generators.
        """
        start_time = time.time()
        stats = {
            'source_name': self.config.name,
            'articles_discovered': 0,
            'articles_processed': 0,
            'articles_failed': 0,
            'articles_skipped': 0,
            'processing_time': 0,
            'errors': []
        }
        
        try:
            logger.info(f"Starting article processing for {self.config.name}")
            
            # Get all articles at once (not async generator)
            articles = await self.fetch_articles()
            stats['articles_discovered'] = len(articles)
            
            if not articles:
                logger.warning(f"No articles discovered from {self.config.name}")
                stats['processing_time'] = time.time() - start_time
                return stats
            
            # Get services
            extractor_service = self.get_extractor_service()
            processor_service = self.get_processor_service()
            duplicate_checker = self.get_duplicate_checker()
            storage_service = self.get_storage_service()
            
            # Process each article
            last_request_time = 0
            for article_meta in articles:
                try:
                    # Rate limiting
                    current_time = time.time()
                    time_since_last = current_time - last_request_time
                    if time_since_last < self.config.rate_limit_seconds:
                        sleep_time = self.config.rate_limit_seconds - time_since_last
                        await asyncio.sleep(sleep_time)
                    
                    last_request_time = time.time()
                    
                    # Check for duplicates
                    if await duplicate_checker.is_duplicate(article_meta):
                        logger.info(f"Skipping duplicate: {article_meta.title[:50]}...")
                        stats['articles_skipped'] += 1
                        continue
                    
                    # Extract content (transcript for YouTube)
                    extraction_result = await extractor_service.extract_content(article_meta)
                    if not extraction_result.success:
                        logger.error(f"Content extraction failed: {extraction_result.error}")
                        stats['articles_failed'] += 1
                        continue
                    
                    # Process content (LLM cleaning)
                    processing_result = await processor_service.process_content(
                        extraction_result.content,
                        article_meta
                    )
                    if not processing_result.success:
                        logger.error(f"Content processing failed: {processing_result.error}")
                        stats['articles_failed'] += 1
                        continue
                    
                    # Store processed content
                    storage_success = await storage_service.store_content(
                        processing_result.content,  # ✅ Store cleaned transcript
                        article_meta
                    )
                    
                    if storage_success:
                        stats['articles_processed'] += 1
                        logger.success(f"✅ Processed: {article_meta.title[:50]}...")
                    else:
                        stats['articles_failed'] += 1
                        logger.error(f"❌ Storage failed: {article_meta.title[:50]}...")
                    
                except Exception as e:
                    stats['articles_failed'] += 1
                    logger.error(f"Error processing article: {e}")
                    stats['errors'].append(str(e))
            
            stats['processing_time'] = time.time() - start_time
            return stats
            
        except Exception as e:
            logger.error(f"Critical error processing {self.config.name}: {e}")
            import traceback
            traceback.print_exc()
            stats['errors'].append(f"Critical error: {str(e)}")
            stats['processing_time'] = time.time() - start_time
            return stats


# Factory function for the source factory
def create_universal_source(config: SourceConfig):
    """Create universal source that works with any type."""
    return UniversalTemplate(config)
