"""
Article content extraction module for NewsRagnarok Crawler.
"""
import asyncio
import re
from urllib.parse import urlparse
from loguru import logger
import aiohttp
from bs4 import BeautifulSoup
from utils.clean_markdown import clean_markdown

async def extract_full_content(url: str, rss_entry) -> str:
    """Extract full article content from URL using multiple methods with enhanced error handling."""
    try:
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
        
        # Domain-specific content selectors
        content_selectors = [
            'article',
            '[class*="article"]',
            '[class*="content"]',
            '[class*="post"]',
            '[class*="entry"]',
            '.post-content',
            '.entry-content',
            '.article-content',
            '.content-body',
            '.story-body',
            'main',
            '.main-content'
        ]
        
        # BabyPips specific selectors - This fixes the "article_processing_failed" error
        if "babypips.com" in domain:
            logger.info(f"Using babypips-specific extraction for: {url}")
            content_selectors = [
                '.post-content',
                '.entry-content',
                '.article-body',
                '.full-post',
                'article',
                '.news-content',
                '.content',
                '#content .post'
            ]
        
        # Method 1: Try Playwright first (if available) with enhanced error handling
        try:
            try:
                from crawl4ai import AsyncWebCrawler
                from crawl4ai.browser_config import BrowserConfig
                logger.info(f"Attempting Playwright extraction for: {url}")
                
                # Log version information for debugging
                try:
                    import playwright
                    import crawl4ai
                    logger.info(f"Using playwright version: {playwright.__version__}")
                    logger.info(f"Using crawl4ai version: {crawl4ai.__version__}")
                except Exception as ver_err:
                    logger.warning(f"Error getting version info: {str(ver_err)}")
                
                browser_config = BrowserConfig(
                    headless=True,
                    extra_args=[
                        "--disable-gpu", 
                        "--disable-dev-shm-usage", 
                        "--no-sandbox",
                        "--disable-extensions",
                        "--disable-plugins",
                        "--disable-images",
                        # Removed: "--disable-javascript" to allow content to load properly
                        "--memory-pressure-off",
                        "--max_old_space_size=512"  # Limit memory
                    ]
                )
                
                try:
                    async with AsyncWebCrawler(config=browser_config) as crawler:
                        # Set a timeout for the extraction
                        result = await asyncio.wait_for(crawler.arun(url), timeout=30.0)
                        if result and result.markdown and result.markdown.raw_markdown:
                            content = result.markdown.raw_markdown
                            if len(content) > 500:
                                # Clean the content using clean_markdown with exception handling
                                try:
                                    cleaned_content = clean_markdown(content)
                                    if cleaned_content and len(cleaned_content) > 50:
                                        logger.info(f"Playwright extraction successful: {len(cleaned_content)} chars")
                                        return cleaned_content
                                    else:
                                        logger.warning(f"Playwright extraction cleaned content too short: {len(cleaned_content) if cleaned_content else 0} chars")
                                except Exception as clean_err:
                                    logger.warning(f"Error cleaning content: {clean_err}")
                                    # Return unprocessed content if clean_markdown fails
                                    if len(content) > 200:
                                        logger.info(f"Using unprocessed Playwright content: {len(content)} chars")
                                        return content
                            else:
                                logger.warning(f"Playwright extraction too short: {len(content)} chars")
                except asyncio.TimeoutError:
                    logger.warning(f"Playwright extraction timed out after 30 seconds for {url}")
                except Exception as inner_e:
                    logger.warning(f"Playwright extraction inner error: {str(inner_e)}")
            except ImportError:
                logger.warning("crawl4ai not available, skipping Playwright extraction")
            except Exception as e:
                logger.warning(f"Playwright extraction failed: {str(e)}")
        except Exception as e:
            logger.warning(f"Outer Playwright extraction block error: {str(e)}")
        
        # Method 2: Fallback to HTTP + BeautifulSoup with enhanced error handling
        logger.info(f"Using HTTP extraction for: {url}")
        
        # Headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Fetch the webpage
        html_content = ""
        try:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, headers=headers, timeout=30) as response:
                        if response.status != 200:
                            logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
                        else:
                            html_content = await response.text()
                except Exception as fetch_err:
                    logger.warning(f"Error fetching URL {url}: {fetch_err}")
        except Exception as session_err:
            logger.warning(f"Session error for {url}: {session_err}")
        
        # If we couldn't get HTML, return RSS summary
        if not html_content:
            logger.warning(f"Failed to get HTML content for {url}, using RSS summary")
            return rss_entry.get('summary', '') or rss_entry.get('description', '')
        
        # Method 2a: Try BeautifulSoup with careful selectors
        try:
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.decompose()
            
            # Try different selectors for article content based on common patterns
            content_selectors = [
                'article',
                '[class*="article"]',
                '[class*="content"]',
                '[class*="post"]',
                '[class*="entry"]',
                '.post-content',
                '.entry-content',
                '.article-content',
                '.content-body',
                '.story-body',
                'main',
                '.main-content'
            ]
            
            content_text = ""
            
            # Try to find content using selectors
            for selector in content_selectors:
                try:
                    elements = soup.select(selector)
                    if elements:
                        # Get text from the largest element (likely the main content)
                        largest_element = max(elements, key=lambda x: len(x.get_text()))
                        candidate_text = largest_element.get_text(separator=' ', strip=True)
                        if len(candidate_text) > 500:  # Only replace if significant content found
                            content_text = candidate_text
                            logger.info(f"Found content using selector '{selector}': {len(content_text)} chars")
                            break
                except Exception as selector_err:
                    logger.warning(f"Error with selector '{selector}': {selector_err}")
                    continue
            
            # Method 2b: If no content found with selectors, try to get all text
            if not content_text or len(content_text) < 500:
                try:
                    logger.info("Using full page text extraction")
                    content_text = soup.get_text(separator=' ', strip=True)
                    logger.info(f"Full page text: {len(content_text)} chars")
                except Exception as full_text_err:
                    logger.warning(f"Error getting full page text: {full_text_err}")
            
            # Method 2c: Clean the content using clean_markdown with exception handling
            cleaned_content = ""
            try:
                if content_text:
                    cleaned_content = clean_markdown(content_text)
                    logger.info(f"Cleaned BeautifulSoup content: {len(cleaned_content)} chars")
            except Exception as clean_err:
                logger.warning(f"Error cleaning BeautifulSoup content: {clean_err}")
                # Use unprocessed content if clean_markdown fails
                cleaned_content = content_text
            
            # Method 3: If we still don't have good content, try a minimal extraction method
            if not cleaned_content or len(cleaned_content) < 200:
                logger.warning(f"Regular extraction methods failed for {url}, attempting minimal extraction")
                try:
                    # Use very basic extraction with minimal regex to avoid errors
                    simple_text = ""
                    try:
                        # Extract text using a very simple, error-resistant approach
                        # Don't use regex here to avoid potential errors
                        simple_soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Get text from paragraphs only
                        paragraphs = simple_soup.find_all('p')
                        if paragraphs:
                            simple_text = ' '.join([p.get_text() for p in paragraphs])
                        
                        # If no paragraphs, just get all text
                        if not simple_text:
                            simple_text = simple_soup.get_text(separator=' ', strip=True)
                        
                        # Basic cleanup without regex
                        simple_text = ' '.join(simple_text.split())
                        logger.info(f"Minimal extraction result: {len(simple_text)} chars")
                    except Exception as simple_e:
                        logger.error(f"Error in minimal extraction: {simple_e}")
                        # Continue with whatever we have
                    
                    if simple_text and len(simple_text) > 200:
                        logger.info(f"Minimal extraction successful: {len(simple_text)} chars")
                        return simple_text
                    else:
                        # Extract title + RSS summary as last resort
                        title = ""
                        try:
                            title_tag = soup.find('title')
                            if title_tag:
                                title = title_tag.get_text()
                        except:
                            pass
                        
                        summary = rss_entry.get('summary', '') or rss_entry.get('description', '')
                        combined = f"{title}\n\n{summary}" if title else summary
                        
                        logger.warning(f"All extraction methods failed, using title + RSS summary: {len(combined)} chars")
                        return combined
                except Exception as fallback_e:
                    logger.error(f"Fallback extraction failed: {fallback_e}")
                    return rss_entry.get('summary', '') or rss_entry.get('description', '')
            
            # Return the best content we have
            if cleaned_content and len(cleaned_content) >= 200:
                logger.info(f"HTTP extraction successful: {len(cleaned_content)} chars")
                return cleaned_content
            elif content_text and len(content_text) >= 200:
                logger.info(f"HTTP extraction successful (uncleaned): {len(content_text)} chars")
                return content_text
            else:
                logger.warning(f"HTTP extraction content too short, using RSS summary")
                return rss_entry.get('summary', '') or rss_entry.get('description', '')
            
        except Exception as bs_err:
            logger.error(f"BeautifulSoup extraction error: {bs_err}")
            
            # Method 4: Emergency fallback - use RSS summary
            logger.warning(f"All extraction methods failed, using RSS summary as last resort")
            return rss_entry.get('summary', '') or rss_entry.get('description', '')
            
    except Exception as e:
        logger.warning(f"Error extracting full content from {url}: {str(e)}")
        # Fall back to RSS summary
        return rss_entry.get('summary', '') or rss_entry.get('description', '')
