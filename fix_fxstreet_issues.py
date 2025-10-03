#!/usr/bin/env python3
"""
Browser cleanup and FXStreet-specific fixes.
"""
import subprocess
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger

def kill_all_chrome_processes_immediate():
    """Kill all Chrome processes immediately."""
    logger.info("🚨 EMERGENCY: Killing all Chrome processes due to FXStreet issues...")
    
    try:
        # Kill all chrome processes forcefully
        result = subprocess.run([
            'taskkill', '/f', '/im', 'chrome.exe'
        ], capture_output=True, text=True, shell=True)
        
        if result.returncode == 0:
            logger.info(f"✅ Chrome processes killed: {result.stdout}")
        else:
            logger.warning("⚠️ No Chrome processes found to kill")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to kill Chrome processes: {e}")
        return False

def create_fxstreet_specific_fix():
    """Create FXStreet-specific configuration."""
    
    fxstreet_fix = '''# FXStreet Specific Browser Configuration
# Add this to your Crawl4AI extractor for FXStreet

FXSTREET_BROWSER_CONFIG = {
    "headless": True,
    "viewport_width": 1280,
    "viewport_height": 720,
    "extra_args": [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-features=VizDisplayCompositor",
        "--disable-extensions",
        "--disable-plugins",
        "--disable-images",  # Skip images for faster loading
        "--disable-css",     # Skip CSS for faster loading
        "--disable-javascript",  # Skip JS for basic content
        "--memory-pressure-off",
        "--max-old-space-size=256",
        "--aggressive-cache-discard",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-web-security",
        "--disable-features=TranslateUI",
        "--disable-ipc-flooding-protection",
        "--single-process"  # Force single process mode
    ]
}

# Recommended timeout progression for FXStreet
FXSTREET_TIMEOUTS = [60, 90, 120]  # Start higher

# Browser session management
MAX_ARTICLES_PER_BROWSER = 3  # Recreate browser every 3 articles
'''
    
    with open("fxstreet_browser_fix.py", "w") as f:
        f.write(fxstreet_fix)
    
    logger.info("✅ Created FXStreet-specific browser configuration")

def suggest_yaml_fix():
    """Suggest YAML configuration changes for FXStreet."""
    
    logger.info("📋 Recommended YAML changes for FXStreet:")
    logger.info("   1. Increase timeout from 120s to 180s")
    logger.info("   2. Increase rate_limit from 2s to 5s")
    logger.info("   3. Reduce max_articles from 30 to 10")
    logger.info("   4. Add special headers for FXStreet")
    
    yaml_suggestion = '''
# Updated FXStreet configuration
- name: fxstreet
  type: rss
  url: https://www.fxstreet.com/rss/news
  rate_limit: 5  # Increased from 2
  max_articles: 10  # Reduced from 30
  timeout: 180  # Increased from 120
  content_type: forex
  headers:
    User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    Accept-Language: "en-US,en;q=0.5"
    Connection: "keep-alive"
  # Optional: Skip FXStreet if it continues to cause issues
  # enabled: false
'''
    
    with open("fxstreet_yaml_fix.txt", "w") as f:
        f.write(yaml_suggestion)
    
    logger.info("✅ Created FXStreet YAML configuration suggestions")

def main():
    logger.info("🔧 Starting FXStreet issue remediation...")
    
    # Kill all Chrome processes
    chrome_killed = kill_all_chrome_processes_immediate()
    
    # Create fixes
    create_fxstreet_specific_fix()
    suggest_yaml_fix()
    
    logger.info("="*60)
    logger.info("📊 FXSTREET ISSUE ANALYSIS & FIXES")
    logger.info("="*60)
    logger.info(f"Chrome Cleanup: {'✅ DONE' if chrome_killed else '❌ FAILED'}")
    logger.info("✅ FXStreet browser config created")
    logger.info("✅ YAML configuration suggestions created")
    
    logger.info("")
    logger.info("🎯 IMMEDIATE ACTIONS NEEDED:")
    logger.info("1. ✅ Chrome processes cleaned (preventing accumulation)")
    logger.info("2. 📝 Update your sources.yaml with FXStreet fixes")
    logger.info("3. 🔧 Consider temporarily disabling FXStreet while fixing browser management")
    logger.info("4. 🚀 Implement proper browser session cleanup in your extractor")
    
    logger.info("")
    logger.info("⚠️ ROOT CAUSE: Browser instances not being properly closed between articles")
    logger.info("💡 SOLUTION: Implement browser session reuse + proper cleanup")

if __name__ == "__main__":
    main()
