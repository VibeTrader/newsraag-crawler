# FXStreet Specific Browser Configuration
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
