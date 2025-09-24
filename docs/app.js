function setStatus(msg) {
  document.getElementById('status').textContent = msg || '';
}

// Minimal CSV parser handling commas and quotes
function parseCSV(text) {
  const rows = [];
  let i = 0, field = '', row = [], inQuotes = false;
  while (i < text.length) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i += 2; continue; } // escaped quote
        inQuotes = false; i++; continue;
      }
      field += c; i++; continue;
    }
    if (c === '"') { inQuotes = true; i++; continue; }
    if (c === ',') { row.push(field); field = ''; i++; continue; }
    if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; i++; continue; }
    if (c === '\r') { i++; continue; }
    field += c; i++;
  }
  // Last field
  row.push(field);
  // Append last row if any non-empty
  if (row.length > 1 || row[0] !== '') rows.push(row);
  // Header mapping
  const header = rows.shift() || [];
  const trimmed = header.map(h => h.replace(/^\uFEFF/, '').trim());
  return rows.map(r => Object.fromEntries(trimmed.map((h, idx) => [h, r[idx] ?? ''])));
}

function normalizeZip(s) { return (String(s || '').match(/\d+/) || [''])[0].padStart(5, '0'); }
function pad(s, n) { return String(s || '').padStart(n, '0'); }

function computeMetrics(rec) {
  const hh = +rec['Households'] || 0;
  const pov = +rec['Poverty Households'] || 0;
  const alice = +rec['ALICE Households'] || 0;
  const below = pov + alice;
  return {
    Below_ALICE_Rate: hh > 0 ? below / hh : null,
    Poverty_Rate: hh > 0 ? pov / hh : null,
    ALICE_Rate: hh > 0 ? alice / hh : null,
  };
}

async function readFileAsText(file) {
  return new Promise((res, rej) => {
    const fr = new FileReader();
    fr.onerror = () => rej(fr.error);
    fr.onload = () => res(String(fr.result));
    fr.readAsText(file);
  });
}

async function readJSON(file) {
  const txt = await readFileAsText(file);
  return JSON.parse(txt);
}

function joinFeatures(geojson, dataRows, level, state) {
  const feats = geojson.features || [];
  // Build index from CSV
  let idx = new Map();
  if (level === 'place') {
    for (const r of dataRows) idx.set(pad(r['GEOID'], 7), r);
  } else if (level === 'subcounty') {
    for (const r of dataRows) idx.set(pad(r['GEOID'], 10), r);
  } else {
    for (const r of dataRows) idx.set(normalizeZip(r['ZIP'] ?? r['ZCTA'] ?? r['ZCTA5']), r);
  }

  let matched = 0;
  for (const f of feats) {
    const p = f.properties || (f.properties = {});
    let key = null;
    if (level === 'place') key = pad(p['GEOID'], 7);
    else if (level === 'subcounty') key = pad(p['GEOID'], 10);
    else key = normalizeZip(p['GEOID20'] ?? p['ZCTA5CE20'] ?? p['GEOID10'] ?? p['ZCTA5CE10']);

    const rec = key ? idx.get(key) : undefined;
    if (rec) {
      matched++;
      // copy fields (avoid overwriting geometry-related fields)
      for (const [k, v] of Object.entries(rec)) {
        if (k === '' || k === 'geometry') continue;
        p[k] = v;
      }
      const m = computeMetrics(rec);
      p['Below_ALICE_Rate'] = m.Below_ALICE_Rate;
      p['Poverty_Rate'] = m.Poverty_Rate;
      p['ALICE_Rate'] = m.ALICE_Rate;
    }
  }
  return { geojson, matched, total: feats.length };
}

function download(filename, text) {
  const blob = new Blob([text], { type: 'application/geo+json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

document.getElementById('joinBtn').addEventListener('click', async () => {
  try {
    const boundaryFile = document.getElementById('boundaryFile').files[0];
    const dataFile = document.getElementById('dataFile').files[0];
    const level = document.getElementById('level').value;
    const state = (document.getElementById('state').value || '').toUpperCase();
    if (!boundaryFile || !dataFile) { setStatus('Please select both files.'); return; }

    setStatus('Reading boundary...');
    const gj = await readJSON(boundaryFile);

    setStatus('Parsing CSV...');
    const csvText = await readFileAsText(dataFile);
    const rows = parseCSV(csvText);

    setStatus('Joining...');
    const { geojson, matched, total } = joinFeatures(gj, rows, level, state);
    setStatus(`Joined ${matched} of ${total} features. Preparing download...`);

    const outName = `${(state||'US')}_${level}_joined.geojson`;
    download(outName, JSON.stringify(geojson));
    setStatus(`Done. Downloaded ${outName}.`);
  } catch (e) {
    console.error(e);
    setStatus('Error: ' + (e && e.message ? e.message : String(e)));
  }
});

