# NewsRaag Crawler - Refactored Architecture

## Overview
This repository contains a news crawler system designed to extract articles from financial news websites. The system has been refactored from a monolithic structure into a modular architecture for better maintainability.

### Code Reduction
- Original main.py: 1,353 lines
- Refactored main.py: 343 lines (75% reduction!)


## Key Components

### Core Modules
- `crawler/core/rss_crawler.py`: Crawls RSS feeds and extracts article data
- `crawler/core/article_processor.py`: Processes articles and stores in Azure and Qdrant
- `crawler/core/source_crawler.py`: Manages crawling of individual sources

### Content Extraction
- `crawler/extractors/article_extractor.py`: Extracts full article content using multiple strategies

### Health Monitoring
- `crawler/health/health_server.py`: HTTP server for health checks and monitoring

### Utilities
- `crawler/utils/cleanup.py`: Data cleanup operations
- `crawler/utils/config_loader.py`: Configuration loading utilities
- `crawler/utils/dependency_checker.py`: Dependency verification
- `crawler/utils/memory_monitor.py`: Memory usage monitoring

## Running the Crawler
```bash
# Normal execution
python main.py

# Clear Qdrant collection
python main.py --clear-collection

# Recreate Qdrant collection
python main.py --recreate-collection
```

## Configuration
- Sources are configured in `config/sources.yaml`
- Environment variables are configured in `.env`

## Monitoring
- Health endpoint: `http://localhost:8000/health`
- Metrics endpoint: `http://localhost:8000/metrics`

## Dependencies
- Azure Blob Storage for document storage
- Qdrant for vector search
- Azure OpenAI for embeddings
- Optional: Redis for caching
