#!/usr/bin/env python3
"""
Test script for robust RSS parser integration
"""
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from crawler.utils.robust_rss_parser import RobustRSSParser

async def test_process_rss_source():
    """Test the process_rss_source function"""
    
    # Import the function from main.py
    from main import process_rss_source
    
    # Test configurations
    test_sources = [
        {
            'name': 'babypips_test',
            'url': 'https://www.babypips.com/feed.rss',
            'max_articles': 5
        },
        {
            'name': 'fxstreet_test', 
            'url': 'https://www.fxstreet.com/rss/news',
            'max_articles': 5
        },
        {
            'name': 'forexlive_test',
            'url': 'https://www.forexlive.com/feed/',
            'max_articles': 5
        }
    ]
    
    logger.info("🧪 Testing robust RSS parser integration...")
    
    for source_config in test_sources:
        logger.info(f"\n📡 Testing {source_config['name']}...")
        
        try:
            result = await process_rss_source(source_config)
            
            logger.info(f"✅ Result for {source_config['name']}:")
            logger.info(f"   Articles discovered: {result['articles_discovered']}")
            logger.info(f"   Articles processed: {result['articles_processed']}")
            logger.info(f"   Articles failed: {result['articles_failed']}")
            
        except Exception as e:
            logger.error(f"❌ Test failed for {source_config['name']}: {e}")
    
    logger.info("\n🏁 Integration test complete!")

if __name__ == "__main__":
    asyncio.run(test_process_rss_source())
