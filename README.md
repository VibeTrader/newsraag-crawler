# NewsRagnarok Crawler

Advanced financial news crawler with AI-powered content cleaning, vector database indexing, and comprehensive monitoring system.

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

## 📁 Project Structure

```
/NewsRagnarok-Crawler
├── main.py                      # Main application entry point
├── requirements.txt             # Python dependencies
├── config/
│   └── sources.yaml            # News sources configuration
├── crawler/
│   ├── core/                   # Core crawling logic
│   ├── utils/                  # Crawler utilities and cleanup
│   └── redis_cache.py         # Redis caching (optional)
├── clients/                    # External service clients
│   ├── qdrant_client.py       # Vector database client
│   └── vector_client.py       # Vector operations wrapper
├── utils/                      # General utilities
│   ├── llm/                   # LLM content cleaning
│   ├── azure_utils.py         # Azure Blob Storage
│   └── cleanup.py             # Data cleanup utilities
├── monitoring/                 # Comprehensive monitoring system
│   ├── metrics.py             # Local metrics collection
│   ├── app_insights.py        # Azure Application Insights
│   ├── health_check.py        # Health monitoring
│   ├── alerts.py              # Slack alerting system
│   └── duplicate_detector.py  # Duplicate detection
├── models/                     # Data models and schemas
└── docs/                      # Documentation
```

## 🔧 Core Features

### **Intelligent Content Processing**
- ✅ RSS feed parsing and discovery
- ✅ AI-powered content cleaning using Azure OpenAI GPT-4
- ✅ Removes navigation, ads, and boilerplate while preserving financial data
- ✅ Semantic duplicate detection with title normalization
- ✅ Multi-source financial news aggregation

### **Data Storage & Indexing** 
- ✅ Vector database indexing with Qdrant (3072-dimension embeddings)
- ✅ Azure Blob Storage archival with structured JSON
- ✅ Automatic 24-hour data cleanup to maintain freshness
- ✅ In-memory caching with optional Redis enhancement

### **Monitoring & Alerting**
- ✅ **Azure Application Insights** integration for cloud telemetry
- ✅ **Local metrics collection** with JSON-based storage
- ✅ **Health check API endpoints** (`/health`, `/metrics`)
- ✅ **Slack alerting system** for failures and anomalies
- ✅ **Resource monitoring** (memory, CPU, dependencies)
- ✅ **LLM usage tracking** with token limits and cost management

### **Reliability & Performance**
- ✅ Graceful degradation when optional services unavailable
- ✅ Comprehensive error handling with detailed logging
- ✅ Memory management with garbage collection
- ✅ Concurrent processing with async/await
- ✅ Configurable retry mechanisms

## 📊 Supported Data Sources

| Source | Type | Content | Status |
|--------|------|---------|---------|
| **BabyPips** | RSS | Forex education & analysis | ✅ Active |
| **FXStreet** | RSS | Professional forex analysis | ✅ Active |
| **ForexLive** | RSS | Real-time forex news | ✅ Active |
| **Kabutan** | HTML | Japanese stock analysis | ✅ Active |

## 🏗️ Architecture Overview

### **Data Flow**
1. **Discovery**: RSS feeds parsed for new articles
2. **Extraction**: Crawl4AI extracts raw content from web pages
3. **Cleaning**: Azure OpenAI GPT-4 removes noise, preserves financial data
4. **Storage**: Clean content stored in Azure Blob Storage
5. **Indexing**: Vector embeddings created and stored in Qdrant
6. **Monitoring**: All operations tracked and monitored

### **Processing Pipeline**
```
RSS Feed → Web Scraping → AI Content Cleaning → Vector Embedding → Storage
    ↓           ↓              ↓                    ↓            ↓
Duplicate   Content      LLM Token         Semantic        Health
Detection   Extraction   Tracking          Search          Monitoring
```

## 📈 Monitoring System

### **Health Check API**
- **Endpoint**: `http://localhost:8001/health`
- **Response**: System status, uptime, memory usage, dependency health
- **Endpoint**: `http://localhost:8001/metrics` 
- **Response**: Detailed performance metrics, processing statistics

### **Azure Application Insights**
- Tracks crawler cycles, LLM usage, processing times
- Custom events for failures, cleanups, memory alerts
- Performance counters and dependency monitoring
- Automatic telemetry correlation

