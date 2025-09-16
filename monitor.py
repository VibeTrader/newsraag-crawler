#!/usr/bin/env python
"""
Monitoring script to check if the crawler is still running and restart it if needed.
This script can be scheduled to run every few minutes using cron or Windows Task Scheduler.
"""
import os
import sys
import time
from datetime import datetime, timedelta
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crawler_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("crawler_monitor")

# Configuration
HEARTBEAT_FILE = os.path.join(os.path.dirname(__file__), 'data', 'heartbeat', 'crawler_heartbeat.txt')
MAX_HEARTBEAT_AGE_MINUTES = 15  # Maximum age of heartbeat file before restart
CRAWLER_SCRIPT = os.path.join(os.path.dirname(__file__), 'main.py')

def check_heartbeat_file():
    """Check if heartbeat file exists and is recent enough."""
    try:
        if not os.path.exists(HEARTBEAT_FILE):
            logger.warning(f"Heartbeat file not found: {HEARTBEAT_FILE}")
            return False
            
        # Get file modification time
        file_mtime = datetime.fromtimestamp(os.path.getmtime(HEARTBEAT_FILE))
        now = datetime.now()
        age_minutes = (now - file_mtime).total_seconds() / 60
        
        # Check file content (last line)
        with open(HEARTBEAT_FILE, 'r') as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1]
                logger.info(f"Last heartbeat: {last_line.strip()}")
            
        logger.info(f"Heartbeat file age: {age_minutes:.2f} minutes")
        
        if age_minutes > MAX_HEARTBEAT_AGE_MINUTES:
            logger.warning(f"Heartbeat file too old: {age_minutes:.2f} minutes")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error checking heartbeat file: {e}")
        return False

def is_crawler_process_running():
    """Check if the crawler process is running using platform-specific commands."""
    try:
        # Windows
        if sys.platform == 'win32':
            # Look for python process running main.py
            output = subprocess.check_output('tasklist /FI "IMAGENAME eq python.exe" /FO CSV', shell=True).decode()
            return 'python.exe' in output
        # Linux/Mac
        else:
            # Look for python process running main.py
            output = subprocess.check_output(['ps', 'aux'], shell=False).decode()
            return 'main.py' in output
    except Exception as e:
        logger.error(f"Error checking process: {e}")
        return False

def start_crawler():
    """Start the crawler process."""
    try:
        logger.info(f"Starting crawler: {CRAWLER_SCRIPT}")
        
        # Windows
        if sys.platform == 'win32':
            # Start in a new window
            subprocess.Popen(f'start python {CRAWLER_SCRIPT}', shell=True)
        # Linux/Mac
        else:
            # Start as a background process
            subprocess.Popen(['python', CRAWLER_SCRIPT], 
                            stdout=open('crawler_output.log', 'a'),
                            stderr=open('crawler_error.log', 'a'),
                            start_new_session=True)
            
        logger.info("Crawler started successfully")
        return True
    except Exception as e:
        logger.error(f"Error starting crawler: {e}")
        return False

def main():
    """Main function to check and restart crawler if needed."""
    logger.info("Starting crawler monitor check")
    
    # Check if heartbeat file is recent
    heartbeat_ok = check_heartbeat_file()
    
    # Check if process is running
    process_running = is_crawler_process_running()
    
    logger.info(f"Heartbeat check: {'OK' if heartbeat_ok else 'FAILED'}")
    logger.info(f"Process check: {'RUNNING' if process_running else 'NOT RUNNING'}")
    
    # Restart if either check fails
    if not heartbeat_ok or not process_running:
        logger.warning("Crawler appears to be dead, restarting...")
        start_crawler()
    else:
        logger.info("Crawler is running normally")
    
    logger.info("Monitor check completed")

if __name__ == "__main__":
    main()
