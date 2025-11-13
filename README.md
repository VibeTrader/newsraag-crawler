# NewsRaag Crawler

**AI-Powered Financial News Aggregation & Vector Indexing System**

A production-ready financial news crawler that automatically collects articles from multiple sources, cleans them using AI, and stores them in a vector database for semantic search.

---

## What Does This Do?

NewsRaag Crawler automates financial news collection and processing:

1. **Crawls** financial news from RSS feeds and websites
2. **Cleans** content using Azure OpenAI GPT-4 (removes ads, navigation, keeps important info)
3. **Creates** semantic embeddings (3072-dimension vectors)
4. **Stores** in Qdrant vector database for semantic search
5. **Archives** full articles in Azure Blob Storage
6. **Monitors** system health and performance

### Current Sources
- **BabyPips** - Forex education and analysis
- **FXStreet** - Professional forex market analysis
- **MarketWatch** - Market news and financial updates
- **Kabutan** - Japanese stock market analysis (with translation)

---

## Quick Start

```bash
# Setup
git clone <repo-url>
cd newsraag-crawler
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium --with-deps

# Configure
cp .env.example .env
# Edit .env with your credentials (Azure OpenAI, Qdrant, Azure Storage)

# Run
python main.py
```

---

## Architecture

### Processing Flow

```
News Sources (RSS/HTML)
         ↓
    Discovery & Validation
         ↓
    Content Extraction
    ├── Crawl4AI (JavaScript rendering)
    ├── BeautifulSoup (HTML parsing)
    └── RSS fallback
         ↓
    AI Content Cleaning (GPT-4)
    ├── Remove ads & navigation
    ├── Keep financial data
    └── Structure content
         ↓
    Vector Embedding (3072-dim)
         ↓
    Storage
    ├── Qdrant (vector search)
    └── Azure Blob (archive)
```

### Design Pattern
- **Factory Pattern**: Creates appropriate handlers for each source type
- **Template Method**: Standardized processing with fallback strategies
- **Graceful Degradation**: Continues working if optional services fail

---

## Project Structure

```
newsraag-crawler/
├── main.py                      # Entry point
├── config/
│   └── sources.yaml            # News source definitions
├── crawler/
│   ├── factories/              # Source creation logic
│   ├── templates/              # Processing templates (RSS, HTML)
│   ├── extractors/             # Content extraction
│   └── utils/                  # Helper functions
├── monitoring/
│   ├── health_check.py         # Health API
│   ├── metrics.py              # Performance tracking
│   └── alerts.py               # Slack notifications
├── clients/
│   ├── qdrant_client.py        # Vector database
│   └── vector_client.py        # Embeddings
├── utils/
│   └── llm/cleaner.py          # AI content cleaning
└── tests/                      # Test suite
```

---

## Configuration

### Required Environment Variables

```bash
# Azure OpenAI (REQUIRED)
OPENAI_BASE_URL=https://your-endpoint.openai.azure.com/
OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOYMENT=gpt-4-1106-preview
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
EMBEDDING_DIMENSION=3072

# Qdrant Vector Database (REQUIRED)
QDRANT_URL=https://your-cluster.qdrant.tech
QDRANT_API_KEY=your_api_key

# Azure Storage (REQUIRED)
AZ_ACCOUNT_NAME=your_storage_account
AZ_ACCOUNT_KEY=your_storage_key

# LLM Configuration (REQUIRED)
LLM_CLEANING_ENABLED=true
LLM_TOKEN_LIMIT_PER_REQUEST=4000
LLM_DAILY_TOKEN_LIMIT=1000000

# Monitoring (OPTIONAL)
APPINSIGHTS_INSTRUMENTATIONKEY=your_key
ALERT_SLACK_WEBHOOK=your_webhook
ALERT_SLACK_ENABLED=true
```

### Adding New Sources

Edit `config/sources.yaml`:

```yaml
sources:
  - name: your_source
    type: rss  # or html_scraping
    url: https://example.com/feed.xml
    rate_limit: 2           # Seconds between requests
    max_articles: 50        # Max articles per run
    timeout: 90             # Request timeout
    content_type: forex     # forex, stocks, news, economics
    
    # For HTML scraping:
    selectors:
      title: ".article-title"
      content: ".article-body"
      link: "a.article-link"
```

---

## Running the Crawler

### Basic Commands

```bash
# Standard run
python main.py

# Test sources before running
python main.py --test-sources

# Clear vector database
python main.py --clear-collection

# Recreate database schema
python main.py --recreate-collection
```

### Health Monitoring

```bash
# Check health
curl http://localhost:8001/health

# View metrics
curl http://localhost:8001/metrics

# Production
curl https://newscrawler.azurewebsites.net/health
```

---

## Testing

```bash
# Run all tests
python run_tests.py all

# Unit tests only
pytest tests/unit/ -v

# With coverage
pytest --cov=crawler --cov=monitoring --cov-report=html

# Specific test
pytest tests/unit/test_source_routing.py -v
```

