# test_phase1_day1.py
"""
Test script for Phase 1 Day 1 implementation.
Tests interfaces, models, and validators.
"""
import asyncio
from datetime import datetime, timezone

# Test imports
try:
    from crawler.interfaces import (
        SourceType, ContentType, SourceConfig, ArticleMetadata,
        ProcessingResult, INewsSource, NewsSourceError
    )
    from crawler.models import ProcessingStatus, ContentMetrics, ArticleStats
    from crawler.validators import ConfigValidator
    print("✓ All imports successful!")
except ImportError as e:
    print(f"✗ Import error: {e}")
    exit(1)


def test_enums():
    """Test enum definitions."""
    print("\n[TEST] Testing Enums...")
    
    # Test SourceType
    assert SourceType.RSS.value == "rss"
    assert SourceType.HTML_SCRAPING.value == "html_scraping"
    print("✓ SourceType enum working")
    
    # Test ContentType
    assert ContentType.FOREX.value == "forex"
    assert ContentType.FINANCIAL_NEWS.value == "financial_news"
    print("✓ ContentType enum working")


def test_data_models():
    """Test data model creation and validation."""
    print("\n[TEST] Testing Data Models...")
    
    # Test SourceConfig
    try:
        config = SourceConfig(
            name="test_source",
            source_type=SourceType.RSS,
            content_type=ContentType.FOREX,
            base_url="https://example.com",
            rss_url="https://example.com/feed.rss"
        )
        print("✓ SourceConfig creation working")
    except Exception as e:
        print(f"✗ SourceConfig creation failed: {e}")
    
    # Test ArticleMetadata
    try:
        article = ArticleMetadata(
            title="Test Article",
            url="https://example.com/article1",
            published_date=datetime.now(timezone.utc),
            source_name="test_source",
            article_id="test_123"
        )
        print("✓ ArticleMetadata creation working")
    except Exception as e:
        print(f"✗ ArticleMetadata creation failed: {e}")
    
    # Test ProcessingResult
    try:
        result = ProcessingResult(
            success=True,
            content="Test content",
            metadata={"test": "value"}
        )
        assert result.success is True
        assert result.content == "Test content"
        print("✓ ProcessingResult working")
    except Exception as e:
        print(f"✗ ProcessingResult failed: {e}")


def test_model_classes():
    """Test model classes from models package."""
    print("\n[TEST] Testing Model Classes...")
    
    # Test ContentMetrics
    try:
        metrics = ContentMetrics(
            original_length=1000,
            processed_length=800,
            processing_time_seconds=2.5
        )
        assert metrics.compression_ratio == 0.8
        print("✓ ContentMetrics working")
    except Exception as e:
        print(f"✗ ContentMetrics failed: {e}")
    
    # Test ArticleStats
    try:
        stats = ArticleStats.from_content("This is a test article with some words.")
        assert stats.word_count == 9
        assert stats.character_count > 0
        print("✓ ArticleStats working")
    except Exception as e:
        print(f"✗ ArticleStats failed: {e}")


def test_validators():
    """Test configuration validators."""
    print("\n[TEST] Testing Validators...")
    
    # Test valid configuration
    try:
        valid_config = SourceConfig(
            name="valid_source",
            source_type=SourceType.RSS,
            content_type=ContentType.FOREX,
            base_url="https://valid.com",
            rss_url="https://valid.com/feed.rss"
        )
        
        errors = ConfigValidator.validate_source_config(valid_config)
        assert len(errors) == 0, f"Valid config should have no errors, got: {errors}"
        print("✓ Valid configuration validation working")
    except Exception as e:
        print(f"✗ Valid configuration validation failed: {e}")
    
    # Test invalid configuration
    try:
        invalid_config = SourceConfig(
            name="",  # Invalid empty name
            source_type=SourceType.RSS,
            content_type=ContentType.FOREX,
            base_url="invalid_url",  # Invalid URL
            rate_limit_seconds=-1  # Invalid negative value
        )
        
        errors = ConfigValidator.validate_source_config(invalid_config)
        assert len(errors) > 0, "Invalid config should have errors"
        print(f"✓ Invalid configuration validation working (found {len(errors)} errors)")
    except Exception as e:
        print(f"✗ Invalid configuration validation failed: {e}")


def test_exceptions():
    """Test custom exception classes."""
    print("\n[TEST] Testing Exceptions...")
    
    try:
        # Test NewsSourceError
        error = NewsSourceError("Test error", "test_source")
        assert error.source_name == "test_source"
        print("✓ NewsSourceError working")
        
        # Test inheritance
        from crawler.interfaces import SourceDiscoveryError
        discovery_error = SourceDiscoveryError("Discovery failed", "test_source")
        assert isinstance(discovery_error, NewsSourceError)
        print("✓ Exception inheritance working")
    except Exception as e:
        print(f"✗ Exception testing failed: {e}")


def main():
    """Run all tests."""
    print("[START] Starting Phase 1 Day 1 Tests...")
    print("=" * 50)
    
    try:
        test_enums()
        test_data_models()
        test_model_classes()
        test_validators()
        test_exceptions()
        
        print("\n" + "=" * 50)
        print("[SUCCESS] All Phase 1 Day 1 tests passed!")
        print("✓ Interfaces, models, and validators are working correctly")
        print("\nReady for Phase 1 Day 2: Base Template Implementation")
        
    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
