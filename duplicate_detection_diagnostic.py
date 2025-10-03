#!/usr/bin/env python3
"""
Comprehensive duplicate detection diagnostic and fix.
Identifies why duplicates are still being stored in Qdrant.
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
import asyncio

def check_duplicate_detection_integration():
    """Check how duplicate detection is integrated in the processing flow."""
    logger.info("🔍 Analyzing duplicate detection integration...")
    
    problems_found = []
    solutions = []
    
    try:
        # 1. Check if duplicate detector is working
        from monitoring.duplicate_detector import get_duplicate_detector
        detector = get_duplicate_detector()
        logger.info("✅ Duplicate detector imports successfully")
        
        # Test with sample data
        test_article = {
            'url': 'https://test-duplicate.com/article-1',
            'title': 'Test Article for Duplicate Detection'
        }
        
        # First check - should not be duplicate
        is_dup1, dup_type1 = detector.is_duplicate(test_article)
        logger.info(f"📝 First check: is_duplicate={is_dup1}, type={dup_type1}")
        
        # Second check - should be duplicate
        is_dup2, dup_type2 = detector.is_duplicate(test_article)
        logger.info(f"📝 Second check: is_duplicate={is_dup2}, type={dup_type2}")
        
        if not is_dup2:
            problems_found.append("Duplicate detector not working - same article not detected as duplicate")
            solutions.append("Fix duplicate detector logic")
        else:
            logger.info("✅ Duplicate detector working correctly")
    
    except Exception as e:
        problems_found.append(f"Duplicate detector import/initialization failed: {e}")
        solutions.append("Fix duplicate detector imports")
    
    # 2. Check template integration
    try:
        from crawler.templates.base_template import BaseDuplicateChecker
        logger.info("✅ BaseDuplicateChecker imports successfully")
        
        # Check if the base template is using the correct flow
        with open("crawler/templates/base_template.py", "r") as f:
            template_content = f.read()
            
        if "await duplicate_checker.is_duplicate(article_meta)" in template_content:
            logger.info("✅ Base template has duplicate check call")
        else:
            problems_found.append("Base template missing duplicate check call")
            solutions.append("Add duplicate check to base template processing loop")
            
        if "articles_skipped" in template_content:
            logger.info("✅ Base template tracks skipped articles")
        else:
            problems_found.append("Base template not tracking skipped articles")
            solutions.append("Add skipped article tracking")
    
    except Exception as e:
        problems_found.append(f"Base template check failed: {e}")
        solutions.append("Fix base template imports")
    
    # 3. Check if hierarchical template uses duplicate detection
    try:
        with open("crawler/templates/hierarchical_template.py", "r") as f:
            hierarchical_content = f.read()
            
        if "duplicate" in hierarchical_content.lower():
            logger.info("✅ Hierarchical template mentions duplicate detection")
        else:
            problems_found.append("Hierarchical template might not use duplicate detection")
            solutions.append("Ensure hierarchical template inherits duplicate detection")
            
    except Exception as e:
        problems_found.append(f"Hierarchical template check failed: {e}")
    
    return problems_found, solutions

def create_duplicate_detection_test():
    """Create a test to verify duplicate detection in the actual flow."""
    
    test_code = '''#!/usr/bin/env python3
"""
Test duplicate detection in actual processing flow.
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_processing_flow_with_duplicates():
    """Test that duplicates are caught in the processing flow."""
    from monitoring.duplicate_detector import get_duplicate_detector
    from crawler.interfaces import ArticleMetadata
    from datetime import datetime
    
    # Clear cache first
    detector = get_duplicate_detector()
    if hasattr(detector, 'url_cache'):
        detector.url_cache.clear()
        detector.title_cache.clear()
    
    print("Testing duplicate detection in processing flow...")
    
    # Create test article metadata
    article_meta = ArticleMetadata(
        title="Breaking: Market News Update",
        url="https://example.com/market-news-123",
        published_date=datetime.now(),
        source="test_source"
    )
    
    # Test 1: First article should not be duplicate
    article_data = {
        'url': article_meta.url,
        'title': article_meta.title
    }
    
    is_dup1, type1 = detector.is_duplicate(article_data)
    print(f"Test 1 - First occurrence: is_duplicate={is_dup1}, type={type1}")
    
    # Test 2: Same article should be duplicate
    is_dup2, type2 = detector.is_duplicate(article_data)
    print(f"Test 2 - Second occurrence: is_duplicate={is_dup2}, type={type2}")
    
    if is_dup2:
        print("✅ DUPLICATE DETECTION WORKING IN FLOW")
        return True
    else:
        print("❌ DUPLICATE DETECTION NOT WORKING IN FLOW")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_processing_flow_with_duplicates())
    if result:
        print("\\n🎉 Duplicate detection is working!")
    else:
        print("\\n❌ Duplicate detection needs fixing!")
'''
    
    with open("test_duplicate_flow.py", "w") as f:
        f.write(test_code)
    
    logger.info("✅ Created duplicate detection flow test")

def analyze_qdrant_duplicates():
    """Check if Qdrant has duplicate entries."""
    logger.info("🔍 Analyzing Qdrant for duplicate entries...")
    
    try:
        from clients.qdrant_client import get_qdrant_client
        
        # This would require implementing a duplicate check in Qdrant
        logger.info("💡 To check Qdrant duplicates, we need to:")
        logger.info("   1. Query recent articles from Qdrant")
        logger.info("   2. Group by URL and title")
        logger.info("   3. Identify entries with same URL/title")
        logger.info("   4. Count duplicate entries")
        
    except Exception as e:
        logger.error(f"❌ Could not analyze Qdrant: {e}")

def create_enhanced_duplicate_detection():
    """Create enhanced duplicate detection that also checks Qdrant."""
    
    enhanced_detector_code = '''#!/usr/bin/env python3
