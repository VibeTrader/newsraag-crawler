"""
YouTube Content Extractor - Extracts transcript content for YouTube videos.
This is called after discovery to get the actual transcript text.
"""
from typing import Optional
from loguru import logger
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import re
import asyncio

from crawler.interfaces import IContentExtractor, ArticleMetadata, ProcessingResult


class YouTubeContentExtractor(IContentExtractor):
    """
    Extract transcript content from YouTube videos.
    This is the second phase after discovery - it fetches the actual transcript.
    """
    
    def __init__(self, config):
        self.config = config
        self.ytt_api = YouTubeTranscriptApi()
        self.formatter = TextFormatter()
    
    async def extract_content(self, article_meta: ArticleMetadata) -> ProcessingResult:
        """
        Extract transcript content from YouTube video.
        
        Args:
            article_meta: Article metadata with video_id
            
        Returns:
            ProcessingResult with transcript content or error
        """
        try:
            # Get video ID from metadata
            video_id = article_meta.video_id
            
            if not video_id:
                # Try to extract from URL as fallback
                video_id = self._extract_video_id_from_url(article_meta.url)
            
            if not video_id:
                error_msg = f"No video ID found for {article_meta.url}"
                logger.error(error_msg)
                return ProcessingResult(
                    success=False,
                    error=error_msg
                )
            
            # Add delay to avoid rate limiting
            await asyncio.sleep(3)
            
            # Fetch transcript
            logger.info(f"Fetching transcript for video: {video_id}")
            transcript = await self._get_transcript(video_id)
            
            if not transcript:
                error_msg = f"No transcript available for {video_id}"
                logger.warning(error_msg)
                return ProcessingResult(
                    success=False,
                    error=error_msg
                )
            
            # Format transcript
            text_formatted = self.formatter.format_transcript(transcript)
            
            if not text_formatted or len(text_formatted) < 50:
                error_msg = f"Transcript too short: {len(text_formatted)} chars"
                logger.warning(error_msg)
                return ProcessingResult(
                    success=False,
                    error=error_msg
                )
            
            logger.success(f"✅ Extracted transcript: {len(text_formatted)} chars for {video_id}")
            logger.info(f"📄 Transcript preview: {text_formatted[:200]}...")
            
            return ProcessingResult(
                success=True,
                content=text_formatted,
                metadata={
                    'video_id': video_id,
                    'transcript_length': len(text_formatted),
                    'has_transcript': True
                }
            )
            
        except Exception as e:
            error_msg = f"Error extracting transcript: {type(e).__name__}: {str(e)}"
            logger.error(error_msg)
            return ProcessingResult(
                success=False,
                error=error_msg
            )
    
    async def _get_transcript(self, video_id: str) -> Optional[list]:
        """
        Fetch transcript using YouTubeTranscriptApi.
        Same implementation as YoutubeRagnarok.
        """
        try:
            # Fetch with multiple language support
            transcript = self.ytt_api.fetch(
                video_id,
                languages=[
                    'en', 'en-US', 'en-GB', 'en-AU', 'en-CA',
                    'fr', 'de', 'es', 'it', 'pt', 'ru',
                    'zh-CN', 'ja', 'ko'
                ]
            )
            return transcript
            
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            logger.debug(f"No transcript for {video_id}: {type(e).__name__}")
            return None
        except Exception as e:
            logger.debug(f"Error fetching transcript for {video_id}: {e}")
            return None
    
    def _extract_video_id_from_url(self, url: str) -> Optional[str]:
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


class BaseContentExtractor:
    """
    Base content extractor that delegates to YouTube extractor for YouTube sources.
    """
    
    def __init__(self, config):
        self.config = config
        self.youtube_extractor = None
        
        # Initialize YouTube extractor if needed
        if config.source_type.value == 'youtube':
            self.youtube_extractor = YouTubeContentExtractor(config)
    
    async def extract_content(self, article_meta: ArticleMetadata) -> ProcessingResult:
        """Extract content based on source type."""
        
        # Use YouTube extractor for YouTube sources
        if self.youtube_extractor:
            return await self.youtube_extractor.extract_content(article_meta)
        
        # For other sources, return success with empty content
        # (content was already extracted during discovery)
        return ProcessingResult(
            success=True,
            content="",
            metadata={}
        )
