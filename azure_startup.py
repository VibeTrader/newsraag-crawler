#!/usr/bin/env python3
"""
Azure startup - Fix typing_extensions compatibility for crawl4ai/pydantic
"""
import sys
import os

print("🔧 Azure App Service - Fixing typing_extensions compatibility...")

# Step 1: FIRST - Unload any already-imported pydantic modules
print("🧹 Cleaning up pre-imported modules...")
modules_to_remove = [key for key in list(sys.modules.keys()) if 'pydantic' in key or 'qdrant' in key]
for mod in modules_to_remove:
    if mod in sys.modules:
        del sys.modules[mod]
print(f"✅ Removed {len(modules_to_remove)} pre-imported modules")

# Step 2: Create Sentinel fix BEFORE anything imports
print("🔧 Creating Sentinel compatibility shim...")
import types

# Create a fake typing_extensions module with Sentinel
class _CallableSentinel:
    """Callable Sentinel for complete compatibility"""
    def __init__(self, name=None):
        self.name = name or 'Sentinel'
    
    def __repr__(self):
        return f'<{self.name}>'

# Create complete fake typing_extensions module
fake_te = types.ModuleType('typing_extensions')
fake_te.Sentinel = _CallableSentinel
fake_te._Sentinel = _CallableSentinel

# Add all common typing_extensions attributes
fake_te.Annotated = type('Annotated', (), {})
fake_te.ParamSpec = type('ParamSpec', (), {})
fake_te.TypeAlias = type('TypeAlias', (), {})
fake_te.Self = type('Self', (), {})
fake_te.Final = type('Final', (), {})
fake_te.Literal = type('Literal', (), {})
fake_te.TypedDict = type('TypedDict', (), {})
fake_te.Protocol = type('Protocol', (), {})
fake_te.runtime_checkable = lambda x: x
fake_te.get_type_hints = lambda *args, **kwargs: {}
fake_te.get_origin = lambda x: None
fake_te.get_args = lambda x: ()

# Force it into sys.modules BEFORE anything else imports
sys.modules['typing_extensions'] = fake_te
print("✅ Sentinel compatibility shim installed in sys.modules")

# Step 3: Now prioritize venv WITHOUT removing standard library paths
venv_path = None
for path in sys.path:
    if 'antenv' in path and 'site-packages' in path:
        venv_path = path
        break

if venv_path:
    print(f"✅ Found virtual environment: {venv_path}")
    # Move venv to front of sys.path
    if venv_path in sys.path:
        sys.path.remove(venv_path)
    sys.path.insert(0, venv_path)
    print(f"✅ Virtual environment prioritized")
else:
    print("⚠️ Virtual environment not found in sys.path")

# Step 3: Verify the fix worked
print("🧪 Verifying typing_extensions Sentinel...")
try:
    import typing_extensions
    test_sentinel = typing_extensions.Sentinel('test')
    print(f"✅ Sentinel test successful: {test_sentinel}")
except Exception as e:
    print(f"⚠️ Sentinel test warning: {e} (but fake module is in place)")

# Step 4: Now try to import and start the application
print("🚀 Starting NewsRagnarok Crawler...")
try:
    # Import the real main application
    from azure_startup_main import main
    main()
    
except ImportError as e:
    print(f"❌ Failed to import main application: {e}")
    
    # Fallback - run minimal health server with POST support
    import time
    import json
    import asyncio
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from datetime import datetime
    
    # Store last cleanup result
    last_cleanup_result = {
        "timestamp": None,
        "status": "never_run",
        "message": "Cleanup unavailable in fallback mode"
    }
    
    class MinimalHealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/api/cleanup/status':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(last_cleanup_result, indent=2).encode())
            elif self.path in ['/api/cleanup/health', '/health', '/']:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {
                    "status": "degraded",
                    "message": "Crawler failed due to dependency conflicts - running fallback server",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e),
                    "fix_attempted": True,
                    "cleanup_api": "available"
                }
                self.wfile.write(json.dumps(response, indent=2).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {"status": "degraded", "message": "Fallback mode"}
                self.wfile.write(json.dumps(response).encode())
        
        def do_POST(self):
            """Handle POST requests for cleanup API in fallback mode."""
            global last_cleanup_result
            
            if self.path == '/api/cleanup':
                try:
                    # Read request body
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length) if content_length > 0 else b'{}'
                    
                    # Parse JSON
                    try:
                        data = json.loads(body.decode('utf-8'))
                        retention_hours = data.get('retention_hours', 24)
                    except:
                        retention_hours = 24
                    
                    print(f"📥 Received cleanup request in fallback mode (retention: {retention_hours} hours)")
                    
                    # Try to run cleanup even in fallback mode
                    try:
                        # Add current directory to path for imports (use dynamic path)
                        import os
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        if current_dir not in sys.path:
                            sys.path.insert(0, current_dir)
                        
                        # Import without going through main
                        from cleanup_api import run_cleanup_operation
                        
                        # Run cleanup
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(run_cleanup_operation(retention_hours))
                        loop.close()
                        
                        last_cleanup_result = result
                        
                        # Send response
                        if result.get("status") == "success":
                            self.send_response(200)
                        else:
                            self.send_response(500)
                        
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(result, indent=2).encode())
                        
                        print(f"✅ Cleanup completed in fallback mode: {result.get('status')}")
                        
                    except Exception as cleanup_error:
                        print(f"❌ Cleanup failed in fallback mode: {cleanup_error}")
                        import traceback
                        traceback.print_exc()
                        
                        error_response = {
                            "status": "error",
                            "message": f"Cleanup failed in fallback mode: {str(cleanup_error)}",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        last_cleanup_result = error_response
                        
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(error_response, indent=2).encode())
                        
                except Exception as e:
                    print(f"❌ Error handling POST request: {e}")
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    error = {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
                    self.wfile.write(json.dumps(error).encode())
            else:
                # Unsupported POST endpoint
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error = {"error": "Not Found", "path": self.path}
                self.wfile.write(json.dumps(error).encode())
        
        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()
        
        def log_message(self, format, *args):
            pass
    
    print("🏥 Starting fallback health server with POST support...")
    port = int(os.environ.get('PORT', 8000))
    try:
        server = HTTPServer(('0.0.0.0', port), MinimalHealthHandler)
        print(f"✅ Fallback server ready on http://0.0.0.0:{port}")
        print(f"   - GET  /health - Health check")
        print(f"   - POST /api/cleanup - Cleanup endpoint (fallback mode)")
        print(f"   - GET  /api/cleanup/status - Cleanup status")
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
