/* ── PE Signal Engine — frontend ─────────────────────────────────────────── */

const API = '/api';  // proxied to FastAPI; change to 'http://localhost:8000' for dev

/* ── API helpers ─────────────────────────────────────────────────────────── */
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(API + path, opts);
  if (!r.ok) { const t = await r.text(); throw new Error(t); }
  const ct = r.headers.get('content-type') || '';
  return ct.includes('json') ? r.json() : r.text();
}
const get  = (p)    => api('GET', p);
const post = (p, b) => api('POST', p, b);
const patch = (p, b) => api('PATCH', p, b);

/* ── State ────────────────────────────────────────────────────────────────── */
const S = {
  view:         'search',
  executives:   [],
  runs:         [],
  sources:      [],
  rules:        [],
  sortCol:      'total_score',
  sortDir:      'desc',
  filterName:   '',
  filterLane:   '',
  filterRun:    '',
  filterContact:'',
  filterMinScore: 0,
  drawerExec:   null,
  drawerPanel:  'evidence',
  companies:    [],  // tag arrays for search form
  sectors:      [],
  countries:    ['Sweden', 'Norway', 'Denmark', 'Finland'],
  lane:         'both',
  templates:    JSON.parse(localStorage.getItem('pe_templates') || '[]'),
};

/* ── Nordic PE sectors — pre-seeded ─────────────────────────────────────── */
const SECTORS = [
  'Vertical SaaS', 'Behavioural Health & Outpatient Specialty',
  'Testing, Inspection & Certification', 'Environmental & Compliance Services',
  'Infrastructure-linked Field Services', 'IT Services (AI/Cloud/Cybersecurity)',
  'Revenue Cycle Management',
];

/* ── Nav ─────────────────────────────────────────────────────────────────── */
document.querySelectorAll('.nav-btn[data-view]').forEach(btn => {
  btn.addEventListener('click', () => switchView(btn.dataset.view));
});

function switchView(name) {
  S.view = name;
  document.querySelectorAll('.nav-btn[data-view]').forEach(b =>
    b.classList.toggle('active', b.dataset.view === name));
  document.querySelectorAll('.view').forEach(v =>
    v.classList.toggle('active', v.id === `view-${name}`));
  if (name === 'runs')   loadRuns();
  if (name === 'table')  loadExecutives();
  if (name === 'config') loadConfig();
}

/* ════════════════════════════════════════════════════════════════════════════
   SEARCH SETUP VIEW
══════════════════════════════════════════════════════════════════════════════ */
function initSearchSetup() {
  // Tag inputs
  makeTagInput('companies-input', 'companies-text', 'companies');
  makeTagInput('sectors-input',   'sectors-text',   'sectors');
  makeTagInput('countries-input', 'countries-text', 'countries');

  // Pre-fill sectors with Nordic PE focus
  S.sectors = [...SECTORS];
  renderTags('sectors-input', S.sectors);

  // Pre-fill countries
  renderTags('countries-input', S.countries);

  // Lane toggle
  document.querySelectorAll('#lane-toggle .toggle-opt').forEach(el => {
    el.addEventListener('click', () => {
      document.querySelectorAll('#lane-toggle .toggle-opt').forEach(x => x.classList.remove('on'));
      el.classList.add('on');
      S.lane = el.dataset.val;
    });
  });

  // Weight validation
  ['w-transition','w-pe-fit','w-network','w-reachability'].forEach(id => {
    document.getElementById(id).addEventListener('input', checkWeights);
  });

  // Source toggles — load from config
  loadSourceToggles();

  // Buttons
  document.getElementById('btn-start-run').addEventListener('click', startRun);
  document.getElementById('btn-save-template').addEventListener('click', saveTemplate);
  document.getElementById('btn-load-template').addEventListener('click', showLoadTemplate);
}

function makeTagInput(containerId, inputId, stateKey) {
  const container = document.getElementById(containerId);
  const input     = document.getElementById(inputId);
  container.addEventListener('click', () => input.focus());
  input.addEventListener('focus',  () => container.classList.add('focused'));
  input.addEventListener('blur',   () => container.classList.remove('focused'));
  input.addEventListener('keydown', e => {
    if ((e.key === 'Enter' || e.key === ',') && input.value.trim()) {
      e.preventDefault();
      const val = input.value.trim().replace(/,$/, '');
      if (val && !S[stateKey].includes(val)) {
        S[stateKey].push(val);
        renderTags(containerId, S[stateKey]);
      }
      input.value = '';
    } else if (e.key === 'Backspace' && !input.value && S[stateKey].length) {
      S[stateKey].pop();
      renderTags(containerId, S[stateKey]);
    }
  });
}

