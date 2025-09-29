import requests
from bs4 import BeautifulSoup
import datetime
import pytz
from loguru import logger
from typing import List, Tuple, Optional, Set
import re
from crawl4ai import AsyncWebCrawler
from models.output import OutputModel
from utils.clean_markdown import clean_markdown
from crawler.utils.azure_utils import upload_json_to_azure
from clients.vector_client import VectorClient
import asyncio
import hashlib
from urllib.parse import urljoin

# Configure Loguru
logger.add("logs/poundsterlinglive_crawler_{time}.log", rotation="1 day", retention="7 days", level="INFO")

# Constants
MARKETS_URL = "https://www.poundsterlinglive.com/markets"
PST = pytz.timezone('America/Los_Angeles')
SOURCE_NAME = "PoundSterlingLive"

def parse_publish_date(date_str: str) -> Optional[datetime.datetime]:
    """Parses the date string and returns a naive datetime object."""
    # Example format: "Published: 14 June 2024"
    match = re.search(r"(\d{1,2})\s+(\w+)\s+(\d{4})", date_str)
    if match:
        day, month_str, year = match.groups()
        try:
            month = datetime.datetime.strptime(month_str, "%B").month
            dt_naive = datetime.datetime(int(year), month, int(day))
            return dt_naive
        except ValueError as e:
            logger.error(f"Error parsing date string '{date_str}': {e}")
            return None
    # Try another format like "09 May 2024"
    match_alt = re.search(r"(\d{1,2})\s+(\w{3})\s+(\d{4})", date_str)
    if match_alt:
        day, month_abbr, year = match_alt.groups()
        try:
            month = datetime.datetime.strptime(month_abbr, "%b").month
            dt_naive = datetime.datetime(int(year), month, int(day))
            return dt_naive
        except ValueError as e:
            logger.error(f"Error parsing alternative date string '{date_str}': {e}")
            return None

    logger.warning(f"Could not parse date string: {date_str}")
    return None

def convert_to_pst(dt_naive: datetime.datetime) -> datetime.datetime:
    """Converts a naive datetime (assumed UTC) to PST."""
    dt_utc = pytz.utc.localize(dt_naive)
    dt_pst = dt_utc.astimezone(PST)
    return dt_pst

