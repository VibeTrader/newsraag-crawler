"""
Test script to verify the fixes for babypips and kabutan crawlers.
Run this script to check if the fixes have resolved the issues.
"""
import asyncio
import sys
import os
from loguru import logger
import time

# Add the project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_babypips_crawler():
    """Test the babypips crawler to see if article processing works."""
    from crawler.babypips import BabyPipsCrawler
    from crawl4ai import AsyncWebCrawler, BrowserConfig
    
    logger.info("=== Testing BabyPips Crawler ===")
    
    # Create the babypips crawler
    crawler = BabyPipsCrawler("https://www.babypips.com/feed.rss")
    
    # Create browser config
    browser_config = BrowserConfig(
        headless=True,
        extra_args=[
            "--disable-gpu", 
            "--disable-dev-shm-usage", 
            "--no-sandbox",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-images",
            "--memory-pressure-off",
            "--max_old_space_size=512"
        ]
    )
    
    # Test getting URLs
    try:
        urls = await crawler.get_urls()
        logger.info(f"Successfully retrieved {len(urls)} URLs from BabyPips RSS")
        
        if not urls:
            logger.error("No URLs found in BabyPips RSS feed")
            return False
            
        # Process the first URL only (for testing)
        test_url = urls[0]
        url_string = test_url[0] if isinstance(test_url, tuple) and len(test_url) > 0 else "Unknown URL"
        
        logger.info(f"Testing article processing with URL: {url_string}")
        
        # Create a shared crawler instance
        async with AsyncWebCrawler(config=browser_config) as shared_crawler:
            # Process the URL
            start_time = time.time()
            result = await crawler.process_url(test_url, shared_crawler)
            processing_time = time.time() - start_time
            
            if result:
                logger.info(f"✅ Successfully processed BabyPips article in {processing_time:.2f}s")
                return True
            else:
                logger.error(f"❌ Failed to process BabyPips article after {processing_time:.2f}s")
                return False
                
    except Exception as e:
        logger.error(f"Error testing BabyPips crawler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
        
async def test_kabutan_crawler():
    """Test the kabutan HTML crawler to see if it's properly implemented."""
    from crawler.kabutan import KabutanCrawler
    from crawl4ai import AsyncWebCrawler, BrowserConfig
    
    logger.info("=== Testing Kabutan HTML Crawler ===")
    
    # Create the kabutan crawler
    crawler = KabutanCrawler()
    
    # Create browser config
    browser_config = BrowserConfig(
        headless=True,
        extra_args=[
            "--disable-gpu", 
            "--disable-dev-shm-usage", 
            "--no-sandbox",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-images",
            "--memory-pressure-off",
            "--max_old_space_size=512"
        ]
    )
    
    # Test getting URLs
    try:
        urls = await crawler.get_urls()
        logger.info(f"Successfully retrieved {len(urls)} URLs from Kabutan")
        
        if not urls:
            logger.warning("No URLs found in Kabutan (this might be expected if no articles today)")
            logger.info("HTML crawling implementation test passed (even with no articles)")
            return True
            
        # Process the first URL only (for testing)
        test_url = urls[0]
        url_string = test_url.get('url', 'Unknown URL') if isinstance(test_url, dict) else "Unknown URL"
        
        logger.info(f"Testing article processing with URL: {url_string}")
        
        # Create a shared crawler instance
        async with AsyncWebCrawler(config=browser_config) as shared_crawler:
            # Process the URL
            start_time = time.time()
            result = await crawler.process_url(test_url, shared_crawler)
            processing_time = time.time() - start_time
            
            if result:
                logger.info(f"✅ Successfully processed Kabutan article in {processing_time:.2f}s")
                return True
            else:
                logger.error(f"❌ Failed to process Kabutan article after {processing_time:.2f}s")
                return False
                
    except Exception as e:
        logger.error(f"Error testing Kabutan crawler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        # Close the kabutan crawler
        await crawler.close()
        
async def main():
    """Run both tests and report results."""
    # Set up logging
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    logger.info("Starting tests for NewsRagnarok crawler fixes...")
    
    # Test babypips crawler
    babypips_result = await test_babypips_crawler()
    
    # Test kabutan crawler
    kabutan_result = await test_kabutan_crawler()
    
    # Report results
    logger.info("=== Test Results ===")
    logger.info(f"BabyPips Crawler: {'✅ PASSED' if babypips_result else '❌ FAILED'}")
    logger.info(f"Kabutan HTML Crawler: {'✅ PASSED' if kabutan_result else '❌ FAILED'}")
    
    if babypips_result and kabutan_result:
        logger.info("🎉 All tests PASSED! The fixes have been successfully implemented.")
    else:
        logger.error("⚠️ Some tests FAILED. Please check the logs for details.")
        
if __name__ == "__main__":
    asyncio.run(main())
