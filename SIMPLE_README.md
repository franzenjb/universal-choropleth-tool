# Free Choropleth Map Maker

## What This Does
Turns any CSV file with geographic data (ZIP codes, counties, etc.) into a choropleth map file - **completely free, no GIS software needed**.

## The Problem It Solves
- **Traditional way**: Need expensive ArcGIS Pro ($100s/year) or ArcGIS Online (costs credits)
- **Technical barrier**: Complex JOIN operations that require GIS expertise
- **This tool**: Free, simple, works in your browser

## How It Works
1. **Upload** your CSV (must have a column with ZIP codes, county names, etc.)
2. **Select** your state and geography type
3. **Download** a GeoJSON file ready for any mapping software

## Quick Start (Easiest Way)
1. Double-click `Start Local App.command`
2. Your browser opens automatically
3. Upload CSV → Select State → Choose Geography → Download Map

## What You Get
A GeoJSON file that:
- Works in ArcGIS Online (no credits needed!)
- Opens in QGIS (free software)
- Imports into Tableau, PowerBI, etc.
- Contains all your data joined to official Census boundaries

## Examples of Data You Can Map
- Sales by ZIP code
- Population by county  
- Health data by census tract
- School districts data
- Any data with geographic identifiers!

## Technical Details (If You Care)
- Uses official Census TIGER/Cartographic boundaries
- Joins your data using standard geographic identifiers (FIPS codes, GEOIDs, etc.)
- Simplifies geometry for smaller file sizes
- Works offline once boundaries are cached

## No Strings Attached
- No signup required
- No credits or payments
- No data uploaded to any server (runs locally)
- Open source - modify as needed

## Geography Types Supported
- **ZIP Codes** (technically ZCTAs - ZIP Code Tabulation Areas)
- **Counties** 
- **Cities/Towns** (Census Places)
- **County Subdivisions** (Townships, MCDs, CCDs)
- **Census Tracts**
- **Block Groups**
- **States**

---
*This tool democratizes GIS - making professional choropleth maps accessible to everyone, not just those with expensive software.*