---

## Deployment

### Local Development
```bash
# Activate environment
source venv/bin/activate

# Run crawler
python main.py
```

### Production (Azure App Service)
- **URL**: https://newscrawler.azurewebsites.net
- **Deployment**: Automatic via GitHub Actions on push to `main`
- **Health Check**: https://newscrawler.azurewebsites.net/health

### CI/CD Pipeline
Push to `main` branch triggers:
1. Run tests
2. Build application
3. Deploy to Azure
4. Health check validation

Manual deployment: GitHub Actions → Run workflow

---

## Performance

### Metrics
- **Processing Speed**: ~1.4 seconds per article
- **Memory Usage**: 115MB baseline, 800MB cleanup threshold
- **Token Usage**: ~2,100 tokens per article
- **Throughput**: 50-200 articles per hour
- **Success Rate**: 85-90% typical

### Resource Usage
- **Daily Processing**: 1,200-4,800 articles
- **Daily Token Usage**: ~2.5M tokens
- **Storage Growth**: 500MB-2GB per month

---

## Troubleshooting

### Sources Not Discovering Articles

**Check:**
```bash
python diagnose_rss_feeds.py
python main.py --test-sources
```

**Fix:** Verify RSS URLs, increase `rate_limit`, check network connectivity

### Memory Warnings

**Check:**
```bash
grep "Memory usage" crawler.log
```

**Fix:** Normal behavior - automatic cleanup at 800MB. Reduce `max_articles` if needed.

### Qdrant Connection Errors

**Check:**
```bash
python -c "from clients.qdrant_client import get_qdrant_client; print('OK' if get_qdrant_client() else 'Failed')"
```

**Fix:** Verify `QDRANT_URL` and `QDRANT_API_KEY` in `.env`

### Token Limit Exceeded

**Check:**
```bash
curl http://localhost:8001/metrics | grep token
```

**Fix:** Increase `LLM_DAILY_TOKEN_LIMIT` or reduce `max_articles` per source

### Browser Errors

**Fix:**
```bash
playwright install chromium --with-deps
```

---

## Key Files

### Configuration
- `.env` - Environment variables (create from `.env.example`)
- `config/sources.yaml` - News sources
- `.deployment` - Azure deployment settings

### Core Code
- `main.py` - Entry point
- `crawler/factories/source_factory.py` - Source creation
- `utils/llm/cleaner.py` - AI content cleaning
- `clients/qdrant_client.py` - Vector database
- `monitoring/health_check.py` - Health monitoring

### Data
- `data/seen_articles.json` - Duplicate detection cache
- `data/metrics/` - Performance metrics
- `data/heartbeat/` - Health status

---

## Tech Stack

### Core
- Python 3.8+ (3.12 recommended)
- Azure OpenAI (GPT-4 + text-embedding-3-large)
- Qdrant Vector Database
- Azure Blob Storage

### Web Scraping
- Crawl4AI 0.6.3 (primary)
- BeautifulSoup4 (fallback)
- Playwright (browser automation)
- feedparser (RSS parsing)

### Monitoring
- FastAPI (health API)
- Azure Application Insights
- Loguru (logging)
- psutil (resource monitoring)

### Testing
- pytest
- pytest-asyncio
- pytest-cov

---

## Important Notes

### Token Usage
- Average: ~2,100 tokens per article
- Daily limit: 1M tokens (configurable)
- Monitor usage via `/metrics` endpoint

### Memory Management
- Automatic cleanup at 800MB
- Normal operation: 200-400MB
- Peak usage: Up to 800MB before cleanup

### Rate Limiting
- Respects per-source rate limits (1-5 seconds)
- Configurable in `sources.yaml`

### Duplicate Detection
- Title normalization
- Local cache (`seen_articles.json`)
- Vector similarity search

---

## Development

### Setup
```bash
git clone <repo>
cd newsraag-crawler
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium --with-deps
cp .env.example .env
# Edit .env with credentials
```

### Code Style
- Follow PEP 8
- Use type hints
- Document public methods
- Test new features

### Testing Before Push
```bash
python run_tests.py all
python main.py --test-sources
```

---

## Support

### Logs
- Console: Structured JSON logging
- Health: `/data/heartbeat/crawler_heartbeat.txt`
- Metrics: `/data/metrics/*.json`
- Azure: App Service → Log Stream

### Health Endpoints
- Local: `http://localhost:8001/health`
- Production: `https://newscrawler.azurewebsites.net/health`

### Diagnostics
```bash
python diagnose_rss_feeds.py      # Check RSS feeds
python test_health_check.py       # Test health system
```

---

**Production Status:** Active and deployed at https://newscrawler.azurewebsites.net

**Python Version:** 3.8+ (3.12 in production)

**Last Updated:** 2024
