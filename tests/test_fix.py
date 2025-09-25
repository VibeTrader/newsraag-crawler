#!/usr/bin/env python3
"""
Test script to verify the Crawl4AI timeout fix and Azure OpenAI configuration.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_env_variables():
    """Test environment variable loading."""
    print("Testing environment variables...")
    
    # Check Azure OpenAI configuration
    azure_deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    openai_base_url = os.getenv('OPENAI_BASE_URL')
    
    print(f"AZURE_OPENAI_DEPLOYMENT: {azure_deployment}")
    print(f"OPENAI_API_KEY: {'***' if openai_api_key else 'NOT SET'}")
    print(f"OPENAI_BASE_URL: {openai_base_url}")
    
    return azure_deployment is not None

def test_crawl4ai_import():
    """Test if Crawl4AI imports correctly."""
    print("\nTesting Crawl4AI import...")
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
        print("✅ Crawl4AI imports successful")
        return True
    except ImportError as e:
        print(f"❌ Crawl4AI import failed: {e}")
        return False

def test_crawler_config():
    """Test if CrawlerRunConfig can be created without timeout_ms."""
    print("\nTesting CrawlerRunConfig creation...")
    try:
        from crawl4ai import CrawlerRunConfig, CacheMode
        from crawl4ai.content_filter_strategy import PruningContentFilter
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
        
        # Try to create a configuration similar to what we fixed
        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            excluded_tags=['nav', 'footer', 'aside', 'header'],
            remove_overlay_elements=True,
            css_selector=".content, .article-body, .post-content",
            markdown_generator=DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(
                    threshold=0.85,
                    threshold_type="fixed",
                    min_word_threshold=50,
                ),
                options={
                    "ignore_links": True,
                    "ignore_images": True,
                    "ignore_tables": False,
                    "ignore_horizontal_rules": True
                }
            )
        )
        print("✅ CrawlerRunConfig created successfully without timeout_ms")
        return True
    except Exception as e:
        print(f"❌ CrawlerRunConfig creation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("NewsRagnarok Crawler Fix Test\n" + "="*40)
    
    env_ok = test_env_variables()
    crawl4ai_ok = test_crawl4ai_import()
    config_ok = test_crawler_config()
    
    print("\n" + "="*40)
    print("Test Results:")
    print(f"Environment Variables: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"Crawl4AI Import: {'✅ PASS' if crawl4ai_ok else '❌ FAIL'}")
    print(f"CrawlerRunConfig: {'✅ PASS' if config_ok else '❌ FAIL'}")
    
    if all([env_ok, crawl4ai_ok, config_ok]):
        print("\n🎉 All tests passed! The fixes should resolve the crawler issues.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Additional fixes may be needed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
