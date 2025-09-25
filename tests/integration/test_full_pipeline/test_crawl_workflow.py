"""
Integration tests for the complete crawling pipeline.

Tests end-to-end workflow from RSS discovery to data storage.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import tempfile
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from crawler.core.source_crawler import crawl_source


class TestFullCrawlPipeline:
    """Integration tests for complete crawl pipeline."""
    
    @pytest.fixture
    def integration_source_config(self):
        """Source configuration for integration testing."""
        return {
            'name': 'integration_test_source',
            'type': 'rss',
            'rss_url': 'https://feeds.example.com/test.xml',
            'base_url': 'https://example.com',
            'enabled': True,
            'priority': 1,
            'category': 'forex',
            'language': 'en'
        }
    
    @pytest.fixture
    def mock_rss_response(self):
        """Mock RSS response for integration testing."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Integration Test Feed</title>
                <item>
                    <title>EUR/USD Integration Test Analysis</title>
                    <link>https://example.com/integration-test-article</link>
                    <description>Integration test article for EUR/USD analysis</description>
                    <pubDate>Mon, 15 Jan 2024 12:00:00 GMT</pubDate>
                    <guid>integration-test-123</guid>
                </item>
            </channel>
        </rss>"""
    
    @pytest.fixture
    def mock_web_content(self):
        """Mock web page content for testing."""
        return """
        <html>
        <head><title>EUR/USD Integration Test Analysis</title></head>
        <body>
            <h1>EUR/USD Integration Test Analysis</h1>
            <p>This is integration test content for EUR/USD analysis.</p>
            <div class="trading-info">
                <span>Current Price: 1.0850</span>
                <span>Support: 1.0800</span>
                <span>Resistance: 1.0900</span>
            </div>
            <p>Technical indicators suggest potential breakout.</p>
        </body>
        </html>
        """
    
    @pytest.fixture
    def mock_cleaned_content(self):
        """Mock LLM-cleaned content."""
        return """# EUR/USD Integration Test Analysis

This is integration test content for EUR/USD analysis.

## Trading Information
- Current Price: 1.0850
- Support: 1.0800  
- Resistance: 1.0900

