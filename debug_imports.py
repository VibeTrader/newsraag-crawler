#!/usr/bin/env python3
"""
Simple import test to debug the import error.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

print("Testing imports...")

try:
    print("1. Testing base import...")
    from crawler.extractors import crawl4ai_extractor
    print("   ✅ crawl4ai_extractor module imported successfully")
    
    print("2. Testing class import...")
    from crawler.extractors.crawl4ai_extractor import EnhancedCrawl4AIExtractor
    print("   ✅ EnhancedCrawl4AIExtractor class imported successfully")
    
    print("3. Testing backward compatibility...")
    from crawler.extractors.crawl4ai_extractor import Crawl4AIExtractor
    print("   ✅ Crawl4AIExtractor (old name) imported successfully")
    
    print("4. Testing hierarchical template import...")
    from crawler.templates.hierarchical_template import HierarchicalTemplate
    print("   ✅ HierarchicalTemplate imported successfully")
    
    print("\n🎉 All imports successful!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    print(f"Full traceback:\n{traceback.format_exc()}")
    
except Exception as e:
    print(f"❌ Other error: {e}")
    import traceback
    print(f"Full traceback:\n{traceback.format_exc()}")
