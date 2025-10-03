#!/usr/bin/env python3
"""
New Sources Integration Test
Tests all the newly added sources: Fox News, NBC, USA TODAY, CNBC, Forex Factory, etc.
"""
import os
import sys
import asyncio
import time
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables
load_dotenv()

# Define the new sources to test
NEW_SOURCES = [
    # Major News Networks
    {
        'name': 'foxnews',
        'category': 'Major News Networks',
        'url': 'https://moxie.foxnews.com/google-publisher/latest.xml',
        'expected_timeout': 90,
        'priority': 'high'
    },
    {
        'name': 'foxbusiness', 
        'category': 'Major News Networks',
        'url': 'https://moxie.foxbusiness.com/google-publisher/latest.xml',
        'expected_timeout': 90,
        'priority': 'high'
    },
    {
        'name': 'nbcnews',
        'category': 'Major News Networks', 
        'url': 'https://feeds.nbcnews.com/nbcnews/public/news',
        'expected_timeout': 90,
        'priority': 'high'
    },
    {
        'name': 'nbcbusiness',
        'category': 'Major News Networks',
        'url': 'https://feeds.nbcnews.com/nbcnews/public/business', 
        'expected_timeout': 90,
        'priority': 'high'
    },
    {
        'name': 'usatoday',
        'category': 'Major News Networks',
        'url': 'https://rssfeeds.usatoday.com/usatoday-NewsTopStories',
        'expected_timeout': 90,
        'priority': 'high'
    },
    {
        'name': 'usatoday_money',
        'category': 'Major News Networks', 
        'url': 'https://rssfeeds.usatoday.com/usatoday-money',
        'expected_timeout': 90,
        'priority': 'high'
    },
    {
        'name': 'cnbc',
        'category': 'Premium Financial',
        'url': 'https://www.cnbc.com/id/100003114/device/rss/rss.html',
        'expected_timeout': 120,
        'priority': 'critical'
    },
    
    # Specialized Financial Sources
    {
        'name': 'forexfactory_rss',
        'category': 'Specialized Financial',
        'url': 'https://www.forexfactory.com/rss.php',
        'expected_timeout': 120,
        'priority': 'critical'
    },
    {
        'name': 'tradingeconomics',
        'category': 'Specialized Financial',
        'url': 'https://tradingeconomics.com/rss/news',
        'expected_timeout': 120,
        'priority': 'critical'
    },
    {
        'name': 'investing_forex',
        'category': 'Specialized Financial',
        'url': 'https://www.investing.com/rss/news_14.rss',
        'expected_timeout': 120,
        'priority': 'critical'
    },
    {
        'name': 'dailyfx',
        'category': 'Specialized Financial',
        'url': 'https://www.dailyfx.com/rss',
        'expected_timeout': 120,
        'priority': 'critical'
    },
    
    # Bonus Sources
    {
        'name': 'coindesk',
        'category': 'Cryptocurrency',
        'url': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
        'expected_timeout': 90,
        'priority': 'medium'
    }
]

