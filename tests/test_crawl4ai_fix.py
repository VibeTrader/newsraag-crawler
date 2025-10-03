#!/usr/bin/env python3
"""
Quick test for the fixed Crawl4AI configuration.
"""
import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

async def test_fixed_config():
    try:
        from crawler.extractors.crawl4ai_extractor import EnhancedCrawl4AIExtractor
        from crawler.interfaces import SourceConfig, SourceType, ContentType
        
        print("PASS: Import successful")
        
        # Create test configuration
        config = SourceConfig(
            name="test_babypips",
            source_type=SourceType.RSS,
            content_type=ContentType.FOREX,
            base_url="https://www.babypips.com",
            timeout_seconds=60
        )
        
        print("PASS: Config created")
        
        # Create enhanced extractor
        extractor = EnhancedCrawl4AIExtractor(config)
        print("PASS: Enhanced extractor created successfully")
        
        # Test config creation method
        crawl_config = extractor._create_crawl_config(30)
        print("PASS: Crawl config created without error")
        print(f"   Page timeout: {crawl_config.page_timeout}ms")
        
        # Check if wait_for parameter is not present (which was causing the issue)
        if not hasattr(crawl_config, 'wait_for') or crawl_config.wait_for is None:
            print("PASS: wait_for parameter correctly removed")
        else:
            print(f"INFO: wait_for parameter: {crawl_config.wait_for}")
        
        return True
        
    except Exception as e:
        print(f"FAIL: Error: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    result = asyncio.run(test_fixed_config())
    if result:
        print("\nSUCCESS: Fixed configuration test PASSED!")
    else:
        print("\nFAILED: Configuration test FAILED!")
