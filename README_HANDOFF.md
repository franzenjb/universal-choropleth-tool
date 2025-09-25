# ALICE Choropleth Tool — Status, Usage, and Handoff

This repo builds ArcGIS‑ready map layers by joining a user CSV (ZIP/County/Place/Sub‑County/etc.) with Census TIGER/Cartographic boundaries, then exporting GeoJSON (and optionally Shapefile).

## Bottom line for Florida (now)
- Public page (zero setup): https://franzenjb.github.io/alice-choropleth-tool/quick.html
  - Works for Florida: County, Sub‑County, Place (preview + download OK)
  - For ZIP: Preview is disabled; download is valid for ArcGIS. If in doubt, use the Local App below.
- One‑click Local App (all areas, no Terminal):
  - Double‑click `Start Local App.command` in the repo root
  - Browser opens: http://127.0.0.1:8765/app/quick.html
  - Drop CSV → pick State + Area → Create → Download → upload to ArcGIS

## What’s already done
- Local “super‑base” cached at `~/data/tiger/GENZ` (US coverage):
  - National: States (2023), Counties (2023), Places (2023), ZCTAs (2020)
  - Per‑state: County Subdivisions (all), Tracts (all)
  - Block Groups: FL, GA, SC, NC, TN, AL, MS
- Server + CLI can export valid GeoJSON (ArcGIS‑ready). Public page works for most FL layers.

## Known limitation to fix next
- Public ZIP (browser‑only) preview/join is flaky. Download from the public page is often OK, but to guarantee success use the Local App (server‑side join). ZIP preview is intentionally disabled on the public page to avoid confusion.

## Repository map
- `docs/` — public UI (served by GitHub Pages)
  - `quick.html`, `quick.js`, `styles.css` — single‑screen “Quick Map” UI
  - `data/` — hosted FL boundaries for browser‑only flow (state/county/sub‑county/place/zcta)
- `tools/` — code
  - `alice_choropleth.py` — CLI: CSV + TIGER → GeoJSON
  - `local_api.py` — FastAPI server; serves UI at `/app/quick.html`; `POST /join` does the join
  - `prefetch_tiger.py` — downloads TIGER (retry/backoff) into `~/data/tiger/GENZ`
  - `convert_cache_to_parquet.py` — optional Parquet conversion (requires `pyarrow`)
  - `record_quick_map_demo.py` — Playwright recorder for short demos
- Launchers (no Terminal):
  - `Start Local App.command` — starts server and opens local UI
  - `Stop Local Engine.command` — stops server
- Docs:
  - `START_HERE.md` — minimal steps
  - `VOLUNTEER_TEST.md` — 30‑minute volunteer usability test

## How to use — public page (Florida)
1) Open https://franzenjb.github.io/alice-choropleth-tool/quick.html
2) Drop CSV → pick State + Area → Create → Download GeoJSON → upload to ArcGIS
3) Notes:
   - ZIP: preview is off; download is valid for ArcGIS.
   - County/Sub‑County/Place: preview + download OK.

## How to use — Local App (all areas; one click)
1) Double‑click `Start Local App.command`
2) Browser opens at http://127.0.0.1:8765/app/quick.html
3) Drop CSV → pick State + Area → Create → Download → upload to ArcGIS
4) ZIP preview is intentionally disabled; download is valid.

## Join rules
- Place: join `GEOID` (7 digits)
- Sub‑County (County Subdivision): `GEOID` (10 digits)
- County: `GEOID` (5 digits)
- State: `STATEFP` or `STUSPS` or 2‑digit FIPS
- Tract: `GEOID` (11 digits)
- Block Group: `GEOID` (12 digits)
- ZIP: 5‑digit (`ZIP`/`ZCTA`/`ZCTA5`) → boundary uses ZCTAs (not USPS ZIPs)
- If ALICE fields exist, server/CLI adds: Below_ALICE_Rate, ALICE_Rate, Poverty_Rate

## Super‑base contents (cached)
- National: `cb_2023_us_state_500k.zip`, `cb_2023_us_county_500k.zip`, `cb_2023_us_place_500k.zip`
- ZCTAs: `cb_2020_us_zcta520_500k.zip`
- Per‑state: `cb_2023_{STATEFIPS}_cousub_500k.zip`, `cb_2023_{STATEFIPS}_tract_500k.zip`
- Block groups (subset states): `cb_2023_{STATEFIPS}_bg_500k.zip`
- Optional Parquet copies in `~/data/tiger/GENZ/parquet` (if `pyarrow` installed)

## CLI quickstart (power users)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install geopandas pyogrio shapely pyproj fiona requests pandas
export ALICE_CACHE_DIR=~/data/tiger/GENZ
export ALICE_OFFLINE=1

# Example (Florida Sub-County)
python tools/alice_choropleth.py \
  --level subcounty --state FL \
  --csv "/Users/you/Desktop/Alice Florida Data/ALICE - Florida Sub_County Data.csv" \
  --out out/fl_subcounty.geojson --simplify 0.0005 \
  --cache-dir "$ALICE_CACHE_DIR" --offline
```

## Troubleshooting
- Public ZIP uploads fail: use Local App (server‑side join) to generate ZIP GeoJSON/Shapefile; preview off by design.
- Local App health: http://127.0.0.1:8765/health; logs at `/tmp/local_app.log`
- CORS errors: use local UI at `/app/quick.html` (no CORS).
- If ArcGIS dislikes GeoJSON: export Shapefile.zip (server path to be added by default).

## Immediate next steps (recommended)
1) Server‑side “repair + validate” pipeline for ZIP joins (FL first): re‑project, safe simplify, make_valid; re‑open and validate; output both GeoJSON and Shapefile.zip; show green “Good to upload” + match count.
2) Re‑enable ZIP on public page only after the server pipeline is in use (or after hosting prebuilt validated state files).
3) Add Georgia to public page (same pattern), then expand state‑by‑state.

## Status for the next maintainer (LM)
- Data layer is complete and cached; Local App/CLI can produce valid outputs today.
- Public page is stable for FL County/Sub‑County/Place; ZIP preview is intentionally disabled until repairs/validation are in place.
- Keep the UI to one screen with one button. Preview is optional; never block download on it. Add “Good to upload” checks and match counts to save users time.

