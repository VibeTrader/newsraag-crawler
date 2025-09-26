# crawler/templates/__init__.py
"""
Templates package for NewsRagnarok Crawler.
Contains template implementations following Template Method pattern.
"""

from .base_template import (
    BaseNewsSourceTemplate,
    BaseArticleDiscovery,
    BaseContentExtractor,
    BaseContentProcessor,
    BaseDuplicateChecker,
    BaseContentStorage
)

from .rss_template import (
    RSSNewsSourceTemplate,
    RSSArticleDiscovery,
    RSSContentExtractor,
    create_rss_source
)

__all__ = [
    # Base template classes
    'BaseNewsSourceTemplate',
    'BaseArticleDiscovery',
    'BaseContentExtractor', 
    'BaseContentProcessor',
    'BaseDuplicateChecker',
    'BaseContentStorage',
    
    # RSS template classes
    'RSSNewsSourceTemplate',
    'RSSArticleDiscovery',
    'RSSContentExtractor',
    'create_rss_source'
]
