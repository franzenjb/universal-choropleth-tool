#!/usr/bin/env python3
import argparse
import io
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd

try:
    import geopandas as gpd  # type: ignore
except Exception as e:  # pragma: no cover
    gpd = None

# Allow opting out of TLS verification if system certs are problematic
INSECURE = False
# Optional cache dir for downloaded TIGER zips; supports offline usage
CACHE_DIR: Optional[str] = None
OFFLINE = False
MAX_RETRIES = 6
RETRY_WAIT = 2.0  # seconds (base; exponential backoff)


# ---------------------------
# State helpers
# ---------------------------
STATE_ABBR_TO_FIPS = {
    'AL': '01','AK': '02','AZ': '04','AR': '05','CA': '06','CO': '08','CT': '09','DE': '10','DC': '11',
    'FL': '12','GA': '13','HI': '15','ID': '16','IL': '17','IN': '18','IA': '19','KS': '20','KY': '21',
    'LA': '22','ME': '23','MD': '24','MA': '25','MI': '26','MN': '27','MS': '28','MO': '29','MT': '30',
    'NE': '31','NV': '32','NH': '33','NJ': '34','NM': '35','NY': '36','NC': '37','ND': '38','OH': '39',
    'OK': '40','OR': '41','PA': '42','RI': '44','SC': '45','SD': '46','TN': '47','TX': '48','UT': '49',
    'VT': '50','VA': '51','WA': '53','WV': '54','WI': '55','WY': '56',
    'AS': '60','GU': '66','MP': '69','PR': '72','VI': '78','UM': '74'
}


def normalize_state(state: str) -> Tuple[str, str]:
    s = state.strip()
    if re.fullmatch(r"\d{2}", s):
        # already FIPS
        fips = s
        abbr = next((k for k, v in STATE_ABBR_TO_FIPS.items() if v == fips), None)
        if not abbr:
            raise ValueError(f"Unknown state FIPS: {fips}")
        return abbr, fips
    s_up = s.upper()
    if s_up in STATE_ABBR_TO_FIPS:
        return s_up, STATE_ABBR_TO_FIPS[s_up]
    raise ValueError(f"State must be 2-letter (e.g., FL) or 2-digit FIPS (e.g., 12). Got: {state}")


# ---------------------------
# TIGER/Cartographic boundary URLs (2023)
# ---------------------------
CB_BASE_2023 = "https://www2.census.gov/geo/tiger/GENZ2023/shp"
CB_BASE_2022 = "https://www2.census.gov/geo/tiger/GENZ2022/shp"
CB_BASE_2021 = "https://www2.census.gov/geo/tiger/GENZ2021/shp"
CB_BASE_2020 = "https://www2.census.gov/geo/tiger/GENZ2020/shp"


def place_url():
    # National place boundaries (500k) for 2023
    return f"{CB_BASE_2023}/cb_2023_us_place_500k.zip"


def cousub_url(state_fips: str):
    # County subdivisions per-state (500k)
    return f"{CB_BASE_2023}/cb_2023_{state_fips}_cousub_500k.zip"


def zcta_urls():
    # Try recent to older ZCTA releases (500k). 2020 is widely used and available.
    return [
        f"{CB_BASE_2023}/cb_2023_us_zcta520_500k.zip",
        f"{CB_BASE_2022}/cb_2022_us_zcta520_500k.zip",
        f"{CB_BASE_2021}/cb_2021_us_zcta520_500k.zip",
        f"{CB_BASE_2020}/cb_2020_us_zcta520_500k.zip",
    ]

def state_us_url():
    return f"{CB_BASE_2023}/cb_2023_us_state_500k.zip"

def county_us_url():
    return f"{CB_BASE_2023}/cb_2023_us_county_500k.zip"

def tract_url(state_fips: str):
    return f"{CB_BASE_2023}/cb_2023_{state_fips}_tract_500k.zip"

def bg_url(state_fips: str):
    return f"{CB_BASE_2023}/cb_2023_{state_fips}_bg_500k.zip"

def resolve_first_available(urls):
    import requests
    if OFFLINE and CACHE_DIR:
        for u in urls:
            cpath = _cache_path_for(u)
            if cpath and os.path.exists(cpath):
                return u
        raise RuntimeError("Offline mode and none of the candidate URLs are cached.")
    for u in urls:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = requests.head(u, allow_redirects=True, timeout=30, verify=(not INSECURE))
                if r.ok:
                    return u
            except Exception:
                pass
            if attempt < MAX_RETRIES:
                import time
                time.sleep(RETRY_WAIT * (2 ** (attempt - 1)))
    raise RuntimeError(f"None of the candidate URLs are available: {urls}")


# ---------------------------
# IO helpers
# ---------------------------
def require_geopandas():
    if gpd is None:
        raise SystemExit(
            "geopandas is required. Install with: pip install geopandas pyogrio shapely pyproj fiona"
        )


