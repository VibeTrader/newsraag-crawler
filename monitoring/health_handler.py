"""
Enhanced health check handler with monitoring metrics.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime
import os
from loguru import logger

class EnhancedHealthHandler(BaseHTTPRequestHandler):
    """Enhanced HTTP handler for health checks with monitoring metrics."""
    
    def __init__(self, *args, **kwargs):
        """Initialize the health handler."""
        # Store reference to health check and metrics
        from monitoring.health_check import get_health_check
        self.health_check = get_health_check()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests for health checks and metrics."""
        # Basic health endpoint
        if self.path in ['/', '/health', '/api/health']:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Get comprehensive health status
            health_status = self.health_check.get_health_status()
            
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
            from monitoring.metrics import get_metrics
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
