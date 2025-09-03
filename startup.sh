#!/bin/bash

# Enable debugging and strict error handling
set -ex

echo "🚀 Starting NewsRagnarok Crawler in Azure App Service..."

# Set working directory to ensure we're in the right place
WWWROOT="/home/site/wwwroot"
cd "$WWWROOT"

echo "📂 Current directory: $(pwd)"
echo "📋 Directory contents:"
ls -la

# Environment setup for Azure App Service
export PORT=${PORT:-8000}
export WEBSITE_HOSTNAME=${WEBSITE_HOSTNAME:-localhost}
export PATH="$HOME/.local/bin:$PATH"
export PYTHONUNBUFFERED=1

# Determine Python command
echo "🐍 Checking Python availability..."
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3.9 &> /dev/null; then
    PYTHON_CMD="python3.9"
elif command -v python3.8 &> /dev/null; then
    PYTHON_CMD="python3.8"
else
    PYTHON_CMD="python3"
fi

echo "✅ Using Python: $($PYTHON_CMD --version)"

# Install/upgrade pip
echo "📦 Upgrading pip..."
$PYTHON_CMD -m pip install --upgrade pip

# Install dependencies from requirements.txt
if [ -f "requirements.txt" ]; then
    echo "📋 Installing packages from requirements.txt..."
    $PYTHON_CMD -m pip install -r requirements.txt
else
    echo "❌ requirements.txt not found in $(pwd)"
    echo "Searching for requirements.txt file..."
    find "$WWWROOT" -name "requirements.txt" -type f
    exit 1
fi

# Install and setup Playwright
echo "🌐 Setting up Playwright..."
$PYTHON_CMD -m pip install playwright
$PYTHON_CMD -m playwright install chromium
echo "✅ Playwright setup complete"

# Create necessary directories
mkdir -p logs
mkdir -p data

# Verify that main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ main.py not found in $(pwd)"
    echo "Searching for main.py file..."
    find "$WWWROOT" -name "main.py" -type f
    exit 1
fi

# Start the application
echo "🚀 Starting NewsRagnarok Crawler with main.py..."
exec $PYTHON_CMD -u main.py