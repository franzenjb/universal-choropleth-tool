#!/usr/bin/env python3
"""
Generate COMPLETE ZIP code (ZCTA) boundaries for the entire United States.
This will be a large file but will support all US ZIP codes.
"""

import os
import json
import geopandas as gpd
from pathlib import Path
import requests
from tqdm import tqdm

# Directories
DATA_DIR = Path.home() / "data" / "tiger" / "GENZ"
OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "boundaries_complete"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def download_zcta_if_needed():
    """Download ZCTA boundaries if not already present."""
    zcta_files = list(DATA_DIR.glob("*zcta*.zip")) + list(DATA_DIR.glob("*zcta*.parquet"))
    
    if not zcta_files:
        print("No ZCTA files found. Downloading from Census...")
        url = "https://www2.census.gov/geo/tiger/GENZ2023/500k/cb_2023_us_zcta520_500k.zip"
        output_path = DATA_DIR / "cb_2023_us_zcta520_500k.zip"
        
        if not output_path.exists():
            print(f"Downloading {url}")
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(output_path, 'wb') as f:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            print(f"Downloaded to {output_path}")
        return output_path
    
    return zcta_files[0]

def simplify_geometry(gdf, tolerance=0.01):
    """Simplify geometries to reduce file size."""
    # Project to Web Mercator for simplification
    gdf_projected = gdf.to_crs('EPSG:3857')
    gdf_projected['geometry'] = gdf_projected.geometry.simplify(tolerance=tolerance)
    # Project back to WGS84
    return gdf_projected.to_crs('EPSG:4326')

def process_complete_zctas():
    """Process ALL US ZCTA boundaries."""
    print("\n=== Processing Complete US ZIP Codes (ZCTAs) ===")
    print("This will include ALL ~33,000 US ZIP codes!")
    
    # Get or download ZCTA file
    zcta_file = download_zcta_if_needed()
    print(f"  Loading from {zcta_file.name}")
    
    # Load the data
    if zcta_file.suffix == '.parquet':
        gdf = gpd.read_parquet(zcta_file)
    else:
        gdf = gpd.read_file(f"zip://{zcta_file}")
    
    print(f"  Loaded {len(gdf)} ZIP codes")
    
    # Create two versions: simplified and high quality
    versions = [
        ("simplified", 500, "us_zctas.json"),  # More aggressive simplification
        ("high_quality", 50, "us_zctas_hq.json")  # Less simplification for quality
    ]
    
    for version_name, tolerance, filename in versions:
        print(f"\n  Creating {version_name} version...")
        
        # Simplify geometry
        gdf_simplified = simplify_geometry(gdf.copy(), tolerance=tolerance)
        
        # Keep minimal columns
        if 'ZCTA5CE20' in gdf_simplified.columns:
            gdf_simplified = gdf_simplified[['ZCTA5CE20', 'geometry']]
            gdf_simplified.columns = ['ZCTA', 'geometry']
        elif 'GEOID20' in gdf_simplified.columns:
            gdf_simplified = gdf_simplified[['GEOID20', 'geometry']]
            gdf_simplified.columns = ['ZCTA', 'geometry']
        
        # Convert to GeoJSON
        print(f"  Converting to GeoJSON...")
        geojson = json.loads(gdf_simplified.to_json())
        
        # Add ID field for each feature
        for feature in geojson['features']:
            if 'ZCTA' in feature['properties']:
                feature['id'] = feature['properties']['ZCTA']
        
        # Save to file
        output_file = OUTPUT_DIR / filename
        print(f"  Saving {filename}...")
        with open(output_file, 'w') as f:
            json.dump(geojson, f, separators=(',', ':'))
        
        file_size = output_file.stat().st_size / 1024 / 1024
        print(f"  ✓ Saved {filename} ({file_size:.1f} MB)")
        
        # Create a smaller regional sample for testing (e.g., Florida ZIPs)
        if version_name == "simplified":
            print("\n  Creating Florida sample for quick testing...")
            florida_zips = gdf_simplified[
                (gdf_simplified['ZCTA'].str.startswith('32')) |
                (gdf_simplified['ZCTA'].str.startswith('33')) |
                (gdf_simplified['ZCTA'].str.startswith('34'))
            ]
            
            fl_geojson = json.loads(florida_zips.to_json())
            for feature in fl_geojson['features']:
                if 'ZCTA' in feature['properties']:
                    feature['id'] = feature['properties']['ZCTA']
            
            fl_output = OUTPUT_DIR / "florida_zctas.json"
            with open(fl_output, 'w') as f:
                json.dump(fl_geojson, f, separators=(',', ':'))
            
            fl_size = fl_output.stat().st_size / 1024
            print(f"  ✓ Saved florida_zctas.json ({fl_size:.1f} KB) - {len(florida_zips)} ZIPs")

def create_metadata():
    """Create metadata file for complete boundaries."""
    print("\n=== Creating Metadata ===")
    
    metadata = {
        "generated": "2025-09-26",
        "description": "Complete US boundary files including all ZIP codes",
        "boundaries": {}
    }
    
    # Check what files were created
    files_info = [
        ("us_zctas.json", "us_zctas", "US ZIP Codes - Complete (Simplified)", "ZCTA"),
        ("us_zctas_hq.json", "us_zctas_hq", "US ZIP Codes - Complete (High Quality)", "ZCTA"),
        ("florida_zctas.json", "florida_zctas", "Florida ZIP Codes (Sample)", "ZCTA")
    ]
    
    for filename, key, name, id_field in files_info:
        filepath = OUTPUT_DIR / filename
        if filepath.exists():
            size_mb = filepath.stat().st_size / 1024 / 1024
            metadata["boundaries"][key] = {
                "file": filename,
                "name": name,
                "level": "zcta",
                "size_mb": round(size_mb, 1),
                "id_field": id_field,
                "join_fields": [id_field],
                "note": "Complete coverage" if "Complete" in name else "Regional sample"
            }
    
    output_file = OUTPUT_DIR / "metadata.json"
    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  Saved metadata.json")

def main():
    """Generate complete ZCTA boundary files."""
    print("Generating COMPLETE ZIP Code Boundaries for Choropleth Tool")
    print("=" * 60)
    print(f"Data directory: {DATA_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    process_complete_zctas()
    create_metadata()
    
    print("\n" + "=" * 60)
    print("Complete ZIP code generation finished!")
    print(f"Files saved to: {OUTPUT_DIR}")
    
    # Show summary
    if OUTPUT_DIR.exists():
        json_files = list(OUTPUT_DIR.glob("*.json"))
        if json_files:
            total_size = sum(f.stat().st_size for f in json_files)
            print(f"\nTotal size: {total_size / 1024 / 1024:.1f} MB")
            print(f"Files created: {len(json_files)}")
            print("\n✅ You now have COMPLETE ZIP code coverage for the entire US!")
            print("Note: These files are large but provide full coverage.")

if __name__ == "__main__":
    import pandas as pd
    main()