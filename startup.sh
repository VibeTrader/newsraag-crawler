#!/bin/bash

# Set error handling
set -e

echo "🚀 Starting NewsRagnarok Crawler Setup..."

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Current directory: $(pwd)"
    ls -la
    exit 1
fi

# Install Playwright browsers with error handling
echo "📦 Installing Playwright browsers..."
if playwright install chromium; then
    echo "✅ Playwright browsers installed successfully"
else
    echo "❌ Failed to install Playwright browsers"
    echo "⚠️ Continuing with RSS-only mode..."
fi

# Check Python environment
echo "🐍 Checking Python environment..."
python --version
pip list | grep -E "(crawl4ai|playwright|qdrant)"

# Start the main application
echo "🚀 Starting NewsRagnarok Crawler..."
exec python main.py
