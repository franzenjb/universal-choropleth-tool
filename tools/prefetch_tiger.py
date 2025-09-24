#!/usr/bin/env python3
import argparse
import os
from typing import List

import requests

from alice_choropleth import (
    place_url,
    zcta_urls,
    cousub_url,
    state_us_url,
    county_us_url,
    tract_url,
    bg_url,
    STATE_ABBR_TO_FIPS,
)


def download(url: str, dest_dir: str, insecure: bool = False, max_retries: int = 6, retry_wait: float = 2.0) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    fn = os.path.basename(url)
    out = os.path.join(dest_dir, fn)
    if os.path.exists(out):
        print(f"cached: {fn}")
        return out
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(url, timeout=120, verify=(not insecure))
            if r.status_code in (429, 500, 502, 503, 504):
                raise RuntimeError(f"HTTP {r.status_code}")
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            with open(out, 'wb') as f:
                f.write(r.content)
            print(f"downloaded: {fn}")
            break
        except Exception as e:
            last_err = e
            if attempt == max_retries:
                raise RuntimeError(f"failed after {attempt} tries: {url}: {last_err}")
            import time
            time.sleep(retry_wait * (2 ** (attempt - 1)))
    return out


def resolve_first_available(urls: List[str], insecure: bool = False, max_retries: int = 6, retry_wait: float = 2.0) -> str:
    for u in urls:
        for attempt in range(1, max_retries + 1):
            try:
                h = requests.head(u, allow_redirects=True, timeout=30, verify=(not insecure))
                if h.ok:
                    return u
            except Exception:
                pass
            if attempt < max_retries:
                import time
                time.sleep(retry_wait * (2 ** (attempt - 1)))
    raise RuntimeError(f"No available URL among: {urls}")


def parse_args():
    p = argparse.ArgumentParser(description="Prefetch TIGER/Cartographic boundary zips for caching")
    p.add_argument('--cache-dir', required=True, help='Directory to store downloaded TIGER zips')
    p.add_argument('--insecure', action='store_true', help='Disable TLS verification for downloads')
    p.add_argument('--states', help='Comma-separated STUSPS or FIPS; default ALL including territories')
    p.add_argument('--max-retries', type=int, default=6, help='Max HTTP retries per file (default 6)')
    p.add_argument('--retry-wait', type=float, default=2.0, help='Base seconds for exponential backoff (default 2.0)')
    p.add_argument('--until-complete', action='store_true', help='Loop passes until all files are cached')
    p.add_argument('--no-cousub', action='store_true', help='Skip county subdivisions downloads')
    p.add_argument('--no-tracts', action='store_true', help='Skip census tracts downloads')
    p.add_argument('--bg-states', help='Comma-separated STUSPS or FIPS to download block groups for (e.g., FL,GA,SC)')
    return p.parse_args()


def main() -> int:
    args = parse_args()
    dest = args.cache_dir
    insecure = args.insecure or bool(os.environ.get('ALICE_INSECURE'))
    max_retries = args.max_retries
    retry_wait = args.retry_wait

    # Determine target states/territories
    if args.states:
        tokens = [t.strip() for t in args.states.split(',') if t.strip()]
        stusps = []
        for t in tokens:
            if len(t) == 2 and t.upper() in STATE_ABBR_TO_FIPS:
                stusps.append(t.upper())
            elif len(t) == 2 and t.isdigit():
                # FIPS provided as 2-digit string
                # map back to STUSPS if possible; otherwise keep FIPS for cousub url
                found = [k for k, v in STATE_ABBR_TO_FIPS.items() if v == t]
                stusps.append(found[0] if found else t)
            else:
                raise SystemExit(f"Unrecognized state token: {t}")
    else:
        stusps = list(STATE_ABBR_TO_FIPS.keys())

    # National layers
    download(place_url(), dest, insecure=insecure, max_retries=max_retries, retry_wait=retry_wait)
    zcta_url = resolve_first_available(zcta_urls(), insecure=insecure, max_retries=max_retries, retry_wait=retry_wait)
    download(zcta_url, dest, insecure=insecure, max_retries=max_retries, retry_wait=retry_wait)
    # States and counties national files
    download(state_us_url(), dest, insecure=insecure, max_retries=max_retries, retry_wait=retry_wait)
    download(county_us_url(), dest, insecure=insecure, max_retries=max_retries, retry_wait=retry_wait)

    # Per-state county subdivisions (may 404 for some territories; skip those)
    def pending_urls():
        urls = []
        for st in stusps:
            fips = STATE_ABBR_TO_FIPS.get(st, st)
            if not args.no_cousub:
                url = cousub_url(fips)
                if not os.path.exists(os.path.join(dest, os.path.basename(url))):
                    urls.append((st, fips, url))
            if not args.no_tracts:
                # Per-state tracts (may 404 for some territories; handled below)
                turl = tract_url(fips)
                if not os.path.exists(os.path.join(dest, os.path.basename(turl))):
                    urls.append((st, fips, turl))
        return urls

    # Initial pass
    for st, fips, url in pending_urls():
        try:
            download(url, dest, insecure=insecure, max_retries=max_retries, retry_wait=retry_wait)
        except Exception as e:
            print(f"defer {st} ({fips}): {e}")

    # Optional: Block groups for selected states
    if args.bg_states:
        tokens = [t.strip() for t in args.bg_states.split(',') if t.strip()]
        for t in tokens:
            st = t.upper()
            fips = STATE_ABBR_TO_FIPS.get(st, st)
            burl = bg_url(fips)
            try:
                download(burl, dest, insecure=insecure, max_retries=max_retries, retry_wait=retry_wait)
            except Exception as e:
                print(f"defer BG {st} ({fips}): {e}")

    # Loop until complete if requested
    if args.until_complete:
        import time
        round_num = 1
        while True:
            pend = pending_urls()
            if not pend:
                break
            print(f"Round {round_num}: retrying {len(pend)} remaining files...")
            for st, fips, url in pend:
                try:
                    download(url, dest, insecure=insecure, max_retries=max_retries, retry_wait=retry_wait)
                except Exception as e:
                    print(f"defer {st} ({fips}): {e}")
            round_num += 1
            time.sleep(retry_wait * 5)

    print(f"Done. Cached files in {dest}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