function renderTags(containerId, arr) {
  const container = document.getElementById(containerId);
  const input     = container.querySelector('input');
  container.querySelectorAll('.tag').forEach(t => t.remove());
  arr.forEach((val, i) => {
    const tag = document.createElement('span');
    tag.className = 'tag';
    tag.innerHTML = `${esc(val)} <span class="tag-rm" data-i="${i}">×</span>`;
    tag.querySelector('.tag-rm').addEventListener('click', (e) => {
      e.stopPropagation();
      arr.splice(i, 1);
      renderTags(containerId, arr);
    });
    container.insertBefore(tag, input);
  });
}

async function loadSourceToggles() {
  try { S.sources = await get('/config/sources'); } catch { S.sources = []; }
  const wrap = document.getElementById('source-toggles');
  const v1 = ['apollo','scrupp','phantombuster','firecrawl','manual'];
  wrap.innerHTML = v1.map(p => {
    const src = S.sources.find(s => s.provider === p) || { provider: p, enabled: false };
    return `<div class="checkbox-row">
      <input type="checkbox" id="src-${p}" ${src.enabled ? 'checked' : ''}>
      <label for="src-${p}" style="cursor:pointer">${providerLabel(p)}</label>
    </div>`;
  }).join('');
}

function getSourceConfig() {
  const cfg = {};
  ['apollo','scrupp','phantombuster','firecrawl','manual'].forEach(p => {
    const el = document.getElementById(`src-${p}`);
    cfg[p] = el ? el.checked : false;
  });
  return cfg;
}

function checkWeights() {
  const sum = ['w-transition','w-pe-fit','w-network','w-reachability']
    .reduce((a, id) => a + (parseInt(document.getElementById(id).value) || 0), 0);
  const warn = document.getElementById('weight-sum-warning');
  warn.textContent = sum !== 100 ? `⚠ Weights sum to ${sum}% — should be 100%` : '';
  warn.style.color = sum !== 100 ? 'var(--amber)' : '';
}

