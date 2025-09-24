#!/usr/bin/env python3
import argparse
import glob
import os
from typing import Iterable

import geopandas as gpd


def to_parquet(zip_path: str, out_dir: str) -> str:
    base = os.path.basename(zip_path)
    name = os.path.splitext(base)[0] + ".parquet"
    out_path = os.path.join(out_dir, name)
    if os.path.exists(out_path):
        print(f"parquet cached: {name}")
        return out_path
    ds = f"zip://{zip_path}"
    gdf = gpd.read_file(ds)
    os.makedirs(out_dir, exist_ok=True)
    gdf.to_parquet(out_path)
    print(f"wrote: {name} ({len(gdf)} features)")
    return out_path


def iter_known_layers(cache_dir: str) -> Iterable[str]:
    # National layers we expect
    for pat in [
        "cb_2023_us_place_500k.zip",
        "cb_2023_us_state_500k.zip",
        "cb_2023_us_county_500k.zip",
        "cb_2020_us_zcta520_500k.zip",
    ]:
        p = os.path.join(cache_dir, pat)
        if os.path.exists(p):
            yield p

    # Per-state families present in cache
    for fam in ["*_cousub_500k.zip", "*_tract_500k.zip", "*_bg_500k.zip"]:
        for p in glob.glob(os.path.join(cache_dir, fam)):
            yield p


def parse_args():
    ap = argparse.ArgumentParser(description="Convert cached TIGER ZIPs to GeoParquet")
    ap.add_argument('--cache-dir', required=True, help='Cache directory with TIGER ZIPs')
    ap.add_argument('--out-dir', help='Output directory for parquet (default <cache>/parquet)')
    ap.add_argument('--glob', help='Optional glob to limit files (e.g., "*_bg_500k.zip")')
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    cache_dir = args.cache_dir
    out_dir = args.out_dir or os.path.join(cache_dir, 'parquet')

    if args.glob:
        paths = glob.glob(os.path.join(cache_dir, args.glob))
    else:
        paths = list(dict.fromkeys(iter_known_layers(cache_dir)))

    if not paths:
        print("No matching ZIPs found to convert.")
        return 0

    for p in paths:
        try:
            to_parquet(p, out_dir)
        except Exception as e:
            print(f"skip {os.path.basename(p)}: {e}")
    print(f"Done. Parquet in {out_dir}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

