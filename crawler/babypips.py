"""
BabyPips crawler module.

This module implements a crawler for the BabyPips website.
"""
import re
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from loguru import logger

from xml.etree import ElementTree

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from models.output import OutputModel
from utils.clean_markdown import clean_markdown
from crawler.base import BaseCrawlerModule 
from utils.dir_utils import get_output_dir, generate_id, get_timestamp
from utils.azure_utils import upload_json_to_azure, check_azure_connection
# Import the PST conversion utility
from utils.time_utils import convert_to_pst, get_current_pst_time 
# Import the Vector client
from clients.vector_client import VectorClient 

# Define the URL data type for BabyPips
BabyPipsUrlData = Tuple[str, str, datetime, str, str]  # url, title, pubDate, creator, category


class BabyPipsCrawler(BaseCrawlerModule[BabyPipsUrlData]):
    """Crawler for BabyPips website."""
    
    def __init__(self, rss_url: str):
        """Initialize the BabyPips crawler.
        
        Args:
            rss_url: The URL of the RSS feed to crawl.
        """
        super().__init__("babypips")
        self.rss_url = rss_url # Store the RSS URL
    
    async def get_urls(self) -> List[BabyPipsUrlData]:
        """Get URLs from the BabyPips RSS feed.
        
        Returns:
            A list of tuples (url, title, pubDate, creator, category)
        """
        # rss_url = "https://www.babypips.com/feed.rss" # Remove hardcoded URL
        logger.info(f"[{self.name}] Fetching URLs from {self.rss_url}...") # Use logger
        try:
            response = requests.get(self.rss_url) # Use the stored URL
            response.raise_for_status()
            
            root = ElementTree.fromstring(response.content)
            urls = []
            # Get yesterday's date in PST
            current_pst = get_current_pst_time()
            if not current_pst:
                logger.error(f"[{self.name}] Error: Could not determine current PST time for filtering.") # Use logger
                return []
            # Ensure yesterday_pst is timezone-aware for comparison
            yesterday_pst = (current_pst - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            logger.info(f"[{self.name}] Filtering articles published after (PST): {yesterday_pst}") # Use logger

            for item in root.findall('.//item'):
                # Extract and clean CDATA sections
                title_elem = item.find('title')
                link_elem = item.find('link')
                pubDate_elem = item.find('pubDate')
                
                if None in (title_elem, link_elem, pubDate_elem):
                    continue
                    
                title = title_elem.text
                link = link_elem.text
                pubDate = pubDate_elem.text
                
                # Clean CDATA if present
                if title and title.startswith('<![CDATA[') and title.endswith(']]>'):
                    title = title[9:-3]
                    
                # Get creator
                creator = ""
                creator_elem = item.find('.//{http://purl.org/dc/elements/1.1/}creator')
                if creator_elem is not None and creator_elem.text:
                    creator = creator_elem.text
                    if creator.startswith('<![CDATA[') and creator.endswith(']]>'):
                        creator = creator[9:-3]
                
                # Get category
                category = ""
                category_elem = item.find('category')
                if category_elem is not None and category_elem.text:
                    category = category_elem.text
                    if category.startswith('<![CDATA[') and category.endswith(']]>'):
                        category = category[9:-3]

                try:
                    datetime_obj = datetime.strptime(pubDate, "%a, %d %b %Y %H:%M:%S %z")
                    # Convert parsed time to PST for comparison
                    datetime_obj_pst = convert_to_pst(datetime_obj)
                    if datetime_obj_pst and datetime_obj_pst > yesterday_pst:
                        # Append original timezone-aware datetime_obj
                        urls.append((link, title, datetime_obj, creator, category))
                except ValueError as e:
                    logger.error(f"[{self.name}] Error parsing date {pubDate}: {e}") # Use logger
                except Exception as parse_e:
                    logger.error(f"[{self.name}] Unexpected error processing item for URL {link}: {parse_e}", exc_info=True)
                    
            logger.info(f"[{self.name}] Found {len(urls)} recent articles.")
            return urls
        except requests.exceptions.RequestException as req_e:
             logger.error(f"[{self.name}] Error fetching RSS feed: {req_e}", exc_info=True) # Use logger
             return []
        except ElementTree.ParseError as xml_e:
             logger.error(f"[{self.name}] Error parsing XML from {self.rss_url}: {xml_e}", exc_info=True)
             return []
        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error fetching URLs: {e}", exc_info=True) # Use logger
            return []
    
    async def process_url(self, url_data: BabyPipsUrlData, crawler_instance: AsyncWebCrawler) -> bool:
        """Process a single URL from BabyPips.
        
        Args:
            url_data: A tuple (url, title, pubDate, creator, category)
            crawler_instance: The shared AsyncWebCrawler instance.
        
        Returns:
            True if the URL was processed successfully, False otherwise
        """
        url, title, pubDate_datetime_obj, creator, category = url_data
        
        # Check if this URL has already been processed
        if self.url_cache.is_processed(url):
            logger.info(f"[{self.name}] Skipping already processed URL: {url}") # Use logger
            return True
        
        try:
            # Define crawler configuration
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                excluded_tags=['nav', 'footer', 'aside', 'header', 'script', 'style', 'iframe', 'form', 'button', 'input', 'menu', 'menuitem'],
                remove_overlay_elements=True,
                # Target the actual article content, exclude navigation
                css_selector=".full-post .post-content, .entry-content, .article-body, .post-body, .content-body, .full-post .entry, .full-post article",  
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=PruningContentFilter(
                        threshold=0.85,
                        threshold_type="fixed",
                        min_word_threshold=50,  # Reverted to original
                        user_query="Main article content only, exclude navigation and site branding"
                    ),
                    options={
                        "ignore_links": True,
                        "ignore_images": True,
                        "ignore_tables": True,
                        "ignore_horizontal_rules": True
                    }
                ),
            )
            
            # Run crawler using the passed instance
            session_id = f"babypips_session_{url[:50]}" # Use slicing for safety
            result = await crawler_instance.arun( # Use passed crawler_instance
                url=url,
                config=crawl_config,
                session_id=session_id
            )
            
            if result.success and result.markdown and result.markdown.raw_markdown: # Check markdown content
                logger.info(f"[{self.name}] Successfully crawled: {url}") # Use logger
                
                # Create a safe title part for the filename/blob name
                safe_title_part = re.sub(r'[^\w\-_.]', '_', title)[:200]

                # Clean and format the markdown content
                logger.info(f"[{self.name}] Original content length: {len(result.markdown.raw_markdown)} characters")
                logger.info(f"[{self.name}] Original content preview: {result.markdown.raw_markdown[:200]}...")
                
                cleaned_markdown = clean_markdown(result.markdown.raw_markdown)
                
                logger.info(f"[{self.name}] Cleaned content length: {len(cleaned_markdown)} characters")
                logger.info(f"[{self.name}] Cleaned content preview: {cleaned_markdown[:200]}...")
                
                # Include metadata in the markdown
                cleaned_markdown = (f'# {title}\n\n'
                                 f'Author: {creator}\n'
                                 f'Category: {category}\n\n'
                                 f'{cleaned_markdown}')
                
                logger.info(f"[{self.name}] Final content length (with metadata): {len(cleaned_markdown)} characters")
                
                # Prepare article data
                article = OutputModel(
                    title=title,
                    # Store the original timezone-aware datetime object
                    publishDate=pubDate_datetime_obj, 
                    content=cleaned_markdown,
                    url=url
                )
                
                # Convert publish date to PST and add to model
                publish_date_pst = convert_to_pst(pubDate_datetime_obj) 
                if publish_date_pst:
                    article.publishDatePst = publish_date_pst
                else:
                    logger.warning(f"Could not convert publishDate {pubDate_datetime_obj} to PST for article {url}")

                # Add additional metadata
                # Use the model's to_dict method for serialization
                article_dict = article.to_dict() 
                article_dict.update({
                    "_source": self.name, 
                    "_author": creator,   
                    "_category": category,
                    "_crawled_at": get_timestamp(),
                    "_article_id": generate_id()
                })
                
                # --- Check Azure Connection --- 
                azure_ok = check_azure_connection()
                if not azure_ok:
                    logger.error(f"[{self.name}] Skipping Azure upload for {url} due to connection issue.")
                else:
                    # --- Save to Azure (Existing) ---
                    logger.info(f"[{self.name}] Attempting Azure upload for {url}...")
                    success, msg = upload_json_to_azure(
                        article_dict, 
                        blob_name=f"{self.name}-{safe_title_part}.json", # Use self.name
                        publish_date_pst=article.publishDatePst # Pass the PST date
                    )
                    if not success:
                        logger.error(f"[{self.name}] Azure upload failed for {url}: {msg}")

                # --- Index in Vector Service (with Metadata) --- 
                vector_client = None # Define outside try for finally block
                try:
                    vector_client = VectorClient()
                    logger.info(f"[{self.name}] Attempting to add document (length: {len(cleaned_markdown)}) to {vector_client.backend}...")
                    
                    # Prepare metadata - ensure datetime is ISO format string
                    doc_metadata = {
                        "publishDatePst": article.publishDatePst.isoformat() if article.publishDatePst else None,
                        "source": article_dict.get("_source"),
                        "author": article_dict.get("_author"),
                        "category": article_dict.get("_category"),
                        "article_id": article_dict.get("_article_id")
                    }
                    # Remove None values from metadata
                    doc_metadata = {k: v for k, v in doc_metadata.items() if v is not None}

                    # Pass metadata to add_document
                    add_result = await vector_client.add_document(cleaned_markdown, metadata=doc_metadata)
                    
                    if add_result:
                        logger.info(f"[{self.name}] {vector_client.backend} add document result: Status='{add_result.get('status')}', Message='{add_result.get('message')}'")
                    else:
                        logger.error(f"[{self.name}] Failed to add document {url} to {vector_client.backend}.")
                except ValueError as ve: # Catch client init error
                     logger.error(f"[{self.name}] Vector client init failed, cannot index document {url}: {ve}")
                except Exception as vector_err:
                    logger.error(f"[{self.name}] Error adding document {url} to {vector_client.backend}: {vector_err}", exc_info=True)
                finally:
                    if vector_client:
                        await vector_client.close()
                # --- End Vector Service Indexing --- 

                # Mark this URL as processed
                self.url_cache.mark_processed(url)
                
                logger.info(f"[{self.name}] Successfully processed and saved: {url}") # Use logger
                logger.info(f"[{self.name}] Content length: {len(cleaned_markdown)}") # Use logger
                return True
            else:
                error_msg = result.error_message if result else "Unknown error or empty content"
                logger.error(f"[{self.name}] Crawling failed for {url}: {error_msg}") # Use logger
                return False
        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error processing {url}: {e}", exc_info=True) # Use logger
            return False