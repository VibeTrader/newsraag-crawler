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

## 🔗 Dependencies

- Qdrant (vector database)
- Redis (caching)
- Azure Blob Storage (archival)
- Feedparser (RSS parsing)


