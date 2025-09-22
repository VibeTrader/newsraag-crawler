"""
Health server for NewsRagnarok Crawler.
"""
import os
import threading
from http.server import HTTPServer
from loguru import logger

from monitoring.health_handler import EnhancedHealthHandler

def start_health_server():
    """
    Start the health check HTTP server.
    """
    try:
        # Get port from environment variable or use default
        port = int(os.environ.get('PORT', '8000'))
        
        # Create HTTP server
        server = HTTPServer(('0.0.0.0', port), EnhancedHealthHandler)
        logger.info(f"Starting health check server on port {port}")
        
        # Start server in a non-blocking way
        server.serve_forever()
    except Exception as e:
        logger.error(f"Error starting health check server: {e}")
