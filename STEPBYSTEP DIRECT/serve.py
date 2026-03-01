#!/usr/bin/env python3
"""
Simple HTTP server for StepByStep Direct website
Run this to view the React frontend in your browser
"""

import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

def main():
    # Change to project root directory
    os.chdir(Path(__file__).parent)
    
    Handler = MyHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        url = f"http://localhost:{PORT}/index.html"
        print(f"\n{'='*60}")
        print(f"StepByStep Direct - Local Web Server")
        print(f"{'='*60}\n")
        print(f"Server running at: {url}")
        print(f"\nOpening browser...")
        print(f"\nPress Ctrl+C to stop the server\n")
        print(f"{'='*60}\n")
        
        # Open browser
        webbrowser.open(url)
        
        # Serve forever
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print(f"\n\n{'='*60}")
            print(f"Server stopped")
            print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
