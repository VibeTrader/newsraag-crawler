#!/bin/bash
echo "🚀 Azure App Service Startup Script"
echo "📁 Current directory: $(pwd)"
echo "📋 Files in directory:"
ls -la

echo "📦 Installing Playwright browsers..."
playwright install chromium

echo "🐍 Starting Python application..."
python main.py
