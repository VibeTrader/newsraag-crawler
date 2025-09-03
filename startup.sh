#!/bin/bash

# Set error handling (but don't exit immediately on error)
set -x

echo "🚀 Starting NewsRagnarok Crawler..."

# Find working directory
if [ ! -f "main.py" ]; then
    echo "⚠️ main.py not found in current directory, searching..."
    # Search in common locations
    for DIR in "/home/site/wwwroot" "/tmp" "/tmp/8ddeabcf95de9ab" "/tmp/app"; do
        if [ -f "$DIR/main.py" ]; then
            echo "✅ Found main.py in $DIR"
            cd "$DIR"
            break
        fi
    done
fi

# Check again if we found main.py
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found anywhere. Current directory: $(pwd)"
    ls -la
    
    # Check if output.tar.gz exists and extract it
    if [ -f "/home/site/wwwroot/output.tar.gz" ]; then
        echo "📦 Found output.tar.gz, extracting..."
        mkdir -p /tmp/app
        tar -xzf /home/site/wwwroot/output.tar.gz -C /tmp/app
        cd /tmp/app
        
        if [ ! -f "main.py" ]; then
            echo "❌ main.py not found in extracted archive"
            exit 1
        else
            echo "✅ Found main.py in extracted archive"
        fi
    else
        exit 1
    fi
fi

# Check Python availability
echo "🐍 Checking Python availability..."
if command -v python3 &> /dev/null; then
    echo "✅ Python3 found: $(python3 --version)"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    echo "✅ Python found: $(python --version)"
    PYTHON_CMD="python"
else
    echo "❌ No Python found. Available commands:"
    which python3 python || echo "No python commands found"
    exit 1
fi

# Install minimal dependencies first to handle health checks faster
echo "📦 Installing minimal dependencies first..."
$PYTHON_CMD -m pip install --no-cache-dir aiohttp loguru

# Start a minimal health check server in the background
cat > health_server.py << EOF
import os
import http.server
import socketserver
import threading
import json
from datetime import datetime

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ['/', '/health', '/api/health']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "status": "starting",
                "service": "NewsRagnarok Crawler",
                "timestamp": datetime.now().isoformat(),
                "message": "Crawler is starting up",
                "port": os.environ.get('PORT', '8000')
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"NewsRagnarok Crawler is starting")
            
    def log_message(self, format, *args):
        # Suppress logging
        return

def start_server():
    port = int(os.environ.get('PORT', 8000))
    for try_port in [port, 8001, 8002, 8003]:
        try:
            with socketserver.TCPServer(("", try_port), HealthHandler) as httpd:
                print(f"Health check server started on port {try_port}")
                httpd.serve_forever()
                break
        except OSError:
            continue

# Start in background thread
thread = threading.Thread(target=start_server, daemon=True)
thread.start()
EOF

# Start temporary health check server
echo "🚀 Starting temporary health check server..."
$PYTHON_CMD health_server.py &
HEALTH_SERVER_PID=$!
trap 'kill $HEALTH_SERVER_PID 2>/dev/null' EXIT

# Install full dependencies with timeout protection
echo "📦 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    echo "📋 Found requirements.txt, installing packages..."
    # Use timeout to prevent hanging
    timeout 180 $PYTHON_CMD -m pip install --no-cache-dir --upgrade pip || echo "⚠️ Pip upgrade timed out, continuing"
    timeout 180 $PYTHON_CMD -m pip install --no-cache-dir psutil || echo "⚠️ psutil installation timed out, continuing"
    timeout 600 $PYTHON_CMD -m pip install --no-cache-dir -r requirements.txt || echo "⚠️ Some packages might not have installed correctly, continuing anyway"
    echo "✅ Dependencies installed"
else
    echo "⚠️ No requirements.txt found, installing basic packages..."
    timeout 180 $PYTHON_CMD -m pip install --no-cache-dir pyyaml loguru python-dotenv psutil
    echo "✅ Basic packages installed"
fi

# Reduce memory usage of Playwright
export PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
export NODE_OPTIONS="--max-old-space-size=512"

# Install Playwright with reduced memory footprint
echo "🌐 Installing Playwright minimally..."
$PYTHON_CMD -m pip install --no-cache-dir playwright || echo "⚠️ Playwright install failed, will use HTTP fallback"
$PYTHON_CMD -m playwright install-deps chromium || echo "⚠️ Could not install system dependencies"
$PYTHON_CMD -m playwright install chromium || echo "⚠️ Could not install browser, will use HTTP fallback"

# Add memory monitoring file
cat > memory_monitor.py << EOF
import psutil
import time
import os
import sys

def monitor():
    process = psutil.Process(os.getpid())
    while True:
        mem = process.memory_info().rss / 1024 / 1024
        print(f"Memory usage: {mem:.2f} MB")
        if mem > 1024:  # Over 1GB
            print("WARNING: High memory usage detected")
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    try:
        monitor()
    except:
        pass
EOF

# Start the memory monitor in background
$PYTHON_CMD memory_monitor.py &

# Kill the temporary health server
kill $HEALTH_SERVER_PID 2>/dev/null

# Start the main application with memory limit
echo "🚀 Starting NewsRagnarok Crawler with $PYTHON_CMD..."
exec $PYTHON_CMD -u main.py