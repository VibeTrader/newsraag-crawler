#!/usr/bin/env python3
"""
Test script for hierarchical content extraction system.

This script tests the new hierarchical extraction system that tries:
1. Crawl4AI (Playwright) - Primary
2. BeautifulSoup - Secondary  
3. RSS feeds - Tertiary

Shows which method succeeds for each source.
"""

import asyncio
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.factories import load_sources_from_yaml, SourceFactory
from loguru import logger

async def test_hierarchical_system():
    """Test the hierarchical content extraction system."""
    logger.info("🚀 Testing Hierarchical Content Extraction System")
    logger.info("=" * 60)
    
    try:
        # Load source configurations
        print("Loading source configurations...")
        sources_config = load_sources_from_yaml()
        
        if not sources_config:
            print("❌ No sources loaded!")
            return
        
        print(f"✅ Loaded {len(sources_config)} sources")
        
        # Test each source
        for i, config in enumerate(sources_config, 1):
            logger.info(f"\n[{i}/{len(sources_config)}] Testing {config.name} ({config.source_type.value})")
            logger.info("-" * 50)
            
            try:
                # Create source using factory
                source = SourceFactory.create_source(config)
                print(f"✅ Source created successfully: {type(source).__name__}")
                
                # Test health check if available
                if hasattr(source, 'health_check'):
                    health = await source.health_check()
                    print(f"Health check: {health}")
                
                # Test article fetching with small limit
                print(f"🔍 Testing article extraction (max 3 articles)...")
                articles = await source.fetch_articles(max_articles=3)
                
                if articles:
                    print(f"✅ Extracted {len(articles)} articles")
                    
                    # Show extraction methods used
                    methods_used = set()
                    for article in articles:
                        method = article.metadata.get('extraction_method', 'unknown')
                        methods_used.add(method)
                    
                    print(f"🎯 Extraction methods used: {', '.join(methods_used)}")
                    
                    # Show sample article info
                    if articles:
                        sample = articles[0]
                        print(f"📄 Sample article: {sample.title[:50]}...")
                        print(f"   URL: {sample.url}")
                        print(f"   Content length: {len(sample.content)} chars")
                        print(f"   Method: {sample.metadata.get('extraction_method', 'unknown')}")
                else:
                    print("⚠️ No articles extracted")
                
                # Show extraction statistics if available
                if hasattr(source, 'get_extraction_stats'):
                    stats = source.get_extraction_stats()
                    print(f"📊 Extraction stats: {stats}")
                    
            except Exception as e:
                print(f"❌ Failed to test {config.name}: {str(e)}")
                import traceback
                print(f"   Error details: {traceback.format_exc()}")
                continue
                
        logger.info("\n" + "=" * 60)
        logger.info("🏁 Hierarchical system testing completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_hierarchical_system())