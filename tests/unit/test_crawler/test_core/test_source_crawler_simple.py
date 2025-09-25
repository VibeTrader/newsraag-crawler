"""
Simple unit tests for source_crawler that match the actual code structure.

Tests the main crawling functionality with proper mocking.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


class TestSourceCrawlerBasic:
    """Basic tests for source_crawler module."""
    
    @pytest.mark.unit
    def test_source_crawler_module_imports(self):
        """Test that source crawler can be imported."""
        try:
            from crawler.core.source_crawler import crawl_source
            assert callable(crawl_source), "crawl_source should be a callable function"
        except ImportError as e:
            pytest.fail(f"Could not import crawl_source: {e}")
    
    @pytest.mark.unit 
    @pytest.mark.asyncio
    async def test_crawl_source_with_invalid_config(self):
        """Test crawl_source handles invalid configuration gracefully."""
        try:
            from crawler.core.source_crawler import crawl_source
        except ImportError:
            pytest.skip("source_crawler module not available")
        
        # Test with empty config
        result = await crawl_source({})
        assert result is not None, "crawl_source should return a result even with empty config"
        assert isinstance(result, tuple), "Result should be a tuple"
        assert len(result) >= 2, "Result should have at least 2 elements (processed, failed)"
    
    @pytest.mark.unit
    @pytest.mark.asyncio  
    async def test_crawl_source_with_minimal_valid_config(self):
        """Test crawl_source with minimal valid configuration."""
        try:
            from crawler.core.source_crawler import crawl_source
        except ImportError:
            pytest.skip("source_crawler module not available")
        
        # Mock dependencies that might not exist
        with patch('crawler.core.source_crawler.get_metrics') as mock_get_metrics, \
             patch('crawler.core.source_crawler.crawl_rss_feed', new_callable=AsyncMock) as mock_crawl_rss:
            
            # Configure mocks
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            mock_crawl_rss.return_value = []  # No articles found
            
            config = {
                'name': 'test_source',
                'type': 'rss', 
                'url': 'https://example.com/feed.rss'
            }
            
            result = await crawl_source(config)
            
            assert result is not None
            assert isinstance(result, tuple)
            assert len(result) >= 2
            
            # Should have called get_metrics
            mock_get_metrics.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_crawl_source_with_rss_articles(self):
        """Test crawl_source processes RSS articles."""
        try:
            from crawler.core.source_crawler import crawl_source
        except ImportError:
            pytest.skip("source_crawler module not available")
        
        # Mock all dependencies
        with patch('crawler.core.source_crawler.get_metrics') as mock_get_metrics, \
             patch('crawler.core.source_crawler.crawl_rss_feed', new_callable=AsyncMock) as mock_crawl_rss, \
             patch('crawler.core.source_crawler.process_article', new_callable=AsyncMock) as mock_process:
            
            # Configure mocks
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            # Mock RSS articles
            mock_articles = [
                {'title': 'Test Article 1', 'link': 'https://example.com/1'},
                {'title': 'Test Article 2', 'link': 'https://example.com/2'}
            ]
            mock_crawl_rss.return_value = mock_articles
            mock_process.return_value = True  # Successful processing
            
            config = {
                'name': 'test_source',
                'type': 'rss',
                'url': 'https://example.com/feed.rss'
            }
            
            result = await crawl_source(config)
            
            assert result is not None
            source_name, processed_count, failed_count = result
            
            assert source_name == 'test_source'
            assert processed_count > 0  # Should have processed articles
            assert failed_count == 0    # No failures
            
            # Verify mocks were called
            mock_crawl_rss.assert_called_once()
            assert mock_process.call_count == len(mock_articles)


class TestSourceCrawlerModules:
    """Test related modules that source_crawler depends on."""
    
    @pytest.mark.unit
    def test_rss_crawler_import(self):
        """Test that RSS crawler can be imported."""
        try:
            from crawler.core.rss_crawler import crawl_rss_feed
            assert callable(crawl_rss_feed)
        except ImportError:
            pytest.skip("rss_crawler module not available yet")
    
    @pytest.mark.unit
    def test_article_processor_import(self):
        """Test that article processor can be imported."""
        try:
            from crawler.core.article_processor import process_article
            assert callable(process_article)
        except ImportError:
            pytest.skip("article_processor module not available yet")
    
    @pytest.mark.unit
    def test_metrics_import(self):
        """Test that metrics can be imported."""
        try:
            from monitoring.metrics import get_metrics
            assert callable(get_metrics)
        except ImportError:
            pytest.skip("metrics module not available yet")


class TestSourceCrawlerErrorHandling:
    """Test error handling in source crawler."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_crawl_source_handles_rss_exception(self):
        """Test that source crawler handles RSS crawling exceptions."""
        try:
            from crawler.core.source_crawler import crawl_source
        except ImportError:
            pytest.skip("source_crawler module not available")
        
        with patch('crawler.core.source_crawler.get_metrics') as mock_get_metrics, \
             patch('crawler.core.source_crawler.crawl_rss_feed', new_callable=AsyncMock) as mock_crawl_rss:
            
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            # Simulate RSS crawling failure
            mock_crawl_rss.side_effect = Exception("RSS feed not accessible")
            
            config = {
                'name': 'test_source',
                'type': 'rss',
                'url': 'https://invalid-feed.com/feed.rss'
            }
            
            # Should not raise exception, should handle gracefully
            result = await crawl_source(config)
            
            assert result is not None
            source_name, processed_count, failed_count = result
            assert source_name == 'test_source'
            # Should have some failure indication
            assert processed_count == 0 or failed_count > 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_crawl_source_handles_processing_exception(self):
        """Test that source crawler handles article processing exceptions."""
        try:
            from crawler.core.source_crawler import crawl_source
        except ImportError:
            pytest.skip("source_crawler module not available")
        
        with patch('crawler.core.source_crawler.get_metrics') as mock_get_metrics, \
             patch('crawler.core.source_crawler.crawl_rss_feed', new_callable=AsyncMock) as mock_crawl_rss, \
             patch('crawler.core.source_crawler.process_article', new_callable=AsyncMock) as mock_process:
            
            mock_metrics = MagicMock()
            mock_get_metrics.return_value = mock_metrics
            
            # Mock successful RSS crawling but failed processing
            mock_articles = [{'title': 'Test Article', 'link': 'https://example.com/1'}]
            mock_crawl_rss.return_value = mock_articles
            mock_process.side_effect = Exception("Processing failed")
            
            config = {
                'name': 'test_source',
                'type': 'rss',
                'url': 'https://example.com/feed.rss'
            }
            
            result = await crawl_source(config)
            
            assert result is not None
            source_name, processed_count, failed_count = result
            assert source_name == 'test_source'
            # Should indicate processing failure
            assert failed_count > 0
