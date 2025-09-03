import time
import asyncio
import yaml
import os
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
    """Extract full article content from URL using multiple methods."""
    try:
        import re
        
        # Try Playwright first (if available) - B1 optimized
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig
            logger.info(f"Attempting Playwright extraction for: {url}")
            
            browser_config = BrowserConfig(
                headless=True,
                extra_args=[
                    "--disable-gpu", 
                    "--disable-dev-shm-usage", 
                    "--no-sandbox",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-images",
                    "--disable-javascript",  # Reduce memory usage
                    "--memory-pressure-off",
                    "--max_old_space_size=512"  # Limit memory
                ]
            )
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url)
                if result and result.markdown and result.markdown.raw_markdown:
                    content = result.markdown.raw_markdown
                    if len(content) > 500:
                        # Clean the content using clean_markdown
                        cleaned_content = clean_markdown(content)
                        if cleaned_content and len(cleaned_content) > 50:
                            logger.info(f"Playwright extraction successful: {len(cleaned_content)} chars")
                            return cleaned_content
                        else:
                            logger.warning(f"Playwright extraction cleaned content too short: {len(cleaned_content) if cleaned_content else 0} chars")
                    else:
                        logger.warning(f"Playwright extraction too short: {len(content)} chars")
        except Exception as e:
            logger.warning(f"Playwright extraction failed: {e}")
        
        # Fallback to HTTP + BeautifulSoup
        logger.info(f"Falling back to HTTP extraction for: {url}")
        
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
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
                    return rss_entry.get('summary', '') or rss_entry.get('description', '')
                
                html_content = await response.text()
        
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
            elements = soup.select(selector)
            if elements:
                # Get text from the largest element (likely the main content)
                largest_element = max(elements, key=lambda x: len(x.get_text()))
                content_text = largest_element.get_text(separator=' ', strip=True)
                if len(content_text) > 500:  # Reverted to original minimum
                    break
        
        # If no content found with selectors, try to get all text
        if not content_text or len(content_text) < 500:
            content_text = soup.get_text(separator=' ', strip=True)
        
        # Clean the content using clean_markdown
        cleaned_content = clean_markdown(content_text)
        
        # If we still don't have good content, fall back to RSS summary
        if not cleaned_content or len(cleaned_content) < 200:  # Reverted to original minimum
            logger.warning(f"Could not extract sufficient content from {url}, using RSS summary")
            content_text = rss_entry.get('summary', '') or rss_entry.get('description', '')
        else:
            content_text = cleaned_content
        
        logger.info(f"HTTP extraction successful: {len(content_text)} chars")
        return content_text
        
    except Exception as e:
        logger.warning(f"Error extracting full content from {url}: {e}")
        # Fall back to RSS summary
        return rss_entry.get('summary', '') or rss_entry.get('description', '')

async def process_article(article_data: Dict[str, Any]) -> bool:
    """Process a single article - store in Azure and index in Qdrant."""
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
        
        # Create article model
        article = OutputModel(
            title=title,
            publishDate=published,
            content=content,
            url=url
        )
        
        # Convert to PST
        publish_date_pst = convert_to_pst(published)
        if publish_date_pst:
            article.publishDatePst = publish_date_pst
        
        # Prepare for Azure storage
        article_dict = article.to_dict()
        article_dict.update({
            "_source": source,
            "_author": article_data.get('author', ''),
            "_category": article_data.get('category', ''),
            "_crawled_at": get_timestamp(),
            "_article_id": generate_id()
        })
        
        # Upload to Azure
        azure_ok = check_azure_connection()
        if azure_ok:
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:200]
            success, msg = upload_json_to_azure(
                article_dict,
                blob_name=f"{source}-{safe_title}.json",
                publish_date_pst=article.publishDatePst
            )
            if not success:
                logger.error(f"Azure upload failed for {url}: {msg}")
        
        # Index in Qdrant
        vector_client = None
        try:
            vector_client = VectorClient()
            logger.info(f"🔍 Adding document to Qdrant: {title}")
            
            doc_metadata = {
                "publishDatePst": article.publishDatePst.isoformat() if article.publishDatePst else None,
                "source": source,
                "author": article_data.get('author', ''),
                "category": article_data.get('category', ''),
                "article_id": article_dict.get("_article_id")
            }
            doc_metadata = {k: v for k, v in doc_metadata.items() if v is not None}
            logger.info(f"   📊 Metadata: {doc_metadata}")
            
            add_result = await vector_client.add_document(content, metadata=doc_metadata)
            logger.info(f"   📤 Qdrant add_document result: {add_result}")
            if add_result:
                logger.info(f"✅ Successfully indexed: {title}")
                return True
            else:
                logger.error(f"❌ Failed to index: {title}")
                return False
                
        except Exception as e:
            logger.error(f"Error indexing article {title}: {e}")
            return False
        finally:
            if vector_client:
                await vector_client.close()
                
    except Exception as e:
        logger.error(f"Error processing article: {e}")
        return False

