const STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','DC','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','PR','GU','VI','AS','MP'
];
const el = (id)=>document.getElementById(id);
let localAPI = null, result = null;
let map = null, layer = null;
// Hosted boundaries for browser-only flow (Florida coverage)
const HOSTED = {
  FL: {
    state: 'data/fl_state_simple.geojson',
    county: 'data/fl_county_simple.geojson',
    subcounty: 'data/fl_subcounty_simple.geojson',
    place: 'data/fl_place_simple.geojson',
    zcta: 'data/fl_zcta_simple.geojson'
  }
};

async function detect() {
  const bases = ['http://127.0.0.1:8765','http://localhost:8765'];
  const holder = el('engine');
  for (const b of bases) {
    try { const r = await fetch(b+'/health', {cache:'no-store'}); if (r.ok) { localAPI={base:b}; holder.textContent='Local Engine: Connected'; return; } } catch {}
  }
  holder.textContent = 'Local Engine: Not connected. Start it for one-click maps.';
}
detect();

// Populate state select
const state = el('state');
state.innerHTML = STATES.map(s=>`<option value="${s}">${s}</option>`).join('');
state.value = 'FL';

// Dropzone behavior
const dz = el('dz');
const fileInput = el('csv');
function setFile(f){ if(!f) return; const lbl=el('dzLabel'); lbl.textContent = `Selected: ${f.name}`; }
dz.addEventListener('click', ()=> fileInput.click());
dz.addEventListener('dragover', (e)=>{ e.preventDefault(); dz.classList.add('hover'); });
dz.addEventListener('dragleave', ()=> dz.classList.remove('hover'));
dz.addEventListener('drop', (e)=>{ e.preventDefault(); dz.classList.remove('hover'); const f=e.dataTransfer.files[0]; if(f){ fileInput.files = e.dataTransfer.files; setFile(f);} });
fileInput.addEventListener('change', ()=>{ const f=fileInput.files[0]; if(f) setFile(f); });

el('go').addEventListener('click', async ()=>{
  const f = el('csv').files[0];
  const st = state.value;
  const level = el('level').value;
  const msg = el('msg');
  if (!f) { msg.textContent='Please choose a CSV file.'; return; }
  if (!localAPI) {
    const byState = HOSTED[st];
    const url = byState && byState[level];
    if (!url) { msg.textContent='Browser-only mode: this State/Area is not yet hosted. Use the Local App (one click) or pick another area.'; return; }
    try {
      msg.textContent = 'Loading boundary…';
      const resp = await fetch(url, { cache: 'no-store' });
      const gj = await resp.json();
      msg.textContent = 'Processing CSV…';
      const text = await el('csv').files[0].text();
      const rows = parseCSV(text);
      msg.textContent = 'Joining…';
      const { geojson } = joinFeatures(gj, rows, level, st);
      result = geojson;
      msg.textContent = 'Map ready.';
      el('after').style.display='block';
      document.getElementById('previewBtn').disabled = false;
      renderPreview();
      return;
    } catch (e) {
      msg.textContent = 'Error (browser mode): ' + (e?.message||String(e));
      return;
    }
  }
  try {
    msg.textContent = 'Building your map…';
    const fd = new FormData();
    fd.append('state', st);
    fd.append('level', level);
    // Simplify option
    const simpOn = document.getElementById('simplifyChk').checked;
    const tol = parseFloat(document.getElementById('simplifyTol').value || '0');
    if (simpOn && tol > 0) fd.append('simplify', String(tol));
    fd.append('csv', f);
    const r = await fetch(localAPI.base+'/join', { method:'POST', body:fd });
    if (!r.ok) throw new Error('Join failed');
    result = await r.json();
    msg.textContent = 'Map ready.';
    el('after').style.display='block';
    // Enable preview button unless too large
    const featCount = (result && result.features) ? result.features.length : 0;
    const btn = document.getElementById('previewBtn');
    const note = document.getElementById('previewNote');
    btn.disabled = false;
    if (featCount > 8000) {
      note.textContent = `Large layer (${featCount} features). Preview may be slow.`;
    } else {
      note.textContent = '';
      // Auto-preview for smaller layers
      renderPreview();
    }
  } catch (e) {
    msg.textContent = 'Error: ' + (e?.message||String(e));
  }
});

