"""
PoundSterlingLive crawler module with LLM-based content cleaning.
"""
import re
from datetime import datetime
from typing import List, Tuple
from loguru import logger

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

# Define the URL data type for PoundSterlingLive
PoundSterlingLiveUrlData = Tuple[str, str, datetime]  # url, title, pubDate

class PoundSterlingLiveCrawler(BaseCrawlerModule[PoundSterlingLiveUrlData]):
    """Crawler for PoundSterlingLive website with LLM-based content cleaning."""
    
    def __init__(self, base_url: str = "https://www.poundsterlinglive.com/markets", max_concurrent: int = 3):
        """Initialize the PoundSterlingLive crawler.
        
        Args:
            base_url: The base URL for the news list page.
            max_concurrent: Maximum number of concurrent crawling tasks
        """
        super().__init__("poundsterlinglive", max_concurrent)
        self.base_url = base_url
        self.browser_config = BrowserConfig(
            headless=True,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )
        self.crawler = None # Initialize crawler instance variable
        
        # Check if LLM cleaning is enabled
        self.use_llm_cleaning = EnvironmentValidator.is_llm_cleaning_enabled()
        logger.info(f"[{self.name}] LLM cleaning is {'enabled' if self.use_llm_cleaning else 'disabled'}")
    
    async def initialize_crawler(self):
        """Initializes the shared AsyncWebCrawler instance."""
        if not self.crawler:
            try:
                logger.info(f"[{self.name}] Initializing shared AsyncWebCrawler...")
                self.crawler = AsyncWebCrawler(config=self.browser_config)
                await self.crawler.start()
                logger.info(f"[{self.name}] Shared AsyncWebCrawler initialized successfully.")
            except Exception as e:
                logger.error(f"[{self.name}] Failed to initialize shared AsyncWebCrawler: {e}", exc_info=True)
                self.crawler = None # Ensure crawler is None if init fails
                raise # Re-raise the exception to signal failure

    async def close_crawler(self):
        """Closes the shared AsyncWebCrawler instance."""
        if self.crawler:
            try:
                logger.info(f"[{self.name}] Closing shared AsyncWebCrawler...")
                await self.crawler.close()
                logger.info(f"[{self.name}] Shared AsyncWebCrawler closed.")
            except Exception as e:
                logger.error(f"[{self.name}] Error closing shared AsyncWebCrawler: {e}", exc_info=True)
            finally:
                self.crawler = None # Reset crawler instance

    async def get_urls(self) -> List[PoundSterlingLiveUrlData]:
        """Get URLs from the PoundSterlingLive news list page.
        
        Returns:
            A list of tuples (url, title, pubDate)
        """
        # Implementation based on PRD 5.4
        logger.info(f"[{self.name}] Fetching URLs from {self.base_url}...")
        # TODO: Implement HTML scraping (requests+bs4) for list page, 
        #       fetching individual article pages for dates, and date filtering logic.
        return []    
    async def process_url(self, url_data: PoundSterlingLiveUrlData) -> bool:
        """Process a single URL from PoundSterlingLive.
        
        Args:
            url_data: A tuple (url, title, pubDate)
        
        Returns:
            True if the URL was processed successfully, False otherwise
        """
        url, title, pubDate_datetime_obj = url_data
        
        # Check if this URL has already been processed
        if self.url_cache.is_processed(url):
            logger.info(f"[{self.name}] Skipping already processed URL: {url}")
            return True
        
        # Ensure crawler is initialized before processing
        if not self.crawler:
            logger.error(f"[{self.name}] Crawler not initialized. Cannot process URL: {url}")
            return False

        logger.info(f"[{self.name}] Processing URL: {url}")
        
        try:
            # Define crawler configuration
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                # Improved selectors for PoundSterlingLive
                css_selector=".article-content, .content-main, .content-body, article", 
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=PruningContentFilter(
                        threshold=0.85,
                        threshold_type="fixed",
                        min_word_threshold=50,
                        user_query="Main article content only"
                    ),
                    options={
                        "ignore_links": True,
                        "ignore_images": True,
                        "ignore_tables": False,  # Allow tables for financial data
                        "ignore_horizontal_rules": True
                    }
                ),
                excluded_tags=['nav', 'footer', 'aside', 'header', 'script', 'style', 'iframe', 'form', 'button', 'input', 'menu', 'menuitem'],
                remove_overlay_elements=True
            )
            
            # Run crawler
            session_id = f"poundsterlinglive_session_{url[:50]}"
            result = await self.crawler.arun(
                url=url,
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
                
                # Prepare article data
                article = OutputModel(
                    title=title,
                    publishDate=pubDate_datetime_obj,
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
                
                # Azure integration
                azure_ok = check_azure_connection()
                if not azure_ok:
                    logger.error(f"[{self.name}] Skipping Azure upload for {url} due to connection issue.")
                else:
                    logger.info(f"[{self.name}] Attempting Azure upload for {url}...")
                    safe_title_part = re.sub(r'[^\w\-_.]', '_', title)[:200]
                    success, msg = upload_json_to_azure(
                        article_dict, 
                        blob_name=f"{self.name}-{safe_title_part}.json",
                        publish_date_pst=article.publishDatePst
                    )
                    if not success:
                        logger.error(f"[{self.name}] Azure upload failed for {url}: {msg}")

                # Vector service integration
                vector_client = None
                try:
                    vector_client = VectorClient()
                    logger.info(f"[{self.name}] Attempting to add document to vector service...")
                    
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
                        logger.info(f"[{self.name}] Vector service add document result: {add_result.get('status', 'unknown')}")
                    else:
                        logger.error(f"[{self.name}] Failed to add document to vector service.")
                except ValueError as ve:
                    logger.error(f"[{self.name}] Vector client init failed: {ve}")
                except Exception as vector_err:
                    logger.error(f"[{self.name}] Error adding document to vector service: {vector_err}", exc_info=True)
                finally:
                    if vector_client:
                        await vector_client.close()

                # Mark this URL as processed
                self.url_cache.mark_processed(url)
                logger.info(f"[{self.name}] Successfully processed and saved: {url}")
                return True
            else:
                error_msg = result.error_message if result else "Unknown error"
                logger.error(f"[{self.name}] Crawling failed for {url}: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error processing URL {url}: {e}", exc_info=True)
            return False