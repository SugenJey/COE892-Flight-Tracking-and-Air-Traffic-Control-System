/* ATC Management System — Dashboard JS */

const API = '';   // same origin; empty string = relative URLs

// ── Utilities ────────────────────────────────────────────────
async function api(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.error || res.statusText);
  return data;
}

function toast(msg, type = 'ok') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `show ${type}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('show'), 3500);
}

function fuelBarClass(pct) {
  if (pct >= 50) return 'high';
  if (pct >= 20) return 'mid';
  return 'low';
}

function statusBadge(s) {
  const map = {
    available: 'badge-green', occupied: 'badge-red',
    active: 'badge-green', maintenance: 'badge-yellow', grounded: 'badge-red',
  };
  return `<span class="badge ${map[s] || 'badge-blue'}">${s}</span>`;
}

function emptyRow(cols, msg = 'No records yet') {
  return `<tr><td colspan="${cols}" style="text-align:center;color:var(--muted);padding:20px">${msg}</td></tr>`;
}

// ── Navigation ────────────────────────────────────────────────
function navigate(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
  document.getElementById('page-' + pageId).classList.add('active');
  document.querySelector(`nav a[data-page="${pageId}"]`).classList.add('active');
  refresh(pageId);
}

// ── Airports ─────────────────────────────────────────────────
async function loadAirports() {
  const airports = await api('GET', '/airports/');
  const tbody = document.getElementById('airports-tbody');
  if (!airports.length) { tbody.innerHTML = emptyRow(6); return; }
  tbody.innerHTML = airports.map(a => `
    <tr>
      <td><strong>${a.iata_code}</strong></td>
      <td>${a.name}</td>
      <td>${a.city}, ${a.country}</td>
      <td>${a.num_runways}</td>
      <td><button class="btn btn-ghost btn-sm" onclick="viewFuel(${a.id})">Fuel</button></td>
      <td><button class="btn btn-danger btn-sm" onclick="deleteAirport(${a.id})">Delete</button></td>
    </tr>`).join('');
}

async function createAirport(e) {
  e.preventDefault();
  const f = e.target;
  try {
    await api('POST', '/airports/', {
      name: f.name_.value, iata_code: f.iata.value.toUpperCase(),
      city: f.city.value, country: f.country.value,
      num_runways: +f.runways.value,
      fuel_capacity_l: +f.fuel_cap.value,
      initial_fuel_l: +f.fuel_init.value,
    });
    toast('Airport queued — refreshing shortly...');
    f.reset();
    setTimeout(loadAirports, 1500);
  } catch (err) { toast(err.message, 'err'); }
}

async function deleteAirport(id) {
  if (!confirm('Delete airport and all its runways/fuel?')) return;
  try {
    await api('DELETE', `/airports/${id}`);
    toast('Airport delete queued — refreshing shortly...');
    setTimeout(loadAirports, 1500);
  } catch (err) { toast(err.message, 'err'); }
}

function viewFuel(airportId) {
  navigate('fuel');
  document.getElementById('fuel-airport-id').value = airportId;
  loadFuelStock(airportId);
}

// ── Runways ──────────────────────────────────────────────────
async function loadRunways() {
  const [runways, airports] = await Promise.all([api('GET', '/runways/'), api('GET', '/airports/')]);
  const airportMap = Object.fromEntries(airports.map(a => [a.id, a.iata_code]));
  const tbody = document.getElementById('runways-tbody');
  if (!runways.length) { tbody.innerHTML = emptyRow(7); return; }
  tbody.innerHTML = runways.map(r => `
    <tr>
      <td>${airportMap[r.airport_id] || r.airport_id}</td>
      <td><strong>${r.runway_identifier}</strong></td>
      <td>${r.length_m.toLocaleString()} m</td>
      <td>${r.surface_type}</td>
      <td>${statusBadge(r.status)}</td>
      <td>${r.assigned_tail_number || '—'}</td>
      <td>
        ${r.status === 'available'
          ? `<button class="btn btn-success btn-sm" onclick="showAssignForm(${r.id})">Assign</button>`
          : `<button class="btn btn-ghost btn-sm" onclick="releaseRunway(${r.id})">Release</button>`}
        ${r.status === 'available' ? `<button class="btn btn-danger btn-sm" onclick="deleteRunway(${r.id})">Del</button>` : ''}
      </td>
    </tr>`).join('');

  // populate airport select in create form
  const sel = document.getElementById('runway-airport-id');
  sel.innerHTML = airports.map(a => `<option value="${a.id}">${a.iata_code} — ${a.name}</option>`).join('');
}

async function createRunway(e) {
  e.preventDefault();
  const f = e.target;
  try {
    await api('POST', '/runways/', {
      airport_id: +f.airport_id.value,
      runway_identifier: f.identifier.value,
      length_m: +f.length.value,
      surface_type: f.surface.value,
    });
    toast('Runway queued — refreshing shortly...');
    f.reset();
    setTimeout(loadRunways, 1500);
  } catch (err) { toast(err.message, 'err'); }
}

function showAssignForm(runwayId) {
  const tail = prompt('Enter tail number to assign:');
  if (!tail) return;
  api('POST', `/runways/${runwayId}/assign`, { tail_number: tail.toUpperCase() })
    .then(() => { toast('Runway assign queued — refreshing shortly...'); setTimeout(loadRunways, 1500); })
    .catch(err => toast(err.message, 'err'));
}

async function releaseRunway(runwayId) {
  try {
    await api('POST', `/runways/${runwayId}/release`);
    toast('Runway release queued — refreshing shortly...');
    setTimeout(loadRunways, 1500);
  } catch (err) { toast(err.message, 'err'); }
}

async function deleteRunway(runwayId) {
  if (!confirm('Delete this runway?')) return;
  try {
    await api('DELETE', `/runways/${runwayId}`);
    toast('Runway delete queued — refreshing shortly...');
    setTimeout(loadRunways, 1500);
  } catch (err) { toast(err.message, 'err'); }
}

// ── Airplanes ─────────────────────────────────────────────────
async function loadAirplanes() {
  const planes = await api('GET', '/airplanes/');
  const tbody = document.getElementById('airplanes-tbody');
  if (!planes.length) { tbody.innerHTML = emptyRow(7); return; }
  tbody.innerHTML = planes.map(p => {
    const pct = Math.round(p.current_fuel_l / p.fuel_capacity_l * 100);
    return `
    <tr>
      <td><strong>${p.tail_number}</strong></td>
      <td>${p.model}</td>
      <td>${statusBadge(p.operational_status)}</td>
      <td>
        <div style="display:flex;align-items:center;gap:8px">
          <div class="fuel-bar-wrap" style="width:80px">
            <div class="fuel-bar ${fuelBarClass(pct)}" style="width:${pct}%"></div>
          </div>
          <span style="font-size:12px;color:var(--muted)">${p.current_fuel_l.toLocaleString()} / ${p.fuel_capacity_l.toLocaleString()} L</span>
        </div>
      </td>
      <td>
        <select onchange="changeStatus('${p.tail_number}', this.value)" style="font-size:12px;padding:4px 8px">
          ${['active','maintenance','grounded'].map(s =>
            `<option value="${s}" ${s === p.operational_status ? 'selected' : ''}>${s}</option>`).join('')}
        </select>
      </td>
      <td><button class="btn btn-danger btn-sm" onclick="deleteAirplane('${p.tail_number}')">Delete</button></td>
    </tr>`;
  }).join('');
}

async function createAirplane(e) {
  e.preventDefault();
  const f = e.target;
  try {
    await api('POST', '/airplanes/', {
      tail_number: f.tail.value.toUpperCase(),
      model: f.model_.value,
      fuel_capacity_l: +f.capacity.value,
      current_fuel_l: +f.current.value,
      operational_status: f.opstatus.value,
    });
    toast('Airplane queued — refreshing shortly...');
    f.reset();
    setTimeout(loadAirplanes, 1500);
  } catch (err) { toast(err.message, 'err'); }
}

async function changeStatus(tail, newStatus) {
  try {
    await api('PUT', `/airplanes/${tail}`, { operational_status: newStatus });
    toast(`${tail} → ${newStatus} queued...`);
    setTimeout(loadAirplanes, 1500);
  } catch (err) { toast(err.message, 'err'); }
}

async function deleteAirplane(tail) {
  if (!confirm(`Delete airplane ${tail}?`)) return;
  try {
    await api('DELETE', `/airplanes/${tail}`);
    toast('Airplane delete queued — refreshing shortly...');
    setTimeout(loadAirplanes, 1500);
  } catch (err) { toast(err.message, 'err'); }
}

// ── Fuel ──────────────────────────────────────────────────────
async function loadAllFuelStocks() {
  const airports = await api('GET', '/airports/');
  const container = document.getElementById('fuel-stocks');
  if (!airports.length) { container.innerHTML = '<p style="color:var(--muted)">No airports yet.</p>'; return; }
  const stocks = await Promise.all(airports.map(a =>
    api('GET', `/fuel/${a.id}`).then(s => ({ ...s, iata: a.iata_code, name: a.name })).catch(() => null)
  ));
  container.innerHTML = stocks.filter(Boolean).map(s => {
    const pct = Math.round(s.quantity_l / s.capacity_l * 100);
    return `
    <div class="card" style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <div>
          <strong>${s.iata}</strong> — ${s.name}
          <div style="font-size:12px;color:var(--muted);margin-top:2px">${s.quantity_l.toLocaleString()} / ${s.capacity_l.toLocaleString()} L (${pct}%)</div>
        </div>
        <button class="btn btn-ghost btn-sm" onclick="showRestockForm(${s.airport_id})">Restock</button>
      </div>
      <div class="fuel-bar-wrap"><div class="fuel-bar ${fuelBarClass(pct)}" style="width:${pct}%"></div></div>
    </div>`;
  }).join('');
}

async function loadFuelStock(airportId) {
  try {
    const s = await api('GET', `/fuel/${airportId}`);
    const pct = Math.round(s.quantity_l / s.capacity_l * 100);
    document.getElementById('fuel-detail').innerHTML = `
      <strong>Airport ${airportId}</strong>: ${s.quantity_l.toLocaleString()} / ${s.capacity_l.toLocaleString()} L
      <span class="badge ${pct < 20 ? 'badge-red' : pct < 50 ? 'badge-yellow' : 'badge-green'}" style="margin-left:8px">${pct}%</span>`;
  } catch (e) { document.getElementById('fuel-detail').textContent = e.message; }
}

function showRestockForm(airportId) {
  document.getElementById('restock-airport-id').value = airportId;
  document.getElementById('fuel-airport-id').value = airportId;
  document.getElementById('fuel-detail').textContent = '';
  loadFuelStock(airportId);
}

async function restockFuel(e) {
  e.preventDefault();
  const f = e.target;
  const id = +document.getElementById('restock-airport-id').value;
  if (!id) { toast('Select an airport first', 'err'); return; }
  try {
    await api('PUT', `/fuel/${id}/restock`, { quantity_l: +f.qty.value });
    toast('Fuel restock queued — refreshing shortly...');
    f.reset();
    setTimeout(() => { loadAllFuelStocks(); loadFuelStock(id); }, 1500);
  } catch (err) { toast(err.message, 'err'); }
}

async function dispenseFuel(e) {
  e.preventDefault();
  const f = e.target;
  try {
    await api('POST', '/fuel/dispense', {
      tail_number: f.tail.value.toUpperCase(),
      runway_id: +f.runway_id.value,
      fuel_required_l: +f.fuel_l.value,
    });
    toast('Fuel dispense queued — refreshing shortly...');
    f.reset();
    setTimeout(loadAllFuelStocks, 1500);
  } catch (err) { toast(err.message, 'err'); }
}

// ── Events ────────────────────────────────────────────────────
async function loadEvents() {
  const evts = await api('GET', '/events/?limit=100');
  const log = document.getElementById('event-log');
  if (!evts.length) {
    log.innerHTML = '<p style="color:var(--muted);text-align:center;padding:24px">No events yet. Trigger an operation to see events.</p>';
    return;
  }
  log.innerHTML = evts.map(e => {
    const payload = JSON.parse(e.payload || '{}');
    const time = new Date(e.created_at + 'Z').toLocaleTimeString();
    return `
    <div class="event-item ${e.event_type}">
      <span class="event-type">${e.event_type}</span>
      <span class="event-payload">${Object.entries(payload).map(([k,v]) => `<b>${k}</b>: ${v}`).join(' · ')}</span>
      <span class="event-time">${time}</span>
    </div>`;
  }).join('');
}

// ── Auto-refresh ──────────────────────────────────────────────
const refreshFns = {
  airports: loadAirports,
  runways: loadRunways,
  airplanes: loadAirplanes,
  fuel: loadAllFuelStocks,
  events: loadEvents,
};

let _currentPage = 'airports';
let _refreshInterval = null;

function refresh(pageId) {
  _currentPage = pageId;
  clearInterval(_refreshInterval);
  const fn = refreshFns[pageId];
  if (fn) {
    fn().catch(err => toast('Load error: ' + err.message, 'err'));
    _refreshInterval = setInterval(() => fn().catch(() => {}), 5000);
  }
}

// ── Boot ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('nav a').forEach(a => {
    a.addEventListener('click', e => { e.preventDefault(); navigate(a.dataset.page); });
  });
  navigate('airports');
});