def read_csv_smart(path: str) -> pd.DataFrame:
    # Handle potential UTF-8 BOM in header
    with open(path, 'rb') as f:
        raw = f.read()
    buf = io.BytesIO(raw)
    try:
        df = pd.read_csv(buf, encoding='utf-8-sig')
    except UnicodeDecodeError:
        buf.seek(0)
        df = pd.read_csv(buf)
    return df


def _cache_path_for(url: str) -> Optional[str]:
    if not CACHE_DIR:
        return None
    fname = os.path.basename(url)
    return os.path.join(CACHE_DIR, fname)


def download_to_temp(url: str) -> str:
    import requests  # local import to avoid hard dep if not used
    cpath = _cache_path_for(url)
    if cpath and os.path.exists(cpath):
        return cpath
    if OFFLINE:
        raise RuntimeError(f"Offline mode and not cached: {url}")
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=120, verify=(not INSECURE))
            # Retry on typical transient statuses
            if resp.status_code in (429, 500, 502, 503, 504):
                raise RuntimeError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            break
        except Exception as e:
            last_err = e
            if attempt == MAX_RETRIES:
                raise
            import time
            time.sleep(RETRY_WAIT * (2 ** (attempt - 1)))
    fd, path = tempfile.mkstemp(suffix=os.path.splitext(url)[1])
    os.close(fd)
    with open(path, 'wb') as f:
        f.write(resp.content)
    if cpath:
        os.makedirs(os.path.dirname(cpath), exist_ok=True)
        try:
            os.replace(path, cpath)
            return cpath
        except Exception:
            pass
    return path


def read_geodata_from_zip(url: str, layer_hint: Optional[str] = None) -> 'gpd.GeoDataFrame':
    require_geopandas()
    zpath = download_to_temp(url)
    ds_path = f"zip://{zpath}"
    gdf = gpd.read_file(ds_path, layer=layer_hint) if layer_hint else gpd.read_file(ds_path)
    return gdf


# ---------------------------
# Join logic per geography
# ---------------------------
def prepare_place(state_abbr: str, state_fips: str, csv_path: str) -> 'gpd.GeoDataFrame':
    gdf = read_geodata_from_zip(place_url())
    # Filter to state
    gdf = gdf[gdf['STATEFP'] == state_fips]

    df = read_csv_smart(csv_path)
    # Expect a 7-digit GEOID for place
    if 'GEOID' not in df.columns:
        raise ValueError("CSV missing GEOID column for place level")
    df['GEOID'] = df['GEOID'].astype(str).str.zfill(7)

    merged = gdf.merge(df, how='left', on='GEOID')
    return merged


def prepare_cousub(state_abbr: str, state_fips: str, csv_path: str) -> 'gpd.GeoDataFrame':
    gdf = read_geodata_from_zip(cousub_url(state_fips))
    df = read_csv_smart(csv_path)
    # Expect 10-digit GEOID: state(2)+county(3)+cousub(5)
    if 'GEOID' not in df.columns:
        raise ValueError("CSV missing GEOID column for Sub_County level")
    df['GEOID'] = df['GEOID'].astype(str).str.zfill(10)
    merged = gdf.merge(df, how='left', on='GEOID')
    return merged


def prepare_zcta(state_abbr: str, state_fips: str, csv_path: str) -> 'gpd.GeoDataFrame':
    url = resolve_first_available(zcta_urls())
    gdf = read_geodata_from_zip(url)
    # ZCTA fields: commonly ZCTA5CE20 and GEOID20 (5-digit string)
    geoid_field = 'GEOID20' if 'GEOID20' in gdf.columns else ('GEOID10' if 'GEOID10' in gdf.columns else None)
    zcta_field = 'ZCTA5CE20' if 'ZCTA5CE20' in gdf.columns else ('ZCTA5CE10' if 'ZCTA5CE10' in gdf.columns else None)
    if not geoid_field and not zcta_field:
        raise ValueError("Unexpected ZCTA schema: missing GEOID/ZCTA5CE fields")

    df = read_csv_smart(csv_path)
    # Many CSVs use ZIP numeric; normalize to 5-digit string
    zip_col = None
    for cand in ['ZIP', 'Zip', 'zip', 'ZCTA', 'ZCTA5']:
        if cand in df.columns:
            zip_col = cand
            break
    if not zip_col:
        raise ValueError("CSV missing ZIP/ZCTA column for ZIP level")
    df['_ZCTA5'] = df[zip_col].astype(str).str.extract(r"(\d+)")[0].str.zfill(5)

    key = geoid_field or zcta_field
    gdf['_ZCTA5'] = gdf[key].astype(str).str.zfill(5)

    merged = gdf.merge(df, how='left', left_on='_ZCTA5', right_on='_ZCTA5')

    # Optional: filter to state using state boundary overlay to reduce size.
    # Simpler heuristic: keep ZCTAs whose centroid lies within the state boundary.
    try:
        states_url = state_us_url()
        states = read_geodata_from_zip(states_url)
        state_poly = states.loc[states['STUSPS'] == state_abbr, 'geometry'].values[0]
        merged = merged.set_geometry('geometry')
        merged = merged[merged.geometry.centroid.within(state_poly)]
    except Exception:
        # If overlay fails (e.g., missing deps), skip filtering
        pass

    return merged


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    # Add commonly useful rates for choropleths
    cols = df.columns
    needed = ['Households', 'Poverty Households', 'ALICE Households']
    if all(c in cols for c in needed):
        hh = df['Households'].astype(float)
        below = df['Poverty Households'].astype(float) + df['ALICE Households'].astype(float)
        with pd.option_context('mode.chained_assignment', None):
            df['Below_ALICE_Rate'] = (below / hh).where(hh > 0)
            df['Poverty_Rate'] = (df['Poverty Households'].astype(float) / hh).where(hh > 0)
            df['ALICE_Rate'] = (df['ALICE Households'].astype(float) / hh).where(hh > 0)
    return df


