"""
Compatibility module to handle typing_extensions version differences.
Azure App Service sometimes has older typing_extensions without Sentinel.
"""
try:
    from typing_extensions import Sentinel
except ImportError:
    # Fallback for older typing_extensions versions
    from typing import Any
    
    class _SentinelType:
        """Fallback Sentinel implementation"""
        def __repr__(self):
            return "SENTINEL"
    
    Sentinel = _SentinelType()

# Export for use by other modules
__all__ = ['Sentinel']
