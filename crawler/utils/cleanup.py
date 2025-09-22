"""
Data cleanup utilities for NewsRagnarok Crawler.
"""
import asyncio
import os
import gc
import time
from datetime import datetime
from loguru import logger
from contextlib import nullcontext
from typing import Optional, Dict, Any

from clients.vector_client import VectorClient, create_vector_client
from monitoring.metrics import get_metrics
from monitoring.app_insights import get_app_insights
from monitoring.health_check import get_health_check

async def cleanup_old_data(hours: int = 24) -> bool:
    """
    Clean up data older than the specified hours.
    
    Args:
        hours: Age threshold in hours (default: 24 hours)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Starting cleanup of old data (older than {hours} hours)...")
        
        # Get metrics for monitoring
        metrics = get_metrics()
        deletion_id = metrics.start_deletion_process()
        
        # Get App Insights for cloud monitoring
        app_insights = get_app_insights()
        
        # Start App Insights operation
        with app_insights.start_operation("cleanup_old_data") if app_insights.enabled else nullcontext():
            start_time = time.time()
            
            # Initialize vector client
            vector_client = None
            try:
                vector_client = VectorClient()
                
                # Delete documents older than specified hours
                result = await vector_client.delete_documents_older_than(hours)
                duration = time.time() - start_time
                
                if result:
                    logger.info(f"Cleanup completed successfully in {duration:.2f}s: {result}")
                    
                    # Record deletion metrics
                    if 'deleted_count' in result:
                        deleted_count = result['deleted_count']
                        metrics.record_documents_deleted(deleted_count, "qdrant")
                        
                        # Track in App Insights
                        if app_insights.enabled:
                            app_insights.track_documents_deleted(deleted_count, "qdrant")
                            
                    metrics.end_deletion_process(success=True)
                    
                    # Track completion in App Insights
                    if app_insights.enabled:
                        duration = metrics.current_deletion.get("duration_seconds", 0) if hasattr(metrics, 'current_deletion') else 0
                        app_insights.track_deletion_duration(duration)
                        app_insights.track_event("cleanup_completed", {"deleted_count": str(deleted_count if 'deleted_count' in result else 0)})
                    
                    # Update health check
                    health_check = get_health_check()
                    health_check.update_dependency_status("qdrant", True)
                    
                    return True
                else:
                    logger.error("Cleanup failed - no result returned")
                    metrics.record_deletion_error("cleanup_failed", "Cleanup returned None", severity="error")
                    metrics.end_deletion_process(success=False)
                    
                    # Track failure in App Insights
                    if app_insights.enabled:
                        app_insights.track_event("cleanup_failed")
                    
                    return False
                    
            except Exception as e:
                logger.error(f"Error during vector client operations: {e}")
                metrics.record_deletion_error("cleanup_exception", str(e), severity="critical")
                metrics.end_deletion_process(success=False)
                
                # Track exception in App Insights
                if app_insights.enabled:
                    app_insights.track_exception(e, {"operation": "cleanup_old_data"})
                
                # Update health check
                health_check = get_health_check()
                health_check.update_dependency_status("qdrant", False, str(e))
                
                return False
            finally:
                # Close vector client if it was initialized
                if vector_client:
                    await vector_client.close()
                    
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return False

async def clear_qdrant_collection() -> bool:
    """
    Clear all documents from the Qdrant collection.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Clearing all documents from Qdrant collection...")
        
        # Initialize vector client
        vector_client = VectorClient()
        try:
            # Clear all documents
            result = await vector_client.clear_all_documents()
            
            if result:
                logger.info(f"Successfully cleared all documents: {result}")
                return True
            else:
                logger.error("Failed to clear documents - no result returned")
                return False
        finally:
            # Close vector client
            await vector_client.close()
            
    except Exception as e:
        logger.error(f"Error clearing Qdrant collection: {e}")
        return False

async def recreate_qdrant_collection() -> bool:
    """
    Delete and recreate the Qdrant collection.
    
    This is a more drastic approach than clear_qdrant_collection as it
    will reset the collection schema and configuration.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Recreating Qdrant collection...")
        
        # Here we need to use the QdrantClientWrapper directly to access the recreate method
        from clients.qdrant_client import QdrantClientWrapper
        
        # Initialize client
        client = QdrantClientWrapper()
        try:
            # Get collection info before recreation for comparison
            before_stats = await client.get_collection_stats()
            if before_stats:
                logger.info(f"Collection before recreation: {before_stats}")
            
            # Delete collection if it exists
            try:
                from qdrant_client import models
                collection_name = client.collection_name
                client.client.delete_collection(collection_name=collection_name)
                logger.info(f"Deleted collection: {collection_name}")
            except Exception as delete_err:
                logger.warning(f"Error deleting collection (may not exist): {delete_err}")
            
            # Recreate collection with same settings
            await client._ensure_collection_exists(force_recreate=True)
            
            # Get collection info after recreation
            after_stats = await client.get_collection_stats()
            if after_stats:
                logger.info(f"Collection after recreation: {after_stats}")
            
            logger.info("Successfully recreated Qdrant collection")
            return True
            
        finally:
            # Close client
            await client.close()
            
    except Exception as e:
        logger.error(f"Error recreating Qdrant collection: {e}")
        return False