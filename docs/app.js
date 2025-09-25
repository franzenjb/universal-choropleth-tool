function setStatus(msg) {
  // no-op in wizard version
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

// Wizard logic injected below
const STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','DC','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','PR','GU','VI','AS','MP'
];

const PROVIDED = {
  FL: {
    subcounty: { label: 'Florida County‑Subdivisions (simplified)', path: 'data/fl_subcounty_simple.geojson' }
  }
};

const el = (id) => document.getElementById(id);
const stepEls = [el('step1'), el('step2'), el('step3'), el('step4'), el('step5')];
let csvRows = [], statePick = '', levelPick = '', boundaryGeoJSON = null, joinedGeoJSON = null, lastMatch = {matched:0,total:0};

function showStep(n) { stepEls.forEach((s,i)=>s.classList.toggle('active', i===n-1)); }

// Step 1: CSV upload
el('csvFile').addEventListener('change', async (e) => {
  const f = e.target.files[0];
  el('csvInfo').textContent = f ? `Selected: ${f.name}` : '';
  if (!f) { el('toStep2').disabled = true; return; }
  const txt = await readFileAsText(f);
  csvRows = parseCSV(txt);
  const cols = Object.keys(csvRows[0]||{});
  const states = new Set(csvRows.map(r => String(r.State||r.state||'').trim().toUpperCase()).filter(Boolean));
  const guess = [...states].find(s=>STATES.includes(s));
  el('csvInfo').textContent = `Columns: ${cols.join(', ').slice(0,120)}${cols.length>15?'…':''}` + (guess?`\nDetected state: ${guess}`:'');
  el('toStep2').disabled = false;
});
el('toStep2').addEventListener('click', () => { showStep(2); });

// Step 2: State select
const stateSelect = el('stateSelect');
stateSelect.innerHTML = STATES.map(s=>`<option value="${s}">${s}</option>`).join('');
el('stateSelect').addEventListener('change', (e)=>{ statePick = e.target.value; el('stateInfo').textContent = `Selected: ${statePick}`; });
function preselectState() {
  const states = new Set(csvRows.map(r => String(r.State||r.state||'').trim().toUpperCase()).filter(Boolean));
  const guess = [...states].find(s=>STATES.includes(s));
  stateSelect.value = guess || 'FL';
  statePick = stateSelect.value;
  el('stateInfo').textContent = `Selected: ${statePick}`;
}
preselectState();
el('toStep3').addEventListener('click', ()=>{ if (!statePick) preselectState(); showStep(3); });
el('step2').addEventListener('click', (e)=>{ if (e.target.classList.contains('back')) showStep(parseInt(e.target.dataset.back,10)); });

// Step 3: Level selection
const cards = el('levelCards').querySelectorAll('.card');
cards.forEach(c=>c.addEventListener('click',()=>{
  cards.forEach(x=>x.classList.remove('selected'));
  c.classList.add('selected');
  levelPick = c.dataset.level;
  el('toStep4').disabled = false;
}));
el('toStep4').addEventListener('click', ()=>{ renderProvidedList(); showStep(4); });
el('step3').addEventListener('click', (e)=>{ if (e.target.classList.contains('back')) showStep(parseInt(e.target.dataset.back,10)); });

// Step 4: Boundary choice
const providedList = el('providedList');
const boundaryFileInput = el('boundaryFile');
document.querySelectorAll('input[name="bmode"]').forEach(r=>{
  r.addEventListener('change', ()=>{
    const up = document.querySelector('input[name="bmode"]:checked').value === 'upload';
    boundaryFileInput.disabled = !up;
    validateBoundaryChoice();
  });
});

function renderProvidedList() {
  providedList.innerHTML = '';
  const entry = (PROVIDED[statePick]||{})[levelPick];
  if (!entry) {
    providedList.innerHTML = '<div class="info">No built‑in boundary for this selection yet. Choose “Upload my own”.</div>';
    return;
  }
  const row = document.createElement('label');
  row.className = 'opt';
  row.innerHTML = `<input type=\"radio\" name=\"prov\" value=\"${entry.path}\" checked> <span>${entry.label}</span>`;
  providedList.appendChild(row);
  validateBoundaryChoice();
}

boundaryFileInput.addEventListener('change', ()=>{ validateBoundaryChoice(); });
function validateBoundaryChoice() {
  const mode = document.querySelector('input[name="bmode"]:checked').value;
  if (mode === 'upload') {
    el('boundaryInfo').textContent = boundaryFileInput.files[0] ? `Selected: ${boundaryFileInput.files[0].name}` : '';
    el('toStep5').disabled = !boundaryFileInput.files[0];
  } else {
    const picked = document.querySelector('input[name="prov"]:checked');
    el('toStep5').disabled = !picked;
    el('boundaryInfo').textContent = picked ? `Using provided boundary.` : '';
  }
}

el('toStep5').addEventListener('click', async ()=>{
  try {
    el('progress').textContent = 'Reading boundary…';
    const mode = document.querySelector('input[name="bmode"]:checked').value;
    if (mode === 'upload') {
      boundaryGeoJSON = await readJSON(boundaryFileInput.files[0]);
    } else {
      const picked = document.querySelector('input[name="prov"]:checked').value;
      const resp = await fetch(picked, { cache: 'no-store' });
      boundaryGeoJSON = await resp.json();
    }
    el('progress').textContent = 'Joining…';
    const { geojson, matched, total } = joinFeatures(boundaryGeoJSON, csvRows, levelPick, statePick);
    joinedGeoJSON = geojson; lastMatch = {matched,total};
    el('progress').textContent = `Matched ${matched} of ${total} areas.`;
    el('downloadBtn').disabled = false;
    showStep(5);
  } catch (err) {
    el('progress').textContent = 'Error preparing map: ' + (err?.message || String(err));
  }
});

el('downloadBtn').addEventListener('click', ()=>{
  if (!joinedGeoJSON) return;
  const outName = `${statePick||'US'}_${levelPick}_joined.geojson`;
  download(outName, JSON.stringify(joinedGeoJSON));
  el('resultInfo').textContent = `Downloaded ${outName}. Now upload to ArcGIS and color by “Below_ALICE_Rate”.`;
});
