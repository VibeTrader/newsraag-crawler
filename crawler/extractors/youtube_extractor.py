"""
YouTube Extractor using YouTube Data API + Transcript API
Adapted from YoutubeRagnarok implementation
"""
from typing import List, Optional
from datetime import datetime
import pytz
from loguru import logger
import os
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from crawler.interfaces import ArticleMetadata, SourceConfig
import re


class YouTubeExtractor:
    """Extract videos and transcripts from YouTube channels using Google API."""
    
    def __init__(self, config: SourceConfig):
        self.config = config
        self.channel_url = config.base_url
        self.channel_id = None
        self.api_key = os.getenv('YOUTUBE_API_KEY') or os.getenv('GOOGLE_API_KEY')
        self.youtube_api = None
        
        # Initialize YouTube API if key available
        if self.api_key:
            try:
                from googleapiclient.discovery import build
                os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
                self.youtube_api = build('youtube', 'v3', developerKey=self.api_key)
                logger.info(f"✅ YouTube Data API initialized for {config.name}")
            except Exception as e:
                logger.warning(f"Failed to initialize YouTube API: {e}")
                self.youtube_api = None
        else:
            logger.warning(f"No YouTube API key found for {config.name}, will use RSS fallback")
    
    def _extract_channel_identifier(self, url: str) -> tuple[str, str]:
        """Extract channel identifier from URL."""
        if "/channel/" in url:
            channel_id = url.split("/channel/")[-1].strip().split("/")[0]
            return ('channel_id', channel_id)
        elif "@" in url:
            handle = url.split("@")[-1].strip().split("/")[0]
            return ('handle', f"@{handle}")
        return ('unknown', url.split("/")[-1].strip())
    
    async def discover_videos(self, max_videos: int = 10) -> List[ArticleMetadata]:
        """Discover recent videos using YouTube Data API or RSS fallback."""
        identifier_type, identifier = self._extract_channel_identifier(self.channel_url)
        logger.info(f"Discovering videos from: {identifier}")
        
        try:
            # Get channel ID if needed
            if identifier_type == 'handle':
                self.channel_id = await self._get_channel_id_from_handle(identifier)
                if not self.channel_id:
                    logger.error(f"Could not resolve channel ID for {identifier}")
                    return []
            else:
                self.channel_id = identifier
            
            # Use YouTube Data API if available, otherwise fallback to RSS
            if self.youtube_api:
                videos = await self._get_videos_via_api(max_videos)
            else:
                videos = await self._get_videos_via_rss(max_videos)
            
            logger.success(f"✅ Got {len(videos)} videos from {self.channel_id}")
            return videos
            
        except Exception as e:
            logger.error(f"Failed to discover videos: {e}")
            return []
    
    async def _get_videos_via_api(self, max_videos: int) -> List[ArticleMetadata]:
        """Get videos using YouTube Data API (from YoutubeRagnarok implementation)."""
        try:
            # Get channel's uploads playlist
            channel_response = self.youtube_api.channels().list(
                part="contentDetails",
                id=self.channel_id
            ).execute()
            
            if not channel_response.get('items'):
                logger.warning(f"No channel found for ID: {self.channel_id}")
                return []
            
            uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get latest videos from uploads playlist
            playlist_response = self.youtube_api.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=max_videos
            ).execute()
            
            videos = []
            for item in playlist_response.get('items', []):
                try:
                    video_data = await self._parse_api_video(item)
                    if video_data:
                        videos.append(video_data)
                except Exception as e:
                    logger.warning(f"Failed to parse video: {e}")
                    continue
            
            return videos
            
        except Exception as e:
            logger.error(f"YouTube API request failed: {e}")
            return []
    
    async def _parse_api_video(self, item) -> Optional[ArticleMetadata]:
        """Parse video from YouTube Data API response."""
        try:
            snippet = item['snippet']
            video_id = snippet['resourceId']['videoId']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            title = snippet['title']
            description = snippet.get('description', '')
            
            # Parse published date
            published_date = self._parse_youtube_date(snippet['publishedAt'])
            if not published_date:
                logger.warning(f"No date found for video: {video_url}")
                return None
            
            # Get transcript
            transcript = await self._get_transcript(video_id)
            content = transcript if transcript else description
            
            if not content or len(content) < 20:
                logger.warning(f"Insufficient content for video: {title}")
                return None
            
            # Create metadata with enhanced YouTube fields
            article_id = f"youtube_{self.config.name}_{video_id}"
            
            return ArticleMetadata(
                title=title,
                url=video_url,
                published_date=published_date,
                source_name=self.config.name,
                article_id=article_id,
                author=self.channel_id,
                category="forex",
                language="en",
                # Enhanced YouTube metadata
                content_type="youtube_transcript",
                video_id=video_id,
                channel_id=self.channel_id,
                has_transcript=bool(transcript)
            )
            
        except Exception as e:
            logger.error(f"Error parsing API video: {e}")
            return None
    
    async def _get_videos_via_rss(self, max_videos: int) -> List[ArticleMetadata]:
        """Fallback: Get videos using RSS feed."""
        import feedparser
        
        try:
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={self.channel_id}"
            logger.info(f"Fetching RSS: {rss_url}")
            
            feed = feedparser.parse(rss_url)
            
            if not feed.entries:
                logger.warning(f"No videos found in RSS feed")
                return []
            
            videos = []
            for entry in feed.entries[:max_videos]:
                try:
                    video_data = await self._parse_rss_video(entry)
                    if video_data:
                        videos.append(video_data)
                except Exception as e:
                    logger.warning(f"Failed to parse RSS video: {e}")
                    continue
            
            return videos
            
        except Exception as e:
            logger.error(f"RSS feed request failed: {e}")
            return []
    
    async def _parse_rss_video(self, entry) -> Optional[ArticleMetadata]:
        """Parse video from RSS feed."""
        try:
            video_url = entry.link
            video_id = self._extract_video_id(video_url)
            
            if not video_id:
                return None
            
            title = entry.title
            description = entry.get('summary', '')
            published_date = self._parse_youtube_date(entry.published)
            
            if not published_date:
                return None
            
            # Get transcript
            transcript = await self._get_transcript(video_id)
            content = transcript if transcript else description
            
            if not content or len(content) < 20:
                return None
            
            article_id = f"youtube_{self.config.name}_{video_id}"
            
            return ArticleMetadata(
                title=title,
                url=video_url,
                published_date=published_date,
                source_name=self.config.name,
                article_id=article_id,
                author=self.channel_id,
                category="forex",
                language="en",
                # Enhanced YouTube metadata
                content_type="youtube_transcript",
                video_id=video_id,
                channel_id=self.channel_id,
                has_transcript=bool(transcript)
            )
            
        except Exception as e:
            logger.error(f"Error parsing RSS video: {e}")
            return None
    
    async def _get_transcript(self, video_id: str) -> Optional[str]:
        """Get transcript using YouTubeTranscriptApi (from YoutubeRagnarok)."""
        try:
            # Add delay to avoid rate limiting
            import asyncio
            await asyncio.sleep(3)  # 3 second delay
            
            # Use YouTubeTranscriptApi (same as YoutubeRagnarok)
            ytt_api = YouTubeTranscriptApi()
            transcript = ytt_api.fetch(
                video_id,
                languages=['en', 'en-US', 'en-GB', 'en-AU', 'en-CA', 'fr', 'de', 'es', 'it', 'pt', 'ru', 'zh-CN', 'ja', 'ko']
            )
            
            # Format transcript using TextFormatter (same as YoutubeRagnarok)
            formatter = TextFormatter()
            text_formatted = formatter.format_transcript(transcript)
            
            if text_formatted:
                logger.success(f"✅ Got transcript for {video_id} ({len(text_formatted)} chars)")
                return text_formatted
            else:
                return None
                
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            logger.debug(f"No transcript for {video_id}: {type(e).__name__}")
            return None
        except Exception as e:
            logger.debug(f"Could not get transcript for {video_id}: {type(e).__name__}")
            return None
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'^([0-9A-Za-z_-]{11})$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _parse_youtube_date(self, date_str: str) -> Optional[datetime]:
        """Parse date from YouTube format to datetime."""
        try:
            parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=pytz.UTC)
            
            return parsed_date
            
        except Exception as e:
            logger.error(f"Error parsing date '{date_str}': {e}")
            return None
    
    async def _get_channel_id_from_handle(self, handle: str) -> Optional[str]:
        """Resolve channel ID from @handle by scraping."""
        import aiohttp
        
        try:
            url = f"https://www.youtube.com/{handle}"
            logger.info(f"Resolving channel ID from: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        logger.error(f"HTTP {response.status} when fetching {url}")
                        return None
                    
                    html = await response.text()
                    
                    # Try multiple patterns to find channel ID
                    patterns = [
                        r'"channelId":"([^"]+)"',
                        r'"browseId":"([^"]+)"',
                        r'/channel/(UC[a-zA-Z0-9_-]{22})',
                        r'channelId=([^&"\s]+)'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, html)
                        if match:
                            channel_id = match.group(1)
                            if channel_id.startswith('UC') and len(channel_id) == 24:
                                logger.success(f"✅ Resolved {handle} → {channel_id}")
                                return channel_id
                    
                    logger.warning(f"Could not find channel ID for {handle}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error resolving channel ID: {e}")
            return None
