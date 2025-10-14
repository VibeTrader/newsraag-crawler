#!/usr/bin/env python3
"""
Azure startup - Nuclear option to fix typing_extensions
"""
import sys
import os

# Step 1: Remove problematic paths FIRST
original_path = sys.path.copy()
sys.path = [p for p in sys.path if '/agents/python' not in p]

# Step 2: Create a fake typing_extensions module with Sentinel
import types
fake_te = types.ModuleType('typing_extensions')

# Add all the basics that might be needed
fake_te.Literal = type('Literal', (), {})
fake_te.TypedDict = type('TypedDict', (), {})
fake_te.Annotated = type('Annotated', (), {})
fake_te.get_args = lambda x: ()
fake_te.get_origin = lambda x: None
fake_te.Protocol = type('Protocol', (), {})

# The critical one - Sentinel
class _FakeSentinel:
    def __repr__(self):
        return '<Sentinel>'

fake_te.Sentinel = _FakeSentinel
fake_te._Sentinel = _FakeSentinel  # In case it tries the underscore version

# Step 3: Force it into sys.modules BEFORE any imports
sys.modules['typing_extensions'] = fake_te
print("✅ Injected fake typing_extensions with Sentinel")

# Step 4: Now import the main app which will use our fake module
try:
    # Import the real main application
    from azure_startup_main import main
    main()
except ImportError as e:
    print(f"Failed to import main: {e}")
    
    # Fallback - run a minimal health server
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
                "message": "Crawler failed due to typing_extensions conflict",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
            self.wfile.write(json.dumps(response).encode())
        
        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()
        
        def log_message(self, format, *args):
            pass
    
    print("Starting minimal health server due to import failure...")
    port = int(os.environ.get('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), MinimalHealthHandler)
    print(f"Health server ready on port {port}")
    server.serve_forever()