#!/usr/bin/env python3
"""
Azure startup with vendored typing_extensions fix
"""
import sys
import os

# Step 1: Vendor the correct typing_extensions by copying it
def ensure_correct_typing_extensions():
    """Copy the correct typing_extensions to override the broken one."""
    import shutil
    import glob
    
    # Find the correct typing_extensions in venv
    venv_patterns = [
        '/tmp/*/antenv/lib/python3.12/site-packages/typing_extensions.py',
        '/tmp/*/antenv/lib/python*/site-packages/typing_extensions.py'
    ]
    
    correct_te = None
    for pattern in venv_patterns:
        matches = glob.glob(pattern)
        if matches:
            correct_te = matches[0]
            break
    
    if correct_te and os.path.exists(correct_te):
        # Copy it to the current directory to take precedence
        local_te = os.path.join(os.path.dirname(__file__), 'typing_extensions.py')
        shutil.copy2(correct_te, local_te)
        print(f"✅ Vendored typing_extensions from {correct_te}")
        
        # Ensure current directory is first in path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        elif sys.path[0] != current_dir:
            sys.path.remove(current_dir)
            sys.path.insert(0, current_dir)
        
        return True
    return False

# Step 2: Clean the environment
sys.path = [p for p in sys.path if '/agents/python' not in p]
if 'PYTHONPATH' in os.environ:
    os.environ['PYTHONPATH'] = ':'.join([
        p for p in os.environ['PYTHONPATH'].split(':') 
        if '/agents/python' not in p
    ])

# Step 3: Vendor the module
if not ensure_correct_typing_extensions():
    print("⚠️ Could not vendor typing_extensions, trying direct import")

# Step 4: Test the import
try:
    from typing_extensions import Sentinel
    print("✅ Sentinel import successful")
except ImportError as e:
    print(f"❌ Failed to import Sentinel: {e}")
    # Last resort: mock it
    print("Creating mock Sentinel as fallback...")
    import typing_extensions
    typing_extensions.Sentinel = type('Sentinel', (), {})
    print("✅ Mock Sentinel created")

# Step 5: Import the main application
from azure_startup_main import main

if __name__ == "__main__":
    main()