#!/usr/bin/env python3
"""
Test script to verify the fixes work for HTML scraping sources.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crawler.factories import load_sources_from_yaml, SourceFactory

async def test_source_types():
    """Test that sources are correctly identified and created."""
    print("Testing source configuration loading...")
    
    # Load sources from YAML
    configs = load_sources_from_yaml('config/sources.yaml')
    
    print(f"\nLoaded {len(configs)} sources:")
    for config in configs:
        print(f"  • {config.name}: {config.source_type.value}")
    
    print(f"\nTesting source creation...")
    
    # Test creating sources
    for config in configs:
        try:
            print(f"\nCreating {config.name} ({config.source_type.value})...")
            source = SourceFactory.create_source(config)
            print(f"SUCCESS {config.name}: Created {type(source).__name__}")
            
            # Test health check
            try:
                is_healthy = await source.health_check()
                print(f"   Health check: {'PASS' if is_healthy else 'FAIL'}")
            except Exception as e:
                print(f"   Health check failed: {e}")
                
        except Exception as e:
            print(f"FAILED {config.name}: Creation failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_source_types())
