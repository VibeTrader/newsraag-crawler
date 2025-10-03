#!/usr/bin/env python3
"""
Industry-standard browser session pool for web scraping.
Implements singleton pattern with proper resource management.
"""
import asyncio
import time
from typing import Dict, Optional, List
from loguru import logger
from crawl4ai import AsyncWebCrawler, BrowserConfig
from contextlib import asynccontextmanager
from dataclasses import dataclass
import weakref
import atexit

@dataclass
class BrowserSession:
    """Represents a browser session with metadata."""
    crawler: AsyncWebCrawler
    created_at: float
    last_used: float
    usage_count: int
    max_usage: int = 50  # Recreate after 50 uses
    max_lifetime: float = 3600  # Recreate after 1 hour

    def is_expired(self) -> bool:
        """Check if session should be recreated."""
        current_time = time.time()
        return (
            self.usage_count >= self.max_usage or
            (current_time - self.created_at) >= self.max_lifetime
        )

class BrowserSessionPool:
    """
    Industry-standard browser session pool.
    Implements singleton pattern with proper resource management.
    """
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._sessions: Dict[str, BrowserSession] = {}
        self._session_lock = asyncio.Lock()
        self._initialized = True
        
        # Register cleanup on exit
        atexit.register(self._cleanup_sync)
        
        logger.info("Browser session pool initialized")
    
    async def get_session(self, source_name: str) -> AsyncWebCrawler:
        """
        Get or create a browser session for a source.
        Implements proper session reuse and cleanup.
        """
        async with self._session_lock:
            current_time = time.time()
            
            # Check if we have a valid session
            if source_name in self._sessions:
                session = self._sessions[source_name]
                
                if session.is_expired():
                    logger.info(f"Session expired for {source_name}, recreating...")
                    await self._cleanup_session(source_name)
                else:
                    # Reuse existing session
                    session.last_used = current_time
                    session.usage_count += 1
                    logger.debug(f"Reusing session for {source_name} (usage: {session.usage_count})")
                    return session.crawler
            
            # Create new session
            return await self._create_session(source_name)
    
    async def _create_session(self, source_name: str) -> AsyncWebCrawler:
        """Create a new browser session."""
        try:
            # Optimized browser configuration
            browser_config = BrowserConfig(
                browser_type="chromium",
                headless=True,
                viewport_width=1280,
                viewport_height=720,
                extra_args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--memory-pressure-off",
                    "--max-old-space-size=256",
                    "--aggressive-cache-discard",
                    # Critical for session reuse
                    "--disable-web-security",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection"
                ]
            )
            
            crawler = AsyncWebCrawler(config=browser_config, verbose=False)
            await crawler.astart()
            
            # Store session
            current_time = time.time()
            session = BrowserSession(
                crawler=crawler,
                created_at=current_time,
                last_used=current_time,
                usage_count=1
            )
            
            self._sessions[source_name] = session
            logger.info(f"Created new browser session for {source_name}")
            
            return crawler
            
        except Exception as e:
            logger.error(f"Failed to create browser session for {source_name}: {e}")
            raise
    
    async def _cleanup_session(self, source_name: str):
        """Cleanup a specific session."""
        if source_name in self._sessions:
            session = self._sessions[source_name]
            try:
                await session.crawler.aclose()
                logger.debug(f"Closed browser session for {source_name}")
            except Exception as e:
                logger.warning(f"Error closing session for {source_name}: {e}")
            finally:
                del self._sessions[source_name]
    
    async def cleanup_expired_sessions(self):
        """Cleanup expired sessions (call periodically)."""
        async with self._session_lock:
            expired_sources = [
                source for source, session in self._sessions.items()
                if session.is_expired()
            ]
            
            for source in expired_sources:
                await self._cleanup_session(source)
                logger.info(f"Cleaned up expired session for {source}")
    
    async def cleanup_all_sessions(self):
        """Cleanup all sessions."""
        async with self._session_lock:
            sources = list(self._sessions.keys())
            for source in sources:
                await self._cleanup_session(source)
            logger.info("All browser sessions cleaned up")
    
    def _cleanup_sync(self):
        """Synchronous cleanup for atexit."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule cleanup
                loop.create_task(self.cleanup_all_sessions())
            else:
                # Run cleanup
                loop.run_until_complete(self.cleanup_all_sessions())
        except:
            pass  # Ignore errors during shutdown
    
    def get_stats(self) -> Dict:
        """Get session pool statistics."""
        return {
            "total_sessions": len(self._sessions),
            "sessions": {
                source: {
                    "usage_count": session.usage_count,
                    "age_seconds": time.time() - session.created_at,
                    "last_used_ago": time.time() - session.last_used
                }
                for source, session in self._sessions.items()
            }
        }

# Global session pool instance
_browser_pool = None

def get_browser_pool() -> BrowserSessionPool:
    """Get the global browser session pool."""
    global _browser_pool
    if _browser_pool is None:
        _browser_pool = BrowserSessionPool()
    return _browser_pool

@asynccontextmanager
async def browser_session(source_name: str):
    """
    Context manager for browser sessions.
    Usage: async with browser_session("source_name") as crawler:
    """
    pool = get_browser_pool()
    crawler = await pool.get_session(source_name)
    try:
        yield crawler
    except Exception as e:
        logger.error(f"Error in browser session for {source_name}: {e}")
        # Session will be cleaned up on next expiry check
        raise
    # Note: We don't close the session here - it's reused

# Cleanup task for periodic maintenance
async def periodic_cleanup_task():
    """Background task to cleanup expired sessions."""
    pool = get_browser_pool()
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            await pool.cleanup_expired_sessions()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")

# Start cleanup task
_cleanup_task = None

def start_browser_pool():
    """Start the browser pool with periodic cleanup."""
    global _cleanup_task
    if _cleanup_task is None:
        _cleanup_task = asyncio.create_task(periodic_cleanup_task())
        logger.info("Browser session pool started with periodic cleanup")

def stop_browser_pool():
    """Stop the browser pool and cleanup all sessions."""
    global _cleanup_task
    if _cleanup_task:
        _cleanup_task.cancel()
        _cleanup_task = None
    
    pool = get_browser_pool()
    asyncio.create_task(pool.cleanup_all_sessions())
    logger.info("Browser session pool stopped")