async function startRun() {
  if (!S.companies.length && !S.sectors.length) {
    alert('Add at least one company or sector before starting.'); return;
  }
  const weights = {
    transition:   (parseInt(document.getElementById('w-transition').value)   || 30) / 100,
    pe_fit:       (parseInt(document.getElementById('w-pe-fit').value)        || 35) / 100,
    network:      (parseInt(document.getElementById('w-network').value)       || 20) / 100,
    reachability: (parseInt(document.getElementById('w-reachability').value)  || 15) / 100,
  };
  const payload = {
    name: document.getElementById('template-name-input').value || `Run ${new Date().toLocaleDateString()}`,
    lane: S.lane,
    target_companies: [...S.companies],
    target_sectors:   [...S.sectors],
    target_countries: [...S.countries],
    source_config:    getSourceConfig(),
    score_weights:    weights,
  };
  const btn = document.getElementById('btn-start-run');
  btn.disabled = true;
  btn.innerHTML = '<span class="loader"></span> Starting…';
  try {
    const run = await post('/search-runs', payload);
    post(`/search-runs/${run.id}/start`);  // fire-and-forget; monitor in Runs view
    switchView('runs');
    setTimeout(loadRuns, 800);
  } catch(e) {
    alert('Failed to start run: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" style="width:13px;height:13px"><polygon points="5 3 19 12 5 21 5 3"/></svg> Start run';
  }
}

function saveTemplate() {
  const name = document.getElementById('template-name-input').value.trim();
  if (!name) { alert('Enter a template name first.'); return; }
  const tpl = {
    name, lane: S.lane,
    companies: [...S.companies],
    sectors:   [...S.sectors],
    countries: [...S.countries],
    source_config: getSourceConfig(),
  };
  S.templates = S.templates.filter(t => t.name !== name);
  S.templates.unshift(tpl);
  localStorage.setItem('pe_templates', JSON.stringify(S.templates));
  alert(`Template "${name}" saved.`);
}

function showLoadTemplate() {
  if (!S.templates.length) { alert('No templates saved yet.'); return; }
  const names = S.templates.map((t,i) => `${i+1}. ${t.name}`).join('\n');
  const idx = parseInt(prompt(`Choose a template:\n${names}`)) - 1;
  if (isNaN(idx) || !S.templates[idx]) return;
  const t = S.templates[idx];
  S.companies = [...(t.companies || [])];
  S.sectors   = [...(t.sectors || [])];
  S.countries = [...(t.countries || [])];
  S.lane      = t.lane || 'both';
  renderTags('companies-input', S.companies);
  renderTags('sectors-input',   S.sectors);
  renderTags('countries-input', S.countries);
  document.querySelectorAll('#lane-toggle .toggle-opt').forEach(el => {
    el.classList.toggle('on', el.dataset.val === S.lane);
  });
  document.getElementById('template-name-input').value = t.name;
  document.getElementById('search-template-name').textContent = `— ${t.name}`;
}

/* ════════════════════════════════════════════════════════════════════════════
   RUN MONITOR VIEW
══════════════════════════════════════════════════════════════════════════════ */
async function loadRuns() {
  try { S.runs = await get('/search-runs'); } catch { S.runs = []; }
  const el = document.getElementById('runs-list');
  if (!S.runs.length) { el.innerHTML = '<div class="empty">No runs yet.</div>'; return; }
  el.innerHTML = S.runs.map(r => renderRunCard(r)).join('');
  el.querySelectorAll('.run-card-header').forEach(h => {
    h.addEventListener('click', () => h.closest('.run-card').classList.toggle('open'));
  });
  el.querySelectorAll('.btn-view-results').forEach(b => {
    b.addEventListener('click', () => {
      S.filterRun = b.dataset.runId;
      switchView('table');
    });
  });
  el.querySelectorAll('.btn-delete-run').forEach(b => {
    b.addEventListener('click', async () => {
      if (!confirm('Delete this run?')) return;
      await api('DELETE', `/search-runs/${b.dataset.runId}`);
      loadRuns();
    });
  });
  // Auto-refresh running runs
  if (S.runs.some(r => r.status === 'running')) setTimeout(loadRuns, 4000);
}

function renderRunCard(r) {
  const stats  = r.stats || {};
  const stages = ['discovery','enrichment','web_enrichment','scoring','complete'];
  const curIdx = stages.indexOf(stats.stage);
  const stageHtml = stages.map((s, i) =>
    `<div class="stage-step ${i < curIdx ? 'done' : i === curIdx ? 'active' : ''}">${s}</div>`
  ).join('');
  const statusBadge = {
    pending:'badge-grey', running:'badge-teal', completed:'badge-green',
    failed:'badge-red', paused:'badge-amber'
  }[r.status] || 'badge-grey';

  return `<div class="run-card">
    <div class="run-card-header">
      <span class="run-card-title">${esc(r.name)}</span>
      <span class="badge ${statusBadge}">${r.status}</span>
      ${r.status === 'running' ? '<span class="loader"></span>' : ''}
      <span class="run-card-meta">${fmtDate(r.created_at)}</span>
    </div>
    <div class="run-card-body">
      <div class="run-grid" style="margin-bottom:10px">
        <div class="stat-tile"><div class="stat-num">${stats.companies_processed||0}</div><div class="stat-lbl">Companies</div></div>
        <div class="stat-tile"><div class="stat-num">${stats.executives_found||0}</div><div class="stat-lbl">Executives found</div></div>
        <div class="stat-tile"><div class="stat-num">${stats.contact_coverage||0}%</div><div class="stat-lbl">Contact coverage</div></div>
        <div class="stat-tile"><div class="stat-num">${stats.evidence_items||0}</div><div class="stat-lbl">Evidence items</div></div>
      </div>
      <div class="stage-track">${stageHtml}</div>
      <div style="display:flex;gap:6px">
        <button class="btn btn-secondary btn-sm btn-view-results" data-run-id="${r.id}">View executives</button>
        <button class="btn btn-ghost btn-sm btn-delete-run" data-run-id="${r.id}">Delete</button>
      </div>
    </div>
  </div>`;
}

document.getElementById('btn-refresh-runs').addEventListener('click', loadRuns);

/* ════════════════════════════════════════════════════════════════════════════
   EXECUTIVE TABLE VIEW
══════════════════════════════════════════════════════════════════════════════ */
async function loadExecutives() {
  const params = new URLSearchParams();
  if (S.filterRun)        params.set('run_id',      S.filterRun);
  if (S.filterLane)       params.set('lane',         S.filterLane);
  if (S.filterContact === 'yes') params.set('has_contact', 'true');
  if (S.filterContact === 'no')  params.set('has_contact', 'false');
  if (S.filterMinScore)   params.set('min_score',    S.filterMinScore);
  params.set('sort_by',  S.sortCol);
  params.set('sort_dir', S.sortDir);
  params.set('limit', '500');
  try { S.executives = await get('/executives?' + params); } catch { S.executives = []; }
  renderExecTable();
  populateRunFilter();
}

function renderExecTable() {
  let rows = S.executives;
  if (S.filterName) {
    const q = S.filterName.toLowerCase();
    rows = rows.filter(e =>
      (e.full_name||'').toLowerCase().includes(q) ||
      (e.current_company||'').toLowerCase().includes(q));
  }

  document.getElementById('exec-count-label').textContent = `${rows.length} executives`;
  document.getElementById('tbl-stat').innerHTML =
    `<strong>${rows.length}</strong> shown`;

  const tbody = document.getElementById('exec-tbody');
  tbody.innerHTML = rows.map(e => `
    <tr data-id="${e.id}">
      <td class="name-cell">${esc(e.full_name)}</td>
      <td class="title-cell">${esc(e.current_title||'')}</td>
      <td class="co-cell">${esc(e.current_company||'')}</td>
      <td>${esc(e.country||'')}</td>
      <td>${laneBadge(e.lane)}</td>
      <td>${scoreTotal(e.total_score)}</td>
      <td>${scoreBar(e.transition_score)}</td>
      <td>${scoreBar(e.pe_fit_score)}</td>
      <td>${scoreBar(e.network_score)}</td>
      <td>${scoreBar(e.reachability_score)}</td>
      <td>${contactBadge(e)}</td>
      <td class="text-muted text-sm">${e.last_signal_date ? relDate(e.last_signal_date) : '—'}</td>
      <td>${dossierBadge(e.dossier_status)}</td>
    </tr>`).join('');

  tbody.querySelectorAll('tr').forEach(tr => {
    tr.addEventListener('click', () => openDrawer(tr.dataset.id));
  });

  // Sort headers
  document.querySelectorAll('#exec-table thead th').forEach(th => {
    th.classList.toggle('sorted', th.dataset.col === S.sortCol);
    th.onclick = () => {
      if (S.sortCol === th.dataset.col) S.sortDir = S.sortDir === 'desc' ? 'asc' : 'desc';
      else { S.sortCol = th.dataset.col; S.sortDir = 'desc'; }
      loadExecutives();
    };
  });
}

async function populateRunFilter() {
  if (!S.runs.length) {
    try { S.runs = await get('/search-runs'); } catch { S.runs = []; }
  }
  const sel = document.getElementById('filter-run');
  const cur = sel.value;
  sel.innerHTML = '<option value="">All runs</option>' +
    S.runs.map(r => `<option value="${r.id}" ${r.id===cur?'selected':''}>${esc(r.name)}</option>`).join('');
}

// Filter wiring
document.getElementById('filter-name').addEventListener('input', e => {
  S.filterName = e.target.value; renderExecTable();
});
document.getElementById('filter-lane').addEventListener('change', e => {
  S.filterLane = e.target.value; loadExecutives();
});
document.getElementById('filter-run').addEventListener('change', e => {
  S.filterRun = e.target.value; loadExecutives();
});
document.getElementById('filter-contact').addEventListener('change', e => {
  S.filterContact = e.target.value; loadExecutives();
});
document.getElementById('filter-min-score').addEventListener('change', e => {
  S.filterMinScore = parseInt(e.target.value)||0; loadExecutives();
});
document.getElementById('btn-export-csv').addEventListener('click', () => {
  const p = S.filterRun ? `?run_id=${S.filterRun}` : '';
  window.open(API + '/executives/export/csv' + p);
});

/* ════════════════════════════════════════════════════════════════════════════
   EXECUTIVE DETAIL DRAWER
══════════════════════════════════════════════════════════════════════════════ */
async function openDrawer(execId) {
  try { S.drawerExec = await get(`/executives/${execId}`); }
  catch { return; }
  renderDrawerHeader();
  switchDrawerPanel('evidence');
  document.getElementById('drawer').classList.add('open');
  document.getElementById('drawer-overlay').classList.add('open');
}

function closeDrawer() {
  document.getElementById('drawer').classList.remove('open');
  document.getElementById('drawer-overlay').classList.remove('open');
  S.drawerExec = null;
}

document.getElementById('drawer-close').addEventListener('click', closeDrawer);
document.getElementById('drawer-overlay').addEventListener('click', closeDrawer);

document.querySelectorAll('.drawer-tab').forEach(tab => {
  tab.addEventListener('click', () => switchDrawerPanel(tab.dataset.panel));
});

function switchDrawerPanel(name) {
  S.drawerPanel = name;
  document.querySelectorAll('.drawer-tab').forEach(t =>
    t.classList.toggle('active', t.dataset.panel === name));
  document.querySelectorAll('.drawer-panel').forEach(p =>
    p.classList.toggle('active', p.id === `panel-${name}`));
  const e = S.drawerExec;
  if (!e) return;
  if (name === 'evidence') loadEvidence(e.id);
  if (name === 'graph')    loadGraph(e.id);
  if (name === 'dossier')  loadDossier(e.id);
  if (name === 'outreach') loadOutreach(e.id);
}

function renderDrawerHeader() {
  const e = S.drawerExec;
  document.getElementById('d-name').textContent = e.full_name;
  document.getElementById('d-sub').textContent =
    [e.current_title, e.current_company, e.country].filter(Boolean).join(' · ');

  const scoreColor = s => s >= 70 ? 'var(--green)' : s >= 45 ? 'var(--amber)' : 'var(--red)';
  document.getElementById('d-scores').innerHTML = [
    ['Total',  e.total_score],
    ['Trans',  e.transition_score],
    ['PE Fit', e.pe_fit_score],
    ['Network',e.network_score],
    ['Reach',  e.reachability_score],
  ].map(([l,v]) => `<div class="dscore">
    <span class="dscore-label">${l}</span>
    <span class="dscore-val" style="color:${scoreColor(v)}">${Math.round(v)}</span>
  </div>`).join('') +
  (e.signal_flags?.length ? `<div style="display:flex;flex-wrap:wrap;gap:3px;align-items:center">
    ${e.signal_flags.map(f => `<span class="flag-chip">${f.replace(/_/g,' ')}</span>`).join('')}
  </div>` : '');
}

document.getElementById('d-btn-enrich').addEventListener('click', async () => {
  const e = S.drawerExec; if (!e) return;
  const btn = document.getElementById('d-btn-enrich');
  btn.disabled = true; btn.textContent = 'Enriching…';
  try {
    await post(`/executives/${e.id}/enrich`);
    S.drawerExec = await get(`/executives/${e.id}`);
    renderDrawerHeader();
    if (S.drawerPanel === 'evidence') loadEvidence(e.id);
    loadExecutives();
  } catch(err) { alert(err.message); }
  finally { btn.disabled = false; btn.textContent = 'Enrich'; }
});

document.getElementById('d-btn-dossier').addEventListener('click', async () => {
  const e = S.drawerExec; if (!e) return;
  const btn = document.getElementById('d-btn-dossier');
  btn.disabled = true; btn.textContent = 'Generating…';
  try {
    await post(`/executives/${e.id}/dossier`);
    switchDrawerPanel('dossier');
  } catch(err) { alert(err.message); }
  finally { btn.disabled = false; btn.textContent = 'Generate dossier'; }
});

/* Evidence panel */
async function loadEvidence(execId) {
  const panel = document.getElementById('panel-evidence');
  panel.innerHTML = '<div class="empty"><span class="loader"></span></div>';
  let items = [];
  try { items = await get(`/executives/${execId}/evidence`); } catch {}
  if (!items.length) { panel.innerHTML = '<div class="empty">No evidence yet — click Enrich.</div>'; return; }
  panel.innerHTML = items.map(ev => `
    <div class="ev-item">
      <div class="ev-dot" style="background:${signalColor(ev.signal_type)}"></div>
      <div class="ev-body">
        <div class="ev-headline">${esc(ev.headline || ev.snippet.slice(0,80))}</div>
        <div class="ev-snippet">${esc(ev.snippet.slice(0,200))}</div>
        <div class="ev-meta">
          <span class="badge badge-grey">${ev.signal_type?.replace(/_/g,' ')}</span>
          <span class="ev-source">${ev.source_provider} / ${ev.source_type}</span>
          ${ev.date_observed ? `<span class="ev-date">${ev.date_observed}</span>` : ''}
          ${ev.source_url ? `<a href="${ev.source_url}" target="_blank" class="ev-source text-teal">↗</a>` : ''}
        </div>
      </div>
    </div>`).join('');
}

/* Graph panel */
async function loadGraph(execId) {
  let graph = { nodes: [], edges: [] };
  try { graph = await get(`/executives/${execId}/graph`); } catch {}
  renderD3Graph(graph);
  const listEl = document.getElementById('graph-edges-list');
  listEl.innerHTML = graph.edges.length
    ? graph.edges.map(e => {
        const tgt = graph.nodes.find(n => n.id === e.target);
        return `<div class="flex-center gap-6 text-sm" style="margin-bottom:4px">
          <span class="badge badge-teal">${e.edge_type.replace(/_/g,' ')}</span>
          <span>${esc(tgt?.label||e.target)}</span>
          <span class="text-muted">${tgt?.type||''}</span>
        </div>`;
      }).join('')
    : '<div class="empty">No graph edges yet.</div>';
}

function renderD3Graph(graph) {
  const svg = document.getElementById('graph-svg');
  svg.innerHTML = '';
  if (!graph.nodes.length) {
    svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#9A948C" font-size="12">No graph data</text>';
    return;
  }
  const W = svg.clientWidth || 520, H = 320;
  const nodeColor = { executive:'#2A7A72', company:'#3B5BDB', board:'#7048A8',
    event:'#C47F17', association:'#2E7D55', investor:'#B84040', advisor:'#555', podcast:'#888' };

  const d3svg = d3.select(svg).attr('viewBox', `0 0 ${W} ${H}`);
  const sim = d3.forceSimulation(graph.nodes)
    .force('link', d3.forceLink(graph.edges).id(d => d.id).distance(90))
    .force('charge', d3.forceManyBody().strength(-180))
    .force('center', d3.forceCenter(W/2, H/2))
    .force('collision', d3.forceCollide(28));

  const link = d3svg.append('g').selectAll('line')
    .data(graph.edges).join('line').attr('class', 'glink');

  const node = d3svg.append('g').selectAll('g')
    .data(graph.nodes).join('g').attr('class', 'gnode')
    .call(d3.drag()
      .on('start', (event, d) => { if (!event.active) sim.alphaTarget(.3).restart(); d.fx=d.x; d.fy=d.y; })
      .on('drag',  (event, d) => { d.fx=event.x; d.fy=event.y; })
      .on('end',   (event, d) => { if (!event.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }));

  node.append('circle').attr('r', d => d.type === 'executive' ? 14 : 10)
    .attr('fill', d => nodeColor[d.type] || '#888').attr('opacity', .85);
  node.append('text').text(d => d.label.length > 18 ? d.label.slice(0,16)+'…' : d.label)
    .attr('y', d => (d.type === 'executive' ? 14 : 10) + 11).attr('text-anchor', 'middle');

  sim.on('tick', () => {
    link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });
}

/* Dossier panel */
async function loadDossier(execId) {
  const panel = document.getElementById('panel-dossier');
  panel.innerHTML = '<div class="empty"><span class="loader"></span></div>';
  let d = null;
  try { d = await get(`/executives/${execId}/dossier`); } catch {}
  if (!d) {
    panel.innerHTML = '<div class="empty">No dossier yet. Click "Generate dossier" above.</div>';
    return;
  }
  panel.innerHTML = `
    ${d.outreach_angle ? `<div class="outreach-box">
      <div class="outreach-label">Outreach angle</div>
      <div class="outreach-text">${esc(d.outreach_angle)}</div>
    </div>` : ''}
    ${d.talking_points?.length ? `<div style="margin-bottom:12px">
      <div class="outreach-label" style="margin-bottom:6px">Talking points</div>
      ${d.talking_points.map(p => `<div class="talking-point">${esc(p)}</div>`).join('')}
    </div>` : ''}
    <div class="dossier-md">${mdToHtml(d.content_md || '')}</div>
    <hr class="divider">
    <div class="text-muted text-sm">Generated ${fmtDate(d.generated_at)} · Status: ${d.status}</div>`;
}

/* Outreach panel */
async function loadOutreach(execId) {
  const panel = document.getElementById('panel-outreach');
  let actions = [];
  try { actions = await get(`/executives/${execId}/outreach`); } catch {}
  panel.innerHTML = `
    <div style="margin-bottom:12px">
      <select class="select" id="new-action-type" style="width:130px;margin-right:6px">
        <option value="email">Email</option>
        <option value="linkedin">LinkedIn</option>
        <option value="intro">Warm intro</option>
        <option value="call">Call</option>
      </select>
      <input class="input" type="text" id="new-action-note" placeholder="Note…" style="width:220px;margin-right:6px">
      <button class="btn btn-secondary btn-sm" id="btn-add-action">Add</button>
    </div>
    ${actions.length ? actions.map(a => `
      <div class="flex-center gap-6 text-sm" style="margin-bottom:6px;padding:6px 8px;background:var(--surface-2);border-radius:4px">
        <span class="badge badge-grey">${a.action_type}</span>
        <span class="badge ${a.status==='replied'?'badge-green':a.status==='sent'?'badge-teal':'badge-grey'}">${a.status}</span>
        <span style="flex:1">${esc(a.notes||'')}</span>
        <span class="text-muted">${fmtDate(a.created_at)}</span>
      </div>`).join('')
    : '<div class="empty" style="padding:20px">No outreach logged yet.</div>'}`;

  document.getElementById('btn-add-action')?.addEventListener('click', async () => {
    const type = document.getElementById('new-action-type').value;
    const note = document.getElementById('new-action-note').value;
    await post(`/executives/${execId}/outreach`, { executive_id: execId, action_type: type, notes: note });
    loadOutreach(execId);
  });
}

/* ════════════════════════════════════════════════════════════════════════════
   CONFIG VIEW
══════════════════════════════════════════════════════════════════════════════ */
async function loadConfig() {
  await Promise.all([loadConfigSources(), loadConfigRules()]);
}

async function loadConfigSources() {
  try { S.sources = await get('/config/sources'); } catch { S.sources = []; }
  const el = document.getElementById('cfg-sources');
  el.innerHTML = S.sources.map(s => {
    const phase = ['boardex','execatlas','affinity'].includes(s.provider) ? 'Phase 3' :
                  s.provider === 'phantombuster' ? 'Phase 2' : 'Phase 1';
    return `<div class="source-row">
      <span class="source-name">${providerLabel(s.provider)}</span>
      <span class="source-phase badge badge-grey">${phase}</span>
      <input class="input source-key-input" type="password" placeholder="API key"
        value="${s.api_key ? '••••••••' : ''}" data-provider="${s.provider}" id="key-${s.provider}">
      <label class="source-enabled">
        <input type="checkbox" ${s.enabled?'checked':''} data-provider="${s.provider}" class="src-enabled-cb">
        Enabled
      </label>
      <button class="btn btn-secondary btn-sm src-save-btn" data-provider="${s.provider}">Save</button>
    </div>`;
  }).join('');

  el.querySelectorAll('.src-save-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const p   = btn.dataset.provider;
      const key = document.getElementById(`key-${p}`).value;
      const enabled = el.querySelector(`.src-enabled-cb[data-provider="${p}"]`).checked;
      btn.textContent = 'Saving…'; btn.disabled = true;
      try {
        await post('/config/source', {
          provider: p, enabled,
          api_key: key.startsWith('•') ? undefined : key,
          settings: {},
        });
        btn.textContent = 'Saved ✓';
      } catch(e) { btn.textContent = 'Error'; alert(e.message); }
      setTimeout(() => { btn.textContent = 'Save'; btn.disabled = false; }, 2000);
    });
  });
}

