# Browser Performance Configuration
# Add these settings to your Crawl4AI extractor

BROWSER_CONFIG_OPTIMIZATIONS = {
    # Limit concurrent browsers
    "max_concurrent_browsers": 1,
    
    # Browser session reuse
    "reuse_browser_session": True,
    
    # Enhanced cleanup
    "auto_cleanup": True,
    "cleanup_interval": 30,  # seconds
    
    # Resource limits
    "memory_limit_mb": 512,
    "timeout_per_request": 30,
    
    # Optimized browser args
    "extra_browser_args": [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu", 
        "--disable-features=VizDisplayCompositor",
        "--disable-extensions",
        "--disable-plugins",
        "--disable-images",  # Skip images for faster loading
        "--disable-javascript",  # For basic HTML content (optional)
        "--memory-pressure-off",
        "--max-old-space-size=512",
        "--aggressive-cache-discard",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding"
    ]
}
