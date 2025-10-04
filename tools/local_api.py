#!/usr/bin/env python3
import io
import os
from typing import Optional, Tuple

import pandas as pd
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

try:
    import geopandas as gpd
except Exception as e:  # pragma: no cover
    gpd = None

STATE_ABBR_TO_FIPS = {
    'AL': '01','AK': '02','AZ': '04','AR': '05','CA': '06','CO': '08','CT': '09','DE': '10','DC': '11',
    'FL': '12','GA': '13','HI': '15','ID': '16','IL': '17','IN': '18','IA': '19','KS': '20','KY': '21',
    'LA': '22','ME': '23','MD': '24','MA': '25','MI': '26','MN': '27','MS': '28','MO': '29','MT': '30',
    'NE': '31','NV': '32','NH': '33','NJ': '34','NM': '35','NY': '36','NC': '37','ND': '38','OH': '39',
    'OK': '40','OR': '41','PA': '42','RI': '44','SC': '45','SD': '46','TN': '47','TX': '48','UT': '49',
    'VT': '50','VA': '51','WA': '53','WV': '54','WI': '55','WY': '56','AS': '60','GU': '66','MP': '69',
    'PR': '72','VI': '78','UM': '74'
}

CACHE_DIR = os.environ.get('CHOROPLETH_CACHE_DIR', os.path.expanduser('~/data/tiger/GENZ'))
PARQUET_DIR = os.path.join(CACHE_DIR, 'parquet')
try:
    import pyarrow  # noqa: F401
    _HAS_ARROW = True
except Exception:
    _HAS_ARROW = False
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.normpath(os.path.join(BASE_DIR, '..', 'docs'))


def require_geopandas():
    if gpd is None:
        raise HTTPException(status_code=500, detail='geopandas is required on the server')


def norm_state(token: str) -> Tuple[str, str]:
    t = (token or '').strip()
    if not t:
        raise HTTPException(status_code=400, detail='state is required')
    
    # Handle special cases for US and regions
    if t == 'US':
        return 'US', 'US'
    if t in ['NORTHEAST', 'MIDWEST', 'SOUTH', 'WEST']:
        return t, t
    
    if len(t) == 2 and t.isdigit():
        fips = t
        abbr = next((k for k, v in STATE_ABBR_TO_FIPS.items() if v == fips), None)
        if not abbr:
            raise HTTPException(status_code=400, detail=f'unknown state FIPS {t}')
        return abbr, fips
    t = t.upper()
    if t in STATE_ABBR_TO_FIPS:
        return t, STATE_ABBR_TO_FIPS[t]
    raise HTTPException(status_code=400, detail=f'unknown state {token}')


def parquet_or_zip(path_parquet: str, path_zip: str) -> str:
    # Use parquet only if pyarrow is available and file exists
    if _HAS_ARROW and os.path.exists(path_parquet):
        return path_parquet
    return path_zip


