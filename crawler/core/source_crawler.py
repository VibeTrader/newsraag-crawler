"""
Source crawler module for NewsRagnarok Crawler.
"""
import time
import asyncio
from typing import Dict, Any, Tuple
from loguru import logger

from crawler.core.rss_crawler import crawl_rss_feed
from crawler.core.article_processor import process_article
from monitoring.metrics import get_metrics

async def crawl_source(source_config: dict) -> tuple:
    """Crawl a single configured source."""
    source_name = source_config.get('name', 'unknown')
    source_type = source_config.get('type', 'unknown')
    source_url = source_config.get('url', '')
    
    logger.info(f"Starting crawl for source: {source_name} (type: {source_type})")
    
    processed_count = 0
    failure_count = 0
    
    # Get metrics instance
    metrics = get_metrics()
    
    try:
        if source_type == 'rss':
            # Crawl RSS feed
            articles = await crawl_rss_feed(source_name, source_url)
            
            # Process each article
            logger.info(f"Processing {len(articles)} articles from {source_name}")
            for i, article in enumerate(articles):
                logger.info(f"Processing article {i+1}/{len(articles)}: {article.get('title', 'Unknown')}")
                
                # Record start time for extraction performance tracking
                start_time = time.time()
                
                # Process the article
                success = await process_article(article)
                
                # Calculate extraction time
                extraction_time = time.time() - start_time
                
                # Record metrics
                try:
                    metrics.record_article_processed(source_name, article.get('url', ''), success, None if success else f"Processing failed for {article.get('title', 'Unknown')}")
                except Exception as metrics_error:
                    logger.warning(f"Error recording metrics: {metrics_error}")
                
                if success:
                    processed_count += 1
                    logger.info(f"✅ Successfully processed article {i+1}")
                else:
                    failure_count += 1
                    logger.error(f"❌ Failed to process article {i+1}")
                    # Record error in metrics with error handling
                    try:
                        metrics.record_error("article_processing_failed", source_name)
                    except Exception as record_error:
                        logger.warning(f"Error recording error metric: {record_error}")
                    
        elif source_type == 'html':
            logger.warning(f"HTML crawling not implemented for {source_name}")
            failure_count += 1
            # Record error in metrics with error handling
            try:
                metrics.record_error("html_crawling_not_implemented", source_name)
            except Exception as record_error:
                logger.warning(f"Error recording error metric: {record_error}")
        else:
            logger.warning(f"Unknown source type: {source_type}")
            failure_count += 1
            # Record error in metrics with error handling
            try:
                metrics.record_error("unknown_source_type", source_name)
            except Exception as record_error:
                logger.warning(f"Error recording error metric: {record_error}")
            
    except Exception as e:
        logger.error(f"Error crawling source {source_name}: {e}")
        failure_count += 1
        # Record error in metrics with error handling
        try:
            metrics.record_error("source_crawl_error", source_name, str(e))
        except Exception as record_error:
            logger.warning(f"Error recording error metric: {record_error}")
    
    logger.info(f"Finished crawling {source_name}: {processed_count} processed, {failure_count} failed")
    return source_name, processed_count, failure_count
