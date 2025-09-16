import time
import asyncio
import yaml
import os
import sys
import argparse
from loguru import logger
import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime
import gc
import psutil
import os
from contextlib import nullcontext

# Import monitoring components
from monitoring import init_monitoring
from monitoring.metrics import get_metrics
from monitoring.health_check import get_health_check
from monitoring.duplicate_detector import get_duplicate_detector
from monitoring.health_handler import EnhancedHealthHandler
from monitoring.alerts import get_alert_manager, trigger_test_alert

# Import monitoring modules
from monitoring.metrics import get_metrics
from monitoring.lifecycle import create_lifecycle_manager
from monitoring.api import start_monitoring_server
# Import our modules
from clients.vector_client import VectorClient
from utils.azure_utils import check_azure_connection, upload_json_to_azure
from utils.time_utils import convert_to_pst, get_current_pst_time
from utils.dir_utils import generate_id, get_timestamp
from models.output import OutputModel

# Import for content extraction
import aiohttp
from bs4 import BeautifulSoup
from utils.clean_markdown import clean_markdown

# Define path to config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'sources.yaml')

CRAWL_INTERVAL_SECONDS = 3600  # Check sources every hour
CLEANUP_INTERVAL_SECONDS = 86400  # Run cleanup every hour

def log_memory_usage():
    """Log current memory usage and record metrics."""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    rss_mb = mem_info.rss / 1024 / 1024
    virtual_mb = process.memory_info().vms / 1024 / 1024
    
    # Log to console
    logger.info(f"Memory usage: {rss_mb:.2f} MB (RSS), {virtual_mb:.2f} MB (Virtual)")
    
    # Record in metrics
    metrics = get_metrics()
    metrics.record_memory_usage(rss_mb, virtual_mb)

