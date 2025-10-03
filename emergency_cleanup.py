#!/usr/bin/env python3
"""
Emergency cleanup script for multiple Chrome processes and data cleaning verification.
"""
import subprocess
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger

def kill_all_chrome_processes():
    """Kill all Chrome/Chromium processes."""
    logger.info("🚨 EMERGENCY: Killing all Chrome processes...")
    
    try:
        # Kill all chrome processes
        result = subprocess.run([
            'taskkill', '/f', '/im', 'chrome.exe'
        ], capture_output=True, text=True, shell=True)
        
        if result.returncode == 0:
            logger.info(f"✅ Successfully killed Chrome processes: {result.stdout}")
        else:
            logger.warning(f"⚠️ Chrome kill result: {result.stderr}")
        
        # Also kill any remaining chromium processes
        result2 = subprocess.run([
            'taskkill', '/f', '/im', 'chromium.exe'
        ], capture_output=True, text=True, shell=True)
        
        logger.info("🧹 Chrome process cleanup completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to kill Chrome processes: {e}")
        return False

def check_data_cleaning_setup():
    """Check if data cleaning (LLM) is properly configured."""
    logger.info("🔍 Checking data cleaning setup...")
    
    try:
        # Check environment variables
        required_env_vars = [
            'OPENAI_API_KEY',
            'AZURE_OPENAI_DEPLOYMENT',
            'OPENAI_BASE_URL'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Missing environment variables: {missing_vars}")
            return False
        
        logger.info("✅ All required environment variables are set")
        
        # Test LLM cleaner import and initialization
        try:
            from utils.llm.cleaner import LLMContentCleaner
            logger.info("✅ LLM cleaner module imports successfully")
            
            # Try to initialize (this will test Azure OpenAI connection)
            cleaner = LLMContentCleaner()
            logger.info(f"✅ LLM cleaner initialized with model: {cleaner.model}")
            
            # Test a simple cleaning operation
            test_content = """
            <div class="advertisement">Buy now!</div>
            <nav>Navigation menu</nav>
            <article>
                <h1>Important Financial News</h1>
                <p>The stock market moved significantly today...</p>
            </article>
            <footer>Copyright 2024</footer>
            """
            
            logger.info("🧪 Testing content cleaning...")
            
            # Test cleaning (this will make an actual API call)
            try:
                cleaned_content = cleaner.clean_content(
                    content=test_content,
                    url="https://test.com/article",
                    title="Test Financial Article"
                )
                
                if cleaned_content and len(cleaned_content.strip()) > 0:
                    logger.info("✅ Content cleaning test PASSED")
                    logger.info(f"📝 Cleaned content preview: {cleaned_content[:200]}...")
                    return True
                else:
                    logger.error("❌ Content cleaning returned empty result")
                    return False
                    
            except Exception as cleaning_error:
                logger.error(f"❌ Content cleaning test FAILED: {cleaning_error}")
                return False
                
        except ImportError as import_error:
            logger.error(f"❌ Cannot import LLM cleaner: {import_error}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Data cleaning setup check FAILED: {e}")
        return False

def check_browser_optimization():
    """Check if browser is properly configured for optimization."""
    logger.info("🔍 Checking browser optimization settings...")
    
    try:
        # Check if we can find Crawl4AI configuration
        from crawler.extractors.crawl4ai_extractor import EnhancedCrawl4AIExtractor
        logger.info("✅ Crawl4AI extractor available")
        
        # Recommend optimization settings
        logger.info("💡 Browser optimization recommendations:")
        logger.info("   1. Use headless mode (should be default)")
        logger.info("   2. Limit concurrent browser instances")
        logger.info("   3. Ensure browser instances are properly closed")
        logger.info("   4. Use session reuse when possible")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Browser optimization check failed: {e}")
        return False

def main():
    """Main cleanup and verification function."""
    logger.info("🚀 Starting emergency cleanup and data cleaning verification...")
    
    # Step 1: Kill all Chrome processes
    chrome_killed = kill_all_chrome_processes()
    
    # Step 2: Check data cleaning setup
    data_cleaning_ok = check_data_cleaning_setup()
    
    # Step 3: Check browser optimization
    browser_optimization_ok = check_browser_optimization()
    
    # Summary
    logger.info("="*60)
    logger.info("📊 CLEANUP & VERIFICATION SUMMARY")
    logger.info("="*60)
    logger.info(f"Chrome Process Cleanup: {'✅ DONE' if chrome_killed else '❌ FAILED'}")
    logger.info(f"Data Cleaning Setup: {'✅ WORKING' if data_cleaning_ok else '❌ ISSUES'}")
    logger.info(f"Browser Optimization: {'✅ CHECKED' if browser_optimization_ok else '❌ ISSUES'}")
    
    if chrome_killed and data_cleaning_ok and browser_optimization_ok:
        logger.info("🎉 ALL SYSTEMS READY! You can now run the crawler.")
        logger.info("💡 The browser performance should be much faster now.")
        return True
    else:
        logger.error("❌ Some issues need to be resolved before running the crawler.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
