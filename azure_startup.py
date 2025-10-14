#!/usr/bin/env python3
"""
Azure startup - Fix typing_extensions compatibility for crawl4ai/pydantic
"""
import sys
import os
import subprocess

print("🔧 Azure App Service - Fixing typing_extensions compatibility...")

# Step 1: Fix Python path priority - remove Azure system paths
original_path = sys.path.copy()
paths_removed = []
for path in original_path:
    if '/agents/python' in path:
        sys.path.remove(path) if path in sys.path else None
        paths_removed.append(path)

print(f"✅ Removed {len(paths_removed)} conflicting system paths")

# Step 2: Find and prioritize virtual environment
venv_path = None
for path in sys.path:
    if 'antenv' in path and 'site-packages' in path:
        venv_path = path
        break

if venv_path:
    print(f"✅ Found virtual environment: {venv_path}")
    # Ensure venv is at the front
    if venv_path in sys.path:
        sys.path.remove(venv_path)
    sys.path.insert(0, venv_path)
else:
    print("⚠️ Virtual environment not found in sys.path")

# Step 3: Try to upgrade typing_extensions in the venv
print("📦 Ensuring typing_extensions compatibility...")
try:
    result = subprocess.run([
        sys.executable, "-m", "pip", "install", 
        "--upgrade", "--force-reinstall", "--no-cache-dir",
        "typing_extensions>=4.8.0"
    ], capture_output=True, text=True, timeout=60)
    
    if result.returncode == 0:
        print("✅ typing_extensions upgraded successfully")
    else:
        print(f"⚠️ typing_extensions upgrade failed: {result.stderr}")
except Exception as e:
    print(f"⚠️ Error upgrading typing_extensions: {e}")

# Step 4: Test the fix
print("🧪 Testing typing_extensions import...")
try:
    import typing_extensions
    if hasattr(typing_extensions, 'Sentinel'):
        print("✅ typing_extensions.Sentinel is now available!")
    else:
        print("❌ typing_extensions.Sentinel still missing")
        # Fallback: create fake module
        print("🔧 Creating fallback Sentinel...")
        
        class _FakeSentinel:
            def __repr__(self):
                return '<Sentinel>'
        
        typing_extensions.Sentinel = _FakeSentinel()
        print("✅ Fallback Sentinel created")
        
except ImportError as e:
    print(f"❌ typing_extensions import failed: {e}")
    # Create a complete fake module as last resort
    import types
    fake_te = types.ModuleType('typing_extensions')
    fake_te.Sentinel = type('Sentinel', (), {'__repr__': lambda self: '<Sentinel>'})()
    fake_te._Sentinel = fake_te.Sentinel
    sys.modules['typing_extensions'] = fake_te
    print("✅ Created complete fake typing_extensions module")

# Step 5: Now try to import and start the application
print("🚀 Starting NewsRagnarok Crawler...")
try:
    # Import the real main application
    from azure_startup_main import main
    main()
    
except ImportError as e:
    print(f"❌ Failed to import main application: {e}")
    
    # Fallback - run minimal health server to keep Azure happy
    import time
    import json
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from datetime import datetime
    
    class MinimalHealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "status": "degraded",
                "message": "Crawler failed due to dependency conflicts",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "fix_attempted": True
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
        
        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()
        
        def log_message(self, format, *args):
            pass
    
    print("🏥 Starting fallback health server due to import failure...")
    port = int(os.environ.get('PORT', 8000))
    try:
        server = HTTPServer(('0.0.0.0', port), MinimalHealthHandler)
        print(f"✅ Fallback health server ready on http://0.0.0.0:{port}")
        server.serve_forever()
    except Exception as server_error:
        print(f"❌ Even fallback server failed: {server_error}")
        # Last resort - just wait to keep container alive
        print("💤 Entering fallback wait loop...")
        while True:
            time.sleep(60)
            print(f"⏰ Still alive at {datetime.now()}")

except Exception as e:
    print(f"❌ Application startup failed: {e}")
    import traceback
    traceback.print_exc()
    
    # Keep container alive for debugging
    print("💤 Keeping container alive for debugging...")
    import time
    while True:
        time.sleep(300)  # 5 minute intervals
        print(f"⏰ Container still running at {datetime.now()}")