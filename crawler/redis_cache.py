import redis
import os
from dotenv import load_dotenv
from loguru import logger

class RedisUrlCache:
    """Redis-based cache to track processed URLs for different sources."""

    def __init__(self, source_name: str):
        """Initialize the Redis URL cache for a specific source.

        Args:
            source_name: The name of the source (e.g., 'babypips', 'fxstreet')
                         This is used as part of the Redis key.
        """
        load_dotenv()
        self.source_name = source_name
        self.redis_key = f"processed_urls:{self.source_name}"
        try:
            # Build Redis connection parameters
            redis_params = {
                'host': os.getenv("REDIS_HOST"),
                'port': int(os.getenv("REDIS_PORT", 6380)),
                'password': os.getenv("REDIS_PASSWORD"),
                'db': int(os.getenv("REDIS_DB", 0)),
                'ssl': os.getenv("REDIS_USE_SSL", "false").lower() == "true",
                'decode_responses': True
            }
            
            # Only add username if it's not empty and not just whitespace
            redis_username = os.getenv("REDIS_USERNAME")
            if redis_username and redis_username.strip() and redis_username.strip() != "#":
                redis_params['username'] = redis_username.strip()
            
            self.redis_client = redis.Redis(**redis_params)
            self.redis_client.ping() # Test connection
            logger.info(f"Successfully connected to Redis for source '{self.source_name}'")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Consider how to handle this - maybe raise the exception or fallback?
            # For now, we'll log and the methods will fail gracefully if client is None
            self.redis_client = None
        except Exception as e:
            logger.error(f"An unexpected error occurred during Redis initialization: {e}")
            self.redis_client = None


    def is_processed(self, url: str) -> bool:
        """Check if a URL has already been processed using Redis SISMEMBER.

        Args:
            url: The URL string to check.

        Returns:
            True if the URL is in the Redis set for this source, False otherwise.
        """
        if not self.redis_client:
            logger.warning("Redis client not available. Cannot check processed status.")
            return False # Or raise an error, depending on desired behavior
        try:
            return self.redis_client.sismember(self.redis_key, url)
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error during is_processed: {e}")
            return False # Treat connection errors as unprocessed?
        except Exception as e:
            logger.error(f"Error checking processed status in Redis for {url}: {e}")
            return False

    def mark_processed(self, url: str) -> None:
        """Mark a URL as processed by adding it to the Redis set using SADD.

        Args:
            url: The URL string to add.
        """
        if not self.redis_client:
            logger.warning("Redis client not available. Cannot mark URL as processed.")
            return
        try:
            self.redis_client.sadd(self.redis_key, url)
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error during mark_processed: {e}")
        except Exception as e:
            logger.error(f"Error marking URL as processed in Redis for {url}: {e}")

    def reset(self) -> None:
        """Reset the URL cache for this source by deleting the Redis key."""
        if not self.redis_client:
            logger.warning("Redis client not available. Cannot reset cache.")
            return
        try:
            self.redis_client.delete(self.redis_key)
            logger.info(f"Reset Redis URL cache for source '{self.source_name}' (Key: {self.redis_key})")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error during reset: {e}")
        except Exception as e:
            logger.error(f"Error resetting Redis cache for source '{self.source_name}': {e}") 