"""
Test script for the NewsRagnarok Crawler fixes.
"""
import asyncio
import sys
import os
from loguru import logger

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_babypips():
    """Test the BabyPips crawler with domain-specific selectors."""
    logger.info("=== Testing BabyPips Crawler Fix ===")
    
    from crawler.babypips import BabyPipsCrawler
    from crawl4ai import AsyncWebCrawler, BrowserConfig
    
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
            success = await crawler.process_url(test_url, shared_crawler)
            
            if success:
                logger.info(f"✅ Successfully processed BabyPips article")
                return True
            else:
                logger.error(f"❌ Failed to process BabyPips article")
                return False
                
    except Exception as e:
        logger.error(f"Error testing BabyPips crawler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_kabutan():
    """Test the Kabutan HTML crawler implementation."""
    logger.info("=== Testing Kabutan HTML Crawler Fix ===")
    
    from crawler.kabutan import KabutanCrawler
    from crawl4ai import AsyncWebCrawler, BrowserConfig
    
    # Create browser config
    browser_config = BrowserConfig(
        headless=True,
        extra_args=[
            "--disable-gpu", 
            "--disable-dev-shm-usage", 
            "--no-sandbox",
            "--disable-extensions",
            "--memory-pressure-off",
            "--max_old_space_size=512"
        ]
    )
    
    try:
        # Create the kabutan crawler
        crawler = KabutanCrawler()
        
        # Create a shared crawler instance
        async with AsyncWebCrawler(config=browser_config) as shared_crawler:
            # Get URLs
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
            
            # Process the URL
            success = await crawler.process_url(test_url, shared_crawler)
            
            if success:
                logger.info(f"✅ Successfully processed Kabutan article")
                return True
            else:
                logger.error(f"❌ Failed to process Kabutan article")
                return False
                
    except Exception as e:
        logger.error(f"Error testing Kabutan crawler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        # Close the crawler if it exists
        if 'crawler' in locals():
            await crawler.close()

async def test_cleanup():
    """Test the cleanup functionality."""
    logger.info("=== Testing Cleanup Functionality ===")
    
    from crawler.utils.cleanup import cleanup_old_data
    
    try:
        success = await cleanup_old_data(hours=24)
        
        if success:
            logger.info("✅ Cleanup successful")
        else:
            logger.error("❌ Cleanup failed")
            
        return success
    except Exception as e:
        logger.error(f"Error testing cleanup: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """Run all tests."""
    logger.info("Starting tests for NewsRagnarok crawler fixes...")
    
    # Test babypips crawler
    babypips_result = await test_babypips()
    
    # Test kabutan crawler
    kabutan_result = await test_kabutan()
    
    # Test cleanup functionality
    cleanup_result = await test_cleanup()
    
    # Report results
    logger.info("=== Test Results ===")
    logger.info(f"BabyPips Crawler: {'✅ PASSED' if babypips_result else '❌ FAILED'}")
    logger.info(f"Kabutan HTML Crawler: {'✅ PASSED' if kabutan_result else '❌ FAILED'}")
    logger.info(f"Cleanup Functionality: {'✅ PASSED' if cleanup_result else '❌ FAILED'}")
    
    if babypips_result and kabutan_result and cleanup_result:
        logger.info("🎉 All tests PASSED! The fixes have been successfully implemented.")
    else:
        logger.error("⚠️ Some tests FAILED. Please check the logs for details.")

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    # Run the tests
    asyncio.run(main())
