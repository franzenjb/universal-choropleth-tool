#!/bin/bash
cd "$(dirname "$0")"

echo "🗺️  Starting Instant Choropleth Map Maker..."
echo ""
echo "This tool lets you:"
echo "• Upload any CSV with geographic data"
echo "• See your map INSTANTLY - no waiting"  
echo "• Export to ArcGIS Online automatically"
echo ""

# Start the local API server
export ALICE_CACHE_DIR=~/data/tiger/GENZ
export ALICE_OFFLINE=1

# Kill any existing server
pkill -f "python.*local_api.py" 2>/dev/null

# Start server in background
echo "Starting local engine..."
python3 tools/local_api.py > /dev/null 2>&1 &
SERVER_PID=$!

# Wait for server to be ready
sleep 2

# Open the instant map interface
open http://127.0.0.1:8765/app/instant.html

echo ""
echo "✅ Map maker is ready!"
echo ""
echo "The browser window will open automatically."
echo "Just drag and drop your CSV file to get started!"
echo ""
echo "Press Ctrl+C to stop the server when done."

# Keep running
wait $SERVER_PID