async def crawl_source(source_config: dict) -> tuple:
    """Crawl a single configured source."""
    source_name = source_config.get('name', 'unknown')
    source_type = source_config.get('type', 'unknown')
    source_url = source_config.get('url', '')
    
    logger.info(f"Starting crawl for source: {source_name} (type: {source_type})")
    
    processed_count = 0
    failure_count = 0
    
    try:
        if source_type == 'rss':
            # Crawl RSS feed
            articles = await crawl_rss_feed(source_name, source_url)
            
            # Process each article
            logger.info(f"Processing {len(articles)} articles from {source_name}")
            for i, article in enumerate(articles):
                logger.info(f"Processing article {i+1}/{len(articles)}: {article.get('title', 'Unknown')}")
                success = await process_article(article)
                if success:
                    processed_count += 1
                    logger.info(f"✅ Successfully processed article {i+1}")
                else:
                    failure_count += 1
                    logger.error(f"❌ Failed to process article {i+1}")
                    
        elif source_type == 'html':
            logger.warning(f"HTML crawling not implemented for {source_name}")
            failure_count += 1
        else:
            logger.warning(f"Unknown source type: {source_type}")
            failure_count += 1
            
    except Exception as e:
        logger.error(f"Error crawling source {source_name}: {e}")
        failure_count += 1
    
    logger.info(f"Finished crawling {source_name}: {processed_count} processed, {failure_count} failed")
    return source_name, processed_count, failure_count

async def check_dependencies() -> bool:
    """Check if all dependencies are available."""
    logger.info("Checking dependencies...")
    
    # Check Redis (optional for now)
    redis_ok = True  # We'll implement this later if needed
    
    # Check Qdrant
    vector_client = None
    try:
        vector_client = VectorClient()
        vector_ok = await vector_client.check_health()
        logger.info(f"- Qdrant vector service connection: {'OK' if vector_ok else 'FAILED'}")
    except Exception as e:
        logger.error(f"- Qdrant vector service connection: FAILED ({e})")
        vector_ok = False
    finally:
        if vector_client:
            await vector_client.close()
    
    # Check Azure
    azure_ok = check_azure_connection()
    logger.info(f"- Azure Blob Storage connection: {'OK' if azure_ok else 'FAILED'}")
    
    return redis_ok and vector_ok and azure_ok

async def cleanup_old_data():
    """Clean up data older than 24 hours."""
    try:
        logger.info("Starting cleanup of old data...")
        vector_client = create_vector_client()
        
        # Delete documents older than 24 hours
        result = await vector_client.delete_documents_older_than(hours=24)
        if result:
            logger.info(f"Cleanup completed successfully: {result}")
        else:
            logger.error("Cleanup failed")
            
        await vector_client.close()
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

