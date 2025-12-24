#!/bin/bash
# Azure App Service Startup Script
# This MUST be set as the startup command in Azure

chmod +x startup.sh
echo "=================================="
echo "NewsRagnarok Crawler - Starting..."
echo "=================================="

# Activate virtual environment
if [ -d "antenv" ]; then
    source antenv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Virtual environment not found"
fi

# Run the Python startup script that fixes typing_extensions
exec python3 azure_startup.py
