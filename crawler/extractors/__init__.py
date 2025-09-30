"""
Extractors package - Open-Closed Principle implementation.
Easy to extend with new source types without modifying existing code.
"""

from .article_discovery import (
    create_article_discovery,
    DISCOVERY_REGISTRY,
    RSSArticleDiscovery,
    HTMLArticleDiscovery,
    YouTubeArticleDiscovery,
    TwitterArticleDiscovery,
    RedditArticleDiscovery
)

from .content_extractors import (
    create_content_extractor,
    EXTRACTOR_REGISTRY,
    HTMLContentExtractor,
    YouTubeContentExtractor,
    TwitterContentExtractor,
    RedditContentExtractor
)

__all__ = [
    # Factory functions
    'create_article_discovery',
    'create_content_extractor',
    
    # Registries for extension
    'DISCOVERY_REGISTRY',
    'EXTRACTOR_REGISTRY',
    
    # Individual extractors
    'RSSArticleDiscovery',
    'HTMLArticleDiscovery', 
    'HTMLContentExtractor',
    'YouTubeArticleDiscovery',
    'YouTubeContentExtractor',
    'TwitterArticleDiscovery', 
    'TwitterContentExtractor',
    'RedditArticleDiscovery',
    'RedditContentExtractor',
]