def load_boundary(level: str, state_abbr: str, state_fips: str) -> 'gpd.GeoDataFrame':
    require_geopandas()
    
    # Define regions
    REGIONS = {
        'NORTHEAST': ['CT', 'MA', 'ME', 'NH', 'NJ', 'NY', 'PA', 'RI', 'VT'],
        'MIDWEST': ['IL', 'IN', 'IA', 'KS', 'MI', 'MN', 'MO', 'NE', 'ND', 'OH', 'SD', 'WI'],
        'SOUTH': ['AL', 'AR', 'DE', 'FL', 'GA', 'KY', 'LA', 'MD', 'MS', 'NC', 'OK', 'SC', 'TN', 'TX', 'VA', 'WV', 'DC'],
        'WEST': ['AZ', 'CA', 'CO', 'ID', 'MT', 'NV', 'NM', 'OR', 'UT', 'WA', 'WY', 'AK', 'HI']
    }
    
    if level == 'state':
        p = parquet_or_zip(
            os.path.join(PARQUET_DIR, 'cb_2023_us_state_500k.parquet'),
            os.path.join(CACHE_DIR, 'cb_2023_us_state_500k.zip'),
        )
        gdf = gpd.read_parquet(p) if p.endswith('.parquet') else gpd.read_file(f'zip://{p}')
        
        # Handle US, regions, or individual states
        if state_abbr == 'US':
            # Return all states except territories for cleaner map
            return gdf[gdf['STATEFP'].astype(int) < 60]
        elif state_abbr in REGIONS:
            # Return states in the specified region
            return gdf[gdf['STUSPS'].isin(REGIONS[state_abbr])]
        else:
            # Return individual state
            return gdf[gdf['STUSPS'] == state_abbr]
    if level == 'county':
        p = parquet_or_zip(
            os.path.join(PARQUET_DIR, 'cb_2023_us_county_500k.parquet'),
            os.path.join(CACHE_DIR, 'cb_2023_us_county_500k.zip'),
        )
        gdf = gpd.read_parquet(p) if p.endswith('.parquet') else gpd.read_file(f'zip://{p}')
        
        if state_abbr == 'US':
            # Return all US counties
            return gdf
        elif state_abbr in REGIONS:
            # Get FIPS codes for states in region
            region_fips = [STATE_ABBR_TO_FIPS[st] for st in REGIONS[state_abbr] if st in STATE_ABBR_TO_FIPS]
            return gdf[gdf['STATEFP'].isin(region_fips)]
        else:
            return gdf[gdf['STATEFP'] == state_fips]
    if level == 'place':
        p = parquet_or_zip(
            os.path.join(PARQUET_DIR, 'cb_2023_us_place_500k.parquet'),
            os.path.join(CACHE_DIR, 'cb_2023_us_place_500k.zip'),
        )
        gdf = gpd.read_parquet(p) if p.endswith('.parquet') else gpd.read_file(f'zip://{p}')
        
        if state_abbr == 'US':
            # Return all US places
            return gdf
        elif state_abbr in REGIONS:
            # Get places for states in region
            region_fips = [STATE_ABBR_TO_FIPS[st] for st in REGIONS[state_abbr] if st in STATE_ABBR_TO_FIPS]
            return gdf[gdf['STATEFP'].isin(region_fips)]
        else:
            return gdf[gdf['STATEFP'] == state_fips]
    if level == 'subcounty':
        base = f'cb_2023_{state_fips}_cousub_500k'
        p = parquet_or_zip(
            os.path.join(PARQUET_DIR, f'{base}.parquet'),
            os.path.join(CACHE_DIR, f'{base}.zip'),
        )
        return gpd.read_parquet(p) if p.endswith('.parquet') else gpd.read_file(f'zip://{p}')
    if level == 'tract':
        base = f'cb_2023_{state_fips}_tract_500k'
        p = parquet_or_zip(
            os.path.join(PARQUET_DIR, f'{base}.parquet'),
            os.path.join(CACHE_DIR, f'{base}.zip'),
        )
        return gpd.read_parquet(p) if p.endswith('.parquet') else gpd.read_file(f'zip://{p}')
    if level == 'bg':
        base = f'cb_2023_{state_fips}_bg_500k'
        p = parquet_or_zip(
            os.path.join(PARQUET_DIR, f'{base}.parquet'),
            os.path.join(CACHE_DIR, f'{base}.zip'),
        )
        return gpd.read_parquet(p) if p.endswith('.parquet') else gpd.read_file(f'zip://{p}')
    if level == 'zcta':
        zp = parquet_or_zip(
            os.path.join(PARQUET_DIR, 'cb_2020_us_zcta520_500k.parquet'),
            os.path.join(CACHE_DIR, 'cb_2020_us_zcta520_500k.zip'),
        )
        gdf = gpd.read_parquet(zp) if zp.endswith('.parquet') else gpd.read_file(f'zip://{zp}')
        
        if state_abbr == 'US':
            # Return all US ZCTAs (warning: large dataset!)
            return gdf
        elif state_abbr in REGIONS:
            # Get ZCTAs for all states in the region
            sp = parquet_or_zip(
                os.path.join(PARQUET_DIR, 'cb_2023_us_state_500k.parquet'),
                os.path.join(CACHE_DIR, 'cb_2023_us_state_500k.zip'),
            )
            states = gpd.read_parquet(sp) if sp.endswith('.parquet') else gpd.read_file(f'zip://{sp}')
            region_states = states[states['STUSPS'].isin(REGIONS[state_abbr])]
            region_geom = region_states.unary_union
            # Use centroid method for better performance with ZCTAs
            return gdf[gdf.geometry.centroid.within(region_geom)]
        else:
            # Single state ZCTAs
            sp = parquet_or_zip(
                os.path.join(PARQUET_DIR, 'cb_2023_us_state_500k.parquet'),
                os.path.join(CACHE_DIR, 'cb_2023_us_state_500k.zip'),
            )
            states = gpd.read_parquet(sp) if sp.endswith('.parquet') else gpd.read_file(f'zip://{sp}')
            geom = states.loc[states['STUSPS'] == state_abbr, 'geometry'].values[0]
            return gdf[gdf.geometry.centroid.within(geom)]
    raise HTTPException(status_code=400, detail=f'unsupported level {level}')


def pick_join_key(level: str, gdf: 'gpd.GeoDataFrame') -> str:
    if level in {'state','county','place','subcounty','tract','bg'}:
        return 'GEOID'
    if level == 'zcta':
        return 'GEOID20' if 'GEOID20' in gdf.columns else ('GEOID10' if 'GEOID10' in gdf.columns else 'ZCTA5CE20')
    return 'GEOID'


