#!/bin/zsh
set -e
echo "Stopping Local Engine on :8765 (if running)..."
pkill -f "uvicorn.*8765" || pkill -f "tools/local_api.py" || true
echo "Done."

