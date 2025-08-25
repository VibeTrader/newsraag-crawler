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

# Import our modules
from clients.vector_client import VectorClient
from utils.azure_utils import check_azure_connection, upload_json_to_azure
from utils.time_utils import convert_to_pst, get_current_pst_time
from utils.dir_utils import generate_id, get_timestamp
from models.output import OutputModel

# Define path to config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config', 'sources.yaml')

CRAWL_INTERVAL_SECONDS = 3600  # Check sources every hour
CLEANUP_INTERVAL_SECONDS = 3600  # Run cleanup every hour

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
    """Crawl RSS feed and extract full article content."""
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
        
        yesterday_pst = (current_pst - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        logger.info(f"Filtering articles published after (PST): {yesterday_pst}")
        
        # Initialize browser for content extraction
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
        
        browser_config = BrowserConfig(
            headless=True,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"]
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
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
                    if pub_date < yesterday_pst:
                        continue
                    
                    # Extract full article content using browser
                    logger.info(f"Extracting full content for: {title}")
                                                try:
                                result = await crawler.arun(link)
                                full_content = result.markdown.raw_markdown if result and result.markdown else entry.get('summary', '')
                                
                                # Fallback to RSS summary if browser extraction fails
                                if not full_content or len(full_content) < 100:
                                    logger.warning(f"Browser extraction failed for {link}, using RSS summary")
                                    full_content = entry.get('summary', '')
                                
                            except Exception as e:
                                logger.warning(f"Error extracting full content for {link}: {e}")
                                full_content = entry.get('summary', '')
                    
                    # Create article data with full content
                    article_data = {
                        'title': title,
                        'url': link,
                        'published': pub_date,
                        'source': source_name,
                        'content': full_content,  # Full article content
                        'author': entry.get('author', ''),
                        'category': entry.get('category', '')
                    }
                    
                    articles.append(article_data)
                    logger.info(f"Found article with full content: {title} ({len(full_content)} chars)")
                    
                except Exception as e:
                    logger.error(f"Error processing RSS entry: {e}")
                    continue
        
        logger.info(f"Found {len(articles)} articles from {source_name}")
        return articles
        
    except Exception as e:
        logger.error(f"Error crawling RSS feed {source_name}: {e}")
        return []

async def process_article(article_data: Dict[str, Any]) -> bool:
    """Process a single article - store in Azure and index in Qdrant."""
    try:
        title = article_data['title']
        url = article_data['url']
        content = article_data['content']
        source = article_data['source']
        published = article_data['published']
        
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
            logger.info(f"Adding document to Qdrant: {title}")
            
            doc_metadata = {
                "publishDatePst": article.publishDatePst.isoformat() if article.publishDatePst else None,
                "source": source,
                "author": article_data.get('author', ''),
                "category": article_data.get('category', ''),
                "article_id": article_dict.get("_article_id")
            }
            doc_metadata = {k: v for k, v in doc_metadata.items() if v is not None}
            
            add_result = await vector_client.add_document(content, metadata=doc_metadata)
            if add_result:
                logger.info(f"Successfully indexed: {title}")
                return True
            else:
                logger.error(f"Failed to index: {title}")
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
            for article in articles:
                success = await process_article(article)
                if success:
                    processed_count += 1
                else:
                    failure_count += 1
                    
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

async def main_loop():
    """Main loop to periodically crawl sources."""
    logger.info("Starting NewsRagnarok main loop...")
    sources = load_sources_config(CONFIG_PATH)
    if not sources:
        logger.error("No valid sources loaded. Exiting.")
        return
    
    try:
        while True:
            start_time = time.monotonic()
            logger.info("--- Starting New Cycle ---")
            
            # Check dependencies
            if not await check_dependencies():
                logger.error("Dependency check failed. Skipping cycle.")
                elapsed_time = time.monotonic() - start_time
                sleep_duration = max(0, CRAWL_INTERVAL_SECONDS - elapsed_time)
                logger.info(f"Sleeping for {sleep_duration:.2f} seconds...")
                await asyncio.sleep(sleep_duration)
                continue
            
            # Crawl sources
            logger.info(f"Starting crawl cycle for {len(sources)} sources...")
            crawl_results = []
            for source in sources:
                result = await crawl_source(source)
                crawl_results.append(result)
            
            # Summary
            logger.info("--- Crawl Cycle Summary ---")
            total_processed = 0
            for source_name, processed_count, failure_count in crawl_results:
                logger.info(f"- Source '{source_name}': {processed_count} processed, {failure_count} failed.")
                total_processed += processed_count
            logger.info(f"--- Total items processed this crawl cycle: {total_processed} ---")
            
            # Sleep until next cycle
            cycle_duration = time.monotonic() - start_time
            sleep_duration = max(0, CRAWL_INTERVAL_SECONDS - cycle_duration)
            logger.info(f"Cycle finished in {cycle_duration:.2f} seconds. Sleeping for {sleep_duration:.2f} seconds...")
            await asyncio.sleep(sleep_duration)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal. Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NewsRagnarok Crawler (Simplified)")
    args = parser.parse_args()
    
    # Run the main loop
    asyncio.run(main_loop())
