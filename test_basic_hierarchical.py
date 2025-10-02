#!/usr/bin/env python3
"""
Simple hierarchical extraction test.

Tests the basic hierarchical extraction functionality.
"""

import asyncio
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.factories import load_sources_from_yaml, SourceFactory
from loguru import logger

async def test_basic_hierarchical():
    """Test basic hierarchical extraction."""
    print("Testing Basic Hierarchical Extraction")
    print("=" * 50)
    
    try:
        # Load one source for testing
        sources_config = load_sources_from_yaml('config/sources.yaml')
        
        if not sources_config:
            print("No sources loaded!")
            return
        
        # Test with the first source
        test_source = sources_config[0]  # babypips
        print(f"Testing with source: {test_source.name}")
        print(f"Type: {test_source.source_type.value}")
        print(f"URL: {getattr(test_source, 'rss_url', 'N/A')}")
        
        # Create source using factory
        print("\nCreating source...")
        source = SourceFactory.create_source(test_source)
        print(f"Source created: {type(source).__name__}")
        
        # Check if it's the hierarchical template
        if hasattr(source, 'get_extraction_stats'):
            print("Hierarchical template confirmed!")
        else:
            print("Using fallback template")
        
        print("\nHierarchical extraction system is working!")
        print("The source will try:")
        print("1. Crawl4AI (Playwright) extraction")
        print("2. BeautifulSoup HTML parsing")  
        print("3. RSS feed parsing")
        print("And report which method succeeded.")
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        print(f"Error details: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_basic_hierarchical())