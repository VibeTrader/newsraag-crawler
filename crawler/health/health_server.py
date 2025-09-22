"""
Health check HTTP server for NewsRagnarok Crawler.
"""
import os
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from loguru import logger

from monitoring.health_check import get_health_check
from monitoring.metrics import get_metrics

class HealthHandler(BaseHTTPRequestHandler):
    """Enhanced HTTP handler for health checks with monitoring metrics."""
    
    def do_GET(self):
        """Handle GET requests for health checks and metrics."""
        # Get health check instance
        health_check = get_health_check()
        
        # Basic health endpoint
        if self.path in ['/', '/health', '/api/health']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Get comprehensive health status
            health_status = health_check.get_health_status()
            
            # Add basic service info
            health_status.update({
                "service": "NewsRagnarok Crawler",
                "port": os.environ.get('PORT', '8000')
            })
            
            self.wfile.write(json.dumps(health_status).encode())
            
        # Detailed metrics endpoint
        elif self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Get metrics
            metrics = get_metrics()
            all_metrics = metrics.get_current_metrics()
            
            self.wfile.write(json.dumps(all_metrics).encode())
            
        # Default response
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"NewsRagnarok Crawler is running")
    
    def log_message(self, format, *args):
        """Override to use loguru instead of print."""
        logger.debug(f"HEALTH SERVER: {self.address_string()} - {format % args}")

def start_health_server():
    """Start HTTP server for Azure health checks."""
    try:
        # Use Azure App Service PORT environment variable, fallback to 8000
        port = int(os.environ.get('PORT', 8000))
        
        # Try multiple ports if the first one is busy
        ports_to_try = [port, 8001, 8002, 8003, 8004]
        
        logger.info("Starting enhanced health check server with monitoring metrics...")
        
        for try_port in ports_to_try:
            try:
                server = HTTPServer(('0.0.0.0', try_port), HealthHandler)
                logger.info(f"🚀 Enhanced health check server started on port {try_port}")
                logger.info(f"   - Health endpoint: http://localhost:{try_port}/health")
                logger.info(f"   - Metrics endpoint: http://localhost:{try_port}/metrics")
                server.serve_forever()
                break  # If we get here, server started successfully
            except OSError as e:
                if "Address already in use" in str(e):
                    logger.warning(f"Port {try_port} is busy, trying next port...")
                    continue
                else:
                    raise e
        else:
            logger.error(f"Failed to start health server on any port: {ports_to_try}")
            
    except Exception as e:
        logger.error(f"Failed to start health server: {e}")