Technical indicators suggest potential breakout."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_crawl_pipeline(self, integration_source_config, mock_rss_response, 
                                          mock_web_content, mock_cleaned_content, temp_dir):
        """Test complete crawl pipeline from RSS to storage."""
        
        # Storage for pipeline results
        stored_articles = []
        generated_embeddings = []
        app_insights_events = []
        
        def mock_store_document(doc_id, content, metadata, embedding):
            stored_articles.append({
                'id': doc_id,
                'content': content,
                'metadata': metadata,
                'embedding': embedding
            })
            return True
        
        def mock_create_embedding(text):
            embedding = [0.1] * 3072  # Mock 3072-dimension embedding
            generated_embeddings.append(text)
            return embedding
        
        def mock_clean_content(content):
            return mock_cleaned_content
        
        def mock_track_event(event_name, properties=None):
            app_insights_events.append({'event': event_name, 'properties': properties or {}})
        
        # Setup comprehensive mocks
        with patch('requests.get') as mock_requests, \
             patch('feedparser.parse') as mock_feedparser, \
             patch('crawler.core.article_processor.AsyncWebCrawler') as mock_crawler, \
             patch('utils.llm.cleaner.clean_article_content', side_effect=mock_clean_content), \
             patch('utils.llm.embeddings.create_embeddings', side_effect=mock_create_embedding), \
             patch('clients.qdrant_client.QdrantClientWrapper') as mock_qdrant_class, \
             patch('monitoring.app_insights.get_app_insights') as mock_ai, \
             patch('monitoring.duplicate_detector.get_duplicate_detector') as mock_dup_detector, \
             patch('monitoring.metrics.get_metrics') as mock_metrics:
            
            # Configure RSS mock
            mock_feed = MagicMock()
            mock_feed.entries = [
                MagicMock(
                    title="EUR/USD Integration Test Analysis",
                    link="https://example.com/integration-test-article", 
                    summary="Integration test article for EUR/USD analysis",
                    published_parsed=(2024, 1, 15, 12, 0, 0, 0, 15, 0),
                    id="integration-test-123"
                )
            ]
            mock_feedparser.return_value = mock_feed
            
            # Configure web crawler mock
            mock_crawler_instance = AsyncMock()
            mock_result = MagicMock()
            mock_result.markdown.raw_markdown = mock_web_content
            mock_crawler_instance.arun.return_value = mock_result
            mock_crawler.return_value.__aenter__.return_value = mock_crawler_instance
            
            # Configure Qdrant mock
            mock_qdrant_instance = MagicMock()
            mock_qdrant_instance.store_document.side_effect = mock_store_document
            mock_qdrant_class.return_value = mock_qdrant_instance
            
            # Configure Application Insights mock
            mock_ai_instance = MagicMock()
            mock_ai_instance.enabled = True
            mock_ai_instance.track_event.side_effect = mock_track_event
            mock_ai_instance.track_articles_discovered = MagicMock()
            mock_ai_instance.track_articles_processed = MagicMock()
            mock_ai.return_value = mock_ai_instance
            
            # Configure duplicate detector mock
            mock_detector = MagicMock()
            mock_detector.is_duplicate.return_value = (False, "")
            mock_detector.add_article = MagicMock()
            mock_dup_detector.return_value = mock_detector
            
            # Configure metrics mock
            mock_metrics_instance = MagicMock()
            mock_metrics_instance.record_article_processed = MagicMock()
            mock_metrics.return_value = mock_metrics_instance
            
            # Execute the complete pipeline
            result = await crawl_source(integration_source_config)
            
            # Verify pipeline results
            assert result is not None
            source_name, processed_count, failed_count = result
            
            # Verify successful processing
            assert source_name == "integration_test_source"
            assert processed_count == 1
            assert failed_count == 0
            
            # Verify RSS parsing was called
            mock_feedparser.assert_called_once()
            
            # Verify web crawling was performed
            mock_crawler_instance.arun.assert_called_once_with(
                "https://example.com/integration-test-article"
            )
            
            # Verify article was stored in Qdrant
            assert len(stored_articles) == 1
            stored_article = stored_articles[0]
            assert stored_article['content'] == mock_cleaned_content
            assert len(stored_article['embedding']) == 3072
            assert 'title' in stored_article['metadata']
            assert stored_article['metadata']['title'] == "EUR/USD Integration Test Analysis"
            
            # Verify embedding generation
            assert len(generated_embeddings) == 1
            assert generated_embeddings[0] == mock_cleaned_content
            
            # Verify duplicate detection was performed
            mock_detector.is_duplicate.assert_called_once()
            mock_detector.add_article.assert_called_once()
            
            # Verify Application Insights tracking
            mock_ai_instance.track_articles_discovered.assert_called_once()
            mock_ai_instance.track_articles_processed.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_with_duplicate_articles(self, integration_source_config, 
                                                   mock_rss_response, mock_web_content):
        """Test pipeline behavior with duplicate articles."""
        
        duplicate_detection_calls = []
        stored_articles = []
        
        def mock_is_duplicate(article):
            duplicate_detection_calls.append(article['title'])
            # Mark second article as duplicate
            return len(duplicate_detection_calls) > 1, "duplicate_title"
        
        def mock_store_document(doc_id, content, metadata, embedding):
            stored_articles.append({'id': doc_id, 'metadata': metadata})
            return True
        
        with patch('feedparser.parse') as mock_feedparser, \
             patch('crawler.core.article_processor.AsyncWebCrawler') as mock_crawler, \
             patch('utils.llm.cleaner.clean_article_content', return_value="Cleaned content"), \
             patch('utils.llm.embeddings.create_embeddings', return_value=[0.1] * 3072), \
             patch('clients.qdrant_client.QdrantClientWrapper') as mock_qdrant_class, \
             patch('monitoring.app_insights.get_app_insights') as mock_ai, \
             patch('monitoring.duplicate_detector.get_duplicate_detector') as mock_dup_detector:
            
            # Configure feed with multiple articles (some duplicates)
            mock_feed = MagicMock()
            mock_feed.entries = [
                MagicMock(title="Article 1", link="https://example.com/1", id="1"),
                MagicMock(title="Article 2", link="https://example.com/2", id="2"),  # Will be duplicate
                MagicMock(title="Article 3", link="https://example.com/3", id="3"),  # Will be duplicate
            ]
            mock_feedparser.return_value = mock_feed
            
            # Configure crawler
            mock_crawler_instance = AsyncMock()
            mock_result = MagicMock()
            mock_result.markdown.raw_markdown = "Test content"
            mock_crawler_instance.arun.return_value = mock_result
            mock_crawler.return_value.__aenter__.return_value = mock_crawler_instance
            
            # Configure duplicate detector
            mock_detector = MagicMock()
            mock_detector.is_duplicate.side_effect = mock_is_duplicate
            mock_dup_detector.return_value = mock_detector
            
            # Configure Qdrant
            mock_qdrant_instance = MagicMock()
            mock_qdrant_instance.store_document.side_effect = mock_store_document
            mock_qdrant_class.return_value = mock_qdrant_instance
            
            # Configure App Insights
            mock_ai_instance = MagicMock()
            mock_ai_instance.enabled = True
            mock_ai.return_value = mock_ai_instance
            
            # Execute pipeline
            result = await crawl_source(integration_source_config)
            
            # Verify results
            source_name, processed_count, failed_count = result
            assert processed_count == 1  # Only first article processed
            assert failed_count == 0
            
            # Verify duplicate detection was called for all articles
            assert len(duplicate_detection_calls) == 3
            
            # Verify only one article was stored (first one)
            assert len(stored_articles) == 1
            
            # Verify duplicates were tracked
            mock_ai_instance.track_duplicates_detected.assert_called()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, integration_source_config):
        """Test pipeline error handling and recovery."""
        
        error_log = []
        processed_articles = []
        
        def mock_process_with_errors(article_url):
            if "error" in article_url:
                error_log.append(f"Failed to process: {article_url}")
                raise Exception(f"Processing failed for {article_url}")
            else:
                processed_articles.append(article_url)
                return "Successfully processed"
        
        with patch('feedparser.parse') as mock_feedparser, \
             patch('crawler.core.article_processor.process_article', 
                   side_effect=lambda article: mock_process_with_errors(article.get('link', ''))), \
             patch('monitoring.app_insights.get_app_insights') as mock_ai, \
             patch('monitoring.duplicate_detector.get_duplicate_detector') as mock_dup_detector:
            
            # Configure feed with mix of good and problematic articles
            mock_feed = MagicMock()
            mock_feed.entries = [
                MagicMock(title="Good Article 1", link="https://example.com/good1", id="good1"),
                MagicMock(title="Error Article", link="https://example.com/error", id="error"),
                MagicMock(title="Good Article 2", link="https://example.com/good2", id="good2"),
            ]
            mock_feedparser.return_value = mock_feed
            
            # Configure mocks
            mock_detector = MagicMock()
            mock_detector.is_duplicate.return_value = (False, "")
            mock_dup_detector.return_value = mock_detector
            
            mock_ai_instance = MagicMock()
            mock_ai_instance.enabled = True
            mock_ai.return_value = mock_ai_instance
            
            # Execute pipeline
            result = await crawl_source(integration_source_config)
            
            # Verify error handling
            source_name, processed_count, failed_count = result
            assert processed_count == 2  # Two good articles
            assert failed_count == 1     # One failed article
            
            # Verify error was logged
            assert len(error_log) == 1
            assert "error" in error_log[0]
            
            # Verify good articles were processed
            assert len(processed_articles) == 2
            assert "good1" in str(processed_articles)
            assert "good2" in str(processed_articles)
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_pipeline_performance_with_multiple_articles(self, integration_source_config, memory_profiler):
        """Test pipeline performance with multiple articles."""
        import time
        
        processing_times = []
        memory_usage = []
        
        def mock_process_with_timing(article):
            start_time = time.time()
            # Simulate processing time
            import asyncio
            asyncio.sleep(0.1)  # 100ms processing time
            end_time = time.time()
            processing_times.append(end_time - start_time)
            memory_usage.append(memory_profiler())
            return True
        
        with patch('feedparser.parse') as mock_feedparser, \
             patch('crawler.core.source_crawler.process_article', 
                   new_callable=AsyncMock, side_effect=mock_process_with_timing), \
             patch('clients.qdrant_client.QdrantClientWrapper') as mock_qdrant, \
             patch('monitoring.app_insights.get_app_insights') as mock_ai, \
             patch('monitoring.duplicate_detector.get_duplicate_detector') as mock_dup_detector:
            
            # Configure feed with many articles
            articles_count = 20
            mock_feed = MagicMock()
            mock_feed.entries = [
                MagicMock(
                    title=f"Performance Test Article {i}",
                    link=f"https://example.com/perf-test-{i}",
                    id=f"perf-{i}"
                ) for i in range(articles_count)
            ]
            mock_feedparser.return_value = mock_feed
            
            # Configure mocks
            mock_detector = MagicMock()
            mock_detector.is_duplicate.return_value = (False, "")
            mock_dup_detector.return_value = mock_detector
            
            mock_qdrant_instance = MagicMock()
            mock_qdrant_instance.store_document.return_value = True
            mock_qdrant.return_value = mock_qdrant_instance
            
            mock_ai_instance = MagicMock()
            mock_ai_instance.enabled = True
            mock_ai.return_value = mock_ai_instance
            
            # Measure performance
            start_memory = memory_profiler()
            start_time = time.time()
            
            # Execute pipeline
            result = await crawl_source(integration_source_config)
            
            end_time = time.time()
            end_memory = memory_profiler()
            
            # Verify performance
            total_time = end_time - start_time
            memory_increase = end_memory - start_memory
            
            # Performance assertions
            assert total_time < 30.0  # Should complete within 30 seconds
            assert memory_increase < 200  # Should not use more than 200MB additional memory
            
            # Verify all articles were processed
            source_name, processed_count, failed_count = result
            assert processed_count == articles_count
            assert failed_count == 0
            
            # Verify processing times are reasonable
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            assert avg_processing_time < 2.0  # Average less than 2 seconds per article


