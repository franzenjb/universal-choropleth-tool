# Universal Choropleth Tool

CLI + browser UI to join any CSV with Census TIGER/Cartographic boundaries and export GeoJSON for ArcGIS (no credits).

## Features
- Place, Sub-County (county subdivisions), and ZCTA joins
- Auto-computed rates from CSV data columns
- Local cache + offline mode (no runtime calls to Census once cached)
- Resilient downloader with retries/backoff
- GeoParquet conversion for fast local I/O
- Browser UI in `docs/` (GitHub Pages-ready) for non-technical users

## Quickstart (CLI)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install geopandas pyogrio shapely pyproj fiona requests pandas
export CHOROPLETH_CACHE_DIR=~/data/tiger/GENZ
export CHOROPLETH_OFFLINE=1

# Example (Florida Sub-County):
python tools/choropleth.py \
  --level subcounty --state FL \
  --csv "/Users/you/Desktop/Data/Florida_Sub_County_Data.csv" \
  --out out/fl_subcounty.geojson --simplify 0.0005 \
  --cache-dir "$CHOROPLETH_CACHE_DIR" --offline
```

## Prefetch Super-Base
```bash
python tools/prefetch_tiger.py --cache-dir "$CHOROPLETH_CACHE_DIR" --until-complete --max-retries 12 --retry-wait 3
```
- Downloads: US places, ZCTA (2020), US states/counties, all per-state county subdivisions + tracts
- Add block groups for selected states: `--bg-states FL,GA,SC,NC,TN,AL,MS`
- Use `--insecure` if your machine has TLS chain issues

## Convert to GeoParquet
```bash
pip install pyarrow
python tools/convert_cache_to_parquet.py --cache-dir "$CHOROPLETH_CACHE_DIR"
```
- Optional `--glob` to limit, e.g., `"*_bg_500k.zip"`

## Browser UI (GitHub Pages)
- Files live in `docs/` so Pages can serve from the `main` branch.
- Quick Map (one screen): https://franzenjb.github.io/alice-choropleth-tool/quick.html
- Wizard: https://franzenjb.github.io/alice-choropleth-tool/
- To run locally: open `docs/index.html` or serve with `python -m http.server -d docs 8080`

## Notes
- ZCTA uses 2020 500k cartographic boundary (most stable/available).
- Some territories lack certain geographies (UM county subdivisions not published).
- `--simplify` helps shrink GeoJSON for upload/performance.
