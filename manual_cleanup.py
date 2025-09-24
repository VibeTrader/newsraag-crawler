"""
Manual cleanup script for NewsRagnarok Crawler.

This script manually runs the cleanup process to delete old data from Qdrant.
By default, it deletes data older than 24 hours.
"""
import asyncio
import sys
import os
from loguru import logger
from datetime import datetime, timedelta
import pytz

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the cleanup function
from crawler.utils.cleanup import cleanup_old_data
from clients.vector_client import VectorClient

async def run_manual_cleanup(hours=24):  # Default: 24 hours (1 day)
    """
    Run a manual cleanup to delete data older than the specified number of hours.
    
    Args:
        hours: Number of hours. Default is 168 (7 days)
    """
    try:
        # Calculate the cutoff date for context
        cutoff_time = datetime.now(pytz.timezone('US/Pacific')) - timedelta(hours=hours)
        logger.info(f"Starting manual cleanup of data older than {hours} hours (before {cutoff_time})")
        
        # First, get statistics before cleanup
        vector_client = VectorClient()
        try:
            before_stats = await vector_client.get_collection_stats()
            if before_stats:
                before_count = before_stats.get('points_count', 0)
                logger.info(f"Before cleanup: {before_count} documents in the collection")
            
            # Run the cleanup
            result = await cleanup_old_data(hours=hours)
            
            # Get statistics after cleanup
            after_stats = await vector_client.get_collection_stats()
            if after_stats:
                after_count = after_stats.get('points_count', 0)
                logger.info(f"After cleanup: {after_count} documents in the collection")
                
                # Calculate difference
                if before_count > 0 and after_count >= 0:
                    deleted = before_count - after_count
                    logger.info(f"Deleted {deleted} documents ({(deleted/before_count)*100:.2f}% of total)")
            
            # Report result
            if result:
                logger.info(f"✅ Manual cleanup completed successfully")
            else:
                logger.error(f"❌ Manual cleanup failed")
                
            return result
        finally:
            # Close the vector client
            await vector_client.close()
            
    except Exception as e:
        logger.error(f"Error during manual cleanup: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """Execute manual cleanup with customizable parameters."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manual data cleanup for NewsRagnarok Crawler")
    parser.add_argument("--hours", type=int, default=24, help="Delete data older than this many hours (default: 24 hours)")
    parser.add_argument("--days", type=int, help="Delete data older than this many days (overrides --hours)")
    args = parser.parse_args()
    
    # Calculate hours
    hours = args.hours
    if args.days is not None:
        hours = args.days * 24
        logger.info(f"Using {args.days} days = {hours} hours as threshold")
    
    # Run the cleanup
    await run_manual_cleanup(hours)

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    # Run the cleanup
    asyncio.run(main())
