# crawler/adapters/__init__.py
"""
Adapters package for NewsRagnarok Crawler.
Contains adapters to integrate existing crawlers with new template system.
"""

from .babypips_adapter import BabyPipsSourceAdapter, create_babypips_adapter
from .fxstreet_adapter import FXStreetSourceAdapter, create_fxstreet_adapter
from .forexlive_adapter import ForexLiveSourceAdapter, create_forexlive_adapter
from .kabutan_adapter import KabutanSourceAdapter, create_kabutan_adapter
from .poundsterlinglive_adapter import PoundSterlingLiveSourceAdapter, create_poundsterlinglive_adapter

__all__ = [
    # BabyPips
    'BabyPipsSourceAdapter',
    'create_babypips_adapter',
    
    # FXStreet
    'FXStreetSourceAdapter', 
    'create_fxstreet_adapter',
    
    # ForexLive
    'ForexLiveSourceAdapter',
    'create_forexlive_adapter',
    
    # Kabutan
    'KabutanSourceAdapter',
    'create_kabutan_adapter',
    
    # PoundSterlingLive
    'PoundSterlingLiveSourceAdapter',
    'create_poundsterlinglive_adapter'
]
