"""
Shared test configuration and fixtures for NewsRaag Crawler tests.

This module provides common fixtures, mocks, and utilities used across all test modules.
"""
import os
import sys
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import project modules for testing (with error handling for missing modules)
try:
    from crawler.utils.config_loader import load_sources_config
except ImportError:
    load_sources_config = None

try:
    from monitoring.metrics import Metrics
except ImportError:
    Metrics = None

try:
    from monitoring.health_check import HealthCheck
except ImportError:
    HealthCheck = None

try:
    from monitoring.duplicate_detector import DuplicateDetector
except ImportError:
    DuplicateDetector = None

try:
    from clients.qdrant_client import QdrantClientWrapper
except ImportError:
    QdrantClientWrapper = None


class TestConfig:
    """Test configuration and constants."""
    
    # Test data paths
    FIXTURES_DIR = Path(__file__).parent / "fixtures"
    RSS_FEEDS_DIR = FIXTURES_DIR / "rss_feeds"
    HTML_CONTENT_DIR = FIXTURES_DIR / "html_content"
    CONFIG_DIR = FIXTURES_DIR / "config"
    
    # Test database settings
    TEST_QDRANT_COLLECTION = "test_collection"
    TEST_REDIS_DB = 15  # Use DB 15 for testing
    
    # Performance thresholds
    MAX_MEMORY_MB = 200
    MAX_PROCESSING_TIME_SECONDS = 5.0
    
    # Test article limits
    MAX_TEST_ARTICLES = 5
    

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return TestConfig()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_rss_entry():
    """Provide a sample RSS entry for testing."""
    return {
        'title': 'Test Financial Article',
        'link': 'https://example.com/test-article',
        'summary': 'This is a test summary for financial news.',
        'published_parsed': (2024, 1, 15, 12, 0, 0, 0, 15, 0),
        'id': 'test-article-123',
        'tags': [{'term': 'forex'}, {'term': 'trading'}]
    }


@pytest.fixture  
def sample_source_config():
    """Provide a sample source configuration."""
    return {
        'name': 'test_source',
        'type': 'rss',
        'rss_url': 'https://example.com/rss.xml',
        'base_url': 'https://example.com',
        'enabled': True,
        'priority': 1,
        'category': 'forex',
        'language': 'en'
    }


@pytest.fixture
def sample_article_content():
    """Provide sample article content for testing."""
    return """
    # Test Article Title
    
    This is a comprehensive test article about financial markets.
    
    ## Market Analysis
    
    The current market conditions show significant volatility in the forex market.
    EUR/USD is trading at 1.0850, showing a 0.5% decline from yesterday's close.
    
    ### Technical Analysis
    
    - Support level: 1.0800
    - Resistance level: 1.0900
    - Moving average: 1.0825
    
    ## Conclusion
    
    Traders should monitor key support and resistance levels closely.
    """


@pytest.fixture
def mock_rss_response():
    """Mock RSS feed response data."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Test Financial News</title>
            <description>Test RSS feed for financial news</description>
            <link>https://example.com</link>
            <item>
                <title>EUR/USD Analysis: Key Levels to Watch</title>
                <link>https://example.com/eur-usd-analysis</link>
                <description>Technical analysis of EUR/USD pair with key support and resistance levels.</description>
                <pubDate>Mon, 15 Jan 2024 12:00:00 GMT</pubDate>
                <guid>eur-usd-analysis-123</guid>
            </item>
            <item>
                <title>Gold Price Forecast: Bullish Momentum Expected</title>
                <link>https://example.com/gold-forecast</link>
                <description>Gold prices are expected to continue bullish momentum based on technical indicators.</description>
                <pubDate>Mon, 15 Jan 2024 10:30:00 GMT</pubDate>
                <guid>gold-forecast-456</guid>
            </item>
        </channel>
    </rss>"""


@pytest.fixture
def mock_html_content():
    """Mock HTML content for web scraping tests."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Financial Article</title>
    </head>
    <body>
        <header>Navigation and ads</header>
        <main>
            <h1>EUR/USD Technical Analysis</h1>
            <div class="article-content">
                <p>The EUR/USD pair is showing interesting patterns today.</p>
                <p>Technical indicators suggest a potential breakout above 1.0900.</p>
                <div class="trading-data">
                    <span>Current Price: 1.0850</span>
                    <span>Change: -0.0050 (-0.46%)</span>
                </div>
                <p>Key levels to watch include support at 1.0800 and resistance at 1.0900.</p>
            </div>
        </main>
        <footer>Footer content and ads</footer>
    </body>
    </html>
    """


