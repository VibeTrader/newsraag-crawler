"""
Data cleanup utilities for NewsRagnarok Crawler.
"""
import asyncio
import os
import gc
from datetime import datetime
from loguru import logger
from contextlib import nullcontext

from clients.vector_client import VectorClient, create_vector_client
from monitoring.metrics import get_metrics
from monitoring.health_check import get_health_check

async def cleanup_old_data():
    """Clean up data older than 24 hours."""
    try:
        logger.info("Starting cleanup of old data...")
        
        # Get metrics for monitoring
        metrics = get_metrics()
        deletion_id = metrics.start_deletion_process()
        
        # Get App Insights for cloud monitoring
        from monitoring.app_insights import get_app_insights
        app_insights = get_app_insights()
        
        # Start App Insights operation
        with app_insights.start_operation("cleanup_old_data") if app_insights.enabled else nullcontext():
            vector_client = create_vector_client()
            
            # Delete documents older than 24 hours
            result = await vector_client.delete_documents_older_than(hours=24)
            if result:
                logger.info(f"Cleanup completed successfully: {result}")
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
                    app_insights.track_event("cleanup_completed", {"deleted_count": str(deleted_count)})
            else:
                logger.error("Cleanup failed")
                metrics.record_deletion_error("cleanup_failed", "Cleanup returned None", severity="error")
                metrics.end_deletion_process(success=False)
                
                # Track failure in App Insights
                if app_insights.enabled:
                    app_insights.track_event("cleanup_failed")
                
            await vector_client.close()
            
        # Update health check
        health_check = get_health_check()
        health_check.update_dependency_status("qdrant", True)
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        
        # Record deletion error
        metrics = get_metrics()
        if hasattr(metrics, 'current_deletion'):
            metrics.record_deletion_error("cleanup_exception", str(e), severity="critical")
            metrics.end_deletion_process(success=False)
        
        # Track exception in App Insights
        from monitoring.app_insights import get_app_insights
        app_insights = get_app_insights()
        if app_insights.enabled:
            app_insights.track_exception(e, {"operation": "cleanup_old_data"})
        
        # Update health check
        health_check = get_health_check()
        health_check.update_dependency_status("qdrant", False, str(e))

async def clear_qdrant_collection():
    """Clear all documents from the Qdrant collection."""
    logger.info("Starting Qdrant collection cleanup...")
    try:
        vector_client = VectorClient()
        try:
            logger.info("Attempting to clear all documents from Qdrant collection...")
            result = await vector_client.clear_all_documents()
            if result:
                logger.info(f"Qdrant collection cleanup successful: {result}")
                return True
            else:
                logger.error("Qdrant collection cleanup failed: received None result")
                return False
        finally:
            await vector_client.close()
    except Exception as e:
        logger.error(f"Error during Qdrant collection cleanup: {str(e)}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False

async def recreate_qdrant_collection():
    """Delete and recreate the Qdrant collection with proper configuration."""
    logger.info("Starting Qdrant collection recreation...")
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models
        
        url = os.getenv("QDRANT_URL")
        api_key = os.getenv("QDRANT_API_KEY")
        collection_name = os.getenv("QDRANT_COLLECTION_NAME", "news_articles")
        
        logger.info(f"Connecting to Qdrant at {url}")
        client = QdrantClient(url=url, api_key=api_key)
        
        # Delete collection if it exists
        try:
            logger.info(f"Attempting to delete collection {collection_name}...")
            client.delete_collection(collection_name=collection_name)
            logger.info(f"Collection {collection_name} deleted successfully")
        except Exception as e:
            logger.warning(f"Error deleting collection (may not exist): {str(e)}")
        
        # Recreate collection with proper configuration
        logger.info(f"Creating collection {collection_name}...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=3072,  # text-embedding-3-large embedding size
                distance=models.Distance.COSINE
            )
        )
        
        # Create payload indices
        logger.info("Creating payload indices...")
        client.create_payload_index(
            collection_name=collection_name,
            field_name="publishDatePst",
            field_schema=models.PayloadFieldSchema.DATETIME
        )
        
        client.create_payload_index(
            collection_name=collection_name,
            field_name="source",
            field_schema=models.PayloadFieldSchema.KEYWORD
        )
        
        logger.info(f"Collection {collection_name} recreated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during Qdrant collection recreation: {str(e)}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return False
