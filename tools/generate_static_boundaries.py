#!/usr/bin/env python3
"""
Generate lightweight, pre-processed boundary files for browser-based choropleth tool.
This creates simplified GeoJSON files that can be served statically from GitHub Pages.
"""

import os
import json
import geopandas as gpd
from pathlib import Path
import zipfile

# Use existing downloaded data
DATA_DIR = Path.home() / "data" / "tiger" / "GENZ"
OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "boundaries"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_from_local(file_pattern):
    """Load from local downloaded files."""
    files = list(DATA_DIR.glob(file_pattern))
    if files:
        file_path = files[0]
        print(f"  Loading from {file_path.name}")
        if file_path.suffix == '.zip':
            return gpd.read_file(f"zip://{file_path}")
        elif file_path.suffix == '.parquet':
            return gpd.read_parquet(file_path)
        else:
            return gpd.read_file(file_path)
    return None

def simplify_geometry(gdf, tolerance=0.01):
    """Simplify geometries to reduce file size."""
    # Project to Web Mercator for simplification
    gdf_projected = gdf.to_crs('EPSG:3857')
    gdf_projected['geometry'] = gdf_projected.geometry.simplify(tolerance=tolerance)
    # Project back to WGS84
    return gdf_projected.to_crs('EPSG:4326')

def process_us_states():
    """Process US state boundaries."""
    print("\n=== Processing US States ===")
    
    # Try to load from local files
    gdf = load_from_local("*state*.zip")
    if gdf is None:
        gdf = load_from_local("*state*.parquet")
    
    if gdf is None:
        print("  No state boundaries found locally")
        return None
    
    # Remove territories we don't typically need for US maps
    if 'STATEFP' in gdf.columns:
        gdf = gdf[~gdf['STATEFP'].isin(['60', '66', '69', '78'])]  # AS, GU, MP, VI
    
    # Simplify geometry - states can be very simplified
    gdf = simplify_geometry(gdf, tolerance=10000)  # More aggressive for states
    
    # Keep only essential columns
    cols_to_keep = []
    if 'STATEFP' in gdf.columns:
        cols_to_keep.append('STATEFP')
    if 'STUSPS' in gdf.columns:
        cols_to_keep.append('STUSPS')
    if 'NAME' in gdf.columns:
        cols_to_keep.append('NAME')
    cols_to_keep.append('geometry')
    
    gdf = gdf[cols_to_keep]
    gdf.columns = ['FIPS', 'ABBR', 'NAME', 'geometry'] if len(cols_to_keep) == 4 else gdf.columns
    
    # Convert to GeoJSON
    geojson = json.loads(gdf.to_json())
    
    # Add properties for easy access
    for i, feature in enumerate(geojson['features']):
        if 'FIPS' in feature['properties']:
            feature['id'] = feature['properties']['FIPS']
    
    # Save to file
    output_file = OUTPUT_DIR / "us_states.json"
    with open(output_file, 'w') as f:
        json.dump(geojson, f, separators=(',', ':'))  # Minify
    
    file_size = output_file.stat().st_size / 1024
    print(f"  Saved us_states.json ({file_size:.1f} KB)")
    return gdf

def process_us_counties():
    """Process US county boundaries."""
    print("\n=== Processing US Counties ===")
    
    # Try to load from local files
    gdf = load_from_local("*county*.zip")
    if gdf is None:
        gdf = load_from_local("*county*.parquet")
    
    if gdf is None:
        print("  No county boundaries found locally")
        # Try to load state-specific counties and combine
        state_gdfs = []
        for state_file in DATA_DIR.glob("*_county_*.parquet"):
            try:
                state_gdf = gpd.read_parquet(state_file)
                state_gdfs.append(state_gdf)
            except:
                pass
        
        if state_gdfs:
            gdf = gpd.GeoDataFrame(pd.concat(state_gdfs, ignore_index=True))
            print(f"  Combined {len(state_gdfs)} state county files")
        else:
            return None
    
    # Remove territories if STATEFP exists
    if 'STATEFP' in gdf.columns:
        gdf = gdf[~gdf['STATEFP'].isin(['60', '66', '69', '78'])]
    
    # Simplify geometry aggressively for counties
    gdf = simplify_geometry(gdf, tolerance=5000)  # Aggressive simplification
    
    # Keep only essential columns and create GEOID
    if 'STATEFP' in gdf.columns and 'COUNTYFP' in gdf.columns:
        gdf['GEOID'] = gdf['STATEFP'] + gdf['COUNTYFP']
        gdf = gdf[['GEOID', 'STATEFP', 'NAME', 'geometry'] if 'NAME' in gdf.columns else ['GEOID', 'STATEFP', 'geometry']]
    
    # Convert to GeoJSON
    geojson = json.loads(gdf.to_json())
    for feature in geojson['features']:
        if 'GEOID' in feature['properties']:
            feature['id'] = feature['properties']['GEOID']
    
    output_file = OUTPUT_DIR / "us_counties.json"
    with open(output_file, 'w') as f:
        json.dump(geojson, f, separators=(',', ':'))
    
    file_size = output_file.stat().st_size / 1024
    if file_size > 1024:
        print(f"  Saved us_counties.json ({file_size/1024:.1f} MB)")
    else:
        print(f"  Saved us_counties.json ({file_size:.1f} KB)")

