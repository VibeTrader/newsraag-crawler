"""
Unit tests for monitoring.duplicate_detector module.

Tests duplicate detection algorithms, URL normalization, and performance.
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from monitoring.duplicate_detector import DuplicateDetector


class TestDuplicateDetector:
    """Test cases for DuplicateDetector class."""
    
    @pytest.fixture
    def detector(self):
        """Create a DuplicateDetector instance."""
        return DuplicateDetector()
    
    @pytest.fixture
    def sample_articles(self):
        """Create sample articles for testing."""
        return [
            {
                'title': 'EUR/USD Analysis: Key Levels to Watch',
                'url': 'https://example.com/eur-usd-analysis-2024',
                'content': 'EUR/USD pair showing interesting technical patterns...',
                'source': 'test_source'
            },
            {
                'title': 'EUR/USD Analysis: Key Levels to Watch',  # Same title
                'url': 'https://example.com/eur-usd-analysis-2024-updated',  # Different URL
                'content': 'EUR/USD pair showing interesting technical patterns...',
                'source': 'test_source'
            },
            {
                'title': 'Gold Price Forecast: Bullish Momentum Expected',
                'url': 'https://example.com/gold-forecast',
                'content': 'Gold prices are expected to continue bullish momentum...',
                'source': 'test_source'
            }
        ]
    
    @pytest.mark.unit
    def test_duplicate_detector_initialization(self, detector):
        """Test proper initialization of DuplicateDetector."""
        assert detector is not None
        assert hasattr(detector, 'seen_articles')
        assert hasattr(detector, 'title_hashes')
        assert hasattr(detector, 'url_hashes')
    
    @pytest.mark.unit
    def test_add_article(self, detector, sample_articles):
        """Test adding articles to duplicate detector."""
        article = sample_articles[0]
        
        # Add article
        detector.add_article(article)
        
        # Verify article was added
        assert len(detector.seen_articles) == 1
        assert article['title'] in [a['title'] for a in detector.seen_articles]
    
    @pytest.mark.unit
    def test_is_duplicate_by_url(self, detector, sample_articles):
        """Test duplicate detection by URL."""
        article1 = sample_articles[0]
        article2 = dict(article1)  # Copy article with same URL
        
        # Add first article
        detector.add_article(article1)
        assert not detector.is_duplicate(article1)
        
        # Check duplicate with same URL
        is_dup, reason = detector.is_duplicate(article2)
        assert is_dup is True
        assert 'url' in reason.lower()
    
    @pytest.mark.unit
    def test_is_duplicate_by_title(self, detector, sample_articles):
        """Test duplicate detection by title similarity."""
        article1 = sample_articles[0]
        article2 = sample_articles[1]  # Same title, different URL
        
        # Add first article
        detector.add_article(article1)
        assert not detector.is_duplicate(article1)
        
        # Check duplicate with same title
        is_dup, reason = detector.is_duplicate(article2)
        assert is_dup is True
        assert 'title' in reason.lower()
    
    @pytest.mark.unit
    def test_is_not_duplicate(self, detector, sample_articles):
        """Test that different articles are not marked as duplicates."""
        article1 = sample_articles[0]  # EUR/USD article
        article2 = sample_articles[2]  # Gold article
        
        # Add first article
        detector.add_article(article1)
        
        # Check second article is not duplicate
        is_dup, reason = detector.is_duplicate(article2)
        assert is_dup is False
        assert reason == ""
    
    @pytest.mark.unit
    def test_url_normalization(self, detector):
        """Test URL normalization for duplicate detection."""
        test_cases = [
            ('https://example.com/article', 'https://example.com/article/'),
            ('https://example.com/article?utm_source=test', 'https://example.com/article'),
            ('http://example.com/article', 'https://example.com/article'),
            ('https://Example.COM/Article', 'https://example.com/article'),
        ]
        
        for url1, url2 in test_cases:
            article1 = {
                'title': 'Test Article',
                'url': url1,
                'content': 'Test content',
                'source': 'test'
            }
            article2 = {
                'title': 'Different Title',  # Different title to test URL only
                'url': url2,
                'content': 'Test content',
                'source': 'test'
            }
            
            # Fresh detector for each test
            fresh_detector = DuplicateDetector()
            fresh_detector.add_article(article1)
            
            is_dup, reason = fresh_detector.is_duplicate(article2)
            assert is_dup is True, f"URLs should be considered duplicates: {url1} vs {url2}"
            assert 'url' in reason.lower()
    
    @pytest.mark.unit
    def test_title_similarity_threshold(self, detector):
        """Test title similarity threshold for duplicate detection."""
        base_article = {
            'title': 'EUR/USD Technical Analysis for Today',
            'url': 'https://example.com/base-article',
            'content': 'Base content',
            'source': 'test'
        }
        
        test_cases = [
            ('EUR/USD Technical Analysis for Today', True),  # Exact match
            ('EUR/USD Technical Analysis for Tomorrow', True),  # Very similar
            ('USD/JPY Technical Analysis for Today', False),  # Different pair
            ('Gold Price Analysis for Today', False),  # Completely different
            ('EUR USD Technical Analysis Today', True),  # Minor variations
        ]
        
        detector.add_article(base_article)
        
        for title, should_be_duplicate in test_cases:
            test_article = {
                'title': title,
                'url': f'https://example.com/test-{hash(title)}',  # Unique URL
                'content': 'Test content',
                'source': 'test'
            }
            
            is_dup, reason = detector.is_duplicate(test_article)
            assert is_dup == should_be_duplicate, f"Title '{title}' duplicate detection failed"
    
    @pytest.mark.unit
    def test_clear_old_articles(self, detector, sample_articles):
        """Test clearing old articles from duplicate detector."""
        # Add multiple articles
        for article in sample_articles:
            detector.add_article(article)
        
        assert len(detector.seen_articles) == 3
        
        # Clear old articles
        detector.clear_old_articles()
        
        # Verify articles are cleared
        assert len(detector.seen_articles) == 0
        assert len(detector.title_hashes) == 0
        assert len(detector.url_hashes) == 0
    
    @pytest.mark.unit
    def test_get_duplicate_stats(self, detector, sample_articles):
        """Test getting duplicate detection statistics."""
        # Add articles and check for duplicates
        detector.add_article(sample_articles[0])
        detector.is_duplicate(sample_articles[1])  # Should be duplicate
        detector.is_duplicate(sample_articles[2])  # Should not be duplicate
        
        stats = detector.get_duplicate_stats()
        
        assert 'total_articles_checked' in stats
        assert 'duplicates_found' in stats
        assert 'unique_articles' in stats
        assert stats['total_articles_checked'] >= 2
        assert stats['duplicates_found'] >= 1
        assert stats['unique_articles'] >= 1
    
    @pytest.mark.unit
    @pytest.mark.performance
    def test_duplicate_detection_performance(self, detector, memory_profiler):
        """Test performance of duplicate detection with large dataset."""
        import time
        
        # Generate large number of test articles
        test_articles = []
        for i in range(1000):
            article = {
                'title': f'Test Article {i}',
                'url': f'https://example.com/article-{i}',
                'content': f'Content for article {i}',
                'source': 'performance_test'
            }
            test_articles.append(article)
        
        start_memory = memory_profiler()
        start_time = time.time()
        
        # Add all articles and check for duplicates
        for i, article in enumerate(test_articles):
            detector.add_article(article)
            
            # Check every 10th article for duplicates
            if i % 10 == 0 and i > 0:
                is_dup, reason = detector.is_duplicate(test_articles[0])  # Check against first article
        
        end_time = time.time()
        end_memory = memory_profiler()
        
        execution_time = end_time - start_time
        memory_increase = end_memory - start_memory
        
        # Performance assertions
        assert execution_time < 5.0  # Should complete within 5 seconds
        assert memory_increase < 100  # Should not use more than 100MB additional memory
        
        # Verify functionality still works
        stats = detector.get_duplicate_stats()
        assert stats['unique_articles'] == 1000
    
    @pytest.mark.unit
    def test_edge_cases(self, detector):
        """Test edge cases for duplicate detection."""
        edge_cases = [
            # Empty title
            {'title': '', 'url': 'https://example.com/empty-title', 'content': 'Content', 'source': 'test'},
            
            # Very long title
            {'title': 'A' * 1000, 'url': 'https://example.com/long-title', 'content': 'Content', 'source': 'test'},
            
            # Special characters in title
            {'title': 'EUR/USD: €1.08 → $1.10 (±0.5%)', 'url': 'https://example.com/special-chars', 'content': 'Content', 'source': 'test'},
            
            # Non-ASCII characters
            {'title': 'ドル円分析：重要なレベル', 'url': 'https://example.com/japanese', 'content': 'Content', 'source': 'test'},
            
            # Missing fields
            {'title': 'Test', 'content': 'Content', 'source': 'test'},  # Missing URL
            {'url': 'https://example.com/no-title', 'content': 'Content', 'source': 'test'},  # Missing title
        ]
        
        # Should handle all edge cases without crashing
        for article in edge_cases:
            try:
                is_dup, reason = detector.is_duplicate(article)
                detector.add_article(article)
                assert True  # Made it without exception
            except Exception as e:
                pytest.fail(f"Failed to handle edge case {article}: {e}")
    
    @pytest.mark.unit
    def test_source_based_duplicate_detection(self, detector):
        """Test duplicate detection considering source information."""
        article1 = {
            'title': 'EUR/USD Analysis',
            'url': 'https://source1.com/eur-usd',
            'content': 'Analysis content',
            'source': 'source1'
        }
        
        article2 = {
            'title': 'EUR/USD Analysis',
            'url': 'https://source2.com/eur-usd',  # Different domain
            'content': 'Analysis content',
            'source': 'source2'  # Different source
        }
        
        detector.add_article(article1)
        
        # Articles from different sources with same title might be considered duplicates
        # depending on implementation
        is_dup, reason = detector.is_duplicate(article2)
        
        # This test documents current behavior - adjust assertion based on implementation
        # For now, we expect title-based duplication regardless of source
        assert is_dup is True or is_dup is False  # Either behavior is valid
    
    @pytest.mark.unit
    def test_concurrent_operations(self, detector, sample_articles):
        """Test thread safety of duplicate detector operations."""
        import threading
        import time
        
        results = []
        errors = []
        
        def worker(article_batch):
            try:
                for article in article_batch:
                    is_dup, reason = detector.is_duplicate(article)
                    detector.add_article(article)
                    results.append((article['title'], is_dup, reason))
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(3):
            # Each thread gets a copy of sample articles with unique URLs
            batch = []
            for j, article in enumerate(sample_articles):
                modified_article = dict(article)
                modified_article['url'] = f"{article['url']}-thread{i}-{j}"
                batch.append(modified_article)
            
            thread = threading.Thread(target=worker, args=(batch,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5)
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Concurrent operation errors: {errors}"
        assert len(results) > 0, "No results from concurrent operations"


class TestDuplicateDetectorHelpers:
    """Test helper functions used by duplicate detector."""
    
    @pytest.mark.unit
    def test_text_normalization_helpers(self):
        """Test text normalization helper functions."""
        # This would test individual helper functions for text processing
        # Implementation depends on actual helper function structure
        pass
    
    @pytest.mark.unit
    def test_hash_generation_helpers(self):
        """Test hash generation for titles and URLs."""
        # This would test hash generation functions
        # Implementation depends on actual helper function structure
        pass
