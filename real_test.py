#!/usr/bin/env python3
"""
Real test of the hierarchical extraction system.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.factories import load_sources_from_yaml, SourceFactory

async def real_test():
    try:
        print("Loading sources...")
        sources = load_sources_from_yaml('config/sources.yaml')
        
        print(f"Testing with {sources[0].name}...")
        source = SourceFactory.create_source(sources[0])  # babypips
        
        print("Trying to fetch 1 article...")
        articles = await source.fetch_articles(max_articles=1)
        
        print(f"Result: {len(articles)} articles")
        if articles:
            article = articles[0]
            print(f"Title: {article.title[:50]}...")
            print(f"URL: {article.url}")
            print(f"Article ID: {article.article_id}")
            print(f"Source: {article.source_name}")
            print(f"Published: {article.published_date}")
            if article.author:
                print(f"Author: {article.author}")
            
            # Check extraction stats from the source
            if hasattr(source, 'get_extraction_stats'):
                stats = source.get_extraction_stats()
                successful_methods = [method for method, data in stats.items() if data['successes'] > 0]
                print(f"Extraction methods used: {successful_methods}")
            
            return True
        else:
            print("No articles extracted")
            return False
            
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(real_test())
    print(f"\nReal test result: {'PASS' if success else 'FAIL'}")
