"""
Unit tests for crawler.core.source_crawler module.

Tests the main crawling functionality including RSS parsing, 
article processing, and error handling.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from crawler.core.source_crawler import crawl_source


class TestSourceCrawler:
    """Test cases for source_crawler module."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_crawl_source_success(self, sample_source_config, mock_feedparser, 
                                       mock_qdrant_client, mock_app_insights):
        """Test successful source crawling with RSS feed."""
        
        # Setup mocks
        with patch('crawler.core.source_crawler.get_qdrant_client', return_value=mock_qdrant_client), \
             patch('crawler.core.source_crawler.get_app_insights', return_value=mock_app_insights), \
             patch('crawler.core.source_crawler.get_duplicate_detector') as mock_dup_detector, \
             patch('crawler.core.source_crawler.process_article', new_callable=AsyncMock) as mock_process:
            
            # Configure mocks
            mock_detector_instance = MagicMock()
            mock_detector_instance.is_duplicate.return_value = False
            mock_detector_instance.add_article.return_value = None
            mock_dup_detector.return_value = mock_detector_instance
            
            mock_process.return_value = True
            
            # Execute test
            result = await crawl_source(sample_source_config)
            
            # Verify results
            assert result is not None
            source_name, processed_count, failed_count = result
            assert source_name == "test_source"
            assert processed_count > 0
            assert failed_count == 0
            
            # Verify mock calls
            mock_feedparser.assert_called_once()
            mock_process.assert_called()
            mock_qdrant_client.store_document.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_crawl_source_rss_parsing_failure(self, sample_source_config, mock_app_insights):
        """Test handling of RSS parsing failures."""
        
        with patch('crawler.core.source_crawler.get_app_insights', return_value=mock_app_insights), \
             patch('feedparser.parse') as mock_parse:
            
            # Simulate RSS parsing failure
            mock_parse.side_effect = Exception("RSS parsing failed")
            
            # Execute test
            result = await crawl_source(sample_source_config)
            
            # Verify error handling
            assert result is not None
            source_name, processed_count, failed_count = result
            assert source_name == "test_source"
            assert processed_count == 0
            assert failed_count >= 1
    
    @pytest.mark.unit
    @pytest.mark.asyncio 
    async def test_crawl_source_duplicate_detection(self, sample_source_config, mock_feedparser,
                                                   mock_qdrant_client, mock_app_insights):
        """Test duplicate article detection during crawling."""
        
        with patch('crawler.core.source_crawler.get_qdrant_client', return_value=mock_qdrant_client), \
             patch('crawler.core.source_crawler.get_app_insights', return_value=mock_app_insights), \
             patch('crawler.core.source_crawler.get_duplicate_detector') as mock_dup_detector, \
             patch('crawler.core.source_crawler.process_article', new_callable=AsyncMock) as mock_process:
            
            # Configure duplicate detector to mark first article as duplicate
            mock_detector_instance = MagicMock()
            mock_detector_instance.is_duplicate.side_effect = [True, False]  # First is duplicate, second is not
            mock_detector_instance.add_article.return_value = None
            mock_dup_detector.return_value = mock_detector_instance
            
            mock_process.return_value = True
            
            # Execute test
            result = await crawl_source(sample_source_config)
            
            # Verify results - should skip duplicate
            assert result is not None
            source_name, processed_count, failed_count = result
            assert source_name == "test_source"
            
            # Verify duplicate detection was called
            mock_detector_instance.is_duplicate.assert_called()
            
            # Verify App Insights tracked duplicates
            mock_app_insights.track_duplicates_detected.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_crawl_source_article_processing_failure(self, sample_source_config, mock_feedparser,
                                                          mock_qdrant_client, mock_app_insights):
        """Test handling of article processing failures."""
        
        with patch('crawler.core.source_crawler.get_qdrant_client', return_value=mock_qdrant_client), \
             patch('crawler.core.source_crawler.get_app_insights', return_value=mock_app_insights), \
             patch('crawler.core.source_crawler.get_duplicate_detector') as mock_dup_detector, \
             patch('crawler.core.source_crawler.process_article', new_callable=AsyncMock) as mock_process:
            
            # Configure mocks
            mock_detector_instance = MagicMock()
            mock_detector_instance.is_duplicate.return_value = False
            mock_dup_detector.return_value = mock_detector_instance
            
            # Simulate article processing failure
            mock_process.side_effect = Exception("Processing failed")
            
            # Execute test
            result = await crawl_source(sample_source_config)
            
            # Verify error handling
            assert result is not None
            source_name, processed_count, failed_count = result
            assert source_name == "test_source"
            assert failed_count > 0
            
            # Verify App Insights tracked failures
            mock_app_insights.track_articles_processed.assert_called()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_crawl_source_empty_rss_feed(self, sample_source_config, mock_app_insights):
        """Test handling of empty RSS feeds."""
        
        with patch('crawler.core.source_crawler.get_app_insights', return_value=mock_app_insights), \
             patch('feedparser.parse') as mock_parse:
            
            # Create empty feed
            mock_feed = MagicMock()
            mock_feed.entries = []
            mock_parse.return_value = mock_feed
            
            # Execute test
            result = await crawl_source(sample_source_config)
            
            # Verify handling of empty feed
            assert result is not None
            source_name, processed_count, failed_count = result
            assert source_name == "test_source"
            assert processed_count == 0
            assert failed_count == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_crawl_source_invalid_config(self, mock_app_insights):
        """Test handling of invalid source configuration."""
        
        invalid_config = {}  # Missing required fields
        
        with patch('crawler.core.source_crawler.get_app_insights', return_value=mock_app_insights):
            
            # Execute test - should handle gracefully
            result = await crawl_source(invalid_config)
            
            # Verify error handling
            assert result is not None
            source_name, processed_count, failed_count = result
            assert failed_count > 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_crawl_source_qdrant_connection_failure(self, sample_source_config, mock_feedparser,
                                                         mock_app_insights):
        """Test handling of Qdrant connection failures."""
        
        with patch('crawler.core.source_crawler.get_qdrant_client') as mock_qdrant_getter, \
             patch('crawler.core.source_crawler.get_app_insights', return_value=mock_app_insights), \
             patch('crawler.core.source_crawler.get_duplicate_detector') as mock_dup_detector:
            
            # Simulate Qdrant connection failure
            mock_qdrant_getter.side_effect = Exception("Qdrant connection failed")
            
            mock_detector_instance = MagicMock()
            mock_detector_instance.is_duplicate.return_value = False
            mock_dup_detector.return_value = mock_detector_instance
            
            # Execute test
            result = await crawl_source(sample_source_config)
            
            # Verify graceful degradation
            assert result is not None
            source_name, processed_count, failed_count = result
            assert source_name == "test_source"
            # Should still attempt to process but fail on storage
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_crawl_source_performance(self, sample_source_config, mock_feedparser,
                                           mock_qdrant_client, mock_app_insights, memory_profiler):
        """Test source crawling performance and memory usage."""
        
        import time
        
        with patch('crawler.core.source_crawler.get_qdrant_client', return_value=mock_qdrant_client), \
             patch('crawler.core.source_crawler.get_app_insights', return_value=mock_app_insights), \
             patch('crawler.core.source_crawler.get_duplicate_detector') as mock_dup_detector, \
             patch('crawler.core.source_crawler.process_article', new_callable=AsyncMock) as mock_process:
            
            # Setup for performance test
            mock_detector_instance = MagicMock()
            mock_detector_instance.is_duplicate.return_value = False
            mock_dup_detector.return_value = mock_detector_instance
            mock_process.return_value = True
            
            # Measure performance
            start_memory = memory_profiler()
            start_time = time.time()
            
            # Execute test
            result = await crawl_source(sample_source_config)
            
            # Measure results
            end_time = time.time()
            end_memory = memory_profiler()
            
            # Verify performance constraints
            execution_time = end_time - start_time
            memory_increase = end_memory - start_memory
            
            assert execution_time < 10.0  # Should complete within 10 seconds
            assert memory_increase < 50  # Should not use more than 50MB additional memory
            
            # Verify successful execution
            assert result is not None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_crawl_source_with_app_insights_disabled(self, sample_source_config, mock_feedparser,
                                                          mock_qdrant_client):
        """Test crawling behavior when App Insights is disabled."""
        
        with patch('crawler.core.source_crawler.get_qdrant_client', return_value=mock_qdrant_client), \
             patch('crawler.core.source_crawler.get_app_insights') as mock_ai_getter, \
             patch('crawler.core.source_crawler.get_duplicate_detector') as mock_dup_detector, \
             patch('crawler.core.source_crawler.process_article', new_callable=AsyncMock) as mock_process:
            
            # Configure disabled App Insights
            mock_ai = MagicMock()
            mock_ai.enabled = False
            mock_ai_getter.return_value = mock_ai
            
            mock_detector_instance = MagicMock()
            mock_detector_instance.is_duplicate.return_value = False
            mock_dup_detector.return_value = mock_detector_instance
            mock_process.return_value = True
            
            # Execute test
            result = await crawl_source(sample_source_config)
            
            # Verify successful execution even without App Insights
            assert result is not None
            source_name, processed_count, failed_count = result
            assert source_name == "test_source"
            
            # Verify App Insights methods were not called
            mock_ai.track_articles_discovered.assert_not_called()
            mock_ai.track_articles_processed.assert_not_called()


class TestSourceCrawlerHelpers:
    """Test helper functions used by source crawler."""
    
    @pytest.mark.unit
    def test_source_config_validation(self, sample_source_config):
        """Test validation of source configuration."""
        # This would test helper functions that validate source config
        # Implementation depends on actual helper function structure
        pass
    
    @pytest.mark.unit 
    @pytest.mark.asyncio
    async def test_article_url_normalization(self):
        """Test URL normalization for articles."""
        # This would test URL normalization functions
        # Implementation depends on actual helper function structure
        pass
