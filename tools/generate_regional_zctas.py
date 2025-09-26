#!/usr/bin/env python3
"""
Split ZIP codes into regional files for better performance.
Each region gets its own file instead of one massive 140MB file.
"""

import os
import json
import geopandas as gpd
from pathlib import Path

# Directories
DATA_DIR = Path.home() / "data" / "tiger" / "GENZ"
OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "boundaries_regional"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Define regions by ZIP code prefixes
REGIONS = {
    'northeast': {
        'name': 'Northeast',
        'states': ['CT', 'MA', 'ME', 'NH', 'NJ', 'NY', 'PA', 'RI', 'VT'],
        'prefixes': ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19']
    },
    'southeast': {
        'name': 'Southeast', 
        'states': ['AL', 'FL', 'GA', 'KY', 'MS', 'NC', 'SC', 'TN', 'VA', 'WV'],
        'prefixes': ['20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '40', '41', '42']
    },
    'midwest': {
        'name': 'Midwest',
        'states': ['IL', 'IN', 'IA', 'MI', 'MN', 'MO', 'ND', 'NE', 'OH', 'SD', 'WI'],
        'prefixes': ['43', '44', '45', '46', '47', '48', '49', '50', '51', '52', '53', '54', '55', '56', '57', '58', '60', '61', '62', '63', '64', '65', '66', '67', '68']
    },
    'south': {
        'name': 'South',
        'states': ['AR', 'LA', 'OK', 'TX'],
        'prefixes': ['70', '71', '72', '73', '74', '75', '76', '77', '78', '79']
    },
    'west': {
        'name': 'West',
        'states': ['AZ', 'CA', 'CO', 'ID', 'KS', 'MT', 'NV', 'NM', 'OR', 'UT', 'WA', 'WY'],
        'prefixes': ['80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95', '96', '97', '98', '99']
    }
}

def simplify_geometry(gdf, tolerance=0.01):
    """Simplify geometries to reduce file size."""
    gdf_projected = gdf.to_crs('EPSG:3857')
    gdf_projected['geometry'] = gdf_projected.geometry.simplify(tolerance=tolerance)
    return gdf_projected.to_crs('EPSG:4326')

def process_regional_zctas():
    """Process ZIP codes by region."""
    print("\n=== Processing Regional ZIP Codes ===")
    
    # Load ZCTA file
    zcta_files = list(DATA_DIR.glob("*zcta*.zip")) + list(DATA_DIR.glob("*zcta*.parquet"))
    if not zcta_files:
        print("No ZCTA files found. Please run generate_complete_zctas.py first.")
        return
    
    zcta_file = zcta_files[0]
    print(f"  Loading from {zcta_file.name}")
    
    # Load the data
    if zcta_file.suffix == '.parquet':
        gdf = gpd.read_parquet(zcta_file)
    else:
        gdf = gpd.read_file(f"zip://{zcta_file}")
    
    # Get ZCTA column name
    if 'ZCTA5CE20' in gdf.columns:
        zcta_col = 'ZCTA5CE20'
    elif 'GEOID20' in gdf.columns:
        zcta_col = 'GEOID20'
    else:
        print("ERROR: No ZCTA column found")
        return
    
    print(f"  Total ZCTAs loaded: {len(gdf)}")
    
    # Process each region
    for region_key, region_info in REGIONS.items():
        print(f"\n  Processing {region_info['name']} region...")
        
        # Filter ZCTAs for this region
        region_gdf = gdf[gdf[zcta_col].str[:2].isin(region_info['prefixes'])].copy()
        
        if len(region_gdf) == 0:
            print(f"    No ZCTAs found for {region_info['name']}")
            continue
        
        print(f"    Found {len(region_gdf)} ZCTAs")
        
        # Simplify geometry (moderate simplification for regional files)
        region_gdf = simplify_geometry(region_gdf, tolerance=200)
        
        # Keep minimal columns
        region_gdf = region_gdf[[zcta_col, 'geometry']]
        region_gdf.columns = ['ZCTA', 'geometry']
        
        # Convert to GeoJSON
        geojson = json.loads(region_gdf.to_json())
        
        # Add ID field for each feature
        for feature in geojson['features']:
            if 'ZCTA' in feature['properties']:
                feature['id'] = feature['properties']['ZCTA']
        
        # Save to file
        output_file = OUTPUT_DIR / f"zctas_{region_key}.json"
        with open(output_file, 'w') as f:
            json.dump(geojson, f, separators=(',', ':'))
        
        file_size = output_file.stat().st_size / 1024
        if file_size > 1024:
            print(f"    ✓ Saved zctas_{region_key}.json ({file_size/1024:.1f} MB)")
        else:
            print(f"    ✓ Saved zctas_{region_key}.json ({file_size:.1f} KB)")
    
    # Also create individual state files for commonly used states
    print("\n  Creating individual state ZIP files...")
    important_states = {
        'FL': '32|33|34',
        'TX': '75|76|77|78|79',
        'CA': '90|91|92|93|94|95|96',
        'NY': '10|11|12|13|14'
    }
    
    for state_code, prefixes in important_states.items():
        state_gdf = gdf[gdf[zcta_col].str[:2].str.match(f'^({prefixes})$')].copy()
        
        if len(state_gdf) > 0:
            # Higher quality for individual states (less simplification)
            state_gdf = simplify_geometry(state_gdf, tolerance=100)
            state_gdf = state_gdf[[zcta_col, 'geometry']]
            state_gdf.columns = ['ZCTA', 'geometry']
            
            geojson = json.loads(state_gdf.to_json())
            for feature in geojson['features']:
                if 'ZCTA' in feature['properties']:
                    feature['id'] = feature['properties']['ZCTA']
            
            output_file = OUTPUT_DIR / f"zctas_{state_code.lower()}.json"
            with open(output_file, 'w') as f:
                json.dump(geojson, f, separators=(',', ':'))
            
            file_size = output_file.stat().st_size / 1024
            if file_size > 1024:
                print(f"    ✓ {state_code}: {len(state_gdf)} ZIPs ({file_size/1024:.1f} MB)")
            else:
                print(f"    ✓ {state_code}: {len(state_gdf)} ZIPs ({file_size:.1f} KB)")

def create_metadata():
    """Create metadata file for regional boundaries."""
    print("\n=== Creating Metadata ===")
    
    metadata = {
        "generated": "2025-09-26",
        "description": "Regional ZIP code boundaries for better performance",
        "boundaries": {}
    }
    
    # Add regional files
    for region_key, region_info in REGIONS.items():
        filepath = OUTPUT_DIR / f"zctas_{region_key}.json"
        if filepath.exists():
            size_kb = filepath.stat().st_size / 1024
            metadata["boundaries"][f"zctas_{region_key}"] = {
                "file": f"zctas_{region_key}.json",
                "name": f"{region_info['name']} ZIP Codes",
                "level": "zcta",
                "size_kb": round(size_kb, 1),
                "id_field": "ZCTA",
                "join_fields": ["ZCTA"],
                "states": region_info['states']
            }
    
    # Add state files
    state_names = {
        'fl': 'Florida',
        'tx': 'Texas', 
        'ca': 'California',
        'ny': 'New York'
    }
    
    for state_code, state_name in state_names.items():
        filepath = OUTPUT_DIR / f"zctas_{state_code}.json"
        if filepath.exists():
            size_kb = filepath.stat().st_size / 1024
            metadata["boundaries"][f"zctas_{state_code}"] = {
                "file": f"zctas_{state_code}.json",
                "name": f"{state_name} ZIP Codes",
                "level": "zcta",
                "size_kb": round(size_kb, 1),
                "id_field": "ZCTA",
                "join_fields": ["ZCTA"]
            }
    
    output_file = OUTPUT_DIR / "metadata.json"
    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"  Saved metadata.json")

def main():
    """Generate regional ZCTA boundary files."""
    print("Generating Regional ZIP Code Boundaries")
    print("=" * 50)
    print(f"Data directory: {DATA_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    
    process_regional_zctas()
    create_metadata()
    
    print("\n" + "=" * 50)
    print("Regional ZIP code generation complete!")
    print(f"Files saved to: {OUTPUT_DIR}")
    
    # Show summary
    if OUTPUT_DIR.exists():
        json_files = list(OUTPUT_DIR.glob("*.json"))
        if json_files:
            total_size = sum(f.stat().st_size for f in json_files) / 1024 / 1024
            print(f"\nTotal size: {total_size:.1f} MB")
            print(f"Files created: {len(json_files)}")
            print("\n✅ ZIP codes split into manageable regional files!")

if __name__ == "__main__":
    import pandas as pd
    main()