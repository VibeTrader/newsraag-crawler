"""
ForexLive crawler module with LLM-based content cleaning.
"""
import re
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from loguru import logger
import requests
from xml.etree import ElementTree

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from models.output import OutputModel
from utils.clean_markdown import clean_markdown
from crawler.base import BaseCrawlerModule 
from utils.dir_utils import get_output_dir, generate_id, get_timestamp
from utils.azure_utils import upload_json_to_azure, check_azure_connection
from utils.time_utils import convert_to_pst, get_current_pst_time 
from clients.vector_client import VectorClient

# Import LLM cleaner and environment validator
from utils.llm.cleaner import create_llm_cleaner
from utils.config.env_validator import EnvironmentValidator

# Define the URL data type for ForexLive
ForexLiveUrlData = Tuple[str, str, datetime]  # url, title, pubDate

class ForexLiveCrawler(BaseCrawlerModule[ForexLiveUrlData]):
    """Crawler for ForexLive website with LLM-based content cleaning."""
    
    def __init__(self, rss_url: str = "https://www.forexlive.com/feed/"):
        """Initialize the ForexLive crawler.
        
        Args:
            rss_url: The URL of the RSS feed to crawl.
        """
        super().__init__("forexlive")
        self.rss_url = rss_url
        
        # Check if LLM cleaning is enabled
        self.use_llm_cleaning = EnvironmentValidator.is_llm_cleaning_enabled()
        logger.info(f"[{self.name}] LLM cleaning is {'enabled' if self.use_llm_cleaning else 'disabled'}")    
    async def get_urls(self) -> List[ForexLiveUrlData]:
        """Get URLs from the ForexLive RSS feed.
        
        Returns:
            A list of tuples (url, title, pubDate)
        """
        logger.info(f"[{self.name}] Fetching URLs from {self.rss_url}...")
        try:
            response = requests.get(self.rss_url)
            response.raise_for_status() # Raise HTTPError for bad responses
            
            root = ElementTree.fromstring(response.content)
            urls = []
            
            # Get the start of yesterday in PST for filtering
            current_pst = get_current_pst_time()
            if not current_pst:
                logger.error(f"[{self.name}] Could not determine current PST time for filtering. Aborting URL fetch.")
                return []
            yesterday_pst = (current_pst - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            logger.info(f"[{self.name}] Filtering articles published after (PST): {yesterday_pst}")

            for item in root.findall('.//item'):
                link_elem = item.find('link')
                title_elem = item.find('title')
                pubDate_elem = item.find('pubDate')
                
                # ForexLive RSS does not seem to have author/category readily available in standard tags
                
                if None in (link_elem, title_elem, pubDate_elem) or not all(e.text for e in [link_elem, title_elem, pubDate_elem]):
                    logger.warning(f"[{self.name}] Skipping item due to missing link, title, or pubDate element/text.")
                    continue
                    
                link = link_elem.text
                title = title_elem.text
                pubDate_str = pubDate_elem.text
                
                try:
                    # Parse the original date string (e.g., "Mon, 29 Jul 2024 10:00:00 GMT")
                    # Note: ForexLive uses GMT which is equivalent to UTC or %z = +0000
                    # We will parse it as timezone-aware
                    datetime_obj = datetime.strptime(pubDate_str, "%a, %d %b %Y %H:%M:%S %Z") 
                    # Ensure it's timezone-aware (strptime with %Z should handle GMT)
                    if datetime_obj.tzinfo is None:
                         # If somehow %Z didn't work, assume GMT/UTC
                         datetime_obj = datetime_obj.replace(tzinfo=timezone.utc)

                    # Convert the parsed time to PST for comparison
                    datetime_obj_pst = convert_to_pst(datetime_obj)
                    
                    if datetime_obj_pst and datetime_obj_pst > yesterday_pst:
                        # Append the original timezone-aware datetime object
                        urls.append((link, title, datetime_obj))
                        logger.debug(f"[{self.name}] Added URL: {link} (Published PST: {datetime_obj_pst})")
                    else:
                         logger.trace(f"[{self.name}] Skipping old article: {link} (Published PST: {datetime_obj_pst})")

                except ValueError as e:
                    logger.error(f"[{self.name}] Error parsing date '{pubDate_str}' for URL {link}: {e}")
                except Exception as parse_e:
                     logger.error(f"[{self.name}] Unexpected error processing item for URL {link}: {parse_e}", exc_info=True)

            logger.info(f"[{self.name}] Found {len(urls)} recent articles.")        
            return urls
        except requests.exceptions.RequestException as req_e:
            logger.error(f"[{self.name}] Error fetching RSS feed from {self.rss_url}: {req_e}", exc_info=True)
            return []
        except ElementTree.ParseError as xml_e:
            logger.error(f"[{self.name}] Error parsing XML from {self.rss_url}: {xml_e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error fetching URLs: {e}", exc_info=True)
            return []
    async def process_url(self, url_data: ForexLiveUrlData, crawler_instance: AsyncWebCrawler) -> bool:
        """Process a single URL from ForexLive.
        
        Args:
            url_data: A tuple (url, title, pubDate)
            crawler_instance: The shared AsyncWebCrawler instance.
        
        Returns:
            True if the URL was processed successfully, False otherwise
        """
        url, title, pubDate_datetime_obj = url_data
        
        # Check if this URL has already been processed
        if self.url_cache.is_processed(url):
            logger.info(f"[{self.name}] Skipping already processed URL: {url}")
            return True
        
        logger.info(f"[{self.name}] Processing URL: {url}")
        
        try:
            # Define crawler configuration - Target the actual article page content
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                # Enhanced selectors for ForexLive
                css_selector=".article-content, .post-content, .entry-content, .story-content, .article-body, .post-body, .content-body, .entry", 
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=PruningContentFilter(
                        threshold=0.85,  # Lower threshold to be more inclusive
                        threshold_type="fixed",
                        min_word_threshold=50,  # Lower word threshold
                        user_query="Main article content only"
                    ),
                    options={ 
                        "ignore_links": True,
                        "ignore_images": True,
                        "ignore_tables": False,  # Allow tables
                        "ignore_horizontal_rules": True
                    }
                ),
                excluded_tags=['nav', 'footer', 'aside', 'header', 'script', 'style', 'iframe', 'form', 'button', 'input', 'menu', 'menuitem'],
                remove_overlay_elements=True,
                # Use a longer timeout
                timeout_ms=60000  # 60 second timeout
            )
            
            # Run crawler using the passed instance on the article URL
            session_id = f"forexlive_session_{url[:50]}"
            result = await crawler_instance.arun( # Use passed crawler_instance
                url=url, # Crawl the actual article URL
                config=crawl_config,
                session_id=session_id
            )
            
            if result.success and result.markdown and result.markdown.raw_markdown:
                logger.info(f"[{self.name}] Successfully crawled: {url}")
                
                # Log original content
                logger.info(f"[{self.name}] Original content length: {len(result.markdown.raw_markdown)} characters")
                logger.info(f"[{self.name}] Original content preview: {result.markdown.raw_markdown[:200]}...")
                
                # Initialize variables for extracted metadata and cleaning method
                extracted_metadata = {}
                cleaned_markdown = None
                cleaning_method = "none"
                author = None
                category = None
                
                # Clean content using LLM if enabled
                if self.use_llm_cleaning:
                    logger.info(f"[{self.name}] Attempting LLM-based content cleaning for {url}")
                    llm_cleaner = create_llm_cleaner()
                    llm_result = await llm_cleaner.clean_content(
                        result.markdown.raw_markdown,
                        self.name,
                        url
                    )
                    
                    if llm_result:
                        cleaned_markdown, extracted_metadata = llm_result
                        cleaning_method = "llm"
                        
                        # Update metadata with extracted information
                        if extracted_metadata.get("title") and not title:
                            title = extracted_metadata.get("title")
                        if extracted_metadata.get("author"):
                            author = extracted_metadata.get("author")
                        if extracted_metadata.get("category"):
                            category = extracted_metadata.get("category")
                            
                        logger.info(f"[{self.name}] Successfully cleaned content with LLM")
                    else:
                        # If LLM cleaning fails, log error and skip processing
                        logger.error(f"[{self.name}] LLM cleaning failed. Skipping URL: {url}")
                        return False
                else:
                    # Use traditional regex-based cleaning
                    logger.info(f"[{self.name}] Using regex-based content cleaning")
                    cleaned_markdown = clean_markdown(result.markdown.raw_markdown)
                    cleaning_method = "regex"
                
                logger.info(f"[{self.name}] Cleaned content length: {len(cleaned_markdown)} characters")
                logger.info(f"[{self.name}] Cleaned content preview: {cleaned_markdown[:200]}...")
                
                # Include metadata in the markdown if needed
                if not cleaned_markdown.startswith(f'# {title}'):
                    metadata_header = f'# {title}\n\n'
                    if author:
                        metadata_header += f'Author: {author}\n\n'
                    if category:
                        metadata_header += f'Category: {category}\n\n'
                    
                    cleaned_markdown = metadata_header + cleaned_markdown
                
                # Prepare article data using OutputModel
                article = OutputModel(
                    title=title,
                    publishDate=pubDate_datetime_obj, # Store original timezone-aware datetime
                    content=cleaned_markdown,
                    url=url
                )
                
                # Convert publish date to PST and add to model
                publish_date_pst = convert_to_pst(pubDate_datetime_obj) 
                if publish_date_pst:
                    article.publishDatePst = publish_date_pst
                else:
                    logger.warning(f"[{self.name}] Could not convert publishDate {pubDate_datetime_obj} to PST for article {url}")

                # Add additional metadata
                article_dict = article.to_dict() 
                article_dict.update({
                    "_source": self.name,
                    "_author": author,
                    "_category": category,
                    "_crawled_at": get_timestamp(),
                    "_article_id": generate_id(),
                    "_cleaning_method": cleaning_method
                })
                
                # --- Azure Integration --- 
                azure_ok = check_azure_connection()
                if not azure_ok:
                    logger.error(f"[{self.name}] Skipping Azure upload for {url} due to connection issue.")
                else:
                    logger.info(f"[{self.name}] Attempting Azure upload for {url}...")
                    safe_title_part = re.sub(r'[^\w\-_.]', '_', title)[:200]
                    success, msg = upload_json_to_azure(
                        article_dict, 
                        blob_name=f"{self.name}-{safe_title_part}.json",
                        publish_date_pst=article.publishDatePst # Pass the PST date
                    )
                    if not success:
                        logger.error(f"[{self.name}] Azure upload failed for {url}: {msg}")

                # --- Vector Service Integration --- 
                vector_client = None
                try:
                    vector_client = VectorClient()
                    logger.info(f"[{self.name}] Attempting to add document (length: {len(cleaned_markdown)}) to {vector_client.backend} for {url}...")
                    
                    # Prepare metadata - filter None values
                    doc_metadata = {
                        "publishDatePst": article.publishDatePst.isoformat() if article.publishDatePst else None,
                        "source": article_dict.get("_source"),
                        "author": article_dict.get("_author"),
                        "category": article_dict.get("_category"),
                        "article_id": article_dict.get("_article_id"),
                        "cleaning_method": article_dict.get("_cleaning_method")
                    }
                    doc_metadata = {k: v for k, v in doc_metadata.items() if v is not None}

                    add_result = await vector_client.add_document(cleaned_markdown, metadata=doc_metadata)
                    
                    if add_result:
                        logger.info(f"[{self.name}] Vector service add document result for {url}: Status='{add_result.get('status')}', Message='{add_result.get('message')}'")
                    else:
                        logger.error(f"[{self.name}] Failed to add document {url} to vector service.")
                except ValueError as ve: 
                     logger.error(f"[{self.name}] Vector client init failed, cannot index document {url}: {ve}")
                except Exception as vector_err:
                    logger.error(f"[{self.name}] Error adding document {url} to vector service: {vector_err}", exc_info=True)
                finally:
                    if vector_client:
                        await vector_client.close()
                # --- End Vector Service Integration ---

                # Mark this URL as processed only after successful steps
                self.url_cache.mark_processed(url)
                logger.info(f"[{self.name}] Successfully processed and saved: {url}")
                logger.info(f"[{self.name}] Content length: {len(cleaned_markdown)}")
                return True # Indicate success
            else:
                error_msg = result.error_message if result else "Unknown error or empty content"
                logger.error(f"[{self.name}] Crawling failed for {url}: {error_msg}")
                return False # Indicate failure
        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error processing URL {url}: {e}", exc_info=True)
            return False # Indicate failure