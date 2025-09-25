const STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','DC','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','PR','GU','VI','AS','MP'
];
const el = (id)=>document.getElementById(id);
let localAPI = null, result = null;

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
  if (!localAPI) { msg.textContent='Local Engine not connected. Please start it (see START_HERE).'; return; }
  try {
    msg.textContent = 'Building your map…';
    const fd = new FormData();
    fd.append('state', st);
    fd.append('level', level);
    fd.append('csv', f);
    const r = await fetch(localAPI.base+'/join', { method:'POST', body:fd });
    if (!r.ok) throw new Error('Join failed');
    result = await r.json();
    msg.textContent = 'Map ready.';
    el('after').style.display='block';
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
