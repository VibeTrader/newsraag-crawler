#!/usr/bin/env python3
"""
Simple test script for the hierarchical concept.

Tests basic source creation and configuration loading.
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.factories import load_sources_from_yaml
from loguru import logger

def test_source_loading():
    """Test basic source loading."""
    print("Testing source configuration loading...")
    
    try:
        # Load source configurations
        sources_config = load_sources_from_yaml('config/sources.yaml')
        
        if not sources_config:
            print("No sources loaded!")
            return False
        
        print(f"Successfully loaded {len(sources_config)} sources:")
        
        for i, config in enumerate(sources_config, 1):
            print(f"  {i}. {config.name} ({config.source_type.value})")
            print(f"     URL: {getattr(config, 'rss_url', getattr(config, 'base_url', 'N/A'))}")
            print(f"     Max articles: {config.max_articles_per_run}")
            
        return True
        
    except Exception as e:
        print(f"Failed to load sources: {str(e)}")
        import traceback
        print(f"   Error details: {traceback.format_exc()}")
        return False

def test_imports():
    """Test key imports."""
    print("\nTesting key imports...")
    
    try:
        print("  Testing crawl4ai...")
        import crawl4ai
        print(f"    Crawl4AI version: {getattr(crawl4ai, '__version__', 'unknown')}")
        
        print("  Testing feedparser...")
        import feedparser
        
        print("  Testing beautifulsoup4...")
        from bs4 import BeautifulSoup
        
        print("  Testing aiohttp...")
        import aiohttp
        
        print("All imports successful!")
        return True
        
    except Exception as e:
        print(f"Import failed: {str(e)}")
        return False

def show_hierarchical_concept():
    """Show the hierarchical extraction concept."""
    print("\n" + "="*60)
    print("HIERARCHICAL CONTENT EXTRACTION SYSTEM")
    print("="*60)
    print()
    print("This system implements a three-tier fallback mechanism:")
    print()
    print("1. PRIMARY: Crawl4AI (Playwright)")
    print("   - Best for modern JavaScript-heavy websites")
    print("   - Renders dynamic content")
    print("   - Most accurate content extraction")
    print()
    print("2. SECONDARY: BeautifulSoup")
    print("   - Lightweight HTML parsing")
    print("   - Good for traditional websites")
    print("   - Faster than browser automation")
    print()
    print("3. TERTIARY: RSS Feeds")
    print("   - Most reliable fallback")
    print("   - Structured content")
    print("   - Minimal processing overhead")
    print()
    print("Benefits:")
    print("- Automatic fallback on failures")
    print("- Transparent method reporting")
    print("- Easy to extend with new sources")
    print("- Optimal extraction for each site")
    print("="*60)

if __name__ == "__main__":
    print("NewsRag Hierarchical System Verification")
    print("="*60)
    
    # Test imports
    imports_ok = test_imports()
    
    # Test source loading
    loading_ok = test_source_loading()
    
    # Show concept
    show_hierarchical_concept()
    
    # Summary
    print("\nTEST RESULTS:")
    print(f"  Imports: {'PASS' if imports_ok else 'FAIL'}")
    print(f"  Source Loading: {'PASS' if loading_ok else 'FAIL'}")
    
    if imports_ok and loading_ok:
        print("\nSystem is ready for hierarchical extraction!")
        print("   Next: Run the full test_hierarchical_system.py")
    else:
        print("\nSystem needs fixes before hierarchical extraction")
    
    print("="*60)