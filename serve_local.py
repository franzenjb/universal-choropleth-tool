#!/usr/bin/env python3
"""
Simple HTTP server to run the choropleth tool locally without CORS issues.
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

# Change to docs directory
os.chdir(Path(__file__).parent / 'docs')

PORT = 8000
Handler = http.server.SimpleHTTPRequestHandler

print(f"Starting local server on http://localhost:{PORT}")
print("Opening browser...")

# Open browser automatically
webbrowser.open(f'http://localhost:{PORT}')

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"\n✅ Server running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop the server\n")
    httpd.serve_forever()