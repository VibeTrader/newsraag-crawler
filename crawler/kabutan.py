"""
Kabutan crawler module.
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

# Load environment variables from .env file
load_dotenv()

# Define the Kabutan news list URL and Tokyo timezone
KABUTAN_NEWS_URL = "https://kabutan.jp/news/marketnews/"
TOKYO_TZ = pytz.timezone("Asia/Tokyo")

class KabutanCrawler:
    """Crawler for Kabutan.jp website. Fetches, parses, cleans, stores, and indexes news articles. Includes optional translation."""
    
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

    def _slugify(self, text: str) -> str:
        """Basic slugify function to create safe filenames."""
        text = re.sub(r'[^\w\s-]', '', text).strip().lower()
        text = re.sub(r'[-\s]+', '-', text)
        return text

    def _generate_blob_name(self, title: str, url: str) -> str:
        """Generates a unique and somewhat readable blob name."""
        slug_title = self._slugify(title)
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8] # Short hash
        # Limit slug length to avoid overly long filenames
        max_slug_len = 50 
        return f"{slug_title[:max_slug_len]}_{url_hash}.json"

    def _check_if_processed(self, blob_name: str, publish_date_pst: datetime) -> bool:
        """Checks if a blob with the given name exists for the specified date."""
        try:
            target_blob_path = construct_blob_path(blob_name, publish_date_pst)
            # We only need the date prefix part for listing
            date_prefix = publish_date_pst.strftime('%Y/%m/%d')
            existing_blobs = list_blobs_by_date_prefix(date_prefix)
            # Check if the *full* constructed path exists in the list
            if target_blob_path in existing_blobs:
                 logger.info(f"[{self.name}] Article already processed (blob exists): {target_blob_path}")
                 return True
            return False
        except Exception as e:
            # Log error but assume not processed to allow processing attempt
            logger.error(f"[{self.name}] Error checking Azure for existing blob {target_blob_path}: {e}")
            return False

    async def get_urls(self) -> list[dict]:
        """
        Fetches the Kabutan market news page, parses it to find articles published
        today (in PST), and returns a list of dictionaries containing article metadata.

        Returns:
            A list of dictionaries, each containing:
            {'url': str, 'title': str, 'publish_date_pst': datetime, 'category': str}
            Returns an empty list if fetching, parsing, or filtering fails.
        """
        logger.debug(f"[{self.name}] Entering get_urls method.")
        articles_today = [] # Initialize default return value
        
        logger.info(f"[{self.name}] Fetching news list from {KABUTAN_NEWS_URL}")
        current_pst_time = get_current_pst_time()
        if not current_pst_time:
            logger.error(f"[{self.name}] Could not determine current PST time. Aborting URL fetch.")
            return []
        
        today_pst = current_pst_time.date()
        current_year = today_pst.year # Use current year for parsing dates

        try:
            # Run synchronous requests.get in a separate thread
            response = await asyncio.to_thread(
                requests.get, KABUTAN_NEWS_URL, timeout=30
            )
            response.raise_for_status()
            
            html_content = response.text 
            detected_encoding = response.apparent_encoding
            logger.debug(f"[{self.name}] Detected encoding: {detected_encoding}")
            logger.debug(f"[{self.name}] Successfully fetched HTML content.")

            # --- Moved parsing inside try block --- 
            logger.info(f"[{self.name}] Parsing HTML content (within try block)")
            soup = BeautifulSoup(html_content, 'html.parser', from_encoding=detected_encoding)
            logger.debug(f"[{self.name}] Successfully created BeautifulSoup object.")
            # --- End Moved --- 

        except requests.exceptions.RequestException as e:
            logger.error(f"[{self.name}] Error fetching Kabutan news list: {e}")
            logger.debug(f"[{self.name}] Exiting get_urls due to RequestException.")
            return []
        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error during fetch/HTML prep/parse: {e}", exc_info=True)
            logger.debug(f"[{self.name}] Exiting get_urls due to unexpected fetch/prep/parse error.")
            return []

        # Now work with the soup object created inside the try block
        news_tables = soup.find_all('table', class_='s_news_list') 
        if not news_tables:
            logger.warning(f"[{self.name}] Could not find any news table elements (table.s_news_list). Check selector.")
            return []
        
        # news_rows = news_table.find_all('tr') # Old logic
        all_rows = []
        for table in news_tables:
            all_rows.extend(table.find_all('tr'))
            
        logger.info(f"[{self.name}] Found {len(all_rows)} potential news rows across {len(news_tables)} tables. Filtering for today (PST: {today_pst}).")

        # Iterate through all found rows
        for row in all_rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 3: continue # Ensure at least 3 cells

                # 1. Extract Date (Index 0 - Correct)
                date_str = cells[0].text.strip() 
                
                # --- Selector Fix --- 
                # 2. Extract Category (Now Index 1)
                category = cells[1].text.strip() # Was cells[2]
                
                # 3. Extract Title and URL (Now Index 2's link)
                title_link = cells[2].find('a') # Was cells[1]
                # --- End Selector Fix --- 

                if not title_link or not title_link.has_attr('href'): continue
                title = title_link.text.strip()
                relative_url = title_link['href']
                
                if relative_url.startswith('/'):
                    base_url = "https://kabutan.jp"
                    url = f"{base_url}{relative_url}"
                else:
                    url = relative_url 

                publish_date_tokyo = self._parse_date(date_str, current_year)
                if not publish_date_tokyo: continue

                publish_date_pst = convert_to_pst(publish_date_tokyo)
                if not publish_date_pst: continue

                if publish_date_pst.date() == today_pst:
                    logger.debug(f"[{self.name}] Found article for today: {title} (Published PST: {publish_date_pst.date()})" )
                    articles_today.append({
                        'url': url,
                        'title': title,
                        'publish_date_pst': publish_date_pst,
                        'category': category,
                    })

            except Exception as e:
                logger.error(f"[{self.name}] Error processing row: {e}. Row content: {row.text[:100]}...")
                continue 

        logger.info(f"[{self.name}] Finished processing. Found {len(articles_today)} articles published today ({today_pst}).")
        logger.debug(f"[{self.name}] Exiting get_urls method successfully with {len(articles_today)} articles.")
        return articles_today

    async def _translate_content_with_openai(self, title: str, content: str) -> Tuple[Optional[str], Optional[str]]:
        """Translate content using OpenAI API directly.

        Args:
            title: The Japanese title to translate
            content: The Japanese content to translate

        Returns:
            Tuple of (translated_title, translated_content). Returns (None, None) on failure.
        """
        log_prefix = f"[{self.name}:Translate]"
        if not self.translate_content or not self.openai_client:
            logger.warning(f"{log_prefix} Translation skipped (disabled or client not initialized).")
            return None, None # Indicate no translation occurred

        try:
            logger.debug(f"{log_prefix} Starting translation for title: {title[:30]}...")
            system_message = """
            You are a professional Japanese to English translator specializing in financial markets.
            Translate the provided Japanese text into natural, accurate English while preserving
            financial terminology, proper names, and the overall meaning.

            Return your response in JSON format with these fields:
            {
                "translated_title": "The translated title in English",
                "translated_content": "The translated content in English"
            }
            """

            # Create a simplified version of content if it's too long for the prompt (adjust token limit as needed)
            # This is a rough estimate; a proper tokenizer would be better for precision.
            max_prompt_chars = 12000 # Rough estimate for ~4k tokens for prompt + response headroom
            content_preview = content
            if len(title) + len(content) > max_prompt_chars:
                 available_chars = max_prompt_chars - len(title) - 100 # Leave headroom
                 content_preview = content[:available_chars] + ("..." if len(content) > available_chars else "")
                 logger.warning(f"{log_prefix} Content truncated for translation prompt (length: {len(content)} -> {len(content_preview)})")


            user_message = f"""
            Please translate the following Japanese financial news to English:

            TITLE: {title}

            CONTENT:
            {content_preview}
            """

            # Make the API call using the async client
            response = await self.openai_client.chat.completions.create(
                model=self.openai_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_message},
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
        publish_date_pst = article_data.get('publish_date_pst')
        category = article_data.get('category')

        processing_success = False
        log_prefix = f"[{self.name}:{title[:20]}]"

        if not shared_crawler:
            logger.error(f"{log_prefix} Invalid shared_crawler instance received.")
            return False
            
        if not all([url, title, publish_date_pst, category]):
             logger.error(f"{log_prefix} Missing essential article data (url, title, date, or category)")
             return False
        
        logger.info(f"{log_prefix} Processing article: {url}")

        # 1. Check cache (using Azure blob existence)
        blob_name = self._generate_blob_name(title, url)
        if self._check_if_processed(blob_name, publish_date_pst):
            logger.info(f"{log_prefix} Status: Already processed.")
            return True

        # 2. Fetch and Clean Content
        logger.debug(f"{log_prefix} Article not cached. Fetching content...")
        try:
            # Define crawler configuration consistent with other crawlers
            crawl_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                # Verify these selectors for Kabutan article pages
                css_selector=".news_det_story, .news_body, #news_text, #main",
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
                        "ignore_tables": True,
                        "ignore_horizontal_rules": True
                    }
                ),
                excluded_tags=['nav', 'footer', 'aside', 'header', 'script', 'style', 'iframe', 'form', 'button', 'input', 'menu', 'menuitem'],
                remove_overlay_elements=True
            )

            # Use arun with CrawlerRunConfig
            session_id = f"kabutan_session_{url[:50]}"
            crawl_result = await shared_crawler.arun(
                url=url,
                config=crawl_config,
                session_id=session_id
            )

            if not crawl_result or not crawl_result.success or not crawl_result.markdown or not crawl_result.markdown.raw_markdown:
                error_msg = crawl_result.error_message if crawl_result else "Crawler returned None"
                if crawl_result and not crawl_result.markdown:
                    error_msg = "Markdown generation failed or content was empty"
                logger.warning(f"{log_prefix} crawl4ai (shared) did not return valid data for URL: {url}. Error: {error_msg}")
                return False

            raw_markdown = crawl_result.markdown.raw_markdown
            cleaned_markdown = clean_markdown(raw_markdown)
            logger.debug(f"{log_prefix} Markdown cleaned (length: {len(cleaned_markdown)}).")

        except Exception as e:
            logger.error(f"{log_prefix} Error during crawl4ai/cleaning for {url}: {e}", exc_info=True)
            return False

        # --- Translation Step ---
        translated_title: Optional[str] = None
        translated_content: Optional[str] = None
        if self.translate_content and cleaned_markdown:
            logger.info(f"{log_prefix} Attempting translation...")
            translated_title, translated_content = await self._translate_content_with_openai(title, cleaned_markdown)
            if translated_title and translated_content:
                 logger.info(f"{log_prefix} Translation successful.")
            else:
                 logger.warning(f"{log_prefix} Translation failed or was skipped. Using original content.")
        elif not cleaned_markdown:
             logger.warning(f"{log_prefix} Skipping translation because cleaned markdown is empty.")


        # 3. Prepare JSON data
        # Ensure publish_date_pst is timezone-aware
        if publish_date_pst.tzinfo is None:
            pst_tz = pytz.timezone("America/Los_Angeles") 
            try:
                publish_date_pst = pst_tz.localize(publish_date_pst) if not publish_date_pst.tzinfo else publish_date_pst.astimezone(pst_tz)
            except Exception as tz_err:
                 logger.error(f"{log_prefix} Failed to make publish_date_pst timezone-aware: {tz_err}")
                 return False
        
        final_data = {
            "source": self.name,
            "url": url,
            "title": title,
            "category": category,
            "publish_date_pst": publish_date_pst.isoformat(),
            "extracted_content_markdown": cleaned_markdown,
            "processing_timestamp_utc": datetime.now(pytz.utc).isoformat()
        }

        # Add translation data if available
        if translated_title and translated_content:
            final_data["translated_title"] = translated_title
            final_data["translated_content_markdown"] = translated_content
            final_data["translation_model"] = self.openai_model
            final_data["translated"] = True
        else:
            final_data["translated"] = False
            final_data["translation_model"] = None

        # 4. Upload to Azure
        logger.info(f"{log_prefix} Uploading processed data to Azure: {blob_name}")
        azure_success, azure_message_or_url = upload_json_to_azure(
            json_data=final_data,
            blob_name=blob_name,
            publish_date_pst=publish_date_pst
        )

        if not azure_success:
            logger.error(f"{log_prefix} Failed to upload to Azure: {azure_message_or_url}")
            return False
        else:
            logger.info(f"{log_prefix} Successfully uploaded to Azure: {azure_message_or_url}")

        # 5. Index in Qdrant
        if not self.vector_client:
            logger.error(f"{log_prefix} Qdrant vector client not initialized; skipping indexing.")
            # If upload succeeded but indexing skipped due to client init error,
            # consider if this should be True or False based on requirements.
            # Let's keep it False as full processing didn't complete.
            return False # Treat as failure if indexing client is missing

        logger.info(f"{log_prefix} Indexing content in Qdrant...")

        # Determine content and title for indexing (prefer translated if available)
        indexing_content = final_data.get("translated_content_markdown", cleaned_markdown)
        # Use translated title if available for metadata, otherwise original
        indexing_metadata_title = final_data.get("translated_title", title)


        qdrant_metadata = {
            "source": final_data["source"],
            "url": final_data["url"],
            "title": indexing_metadata_title, # Use translated title if available
            "original_title": title,          # Always store original title
            "category": final_data["category"],
            "publish_date_pst": final_data["publish_date_pst"],
            "azure_blob_url": azure_message_or_url,
            "translated": final_data.get("translated", False),
            "translation_model": final_data.get("translation_model")
        }

        # Ensure we don't try to index empty content
        if not indexing_content:
             logger.warning(f"{log_prefix} Skipping Qdrant indexing because content is empty (original and translated).")
             # If Azure upload succeeded, maybe return True here? For now, let's say indexing failure = process failure.
             return False


        try:
            vector_response = await self.vector_client.add_document(
                text_content=indexing_content, # Index translated or original content
                metadata=qdrant_metadata
            )
            
            if vector_response and vector_response.get("status") in ["success", "duplicated"]:
                vector_status = vector_response.get("status")
                logger.info(f"{log_prefix} Successfully indexed in {self.vector_client.backend} (Status: {vector_status}).")
                processing_success = True
            else:
                error_detail = vector_response.get("message") if vector_response else "No response/error"
                logger.error(f"{log_prefix} Failed to index in {self.vector_client.backend}: {error_detail}")
                processing_success = False
        
        except Exception as e:
            logger.error(f"{log_prefix} Error during {self.vector_client.backend} indexing for {url}: {e}", exc_info=True)
            processing_success = False

        return processing_success 