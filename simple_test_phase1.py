# simple_test_phase1.py
"""
Simple test script for Phase 1 Day 1 implementation.
Tests interfaces, models, and validators.
"""
from datetime import datetime, timezone

def test_imports():
    """Test if all imports work."""
    print("Testing imports...")
    try:
        from crawler.interfaces import (
            SourceType, ContentType, SourceConfig, ArticleMetadata,
            ProcessingResult, NewsSourceError
        )
        from crawler.models import ProcessingStatus, ContentMetrics, ArticleStats
        from crawler.validators import ConfigValidator
        print("SUCCESS: All imports working!")
        return True
    except ImportError as e:
        print(f"ERROR: Import failed - {e}")
        return False

def test_basic_functionality():
    """Test basic functionality."""
    print("\nTesting basic functionality...")
    
    from crawler.interfaces import SourceType, ContentType, SourceConfig, ArticleMetadata
    from crawler.validators import ConfigValidator
    
    # Test SourceConfig creation
    try:
        config = SourceConfig(
            name="test_source",
            source_type=SourceType.RSS,
            content_type=ContentType.FOREX,
            base_url="https://example.com",
            rss_url="https://example.com/feed.rss"
        )
        print("SUCCESS: SourceConfig creation works")
    except Exception as e:
        print(f"ERROR: SourceConfig creation failed - {e}")
        return False
    
    # Test ArticleMetadata creation
    try:
        article = ArticleMetadata(
            title="Test Article",
            url="https://example.com/article1",
            published_date=datetime.now(timezone.utc),
            source_name="test_source",
            article_id="test_123"
        )
        print("SUCCESS: ArticleMetadata creation works")
    except Exception as e:
        print(f"ERROR: ArticleMetadata creation failed - {e}")
        return False
    
    # Test config validation
    try:
        errors = ConfigValidator.validate_source_config(config)
        print(f"SUCCESS: Config validation works (found {len(errors)} errors)")
    except Exception as e:
        print(f"ERROR: Config validation failed - {e}")
        return False
    
    return True

def main():
    """Run tests."""
    print("Phase 1 Day 1 - Simple Test")
    print("=" * 40)
    
    success = True
    success &= test_imports()
    success &= test_basic_functionality()
    
    print("\n" + "=" * 40)
    if success:
        print("SUCCESS: All Phase 1 Day 1 tests passed!")
        print("Ready for Phase 1 Day 2!")
    else:
        print("ERROR: Some tests failed!")

if __name__ == "__main__":
    main()
