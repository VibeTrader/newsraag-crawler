# NewsRagnarok Crawler

RSS feed crawler for news articles with vector database indexing.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

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
└── .env (environment variables)
```

## 🔧 Features

- ✅ RSS feed parsing
- ✅ Article content extraction
- ✅ Vector database indexing
- ✅ Azure Blob Storage archival
- ✅ Redis caching
- ✅ Configurable sources
- ✅ Comprehensive monitoring with Azure Application Insights

## 📊 Data Sources

- BabyPips (RSS)
- FXStreet (RSS)
- ForexLive (RSS)
- Kabutan (HTML)

## 💡 Benefits

- ✅ Lightweight (~300MB total)
- ✅ No browser dependencies
- ✅ Simple RSS parsing
- ✅ Easy to extend
- ✅ Comprehensive monitoring
- ✅ Duplicate detection

## 🔗 Dependencies

- Qdrant (vector database)
- Redis (caching)
- Azure Blob Storage (archival)
- Feedparser (RSS parsing)
- Azure Application Insights (monitoring)

## 📊 Monitoring

The crawler includes comprehensive monitoring capabilities:

- Local metrics collection in JSON files
- Azure Application Insights integration for cloud monitoring
- Health check API for status monitoring
- Duplicate detection to prevent redundant processing

See the [Application Insights Setup Guide](docs/app_insights_setup.md) for details on configuring and using the monitoring system.




