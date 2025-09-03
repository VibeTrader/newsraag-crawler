#!/bin/bash

# Set error handling
set -e

echo "🚀 Starting NewsRagnarok Crawler in Azure App Service..."

# Set working directory
cd /home/site/wwwroot || exit 1

# Environment setup for Azure App Service
export PORT=${PORT:-8000}
export WEBSITE_HOSTNAME=${WEBSITE_HOSTNAME:-localhost}
export PATH="$HOME/.local/bin:$PATH"

# Check Python availability
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

# Install dependencies
echo "📦 Installing Python dependencies..."
# Avoid using --user flag for pip upgrade
$PYTHON_CMD -m pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    echo "📋 Installing packages from requirements.txt..."
    $PYTHON_CMD -m pip install -r requirements.txt
else
    echo "❌ No requirements.txt found"
    exit 1
fi

# Install Playwright
echo "🌐 Setting up Playwright..."
$PYTHON_CMD -m pip install playwright
$PYTHON_CMD -m playwright install chromium
# Avoid --with-deps as it might be causing issues in Azure environment
echo "✅ Playwright setup complete"

# Create necessary directories
mkdir -p logs
mkdir -p data

# Make sure app binds to the right port
echo "🔧 Setting PORT environment variable to $PORT"
export PYTHONUNBUFFERED=1

# Start the application
echo "🚀 Starting NewsRagnarok Crawler..."
# Add more verbose output for debugging
$PYTHON_CMD -u main.py