def normalize_csv_key(level: str, df: pd.DataFrame, provided: Optional[str]) -> Tuple[pd.DataFrame, str]:
    candidates = []
    if provided:
        candidates = [provided]
    else:
        defaults = {
            'state': ['STATEFP','statefp','STATE','state','STUSPS','stusps','GEOID','FIPS'],
            'county': ['GEOID','FIPS','FIPS5','COUNTYFP','CountyFIPS'],
            'place': ['GEOID','PlaceGEOID'],
            'subcounty': ['GEOID'],
            'tract': ['GEOID'],
            'bg': ['GEOID'],
            'zcta': ['ZIP','Zip','zip','ZCTA','ZCTA5','GEOID'],
        }
        candidates = defaults.get(level, ['GEOID'])
    key = next((c for c in candidates if c in df.columns), None)
    if not key:
        raise HTTPException(status_code=400, detail=f'could not find join column in CSV (tried: {candidates})')
    s = df[key].astype(str)
    if level == 'state': df['_J'] = s.str.extract(r'(\d+)')[0].str.zfill(2).fillna('')
    elif level == 'county': df['_J'] = s.str.extract(r'(\d+)')[0].str.zfill(5).fillna('')
    elif level == 'place': df['_J'] = s.str.extract(r'(\d+)')[0].str.zfill(7).fillna('')
    elif level == 'subcounty': df['_J'] = s.str.extract(r'(\d+)')[0].str.zfill(10).fillna('')
    elif level == 'tract': df['_J'] = s.str.extract(r'(\d+)')[0].str.zfill(11).fillna('')
    elif level == 'bg': df['_J'] = s.str.extract(r'(\d+)')[0].str.zfill(12).fillna('')
    elif level == 'zcta': df['_J'] = s.str.extract(r'(\d+)')[0].str.zfill(5).fillna('')
    else: df['_J'] = s
    return df, '_J'


def compute_rates(df: pd.DataFrame) -> None:
    needed = ['Households', 'Poverty Households', 'ALICE Households']
    if all(c in df.columns for c in needed):
        hh = df['Households'].astype(float)
        below = df['Poverty Households'].astype(float) + df['ALICE Households'].astype(float)
        df['Below_ALICE_Rate'] = (below / hh).where(hh > 0)
        df['Poverty_Rate'] = (df['Poverty Households'].astype(float) / hh).where(hh > 0)
        df['ALICE_Rate'] = (df['ALICE Households'].astype(float) / hh).where(hh > 0)


app = FastAPI(title='Local Boundary & Join API')

# Permissive CORS during development if env set
ALLOW_ALL = bool(os.environ.get('CHOROPLETH_CORS_ALLOW_ALL'))
if ALLOW_ALL:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_origin_regex=r".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            'http://localhost:8000','http://127.0.0.1:8000',
            'https://franzenjb.github.io'
        ],
        allow_origin_regex=r"^https://([a-z0-9-]+)\.github\.io$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Serve the local web app to avoid mixed-content/CORS when using GitHub Pages
if os.path.isdir(DOCS_DIR):
    app.mount('/app', StaticFiles(directory=DOCS_DIR), name='app')


@app.get('/')
def root():
    if os.path.isdir(DOCS_DIR):
        return RedirectResponse(url='/app/quick.html')
    return {'status': 'ok'}


@app.get('/app')
def app_root():
    if os.path.isdir(DOCS_DIR):
        return FileResponse(os.path.join(DOCS_DIR, 'quick.html'))
    raise HTTPException(status_code=404, detail='Not Found')


@app.get('/app/quick.html')
def app_quick():
    path = os.path.join(DOCS_DIR, 'quick.html')
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail='Not Found')


@app.get('/health')
def health() -> dict:
    return {'status': 'ok', 'cache_dir': CACHE_DIR}


@app.get('/boundaries')
def boundaries(state: str, level: str):
    abbr, fips = norm_state(state)
    gdf = load_boundary(level, abbr, fips)
    return JSONResponse(content=gdf.to_json())


@app.post('/join')
async def join(state: str = Form(...), level: str = Form(...), join_col: Optional[str] = Form(None), simplify: Optional[float] = Form(None), csv: UploadFile = File(...)):
    # Handle special cases where norm_state returns the same value for both
    if state in ['US', 'NORTHEAST', 'MIDWEST', 'SOUTH', 'WEST']:
        abbr = state
        fips = state
    else:
        abbr, fips = norm_state(state)
    
    gdf = load_boundary(level, abbr, fips)
    raw = await csv.read()
    try:
        df = pd.read_csv(io.BytesIO(raw), encoding='utf-8-sig')
    except Exception:
        df = pd.read_csv(io.BytesIO(raw))
    df, jcol = normalize_csv_key(level, df, join_col)
    bkey = pick_join_key(level, gdf)
    gdf['_J'] = gdf[bkey].astype(str)
    if level == 'zcta':
        gdf['_J'] = gdf['_J'].str.zfill(5)
    mg = gdf.merge(df, how='left', left_on='_J', right_on=jcol)
    compute_rates(mg)
    if simplify and 'geometry' in mg:
        try: mg['geometry'] = mg.geometry.simplify(float(simplify), preserve_topology=True)
        except Exception: pass
    mg = mg.drop(columns=[c for c in mg.columns if c == '_J'])
    return JSONResponse(content=mg.to_json())


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8765)
