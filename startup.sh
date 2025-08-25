#!/bin/bash

# Set error handling
set -e

echo "🚀 Starting NewsRagnarok Crawler (Simplified)..."

# Ensure script is executable
chmod +x "$0"

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Current directory: $(pwd)"
    ls -la
    exit 1
fi

# Install Playwright browsers in background (non-blocking)
echo "📦 Installing Playwright browsers in background..."
playwright install chromium > /dev/null 2>&1 &
PLAYWRIGHT_PID=$!

# Start the main application immediately
echo "🚀 Starting NewsRagnarok Crawler..."
exec python main.py