### **Slack Alerting**
- Real-time notifications for system failures
- Memory threshold alerts (>800MB)
- Processing failure rate monitoring
- Dependency outage notifications

### **Local Metrics Collection**
- JSON-based metrics stored in `/data/metrics/`
- Cycle performance tracking
- Error rate analysis
- Resource utilization history

## 🔧 Dependencies & Configuration

### **Required Services**
- **Qdrant Vector Database**: Semantic search and retrieval
- **Azure Blob Storage**: Document archival and backup
- **Azure OpenAI**: Content cleaning and embeddings

### **Optional Services**
- **Redis**: Enhanced caching (fallback: in-memory cache)
- **Azure Application Insights**: Cloud telemetry
- **Slack**: Failure notifications

### **Environment Configuration**
Key environment variables in `.env`:

```bash
# Vector Database
QDRANT_URL=https://your-qdrant-instance.com
QDRANT_API_KEY=your-api-key

# Azure Services
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-stocks
OPENAI_API_KEY=your-azure-openai-key
AZ_ACCOUNT_NAME=your-storage-account

# Monitoring (Optional)
APPINSIGHTS_INSTRUMENTATIONKEY=your-insights-key
ALERT_SLACK_WEBHOOK=your-slack-webhook
ALERT_SLACK_ENABLED=true

# Redis (Optional)
REDIS_HOST=your-redis-host
REDIS_PASSWORD=your-redis-password
```

## 💡 Key Benefits

### **Enterprise-Ready**
- Lightweight operation (~115MB memory usage)
- Cloud-native with Azure integration
- Comprehensive monitoring and alerting
- Graceful handling of service outages

### **AI-Powered Quality**
- Intelligent content extraction preserving financial data
- Semantic duplicate detection
- Token usage optimization for cost control
- Multilingual support (Japanese content translation)

### **Developer Friendly**
- Modular architecture for easy extension
- Comprehensive logging with structured data
- Health check APIs for integration monitoring
- Extensive documentation and examples

## 🔄 Operational Processes

### **Crawl Cycles**
- **Frequency**: Every hour (3600 seconds)
- **Process**: RSS discovery → Content extraction → AI cleaning → Storage
- **Monitoring**: Full telemetry and health tracking

### **Data Cleanup**
- **Frequency**: Every 24 hours
- **Process**: Identifies and removes documents older than 24 hours
- **Safety**: Backup and restore approach preserves recent data
- **Monitoring**: Deletion counts and performance tracking

### **Health Monitoring**
- **Continuous**: Memory, CPU, and dependency monitoring
- **Alerting**: Proactive notifications for failures
- **Recovery**: Automatic retry mechanisms and graceful degradation

## 🚀 Installation & Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd newsraag-crawler

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your service credentials

# Test monitoring setup (optional)
python tests/test_app_insights.py

# Run the crawler
python main.py
```

## 🔒 Security Features

- Environment-based credential management
- No hardcoded secrets or API keys
- Content sanitization before storage
- Path validation for file operations
- URL validation and sanitization
- Memory usage monitoring and limits

## 📊 Performance Metrics

- **Memory Usage**: ~115MB baseline, monitored continuously
- **Processing Speed**: ~1.4 seconds per article (including AI cleaning)
- **Token Efficiency**: ~2,100 tokens per article cleanup
- **Storage Efficiency**: 50% size reduction through intelligent cleaning
- **Uptime**: Continuous operation with automatic error recovery

## 🆘 Troubleshooting

### **Common Issues**
- **Redis warnings**: Expected when Redis not configured - system uses in-memory fallback
- **Memory alerts**: Normal for large batches - automatic garbage collection handles cleanup
- **Dependency failures**: System continues operation with graceful degradation

### **Log Locations**
- Application logs: Console output with structured logging
- Metrics: `/data/metrics/` JSON files
- Health status: Available via `/health` endpoint

## 📚 Documentation

- [Application Insights Setup Guide](docs/app_insights_setup.md)
- [Adding New Sources](docs/adding_sources.md) 
- [Monitoring Configuration](docs/monitoring_config.md)

---

Built for reliable, intelligent financial news processing with enterprise-grade monitoring and AI-powered content quality.