el('download').addEventListener('click', ()=>{
  if (!result) return;
  const name = `${el('state').value}_${el('level').value}_joined.geojson`;
  const blob = new Blob([JSON.stringify(result)], {type:'application/geo+json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url);
});

document.getElementById('previewBtn').addEventListener('click', ()=>{
  renderPreview();
});

function renderPreview(){
  if (!result) return;
  const mapEl = document.getElementById('map');
  mapEl.style.display = 'block';
  if (!map) {
    map = L.map('map');
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18, attribution: '&copy; OpenStreetMap'
    }).addTo(map);
  }
  if (layer) { layer.remove(); }
  const { styleFn, legend } = styleFor(result);
  layer = L.geoJSON(result, { style: styleFn, onEachFeature: (f, l)=>{
    const p = f.properties||{};
    const name = p['GEO display_label']||p['NAME']||p['NAMELSAD']||p['ZCTA5CE10']||p['ZCTA5CE20']||'';
    const hh = p['Households'];
    const below = p['Below_ALICE_Rate'];
    const pr = p['Poverty_Rate'];
    const ar = p['ALICE_Rate'];
    const fmt = n => (n==null||isNaN(n))?'-':(Math.round(n*1000)/10)+'%';
    l.bindTooltip(`<b>${name}</b><br>`+
      (below!=null?`Below ALICE: ${fmt(below)}<br>`:'')+
      (ar!=null?`ALICE: ${fmt(ar)}<br>`:'')+
      (pr!=null?`Poverty: ${fmt(pr)}<br>`:'')+
      (hh!=null?`Households: ${hh}`:''));
  }}).addTo(map);
  try { map.fitBounds(layer.getBounds(), { padding: [20,20] }); } catch {}
  // Legend
  addLegend(legend);
}

function styleFor(gj){
  const feats = gj.features||[];
  const getVals = key => feats.map(f=>f.properties?.[key]).filter(v=>typeof v==='number' && !isNaN(v));
  let key = null;
  for (const k of ['Below_ALICE_Rate','ALICE_Rate','Poverty_Rate']) { if (getVals(k).length>0){ key=k; break; } }
  if (!key) return { styleFn: ()=>({ color:'#3da9fc', weight:1, fillOpacity:0.2 }), legend: null };
  const vals = getVals(key);
  vals.sort((a,b)=>a-b);
  const q = n => vals.length? vals[Math.floor((n)*(vals.length-1))] : 0;
  const breaks = [q(0.05), q(0.25), q(0.5), q(0.75), q(0.95)];
  const colors = ['#f2f0f7','#cbc9e2','#9e9ac8','#756bb1','#54278f'];
  const colorFor = v => v==null? '#ddd' : (v<=breaks[0]?colors[0]: v<=breaks[1]?colors[1]: v<=breaks[2]?colors[2]: v<=breaks[3]?colors[3]: colors[4]);
  const styleFn = f => ({ color:'#333', weight:0.6, fillColor: colorFor(f.properties?.[key]), fillOpacity:0.8 });
  return { styleFn, legend: { key, breaks, colors } };
}

let legendControl = null;
function addLegend(legend){
  if (legendControl) { legendControl.remove(); legendControl=null; }
  if (!legend) return;
  const { key, breaks, colors } = legend;
  legendControl = L.control({position:'bottomright'});
  legendControl.onAdd = function(){
    const div = L.DomUtil.create('div','legend');
    div.style.background = 'rgba(20,24,32,0.9)';
    div.style.color = '#e7edf3';
    div.style.padding = '8px 10px';
    div.style.borderRadius = '8px';
    div.style.fontSize = '12px';
    div.innerHTML = `<b>${key}</b><br>` + breaks.map((b,i)=>{
      const label = Math.round(b*1000)/10 + '%';
      return `<span style="display:inline-block;width:10px;height:10px;background:${colors[i]};margin-right:6px"></span>${label}`;
    }).join('<br>');
    return div;
  };
  legendControl.addTo(map);
}
