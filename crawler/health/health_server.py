"""
Health check HTTP server for NewsRagnarok Crawler with Cleanup API support.
"""
import os
import json
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from loguru import logger
from datetime import datetime

from monitoring.health_check import get_health_check
from monitoring.metrics import get_metrics

# Store last cleanup result
last_cleanup_result = {
    "timestamp": None,
    "status": "never_run",
    "message": "Cleanup has not been executed yet"
}


class HealthHandler(BaseHTTPRequestHandler):
    """Enhanced HTTP handler for health checks, metrics, and cleanup API."""
    
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
        
        # Cleanup status endpoint
        elif self.path == '/api/cleanup/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            self.wfile.write(json.dumps(last_cleanup_result).encode())
        
        # Cleanup health endpoint
        elif self.path == '/api/cleanup/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "status": "healthy",
                "service": "cleanup_api",
                "timestamp": datetime.utcnow().isoformat(),
                "last_cleanup": last_cleanup_result.get("timestamp", "never")
            }
            
            self.wfile.write(json.dumps(response).encode())
            
        # Default response
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"NewsRagnarok Crawler is running")
    
    def do_POST(self):
        """Handle POST requests for cleanup API."""
        global last_cleanup_result
        
        # Only handle cleanup endpoint
        if self.path == '/api/cleanup':
            try:
                # Read request body
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length) if content_length > 0 else b'{}'
                
                # Parse JSON
                try:
                    data = json.loads(body.decode('utf-8'))
                    retention_hours = data.get('retention_hours', 24)
                except:
                    retention_hours = 24
                
                logger.info(f"Received cleanup request (retention: {retention_hours} hours)")
                
                # Import cleanup function
                from cleanup_api import run_cleanup_operation
                
                # Run cleanup in event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(run_cleanup_operation(retention_hours))
                loop.close()
                
                # Store result
                last_cleanup_result = result
                
                # Send response
                if result["status"] == "success":
                    self.send_response(200)
                else:
                    self.send_response(500)
                
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
                
            except Exception as e:
                logger.error(f"Error in cleanup endpoint: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
                error_response = {
                    "status": "error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(error_response).encode())
        else:
            # Unsupported POST endpoint
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error = {"error": "Not Found", "path": self.path}
            self.wfile.write(json.dumps(error).encode())
    
    def log_message(self, format, *args):
        """Override to use loguru instead of print."""
        logger.debug(f"HTTP: {self.address_string()} - {format % args}")


def start_health_server():
    """Start HTTP server for Azure health checks and cleanup API."""
    try:
        # Use Azure App Service PORT environment variable, fallback to 8000
        port = int(os.environ.get('PORT', 8000))
        
        # Try multiple ports if the first one is busy
        ports_to_try = [port, 8001, 8002, 8003, 8004]
        
        logger.info("Starting enhanced health check server with cleanup API...")
        
        for try_port in ports_to_try:
            try:
                server = HTTPServer(('0.0.0.0', try_port), HealthHandler)
                logger.info(f"🚀 Enhanced HTTP server started on port {try_port}")
                logger.info(f"   - Health endpoint: http://localhost:{try_port}/health")
                logger.info(f"   - Metrics endpoint: http://localhost:{try_port}/metrics")
                logger.info(f"   - Cleanup API: http://localhost:{try_port}/api/cleanup")
                logger.info(f"   - Cleanup status: http://localhost:{try_port}/api/cleanup/status")
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
