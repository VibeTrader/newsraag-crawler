#!/usr/bin/env python3
"""
Test script for full content extraction using browser-based crawling.
"""
import asyncio
import feedparser
from loguru import logger
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async def test_full_content_extraction():
    """Test full content extraction for a few articles."""
    logger.info("🚀 Testing Full Content Extraction...")
    
    # Test with a few RSS feeds
    test_sources = [
        ("babypips", "https://www.babypips.com/feed.rss"),
        ("fxstreet", "https://www.fxstreet.com/rss/news"),
    ]
    
    # Initialize browser
    browser_config = BrowserConfig(
        headless=True,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for source_name, rss_url in test_sources:
            logger.info(f"\n🔍 Testing {source_name.upper()}")
            
            try:
                # Parse RSS feed
                feed = feedparser.parse(rss_url)
                logger.info(f"Found {len(feed.entries)} articles in RSS")
                
                # Test first 2 articles
                for i, entry in enumerate(feed.entries[:2]):
                    title = entry.get('title', 'No title')
                    link = entry.get('link', '')
                    rss_summary = entry.get('summary', '')
                    
                    logger.info(f"\n📄 Article {i+1}: {title}")
                    logger.info(f"RSS Summary length: {len(rss_summary)} chars")
                    
                    if link:
                        try:
                            # Extract full content
                            logger.info("🌐 Extracting full content...")
                            result = await crawler.arun(link)
                            
                            if result and result.markdown and result.markdown.raw_markdown:
                                full_content = result.markdown.raw_markdown
                                logger.success(f"✅ Full content extracted: {len(full_content)} chars")
                                
                                # Show content comparison
                                logger.info(f"RSS Summary: {rss_summary[:100]}...")
                                logger.info(f"Full Content: {full_content[:200]}...")
                                
                                # Check if full content is significantly longer
                                if len(full_content) > len(rss_summary) * 2:
                                    logger.success("✅ Full content is significantly longer than RSS summary")
                                else:
                                    logger.warning("⚠️ Full content not much longer than RSS summary")
                                    
                            else:
                                logger.error("❌ No content extracted")
                                
                        except Exception as e:
                            logger.error(f"❌ Error extracting content: {e}")
                    else:
                        logger.warning("⚠️ No link available")
                        
            except Exception as e:
                logger.error(f"❌ Error processing {source_name}: {e}")

async def test_single_article():
    """Test a single article extraction in detail."""
    logger.info("\n🧪 Testing Single Article Extraction...")
    
    # Test with one specific article
    test_url = "https://www.babypips.com/learn/forex/eur-usd-forecast"
    
    browser_config = BrowserConfig(
        headless=True,
        extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        try:
            logger.info(f"🌐 Extracting content from: {test_url}")
            result = await crawler.arun(test_url)
            
            if result and result.markdown and result.markdown.raw_markdown:
                content = result.markdown.raw_markdown
                logger.success(f"✅ Content extracted: {len(content)} characters")
                logger.info(f"📄 Content preview: {content[:500]}...")
                
                # Check for key indicators of full content
                has_paragraphs = content.count('\n\n') > 5
                has_detailed_text = len(content) > 1000
                has_analysis = any(word in content.lower() for word in ['analysis', 'strategy', 'technical', 'fundamental'])
                
                logger.info(f"Has paragraphs: {has_paragraphs}")
                logger.info(f"Has detailed text: {has_detailed_text}")
                logger.info(f"Has analysis content: {has_analysis}")
                
                if has_paragraphs and has_detailed_text and has_analysis:
                    logger.success("🎉 Full content extraction working perfectly!")
                else:
                    logger.warning("⚠️ Content extraction may be incomplete")
                    
            else:
                logger.error("❌ No content extracted")
                
        except Exception as e:
            logger.error(f"❌ Error: {e}")

async def main():
    """Run all tests."""
    logger.info("🚀 Starting Full Content Extraction Tests...")
    
    # Test multiple articles
    await test_full_content_extraction()
    
    # Test single article in detail
    await test_single_article()
    
    logger.info("\n✅ Full Content Extraction Tests Complete!")

if __name__ == "__main__":
    asyncio.run(main())
