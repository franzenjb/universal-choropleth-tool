Start Here

What this does
- Make a choropleth GeoJSON from any CSV that has a geographic key (state, county, place, county‑subdivision, tract, block group, ZIP).
- Use local cached boundaries (no Census calls) from `~/data/tiger/GENZ`.
- Two ways to use it: Web UI (easiest) or CLI (power users).

Quickest path (Web UI)
1) Open the live page: https://franzenjb.github.io/alice-choropleth-tool/
2) Upload your CSV.
3) Pick your state and area type (ZIP, county, etc.).
4) Use a provided boundary or (optionally) upload one.
5) Click “Create My Map” and download the GeoJSON.

Optional: Enable the Local Engine (for auto boundaries and big layers)
1) Terminal:
   - `cd "/Users/jefffranzen/Desktop/alice-choropleth-tool"`
   - `python3 -m venv .venv && source .venv/bin/activate`
   - `pip install fastapi uvicorn[standard] geopandas pyogrio shapely pyproj pandas`
   - `export ALICE_CACHE_DIR=~/data/tiger/GENZ`
   - `python tools/local_api.py`
2) Refresh the web page. It will auto‑detect the local engine. You no longer need to pick/upload boundaries — the page will fetch the correct one and join server‑side.

CLI (offline batch runs)
1) `cd "/Users/jefffranzen/Desktop/alice-choropleth-tool" && python3 -m venv .venv && source .venv/bin/activate`
2) `pip install geopandas pyogrio shapely pyproj fiona requests pandas`
3) `export ALICE_CACHE_DIR=~/data/tiger/GENZ && export ALICE_OFFLINE=1`
4) Example (Florida county‑subdivision):
   ```
   python tools/alice_choropleth.py \
     --level subcounty --state FL \
     --csv "/Users/jefffranzen/Desktop/Alice Florida Data/ALICE - Florida Sub_County Data.csv" \
     --out out/fl_subcounty.geojson --simplify 0.0005
   ```

Troubleshooting
- Pages 404 after push: wait 1–3 minutes and refresh.
- Local Engine not detected: make sure `tools/local_api.py` is running and `ALICE_CACHE_DIR` is set.
- ZIP vs ZCTA mismatches: Some ZIPs don’t map to ZCTAs; expect some nulls.
