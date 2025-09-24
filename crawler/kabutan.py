"""
Kabutan crawler module with LLM-based content cleaning.
"""
import re
import os
from datetime import datetime, date
import pytz
from typing import List, Tuple, Dict, Any, Optional
from loguru import logger
from dotenv import load_dotenv
import asyncio
import hashlib
import requests
from bs4 import BeautifulSoup
import openai
import json

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from utils.clean_markdown import clean_markdown
from utils.dir_utils import get_output_dir, generate_id, get_timestamp
from utils.azure_utils import upload_json_to_azure, list_blobs_by_date_prefix, construct_blob_path, check_azure_connection
from utils.time_utils import convert_to_pst, get_current_pst_time
from clients.vector_client import VectorClient

# Import LLM cleaner and environment validator
from utils.llm.cleaner import create_llm_cleaner
from utils.config.env_validator import EnvironmentValidator

# Load environment variables from .env file
load_dotenv()

# Define the Kabutan news list URL and Tokyo timezone
KABUTAN_NEWS_URL = "https://kabutan.jp/news/marketnews/"
TOKYO_TZ = pytz.timezone("Asia/Tokyo")

class KabutanCrawler:
    """Crawler for Kabutan.jp website with LLM-based content cleaning. Fetches, parses, cleans, stores, and indexes news articles. Includes optional translation."""
    
    def __init__(self, translate_env_var="KABUTAN_TRANSLATE_ENABLED"):
        """Initialize the Kabutan crawler with optional translation.

        Args:
            translate_env_var (str): Environment variable name to check for enabling translation (defaults to KABUTAN_TRANSLATE_ENABLED).
                                      Set this variable to "true" (case-insensitive) to enable translation.
        """
        self.name = "kabutan"
        logger.info(f"[{self.name}] Initializing KabutanCrawler")

        # Translation Setup
        self.api_key = os.getenv("OPENAI_API_KEY")
        # Default to gpt-4o-mini if not specified
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.translate_content = os.getenv(translate_env_var, "false").lower() == "true"
        self.openai_client = None

        if self.translate_content:
            if not self.api_key:
                logger.warning(f"[{self.name}] {translate_env_var} is true, but OPENAI_API_KEY is not set. Translation DISABLED.")
                self.translate_content = False
            else:
                try:
                    self.openai_client = openai.AsyncOpenAI( # Use AsyncOpenAI
                        api_key=self.api_key,
                        base_url=self.openai_base_url
                    )
                    logger.info(f"[{self.name}] Translation ENABLED using model: {self.openai_model}")
                except Exception as e:
                     logger.error(f"[{self.name}] Failed to initialize OpenAI client: {e}. Translation DISABLED.")
                     self.translate_content = False
        else:
             logger.info(f"[{self.name}] Translation DISABLED ({translate_env_var} is not 'true' or missing).")

        # Check if LLM cleaning is enabled
        self.use_llm_cleaning = EnvironmentValidator.is_llm_cleaning_enabled()
        logger.info(f"[{self.name}] LLM cleaning is {'enabled' if self.use_llm_cleaning else 'disabled'}")

        # Initialize Qdrant vector client
        try:
            self.vector_client = VectorClient()
        except ValueError as e:
            logger.error(f"[{self.name}] Failed to initialize VectorClient: {e}. Indexing will fail.")
            self.vector_client = None            
    async def close(self):
        """Closes the vector client connection."""
        if self.vector_client:
            logger.info(f"[{self.name}] Closing vector client...")
            await self.vector_client.close()

    def _parse_date(self, date_str: str, year: int) -> datetime | None:
        """
        Parses the date string from Kabutan (e.g., 'MM/DD HH:MM') and makes it timezone-aware (Asia/Tokyo).
        Assumes the year is the current year unless specified otherwise.
        """
        try:
            # Assuming format 'MM/DD HH:MM' - ADJUST if needed
            parsed_dt = datetime.strptime(f"{year}/{date_str}", "%Y/%m/%d %H:%M")
            # Make the datetime timezone-aware with Tokyo timezone
            aware_dt = TOKYO_TZ.localize(parsed_dt)
            return aware_dt
        except ValueError as e:
            logger.error(f"[{self.name}] Error parsing date string '{date_str}': {e}. Check format.")
            return None
        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error parsing date '{date_str}': {e}")
            return None

    async def fetch_article_urls(self, current_date: date = None) -> List[Dict[str, Any]]:
        """
        Fetches article URLs from Kabutan news page.
        
        Args:
            current_date: Date to use for article date parsing (defaults to today in Tokyo).
                          This helps convert partial date strings (MM/DD) to full dates.
        
        Returns:
            List of article data dictionaries with 'url', 'title', 'date', 'category'
            sorted by date (newest first).
        """
        # Use Tokyo's current date if not specified
        if current_date is None:
            tokyo_now = datetime.now(TOKYO_TZ)
            current_date = tokyo_now.date()
        
        current_year = current_date.year
            
        logger.info(f"[{self.name}] Fetching news article URLs from: {KABUTAN_NEWS_URL}")
        
        try:
            response = requests.get(KABUTAN_NEWS_URL, timeout=30)
            response.raise_for_status()  # Raises exception for 4XX/5XX responses
            response.encoding = 'utf-8'  # Ensure proper encoding for Japanese text
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all news items on the page (adjust selectors based on site structure)
            articles = []
            
            # Yesterday's date in Tokyo timezone for filtering recent articles
            tokyo_now = datetime.now(TOKYO_TZ)
            yesterday_tokyo = (tokyo_now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            logger.info(f"[{self.name}] Filtering articles published after (Tokyo): {yesterday_tokyo}")
            
            # Find news table - Update these selectors to match actual HTML structure
            news_table = soup.select_one('table.s_news_list')
            if not news_table:
                logger.error(f"[{self.name}] Failed to find news table on page. Check selector.")
                return []
            
            news_rows = news_table.select('tr:has(th a)')  # Select rows with link in th
            if not news_rows:
                logger.error(f"[{self.name}] Found news table but no news rows. Check selector.")
                return []
                
            logger.info(f"[{self.name}] Found {len(news_rows)} news rows in table.")
                
            for row in news_rows:
                try:
                    # Extract article details from row
                    link_elem = row.select_one('th a') 
                    if not link_elem or not link_elem.has_attr('href'):
                        continue
                    
                    # Get relative URL and make absolute
                    rel_url = link_elem['href']
                    url = f"https://kabutan.jp{rel_url}"
                    
                    # Get title
                    title = link_elem.get_text().strip()
                    
                    # Get date string - ADJUST selector to match actual HTML
                    date_cell = row.select_one('td.news_time')
                    if not date_cell:
                        logger.warning(f"[{self.name}] Could not find date for article: {title[:30]}")
                        continue
                    date_str = date_cell.get_text().strip()
                    
                    # Get category - ADJUST selector to match actual HTML
                    category_cell = row.select_one('td.news_category')
                    category = category_cell.get_text().strip() if category_cell else "General"
                    
                    # Parse date with current year
                    pub_date = self._parse_date(date_str, current_year) 
                    if not pub_date:
                        logger.warning(f"[{self.name}] Could not parse date '{date_str}' for article: {title[:30]}. Skipping.")
                        continue
                    
                    # Check if article is recent enough
                    if pub_date >= yesterday_tokyo:
                        # Convert to PST for standard storage convention
                        pub_date_pst = convert_to_pst(pub_date)
                        if not pub_date_pst:
                            logger.error(f"[{self.name}] Could not convert date to PST: {pub_date}. Using original date.")
                            pub_date_pst = pub_date
                        
                        articles.append({
                            'url': url,
                            'title': title,
                            'date': pub_date,
                            'date_pst': pub_date_pst,
                            'category': category
                        })
                    else:
                        logger.debug(f"[{self.name}] Skipping older article: {title[:30]} from {pub_date}")
                except Exception as e:
                    logger.error(f"[{self.name}] Error processing news row: {e}")
                    continue
            
            # Sort by date, newest first
            articles.sort(key=lambda x: x['date'], reverse=True)
            logger.info(f"[{self.name}] Found {len(articles)} recent articles from Kabutan.")
            
            return articles
        
        except requests.exceptions.RequestException as e:
            logger.error(f"[{self.name}] Error fetching news list page: {e}")
            return []
        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error in fetch_article_urls: {e}", exc_info=True)
            return []    
    async def _translate_content(self, title: str, content: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Translates article title and content from Japanese to English using Azure OpenAI.
        
        Args:
            title: The Japanese article title
            content: The Japanese article content
            
        Returns:
            Tuple of (translated_title, translated_content), or (None, None) if translation fails
        """
        if not self.openai_client or not self.translate_content:
            logger.warning(f"[{self.name}] Translation not enabled or OpenAI client not initialized.")
            return None, None
            
        if not title or not content:
            logger.warning(f"[{self.name}] Cannot translate empty title or content.")
            return None, None
            
        log_prefix = f"[{self.name}] [Translation]"
        
        # Generate a content hash for logging
        content_hash = hashlib.md5(content[:100].encode('utf-8')).hexdigest()[:8]
        logger.info(f"{log_prefix} Translating article {content_hash}: {title[:30]}...")
        
        try:
            # Prepare system prompt for translation
            system_prompt = """You are a professional Japanese to English translator specializing in financial news. 
            Translate the provided Japanese financial article into clear, professional English.
            Preserve financial terms, company names, numerical data, and dates accurately.
            Return ONLY a JSON object with two fields: 
            "translated_title": <the English title>,
            "translated_content": <the English content in Markdown format>
            Don't include any explanations or notes outside the JSON object."""
            
            # Prepare user prompt with content to translate
            user_message = f"""
            # Japanese Original Title
            {title}
            
            # Japanese Original Content
            {content}
            
            Translate both the title and content to English. Keep formatting (paragraphs, lists) intact.
            """
            
            response = await self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3 # Lower temperature for more factual translation
            )

            response_text = response.choices[0].message.content
            if not response_text:
                 logger.error(f"{log_prefix} OpenAI response was empty.")
                 return None, None


            # Parse the JSON response
            translated = json.loads(response_text)
            translated_title = translated.get("translated_title")
            translated_content = translated.get("translated_content")

            if not translated_title or not translated_content:
                 logger.error(f"{log_prefix} Failed to extract title/content from JSON response: {response_text[:100]}...")
                 return None, None # Indicate partial failure

            logger.info(f"{log_prefix} Translation successful for title: {title[:30]}")
            return translated_title, translated_content

        except json.JSONDecodeError as e:
            logger.error(f"{log_prefix} Failed to parse translation response as JSON: {e}. Response: {response_text[:200]}...")
            return None, None
        except openai.APIError as e:
             logger.error(f"{log_prefix} OpenAI API error during translation: {e}")
             return None, None
        except Exception as e:
            logger.error(f"{log_prefix} Unexpected error during translation: {e}", exc_info=True)
            return None, None
    async def process_url(self, article_data: Dict[str, Any], shared_crawler: AsyncWebCrawler) -> bool:
        """
        Processes a single article: checks cache, fetches content, cleans,
        optionally translates, uploads the combined data as JSON to Azure,
        and indexes in Qdrant.

        Args:
            article_data: Dictionary containing article metadata
                          (url, title, publish_date_pst, category).
            shared_crawler: The shared AsyncWebCrawler instance from main.py.

        Returns:
            True if the article was successfully processed (including already processed)
            or indexed, False otherwise.
        """
        url = article_data.get('url')
        title = article_data.get('title') # Original Title (Japanese)
        category = article_data.get('category')
        date = article_data.get('date')
        date_pst = article_data.get('date_pst')
        
        if not url or not title or not date:
            logger.error(f"[{self.name}] Missing required article data (url/title/date). Cannot process.")
            return False
        
        logger.info(f"[{self.name}] Processing article: {url}")
        
        # Calculate cache key from URL
        cache_key = hashlib.md5(url.encode()).hexdigest()
        
        # Check if already processed in a previous run
        # Using Azure Blob Storage to check for existing articles
        # (this avoids re-crawling and re-translating articles we already processed)
        try:
            existing_blobs = []
            if date_pst:
                # Create date prefix for blob storage (e.g., 2023/09/25/)
                date_prefix = date_pst.strftime("%Y/%m/%d/")
                # List blobs with this date prefix
                existing_blobs = list_blobs_by_date_prefix(date_prefix)
            
            # Check if this URL is already processed (by searching for URL in blob content)
            for blob_name in existing_blobs:
                if cache_key in blob_name or url in blob_name:
                    logger.info(f"[{self.name}] Article already processed and stored: {url}")
                    return True # Already processed, consider this success
        except Exception as e:
            logger.error(f"[{self.name}] Error checking Azure blob cache: {e}")
            # Continue processing (worst case: we re-process an article)
        
        # Crawl article page to get content
        try:
            # Create crawler configuration for Japanese content
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                css_selector=".news_content, .article-content, .content, #readArea, .body", # Adjust selectors for Kabutan
                markdown_generator=DefaultMarkdownGenerator(
                    content_filter=PruningContentFilter(
                        threshold=0.85,  # Lower threshold
                        threshold_type="fixed",
                        min_word_threshold=50,
                        user_query="株式ニュース本文のみ" # Japanese for "Stock news content only"
                    ),
                    options={
                        "ignore_links": True,
                        "ignore_images": True,
                        "ignore_tables": False, # Allow tables for financial data
                        "ignore_horizontal_rules": True
                    }
                ),
                excluded_tags=['nav', 'footer', 'aside', 'header', 'script', 'style', 'iframe', 'form', 'button', 'input', 'menu', 'menuitem'],
                remove_overlay_elements=True,
                # Use a longer timeout for Japanese content
                timeout_ms=60000,  # 60 second timeout
            )
            
            # Run crawler with shared instance
            session_id = f"kabutan_session_{cache_key}"
            result = await shared_crawler.arun(
                url=url,
                config=crawl_config,
                session_id=session_id
            )
            
            if not result.success or not result.markdown or not result.markdown.raw_markdown:
                logger.error(f"[{self.name}] Failed to crawl article: {url}. Error: {result.error_message if result else 'Unknown error'}")
                return False
                
            # Get the raw content
            raw_content = result.markdown.raw_markdown
            
            # Log original content statistics
            logger.info(f"[{self.name}] Raw content length: {len(raw_content)} characters")
            logger.info(f"[{self.name}] Raw content preview: {raw_content[:100]}...")
            
            # Initialize variables
            cleaned_japanese_content = None
            cleaning_method = "none"
            extracted_metadata = {}
            
            # Clean content using LLM if enabled (with Japanese-specific prompt)
            if self.use_llm_cleaning:
                logger.info(f"[{self.name}] Attempting LLM-based content cleaning for {url}")
                llm_cleaner = create_llm_cleaner()
                llm_result = await llm_cleaner.clean_content(
                    raw_content,
                    self.name,
                    url
                )
                
                if llm_result:
                    cleaned_japanese_content, extracted_metadata = llm_result
                    cleaning_method = "llm"
                    
                    # Update metadata with extracted information
                    if extracted_metadata.get("title") and not title:
                        title = extracted_metadata.get("title")
                    if extracted_metadata.get("category") and not category:
                        category = extracted_metadata.get("category")
                        
                    logger.info(f"[{self.name}] Successfully cleaned Japanese content with LLM")
                else:
                    # If LLM cleaning fails, fall back to regex cleaning
                    logger.error(f"[{self.name}] LLM cleaning failed for Japanese content. Using regex cleaning.")
                    cleaned_japanese_content = clean_markdown(raw_content)
                    cleaning_method = "regex_fallback"
            else:
                # Use traditional regex-based cleaning
                logger.info(f"[{self.name}] Using regex-based content cleaning")
                cleaned_japanese_content = clean_markdown(raw_content)
                cleaning_method = "regex"
            
            logger.info(f"[{self.name}] Cleaned Japanese content length: {len(cleaned_japanese_content)} characters")
            
            # Format markdown with title
            if not cleaned_japanese_content.startswith(f'# {title}'):
                cleaned_japanese_content = f"# {title}\n\n{cleaned_japanese_content}"
            
            # Translate if enabled
            translated_title = None
            translated_content = None
            
            if self.translate_content and self.openai_client:
                logger.info(f"[{self.name}] Translating content for {url}")
                translated_title, translated_content = await self._translate_content(title, cleaned_japanese_content)
                
                if translated_title and translated_content:
                    logger.info(f"[{self.name}] Translation successful.")
                else:
                    logger.error(f"[{self.name}] Translation failed for {url}")
            
            # Prepare article data
            article = {
                "title": title,
                "title_en": translated_title,
                "content": cleaned_japanese_content,
                "content_en": translated_content,
                "url": url,
                "category": category,
                "publish_date": date.isoformat() if isinstance(date, datetime) else str(date),
                "publish_date_pst": date_pst.isoformat() if isinstance(date_pst, datetime) else str(date_pst),
                "_source": self.name,
                "_crawled_at": get_timestamp(),
                "_article_id": generate_id(),
                "_cache_key": cache_key,
                "_cleaning_method": cleaning_method,
                "_translation_status": "success" if translated_content else "disabled" if not self.translate_content else "failed"
            }
            
            # Save to Azure Blob Storage
            azure_ok = check_azure_connection()
            if not azure_ok:
                logger.error(f"[{self.name}] Skipping Azure upload for {url} due to connection issue.")
            else:
                # Safe filename based on date and title
                date_str = date_pst.strftime("%Y-%m-%d") if isinstance(date_pst, datetime) else "unknown-date"
                safe_title = re.sub(r'[^\w\-_.]', '_', title[:50])
                blob_name = f"{self.name}-{date_str}-{cache_key}-{safe_title}.json"
                
                logger.info(f"[{self.name}] Uploading article to Azure: {blob_name}")
                success, msg = upload_json_to_azure(
                    article,
                    blob_name=blob_name,
                    publish_date_pst=date_pst if isinstance(date_pst, datetime) else None
                )
                
                if not success:
                    logger.error(f"[{self.name}] Azure upload failed for {url}: {msg}")
            
            # Index in Qdrant
            if not self.vector_client:
                logger.error(f"[{self.name}] Vector client not initialized, skipping indexing.")
            else:
                try:
                    # Choose which content to index (translated if available, otherwise original)
                    index_content = translated_content if translated_content else cleaned_japanese_content
                    logger.info(f"[{self.name}] Indexing {'translated' if translated_content else 'original'} content ({len(index_content)} chars)")
                    
                    # Prepare metadata - filter None values
                    doc_metadata = {
                        "publishDatePst": date_pst.isoformat() if isinstance(date_pst, datetime) else None,
                        "source": self.name,
                        "author": None, # Kabutan articles don't have author info
                        "category": category,
                        "article_id": article.get("_article_id"),
                        "cleaning_method": cleaning_method,
                        "language": "en" if translated_content else "jp",
                        "translation_status": article.get("_translation_status")
                    }
                    doc_metadata = {k: v for k, v in doc_metadata.items() if v is not None}
                    
                    # Add to vector DB
                    add_result = await self.vector_client.add_document(index_content, metadata=doc_metadata)
                    
                    if add_result:
                        logger.info(f"[{self.name}] Successfully indexed article: {title[:30]}")
                    else:
                        logger.error(f"[{self.name}] Failed to index article: {title[:30]}")
                        
                except Exception as ve:
                    logger.error(f"[{self.name}] Error indexing document: {ve}", exc_info=True)
            
            logger.info(f"[{self.name}] Article processing completed successfully: {url}")
            return True
            
        except Exception as e:
            logger.error(f"[{self.name}] Error processing article {url}: {e}", exc_info=True)
            return False
    async def run(self, shared_crawler: AsyncWebCrawler) -> Tuple[int, int]:
        """
        Main entry point for the Kabutan crawler. Fetches all recent articles
        from Kabutan.jp and processes them.
        
        Args:
            shared_crawler: The shared AsyncWebCrawler instance from main.py.
            
        Returns:
            Tuple of (success_count, error_count)
        """
        logger.info(f"[{self.name}] Starting Kabutan crawler")
        success_count = 0
        error_count = 0
        
        # Fetch all article URLs
        articles = await self.fetch_article_urls()
        
        if not articles:
            logger.warning(f"[{self.name}] No new articles found to process.")
            return 0, 0
        
        # Process each article
        for article in articles:
            try:
                result = await self.process_url(article, shared_crawler)
                if result:
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"[{self.name}] Unexpected error processing article {article.get('url')}: {e}", exc_info=True)
                error_count += 1
                
            # Add small delay between articles to avoid rate limiting
            await asyncio.sleep(1)
            
        logger.info(f"[{self.name}] Completed processing with {success_count} successes and {error_count} errors")
        return success_count, error_count