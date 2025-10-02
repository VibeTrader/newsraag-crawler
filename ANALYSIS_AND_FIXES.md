# NewsRaag Crawler Analysis & Fixes

## 🔍 Analysis Summary

### Current State
✅ **Working Sources**: BabyPips (30/30), FXStreet (30/30)
❌ **Failing Sources**: ForexLive, PoundSterlingLive, Kabutan, Bloomberg

### Architecture Strengths
- Clean factory pattern implementation
- Comprehensive monitoring system
- Vector database integration (Qdrant)
- AI-powered content cleaning with GPT-4
- Azure cloud integration

## 🐛 Critical Issues Identified

### 1. Source Type Processing Bug
**Problem**: Main.py forces ALL sources through RSS processing
```python
# main.py line ~393 - INCORRECT
result = await process_rss_source(rss_config)  # Applied to ALL sources!
```

**Impact**: HTML scraping sources (Kabutan) fail with XML parsing errors

### 2. RSS Feed Quality Issues
- **ForexLive**: Malformed XML (`mismatched tag`)
- **PoundSterlingLive**: Malformed XML (`mismatched tag`)
- **Bloomberg**: 403 Forbidden (paywall protection)

### 3. Missing HTML Extractor Implementation
The `UniversalTemplate` exists but HTML article discovery is incomplete.

## 🔧 Immediate Fixes Required

### Fix 1: Correct Source Type Routing
The main.py needs to properly route sources based on their type:

```python
# CURRENT (BROKEN)
if source.config.source_type == SourceType.RSS:
    # ... RSS processing
    result = await process_rss_source(rss_config)  # Called for ALL!

elif source.config.source_type == SourceType.HTML_SCRAPING:
    # ... HTML processing  
    result = await source.process_articles()  # Never reached!

# FIXED VERSION NEEDED
if source.config.source_type == SourceType.RSS:
    result = await process_rss_source(rss_config)
elif source.config.source_type == SourceType.HTML_SCRAPING:
    result = await process_html_source(source)
else:
    result = await source.process_articles()
```

### Fix 2: Implement Missing HTML Article Discovery

Create proper HTML scraping article discovery:

```python
# crawler/extractors/html_article_discovery.py
class HTMLArticleDiscovery(BaseArticleDiscovery):
    async def discover_articles(self) -> AsyncGenerator[ArticleMetadata, None]:
        # Use Crawl4AI/Playwright to get page content
        # Extract article links using selectors
        # Convert to ArticleMetadata objects
```

### Fix 3: RSS Feed Robustness

For malformed RSS feeds, implement fallback strategies:

```python
# Enhanced RSS parsing with fallbacks
async def _parse_rss_feed(self):
    try:
        # Primary: feedparser
        feed = feedparser.parse(self.config.rss_url)
        if feed.bozo and feed.bozo_exception:
            # Fallback: BeautifulSoup XML parsing
            return await self._parse_with_beautifulsoup()
    except:
        # Final fallback: Treat as HTML page
        return await self._parse_as_html_page()
```

### Fix 4: Bloomberg Alternative

Replace Bloomberg with working alternatives:
- **MarketWatch RSS**: `https://feeds.marketwatch.com/marketwatch/realtimeheadlines/`
- **Reuters RSS**: `https://feeds.reuters.com/reuters/businessNews`
- **Yahoo Finance RSS**: `https://feeds.finance.yahoo.com/rss/2.0/headline`

## 🚀 Implementation Priority

### Phase 1: Critical Fixes (Immediate)
1. **Fix main.py source routing** - This will immediately fix Kabutan
2. **Implement HTML article discovery** - Complete the HTML scraping pipeline  
3. **Add RSS fallback parsing** - Fix ForexLive and PoundSterlingLive

### Phase 2: Enhancements (Next)
1. Replace Bloomberg with working alternatives
2. Add more robust error handling
3. Implement retry mechanisms for failed sources

### Phase 3: Optimization (Later)
1. Add caching layer for article discovery
2. Implement smart duplicate detection at discovery level
3. Add source health scoring and auto-disable

## 📋 Files That Need Updates

### 1. main.py (Critical)
- Fix source type routing logic
- Remove hardcoded RSS processing for all sources

### 2. crawler/extractors/article_discovery.py
- Implement HTML article discovery extractor
- Add registry mapping for html_scraping type

### 3. crawler/templates/rss_template.py
- Add fallback parsing methods
- Improve error handling for malformed XML

### 4. config/sources.yaml
- Replace Bloomberg with working alternative
- Verify selectors for HTML sources

## 🧪 Testing Strategy

### 1. Unit Tests
```bash
python -m pytest tests/unit/test_source_routing.py -v
python -m pytest tests/unit/test_html_discovery.py -v
```

### 2. Integration Tests
```bash
python -m pytest tests/integration/test_sources.py -v
```

### 3. Manual Verification
```bash
python diagnose_rss_feeds.py  # Check RSS feed health
python main.py --test-mode    # Run single cycle
```

## 💡 Recommendations

### Immediate Actions (Today)
1. **Backup current working state**
2. **Fix main.py source routing** (30 min)
3. **Test with current working sources** (BabyPips, FXStreet)
4. **Implement basic HTML discovery** (2 hours)

### Short Term (This Week)  
1. **Complete HTML scraping implementation**
2. **Add RSS fallback parsing**
3. **Replace Bloomberg source**
4. **Add comprehensive testing**

### Long Term (Next Month)
1. **Add smart source health monitoring**
2. **Implement adaptive retry strategies** 
3. **Add more financial news sources**
4. **Optimize memory usage and performance**

This analysis shows you have a solid foundation - the main issue is just incorrect source routing in main.py. Once fixed, your HTML scraping sources should work properly!
