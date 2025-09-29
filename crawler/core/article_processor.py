"""
Article processing module for NewsRagnarok Crawler.
"""
import asyncio
from typing import Dict, Any, Optional
from loguru import logger
from datetime import datetime
import time

from clients.vector_client import VectorClient
from crawler.utils.azure_utils import check_azure_connection, upload_json_to_azure
from utils.time_utils import convert_to_pst
from utils.dir_utils import generate_id, get_timestamp
from models.output import OutputModel
from monitoring.metrics import get_metrics
from monitoring.health_check import get_health_check
from monitoring.duplicate_detector import get_duplicate_detector

async def process_article(article_data: Dict[str, Any]) -> bool:
    """Process a single article - store in Azure and index in Qdrant with enhanced retry mechanism."""
    # Retry configuration for cloud environments
    max_retries = 3
    retry_delay_base = 2  # seconds
    
    for attempt in range(max_retries):
        retry_delay = retry_delay_base ** attempt if attempt > 0 else 0
        if attempt > 0:
            logger.info(f"Retry attempt {attempt}/{max_retries} for article processing after {retry_delay}s delay")
            await asyncio.sleep(retry_delay)
            
        try:
            title = article_data['title']
            url = article_data['url']
            content = article_data['content']
            source = article_data['source']
            published = article_data['published']
            
            logger.info(f"🔄 Processing article: {title}")
            logger.info(f"   📄 Content length: {len(content)} characters")
            logger.info(f"   🔗 URL: {url}")
            logger.info(f"   📅 Published: {published}")
            
            # Check for duplicates with error handling
            try:
                duplicate_detector = get_duplicate_detector()
                is_duplicate, duplicate_type = duplicate_detector.is_duplicate(article_data)
                
                if is_duplicate:
                    logger.info(f"🔍 Detected duplicate article: {title} (type: {duplicate_type})")
                    # Record duplicate in metrics
                    try:
                        metrics = get_metrics()
                        metrics.record_duplicate_detected(source, url, duplicate_type)
                    except Exception as metrics_err:
                        logger.warning(f"Error recording duplicate metrics: {metrics_err}")
                    return False
            except Exception as dup_err:
                logger.warning(f"Error checking for duplicates: {dup_err}, continuing with processing")
            
            # Create article model
            article = OutputModel(
                title=title,
                publishDate=published,
                content=content,
                url=url
            )
            
            # Convert to PST with error handling
            publish_date_pst = None
            try:
                publish_date_pst = convert_to_pst(published)
                if publish_date_pst:
                    article.publishDatePst = publish_date_pst
            except Exception as date_err:
                logger.warning(f"Error converting date to PST: {date_err}, using original date")
            
            # Prepare for Azure storage
            article_dict = article.to_dict()
            article_dict.update({
                "_source": source,
                "_author": article_data.get('author', ''),
                "_category": article_data.get('category', ''),
                "_crawled_at": get_timestamp(),
                "_article_id": generate_id()
            })
            
            # Upload to Azure with retry logic
            azure_ok = False
            try:
                azure_ok = check_azure_connection()
            except Exception as azure_conn_err:
                logger.warning(f"Error checking Azure connection: {azure_conn_err}")
            
            if azure_ok:
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:200]
                for azure_attempt in range(2):  # Inner retry for Azure
                    try:
                        success, msg = upload_json_to_azure(
                            article_dict,
                            blob_name=f"{source}-{safe_title}.json",
                            publish_date_pst=article.publishDatePst
                        )
                        if not success:
                            logger.error(f"Azure upload failed (attempt {azure_attempt+1}): {msg}")
                            if azure_attempt < 1:  # If not the last attempt
                                await asyncio.sleep(1)  # Short delay before retry
                                continue
                            # Update health check for Azure
                            try:
                                health_check = get_health_check()
                                health_check.update_dependency_status("azure", False, msg)
                            except Exception as health_err:
                                logger.warning(f"Error updating health check: {health_err}")
                        else:
                            logger.info(f"Azure upload successful for {url}")
                            break  # Exit the retry loop on success
                    except Exception as azure_err:
                        logger.error(f"Azure upload exception (attempt {azure_attempt+1}): {azure_err}")
                        if azure_attempt < 1:  # If not the last attempt
                            await asyncio.sleep(1)  # Short delay before retry
            
            # Index in Qdrant with robust error handling
            vector_client = None
            try:
                # Create client for each attempt to ensure fresh connection
                vector_client = VectorClient()
                logger.info(f"🔍 Adding document to Qdrant: {title}")
                
                # Prepare metadata
                doc_metadata = {
                    "publishDatePst": article.publishDatePst.isoformat() if article.publishDatePst else None,
                    "source": source,
                    "author": article_data.get('author', ''),
                    "category": article_data.get('category', ''),
                    "article_id": article_dict.get("_article_id")
                }
                doc_metadata = {k: v for k, v in doc_metadata.items() if v is not None}
                logger.info(f"   📊 Metadata: {doc_metadata}")
                
                # Try to ensure collection exists before adding
                logger.info("Ensuring Qdrant collection exists before adding document")
                try:
                    if hasattr(vector_client.client, "_ensure_collection_exists"):
                        await vector_client.client._ensure_collection_exists()
                except Exception as ensure_err:
                    logger.warning(f"Error ensuring collection exists: {ensure_err}")
                
                # Add document with built-in retry from the enhanced VectorClient
                add_result = await vector_client.add_document(content, metadata=doc_metadata)
                logger.info(f"   📤 Qdrant add_document result: {add_result}")
                
                if add_result:
                    logger.info(f"✅ Successfully indexed: {title}")
                    
                    # Record successful processing in metrics
                    try:
                        metrics = get_metrics()
                        metrics.record_article_processed(source, url, True)
                    except Exception as metrics_err:
                        logger.warning(f"Error recording success metrics: {metrics_err}")
                    
                    # Success - return true
                    return True
                else:
                    logger.error(f"❌ Failed to index: {title}, result was None")
                    
                    # Record failure in metrics and alert for Qdrant error
                    try:
                        metrics = get_metrics()
                        metrics.record_article_processed(source, url, False, "Qdrant indexing failed")
                        
                        # Send specific Qdrant alert
                        metrics.record_qdrant_error(
                            "Qdrant failed to index document - possible timeout parameter issue", 
                            title, 
                            "error"
                        )
                    except Exception as metrics_err:
                        logger.warning(f"Error recording failure metrics: {metrics_err}")
                    except Exception as metrics_err:
                        logger.warning(f"Error recording failure metrics: {metrics_err}")
                    
                    # If this is not the last attempt, continue to retry
                    if attempt < max_retries - 1:
                        continue
                    
                    return False
                    
            except Exception as e:
                logger.error(f"Error indexing article {title} (attempt {attempt+1}): {e}")
                
                # Record failure in metrics with specific Qdrant alert
                try:
                    metrics = get_metrics()
                    metrics.record_article_processed(source, url, False, str(e))
                    
                    # Send specific Qdrant error alert
                    metrics.record_qdrant_error(
                        f"Error indexing article in Qdrant: {str(e)}", 
                        title, 
                        "error"
                    )
                except Exception as metrics_err:
                    logger.warning(f"Error recording error metrics: {metrics_err}")
                
                # If this is not the last attempt, continue to retry
                if attempt < max_retries - 1:
                    continue
                
                return False
            finally:
                if vector_client:
                    try:
                        await vector_client.close()
                    except Exception as close_err:
                        logger.warning(f"Error closing vector client: {close_err}")
                    
        except Exception as e:
            logger.error(f"Error processing article (attempt {attempt+1}): {e}")
            
            # Record error in metrics if we have enough info
            if 'source' in article_data and 'url' in article_data:
                try:
                    metrics = get_metrics()
                    metrics.record_article_processed(
                        article_data['source'], 
                        article_data['url'], 
                        False, 
                        str(e)
                    )
                except Exception as metrics_err:
                    logger.warning(f"Error recording error metrics: {metrics_err}")
            
            # If this is not the last attempt, continue to retry
            if attempt < max_retries - 1:
                continue
            
            return False
    
    # If we've exhausted all retries
    logger.error(f"All retry attempts failed for processing article: {article_data.get('title', 'Unknown')}")
    return False
