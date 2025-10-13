#!/usr/bin/env python3
"""
Azure-optimized startup script for NewsRagnarok Crawler.
Handles the health server and main crawler in the same process.
Version: 2.0 - Force fresh build
"""
import os
import sys
import time
import json
import asyncio
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler for Azure health checks."""
    
    def do_GET(self):
        """Handle GET requests with application status."""
        try:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            # Get current status from global state
            response = get_application_status()
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_HEAD(self):
        """Handle HEAD requests from Azure health checks."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Reduce HTTP log noise."""
        pass

# Global application state
app_state = {
    'status': 'starting',
    'start_time': time.time(),
    'cycles_completed': 0,
    'cycles_failed': 0,
    'last_cycle_time': None,
    'crawler_running': False,
    'dependencies_status': {
        'qdrant': {'status': 'checking', 'last_check': None, 'error': None},
        'azure': {'status': 'checking', 'last_check': None, 'error': None},
        'openai': {'status': 'checking', 'last_check': None, 'error': None},
        'redis': {'status': 'checking', 'last_check': None, 'error': None}
    }
}

def get_application_status():
    """Get current application status for health endpoint."""
    uptime = time.time() - app_state['start_time']
    
    return {
        "status": "healthy" if app_state['crawler_running'] else "initializing",
        "uptime": f"{int(uptime)}s",
        "dependencies": app_state['dependencies_status'],
        "memory": {
            "memory_mb": get_memory_usage(),
            "check_time": datetime.now().isoformat()
        },
        "metrics": {
            "cycles_completed": app_state['cycles_completed'],
            "cycles_failed": app_state['cycles_failed'],
            "total_articles_processed": 0,  # Will be updated by actual crawler
            "total_duplicates_detected": 0,
            "last_deletion_time": None,
            "last_deletion_count": 0
        },
        "current_cycle": None,
        "timestamp": datetime.now().isoformat(),
        "service": "NewsRagnarok Crawler",
        "port": os.environ.get('PORT', '8000')
    }

def get_memory_usage():
    """Get current memory usage in MB."""
    try:
        import psutil
        return round(psutil.Process().memory_info().rss / 1024 / 1024, 2)
    except ImportError:
        return 0.0

def start_health_server():
    """Start the health check server."""
    port = int(os.environ.get('PORT', 8000))
    
    print(f"Starting health server on port {port}")
    
    try:
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        print(f"Health server ready on http://0.0.0.0:{port}")
        server.serve_forever()
    except Exception as e:
        print(f"Failed to start health server: {e}")
        return False

async def check_dependencies():
    """Check all service dependencies."""
    print("Checking dependencies...")
    
    # Check Qdrant
    try:
        qdrant_url = os.environ.get('QDRANT_URL')
        if qdrant_url:
            print(f"Qdrant URL configured: {qdrant_url}")
            app_state['dependencies_status']['qdrant'] = {
                'status': 'healthy',
                'last_check': datetime.now().isoformat(),
                'error': None
            }
        else:
            raise Exception("QDRANT_URL not configured")
    except Exception as e:
        print(f"Qdrant check failed: {e}")
        app_state['dependencies_status']['qdrant'] = {
            'status': 'unhealthy',
            'last_check': datetime.now().isoformat(),
            'error': str(e)
        }
    
    # Check Azure OpenAI
    try:
        openai_url = os.environ.get('OPENAI_BASE_URL')
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_url and openai_key:
            print(f"Azure OpenAI configured: {openai_url}")
            app_state['dependencies_status']['openai'] = {
                'status': 'healthy',
                'last_check': datetime.now().isoformat(),
                'error': None
            }
        else:
            raise Exception("Azure OpenAI not properly configured")
    except Exception as e:
        print(f"Azure OpenAI check failed: {e}")
        app_state['dependencies_status']['openai'] = {
            'status': 'unhealthy',
            'last_check': datetime.now().isoformat(),
            'error': str(e)
        }
    
    # Check Redis
    try:
        redis_host = os.environ.get('REDIS_HOST')
        if redis_host:
            print(f"Redis configured: {redis_host}")
            app_state['dependencies_status']['redis'] = {
                'status': 'healthy',
                'last_check': datetime.now().isoformat(),
                'error': None
            }
        else:
            raise Exception("Redis not configured")
    except Exception as e:
        print(f"Redis check failed: {e}")
        app_state['dependencies_status']['redis'] = {
            'status': 'unhealthy',
            'last_check': datetime.now().isoformat(),
            'error': str(e)
        }
    
    print("Dependency check completed")

async def run_crawler():
    """Run the main crawler logic."""
    print("Starting crawler...")
    app_state['crawler_running'] = True
    
    try:
        # Import and run the main crawler
        from main import main_loop
        await main_loop()
    except Exception as e:
        print(f"Crawler error: {e}")
        app_state['cycles_failed'] += 1
        # Don't exit, just log the error and continue

def main():
    """Main entry point for Azure deployment."""
    print("=" * 60)
    print("NewsRagnarok Crawler - Azure Optimized Startup")
    print("=" * 60)
    print(f"Start time: {datetime.now()}")
    print(f"PORT: {os.environ.get('PORT', '8000')}")
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
    
    # Set up environment
    os.environ.setdefault('PYTHONUNBUFFERED', '1')
    
    # Create necessary directories
    os.makedirs('data/metrics', exist_ok=True)
    os.makedirs('data/heartbeat', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    print("Directories created")
    
    # Install Playwright browsers for Azure App Service
    print("Installing Playwright browsers...")
    try:
        import subprocess
        
        # Install chromium browser
        result = subprocess.run([
            'python', '-m', 'playwright', 'install', 'chromium'
        ], capture_output=True, text=True, timeout=240)
        
        if result.returncode == 0:
            print("✅ Playwright chromium installed successfully")
        else:
            print(f"⚠️ Playwright install output: {result.stdout}")
            print(f"⚠️ Playwright install errors: {result.stderr}")
        
        # Install system dependencies  
        deps_result = subprocess.run([
            'python', '-m', 'playwright', 'install-deps', 'chromium'
        ], capture_output=True, text=True, timeout=120)
        
        if deps_result.returncode == 0:
            print("✅ Playwright dependencies installed")
        else:
            print(f"⚠️ Dependencies install: {deps_result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("⚠️ Playwright installation timed out - continuing with fallbacks")
    except Exception as e:
        print(f"⚠️ Playwright installation error: {e}")
        print("Continuing - app will use BeautifulSoup fallback extractors")
    
    # Check dependencies first
    asyncio.run(check_dependencies())
    
    # Start health server in a separate thread
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    print("Health server started")
    
    # Give health server a moment to start
    time.sleep(2)
    
    # Start the crawler
    print("Initializing crawler...")
    try:
        asyncio.run(run_crawler())
    except KeyboardInterrupt:
        print("Received interrupt signal")
    except Exception as e:
        print(f"Application error: {e}")
    finally:
        print("Application shutdown")

if __name__ == "__main__":
    main()
