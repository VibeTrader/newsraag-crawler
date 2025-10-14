#!/bin/bash
set -e
chmod +x startup.sh

echo "=== NewsRagnarok Azure Optimized Startup ==="
echo "🌐 Azure App Service Deployment"
echo "⏰ Start time: $(date)"
echo "📊 PORT: ${PORT:-8000}"
echo "🔧 Environment: ${ENVIRONMENT:-development}"

# Set critical environment variables
export PYTHONUNBUFFERED=1
export PYTHONPATH="/home/site/wwwroot:${PYTHONPATH}"
export AZURE_ENV=true

# Create essential directories
echo "📁 Creating directories..."
mkdir -p /home/site/wwwroot/data/{metrics,heartbeat,logs}
mkdir -p /home/site/wwwroot/logs

# CRITICAL: Fix typing_extensions compatibility BEFORE starting app
echo "🔧 Applying typing_extensions compatibility fixes..."
python3 -c "
import sys
import subprocess
import os

# Remove Azure's conflicting paths
paths_removed = []
for path in sys.path.copy():
    if '/agents/python' in path:
        sys.path.remove(path) if path in sys.path else None
        paths_removed.append(path)

print(f'✅ Removed {len(paths_removed)} conflicting system paths')

# Upgrade typing_extensions
try:
    result = subprocess.run([
        sys.executable, '-m', 'pip', 'install', 
        '--upgrade', '--force-reinstall', '--no-cache-dir',
        'typing_extensions>=4.8.0'
    ], capture_output=True, text=True, timeout=60)
    
    if result.returncode == 0:
        print('✅ typing_extensions upgraded successfully')
    else:
        print(f'⚠️ typing_extensions upgrade warning: {result.stderr}')
        
except Exception as e:
    print(f'⚠️ typing_extensions upgrade failed: {e}')

# Test critical imports
try:
    from typing_extensions import Sentinel
    print('✅ typing_extensions.Sentinel - OK')
    import pydantic
    print('✅ pydantic - OK')
    print('🚀 Critical imports successful - ready for crawl4ai')
except Exception as e:
    print(f'❌ Import test failed: {e}')
    print('⚠️ Will attempt fallback fixes during startup')
"

# Install Playwright in background (non-blocking)
echo "📦 Installing Playwright browsers (background)..."
(
    timeout 180 python3 -m playwright install chromium --with-deps 2>/dev/null || {
        echo "⚠️ Playwright installation timed out - using BeautifulSoup fallback"
    }
) &

PLAYWRIGHT_PID=$!

# Start the main application using Azure startup script
echo "🚀 Starting NewsRagnarok Crawler via Azure startup script..."
python3 azure_startup.py &

MAIN_PID=$!

echo "✅ Application startup initiated"
echo "📊 Process Status:"
echo "   - Main application PID: $MAIN_PID"
echo "   - Playwright install PID: $PLAYWRIGHT_PID"
echo "   - Health server: Starting with main app"
echo ""
echo "🌐 Expected endpoints:"
echo "   - Health check: http://localhost:${PORT:-8000}/"
echo "   - Logs: /home/site/wwwroot/logs/"
echo ""

# Wait for main application
echo "🛡️ Monitoring main application..."
wait $MAIN_PID

APP_EXIT_CODE=$?
echo "📊 Main application exited with code: $APP_EXIT_CODE"

# Clean up background processes
kill $PLAYWRIGHT_PID 2>/dev/null || true

exit $APP_EXIT_CODE