async function loadConfigRules() {
  try { S.rules = await get('/config/score-rules'); } catch { S.rules = []; }
  const el = document.getElementById('cfg-rules');
  el.innerHTML = S.rules.map(r => `
    <div class="rule-row" data-id="${r.id}">
      <span class="rule-name">${esc(r.name.replace(/_/g,' '))}</span>
      <span class="badge ${r.bucket==='pe_fit'?'badge-teal':r.bucket==='transition'?'badge-transition':r.bucket==='network'?'badge-successor':'badge-grey'}">${r.bucket}</span>
      <input class="input rule-delta-input" type="number" value="${r.delta}" style="width:58px;text-align:right">
      <input type="checkbox" ${r.enabled?'checked':''} class="rule-enabled-cb" style="margin:auto">
      <button class="btn btn-secondary btn-sm rule-save-btn">Save</button>
    </div>`).join('');

  el.querySelectorAll('.rule-save-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const row = btn.closest('.rule-row');
      const delta   = parseFloat(row.querySelector('.rule-delta-input').value);
      const enabled = row.querySelector('.rule-enabled-cb').checked;
      btn.textContent = '…'; btn.disabled = true;
      try {
        await patch(`/config/score-rules/${row.dataset.id}`, { delta, enabled });
        btn.textContent = '✓';
      } catch(e) { btn.textContent = '!'; alert(e.message); }
      setTimeout(() => { btn.textContent = 'Save'; btn.disabled = false; }, 1500);
    });
  });

  document.getElementById('btn-reset-rules')?.addEventListener('click', async () => {
    if (!confirm('Reset all score rules to defaults?')) return;
    // Delete all then re-seed by hitting the GET which calls seed_default_rules
    await Promise.all(S.rules.map(r => api('DELETE', `/config/score-rules/${r.id}`)));
    await get('/config/score-rules');
    loadConfigRules();
  });
}

