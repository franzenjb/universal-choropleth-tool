Volunteer Test Plan (30 minutes)

Purpose
- Validate that a Red Cross volunteer can make a choropleth without training.
- Identify points of confusion and make copy/flow fixes.

Setup
- Ask the volunteer to use a laptop + Chrome/Edge.
- Ensure Local Engine is running: double‑click “Start Local Engine.command”.
- Open Quick Map: https://franzenjb.github.io/alice-choropleth-tool/quick.html

Script (Think‑aloud)
1) “Please make a ZIP map for Florida with this CSV.” (provide file)
   - Observe: CSV drop, state FL, area ZIP, click Create, preview, download.
2) “Please make a county‑subdivision map for Georgia with this CSV.”
3) “Upload the GeoJSON to ArcGIS Online and style by Below_ALICE_Rate.”

Measures
- Time to first map (mm:ss)
- Success without assistance (Y/N)
- Error count (blocking/non‑blocking)
- SUS (System Usability Scale) after test

Notes to capture
- Where did they pause? What text did they read or ignore?
- Any confusion on ZIP vs ZCTA? Did the helper text suffice?
- Was the preview helpful? Any performance concerns?

Exit questions
- What would you rename/change on this screen?
- What felt unnecessary or confusing?
- Would you feel comfortable doing this again without support?

Acceptance Criteria (v1)
- ≥90% complete Task 1 and 2 within 2 minutes each.
- 0 blocking errors.
- Median SUS ≥80.
