"""
Test script for the cleanup functionality.
"""
import asyncio
import sys
import os
from loguru import logger

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the cleanup functions
from crawler.utils.cleanup import cleanup_old_data, clear_qdrant_collection

async def test_cleanup():
    """Test the cleanup functionality."""
    logger.info("Testing cleanup functionality...")
    
    # Test regular cleanup
    logger.info("Running cleanup_old_data (deleting data older than 24 hours)...")
    success = await cleanup_old_data(hours=24)
    
    if success:
        logger.info("✅ Cleanup successful")
    else:
        logger.error("❌ Cleanup failed")
    
    return success

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    
    # Run the test
    asyncio.run(test_cleanup())
