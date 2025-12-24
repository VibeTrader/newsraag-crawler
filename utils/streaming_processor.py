"""
Streaming content processor for memory-efficient article processing.
Processes articles one at a time instead of loading all into memory.
"""
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from loguru import logger
import gc
from utils.memory_optimizer import get_memory_optimizer, ContentSizeOptimizer


class StreamingArticleProcessor:
    """
    Process articles in streaming fashion to minimize memory usage.
    """
    
    def __init__(self, memory_check_interval: int = 10):
        """
        Initialize streaming processor.
        
        Args:
            memory_check_interval: Check memory after every N articles
        """
        self.memory_check_interval = memory_check_interval
        self.memory_optimizer = get_memory_optimizer()
        self.processed_count = 0
        
    async def process_articles_stream(
        self, 
        articles_generator: AsyncGenerator[Dict[str, Any], None],
        processor_func: callable,
        max_concurrent: int = 1
    ) -> Dict[str, int]:
        """
        Process articles from an async generator with memory management.
        
        Args:
            articles_generator: Async generator yielding article data
            processor_func: Function to process each article
            max_concurrent: Maximum concurrent processing (keep low for memory)
            
        Returns:
            Processing statistics
        """
        stats = {
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'memory_optimizations': 0
        }
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_article(article_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            """Process a single article with memory optimization."""
            async with semaphore:
                try:
                    # Optimize article data size before processing
                    optimized_data = ContentSizeOptimizer.compress_article_data(article_data)
                    
                    # Process the article
                    result = await processor_func(optimized_data)
                    
                    # Increment processed count
                    self.processed_count += 1
                    
                    # Check memory periodically
                    if self.processed_count % self.memory_check_interval == 0:
                        should_optimize, level = self.memory_optimizer.should_optimize()
                        if should_optimize:
                            logger.info(f"Memory optimization during streaming: {level}")
                            self.memory_optimizer.optimize_memory(level)
                            stats['memory_optimizations'] += 1
                    
                    # Small delay to prevent overwhelming the system
                    await asyncio.sleep(0.01)
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"Error processing article {article_data.get('title', 'Unknown')}: {e}")
                    return None
        
        # Process articles from the stream
        async for article in articles_generator:
            try:
                result = await process_single_article(article)
                
                if result is not None:
                    stats['processed'] += 1
                else:
                    stats['failed'] += 1
                    
            except Exception as e:
                logger.error(f"Stream processing error: {e}")
                stats['failed'] += 1
        
        # Final memory optimization
        self.memory_optimizer.optimize_memory("soft")
        
        return stats


class MemoryEfficientBatchProcessor:
    """
    Process articles in small batches with aggressive memory management.
    """
    
    def __init__(self, batch_size: int = 5, memory_threshold_mb: int = 300):
        """
        Initialize batch processor.
        
        Args:
            batch_size: Number of articles to process in each batch
            memory_threshold_mb: Memory threshold for forced optimization
        """
        self.batch_size = batch_size
        self.memory_threshold = memory_threshold_mb * 1024 * 1024
        self.memory_optimizer = get_memory_optimizer()
        
    async def process_articles_batch(
        self,
        articles: List[Dict[str, Any]],
        processor_func: callable
    ) -> Dict[str, int]:
        """
        Process articles in memory-efficient batches.
        
        Args:
            articles: List of articles to process
            processor_func: Function to process each article
            
        Returns:
            Processing statistics
        """
        stats = {
            'processed': 0,
            'failed': 0,
            'skipped': 0,
            'batches_processed': 0,
            'memory_optimizations': 0
        }
        
        total_articles = len(articles)
        logger.info(f"Processing {total_articles} articles in batches of {self.batch_size}")
        
        # Process in batches
        for i in range(0, total_articles, self.batch_size):
            batch = articles[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (total_articles + self.batch_size - 1) // self.batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} articles)")
            
            # Process batch
            batch_results = await self._process_batch(batch, processor_func)
            
            # Update statistics
            stats['processed'] += batch_results['processed']
            stats['failed'] += batch_results['failed']
            stats['skipped'] += batch_results['skipped']
            stats['batches_processed'] += 1
            
            # Memory optimization after each batch
            should_optimize, level = self.memory_optimizer.should_optimize()
            if should_optimize or batch_num % 3 == 0:  # Every 3 batches or when needed
                logger.info(f"Memory optimization after batch {batch_num}")
                self.memory_optimizer.optimize_memory(level if should_optimize else "soft")
                stats['memory_optimizations'] += 1
            
            # Clear batch from memory
            del batch
            del batch_results
            
            # Small delay between batches
            await asyncio.sleep(0.1)
            
            # Force garbage collection every few batches
            if batch_num % 5 == 0:
                gc.collect()
        
        return stats
    
    async def _process_batch(
        self,
        batch: List[Dict[str, Any]],
        processor_func: callable
    ) -> Dict[str, int]:
        """Process a single batch of articles."""
        batch_stats = {'processed': 0, 'failed': 0, 'skipped': 0}
        
        # Process articles in the batch concurrently (but limited)
        semaphore = asyncio.Semaphore(2)  # Limit concurrent processing
        
        async def process_article(article_data: Dict[str, Any]):
            async with semaphore:
                try:
                    # Optimize article data size
                    optimized_data = ContentSizeOptimizer.compress_article_data(article_data)
                    
                    # Process article
                    result = await processor_func(optimized_data)
                    
                    if result:
                        batch_stats['processed'] += 1
                    else:
                        batch_stats['failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Batch processing error for {article_data.get('title', 'Unknown')}: {e}")
                    batch_stats['failed'] += 1
        
        # Process all articles in batch concurrently
        tasks = [process_article(article) for article in batch]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return batch_stats


# Memory-aware wrapper functions for existing code
def create_memory_efficient_processor(processing_mode: str = "streaming"):
    """
    Create memory-efficient processor based on mode.
    
    Args:
        processing_mode: "streaming" or "batch"
        
    Returns:
        Appropriate processor instance
    """
    if processing_mode == "streaming":
        return StreamingArticleProcessor()
    else:
        return MemoryEfficientBatchProcessor()


async def process_with_memory_management(
    articles: List[Dict[str, Any]],
    processor_func: callable,
    mode: str = "batch"
) -> Dict[str, int]:
    """
    Convenience function to process articles with memory management.
    
    Args:
        articles: List of articles to process
        processor_func: Function to process each article
        mode: "batch" or "streaming"
        
    Returns:
        Processing statistics
    """
    if mode == "streaming":
        # Convert list to async generator for streaming
        async def article_generator():
            for article in articles:
                yield article
        
        processor = StreamingArticleProcessor()
        return await processor.process_articles_stream(article_generator(), processor_func)
    
    else:  # batch mode
        processor = MemoryEfficientBatchProcessor()
        return await processor.process_articles_batch(articles, processor_func)
