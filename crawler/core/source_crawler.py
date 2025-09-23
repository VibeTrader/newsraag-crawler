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
# Import these for HTML crawling
from crawl4ai import AsyncWebCrawler, BrowserConfig


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
            # Special case for babypips
            if source_name == 'babypips':
                logger.info(f"Using specialized BabyPips crawler for {source_name}")
                try:
                    from crawl4ai import AsyncWebCrawler, BrowserConfig
                    from crawler.babypips import BabyPipsCrawler
                    
                    # Create browser config
                    browser_config = BrowserConfig(
                        headless=True,
                        extra_args=[
                            "--disable-gpu", 
                            "--disable-dev-shm-usage", 
                            "--no-sandbox",
                            "--disable-extensions",
                            "--memory-pressure-off",
                            "--max_old_space_size=512"
                        ]
                    )
                    
                    # Create babypips crawler
                    babypips_crawler = BabyPipsCrawler(source_url)
                    
                    # Get URLs using the specialized crawler
                    urls = await babypips_crawler.get_urls()
                    logger.info(f"Found {len(urls)} articles from BabyPips")
                    
                    # Create crawler instance for processing
                    async with AsyncWebCrawler(config=browser_config) as crawler_instance:
                        # Process each URL
                        for i, url_data in enumerate(urls):
                            url = url_data[0] if isinstance(url_data, tuple) and len(url_data) > 0 else "Unknown URL"
                            logger.info(f"Processing BabyPips article {i+1}/{len(urls)}: {url}")
                            
                            # Record start time
                            start_time = time.time()
                            
                            # Process using the specialized method
                            success = await babypips_crawler.process_url(url_data, crawler_instance)
                            
                            # Calculate time
                            extraction_time = time.time() - start_time
                            
                            # Record metrics
                            try:
                                title = url_data[1] if isinstance(url_data, tuple) and len(url_data) > 1 else "Unknown"
                                metrics.record_article_processed(source_name, url, success, None if success else f"Processing failed for {title}")
                            except Exception as metrics_error:
                                logger.warning(f"Error recording metrics: {metrics_error}")
                            
                            if success:
                                processed_count += 1
                                logger.info(f"✅ Successfully processed BabyPips article {i+1}")
                            else:
                                failure_count += 1
                                logger.error(f"❌ Failed to process BabyPips article {i+1}")
                                # Record error in metrics
                                try:
                                    metrics.record_error("article_processing_failed", source_name)
                                except Exception as record_error:
                                    logger.warning(f"Error recording error metric: {record_error}")
                except Exception as babypips_err:
                    logger.error(f"Error using specialized BabyPips crawler: {babypips_err}")
                    logger.info(f"Falling back to standard RSS crawler for {source_name}")
                    
                    # Fall back to standard RSS crawling
                    articles = await crawl_rss_feed(source_name, source_url)
                    
                    # Process articles with standard method
                    logger.info(f"Processing {len(articles)} articles from {source_name} (fallback method)")
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
                            # Record error in metrics
                            try:
                                metrics.record_error("article_processing_failed", source_name)
                            except Exception as record_error:
                                logger.warning(f"Error recording error metric: {record_error}")
            
            # Special case for fxstreet
            elif source_name == 'fxstreet':
                logger.info(f"Using specialized FXStreet crawler for {source_name}")
                try:
                    from crawl4ai import AsyncWebCrawler, BrowserConfig
                    from crawler.fxstreet import FXStreetCrawler
                    
                    # Create browser config
                    browser_config = BrowserConfig(
                        headless=True,
                        extra_args=[
                            "--disable-gpu", 
                            "--disable-dev-shm-usage", 
                            "--no-sandbox",
                            "--disable-extensions",
                            "--memory-pressure-off",
                            "--max_old_space_size=512"
                        ]
                    )
                    
                    # Create fxstreet crawler
                    fxstreet_crawler = FXStreetCrawler(source_url)
                    
                    # Get URLs using the specialized crawler
                    urls = await fxstreet_crawler.get_urls()
                    logger.info(f"Found {len(urls)} articles from FXStreet")
                    
                    # Create crawler instance for processing
                    async with AsyncWebCrawler(config=browser_config) as crawler_instance:
                        # Process each URL
                        for i, url_data in enumerate(urls):
                            url = url_data[0] if isinstance(url_data, tuple) and len(url_data) > 0 else "Unknown URL"
                            logger.info(f"Processing FXStreet article {i+1}/{len(urls)}: {url}")
                            
                            # Record start time
                            start_time = time.time()
                            
                            # Process using the specialized method
                            success = await fxstreet_crawler.process_url(url_data, crawler_instance)
                            
                            # Calculate time
                            extraction_time = time.time() - start_time
                            
                            # Record metrics
                            try:
                                title = url_data[1] if isinstance(url_data, tuple) and len(url_data) > 1 else "Unknown"
                                metrics.record_article_processed(source_name, url, success, None if success else f"Processing failed for {title}")
                            except Exception as metrics_error:
                                logger.warning(f"Error recording metrics: {metrics_error}")
                            
                            if success:
                                processed_count += 1
                                logger.info(f"✅ Successfully processed FXStreet article {i+1}")
                            else:
                                failure_count += 1
                                logger.error(f"❌ Failed to process FXStreet article {i+1}")
                                # Record error in metrics
                                try:
                                    metrics.record_error("article_processing_failed", source_name)
                                    
                                    # Send an alert for FXStreet failures
                                    logger.error(f"FXStreet processing failure details: URL={url}, Title={title}")
                                    
                                    try:
                                        from monitoring.alerts import get_alert_manager
                                        alert_manager = get_alert_manager()
                                        alert_manager.send_alert(
                                            "fxstreet_failure",
                                            f"FXStreet article processing failed: {title}",
                                            {
                                                "url": url,
                                                "cycle_id": metrics.current_cycle_id
                                            }
                                        )
                                    except Exception as alert_error:
                                        logger.warning(f"Failed to send FXStreet alert: {alert_error}")
                                except Exception as record_error:
                                    logger.warning(f"Error recording error metric: {record_error}")
                except Exception as fxstreet_err:
                    logger.error(f"Error using specialized FXStreet crawler: {fxstreet_err}")
                    logger.info(f"Falling back to standard RSS crawler for {source_name}")
                    
                    # Fall back to standard RSS crawling
                    articles = await crawl_rss_feed(source_name, source_url)
                    
                    # Process articles with standard method
                    logger.info(f"Processing {len(articles)} articles from {source_name} (fallback method)")
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
                            # Record error in metrics
                            try:
                                metrics.record_error("article_processing_failed", source_name)
                            except Exception as record_error:
                                logger.warning(f"Error recording error metric: {record_error}")
                                
            else:
                # Standard RSS crawling for other sources
                # Crawl RSS feed
                articles = await crawl_rss_feed(source_name, source_url)
                
                # Process each article
                logger.info(f"Processing {len(articles)} articles from {source_name}")
                for i, article in enumerate(articles):
                    logger.info(f"Processing article {i+1}/{len(articles)}: {article.get('title', 'Unknown')}")
                    
                    # Record start time for extraction performance track
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
                            # Add more detailed error info for babypips
                            if source_name == 'babypips':
                                logger.error(f"BabyPips processing failure details: URL={article.get('url', 'Unknown')}, Title={article.get('title', 'Unknown')}")
                                # Try to get more detailed diagnostic info
                                content_length = len(article.get('content', '')) if article.get('content') else 0
                                logger.error(f"BabyPips content diagnostic: Content length={content_length} chars")
                                
                                # Record a specific babypips error
                                metrics.record_error("babypips_article_processing_failed", "babypips", 
                                                    f"Failed to process BabyPips article: {article.get('title', 'Unknown')}, content length: {content_length}")
                                
                                # Optionally send an alert for continued babypips failures
                                try:
                                    from monitoring.alerts import get_alert_manager
                                    alert_manager = get_alert_manager()
                                    alert_manager.send_alert(
                                        "babypips_failure",
                                        f"BabyPips article processing failed: {article.get('title', 'Unknown')}",
                                        {
                                            "url": article.get('url', 'Unknown'),
                                            "content_length": content_length,
                                            "cycle_id": metrics.current_cycle_id
                                        }
                                    )
                                except Exception as alert_error:
                                    logger.warning(f"Failed to send BabyPips alert: {alert_error}")
                            else:
                                metrics.record_error("article_processing_failed", source_name)
                        except Exception as record_error:
                            logger.warning(f"Error recording error metric: {record_error}")
        elif source_type == 'html':
            logger.info(f"Processing HTML source: {source_name}")
            
            # For kabutan specifically
            if source_name == 'kabutan':
                try:
                    # Import necessary modules
                    from crawl4ai import AsyncWebCrawler, BrowserConfig
                    from crawler.kabutan import KabutanCrawler
                    
                    # Create browser config for HTML crawling
                    browser_config = BrowserConfig(
                        headless=True,
                        extra_args=[
                            "--disable-gpu", 
                            "--disable-dev-shm-usage", 
                            "--no-sandbox",
                            "--disable-extensions",
                            "--memory-pressure-off",
                            "--max_old_space_size=512"
                        ]
                    )
                    
                    # Create and use the crawler
                    async with AsyncWebCrawler(config=browser_config) as crawler_instance:
                        kabutan_crawler = KabutanCrawler()
                        
                        # Get URLs to process
                        articles = await kabutan_crawler.get_urls()
                        logger.info(f"Found {len(articles)} articles from {source_name}")
                        
                        # Process each article
                        for i, article_data in enumerate(articles):
                            url = article_data.get('url', 'Unknown URL')
                            logger.info(f"Processing article {i+1}/{len(articles)}: {url}")
                            
                            # Record start time for extraction performance tracking
                            start_time = time.time()
                            
                            # Process the article
                            success = await kabutan_crawler.process_url(article_data, crawler_instance)
                            
                            # Calculate extraction time
                            extraction_time = time.time() - start_time
                            
                            # Record metrics
                            try:
                                metrics.record_article_processed(source_name, url, success, None if success else f"Processing failed for {article_data.get('title', 'Unknown')}")
                            except Exception as metrics_error:
                                logger.warning(f"Error recording metrics: {metrics_error}")
                            
                            if success:
                                processed_count += 1
                                logger.info(f"✅ Successfully processed article {i+1}")
                            else:
                                failure_count += 1
                                logger.error(f"❌ Failed to process article {i+1}")
                                # Record error in metrics
                                try:
                                    metrics.record_error("article_processing_failed", source_name)
                                except Exception as record_error:
                                    logger.warning(f"Error recording error metric: {record_error}")
                        
                        # Close the crawler
                        await kabutan_crawler.close()
                        
                except Exception as e:
                    logger.error(f"Error processing HTML source {source_name}: {e}")
                    failure_count += 1
                    # Record error in metrics
                    try:
                        metrics.record_error("html_crawling_error", source_name, str(e))
                    except Exception as record_error:
                        logger.warning(f"Error recording error metric: {record_error}")
            else:
                logger.warning(f"HTML crawling not implemented for {source_name}")
                failure_count += 1
                # Record error in metrics
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
