#!/bin/bash

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium --with-deps

# Check installation
echo "Checking Playwright browser installation..."
ls -la /root/.cache/ms-playwright/
echo "Browser installation status complete."

# Start your application
echo "Starting application..."
python main.py
