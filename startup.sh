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
$PYTHON_CMD -m pip install --user --upgrade pip

if [ -f "requirements.txt" ]; then
    echo "📋 Installing packages from requirements.txt..."
    $PYTHON_CMD -m pip install --user -r requirements.txt
else
    echo "❌ No requirements.txt found"
    exit 1
fi

# Install Playwright
echo "🌐 Setting up Playwright..."
$PYTHON_CMD -m pip install --user playwright
$PYTHON_CMD -m playwright install --with-deps chromium
echo "✅ Playwright setup complete"

# Create necessary directories
mkdir -p logs
mkdir -p data

# Start the application
echo "🚀 Starting NewsRagnarok Crawler..."
exec $PYTHON_CMD main.py