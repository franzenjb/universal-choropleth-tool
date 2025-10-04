**Overview**
- Purpose: Join any CSV (Place, Sub-County, ZIP, etc.) with Census TIGER/Cartographic boundaries to export GeoJSON for ArcGIS.
- Output: A `.geojson` you can upload to ArcGIS Online or Pro and style as a choropleth without consuming credits.
- Inputs: One CSV per level per state. Works across states by switching the `--state` argument.

**Supported Levels**
- place: TIGER `cb_2023_us_place_500k.zip` filtered to a state/territory. Join on `GEOID` (7-digit: state+place).
- subcounty: TIGER `cb_2023_{STATEFIPS}_cousub_500k.zip`. Join on `GEOID` (10-digit: state+county+cousub).
- zcta: TIGER ZCTA 5-digit (500k). Tries 2023→2022→2021→2020; typically resolves to `cb_2020_us_zcta520_500k.zip`.

**Join Keys**
- Place: CSV `GEOID` → boundary `GEOID` (7 digits).
- Sub-County: CSV `GEOID` → boundary `GEOID` (10 digits).
- ZIP/ZCTA: CSV `ZIP` (5-digit) → boundary `GEOID20` or `ZCTA5CE20`.
  - Note: USPS ZIPs ≠ Census ZCTAs. Small differences are normal.

**Computed Metrics (ALICE Data Example)**
When working with ALICE household data, these metrics are auto-calculated:
- `Below_ALICE_Rate`: (`Poverty Households` + `ALICE Households`) / `Households`
- `Poverty_Rate`: `Poverty Households` / `Households`
- `ALICE_Rate`: `ALICE Households` / `Households`

**Usage**
- Install deps (suggested): `pip install geopandas pyogrio shapely pyproj fiona requests pandas`
- Run examples:
  - Place (Florida): `python tools/choropleth.py --level place --state FL --csv "/Users/you/Desktop/Data/Florida_Place_Data.csv" --out out/fl_place.geojson`
  - Sub-County (Florida): `python tools/choropleth.py --level subcounty --state FL --csv "/Users/you/Desktop/Data/Florida_Sub_County_Data.csv" --out out/fl_subcounty.geojson`
  - ZIP/ZCTA (Florida): `python tools/choropleth.py --level zcta --state FL --csv "/Users/you/Desktop/Data/Florida_ZIP_Data.csv" --out out/fl_zcta.geojson`

**All States + Territories**
- The tool accepts `--state` for any STUSPS in: 50 states, DC, PR, GU, VI, AS, MP (FIPS: 72, 66, 78, 60, 69). Some geographies may not exist for certain territories (e.g., county subdivisions).

**Caching & Offline**
- Add a cache dir to avoid re-downloading and enable offline:
  - `--cache-dir ~/data/tiger/GENZ` (or set env `CHOROPLETH_CACHE_DIR`)
  - `--offline` to force reads from cache only.
- Insecure TLS toggle if your OS certs are misconfigured: `--insecure` (or `CHOROPLETH_INSECURE=1`).
 - Resilience: tune retries/backoff with `--max-retries` and `--retry-wait` (seconds). Env overrides: `CHOROPLETH_MAX_RETRIES`, `CHOROPLETH_RETRY_WAIT`.

**Prefetching**
- Download everything at once for all states/territories:
  - `python tools/prefetch_tiger.py --cache-dir ~/data/tiger/GENZ --insecure --until-complete`
  - This fetches: places (US), ZCTA (US), and county subdivisions per state/territory (skips those not available).
  - Add `--max-retries` and `--retry-wait` to persist through flaky periods.

**ArcGIS Tips**
- Upload the GeoJSON as a hosted feature layer, then style by any numeric column with quantiles or natural breaks.
- For consistent multi-state maps, use the same class breaks across layers.

**Caveats**
- ZCTA vs ZIP: Some ZIPs will not match a ZCTA; these will have nulls. Consider a USPS ZIP↔ZCTA crosswalk if needed.
- CCD/MCD availability: Sub-county geographies vary by state (MCDs vs CCDs). Your CSV’s 10-digit `GEOID` should align with TIGER county subdivisions.
- Encoding: CSVs with a UTF-8 BOM are handled automatically.
- Performance: National place/ZCTA files can be large; the tool trims ZCTAs to the target state by centroid, but you can post-filter if needed.

**Troubleshooting**
- If you see `geopandas is required`, install dependencies as above.
- If joins return many nulls:
  - Verify join keys: `GEOID` zero-padding for place (7) and sub-county (10), and 5-digit strings for ZCTA.
  - Spot-check an ID present in both the CSV and the boundary file.
- If uploads to ArcGIS fail, try re-saving GeoJSON in WGS84 (EPSG:4326). The tool writes EPSG:4326 by default via TIGER inputs.
