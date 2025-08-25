#!/usr/bin/env python3
"""
Azure App Service Startup Script for NewsRagnarok Crawler
"""

import os
import subprocess
import sys
import time

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"📄 Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stderr:
            print(f"📄 Error: {e.stderr.strip()}")
        return False

def main():
    """Main startup function."""
    print("🚀 Starting NewsRagnarok Crawler Setup...")
    
    # Check if we're in the right directory
    if not os.path.exists("main.py"):
        print("❌ Error: main.py not found. Current directory:", os.getcwd())
        print("📁 Files in current directory:", os.listdir("."))
        sys.exit(1)
    
    # Install Playwright browsers
    playwright_success = run_command(
        "playwright install chromium", 
        "Installing Playwright browsers"
    )
    
    if not playwright_success:
        print("⚠️ Playwright installation failed, continuing with RSS-only mode...")
    
    # Check Python environment
    print("🐍 Checking Python environment...")
    run_command("python --version", "Checking Python version")
    run_command("pip list | grep -E '(crawl4ai|playwright|qdrant)'", "Checking key packages")
    
    # Start the main application
    print("🚀 Starting NewsRagnarok Crawler...")
    print("=" * 50)
    
    # Run the main application
    try:
        subprocess.run([sys.executable, "main.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Main application failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("🛑 Application stopped by user")
        sys.exit(0)

if __name__ == "__main__":
    main()
