# NewsRagnarok Crawler

RSS feed crawler for news articles with vector database indexing and comprehensive monitoring.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your credentials

# Run crawler
python main.py
```

## 📁 Structure

```
/NewsRagnarok-Crawler
├── main.py (crawler entry point)
├── requirements.txt (crawler dependencies)
├── config/ (sources.yaml)
├── crawler/ (crawler modules)
├── crawlers/ (additional crawlers)
├── clients/ (Qdrant, Redis clients)
├── utils/ (utilities)
├── models/ (data models)
├── monitoring/ (monitoring modules)
├── docs/ (documentation)
└── .env (environment variables)
```

## 🔧 Features

- ✅ RSS feed parsing and article extraction
- ✅ Vector database indexing (Qdrant)
- ✅ Azure Blob Storage archival
- ✅ Redis caching for performance
- ✅ Configurable data sources
- ✅ Comprehensive monitoring with Azure Application Insights
- ✅ Duplicate detection to prevent redundant processing
- ✅ Secure credential management
- ✅ Health check API endpoints

## 📊 Data Sources

- BabyPips (RSS)
- FXStreet (RSS)
- ForexLive (RSS)
- Kabutan (HTML)

## 💡 Benefits

- ✅ Lightweight (~300MB memory usage)
- ✅ No browser dependencies for core functionality
- ✅ Simple RSS-based discovery
- ✅ Easy to extend with new sources
- ✅ Comprehensive monitoring and alerting
- ✅ Duplicate detection for efficiency
- ✅ Secure by design

## 🔗 Dependencies

- **Vector Storage**: Qdrant for semantic search
- **Content Caching**: Redis for performance optimization
- **Archival Storage**: Azure Blob Storage
- **RSS Processing**: Feedparser
- **Monitoring**: Azure Application Insights
- **Content Extraction**: BeautifulSoup, crawl4ai (optional)

## 📊 Monitoring

The crawler includes comprehensive monitoring capabilities:

- **Local Metrics**: JSON file-based metrics collection
- **Cloud Monitoring**: Azure Application Insights integration
- **Health API**: RESTful health check endpoints
- **Duplicate Detection**: Prevents redundant processing
- **Resource Monitoring**: Memory and CPU tracking
- **Dependency Checks**: Monitoring of external services

For monitoring setup, see the [Application Insights Setup Guide](docs/app_insights_setup.md).

## 🔒 Security Features

- Environment-based credential management
- No hardcoded secrets
- Path validation for file operations
- URL validation and sanitization
- Comprehensive error handling
- Content sanitization before storage
- Memory usage monitoring and management

## 🔄 Process Management

The crawler runs two key processes:

1. **5-Minute Crawl Cycles**: Regular crawling of RSS feeds for new content
2. **Daily Cleanup Process**: Removal of old data to maintain storage efficiency

Both processes are monitored with detailed metrics and health checks.

## 📝 Configuration

Configuration is managed through:

- `.env` file for credentials and API keys
- `config/sources.yaml` for data source configuration

## 🔧 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/newsraag-crawler.git
cd newsraag-crawler

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your credentials

# Test Application Insights setup (optional)
python tests/test_app_insights.py

# Run the crawler
python main.py
```

## 📈 Health Check API

The crawler exposes two API endpoints:

- `/health` - Basic health status and dependency information
- `/metrics` - Detailed metrics about crawler performance

Access these endpoints at `http://localhost:8000/` when the crawler is running.


