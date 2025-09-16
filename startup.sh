#!/bin/bash

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium --with-deps

# Check installation
echo "Checking Playwright browser installation..."
ls -la /root/.cache/ms-playwright/
echo "Browser installation status complete."

# Create monitor script to restart crawler if it dies
echo "Setting up crawler monitor..."
cat > monitor_crawler.sh << 'EOF'
#!/bin/bash
while true; do
  # Check if main.py is running
  if ! pgrep -f "python main.py" > /dev/null; then
    echo "$(date) - Crawler not running, restarting..."
    nohup python main.py > crawler.log 2>&1 &
    sleep 10
  else
    echo "$(date) - Crawler running OK"
  fi
  sleep 300  # Check every 5 minutes
done
EOF

# Make monitor script executable
chmod +x monitor_crawler.sh

# Start monitor in background
echo "Starting crawler monitor..."
nohup ./monitor_crawler.sh > monitor.log 2>&1 &

# Start your application
echo "Starting main application..."
python main.py