/* ════════════════════════════════════════════════════════════════════════════
   HELPERS
══════════════════════════════════════════════════════════════════════════════ */
function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function scoreBar(v) {
  const cls = v >= 70 ? 'high' : v >= 45 ? 'mid' : 'low';
  return `<div class="score-cell">
    <div class="score-bar"><div class="score-fill ${cls}" style="width:${Math.round(v)}%"></div></div>
    <span class="score-num">${Math.round(v)}</span>
  </div>`;
}

function scoreTotal(v) {
  const cls = v >= 70 ? 'high' : v >= 45 ? 'mid' : 'low';
  return `<span class="score-total ${cls}">${Math.round(v)}</span>`;
}

function laneBadge(lane) {
  const cls = { transition:'badge-transition', successor:'badge-successor', both:'badge-both' }[lane]||'badge-grey';
  return `<span class="badge ${cls}">${lane}</span>`;
}

function contactBadge(e) {
  if (e.emails?.length && e.phones?.length)
    return `<span><span class="contact-dot dot-full"></span>email+ph</span>`;
  if (e.emails?.length)
    return `<span><span class="contact-dot dot-email"></span>email</span>`;
  return `<span><span class="contact-dot dot-none"></span>—</span>`;
}

function dossierBadge(s) {
  const map = { none:'badge-grey', drafted:'badge-amber', reviewed:'badge-teal', sent:'badge-green' };
  return `<span class="badge ${map[s]||'badge-grey'}">${s}</span>`;
}

