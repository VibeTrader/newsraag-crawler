"""
API endpoints for monitoring the NewsRagnarok crawler.
Provides metrics, health checks, and data lifecycle management interfaces.
"""

import os
import json
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Callable, Awaitable
from urllib.parse import urlparse, parse_qs
from loguru import logger
import threading
import traceback

from monitoring.metrics import get_metrics
from monitoring.lifecycle import create_lifecycle_manager

class MonitoringHandler(BaseHTTPRequestHandler):
    """HTTP handler for monitoring endpoints."""
    
    def __init__(self, *args, **kwargs):
        self.routes = {
            '/': self.handle_root,
            '/health': self.handle_health,
            '/api/health': self.handle_health,
            '/api/metrics': self.handle_metrics,
            '/api/metrics/report': self.handle_metrics_report,
            '/api/lifecycle/cleanup': self.handle_cleanup,
            '/api/lifecycle/verify': self.handle_verify,
            '/dashboard': self.handle_dashboard
        }
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        try:
            # Parse URL and query parameters
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            # Route to the appropriate handler
            if path in self.routes:
                self.routes[path]()
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'error',
                    'message': f'Endpoint not found: {path}'
                }).encode())
                
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'error',
                'message': f'Internal server error: {str(e)}',
                'traceback': traceback.format_exc()
            }).encode())
    
    def handle_root(self):
        """Handle root endpoint."""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"NewsRagnarok Crawler Monitoring API")
    
    def handle_health(self):
        """Handle health check endpoint."""
        from datetime import datetime
        metrics = get_metrics()
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            'status': 'healthy',
            'service': 'NewsRagnarok Crawler',
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': metrics.get_current_metrics()['uptime_seconds'],
            'total_cycles': metrics.get_current_metrics()['total_cycles'],
            'articles_processed': metrics.get_current_metrics()['articles']['processed'],
            'port': os.environ.get('PORT', '8000')
        }
        
        self.wfile.write(json.dumps(response).encode())
    
    def handle_metrics(self):
        """Handle metrics endpoint."""
        metrics = get_metrics()
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        self.wfile.write(json.dumps(metrics.get_current_metrics()).encode())
    
    def handle_metrics_report(self):
        """Handle metrics report endpoint."""
        metrics = get_metrics()
        
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        
        self.wfile.write(metrics.get_metrics_report().encode())
    
    def handle_cleanup(self):
        """Handle cleanup endpoint - triggers data cleanup asynchronously."""
        # Create lifecycle manager
        lifecycle_manager = create_lifecycle_manager()
        
        # This will run asynchronously, so we need to return immediately
        self.send_response(202)  # Accepted
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            'status': 'accepted',
            'message': 'Cleanup operation started in the background'
        }
        
        self.wfile.write(json.dumps(response).encode())
        
        # Schedule the cleanup task
        def run_cleanup():
            asyncio.run(lifecycle_manager.cleanup_old_data())
        
        threading.Thread(target=run_cleanup).start()
    
    def handle_verify(self):
        """Handle verification endpoint - checks data integrity."""
        # Create lifecycle manager
        lifecycle_manager = create_lifecycle_manager()
        
        # This will run asynchronously, so we need to return immediately
        self.send_response(202)  # Accepted
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        response = {
            'status': 'accepted',
            'message': 'Verification operation started in the background'
        }
        
        self.wfile.write(json.dumps(response).encode())
        
        # Schedule the verification task
        def run_verify():
            asyncio.run(lifecycle_manager.verify_data_integrity())
        
        threading.Thread(target=run_verify).start()
    
    def handle_dashboard(self):
        """Handle dashboard endpoint - serves the monitoring dashboard."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>NewsRagnarok Crawler - Monitoring Dashboard</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                    color: #333;
                }
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }
                header {
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    margin-bottom: 20px;
                }
                h1 {
                    margin: 0;
                }
                .dashboard-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }
                .card {
                    background-color: #fff;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    padding: 20px;
                }
                .card h2 {
                    margin-top: 0;
                    color: #2c3e50;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 10px;
                }
                .metric {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 10px;
                }
                .metric-name {
                    font-weight: 600;
                }
                .metric-value {
                    font-weight: 400;
                }
                .big-number {
                    font-size: 32px;
                    font-weight: 700;
                    text-align: center;
                    margin: 20px 0;
                    color: #3498db;
                }
                .actions {
                    margin-top: 20px;
                    text-align: center;
                }
                button {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                    margin: 0 10px;
                }
                button:hover {
                    background-color: #2980b9;
                }
                .status-indicator {
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    margin-right: 8px;
                }
                .status-healthy {
                    background-color: #2ecc71;
                }
                .status-warning {
                    background-color: #f39c12;
                }
                .status-error {
                    background-color: #e74c3c;
                }
                .refresh-timer {
                    text-align: center;
                    margin-bottom: 20px;
                    color: #7f8c8d;
                }
                .chart-container {
                    width: 100%;
                    height: 300px;
                }
                .bar {
                    fill: #3498db;
                }
                pre {
                    background-color: #f8f9fa;
                    padding: 15px;
                    border-radius: 4px;
                    overflow-x: auto;
                    white-space: pre-wrap;
                }
            </style>
        </head>
        <body>
            <header>
                <h1>NewsRagnarok Crawler - Monitoring Dashboard</h1>
            </header>
            
            <div class="container">
                <div class="refresh-timer">
                    Auto-refreshing in <span id="countdown">30</span> seconds
                    <button id="refresh-now">Refresh Now</button>
                </div>
                
                <div class="dashboard-grid">
                    <div class="card">
                        <h2>System Status</h2>
                        <div class="metric">
                            <span class="metric-name">Status:</span>
                            <span class="metric-value">
                                <span class="status-indicator status-healthy"></span>
                                <span id="system-status">Healthy</span>
                            </span>
                        </div>
                        <div class="metric">
                            <span class="metric-name">Uptime:</span>
                            <span class="metric-value" id="uptime">Loading...</span>
                        </div>
                        <div class="metric">
                            <span class="metric-name">Memory Usage:</span>
                            <span class="metric-value" id="memory-usage">Loading...</span>
                        </div>
                        <div class="metric">
                            <span class="metric-name">Last Updated:</span>
                            <span class="metric-value" id="last-updated">Loading...</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Crawler Performance</h2>
                        <div class="metric">
                            <span class="metric-name">Total Cycles:</span>
                            <span class="metric-value" id="total-cycles">Loading...</span>
                        </div>
                        <div class="metric">
                            <span class="metric-name">Articles Processed:</span>
                            <span class="metric-value" id="articles-processed">Loading...</span>
                        </div>
                        <div class="metric">
                            <span class="metric-name">Success Rate:</span>
                            <span class="metric-value" id="success-rate">Loading...</span>
                        </div>
                        <div class="metric">
                            <span class="metric-name">Avg. Extraction Time:</span>
                            <span class="metric-value" id="avg-extraction-time">Loading...</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Storage</h2>
                        <div class="metric">
                            <span class="metric-name">Qdrant Documents:</span>
                            <span class="metric-value" id="qdrant-documents">Loading...</span>
                        </div>
                        <div class="metric">
                            <span class="metric-name">Azure Blobs:</span>
                            <span class="metric-value" id="azure-blobs">Loading...</span>
                        </div>
                        <div class="metric">
                            <span class="metric-name">Deleted Documents:</span>
                            <span class="metric-value" id="deleted-documents">Loading...</span>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>Source Breakdown</h2>
                    <div id="source-chart" class="chart-container">
                        <svg width="100%" height="100%" id="source-svg"></svg>
                    </div>
                </div>
                
                <div class="card">
                    <h2>Error Monitoring</h2>
                    <div class="metric">
                        <span class="metric-name">Total Errors:</span>
                        <span class="metric-value" id="total-errors">Loading...</span>
                    </div>
                    <div id="errors-by-type"></div>
                </div>
                
                <div class="card">
                    <h2>Full Metrics Report</h2>
                    <pre id="metrics-report">Loading...</pre>
                </div>
                
                <div class="actions">
                    <button id="trigger-cleanup">Trigger Cleanup</button>
                    <button id="verify-integrity">Verify Data Integrity</button>
                </div>
            </div>
            
            <script>
                // Function to format time duration
                function formatDuration(seconds) {
                    const days = Math.floor(seconds / 86400);
                    const hours = Math.floor((seconds % 86400) / 3600);
                    const minutes = Math.floor((seconds % 3600) / 60);
                    const secs = Math.floor(seconds % 60);
                    
                    let result = '';
                    if (days > 0) result += days + 'd ';
                    if (hours > 0 || days > 0) result += hours + 'h ';
                    if (minutes > 0 || hours > 0 || days > 0) result += minutes + 'm ';
                    result += secs + 's';
                    
                    return result;
                }
                
                // Function to update dashboard with metrics
                async function updateDashboard() {
                    try {
                        // Fetch metrics data
                        const metricsResponse = await fetch('/api/metrics');
                        const metrics = await metricsResponse.json();
                        
                        // Fetch metrics report
                        const reportResponse = await fetch('/api/metrics/report');
                        const report = await reportResponse.text();
                        
                        // Update system status
                        document.getElementById('uptime').textContent = formatDuration(metrics.uptime_seconds);
                        document.getElementById('last-updated').textContent = new Date(metrics.timestamp).toLocaleString();
                        
                        if (metrics.memory.current) {
                            document.getElementById('memory-usage').textContent = 
                                `${metrics.memory.current.rss_mb.toFixed(2)} MB (RSS)`;
                        } else {
                            document.getElementById('memory-usage').textContent = 'Not available';
                        }
                        
                        // Update crawler performance
                        document.getElementById('total-cycles').textContent = metrics.total_cycles;
                        document.getElementById('articles-processed').textContent = metrics.articles.processed;
                        document.getElementById('success-rate').textContent = 
                            `${metrics.articles.success_rate.toFixed(2)}%`;
                        document.getElementById('avg-extraction-time').textContent = 
                            `${metrics.extraction_time.average.toFixed(2)}s`;
                        
                        // Update storage metrics
                        document.getElementById('qdrant-documents').textContent = metrics.storage.qdrant_documents;
                        document.getElementById('azure-blobs').textContent = metrics.storage.azure_blobs;
                        document.getElementById('deleted-documents').textContent = metrics.storage.deleted_documents;
                        
                        // Update error monitoring
                        document.getElementById('total-errors').textContent = metrics.errors.total;
                        
                        const errorsByTypeDiv = document.getElementById('errors-by-type');
                        errorsByTypeDiv.innerHTML = '';
                        
                        for (const [type, count] of Object.entries(metrics.errors.by_type)) {
                            const errorDiv = document.createElement('div');
                            errorDiv.className = 'metric';
                            errorDiv.innerHTML = `
                                <span class="metric-name">${type}:</span>
                                <span class="metric-value">${count}</span>
                            `;
                            errorsByTypeDiv.appendChild(errorDiv);
                        }
                        
                        // Update source chart
                        updateSourceChart(metrics.articles.by_source);
                        
                        // Update metrics report
                        document.getElementById('metrics-report').textContent = report;
                        
                    } catch (error) {
                        console.error('Error updating dashboard:', error);
                        // Update system status to error
                        const statusIndicator = document.querySelector('.status-indicator');
                        statusIndicator.className = 'status-indicator status-error';
                        document.getElementById('system-status').textContent = 'Error';
                    }
                }
                
                // Function to update source chart
                function updateSourceChart(sourceData) {
                    const svg = document.getElementById('source-svg');
                    svg.innerHTML = '';
                    
                    const sources = Object.keys(sourceData);
                    const values = Object.values(sourceData);
                    
                    if (sources.length === 0) {
                        svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle">No source data available</text>';
                        return;
                    }
                    
                    const width = svg.clientWidth;
                    const height = svg.clientHeight;
                    const margin = { top: 20, right: 20, bottom: 40, left: 60 };
                    const chartWidth = width - margin.left - margin.right;
                    const chartHeight = height - margin.top - margin.bottom;
                    
                    // Create chart group
                    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                    g.setAttribute('transform', `translate(${margin.left},${margin.top})`);
                    svg.appendChild(g);
                    
                    // Calculate max value for scaling
                    const maxValue = Math.max(...values);
                    
                    // Create scales
                    const barWidth = chartWidth / sources.length;
                    
                    // Create bars
                    sources.forEach((source, i) => {
                        const value = sourceData[source];
                        const barHeight = (value / maxValue) * chartHeight;
                        const x = i * barWidth;
                        const y = chartHeight - barHeight;
                        
                        // Create bar
                        const bar = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                        bar.setAttribute('class', 'bar');
                        bar.setAttribute('x', x);
                        bar.setAttribute('y', y);
                        bar.setAttribute('width', barWidth - 5);
                        bar.setAttribute('height', barHeight);
                        g.appendChild(bar);
                        
                        // Create label
                        const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                        label.setAttribute('x', x + barWidth / 2);
                        label.setAttribute('y', height - margin.bottom / 2);
                        label.setAttribute('text-anchor', 'middle');
                        label.textContent = source;
                        svg.appendChild(label);
                        
                        // Create value label
                        const valueLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                        valueLabel.setAttribute('x', x + barWidth / 2);
                        valueLabel.setAttribute('y', y - 5);
                        valueLabel.setAttribute('text-anchor', 'middle');
                        valueLabel.textContent = value;
                        g.appendChild(valueLabel);
                    });
                    
                    // Create y-axis
                    const yAxis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    yAxis.setAttribute('x1', 0);
                    yAxis.setAttribute('y1', 0);
                    yAxis.setAttribute('x2', 0);
                    yAxis.setAttribute('y2', chartHeight);
                    yAxis.setAttribute('stroke', '#333');
                    g.appendChild(yAxis);
                    
                    // Create x-axis
                    const xAxis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    xAxis.setAttribute('x1', 0);
                    xAxis.setAttribute('y1', chartHeight);
                    xAxis.setAttribute('x2', chartWidth);
                    xAxis.setAttribute('y2', chartHeight);
                    xAxis.setAttribute('stroke', '#333');
                    g.appendChild(xAxis);
                }
                
                // Auto-refresh countdown
                let countdown = 30;
                
                function updateCountdown() {
                    document.getElementById('countdown').textContent = countdown;
                    countdown--;
                    
                    if (countdown < 0) {
                        countdown = 30;
                        updateDashboard();
                    }
                    
                    setTimeout(updateCountdown, 1000);
                }
                
                // Event listeners
                document.getElementById('refresh-now').addEventListener('click', () => {
                    updateDashboard();
                    countdown = 30;
                });
                
                document.getElementById('trigger-cleanup').addEventListener('click', async () => {
                    try {
                        const response = await fetch('/api/lifecycle/cleanup');
                        alert('Cleanup operation triggered successfully!');
                    } catch (error) {
                        console.error('Error triggering cleanup:', error);
                        alert('Error triggering cleanup. Check console for details.');
                    }
                });
                
                document.getElementById('verify-integrity').addEventListener('click', async () => {
                    try {
                        const response = await fetch('/api/lifecycle/verify');
                        alert('Verification operation triggered successfully!');
                    } catch (error) {
                        console.error('Error triggering verification:', error);
                        alert('Error triggering verification. Check console for details.');
                    }
                });
                
                // Initial update
                updateDashboard();
                updateCountdown();
            </script>
        </body>
        </html>
        """
        
        self.wfile.write(html.encode())

def start_monitoring_server(port: int = 8080):
    """Start the monitoring HTTP server.
    
    Args:
        port: Port to listen on (default: 8080)
    """
    try:
        # Try multiple ports if the first one is busy
        ports_to_try = [port, 8081, 8082, 8083, 8084]
        
        for try_port in ports_to_try:
            try:
                server = HTTPServer(('0.0.0.0', try_port), MonitoringHandler)
                logger.info(f"🚀 Monitoring server started on port {try_port}")
                logger.info(f"📊 Dashboard available at http://localhost:{try_port}/dashboard")
                server.serve_forever()
                break  # If we get here, server started successfully
            except OSError as e:
                if "Address already in use" in str(e):
                    logger.warning(f"Port {try_port} is busy, trying next port...")
                    continue
                else:
                    raise e
        else:
            logger.error(f"Failed to start monitoring server on any port: {ports_to_try}")
            
    except Exception as e:
        logger.error(f"Failed to start monitoring server: {e}")