def get_publish_date_from_url(article_url: str) -> Optional[datetime.datetime]:
    """Fetches an article page and extracts its publish date."""
    try:
        response = requests.get(article_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        date_span = soup.find('span', class_='publishing-date')
        # Fallback selectors based on inspection of different articles
        if not date_span:
            date_span = soup.find('time') # Check <time> element
        if not date_span:
             date_span = soup.find('span', text=re.compile(r'Published:')) # Text based

        if date_span:
             date_text = date_span.get('datetime', None) # Check for datetime attribute first
             if not date_text:
                 date_text = date_span.text.strip()

             if date_text:
                 parsed_date = parse_publish_date(date_text)
                 return parsed_date

        logger.warning(f"Publish date not found on {article_url}")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching article {article_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing article {article_url}: {e}")
        return None


class PoundSterlingLiveCrawler:
    def __init__(self, vector_client: VectorClient):
        self.crawler = AsyncWebCrawler()
        self.processed_urls: Set[str] = set() # Simple in-memory cache
        self.vector_client = vector_client
        logger.info("PoundSterlingLiveCrawler initialized.")

    async def process_url(self, url: str, title: str, publish_date_naive: datetime.datetime):
        """Processes a single article URL: crawls, cleans, stores, and indexes."""
        if url in self.processed_urls:
            logger.info(f"Skipping already processed URL: {url}")
            return

        logger.info(f"Processing article: {title} ({url})")
        try:
            # 1. Crawl using crawl4ai (using await and arun)
            # Use specific selectors identified from website inspection
            # Selectors: .item-page (main content area), .blog-featured (featured image area), .item (generic item)
            # Exclude common noisy elements if needed: nav, footer, .sidebar, etc.
            # Choose node_selectors that are likely to contain the main article body
            # Force browser usage to handle potential JS rendering or anti-scraping
            result = await self.crawler.arun(
                url, 
                node_selectors=[".item-page", ".blog-featured", ".item"],
                use_browser=True # Added to force browser rendering
            )

            if not result or not result.markdown:
                logger.error(f"Failed to crawl content for {url}")
                return

            # 2. Clean Markdown
            cleaned_content = clean_markdown(result.markdown)
            if not cleaned_content:
                 logger.warning(f"Content became empty after cleaning for {url}")
                 # Decide if we should still proceed or skip
                 # return

            # 3. Create OutputModel
            publish_date_pst = convert_to_pst(publish_date_naive)
            crawled_at_iso = datetime.datetime.now(pytz.utc).isoformat()
            article_id = hashlib.sha256(url.encode()).hexdigest()

            output_data = OutputModel(
                title=title,
                publishDate=publish_date_naive, # Store original naive date
                publishDatePst=publish_date_pst, # Store PST converted date
                content=cleaned_content,
                url=url,
                source=SOURCE_NAME,
                author=None, # crawl4ai might extract this, check result.metadata
                category="Markets", # Assuming based on URL source
                crawled_at=crawled_at_iso,
                article_id=article_id
            )

            # 4. Upload to Azure
            blob_base_name = f"{SOURCE_NAME.lower()}_{article_id}.json"
            # Pass publish_date_pst to organize in folders like YYYY/MM/DD/
            upload_success, blob_url_or_error = upload_json_to_azure(
                json_data=output_data.to_dict(),
                blob_name=blob_base_name,
                publish_date_pst=publish_date_pst # Use PST date for folder structure
            )

            if not upload_success:
                logger.error(f"Failed to upload {url} to Azure: {blob_url_or_error}")
                # Decide on error handling: continue, retry, stop?
            else:
                logger.info(f"Successfully uploaded to Azure: {blob_url_or_error}")

            # 5. Index in Qdrant
            # Use the cleaned markdown content for indexing
            # Include key metadata like title, url, source, publishDatePst
            qdrant_metadata = {
                "title": output_data.title,
                "url": output_data.url,
                "source": output_data.source,
                "publishDatePst": output_data.publishDatePst.isoformat() if output_data.publishDatePst else None,
                "article_id": output_data.article_id
                # Add any other relevant metadata fields
            }
            add_response = await self.vector_client.add_document(
                text_content=output_data.content,
                metadata=qdrant_metadata
            )

            if add_response:
                logger.info(f"Successfully indexed in Qdrant: {url} (Status: {add_response.get('status')}, ID: {add_response.get('id')})")
            else:
                logger.error(f"Failed to index {url} in Qdrant.")

            # 6. Update Cache
            self.processed_urls.add(url)

        except Exception as e:
            logger.exception(f"An unexpected error occurred processing URL {url}: {e}")

    async def get_and_process_urls(self, days_limit: int = 1):
        """
        Fetches the markets page using crawl4ai, extracts article URLs, 
        filters them by publish date (PST), and processes the valid URLs.
        """
        logger.info(f"Starting PoundSterlingLive URL fetch and processing for the last {days_limit} day(s) PST.")
        valid_articles: List[Tuple[str, str, datetime.datetime]] = [] # url, title, naive_publish_date
        today_pst = datetime.datetime.now(PST).date()
        start_date_pst = today_pst - datetime.timedelta(days=days_limit - 1)

        try:
            # Use crawl4ai with browser for the main market page
            logger.info(f"Fetching market page {MARKETS_URL} using crawl4ai with browser...")
            market_page_result = await self.crawler.arun(MARKETS_URL, use_browser=True)

            if not market_page_result or not market_page_result.html:
                logger.error(f"Failed to fetch market page {MARKETS_URL} using crawl4ai.")
                return # Cannot proceed without the main page
                
            logger.info(f"Successfully fetched market page content. Parsing with BeautifulSoup...")
            soup = BeautifulSoup(market_page_result.html, 'html.parser')
            
            # Selector based on inspection (April 2025)
            article_containers = soup.find_all('div', class_='card mb-3')
            logger.info(f"Found {len(article_containers)} potential article containers using selector 'div.card.mb-3'.")

            for container in article_containers:
                # Updated title/link selector
                link_tag_container = container.find('h3', class_='card-title')
                if link_tag_container and link_tag_container.find('a'):
                    a_tag = link_tag_container.find('a')
                    url = a_tag.get('href')
                    title = a_tag.text.strip()

                    if not url or not title:
                         logger.debug("Skipping container with missing URL or title.")
                         continue

                    # Ensure URL is absolute
                    if not url.startswith('http'):
                        if url.startswith('/'):
                           # Attempt to join with base URL
                           url = urljoin("https://www.poundsterlinglive.com", url)
                           logger.debug(f"Converted relative URL to: {url}")
                        else:
                            logger.warning(f"Skipping invalid or non-absolute URL: {url}")
                            continue

                    logger.debug(f"Checking potential article: {title} ({url})")
                    # IMPORTANT: Fetching individual article dates still uses requests helper
                    # This could also fail if individual pages require JS. Consider refactoring
                    # get_publish_date_from_url if needed.
                    naive_publish_date = get_publish_date_from_url(url)

                    if naive_publish_date:
                        pst_publish_date = convert_to_pst(naive_publish_date).date()
                        logger.debug(f"Article '{title}' published {pst_publish_date} PST (Original: {naive_publish_date})")

                        if pst_publish_date >= start_date_pst:
                            logger.info(f"Adding valid article: {title} (Published: {pst_publish_date} PST)")
                            valid_articles.append((url, title, naive_publish_date))
                        else:
                            logger.debug(f"Skipping old article: {title} (Published: {pst_publish_date} PST)")
                    else:
                         logger.warning(f"Skipping article due to missing/unparseable date: {title} ({url})")

        except Exception as e:
            logger.exception(f"An unexpected error occurred during URL fetching/processing: {e}")

        logger.info(f"Finished URL fetch. Found {len(valid_articles)} valid URLs to process.")

        # Process the collected URLs asynchronously
        tasks = [self.process_url(url, title, pub_date) for url, title, pub_date in valid_articles]
        await asyncio.gather(*tasks)

        logger.info("Finished processing all valid PoundSterlingLive articles.")


# --- Main Execution Logic --- 
async def main(days_limit: int = 1):
    lightrag_client = None
    try:
        # Initialize LightRag Client
        lightrag_client = LightRagClient()
        # Perform health check (optional but recommended)
        if not await lightrag_client.check_health():
             logger.error("LightRag API health check failed. Aborting crawl.")
             return

        # Initialize and run the crawler
        crawler = PoundSterlingLiveCrawler(lightrag_client)
        await crawler.get_and_process_urls(days_limit=days_limit)

    except ValueError as e:
         logger.error(f"Configuration error: {e}") # Catch client init errors
    except Exception as e:
        logger.exception(f"An error occurred during the crawl process: {e}")
    finally:
        # Ensure the LightRag client is closed
        if lightrag_client:
            await lightrag_client.close()


if __name__ == '__main__':
    # Example usage: Crawl articles published today or yesterday (PST)
    logger.info("Starting PoundSterlingLive crawl script...")
    asyncio.run(main(days_limit=2))
    logger.info("PoundSterlingLive crawl script finished.")

# Removed old get_urls function as it's integrated into the class method
# def get_urls(days_limit: int = 1) -> List[Tuple[str, str]]: ... 