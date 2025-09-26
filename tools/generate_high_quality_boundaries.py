#!/usr/bin/env python3
"""
Generate HIGH QUALITY boundary files for professional choropleth maps.
These will look great when exported to ArcGIS.
"""

import os
import json
import geopandas as gpd
from pathlib import Path
import zipfile

# Use existing downloaded data
DATA_DIR = Path.home() / "data" / "tiger" / "GENZ"
OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "boundaries_hq"
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
    """Minimal simplification to preserve quality while reducing file size slightly."""
    # Project to Web Mercator for simplification
    gdf_projected = gdf.to_crs('EPSG:3857')
    # MUCH less aggressive simplification for quality
    gdf_projected['geometry'] = gdf_projected.geometry.simplify(tolerance=tolerance)
    # Project back to WGS84
    return gdf_projected.to_crs('EPSG:4326')

def process_us_states():
    """Process US state boundaries with HIGH QUALITY."""
    print("\n=== Processing US States (High Quality) ===")
    
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
    
    # MINIMAL simplification for high quality (was 10000, now 100)
    gdf = simplify_geometry(gdf, tolerance=100)  # Much less aggressive
    
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
    
    # Convert to GeoJSON with higher precision
    geojson = json.loads(gdf.to_json(ensure_ascii=False))
    
    # Add properties for easy access
    for i, feature in enumerate(geojson['features']):
        if 'FIPS' in feature['properties']:
            feature['id'] = feature['properties']['FIPS']
    
    # Save to file (not minified for better debugging)
    output_file = OUTPUT_DIR / "us_states_hq.json"
    with open(output_file, 'w') as f:
        json.dump(geojson, f, separators=(',', ':'))
    
    file_size = output_file.stat().st_size / 1024
    if file_size > 1024:
        print(f"  Saved us_states_hq.json ({file_size/1024:.1f} MB) - HIGH QUALITY")
    else:
        print(f"  Saved us_states_hq.json ({file_size:.1f} KB) - HIGH QUALITY")
    return gdf

def process_us_counties():
    """Process US county boundaries with HIGH QUALITY."""
    print("\n=== Processing US Counties (High Quality) ===")
    
    # Try to load from local files
    gdf = load_from_local("*county*.zip")
    if gdf is None:
        gdf = load_from_local("*county*.parquet")
    
    if gdf is None:
        print("  No county boundaries found locally")
        return None
    
    # Remove territories if STATEFP exists
    if 'STATEFP' in gdf.columns:
        gdf = gdf[~gdf['STATEFP'].isin(['60', '66', '69', '78'])]
    
    # MINIMAL simplification for counties (was 5000, now 50)
    gdf = simplify_geometry(gdf, tolerance=50)  # Much less aggressive
    
    # Keep only essential columns and create GEOID
    if 'STATEFP' in gdf.columns and 'COUNTYFP' in gdf.columns:
        gdf['GEOID'] = gdf['STATEFP'] + gdf['COUNTYFP']
        gdf = gdf[['GEOID', 'STATEFP', 'NAME', 'geometry'] if 'NAME' in gdf.columns else ['GEOID', 'STATEFP', 'geometry']]
    
    # Convert to GeoJSON
    geojson = json.loads(gdf.to_json(ensure_ascii=False))
    for feature in geojson['features']:
        if 'GEOID' in feature['properties']:
            feature['id'] = feature['properties']['GEOID']
    
    output_file = OUTPUT_DIR / "us_counties_hq.json"
    with open(output_file, 'w') as f:
        json.dump(geojson, f, separators=(',', ':'))
    
    file_size = output_file.stat().st_size / 1024
    if file_size > 1024:
        print(f"  Saved us_counties_hq.json ({file_size/1024:.1f} MB) - HIGH QUALITY")
    else:
        print(f"  Saved us_counties_hq.json ({file_size:.1f} KB) - HIGH QUALITY")
    
    return gdf

def create_metadata():
    """Create a metadata file listing all available boundaries."""
    print("\n=== Creating Metadata ===")
    
    metadata = {
        "generated": "2025-09-26",
        "description": "High quality boundary files for professional choropleth mapping",
        "quality": "HIGH - Minimal simplification for ArcGIS export quality",
        "boundaries": {}
    }
    
    # Check what files were actually created
    if (OUTPUT_DIR / "us_states_hq.json").exists():
        size_kb = (OUTPUT_DIR / "us_states_hq.json").stat().st_size / 1024
        metadata["boundaries"]["us_states"] = {
            "file": "us_states_hq.json",
            "name": "US States (High Quality)",
            "level": "state",
            "size_kb": round(size_kb, 1),
            "id_field": "FIPS",
            "join_fields": ["FIPS", "ABBR", "NAME"],
            "quality": "HIGH"
        }
    
    if (OUTPUT_DIR / "us_counties_hq.json").exists():
        size_kb = (OUTPUT_DIR / "us_counties_hq.json").stat().st_size / 1024
        metadata["boundaries"]["us_counties"] = {
            "file": "us_counties_hq.json",
            "name": "US Counties (High Quality)", 
            "level": "county",
            "size_kb": round(size_kb, 1),
            "id_field": "GEOID",
            "join_fields": ["GEOID", "STATEFP", "NAME"],
            "quality": "HIGH"
        }
    
    output_file = OUTPUT_DIR / "metadata.json"
    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  Saved metadata.json")

def main():
    """Generate all high quality boundary files."""
    print("Generating HIGH QUALITY Boundary Files for Professional Choropleth Maps")
    print("=" * 70)
    print(f"Looking for data in: {DATA_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("\nThese boundaries will look GREAT in ArcGIS!")
    print("Trading file size for quality...")
    
    # Process boundaries
    process_us_states()
    process_us_counties()
    create_metadata()
    
    print("\n" + "=" * 70)
    print("High quality boundary generation complete!")
    print(f"Files saved to: {OUTPUT_DIR}")
    
    # Show total size
    if OUTPUT_DIR.exists():
        json_files = list(OUTPUT_DIR.glob("*.json"))
        if json_files:
            total_size = sum(f.stat().st_size for f in json_files)
            print(f"Total size: {total_size / 1024 / 1024:.2f} MB")
            print(f"Files created: {len(json_files)}")
            print("\nThese will look professional when exported to ArcGIS!")

if __name__ == "__main__":
    import pandas as pd  # Import here in case it's needed
    main()