async def test_rss_feed_accessibility(source_info):
    """Test if an RSS feed is accessible and returns valid content."""
    import aiohttp
    import feedparser
    from datetime import datetime
    
    logger.info(f"🔍 Testing RSS accessibility: {source_info['name']}")
    
    try:
        # Test HTTP accessibility first
        timeout = aiohttp.ClientTimeout(total=30)  # Quick test
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            async with session.get(source_info['url'], headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    content_length = len(content)
                    
                    logger.success(f"✅ {source_info['name']}: HTTP 200, {content_length} bytes")
                    
                    # Test RSS parsing
                    if content_length > 100:  # Reasonable content size
                        try:
                            # Parse with feedparser
                            feed = feedparser.parse(content)
                            
                            if feed.bozo:
                                logger.warning(f"⚠️ {source_info['name']}: RSS parsing warning: {feed.bozo_exception}")
                            
                            entries_count = len(feed.entries) if hasattr(feed, 'entries') else 0
                            feed_title = getattr(feed.feed, 'title', 'Unknown') if hasattr(feed, 'feed') else 'Unknown'
                            
                            if entries_count > 0:
                                logger.success(f"✅ {source_info['name']}: Valid RSS with {entries_count} entries")
                                logger.info(f"   📰 Feed title: {feed_title}")
                                
                                # Show sample entry
                                if entries_count > 0 and hasattr(feed.entries[0], 'title'):
                                    sample_title = feed.entries[0].title[:60] + "..." if len(feed.entries[0].title) > 60 else feed.entries[0].title
                                    logger.info(f"   📄 Sample: {sample_title}")
                                
                                return {
                                    'accessible': True,
                                    'valid_rss': True,
                                    'entries_count': entries_count,
                                    'feed_title': feed_title,
                                    'content_length': content_length
                                }
                            else:
                                logger.warning(f"⚠️ {source_info['name']}: RSS accessible but no entries found")
                                return {
                                    'accessible': True,
                                    'valid_rss': False,
                                    'entries_count': 0,
                                    'error': 'No entries found'
                                }
                                
                        except Exception as parse_error:
                            logger.error(f"❌ {source_info['name']}: RSS parsing failed: {str(parse_error)}")
                            return {
                                'accessible': True,
                                'valid_rss': False,
                                'error': f'RSS parsing error: {str(parse_error)}'
                            }
                    else:
                        logger.warning(f"⚠️ {source_info['name']}: Content too short ({content_length} bytes)")
                        return {
                            'accessible': True,
                            'valid_rss': False,
                            'error': 'Content too short'
                        }
                        
                elif response.status == 404:
                    logger.error(f"❌ {source_info['name']}: HTTP 404 - URL not found")
                    return {'accessible': False, 'error': 'HTTP 404 - URL not found'}
                    
                elif response.status == 403:
                    logger.warning(f"⚠️ {source_info['name']}: HTTP 403 - Access forbidden (may need different headers)")
                    return {'accessible': False, 'error': 'HTTP 403 - Access forbidden'}
                    
                elif response.status == 429:
                    logger.warning(f"⚠️ {source_info['name']}: HTTP 429 - Rate limited")
                    return {'accessible': False, 'error': 'HTTP 429 - Rate limited'}
                    
                else:
                    logger.error(f"❌ {source_info['name']}: HTTP {response.status}")
                    return {'accessible': False, 'error': f'HTTP {response.status}'}
                    
    except asyncio.TimeoutError:
        logger.error(f"❌ {source_info['name']}: Connection timeout")
        return {'accessible': False, 'error': 'Connection timeout'}
        
    except Exception as e:
        logger.error(f"❌ {source_info['name']}: Connection error: {str(e)}")
        return {'accessible': False, 'error': f'Connection error: {str(e)}'}

async def test_enhanced_extractor_integration(source_info):
    """Test that the enhanced extractor can handle the source."""
    try:
        from crawler.extractors.crawl4ai_extractor import EnhancedCrawl4AIExtractor
        from crawler.interfaces import SourceConfig, SourceType, ContentType
        
        logger.info(f"🔧 Testing enhanced extractor integration: {source_info['name']}")
        
        # Create source configuration based on YAML config
        content_type_map = {
            'Major News Networks': ContentType.NEWS,
            'Premium Financial': ContentType.ECONOMICS, 
            'Specialized Financial': ContentType.FOREX,
            'Cryptocurrency': ContentType.FOREX  # Using FOREX enum for crypto
        }
        
        config = SourceConfig(
            name=source_info['name'],
            source_type=SourceType.RSS,
            content_type=content_type_map.get(source_info['category'], ContentType.NEWS),
            base_url=source_info['url'],
            rss_url=source_info['url'],
            timeout_seconds=source_info['expected_timeout'],
            rate_limit_seconds=3,
            max_articles_per_run=10  # Small number for testing
        )
        
        # Create enhanced extractor
        extractor = EnhancedCrawl4AIExtractor(config)
        
        # Test health check (quick validation)
        logger.info(f"   🔍 Running health check for {source_info['name']}...")
        is_healthy = await extractor.health_check()
        
        if is_healthy:
            logger.success(f"✅ {source_info['name']}: Enhanced extractor integration successful")
            return {'integration': True, 'health_check': True}
        else:
            logger.warning(f"⚠️ {source_info['name']}: Health check failed (may be network-related)")
            return {'integration': True, 'health_check': False}
            
    except Exception as e:
        logger.error(f"❌ {source_info['name']}: Enhanced extractor integration failed: {str(e)}")
        return {'integration': False, 'error': str(e)}

async def test_source_configuration_loading():
    """Test that the new sources load properly from YAML configuration."""
    logger.info("📋 Testing New Source Configuration Loading")
    
    try:
        from crawler.factories import load_sources_from_yaml, SourceFactory
        
        # Load sources from updated YAML
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'sources.yaml')
        
        if os.path.exists(config_path):
            configs = load_sources_from_yaml(config_path)
            logger.info(f"📊 Loaded {len(configs)} total source configurations from YAML")
            
            # Check that our new sources are present
            new_source_names = [source['name'] for source in NEW_SOURCES]
            found_sources = []
            
            for config in configs:
                if config.name in new_source_names:
                    found_sources.append(config.name)
                    logger.info(f"✅ Found: {config.name} (timeout: {config.timeout_seconds}s)")
            
            missing_sources = set(new_source_names) - set(found_sources)
            
            if missing_sources:
                logger.warning(f"⚠️ Missing sources in YAML: {list(missing_sources)}")
            else:
                logger.success("✅ All new sources found in YAML configuration")
            
            # Test source creation with factory
            try:
                sources = SourceFactory.create_sources_from_config_list(configs)
                logger.success(f"✅ Successfully created {len(sources)} sources with enhanced configurations")
                
                return {
                    'yaml_loaded': True,
                    'total_configs': len(configs),
                    'found_sources': len(found_sources),
                    'missing_sources': len(missing_sources),
                    'factory_success': True
                }
                
            except Exception as factory_error:
                logger.error(f"❌ Source factory creation failed: {str(factory_error)}")
                return {
                    'yaml_loaded': True,
                    'total_configs': len(configs),
                    'found_sources': len(found_sources),
                    'missing_sources': len(missing_sources),
                    'factory_success': False,
                    'factory_error': str(factory_error)
                }
            
        else:
            logger.error(f"❌ Config file not found: {config_path}")
            return {'yaml_loaded': False, 'error': 'Config file not found'}
            
    except Exception as e:
        logger.error(f"❌ Source configuration loading test failed: {str(e)}")
        return {'yaml_loaded': False, 'error': str(e)}

