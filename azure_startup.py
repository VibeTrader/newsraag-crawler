#!/usr/bin/env python3
"""
Wrapper to fix typing_extensions import before starting the main app
"""
import sys
import os

# Remove problematic paths BEFORE any imports
original_path = sys.path.copy()
sys.path = [p for p in sys.path if '/agents/python' not in p]

# Clean environment
if 'PYTHONPATH' in os.environ:
    os.environ['PYTHONPATH'] = ':'.join([
        p for p in os.environ['PYTHONPATH'].split(':') 
        if '/agents/python' not in p
    ])

# Find and prioritize venv
import glob
for pattern in ['/tmp/*/antenv/lib/python3.12/site-packages']:
    matches = glob.glob(pattern)
    if matches:
        sys.path.insert(0, matches[0])
        print(f"Using venv: {matches[0]}")
        break

# Test import
try:
    from typing_extensions import Sentinel
    print("✅ Sentinel available - proceeding with startup")
except ImportError as e:
    print(f"❌ Still failing: {e}")
    print(f"Path: {sys.path}")
    
# Import the actual startup
from azure_startup_main import main

if __name__ == "__main__":
    main()