def process_sample_zctas():
    """Process sample ZCTA (ZIP code) data for demos."""
    print("\n=== Processing Sample ZIP Codes ===")
    
    # Look for any ZCTA files
    zcta_files = list(DATA_DIR.glob("*zcta*.parquet")) + list(DATA_DIR.glob("*zcta*.zip"))
    
    if not zcta_files:
        print("  No ZCTA files found locally")
        return
    
    # Process first available ZCTA file as sample
    for zcta_file in zcta_files[:1]:  # Just process one for demo
        print(f"  Processing {zcta_file.name}")
        
        if zcta_file.suffix == '.parquet':
            gdf = gpd.read_parquet(zcta_file)
        else:
            gdf = gpd.read_file(f"zip://{zcta_file}")
        
        # Take a sample of ZCTAs
        gdf = gdf.head(100)  # Just 100 ZIPs for demo
        
        # Simplify heavily
        gdf = simplify_geometry(gdf, tolerance=1000)
        
        # Keep minimal columns
        if 'ZCTA5CE20' in gdf.columns:
            gdf = gdf[['ZCTA5CE20', 'geometry']]
            gdf.columns = ['ZCTA', 'geometry']
        elif 'GEOID20' in gdf.columns:
            gdf = gdf[['GEOID20', 'geometry']]
            gdf.columns = ['ZCTA', 'geometry']
        
        # Convert to GeoJSON
        geojson = json.loads(gdf.to_json())
        for feature in geojson['features']:
            if 'ZCTA' in feature['properties']:
                feature['id'] = feature['properties']['ZCTA']
        
        output_file = OUTPUT_DIR / "sample_zctas.json"
        with open(output_file, 'w') as f:
            json.dump(geojson, f, separators=(',', ':'))
        
        file_size = output_file.stat().st_size / 1024
        print(f"  Saved sample_zctas.json ({file_size:.1f} KB)")
        break

def create_metadata():
    """Create a metadata file listing all available boundaries."""
    print("\n=== Creating Metadata ===")
    
    metadata = {
        "generated": "2024-01-26",
        "description": "Lightweight boundary files for browser-based choropleth mapping",
        "boundaries": {}
    }
    
    # Check what files were actually created
    if (OUTPUT_DIR / "us_states.json").exists():
        size_kb = (OUTPUT_DIR / "us_states.json").stat().st_size / 1024
        metadata["boundaries"]["us_states"] = {
            "file": "us_states.json",
            "name": "US States",
            "level": "state",
            "size_kb": round(size_kb, 1),
            "id_field": "FIPS",
            "join_fields": ["FIPS", "ABBR", "NAME"]
        }
    
    if (OUTPUT_DIR / "us_counties.json").exists():
        size_kb = (OUTPUT_DIR / "us_counties.json").stat().st_size / 1024
        metadata["boundaries"]["us_counties"] = {
            "file": "us_counties.json",
            "name": "US Counties", 
            "level": "county",
            "size_kb": round(size_kb, 1),
            "id_field": "GEOID",
            "join_fields": ["GEOID", "STATEFP", "NAME"]
        }
    
    if (OUTPUT_DIR / "sample_zctas.json").exists():
        size_kb = (OUTPUT_DIR / "sample_zctas.json").stat().st_size / 1024
        metadata["boundaries"]["sample_zctas"] = {
            "file": "sample_zctas.json",
            "name": "Sample ZIP Codes",
            "level": "zcta",
            "size_kb": round(size_kb, 1),
            "id_field": "ZCTA",
            "join_fields": ["ZCTA"],
            "note": "Limited sample for demo purposes"
        }
    
    output_file = OUTPUT_DIR / "metadata.json"
    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  Saved metadata.json")

def main():
    """Generate all static boundary files."""
    print("Generating Static Boundary Files for Choropleth Tool")
    print("=" * 50)
    print(f"Looking for data in: {DATA_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Process boundaries
    process_us_states()
    process_us_counties()
    process_sample_zctas()
    create_metadata()
    
    print("\n" + "=" * 50)
    print("Static boundary generation complete!")
    print(f"Files saved to: {OUTPUT_DIR}")
    
    # Show total size
    if OUTPUT_DIR.exists():
        json_files = list(OUTPUT_DIR.glob("*.json"))
        if json_files:
            total_size = sum(f.stat().st_size for f in json_files)
            print(f"Total size: {total_size / 1024 / 1024:.2f} MB")
            print(f"Files created: {len(json_files)}")

if __name__ == "__main__":
    import pandas as pd  # Import here in case it's needed
    main()