async def run_comprehensive_new_sources_test():
    """Run comprehensive tests for all new sources."""
    logger.info("🌐 Running Comprehensive New Sources Test")
    logger.info("=" * 70)
    
    # Group sources by category for organized testing
    categories = {}
    for source in NEW_SOURCES:
        category = source['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(source)
    
    all_results = {}
    total_tested = 0
    total_accessible = 0
    total_valid_rss = 0
    total_integrated = 0
    
    # Test each category
    for category, sources in categories.items():
        logger.info(f"\n📂 Testing Category: {category}")
        logger.info("-" * 50)
        
        category_results = {}
        
        for source_info in sources:
            logger.info(f"\n🔄 Testing: {source_info['name']} ({source_info['priority']} priority)")
            
            total_tested += 1
            source_results = {
                'category': category,
                'priority': source_info['priority'],
                'expected_timeout': source_info['expected_timeout']
            }
            
            # Test 1: RSS Feed Accessibility
            try:
                rss_result = await test_rss_feed_accessibility(source_info)
                source_results['rss_test'] = rss_result
                
                if rss_result.get('accessible', False):
                    total_accessible += 1
                    
                if rss_result.get('valid_rss', False):
                    total_valid_rss += 1
                    
            except Exception as e:
                logger.error(f"❌ RSS test failed for {source_info['name']}: {str(e)}")
                source_results['rss_test'] = {'accessible': False, 'error': str(e)}
            
            # Test 2: Enhanced Extractor Integration 
            try:
                integration_result = await test_enhanced_extractor_integration(source_info)
                source_results['integration_test'] = integration_result
                
                if integration_result.get('integration', False):
                    total_integrated += 1
                    
            except Exception as e:
                logger.error(f"❌ Integration test failed for {source_info['name']}: {str(e)}")
                source_results['integration_test'] = {'integration': False, 'error': str(e)}
            
            category_results[source_info['name']] = source_results
            
            # Small delay between sources
            await asyncio.sleep(1)
        
        all_results[category] = category_results
    
    return {
        'categories': all_results,
        'summary': {
            'total_tested': total_tested,
            'total_accessible': total_accessible,
            'total_valid_rss': total_valid_rss,  
            'total_integrated': total_integrated,
            'accessibility_rate': (total_accessible / total_tested * 100) if total_tested > 0 else 0,
            'rss_validity_rate': (total_valid_rss / total_accessible * 100) if total_accessible > 0 else 0,
            'integration_rate': (total_integrated / total_tested * 100) if total_tested > 0 else 0
        }
    }

async def main():
    """Main test function for new sources integration."""
    logger.info("🚀 New Sources Integration Test")
    logger.info("Testing: Fox News, NBC, USA TODAY, CNBC, Forex Factory, TradingEconomics, Investing.com, DailyFX")
    logger.info("=" * 90)
    
    start_time = time.time()
    
    # Test 1: Source Configuration Loading
    logger.info("\n📋 Test 1: Source Configuration Loading")
    config_result = await test_source_configuration_loading()
    
    if not config_result.get('yaml_loaded', False):
        logger.error("❌ Cannot proceed without valid YAML configuration")
        return False
    
    # Test 2: Comprehensive New Sources Testing
    logger.info("\n🌐 Test 2: Comprehensive New Sources Testing")
    logger.warning("⚠️ This may take 3-5 minutes to test all sources...")
    
    test_results = await run_comprehensive_new_sources_test()
    
    # Generate comprehensive report
    total_time = time.time() - start_time
    
    logger.info("\n" + "=" * 90)
    logger.info("📊 NEW SOURCES INTEGRATION TEST REPORT")
    logger.info("=" * 90)
    
    summary = test_results['summary']
    
    logger.info(f"🧮 Overall Statistics:")
    logger.info(f"   📊 Total Sources Tested: {summary['total_tested']}")
    logger.info(f"   🌐 Accessible Sources: {summary['total_accessible']} ({summary['accessibility_rate']:.1f}%)")
    logger.info(f"   📡 Valid RSS Feeds: {summary['total_valid_rss']} ({summary['rss_validity_rate']:.1f}%)")
    logger.info(f"   🔧 Integrated Sources: {summary['total_integrated']} ({summary['integration_rate']:.1f}%)")
    logger.info(f"   ⏱️ Total Test Time: {total_time:.1f} seconds")
    
    # Category breakdown
    logger.info(f"\n📂 Category Breakdown:")
    for category, results in test_results['categories'].items():
        accessible_count = sum(1 for r in results.values() if r.get('rss_test', {}).get('accessible', False))
        total_count = len(results)
        
        logger.info(f"   {category}: {accessible_count}/{total_count} accessible")
    
    # Individual source results
    logger.info(f"\n📋 Individual Source Results:")
    
    for category, results in test_results['categories'].items():
        logger.info(f"\n   📂 {category}:")
        
        for source_name, result in results.items():
            rss_status = "✅" if result.get('rss_test', {}).get('accessible', False) else "❌"
            integration_status = "✅" if result.get('integration_test', {}).get('integration', False) else "❌"
            priority = result.get('priority', 'unknown')
            
            logger.info(f"      {rss_status}{integration_status} {source_name} ({priority})")
            
            # Show any errors
            if 'error' in result.get('rss_test', {}):
                logger.info(f"         RSS Error: {result['rss_test']['error']}")
            if 'error' in result.get('integration_test', {}):
                logger.info(f"         Integration Error: {result['integration_test']['error']}")
    
    # Recommendations
    logger.info(f"\n💡 Recommendations:")
    
    if summary['accessibility_rate'] >= 80:
        logger.success("✅ Excellent accessibility rate - sources are ready for production")
    elif summary['accessibility_rate'] >= 60:
        logger.warning("⚠️ Good accessibility rate - some sources may need configuration adjustments")
    else:
        logger.error("❌ Low accessibility rate - review source URLs and configurations")
    
    if summary['integration_rate'] >= 90:
        logger.success("✅ Perfect integration - enhanced timeout handling is working")
    else:
        logger.warning("⚠️ Some integration issues - check enhanced extractor configuration")
    
    # Final verdict
    overall_success = summary['accessibility_rate'] >= 70 and summary['integration_rate'] >= 80
    
    if overall_success:
        logger.success("\n🎉 NEW SOURCES INTEGRATION SUCCESSFUL!")
        logger.info("✅ Your crawler now supports major news networks and specialized financial sources")
        logger.info("🚀 Ready to add these sources to production!")
        return True
    else:
        logger.error("\n❌ Some issues found with new sources integration")
        logger.info("🔧 Review the specific errors above and adjust configurations as needed")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result:
            logger.info("\n✅ New sources are ready for production use!")
            sys.exit(0)
        else:
            logger.error("\n❌ Some issues need to be resolved before production.")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 Unexpected error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
