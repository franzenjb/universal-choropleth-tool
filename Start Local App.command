#!/bin/zsh
set -e
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null 2>&1 || true
python -m pip install -q fastapi "uvicorn[standard]" python-multipart geopandas pyogrio shapely pyproj pandas || exit 1
export ALICE_CACHE_DIR="$HOME/data/tiger/GENZ"
export ALICE_CORS_ALLOW_ALL=1
nohup python -m uvicorn tools.local_api:app --host 127.0.0.1 --port 8765 > /tmp/local_app.log 2>&1 &
sleep 1
open "http://127.0.0.1:8765/app/quick.html"
echo "Opened http://127.0.0.1:8765/app/quick.html"