def load_sources_config(config_path: str) -> list:
    """Loads the sources configuration from the YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            if config and 'sources' in config and isinstance(config['sources'], list):
                logger.info(f"Loaded {len(config['sources'])} sources from {config_path}")
                return config['sources']
            else:
                logger.warning(f"Invalid or empty configuration format in {config_path}")
                return []
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        return []
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration file {config_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred loading configuration: {e}")
        return []

async def crawl_rss_feed(source_name: str, rss_url: str) -> List[Dict[str, Any]]:
    """Crawl RSS feed and extract full article content using requests and BeautifulSoup."""
    logger.info(f"Crawling RSS feed: {source_name} from {rss_url}")
    
    try:
        # Parse RSS feed for article discovery
        feed = feedparser.parse(rss_url)
        articles = []
        
        # Get yesterday's date in PST for filtering
        current_pst = get_current_pst_time()
        if not current_pst:
            logger.error(f"Error: Could not determine current PST time for filtering.")
            return []
        
        # Filter for articles from the last 7 days instead of just yesterday
        week_ago_pst = (current_pst - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        logger.info(f"Filtering articles published after (PST): {week_ago_pst}")
        
        # Process RSS entries and extract full content
        for entry in feed.entries:
            try:
                # Extract basic article data from RSS
                title = entry.get('title', '')
                link = entry.get('link', '')
                published = entry.get('published', '')
                
                # Parse published date
                pub_date = datetime.now()  # Default fallback
                if published:
                    try:
                        import email.utils
                        parsed_date = email.utils.parsedate_to_datetime(published)
                        pub_date = parsed_date
                    except:
                        logger.warning(f"Could not parse date: {published}")
                
                # Filter by date
                if pub_date < week_ago_pst:
                    logger.debug(f"Skipping old article: {title} (published: {pub_date})")
                    continue
                
                # Extract full article content using requests and BeautifulSoup
                logger.info(f"Extracting full content for: {title}")
                full_content = await extract_full_content(link, entry)
                
                # Create article data
                article_data = {
                    'title': title,
                    'url': link,
                    'published': pub_date,
                    'source': source_name,
                    'content': full_content,
                    'author': entry.get('author', ''),
                    'category': entry.get('category', '')
                }
                
                articles.append(article_data)
                logger.info(f"Found article with full content: {title} (published: {pub_date}, {len(full_content)} chars)")
                
            except Exception as e:
                logger.error(f"Error processing RSS entry: {e}")
                continue
        
        logger.info(f"Found {len(articles)} articles from {source_name}")
        return articles
        
    except Exception as e:
        logger.error(f"Error crawling RSS feed {source_name}: {e}")
        return []

async def extract_full_content(url: str, rss_entry) -> str:
    """Extract full article content from URL using multiple methods with enhanced error handling."""
    try:
        import re
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

async def process_article(article_data: Dict[str, Any]) -> bool:
    """Process a single article - store in Azure and index in Qdrant with enhanced retry mechanism."""
    # Retry configuration for cloud environments
    max_retries = 3
    retry_delay_base = 2  # seconds
    
    for attempt in range(max_retries):
        retry_delay = retry_delay_base ** attempt if attempt > 0 else 0
        if attempt > 0:
            logger.info(f"Retry attempt {attempt}/{max_retries} for article processing after {retry_delay}s delay")
            await asyncio.sleep(retry_delay)
            
        try:
            title = article_data['title']
            url = article_data['url']
            content = article_data['content']
            source = article_data['source']
            published = article_data['published']
            
            logger.info(f"🔄 Processing article: {title}")
            logger.info(f"   📄 Content length: {len(content)} characters")
            logger.info(f"   🔗 URL: {url}")
            logger.info(f"   📅 Published: {published}")
            
            # Check for duplicates with error handling
            try:
                duplicate_detector = get_duplicate_detector()
                is_duplicate, duplicate_type = duplicate_detector.is_duplicate(article_data)
                
                if is_duplicate:
                    logger.info(f"🔍 Detected duplicate article: {title} (type: {duplicate_type})")
                    # Record duplicate in metrics
                    try:
                        metrics = get_metrics()
                        metrics.record_duplicate_detected(source, url, duplicate_type)
                    except Exception as metrics_err:
                        logger.warning(f"Error recording duplicate metrics: {metrics_err}")
                    return False
            except Exception as dup_err:
                logger.warning(f"Error checking for duplicates: {dup_err}, continuing with processing")
            
            # Create article model
            article = OutputModel(
                title=title,
                publishDate=published,
                content=content,
                url=url
            )
            
            # Convert to PST with error handling
            publish_date_pst = None
            try:
                publish_date_pst = convert_to_pst(published)
                if publish_date_pst:
                    article.publishDatePst = publish_date_pst
            except Exception as date_err:
                logger.warning(f"Error converting date to PST: {date_err}, using original date")
            
            # Prepare for Azure storage
            article_dict = article.to_dict()
            article_dict.update({
                "_source": source,
                "_author": article_data.get('author', ''),
                "_category": article_data.get('category', ''),
                "_crawled_at": get_timestamp(),
                "_article_id": generate_id()
            })
            
            # Upload to Azure with retry logic
            azure_ok = False
            try:
                azure_ok = check_azure_connection()
            except Exception as azure_conn_err:
                logger.warning(f"Error checking Azure connection: {azure_conn_err}")
            
            if azure_ok:
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:200]
                for azure_attempt in range(2):  # Inner retry for Azure
                    try:
                        success, msg = upload_json_to_azure(
                            article_dict,
                            blob_name=f"{source}-{safe_title}.json",
                            publish_date_pst=article.publishDatePst
                        )
                        if not success:
                            logger.error(f"Azure upload failed (attempt {azure_attempt+1}): {msg}")
                            if azure_attempt < 1:  # If not the last attempt
                                await asyncio.sleep(1)  # Short delay before retry
                                continue
                            # Update health check for Azure
                            try:
                                health_check = get_health_check()
                                health_check.update_dependency_status("azure", False, msg)
                            except Exception as health_err:
                                logger.warning(f"Error updating health check: {health_err}")
                        else:
                            logger.info(f"Azure upload successful for {url}")
                            break  # Exit the retry loop on success
                    except Exception as azure_err:
                        logger.error(f"Azure upload exception (attempt {azure_attempt+1}): {azure_err}")
                        if azure_attempt < 1:  # If not the last attempt
                            await asyncio.sleep(1)  # Short delay before retry
            
            # Index in Qdrant with robust error handling
            vector_client = None
            try:
                # Create client for each attempt to ensure fresh connection
                vector_client = VectorClient()
                logger.info(f"🔍 Adding document to Qdrant: {title}")
                
                # Prepare metadata
                doc_metadata = {
                    "publishDatePst": article.publishDatePst.isoformat() if article.publishDatePst else None,
                    "source": source,
                    "author": article_data.get('author', ''),
                    "category": article_data.get('category', ''),
                    "article_id": article_dict.get("_article_id")
                }
                doc_metadata = {k: v for k, v in doc_metadata.items() if v is not None}
                logger.info(f"   📊 Metadata: {doc_metadata}")
                
                # Try to ensure collection exists before adding
                logger.info("Ensuring Qdrant collection exists before adding document")
                try:
                    if hasattr(vector_client.client, "_ensure_collection_exists"):
                        await vector_client.client._ensure_collection_exists()
                except Exception as ensure_err:
                    logger.warning(f"Error ensuring collection exists: {ensure_err}")
                
                # Add document with built-in retry from the enhanced VectorClient
                add_result = await vector_client.add_document(content, metadata=doc_metadata)
                logger.info(f"   📤 Qdrant add_document result: {add_result}")
                
                if add_result:
                    logger.info(f"✅ Successfully indexed: {title}")
                    
                    # Record successful processing in metrics
                    try:
                        metrics = get_metrics()
                        metrics.record_article_processed(source, url, True)
                    except Exception as metrics_err:
                        logger.warning(f"Error recording success metrics: {metrics_err}")
                    
                    # Success - return true
                    return True
                else:
                    logger.error(f"❌ Failed to index: {title}, result was None")
                    
                    # Record failure in metrics and alert for Qdrant error
                    try:
                        metrics = get_metrics()
                        metrics.record_article_processed(source, url, False, "Qdrant indexing failed")
                        
                        # Send specific Qdrant alert
                        metrics.record_qdrant_error(
                            "Qdrant failed to index document - possible timeout parameter issue", 
                            title, 
                            "error"
                        )
                    except Exception as metrics_err:
                        logger.warning(f"Error recording failure metrics: {metrics_err}")
                    except Exception as metrics_err:
                        logger.warning(f"Error recording failure metrics: {metrics_err}")
                    
                    # If this is not the last attempt, continue to retry
                    if attempt < max_retries - 1:
                        continue
                    
                    return False
                    
            except Exception as e:
                logger.error(f"Error indexing article {title} (attempt {attempt+1}): {e}")
                
                # Record failure in metrics with specific Qdrant alert
                try:
                    metrics = get_metrics()
                    metrics.record_article_processed(source, url, False, str(e))
                    
                    # Send specific Qdrant error alert
                    metrics.record_qdrant_error(
                        f"Error indexing article in Qdrant: {str(e)}", 
                        title, 
                        "error"
                    )
                except Exception as metrics_err:
                    logger.warning(f"Error recording error metrics: {metrics_err}")
                
                # If this is not the last attempt, continue to retry
                if attempt < max_retries - 1:
                    continue
                
                return False
            finally:
                if vector_client:
                    try:
                        await vector_client.close()
                    except Exception as close_err:
                        logger.warning(f"Error closing vector client: {close_err}")
                    
        except Exception as e:
            logger.error(f"Error processing article (attempt {attempt+1}): {e}")
            
            # Record error in metrics if we have enough info
            if 'source' in article_data and 'url' in article_data:
                try:
                    metrics = get_metrics()
                    metrics.record_article_processed(
                        article_data['source'], 
                        article_data['url'], 
                        False, 
                        str(e)
                    )
                except Exception as metrics_err:
                    logger.warning(f"Error recording error metrics: {metrics_err}")
            
            # If this is not the last attempt, continue to retry
            if attempt < max_retries - 1:
                continue
            
            return False
    
    # If we've exhausted all retries
    logger.error(f"All retry attempts failed for processing article: {article_data.get('title', 'Unknown')}")
    return False

async def crawl_source(source_config: dict) -> tuple:
    """Crawl a single configured source."""
    source_name = source_config.get('name', 'unknown')
    source_type = source_config.get('type', 'unknown')
    source_url = source_config.get('url', '')
    
    logger.info(f"Starting crawl for source: {source_name} (type: {source_type})")
    
    processed_count = 0
    failure_count = 0
    
    # Get metrics instance
    metrics = get_metrics()
    
    try:
        if source_type == 'rss':
            # Crawl RSS feed
            articles = await crawl_rss_feed(source_name, source_url)
            
            # Process each article
            logger.info(f"Processing {len(articles)} articles from {source_name}")
            for i, article in enumerate(articles):
                logger.info(f"Processing article {i+1}/{len(articles)}: {article.get('title', 'Unknown')}")
                
                # Record start time for extraction performance tracking
                start_time = time.time()
                
                # Process the article
                success = await process_article(article)
                
                # Calculate extraction time
                extraction_time = time.time() - start_time
                
                # Record metrics
                try:
                    metrics.record_article_processed(source_name, article.get('url', ''), success, None if success else f"Processing failed for {article.get('title', 'Unknown')}")
                except Exception as metrics_error:
                    logger.warning(f"Error recording metrics: {metrics_error}")
                
                if success:
                    processed_count += 1
                    logger.info(f"✅ Successfully processed article {i+1}")
                else:
                    failure_count += 1
                    logger.error(f"❌ Failed to process article {i+1}")
                    # Record error in metrics with error handling
                    try:
                        metrics.record_error("article_processing_failed", source_name)
                    except Exception as record_error:
                        logger.warning(f"Error recording error metric: {record_error}")
                    
        elif source_type == 'html':
            logger.warning(f"HTML crawling not implemented for {source_name}")
            failure_count += 1
            # Record error in metrics with error handling
            try:
                metrics.record_error("html_crawling_not_implemented", source_name)
            except Exception as record_error:
                logger.warning(f"Error recording error metric: {record_error}")
        else:
            logger.warning(f"Unknown source type: {source_type}")
            failure_count += 1
            # Record error in metrics with error handling
            try:
                metrics.record_error("unknown_source_type", source_name)
            except Exception as record_error:
                logger.warning(f"Error recording error metric: {record_error}")
            
    except Exception as e:
        logger.error(f"Error crawling source {source_name}: {e}")
        failure_count += 1
        # Record error in metrics with error handling
        try:
            metrics.record_error("source_crawl_error", source_name, str(e))
        except Exception as record_error:
            logger.warning(f"Error recording error metric: {record_error}")
    
    logger.info(f"Finished crawling {source_name}: {processed_count} processed, {failure_count} failed")
    return source_name, processed_count, failure_count

async def check_dependencies() -> bool:
    """Check if all dependencies are available."""
    logger.info("Checking dependencies...")
    health_check = get_health_check()
    
    # Get App Insights for monitoring
    from monitoring.app_insights import get_app_insights
    app_insights = get_app_insights()
    
    # Check Redis (optional for now)
    redis_ok = True  # We'll implement this later if needed
    health_check.update_dependency_status("redis", redis_ok)
    if app_insights.enabled:
        app_insights.track_dependency_status("redis", redis_ok)
    
    # Check Qdrant
    vector_client = None
    try:
        start_time = time.time()
        vector_client = VectorClient()
        vector_ok = await vector_client.check_health()
        duration_ms = (time.time() - start_time) * 1000
        
        logger.info(f"- Qdrant vector service connection: {'OK' if vector_ok else 'FAILED'}")
        health_check.update_dependency_status("qdrant", vector_ok)
        
        # Track in App Insights
        if app_insights.enabled:
            app_insights.track_dependency_status("qdrant", vector_ok, duration_ms)
    except Exception as e:
        logger.error(f"- Qdrant vector service connection: FAILED ({e})")
        vector_ok = False
        health_check.update_dependency_status("qdrant", False, str(e))
        
        # Track failure in App Insights
        if app_insights.enabled:
            app_insights.track_dependency_status("qdrant", False)
            app_insights.track_exception(e, {"dependency": "qdrant"})
    finally:
        if vector_client:
            await vector_client.close()
    
    # Check Azure
    start_time = time.time()
    azure_ok = check_azure_connection()
    duration_ms = (time.time() - start_time) * 1000
    
    logger.info(f"- Azure Blob Storage connection: {'OK' if azure_ok else 'FAILED'}")
    health_check.update_dependency_status("azure", azure_ok)
    
    # Track in App Insights
    if app_insights.enabled:
        app_insights.track_dependency_status("azure_blob", azure_ok, duration_ms)
    
    # Check OpenAI API by simply checking if keys are set
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_ok = openai_api_key is not None
    logger.info(f"- OpenAI API credentials: {'OK' if openai_ok else 'MISSING'}")
    health_check.update_dependency_status("openai", openai_ok)
    
    # Track in App Insights
    if app_insights.enabled:
        app_insights.track_dependency_status("openai", openai_ok)
    
    return redis_ok and vector_ok and azure_ok

async def cleanup_old_data():
    """Clean up data older than 24 hours."""
    try:
        logger.info("Starting cleanup of old data...")
        
        # Get metrics for monitoring
        metrics = get_metrics()
        deletion_id = metrics.start_deletion_process()
        
        # Get App Insights for cloud monitoring
        from monitoring.app_insights import get_app_insights
        app_insights = get_app_insights()
        
        # Start App Insights operation
        with app_insights.start_operation("cleanup_old_data") if app_insights.enabled else nullcontext():
            vector_client = create_vector_client()
            
            # Delete documents older than 24 hours
            result = await vector_client.delete_documents_older_than(hours=24)
            if result:
                logger.info(f"Cleanup completed successfully: {result}")
                # Record deletion metrics
                if 'deleted_count' in result:
                    deleted_count = result['deleted_count']
                    metrics.record_documents_deleted(deleted_count, "qdrant")
                    
                    # Track in App Insights
                    if app_insights.enabled:
                        app_insights.track_documents_deleted(deleted_count, "qdrant")
                        
                metrics.end_deletion_process(success=True)
                
                # Track completion in App Insights
                if app_insights.enabled:
                    duration = metrics.current_deletion.get("duration_seconds", 0) if hasattr(metrics, 'current_deletion') else 0
                    app_insights.track_deletion_duration(duration)
                    app_insights.track_event("cleanup_completed", {"deleted_count": str(deleted_count)})
            else:
                logger.error("Cleanup failed")
                metrics.record_deletion_error("cleanup_failed", "Cleanup returned None", severity="error")
                metrics.end_deletion_process(success=False)
                
                # Track failure in App Insights
                if app_insights.enabled:
                    app_insights.track_event("cleanup_failed")
                
            await vector_client.close()
            
        # Update health check
        health_check = get_health_check()
        health_check.update_dependency_status("qdrant", True)
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        
        # Record deletion error
        metrics = get_metrics()
        if hasattr(metrics, 'current_deletion'):
            metrics.record_deletion_error("cleanup_exception", str(e), severity="critical")
            metrics.end_deletion_process(success=False)
        
        # Track exception in App Insights
        from monitoring.app_insights import get_app_insights
        app_insights = get_app_insights()
        if app_insights.enabled:
            app_insights.track_exception(e, {"operation": "cleanup_old_data"})
        
        # Update health check
        health_check = get_health_check()
        health_check.update_dependency_status("qdrant", False, str(e))
async def main_loop():
    """Main loop to periodically crawl sources."""
    logger.info("Starting NewsRagnarok main loop...")
    sources = load_sources_config(CONFIG_PATH)
    if not sources:
        logger.error("No valid sources loaded. Exiting.")
        return
    
    last_cleanup_time = datetime.now()
    
    # Create heartbeat directory
    heartbeat_dir = os.path.join(os.path.dirname(__file__), 'data', 'heartbeat')
    os.makedirs(heartbeat_dir, exist_ok=True)
    heartbeat_file = os.path.join(heartbeat_dir, 'crawler_heartbeat.txt')
    
    # Update heartbeat file at startup
    with open(heartbeat_file, 'w') as f:
        f.write(f"Crawler started at: {datetime.now().isoformat()}\n")
    
    # Add memory tracking
    try:
        import gc
        import psutil
        process = psutil.Process(os.getpid())
        logger.info(f"Initial memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
    except ImportError:
        logger.warning("psutil not available, memory tracking disabled")
        process = None
    
    try:
        while True:
            start_time = time.monotonic()
            logger.info("--- Starting New Cycle ---")
            logger.info(f"Current time: {datetime.now()}")
            
            # Start cycle metrics tracking
            metrics = get_metrics()
            cycle_id = metrics.start_cycle()
            
            # Get App Insights for cloud monitoring
            from monitoring.app_insights import get_app_insights
            app_insights = get_app_insights()
            
            # Track cycle start in App Insights
            if app_insights.enabled:
                app_insights.track_event("cycle_start", {"cycle_id": cycle_id})
            
            # Log memory usage at cycle start if available
            if process:
                mem_info = process.memory_info()
                memory_mb = mem_info.rss / 1024 / 1024
                logger.info(f"Memory usage at cycle start: {memory_mb:.2f} MB")
                
                # Update memory usage in metrics
                metrics.update_memory_usage(memory_mb)
                
                # Track in App Insights
                if app_insights.enabled:
                    app_insights.track_memory_usage(memory_mb)
                
                # Update health check
                health_check = get_health_check()
                health_check.check_memory_usage()
            
            # Check if cleanup is needed (every 24 hours)
            current_time = datetime.now()
            if (current_time - last_cleanup_time).total_seconds() >= CLEANUP_INTERVAL_SECONDS:
                logger.info("Running scheduled cleanup...")
                await cleanup_old_data()
                last_cleanup_time = current_time
                logger.info("Cleanup completed, continuing with crawl cycle...")
                
                # Force garbage collection after cleanup
                if gc:
                    logger.info("Forcing garbage collection after cleanup...")
                    gc.collect()
                    if process:
                        logger.info(f"Memory after cleanup: {process.memory_info().rss / 1024 / 1024:.2f} MB")
            
            # Check dependencies
            if not await check_dependencies():
                logger.error("Dependency check failed. Skipping cycle.")
                
                # Record error in metrics
                metrics.record_cycle_error("dependency_check_failed", "Dependency check failed, skipping cycle", "critical")
                metrics.end_cycle(success=False)
                
                elapsed_time = time.monotonic() - start_time
                sleep_duration = max(0, CRAWL_INTERVAL_SECONDS - elapsed_time)
                logger.info(f"Sleeping for {sleep_duration:.2f} seconds...")
                await asyncio.sleep(sleep_duration)
                continue
            
            # Crawl sources (run every hour)
            logger.info(f"Starting crawl cycle for {len(sources)} sources...")
            crawl_results = []
            
            for i, source in enumerate(sources):
                try:
                    logger.info(f"Processing source {i+1}/{len(sources)}: {source.get('name', 'Unknown')}")
                    result = await crawl_source(source)
                    crawl_results.append(result)
                    
                    # Small delay between sources to manage memory
                    await asyncio.sleep(5)
                    
                    # Garbage collect after each source
                    if gc and i % 2 == 1:  # Every 2 sources
                        logger.info(f"Performing garbage collection after source {i+1}/{len(sources)}")
                        gc.collect()
                        if process:
                            logger.info(f"Memory after source {i+1}: {process.memory_info().rss / 1024 / 1024:.2f} MB")
                            
                    # Check for excessive memory usage and reduce pressure if needed
                    if process and process.memory_info().rss > 800 * 1024 * 1024:  # Over 800MB
                        logger.warning("Memory usage high, performing emergency cleanup")
                        gc.collect()
                        # You could also implement a more aggressive cleanup here
                        await asyncio.sleep(10)  # Give system time to reclaim memory
                        
                except Exception as e:
                    logger.error(f"Error crawling source {source.get('name', 'Unknown')}: {e}")
                    crawl_results.append((source.get('name', 'Unknown'), 0, 1))  # Count as failed
            
            # Summary
            logger.info("--- Crawl Cycle Summary ---")
            total_processed = 0
            total_failed = 0
            for source_name, processed_count, failure_count in crawl_results:
                logger.info(f"- Source '{source_name}': {processed_count} processed, {failure_count} failed.")
                total_processed += processed_count
                total_failed += failure_count
            
            # Calculate success rate
            success_rate = (total_processed/(total_processed+total_failed)*100) if (total_processed + total_failed) > 0 else 0
            logger.info(f"Total items processed: {total_processed}")
            logger.info(f"Total items failed: {total_failed}")
            logger.info(f"Success rate: {success_rate:.2f}%")
            
            # Calculate time until next cleanup
            time_until_cleanup = CLEANUP_INTERVAL_SECONDS - (datetime.now() - last_cleanup_time).total_seconds()
            logger.info(f"Next cleanup in: {time_until_cleanup/3600:.2f} hours")
            
            # Final garbage collection at end of cycle
            if gc:
                logger.info("Forcing final garbage collection at end of cycle...")
                gc.collect()
                if process:
                    logger.info(f"Memory after cycle end: {process.memory_info().rss / 1024 / 1024:.2f} MB")
            
            # Calculate next run time
            cycle_duration = time.monotonic() - start_time
            sleep_duration = max(0, CRAWL_INTERVAL_SECONDS - cycle_duration)
            next_run_time = datetime.now() + timedelta(seconds=sleep_duration)
            
            logger.info(f"Cycle finished in {cycle_duration:.2f} seconds")
            logger.info(f"Next crawl cycle scheduled for: {next_run_time}")
            logger.info(f"===============================================")
            logger.info(f"SLEEPING for {sleep_duration:.2f} seconds...")
            logger.info(f"Will wake up at {next_run_time}")
            logger.info(f"===============================================")
            
            # End cycle metrics tracking
            metrics.end_cycle(success=True)
            
            # Track cycle completion in App Insights
            if app_insights.enabled:
                app_insights.track_cycle_duration(cycle_duration)
                app_insights.track_event("cycle_completed", {
                    "cycle_id": cycle_id,
                    "duration_seconds": str(round(cycle_duration, 2)),
                    "articles_processed": str(total_processed),
                    "articles_failed": str(total_failed),
                    "success_rate": str(round(success_rate, 2))
                })
            
            # Save daily metrics
            metrics.save_daily_metrics()
            
            # Optional: log system resources before sleep
            if process:
                try:
                    cpu_percent = psutil.cpu_percent(interval=1)
                    mem_percent = psutil.virtual_memory().percent
                    logger.info(f"System resources: CPU {cpu_percent}%, Memory {mem_percent}%")
                except:
                    pass
                    
            # Update heartbeat file before sleep
            try:
                with open(heartbeat_file, 'a') as f:
                    f.write(f"Cycle completed at: {datetime.now().isoformat()}, next cycle at: {next_run_time.isoformat()}\n")
            except Exception as heartbeat_err:
                logger.warning(f"Failed to update heartbeat file: {str(heartbeat_err)}")
                
            # Sleep until next cycle - with additional wake-up logging
            try:
                logger.info(f"Starting sleep at: {datetime.now()}")
                await asyncio.sleep(sleep_duration)
                logger.info(f"Woke up from sleep at: {datetime.now()}")
                logger.info(f"===============================================")
                logger.info(f"STARTING NEXT CYCLE after sleeping")
                logger.info(f"===============================================")
            except Exception as sleep_err:
                logger.error(f"Error during sleep: {str(sleep_err)}")
                # Continue to next cycle anyway
                await asyncio.sleep(5)  # Short delay before retry
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal. Shutting down...")
        
        # Flush App Insights telemetry before exit
        from monitoring.app_insights import get_app_insights
        app_insights = get_app_insights()
        if app_insights.enabled:
            app_insights.track_event("application_shutdown", {"reason": "keyboard_interrupt"})
            app_insights.flush()
            
        await cleanup_old_data()
        logger.info("Final cleanup completed. Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
        import traceback
        logger.error(f"Stack trace:\n{traceback.format_exc()}")
        
        # Try to recover - perform cleanup and restart the loop
        try:
            logger.info("Attempting recovery...")
            if gc:
                gc.collect()
            await asyncio.sleep(60)  # Wait a minute before restarting
            await main_loop()  # Recursive call to restart the loop
        except Exception as recover_error:
            logger.critical(f"Recovery failed: {recover_error}")
            
class HealthHandler(BaseHTTPRequestHandler):
    """Enhanced HTTP handler for health checks with monitoring metrics."""
    
    def do_GET(self):
        """Handle GET requests for health checks and metrics."""
        # Get health check instance
        from monitoring.health_check import get_health_check
        health_check = get_health_check()
        
        # Basic health endpoint
        if self.path in ['/', '/health', '/api/health']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Get comprehensive health status
            health_status = health_check.get_health_status()
            
            # Add basic service info
            health_status.update({
                "service": "NewsRagnarok Crawler",
                "port": os.environ.get('PORT', '8000')
            })
            
            self.wfile.write(json.dumps(health_status).encode())
            
        # Detailed metrics endpoint
        elif self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Get metrics
            from monitoring.metrics import get_metrics
            metrics = get_metrics()
            all_metrics = metrics.get_current_metrics()
            
            self.wfile.write(json.dumps(all_metrics).encode())
            
        # Default response
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"NewsRagnarok Crawler is running")
    
    def log_message(self, format, *args):
        """Override to use loguru instead of print."""
        logger.debug(f"HEALTH SERVER: {self.address_string()} - {format % args}")

def start_health_server():
    """Start HTTP server for Azure health checks."""
    try:
        # Use Azure App Service PORT environment variable, fallback to 8000
        port = int(os.environ.get('PORT', 8000))
        
        # Try multiple ports if the first one is busy
        ports_to_try = [port, 8001, 8002, 8003, 8004]
        
        logger.info("Starting enhanced health check server with monitoring metrics...")
        
        for try_port in ports_to_try:
            try:
                server = HTTPServer(('0.0.0.0', try_port), HealthHandler)
                logger.info(f"🚀 Enhanced health check server started on port {try_port}")
                logger.info(f"   - Health endpoint: http://localhost:{try_port}/health")
                logger.info(f"   - Metrics endpoint: http://localhost:{try_port}/metrics")
                server.serve_forever()
                break  # If we get here, server started successfully
            except OSError as e:
                if "Address already in use" in str(e):
                    logger.warning(f"Port {try_port} is busy, trying next port...")
                    continue
                else:
                    raise e
        else:
            logger.error(f"Failed to start health server on any port: {ports_to_try}")
            
    except Exception as e:
        logger.error(f"Failed to start health server: {e}")

async def clear_qdrant_collection():
    """Clear all documents from the Qdrant collection."""
    logger.info("Starting Qdrant collection cleanup...")
    try:
        vector_client = VectorClient()
        try:
            logger.info("Attempting to clear all documents from Qdrant collection...")
            result = await vector_client.clear_all_documents()
            if result:
                logger.info(f"Qdrant collection cleanup successful: {result}")
                return True
            else:
                logger.error("Qdrant collection cleanup failed: received None result")
                return False
        finally:
            await vector_client.close()
    except Exception as e:
        logger.error(f"Error during Qdrant collection cleanup: {str(e)}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False

async def recreate_qdrant_collection():
    """Delete and recreate the Qdrant collection with proper configuration."""
    logger.info("Starting Qdrant collection recreation...")
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models
        
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        collection_name = os.getenv("QDRANT_COLLECTION_NAME", "news_articles")
        
        logger.info(f"Connecting to Qdrant at {url}")
        client = QdrantClient(url=url, api_key=api_key)
        
        # Delete collection if it exists
        try:
            logger.info(f"Attempting to delete collection {collection_name}...")
            client.delete_collection(collection_name=collection_name)
            logger.info(f"Collection {collection_name} deleted successfully")
        except Exception as e:
            logger.warning(f"Error deleting collection (may not exist): {str(e)}")
        
        # Recreate collection with proper configuration
        logger.info(f"Creating collection {collection_name}...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=3072,  # text-embedding-3-large embedding size
                distance=models.Distance.COSINE
            )
        )
        
        # Create payload indices
        logger.info("Creating payload indices...")
        client.create_payload_index(
            collection_name=collection_name,
            field_name="publishDatePst",
            field_schema=models.PayloadFieldSchema.DATETIME
        )
        
        client.create_payload_index(
            collection_name=collection_name,
            field_name="source",
            field_schema=models.PayloadFieldSchema.KEYWORD
        )
        
        logger.info(f"Collection {collection_name} recreated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during Qdrant collection recreation: {str(e)}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NewsRagnarok Crawler (Simplified)")
    parser.add_argument("--clear-collection", action="store_true", help="Clear all documents from the Qdrant collection")
    parser.add_argument("--recreate-collection", action="store_true", help="Delete and recreate the Qdrant collection")
    args = parser.parse_args()
    
    # Initialize monitoring system
    logger.info("🔍 Initializing monitoring system...")
    from monitoring import init_monitoring
    metrics, health_check, duplicate_detector, app_insights, alert_manager = init_monitoring()
    logger.info("✅ Monitoring system initialized successfully")
    
    # Test Slack alerts on startup to verify configuration
    if os.getenv("ALERT_SLACK_ENABLED", "false").lower() == "true":
        logger.info("🔔 Testing Slack alerts...")
        try:
            # Send a test alert to confirm Slack integration is working
            trigger_test_alert(
                message=f"NewsRagnarok startup test alert from {os.environ.get('COMPUTERNAME') or os.environ.get('HOSTNAME') or 'unknown'}",
                alert_type="startup_test"
            )
            logger.info("✅ Slack test alert triggered successfully")
        except Exception as e:
            logger.error(f"❌ Failed to send Slack test alert: {str(e)}")
    else:
        logger.info("⚠️ Slack alerts are disabled. Set ALERT_SLACK_ENABLED=true to enable.")
    
    # Check if we need to perform collection cleanup or recreation
    if args.clear_collection or args.recreate_collection:
        if args.recreate_collection:
            logger.info("Recreate collection flag detected, recreating Qdrant collection...")
            success = asyncio.run(recreate_qdrant_collection())
            if success:
                logger.info("✅ Qdrant collection recreation completed successfully")
            else:
                logger.error("❌ Qdrant collection recreation failed")
        elif args.clear_collection:
            logger.info("Clear collection flag detected, clearing Qdrant collection...")
            success = asyncio.run(clear_qdrant_collection())
            if success:
                logger.info("✅ Qdrant collection cleanup completed successfully")
            else:
                logger.error("❌ Qdrant collection cleanup failed")
        
        # Exit after cleanup operations if requested
        if not (args.clear_collection and not args.recreate_collection):
            logger.info("Cleanup/recreation operations completed, exiting...")
            sys.exit(0)
    
    # Track application start event in App Insights
    if app_insights.enabled:
        app_insights.track_event("application_start", {
            "version": "1.0.0",  # Update with your version
            "environment": os.environ.get("ENVIRONMENT", "development")
        })
    
    # Ensure data directories exist
    os.makedirs(os.path.join(os.path.dirname(__file__), 'data', 'metrics'), exist_ok=True)
    
    # Log Azure App Service configuration
    port = os.environ.get('PORT', '8000')
    logger.info(f"🌐 Azure App Service Configuration:")
    logger.info(f"   📡 PORT environment variable: {port}")
    logger.info(f"   🚀 Starting enhanced health check server on port {port}")
    
    # Start health check server IMMEDIATELY in a separate thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Give health server a moment to start
    import time
    time.sleep(2)
    
    # Run the main crawler loop
    asyncio.run(main_loop())
