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

# Install dependencies if needed
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install system dependencies for Playwright
echo "🔧 Installing system dependencies for Playwright..."
apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnspr4 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxcb1 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libcairo2 \
    libpango-1.0-0 \
    libasound2

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

# Log Azure App Service environment
echo "🌐 Azure App Service Environment:"
echo "   PORT: $PORT"
echo "   WEBSITE_SITE_NAME: $WEBSITE_SITE_NAME"
echo "   WEBSITE_HOSTNAME: $WEBSITE_HOSTNAME"

# Start the main application
echo "🚀 Starting NewsRagnarok Crawler..."
exec python main.py