@pytest.fixture
def mock_cleaned_content():
    """Mock LLM-cleaned content."""
    return """
    # EUR/USD Technical Analysis

    The EUR/USD pair is showing interesting patterns today with technical indicators suggesting a potential breakout above 1.0900.

    ## Current Market Data
    - Current Price: 1.0850
    - Change: -0.0050 (-0.46%)

    ## Key Technical Levels
    - Support: 1.0800
    - Resistance: 1.0900

    Key levels to watch include support at 1.0800 and resistance at 1.0900.
    """


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for testing."""
    # Create a flexible mock that can handle both sync and async methods
    mock_client = MagicMock()
    
    # Add async methods as AsyncMock
    mock_client.store_document = AsyncMock(return_value=True)
    mock_client.search_similar = AsyncMock(return_value=[])
    mock_client.delete_documents = AsyncMock(return_value={"deleted": 5})
    mock_client.get_collection_info = AsyncMock(return_value={"vectors_count": 100})
    
    # Add sync methods as regular MagicMock
    mock_client.is_connected = MagicMock(return_value=True)
    mock_client.collection_exists = MagicMock(return_value=True)
    
    return mock_client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    try:
        import fakeredis
        return fakeredis.FakeRedis(db=TestConfig.TEST_REDIS_DB)
    except ImportError:
        # Fallback to basic mock if fakeredis not available
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.exists.return_value = False
        return mock_redis


@pytest.fixture
def mock_azure_openai():
    """Mock Azure OpenAI client for testing."""
    mock_client = AsyncMock()
    
    # Mock embeddings response
    mock_embeddings = MagicMock()
    mock_embeddings.data = [MagicMock(embedding=[0.1] * 3072)]
    mock_client.embeddings.create.return_value = mock_embeddings
    
    # Mock chat completion response
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "Cleaned article content"
    mock_client.chat.completions.create.return_value = mock_completion
    
    return mock_client


@pytest.fixture
def mock_crawl4ai():
    """Mock Crawl4AI for testing."""
    with patch('crawler.core.article_processor.AsyncWebCrawler') as mock_crawler:
        mock_instance = AsyncMock()
        mock_result = MagicMock()
        mock_result.markdown.raw_markdown = "Extracted content from web page"
        mock_instance.arun.return_value = mock_result
        mock_crawler.return_value.__aenter__.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_feedparser():
    """Mock feedparser for RSS testing."""
    with patch('feedparser.parse') as mock_parse:
        mock_feed = MagicMock()
        mock_feed.entries = [
            MagicMock(
                title="Test Article 1",
                link="https://example.com/article1",
                summary="Test summary 1",
                published_parsed=(2024, 1, 15, 12, 0, 0, 0, 15, 0),
                id="article-1"
            ),
            MagicMock(
                title="Test Article 2", 
                link="https://example.com/article2",
                summary="Test summary 2",
                published_parsed=(2024, 1, 15, 11, 0, 0, 0, 15, 0),
                id="article-2"
            )
        ]
        mock_parse.return_value = mock_feed
        yield mock_parse


@pytest.fixture
def mock_app_insights():
    """Mock Application Insights for testing."""
    with patch('monitoring.app_insights.get_app_insights') as mock_ai:
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.track_event = MagicMock()
        mock_client.track_metric = MagicMock()
        mock_client.track_trace = MagicMock()
        mock_client.track_exception = MagicMock()
        mock_client.flush = MagicMock()
        mock_ai.return_value = mock_client
        yield mock_client


@pytest.fixture
def metrics_instance(temp_dir):
    """Provide a Metrics instance with temporary storage."""
    if Metrics is None:
        pytest.skip("Metrics class not available")
    with patch('monitoring.metrics.METRICS_DIR', temp_dir):
        metrics = Metrics()
        yield metrics


@pytest.fixture
def health_check_instance():
    """Provide a HealthCheck instance for testing."""
    if HealthCheck is None:
        pytest.skip("HealthCheck class not available")
    return HealthCheck()


@pytest.fixture
def duplicate_detector_instance():
    """Provide a DuplicateDetector instance for testing."""
    if DuplicateDetector is None:
        pytest.skip("DuplicateDetector class not available")
    return DuplicateDetector()


@pytest.fixture
def mock_environment_variables():
    """Mock environment variables for testing."""
    test_env_vars = {
        'QDRANT_URL': 'http://localhost:6333',
        'QDRANT_API_KEY': 'test-api-key',
        'OPENAI_API_KEY': 'test-openai-key',
        'AZURE_OPENAI_DEPLOYMENT': 'test-deployment',
        'AZ_ACCOUNT_NAME': 'teststorage',
        'AZ_ACCOUNT_KEY': 'test-storage-key',
        'REDIS_HOST': 'localhost',
        'REDIS_PASSWORD': 'test-password',
        'APPINSIGHTS_INSTRUMENTATIONKEY': 'test-insights-key',
        'ALERT_SLACK_WEBHOOK': 'https://hooks.slack.com/test',
        'ALERT_SLACK_ENABLED': 'true'
    }
    
    with patch.dict(os.environ, test_env_vars):
        yield test_env_vars


# Performance testing utilities
@pytest.fixture
def memory_profiler():
    """Provide memory profiling utilities."""
    import psutil
    process = psutil.Process(os.getpid())
    
    def get_memory_usage():
        return process.memory_info().rss / 1024 / 1024  # MB
    
    return get_memory_usage


# Test data generation utilities
class ArticleFactory:
    """Factory for generating test articles."""
    
    @staticmethod
    def create_article(title: str = None, content: str = None, url: str = None) -> Dict[str, Any]:
        """Create a test article with default or provided values."""
        return {
            'title': title or f"Test Article {datetime.now().isoformat()}",
            'content': content or "Test article content with financial analysis.",
            'url': url or f"https://example.com/article-{datetime.now().timestamp()}",
            'published_date': datetime.now().isoformat(),
            'source': 'test_source',
            'category': 'forex',
            'language': 'en',
            'metadata': {
                'word_count': len((content or "test content").split()),
                'reading_time': 2
            }
        }
    
    @staticmethod
    def create_articles(count: int = 3) -> List[Dict[str, Any]]:
        """Create multiple test articles."""
        return [ArticleFactory.create_article(title=f"Test Article {i+1}") 
                for i in range(count)]


@pytest.fixture
def article_factory():
    """Provide article factory for test data generation."""
    return ArticleFactory()


# Async testing utilities
@pytest.fixture
def async_context_manager():
    """Provide utilities for testing async context managers."""
    class AsyncContextManager:
        def __init__(self, return_value=None):
            self.return_value = return_value
            
        async def __aenter__(self):
            return self.return_value or MagicMock()
            
        async def __aebxit__(self, exc_type, exc_val, exc_tb):
            pass
    
    return AsyncContextManager