function signalColor(sig) {
  const map = {
    role_change:'#3B5BDB', speaker:'#2A7A72', board_role:'#7048A8',
    advisor_role:'#7048A8', m_and_a:'#B84040', integration:'#C47F17',
    pricing:'#C47F17', turnaround:'#B84040', international_scale:'#2E7D55',
    network_edge:'#9A948C',
  };
  return map[sig] || '#9A948C';
}

function providerLabel(p) {
  return { apollo:'Apollo', scrupp:'Scrupp', phantombuster:'PhantomBuster',
    firecrawl:'Firecrawl', manual:'Manual / LinkedIn', boardex:'BoardEx (Phase 3)',
    execatlas:'ExecAtlas (Phase 3)', affinity:'Affinity (Phase 3)' }[p] || p;
}

function fmtDate(s) {
  if (!s) return '—';
  try { return new Date(s).toLocaleDateString('en-GB', { day:'numeric', month:'short', year:'numeric' }); }
  catch { return s; }
}

function relDate(s) {
  if (!s) return '—';
  const days = Math.floor((Date.now() - new Date(s)) / 86400000);
  if (days === 0) return 'today';
  if (days < 7)   return `${days}d ago`;
  if (days < 30)  return `${Math.floor(days/7)}w ago`;
  if (days < 365) return `${Math.floor(days/30)}mo ago`;
  return `${Math.floor(days/365)}y ago`;
}

function mdToHtml(md) {
  // Minimal markdown → html for dossier display
  return md
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[hup])(.+)$/gm, '<p>$1</p>');
}

/* ── Boot ────────────────────────────────────────────────────────────────── */
initSearchSetup();