async def main_loop():
    """Main loop to periodically crawl sources."""
    logger.info("Starting NewsRagnarok main loop...")
    sources = load_sources_config(CONFIG_PATH)
    if not sources:
        logger.error("No valid sources loaded. Exiting.")
        return
    
    last_cleanup_time = datetime.now()
    
    try:
        while True:
            start_time = time.monotonic()
            logger.info("--- Starting New Cycle ---")
            logger.info(f"Current time: {datetime.now()}")
            
            # Check if cleanup is needed (every 24 hours)
            current_time = datetime.now()
            if (current_time - last_cleanup_time).total_seconds() >= CLEANUP_INTERVAL_SECONDS:
                logger.info("Running scheduled cleanup...")
                await cleanup_old_data()
                last_cleanup_time = current_time
                logger.info("Cleanup completed, continuing with crawl cycle...")
            
            # Check dependencies
            if not await check_dependencies():
                logger.error("Dependency check failed. Skipping cycle.")
                elapsed_time = time.monotonic() - start_time
                sleep_duration = max(0, CRAWL_INTERVAL_SECONDS - elapsed_time)
                logger.info(f"Sleeping for {sleep_duration:.2f} seconds...")
                await asyncio.sleep(sleep_duration)
                continue
            
            # Crawl sources (run every hour)
            logger.info(f"Starting crawl cycle for {len(sources)} sources...")
            crawl_results = []
            for source in sources:
                try:
                    result = await crawl_source(source)
                    crawl_results.append(result)
                    # Small delay between sources to manage memory
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"Error crawling source {source}: {e}")
                    crawl_results.append((source, 0, 1))  # Count as failed
            
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
            
            # Calculate next run time
            cycle_duration = time.monotonic() - start_time
            sleep_duration = max(0, CRAWL_INTERVAL_SECONDS - cycle_duration)
            next_run_time = datetime.now() + timedelta(seconds=sleep_duration)
            
            logger.info(f"Cycle finished in {cycle_duration:.2f} seconds")
            logger.info(f"Next crawl cycle scheduled for: {next_run_time}")
            logger.info(f"Sleeping for {sleep_duration:.2f} seconds...")
            
            await asyncio.sleep(sleep_duration)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal. Shutting down...")
        await cleanup_old_data()
        logger.info("Final cleanup completed. Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
        import traceback
        logger.error(f"Stack trace:\n{traceback.format_exc()}")
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal. Shutting down...")
        # Perform final cleanup before shutting down
        await cleanup_old_data()
        logger.info("Final cleanup completed. Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
        # Log stack trace for debugging
        import traceback
        logger.error(f"Stack trace:\n{traceback.format_exc()}")

class HealthHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for Azure App Service health checks."""
    
    def do_GET(self):
        # Handle Azure App Service health checks
        if self.path in ['/', '/health', '/api/health']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "status": "healthy",
                "service": "NewsRagnarok Crawler",
                "timestamp": datetime.now().isoformat(),
                "message": "Crawler is running successfully",
                "port": os.environ.get('PORT', '8000')
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"NewsRagnarok Crawler is running")

def start_health_server():
    """Start HTTP server for Azure health checks."""
    try:
        # Use Azure App Service PORT environment variable, fallback to 8000
        port = int(os.environ.get('PORT', 8000))
        
        # Try multiple ports if the first one is busy
        ports_to_try = [port, 8001, 8002, 8003, 8004]
        
        for try_port in ports_to_try:
            try:
                server = HTTPServer(('0.0.0.0', try_port), HealthHandler)
                logger.info(f"🚀 Health check server started on port {try_port}")
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NewsRagnarok Crawler (Simplified)")
    args = parser.parse_args()
    
    # Log Azure App Service configuration
    port = os.environ.get('PORT', '8000')
    logger.info(f"🌐 Azure App Service Configuration:")
    logger.info(f"   📡 PORT environment variable: {port}")
    logger.info(f"   🚀 Starting health check server on port {port}")
    
    # Start health check server IMMEDIATELY in a separate thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Give health server a moment to start
    import time
    time.sleep(2)
    
    # Run the main crawler loop
    asyncio.run(main_loop())
