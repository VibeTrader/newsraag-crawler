"""
RSS feed crawler module for NewsRagnarok Crawler.
"""
import asyncio
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Any
from loguru import logger
import email.utils

from crawler.extractors.article_extractor import extract_full_content
from utils.time_utils import get_current_pst_time

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
        
        # Filter for articles from the last day instead of just 7 days
        # Since we're running hourly now, we can reduce the look-back period
        day_ago_pst = (current_pst - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        logger.info(f"Filtering articles published after (PST): {day_ago_pst}")
        
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
                        parsed_date = email.utils.parsedate_to_datetime(published)
                        pub_date = parsed_date
                    except:
                        logger.warning(f"Could not parse date: {published}")
                
                # Filter by date
                if pub_date < day_ago_pst:
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
