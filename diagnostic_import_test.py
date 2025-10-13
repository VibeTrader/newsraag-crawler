#!/usr/bin/env python3
"""
Quick diagnostic script to identify which import is failing.
Run this to see where the Sentinel import error occurs.
"""
import sys

def test_import(module_name):
    """Test importing a module and report success/failure"""
    try:
        __import__(module_name)
        print(f"✅ {module_name} imported successfully")
        return True
    except Exception as e:
        print(f"❌ {module_name} failed: {e}")
        return False

def main():
    print("Testing imports to identify typing_extensions.Sentinel issue...")
    print("=" * 60)
    
    # Test core modules first
    modules_to_test = [
        "typing_extensions",
        "pydantic", 
        "qdrant_client",
        "crawl4ai",
        "openai",
        "crawler",
        "monitoring",
        "clients"
    ]
    
    failed_imports = []
    
    for module in modules_to_test:
        if not test_import(module):
            failed_imports.append(module)
    
    print("=" * 60)
    if failed_imports:
        print(f"Failed imports: {', '.join(failed_imports)}")
        print("These are likely causing the Sentinel import issue.")
    else:
        print("All imports successful!")
    
    # Test typing_extensions.Sentinel specifically
    try:
        from typing_extensions import Sentinel
        print("✅ typing_extensions.Sentinel available")
    except ImportError as e:
        print(f"❌ typing_extensions.Sentinel not available: {e}")

if __name__ == "__main__":
    main()
