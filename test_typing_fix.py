#!/usr/bin/env python3
"""
Test script to verify typing_extensions fix works locally
"""
import os
import sys

print("=" * 60)
print("Testing typing_extensions import fix")
print("=" * 60)

# Show current sys.path
print("\nOriginal sys.path (first 5 entries):")
for i, path in enumerate(sys.path[:5]):
    print(f"  {i}: {path}")

# Simulate Azure's environment by adding a fake /agents/python path
fake_azure_path = '/agents/python'
if fake_azure_path not in sys.path:
    sys.path.insert(0, fake_azure_path)
    print(f"\nAdded fake Azure path: {fake_azure_path}")

# Show modified path
print("\nModified sys.path (first 5 entries):")
for i, path in enumerate(sys.path[:5]):
    print(f"  {i}: {path}")

# Apply the fix
sys.path = [p for p in sys.path if '/agents/python' not in p]
print("\nApplied fix: Removed /agents/python from sys.path")

# Show cleaned path
print("\nCleaned sys.path (first 5 entries):")
for i, path in enumerate(sys.path[:5]):
    print(f"  {i}: {path}")

# Test importing typing_extensions
print("\nTesting imports:")
try:
    import typing_extensions
    print(f"[OK] typing_extensions imported from: {typing_extensions.__file__}")
    
    # Check for Sentinel
    if hasattr(typing_extensions, 'Sentinel'):
        print("[OK] typing_extensions.Sentinel is available")
    else:
        print("[FAIL] typing_extensions.Sentinel is NOT available")
        print(f"   Available attributes: {[attr for attr in dir(typing_extensions) if not attr.startswith('_')][:10]}...")
        
except ImportError as e:
    print(f"[FAIL] Failed to import typing_extensions: {e}")

# Test pydantic import
try:
    from pydantic import BaseModel
    print("[OK] pydantic imported successfully")
except ImportError as e:
    print(f"[FAIL] Failed to import pydantic: {e}")

# Test crawl4ai import (if available)
try:
    from crawl4ai import AsyncWebCrawler
    print("[OK] crawl4ai imported successfully")
except ImportError as e:
    print(f"[FAIL] Failed to import crawl4ai: {e}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)