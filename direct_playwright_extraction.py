async def extract_full_content_direct_playwright(url: str, rss_entry) -> str:
    """Extract full article content using direct Playwright (without crawl4ai)."""
    try:
        from urllib.parse import urlparse
        
        # Check if URL is valid first
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                logger.warning(f"Invalid URL format: {url}")
                return rss_entry.get('summary', '') or rss_entry.get('description', '')
        except Exception as url_e:
            logger.warning(f"Error parsing URL {url}: {url_e}")
            return rss_entry.get('summary', '') or rss_entry.get('description', '')
        
        # Get domain for debugging
        domain = parsed_url.netloc
        logger.info(f"Extracting content from domain: {domain}")
        
        # Method 1: Try direct Playwright
        try:
            from playwright.async_api import async_playwright
            logger.info(f"Attempting direct Playwright extraction for: {url}")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-gpu", 
                        "--disable-dev-shm-usage", 
                        "--no-sandbox",
                        "--disable-extensions",
                        "--disable-plugins",
                        "--disable-images"
                    ]
                )
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
                page = await context.new_page()
                
                try:
                    # Navigate with timeout
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                    
                    # Wait for content to load
                    await page.wait_for_load_state('networkidle')
                    
                    # Extract the article content
                    content = await page.evaluate("""() => {
                        // First try to find article tag
                        const article = document.querySelector('article');
                        if (article) return article.innerText;
                        
                        // Try common content selectors
                        const selectors = [
                            '[class*="article"]', '[class*="content"]', '[class*="post"]',
                            '[class*="entry"]', '.post-content', '.entry-content',
                            '.article-content', '.content-body', '.story-body',
                            'main', '.main-content'
                        ];
                        
                        for (const selector of selectors) {
                            const element = document.querySelector(selector);
                            if (element) return element.innerText;
                        }
                        
                        // If all else fails, get the body text
                        return document.body.innerText;
                    }""")
                    
                    if content and len(content) > 500:
                        # Clean the content
                        try:
                            cleaned_content = clean_markdown(content)
                            if cleaned_content and len(cleaned_content) > 50:
                                logger.info(f"Direct Playwright extraction successful: {len(cleaned_content)} chars")
                                await browser.close()
                                return cleaned_content
                            else:
                                logger.warning(f"Direct Playwright extraction cleaned content too short: {len(cleaned_content) if cleaned_content else 0} chars")
                        except Exception as clean_err:
                            logger.warning(f"Error cleaning content: {clean_err}")
                            # Return unprocessed content if clean_markdown fails
                            if len(content) > 200:
                                logger.info(f"Using unprocessed Playwright content: {len(content)} chars")
                                await browser.close()
                                return content
                    else:
                        logger.warning(f"Direct Playwright extraction too short: {len(content) if content else 0} chars")
                except Exception as inner_e:
                    logger.warning(f"Direct Playwright extraction inner error: {str(inner_e)}")
                
                await browser.close()
        except ImportError:
            logger.warning("playwright not available, skipping direct Playwright extraction")
        except Exception as e:
            logger.warning(f"Direct Playwright extraction failed: {str(e)}")
        
        # Continue with BeautifulSoup fallback methods...
        # [Remaining code from your existing extract_full_content function]
