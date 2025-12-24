"""
Twitter Extractor using Nitter
Scrapes tweets from Twitter profiles via Nitter (no auth needed)
"""
from typing import List, Optional
from datetime import datetime
import pytz
from loguru import logger
from bs4 import BeautifulSoup
import aiohttp
from crawler.interfaces import ArticleMetadata, SourceConfig


class TwitterExtractor:
    """Extract tweets from Twitter profiles using Nitter."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self.profile_name = self._extract_profile_name(config.base_url)
        self.nitter_instances = [
            "https://nitter.net",
            "https://nitter.poast.org",
            "https://nitter.privacydev.net",
            "https://nitter.cz",
            "https://nitter.fdn.fr",
            "https://nitter.1d4.us",
            "https://nitter.kavin.rocks",
            "https://nitter.unixfox.eu",
            "https://nitter.mint.lgbt",
            "https://nitter.esmailelbob.xyz"
        ]
        
    def _extract_profile_name(self, url: str) -> str:
        """Extract Twitter handle from URL."""
        # Handle formats: https://twitter.com/username or @username
        if "@" in url:
            return url.split("@")[-1].strip()
        return url.split("/")[-1].strip()
    
    async def discover_tweets(self, max_tweets: int = 20) -> List[ArticleMetadata]:
        """Discover recent tweets from profile."""
        logger.info(f"Discovering tweets from @{self.profile_name}")
        
        tweets = []
        
        # Try each Nitter instance until one works
        for nitter_url in self.nitter_instances:
            try:
                profile_url = f"{nitter_url}/{self.profile_name}"
                tweets = await self._scrape_nitter(profile_url, max_tweets)
                
                if tweets:
                    logger.success(f"✅ Got {len(tweets)} tweets from {nitter_url}")
                    break
                    
            except Exception as e:
                logger.warning(f"Failed to scrape {nitter_url}: {e}")
                continue
        
        if not tweets:
            logger.error(f"All Nitter instances failed for @{self.profile_name}")
            
        return tweets
    
    async def _scrape_nitter(self, url: str, max_tweets: int) -> List[ArticleMetadata]:
        """Scrape tweets from Nitter instance."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                tweets = []
                tweet_items = soup.find_all('div', class_='timeline-item')[:max_tweets]
                
                for item in tweet_items:
                    try:
                        # Extract tweet data
                        tweet_data = self._parse_tweet_item(item)
                        if tweet_data:
                            tweets.append(tweet_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse tweet: {e}")
                        continue
                
                return tweets
    
    def _parse_tweet_item(self, item) -> Optional[ArticleMetadata]:
        """Parse individual tweet from HTML."""
        try:
            # Get tweet content
            tweet_content_div = item.find('div', class_='tweet-content')
            if not tweet_content_div:
                return None
            
            tweet_text = tweet_content_div.get_text(strip=True)
            if not tweet_text or len(tweet_text) < 10:
                return None
            
            # Get tweet URL
            tweet_link = item.find('a', class_='tweet-link')
            if not tweet_link:
                return None
            
            tweet_url = f"https://twitter.com{tweet_link.get('href')}"
            
            # Get published date/time - CRITICAL for avoiding stale data
            tweet_date_span = item.find('span', class_='tweet-date')
            if not tweet_date_span:
                logger.warning(f"No date found for tweet: {tweet_url}")
                return None
            
            # Parse date from Nitter format
            date_link = tweet_date_span.find('a')
            if date_link and date_link.get('title'):
                date_str = date_link.get('title')
                published_date = self._parse_nitter_date(date_str)
            else:
                logger.warning(f"Could not parse date for tweet: {tweet_url}")
                return None
            
            if not published_date:
                return None
            
            # Create unique article ID
            tweet_id = tweet_url.split('/')[-1]
            article_id = f"twitter_{self.profile_name}_{tweet_id}"
            
            # Create metadata
            return ArticleMetadata(
                title=f"@{self.profile_name}: {tweet_text[:100]}...",
                url=tweet_url,
                published_date=published_date,
                source_name=self.config.name,
                article_id=article_id,
                author=f"@{self.profile_name}",
                category="forex",
                language="en"
            )
            
        except Exception as e:
            logger.error(f"Error parsing tweet item: {e}")
            return None
    
    def _parse_nitter_date(self, date_str: str) -> Optional[datetime]:
        """Parse date from Nitter format to datetime with PST timezone."""
        try:
            # Nitter format: "Jan 15, 2025 · 3:45 PM UTC"
            # Remove the · separator and parse
            date_str = date_str.replace('·', '').strip()
            
            # Try multiple date formats
            formats = [
                "%b %d, %Y %I:%M %p %Z",  # Jan 15, 2025 3:45 PM UTC
                "%b %d, %Y %I:%M %p",      # Jan 15, 2025 3:45 PM
                "%Y-%m-%d %H:%M:%S %Z",    # 2025-01-15 15:45:00 UTC
            ]
            
            parsed_date = None
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if not parsed_date:
                logger.warning(f"Could not parse date: {date_str}")
                return None
            
            # Ensure timezone aware (assume UTC if not specified)
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=pytz.UTC)
            
            return parsed_date
            
        except Exception as e:
            logger.error(f"Error parsing Nitter date '{date_str}': {e}")
            return None
