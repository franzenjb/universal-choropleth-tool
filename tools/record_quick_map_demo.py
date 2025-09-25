#!/usr/bin/env python3
"""
Record a short demo of using the local Quick Map app with Playwright.

Prereqs:
  - Local Engine/App running at http://127.0.0.1:8765/app/quick.html
  - pip install playwright && python -m playwright install chromium

Usage:
  python tools/record_quick_map_demo.py \
     --csv "/Users/jefffranzen/Desktop/Alice Florida Data/ALICE - Florida Sub_County Data.csv" \
     --state FL --level subcounty --out out/quickmap-demo.webm
"""
import argparse
import os
from playwright.sync_api import sync_playwright


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True, help='Path to a CSV to demo')
    ap.add_argument('--state', default='FL')
    ap.add_argument('--level', default='subcounty', choices=['state','county','subcounty','place','zcta','tract'])
    ap.add_argument('--out', default='out/quickmap-demo.webm')
    ap.add_argument('--url', default='http://127.0.0.1:8765/app/quick.html')
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(record_video_dir=os.path.dirname(args.out), record_video_size={"width":1280, "height":800})
        page = context.new_page()
        page.goto(args.url, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(800)
        # Upload CSV
        page.set_input_files('#csv', args.csv)
        # Select state and level
        page.select_option('#state', args.state)
        page.select_option('#level', args.level)
        # Turn on simplify for speed
        page.check('#simplifyChk')
        # Click Create
        page.click('#go')
        page.wait_for_timeout(2500)
        # Show preview
        try:
            page.click('#previewBtn')
            page.wait_for_selector('#map', timeout=10000)
            page.wait_for_timeout(1500)
        except Exception:
            pass
        # Download
        page.click('#download')
        page.wait_for_timeout(1200)
        # Ensure video saved as requested name
        video_path = page.video.path()
        page.close()
        context.close()
        browser.close()
        if os.path.exists(video_path):
            os.replace(video_path, args.out)
            print('Wrote', args.out)
        else:
            print('Video at', video_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