# ---------------------------
# CLI
# ---------------------------
@dataclass
class Args:
    level: str
    state: str
    csv: str
    out: str
    insecure: bool
    cache_dir: Optional[str]
    offline: bool
    max_retries: int
    retry_wait: float


def parse_args(argv=None) -> Args:
    p = argparse.ArgumentParser(description="Join ALICE CSVs to TIGER geometries and export GeoJSON")
    p.add_argument('--level', required=True, choices=['place', 'subcounty', 'zcta'], help='Geography level to join')
    p.add_argument('--state', required=True, help='State 2-letter (e.g., FL) or 2-digit FIPS (e.g., 12)')
    p.add_argument('--csv', required=True, help='Path to the ALICE CSV for the chosen level')
    p.add_argument('--out', required=True, help='Output GeoJSON path')
    p.add_argument('--insecure', action='store_true', help='Disable TLS verification when downloading TIGER files')
    p.add_argument('--cache-dir', help='Directory to cache TIGER zip files for reuse/offline')
    p.add_argument('--offline', action='store_true', help='Use only cached files; do not attempt network downloads')
    p.add_argument('--max-retries', type=int, default=MAX_RETRIES, help='Max HTTP retries for downloads (default 6)')
    p.add_argument('--retry-wait', type=float, default=RETRY_WAIT, help='Base seconds for exponential backoff (default 2.0)')
    p.add_argument('--simplify', type=float, help='Douglas-Peucker tolerance in degrees to simplify geometry (e.g., 0.0005)')
    ns = p.parse_args(argv)
    # Extend Args dynamically with simplify without changing dataclass signature for brevity
    args_obj = Args(level=ns.level, state=ns.state, csv=ns.csv, out=ns.out, insecure=ns.insecure, cache_dir=ns.cache_dir, offline=ns.offline, max_retries=ns.max_retries, retry_wait=ns.retry_wait)
    setattr(args_obj, 'simplify', ns.simplify)
    return args_obj


def main(argv=None) -> int:
    args = parse_args(argv)
    abbr, fips = normalize_state(args.state)

    global INSECURE
    INSECURE = bool(args.insecure or os.environ.get('ALICE_INSECURE'))
    global CACHE_DIR, OFFLINE, MAX_RETRIES, RETRY_WAIT
    CACHE_DIR = args.cache_dir or os.environ.get('ALICE_CACHE_DIR')
    OFFLINE = bool(args.offline or os.environ.get('ALICE_OFFLINE'))
    MAX_RETRIES = int(os.environ.get('ALICE_MAX_RETRIES', args.max_retries))
    RETRY_WAIT = float(os.environ.get('ALICE_RETRY_WAIT', args.retry_wait))

    if args.level == 'place':
        gdf = prepare_place(abbr, fips, args.csv)
    elif args.level == 'subcounty':
        gdf = prepare_cousub(abbr, fips, args.csv)
    else:
        gdf = prepare_zcta(abbr, fips, args.csv)

    # Compute common metrics and write GeoJSON
    gdf = gdf.pipe(lambda df: df.set_geometry('geometry') if 'geometry' in df else df)
    gdf = gdf.copy()
    gdf = gdf.assign(**compute_metrics(gdf))

    # Optional simplify
    simp = getattr(args, 'simplify', None)
    if simp and hasattr(gdf, 'geometry'):
        try:
            gdf['geometry'] = gdf.geometry.simplify(simp, preserve_topology=True)
        except Exception:
            pass

    # Keep geometry + useful attributes; drop any temp columns
    drop_cols = [c for c in gdf.columns if c.startswith('_')]
    if drop_cols:
        gdf = gdf.drop(columns=drop_cols)

    # Write
    require_geopandas()
    gdf.to_file(args.out, driver='GeoJSON')
    print(f"Wrote {args.out} ({len(gdf)} features)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