class TestPipelineComponentIntegration:
    """Test integration between specific pipeline components."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_rss_to_web_crawler_integration(self, mock_rss_response, mock_web_content):
        """Test integration between RSS parsing and web crawling."""
        
        crawled_urls = []
        
        def mock_crawl_url(url):
            crawled_urls.append(url)
            return mock_web_content
        
        with patch('feedparser.parse') as mock_feedparser, \
             patch('crawler.core.article_processor.AsyncWebCrawler') as mock_crawler:
            
            # Configure RSS feed
            mock_feed = MagicMock()
            mock_feed.entries = [
                MagicMock(
                    title="Test Article",
                    link="https://example.com/test-article",
                    summary="Test summary",
                    id="test-123"
                )
            ]
            mock_feedparser.return_value = mock_feed
            
            # Configure web crawler
            mock_crawler_instance = AsyncMock()
            mock_result = MagicMock()
            mock_result.markdown.raw_markdown = mock_web_content
            mock_crawler_instance.arun.return_value = mock_result
            mock_crawler.return_value.__aenter__.return_value = mock_crawler_instance
            
            # Test integration point
            from crawler.core.rss_crawler import discover_articles
            from crawler.core.article_processor import extract_full_content
            
            # Discover articles from RSS
            articles = await discover_articles("https://test-feed.com/rss")
            assert len(articles) == 1
            assert articles[0]['link'] == "https://example.com/test-article"
            
            # Extract full content
            full_content = await extract_full_content(articles[0]['link'])
            assert full_content == mock_web_content
            
            # Verify integration
            mock_crawler_instance.arun.assert_called_once_with("https://example.com/test-article")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_content_processing_to_storage_integration(self, mock_cleaned_content, temp_dir):
        """Test integration between content processing and storage."""
        
        stored_documents = []
        
        def mock_store_document(doc_id, content, metadata, embedding):
            stored_documents.append({
                'id': doc_id,
                'content': content,
                'metadata': metadata,
                'embedding': embedding[:5]  # Store only first 5 values for testing
            })
            return True
        
        with patch('utils.llm.cleaner.clean_article_content', return_value=mock_cleaned_content), \
             patch('utils.llm.embeddings.create_embeddings', return_value=[0.1] * 3072), \
             patch('clients.qdrant_client.QdrantClientWrapper') as mock_qdrant:
            
            # Configure storage mock
            mock_qdrant_instance = MagicMock()
            mock_qdrant_instance.store_document.side_effect = mock_store_document
            mock_qdrant.return_value = mock_qdrant_instance
            
            # Test integration
            from crawler.core.article_processor import process_and_store_article
            
            test_article = {
                'title': 'Integration Test Article',
                'content': 'Raw article content with ads and navigation',
                'url': 'https://example.com/integration-test',
                'source': 'integration_test'
            }
            
            # Process and store
            success = await process_and_store_article(test_article)
            
            assert success is True
            assert len(stored_documents) == 1
            
            stored_doc = stored_documents[0]
            assert stored_doc['content'] == mock_cleaned_content
            assert len(stored_doc['embedding']) == 5  # First 5 values
            assert stored_doc['metadata']['title'] == 'Integration Test Article'
            assert stored_doc['metadata']['source'] == 'integration_test'