"""
Enhanced duplicate detector that also checks Qdrant for existing documents.
"""
from typing import Tuple, Optional, Dict, Any
from loguru import logger

class EnhancedDuplicateDetector:
    """Enhanced duplicate detector that checks both cache and Qdrant."""
    
    def __init__(self):
        # Import existing detector
        from monitoring.duplicate_detector import get_duplicate_detector
        self.basic_detector = get_duplicate_detector()
        
        # Import Qdrant client
        try:
            from clients.qdrant_client import get_qdrant_client
            self.qdrant_client = get_qdrant_client()
            self.check_qdrant = True
            logger.info("Enhanced duplicate detector with Qdrant integration")
        except:
            self.qdrant_client = None
            self.check_qdrant = False
            logger.warning("Qdrant not available, using cache-only detection")
    
    async def is_duplicate_enhanced(self, article_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Enhanced duplicate check that includes Qdrant lookup."""
        
        # 1. Check cache first (fast)
        is_cache_dup, cache_type = self.basic_detector.is_duplicate(article_data)
        if is_cache_dup:
            logger.debug(f"Cache duplicate detected: {article_data.get('url', 'No URL')}")
            return True, f"cache_{cache_type}"
        
        # 2. Check Qdrant for existing documents (thorough)
        if self.check_qdrant and self.qdrant_client:
            try:
                is_qdrant_dup = await self._check_qdrant_duplicate(article_data)
                if is_qdrant_dup:
                    logger.debug(f"Qdrant duplicate detected: {article_data.get('url', 'No URL')}")
                    # Add to cache so we don't check Qdrant again
                    self.basic_detector.is_duplicate(article_data)  # This adds to cache
                    return True, "qdrant"
            except Exception as e:
                logger.warning(f"Qdrant duplicate check failed: {e}")
        
        # 3. Not a duplicate - add to cache
        self.basic_detector.is_duplicate(article_data)  # This adds to cache
        return False, None
    
    async def _check_qdrant_duplicate(self, article_data: Dict[str, Any]) -> bool:
        """Check if article exists in Qdrant."""
        try:
            url = article_data.get('url', '')
            title = article_data.get('title', '')
            
            if not url:
                return False
            
            # Search Qdrant for documents with same URL or similar title
            # This is a simplified check - you might want to use vector similarity
            search_results = await self.qdrant_client.search_similar_documents(
                query_text=f"{title} {url}",
                limit=5
            )
            
            for result in search_results:
                # Check if URL matches exactly
                if result.get('url') == url:
                    return True
                
                # Check if title is very similar
                result_title = result.get('title', '')
                if self._titles_similar(title, result_title):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Qdrant duplicate check error: {e}")
            return False
    
    def _titles_similar(self, title1: str, title2: str, threshold: float = 0.9) -> bool:
        """Simple title similarity check."""
        if not title1 or not title2:
            return False
        
        # Normalize titles
        norm1 = title1.lower().strip()
        norm2 = title2.lower().strip()
        
        # Simple similarity - could be enhanced with fuzzy matching
        if norm1 == norm2:
            return True
        
        # Check if one title contains the other (with some tolerance)
        if len(norm1) > 10 and len(norm2) > 10:
            if norm1 in norm2 or norm2 in norm1:
                return True
        
        return False

# Global enhanced detector instance
_enhanced_detector = None

def get_enhanced_duplicate_detector():
    """Get enhanced duplicate detector singleton."""
    global _enhanced_detector
    if _enhanced_detector is None:
        _enhanced_detector = EnhancedDuplicateDetector()
    return _enhanced_detector
'''
    
    with open("enhanced_duplicate_detector.py", "w") as f:
        f.write(enhanced_detector_code)
    
    logger.info("✅ Created enhanced duplicate detector with Qdrant integration")

def main():
    """Main diagnostic function."""
    logger.info("🔍 Starting comprehensive duplicate detection analysis...")
    
    # Check current integration
    problems, solutions = check_duplicate_detection_integration()
    
    # Create test files
    create_duplicate_detection_test()
    create_enhanced_duplicate_detection()
    
    # Analyze potential Qdrant duplicates
    analyze_qdrant_duplicates()
    
    # Report findings
    logger.info("="*80)
    logger.info("📊 DUPLICATE DETECTION DIAGNOSTIC RESULTS")
    logger.info("="*80)
    
    if problems:
        logger.error("❌ Problems found:")
        for i, problem in enumerate(problems, 1):
            logger.error(f"   {i}. {problem}")
        
        logger.info("🔧 Recommended solutions:")
        for i, solution in enumerate(solutions, 1):
            logger.info(f"   {i}. {solution}")
    else:
        logger.info("✅ No obvious problems found in duplicate detection setup")
    
    logger.info("")
    logger.info("🎯 NEXT STEPS:")
    logger.info("1. Run test_duplicate_flow.py to verify detection in processing")
    logger.info("2. Check your logs for 'articles_skipped' to see if duplicates are being caught")
    logger.info("3. Consider using enhanced_duplicate_detector.py for Qdrant integration")
    logger.info("4. Monitor Qdrant collection size growth vs articles processed")

if __name__ == "__main__":
    main()
