/**
 * ============================================================
 *  EnergyAI Dashboard — script.js
 *  Handles: API calls, fallback data, charts, UI updates
 * ============================================================
 *
 *  STEP 7 — FALLBACK SYSTEM:
 *  Every API call is wrapped in try/catch.
 *  If the backend is unreachable → getFallbackData(city)
 *  is called instead. The dashboard NEVER breaks.
 * ============================================================
 */

// ─────────────────────────────────────────────
//  Configuration
// ─────────────────────────────────────────────
let API_BASE = "http://localhost:5000";
let apiOnline = false;
let currentCity = null;
let chartInstances = {};   // store Chart.js instances

// ─────────────────────────────────────────────
//  STEP 7: FALLBACK DATA ENGINE
//  Simulates realistic city data when backend
//  is offline — dashboard always works.
// ─────────────────────────────────────────────
const FALLBACK_CITY_DATA = {
  delhi:      { temp: 38, modTemp: 52, irr: 0.82, wind: 3.2, cloud: 0.15, region: "North India",      yield: 5200, dcPower: 2750 },
  una:        { temp: 40, modTemp: 55, irr: 0.88, wind: 2.8, cloud: 0.10, region: "Himachal Pradesh", yield: 5600, dcPower: 2900 },
  chandigarh: { temp: 36, modTemp: 50, irr: 0.79, wind: 3.5, cloud: 0.20, region: "Punjab/Haryana",   yield: 5000, dcPower: 2600 },
  amritsar:   { temp: 37, modTemp: 51, irr: 0.80, wind: 4.0, cloud: 0.18, region: "Punjab",           yield: 5100, dcPower: 2650 },
  mumbai:     { temp: 30, modTemp: 44, irr: 0.72, wind: 5.1, cloud: 0.35, region: "West India",       yield: 4600, dcPower: 2400 },
  pune:       { temp: 28, modTemp: 42, irr: 0.75, wind: 4.2, cloud: 0.25, region: "Maharashtra",      yield: 4800, dcPower: 2500 },
  jaipur:     { temp: 42, modTemp: 58, irr: 0.91, wind: 4.5, cloud: 0.08, region: "Rajasthan",        yield: 5800, dcPower: 3000 },
  bangalore:  { temp: 26, modTemp: 40, irr: 0.77, wind: 3.8, cloud: 0.22, region: "South India",      yield: 4900, dcPower: 2550 },
  hyderabad:  { temp: 32, modTemp: 46, irr: 0.84, wind: 3.5, cloud: 0.18, region: "Telangana",        yield: 5300, dcPower: 2780 },
  chennai:    { temp: 33, modTemp: 47, irr: 0.80, wind: 5.5, cloud: 0.30, region: "Tamil Nadu",       yield: 5100, dcPower: 2650 },
  kolkata:    { temp: 30, modTemp: 44, irr: 0.68, wind: 4.2, cloud: 0.40, region: "East India",       yield: 4300, dcPower: 2250 },
  bhopal:     { temp: 36, modTemp: 50, irr: 0.83, wind: 3.0, cloud: 0.20, region: "Madhya Pradesh",   yield: 5250, dcPower: 2750 },
};

function getFallbackData(city) {
  /**
   * Generate complete prediction response from local data.
   * Called automatically when API is unreachable.
   */
  const key = city.trim().toLowerCase();
  let base = FALLBACK_CITY_DATA[key];

  // Partial match (e.g. "new delhi" → delhi)
  if (!base) {
    for (const [k, v] of Object.entries(FALLBACK_CITY_DATA)) {
      if (k.includes(key) || key.includes(k)) { base = v; break; }
    }
  }
  if (!base) {
    // Unknown city — use average values
    base = { temp: 32, modTemp: 46, irr: 0.76, wind: 3.5, cloud: 0.22,
             region: "India", yield: 5000, dcPower: 2600 };
  }

  // Compute predicted power using simple rule-based formula
  const efficiency = Math.max(0.55, 1.0 - (base.modTemp - 25) * 0.004);
  const predictedPower = Math.round(base.irr * 3200 * efficiency);
  const productionKwh  = +(predictedPower / 1000).toFixed(2);
  const consumptionKwh = 2.5;
  const surplus        = +(productionKwh - consumptionKwh).toFixed(2);

  let batteryAction = "balanced";
  let recommendation = "";
  if (surplus > 1.0) { batteryAction = "charge"; recommendation = `Surplus ${surplus} kWh — charging battery banks.`; }
  else if (surplus < -0.5) { batteryAction = "discharge"; recommendation = `Deficit ${Math.abs(surplus)} kWh — discharging batteries.`; }
  else { batteryAction = "balanced"; recommendation = "Production balanced with consumption. System running optimally."; }

  if (base.modTemp > 45) recommendation += " Clean panels to reduce heat buildup.";

  // Fault detection
  const hasFault = base.modTemp > 52 || (base.irr > 0.75 && predictedPower < 500);
  const severity = base.modTemp > 65 ? "critical" : base.modTemp > 52 ? "warning" : "normal";
  const faultMsg = hasFault
    ? [`${severity === "critical" ? "Critical" : "Warning"}: Panel temp ${base.modTemp}°C — efficiency reduced`]
    : ["All systems operating normally"];

  return {
    status: "success",
    city: city.split(' ').map(w => w[0].toUpperCase() + w.slice(1)).join(' '),
    predicted_power_kw: predictedPower,
    daily_yield_kwh: base.yield,
    ambient_temperature: base.temp,
    module_temperature: base.modTemp,
    irradiation: base.irr,
    wind_speed: base.wind,
    cloud_cover: base.cloud,
    region: base.region,
    climate: "Varied",
    consumption_kwh: consumptionKwh,
    production_kwh: productionKwh,
    surplus_kwh: surplus,
    battery_action: batteryAction,
    recommendation,
    fault: {
      has_fault: hasFault,
      severity,
      fault_messages: faultMsg,
      fault_count: hasFault ? 1 : 0
    },
    _fallback: true  // flag so UI can show "Offline Mode" badge
  };
}

function getFallbackHistory(city) {
  /**
   * Generate 7-day historical data for charts when API is offline.
   */
  const key = city.trim().toLowerCase();
  const base = FALLBACK_CITY_DATA[key] || { irr: 0.76, temp: 32 };
  const days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];
  const seeded = (i) => Math.sin(i * 9.7 + base.irr * 100) * 0.5 + 0.5; // deterministic pseudo-random

  return {
    status: "success",
    city: city,
    history: days.map((day, i) => {
      const irrVar = base.irr * (0.85 + seeded(i) * 0.3);
      const tempVar = base.temp + (seeded(i+7) - 0.5) * 6;
      const eff = Math.max(0.6, 1.0 - (tempVar - 25) * 0.004);
      return {
        day,
        production_kw: +(irrVar * 3000 * eff).toFixed(1),
        consumption_kw: +(1800 + seeded(i+14) * 900).toFixed(1),
        irradiation: +irrVar.toFixed(3),
        temperature: +tempVar.toFixed(1)
      };
    })
  };
}


// ─────────────────────────────────────────────
//  API Status Check
// ─────────────────────────────────────────────
async function checkAPIStatus() {
  const dot  = document.getElementById('api-status-dot');
  const text = document.getElementById('api-status-text');
  const settingsStatus = document.getElementById('settings-api-status');

  API_BASE = document.getElementById('setting-api-url')?.value || API_BASE;

  try {
    const res = await fetch(`${API_BASE}/`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      apiOnline = true;
      dot.className = 'status-dot online';
      text.textContent = 'API online';
      if (settingsStatus) settingsStatus.textContent = '✓ Connected to ' + API_BASE;
      hideFallbackBadge();
    } else { throw new Error('Bad status'); }
  } catch {
    apiOnline = false;
    dot.className = 'status-dot offline';
    text.textContent = 'Offline (fallback)';
    if (settingsStatus) settingsStatus.textContent = '✗ Cannot reach ' + API_BASE;
  }
}

function showFallbackBadge() { document.getElementById('fallback-badge').classList.remove('hidden'); }
function hideFallbackBadge() { document.getElementById('fallback-badge').classList.add('hidden'); }


// ─────────────────────────────────────────────
//  Main Prediction Flow
// ─────────────────────────────────────────────
async function runPrediction() {
  const cityInput = document.getElementById('city-input');
  const city = cityInput.value.trim();

  if (!city) {
    cityInput.focus();
    cityInput.style.borderColor = 'var(--accent-red)';
    setTimeout(() => { cityInput.style.borderColor = ''; }, 1500);
    return;
  }

  setLoadingState(true);
  currentCity = city;

  // 1. Fetch prediction + history in parallel
  const [predData, histData] = await Promise.all([
    fetchPredict(city),
    fetchHistory(city)
  ]);

  // 2. Update all UI sections
  updateMonitorCards(predData);
  updateWeatherInfo(predData);
  updateBatteryCard(predData);
  updateSystemStatus(predData);
  updateChartTrend(histData);
  updateChartBalance(predData);
  updateForecastSection(predData);
  updateFaultSection(predData);
  updateReportsSection(predData, histData);

  // 3. Show fallback badge if needed
  if (predData._fallback) showFallbackBadge();
  else hideFallbackBadge();

  setLoadingState(false);
}

// Fetch with auto-fallback
async function fetchPredict(city) {
  if (apiOnline) {
    try {
      const res = await fetch(`${API_BASE}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ city }),
        signal: AbortSignal.timeout(5000)
      });
      if (!res.ok) throw new Error('API error');
      return await res.json();
    } catch { /* fall through */ }
  }
  return getFallbackData(city);
}

async function fetchHistory(city) {
  if (apiOnline) {
    try {
      const res = await fetch(`${API_BASE}/data?city=${encodeURIComponent(city)}`, {
        signal: AbortSignal.timeout(5000)
      });
      if (!res.ok) throw new Error('API error');
      return await res.json();
    } catch { /* fall through */ }
  }
  return getFallbackHistory(city);
}

function setLoadingState(loading) {
  const btn  = document.getElementById('predict-btn');
  const text = document.getElementById('btn-text');
  const spin = document.getElementById('btn-spinner');

  btn.disabled = loading;
  if (loading) {
    text.textContent = 'Analysing...';
    spin.classList.remove('hidden');
    // Show skeleton values
    ['val-production','val-consumption','val-yield','val-irradiation'].forEach(id => {
      const el = document.getElementById(id);
      if (el) { el.textContent = '...'; el.classList.add('loading'); }
    });
  } else {
    text.textContent = 'Get Prediction';
    spin.classList.add('hidden');
    ['val-production','val-consumption','val-yield','val-irradiation'].forEach(id => {
      document.getElementById(id)?.classList.remove('loading');
    });
  }
}


// ─────────────────────────────────────────────
//  UI Update Functions
// ─────────────────────────────────────────────
function updateMonitorCards(data) {
  setVal('val-production', data.predicted_power_kw?.toFixed(0) + ' kW');
  setVal('val-consumption', data.consumption_kwh?.toFixed(1));
  setVal('val-yield', (data.daily_yield_kwh / 1000)?.toFixed(1) + ' k');
  setVal('val-irradiation', data.irradiation?.toFixed(2));
  setVal('city-label-chart', data.city || '—');
}

function updateWeatherInfo(data) {
  setVal('info-temp',    (data.ambient_temperature ?? '—') + '°C');
  setVal('info-modtemp', (data.module_temperature ?? '—') + '°C');
  setVal('info-wind',    (data.wind_speed ?? '—') + ' m/s');
  setVal('info-cloud',   ((data.cloud_cover ?? 0) * 100).toFixed(0) + '%');
}

function updateBatteryCard(data) {
  const action = data.battery_action || 'hold';
  const pct    = estimateBatteryPct(data.surplus_kwh);

  const fill  = document.getElementById('battery-fill');
  const pctEl = document.getElementById('battery-pct');
  const badge = document.getElementById('action-badge');
  const rec   = document.getElementById('battery-recommendation');

  if (fill)  { fill.style.width = pct + '%'; fill.className = 'battery-fill ' + (pct < 25 ? 'low' : pct < 60 ? 'medium' : ''); }
  if (pctEl) { pctEl.textContent = pct + '%'; }
  if (badge) { badge.textContent = action; badge.className = 'action-badge ' + action; }
  if (rec)   { rec.textContent   = data.recommendation || '—'; }
}

function estimateBatteryPct(surplus) {
  // Map surplus kWh to a battery % display (for visual demo)
  if (surplus > 2)    return 92;
  if (surplus > 1)    return 78;
  if (surplus > 0)    return 62;
  if (surplus > -0.5) return 50;
  if (surplus > -1.5) return 35;
  return 18;
}

function updateSystemStatus(data) {
  const fault   = data.fault || {};
  const iconEl  = document.getElementById('status-icon-large');
  const textEl  = document.getElementById('status-text');

  const icons = {
    normal:   `<svg viewBox="0 0 40 40" width="40" height="40"><circle cx="20" cy="20" r="16" stroke="#4ade80" stroke-width="2" fill="none"/><path d="M12 20l5 5 11-10" stroke="#4ade80" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>`,
    warning:  `<svg viewBox="0 0 40 40" width="40" height="40"><path d="M20 5L36 33H4Z" stroke="#fbbf24" stroke-width="2" fill="none" stroke-linejoin="round"/><path d="M20 16v8M20 27v2" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round"/></svg>`,
    critical: `<svg viewBox="0 0 40 40" width="40" height="40"><circle cx="20" cy="20" r="16" stroke="#f87171" stroke-width="2" fill="none"/><path d="M14 14l12 12M26 14L14 26" stroke="#f87171" stroke-width="2.5" stroke-linecap="round"/></svg>`
  };

  const sev = fault.severity || 'normal';
  if (iconEl) iconEl.innerHTML = icons[sev] || icons.normal;
  if (textEl) textEl.textContent = fault.fault_messages?.[0] || '—';
}


// ─────────────────────────────────────────────
//  Chart: 7-Day Trend
// ─────────────────────────────────────────────
function updateChartTrend(histData) {
  const ctx = document.getElementById('chart-trend')?.getContext('2d');
  if (!ctx) return;

  const history = histData.history || [];
  const labels  = history.map(d => d.day);
  const prod    = history.map(d => d.production_kw);
  const cons    = history.map(d => d.consumption_kw);

  destroyChart('trend');
  chartInstances.trend = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Production (kW)',
          data: prod,
          borderColor: '#4ade80',
          backgroundColor: 'rgba(74,222,128,0.08)',
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: '#4ade80',
          borderWidth: 2
        },
        {
          label: 'Consumption (kW)',
          data: cons,
          borderColor: '#60a5fa',
          backgroundColor: 'rgba(96,165,250,0.06)',
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: '#60a5fa',
          borderWidth: 2
        }
      ]
    },
    options: chartOptions()
  });
}


// ─────────────────────────────────────────────
//  Chart: Balance Doughnut
// ─────────────────────────────────────────────
function updateChartBalance(data) {
  const ctx = document.getElementById('chart-balance')?.getContext('2d');
  if (!ctx) return;

  const prod = Math.max(0, data.production_kwh || 0) * 1000;
  const cons = Math.max(0, data.consumption_kwh || 0) * 1000;

  destroyChart('balance');
  chartInstances.balance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Production', 'Consumption'],
      datasets: [{
        data: [prod, cons],
        backgroundColor: ['rgba(74,222,128,0.8)', 'rgba(96,165,250,0.7)'],
        borderColor: ['#4ade80', '#60a5fa'],
        borderWidth: 1,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', font: { size: 12 }, padding: 14 }
        }
      },
      cutout: '68%'
    }
  });
}


// ─────────────────────────────────────────────
//  Forecast Section — Hourly Chart + Table
// ─────────────────────────────────────────────
function updateForecastSection(data) {
  const irr    = data.irradiation    || 0.75;
  const temp   = data.ambient_temperature || 30;
  const base   = data.predicted_power_kw || 1500;

  // Generate 24 hourly values (solar curve)
  const hours = Array.from({length: 24}, (_, i) => i);
  const powers = hours.map(h => {
    if (h < 5 || h > 19) return 0;
    const solarAngle = Math.sin((h - 5) / 14 * Math.PI);
    const noise = 0.9 + Math.sin(h * 3.7) * 0.08;
    return Math.max(0, base * solarAngle * noise);
  });

  // Hourly chart
  const ctx = document.getElementById('chart-hourly')?.getContext('2d');
  if (ctx) {
    destroyChart('hourly');
    chartInstances.hourly = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: hours.map(h => h + ':00'),
        datasets: [{
          label: 'Predicted Power (kW)',
          data: powers.map(p => +p.toFixed(0)),
          backgroundColor: hours.map(h => h >= 6 && h <= 18 ? 'rgba(74,222,128,0.65)' : 'rgba(74,222,128,0.15)'),
          borderColor: '#4ade80',
          borderWidth: 1,
          borderRadius: 3
        }]
      },
      options: chartOptions({ x: { ticks: { maxTicksLimit: 12 } } })
    });
  }

  // Pie chart — production split
  const ctx2 = document.getElementById('chart-pie')?.getContext('2d');
  if (ctx2) {
    const totalProd = powers.reduce((a,b) => a+b, 0);
    const used = Math.min(totalProd, 2400);
    const stored = Math.max(0, totalProd - used);
    destroyChart('pie');
    chartInstances.pie = new Chart(ctx2, {
      type: 'doughnut',
      data: {
        labels: ['Used (kW)', 'Battery stored (kW)'],
        datasets: [{
          data: [+used.toFixed(0), +stored.toFixed(0)],
          backgroundColor: ['rgba(167,139,250,0.7)', 'rgba(251,191,36,0.7)'],
          borderColor: ['#a78bfa', '#fbbf24'],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 12 }, padding: 12 } } },
        cutout: '65%'
      }
    });
  }

  // Table
  const tbody = document.getElementById('forecast-tbody');
  if (tbody) {
    tbody.innerHTML = hours.map(h => {
      const p = powers[h];
      const solarIrr = h >= 5 && h <= 19 ? (irr * Math.sin((h-5)/14*Math.PI)).toFixed(3) : '0.000';
      const tempH = (temp + (h >= 12 ? (h-12)*0.5 : 0) - (h < 8 ? (8-h)*0.8 : 0)).toFixed(1);
      const status = p > 1000 ? 'good' : p > 200 ? 'warning' : 'low';
      const statusLabel = p > 1000 ? 'High' : p > 200 ? 'Moderate' : 'Low';
      return `<tr>
        <td>${String(h).padStart(2,'0')}:00</td>
        <td>${p.toFixed(0)}</td>
        <td>${solarIrr}</td>
        <td>${tempH}</td>
        <td><span class="status-pill ${status}">${statusLabel}</span></td>
      </tr>`;
    }).join('');
  }
}


// ─────────────────────────────────────────────
//  Fault Section
// ─────────────────────────────────────────────
function updateFaultSection(data) {
  const container = document.getElementById('fault-cards-container');
  if (!container) return;

  const fault = data.fault || {};
  const sev   = fault.severity || 'normal';
  const msgs  = fault.fault_messages || ['All systems operating normally'];

  const checks = [
    { name: "Panel Temperature", value: `${data.module_temperature}°C`, ok: data.module_temperature < 52, warn: data.module_temperature < 65, msg: data.module_temperature >= 65 ? "Critical: overheating!" : data.module_temperature >= 52 ? "Elevated temperature" : "Normal range" },
    { name: "Solar Irradiation", value: `${data.irradiation} kWh/m²`, ok: data.irradiation > 0.3, warn: data.irradiation > 0.1, msg: data.irradiation > 0.5 ? "Good irradiation levels" : data.irradiation > 0.2 ? "Moderate irradiation" : "Low irradiation — check for shading" },
    { name: "Power Output",      value: `${data.predicted_power_kw} kW`, ok: data.predicted_power_kw > 1000, warn: data.predicted_power_kw > 300, msg: data.predicted_power_kw > 1500 ? "Excellent output" : data.predicted_power_kw > 500 ? "Moderate output" : "Low output — possible fault" },
    { name: "Energy Balance",    value: `${data.surplus_kwh > 0 ? '+' : ''}${data.surplus_kwh} kWh`, ok: Math.abs(data.surplus_kwh) < 2, warn: data.surplus_kwh > -2, msg: data.surplus_kwh > 1 ? "Surplus — charge batteries" : data.surplus_kwh > -1 ? "Balanced" : "Deficit — discharge batteries" }
  ];

  container.innerHTML = `
    <div class="fault-grid">
      ${checks.map(c => `
        <div class="fault-card ${c.ok ? 'normal' : c.warn ? 'warning' : 'critical'}">
          <h4 class="${c.ok ? 'normal' : c.warn ? 'warning' : 'critical'}">
            ${c.ok ? '✓' : c.warn ? '⚠' : '✗'} ${c.name}
          </h4>
          <p><strong>${c.value}</strong> — ${c.msg}</p>
        </div>
      `).join('')}
    </div>
    <div class="fault-card ${sev}" style="margin-top:14px">
      <h4 class="${sev}">AI Fault Summary — ${sev.toUpperCase()}</h4>
      ${msgs.map(m => `<p style="margin-bottom:6px">• ${m}</p>`).join('')}
    </div>`;
}


// ─────────────────────────────────────────────
//  Reports Section
// ─────────────────────────────────────────────
function updateReportsSection(data, histData) {
  const container = document.getElementById('report-container');
  if (!container) return;

  const history = histData.history || [];
  const avgProd = history.length
    ? (history.reduce((s,d) => s + d.production_kw, 0) / history.length).toFixed(0)
    : data.predicted_power_kw || '—';
  const totalYield = history.length
    ? history.reduce((s,d) => s + d.production_kw, 0).toFixed(0)
    : '—';
  const avgTemp = history.length
    ? (history.reduce((s,d) => s + d.temperature, 0) / history.length).toFixed(1)
    : data.ambient_temperature || '—';

  container.innerHTML = `
    <div class="report-grid">
      <div class="report-stat">
        <div class="report-stat-label">City</div>
        <div class="report-stat-val blue" style="font-size:18px">${data.city || '—'}</div>
        <div style="font-size:12px;color:var(--text-sec);margin-top:4px">${data.region || ''}</div>
      </div>
      <div class="report-stat">
        <div class="report-stat-label">Avg 7-Day Production</div>
        <div class="report-stat-val green">${avgProd} kW</div>
      </div>
      <div class="report-stat">
        <div class="report-stat-label">Total Weekly Yield</div>
        <div class="report-stat-val amber">${totalYield} kW</div>
      </div>
      <div class="report-stat">
        <div class="report-stat-label">ML Prediction</div>
        <div class="report-stat-val green">${data.predicted_power_kw} kW</div>
        <div style="font-size:12px;color:var(--text-sec);margin-top:4px">Random Forest model</div>
      </div>
      <div class="report-stat">
        <div class="report-stat-label">Avg Temperature</div>
        <div class="report-stat-val amber">${avgTemp}°C</div>
      </div>
      <div class="report-stat">
        <div class="report-stat-label">Fault Status</div>
        <div class="report-stat-val ${data.fault?.severity === 'normal' ? 'green' : 'amber'}" style="font-size:18px;text-transform:capitalize">
          ${data.fault?.severity || '—'}
        </div>
      </div>
    </div>
    <div class="fault-card normal" style="padding:14px 18px">
      <h4 class="normal">AI Recommendation</h4>
      <p>${data.recommendation || '—'}</p>
    </div>`;
}


// ─────────────────────────────────────────────
//  Chart.js Shared Options
// ─────────────────────────────────────────────
function chartOptions(extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: '#94a3b8', font: { size: 12 }, padding: 16 } }
    },
    scales: {
      x: {
        grid: { color: 'rgba(31,47,71,0.6)' },
        ticks: { color: '#4b5563', font: { size: 11 }, ...(extra.x?.ticks || {}) }
      },
      y: {
        grid: { color: 'rgba(31,47,71,0.6)' },
        ticks: { color: '#4b5563', font: { size: 11 } }
      }
    },
    ...extra
  };
}

function destroyChart(name) {
  if (chartInstances[name]) {
    chartInstances[name].destroy();
    chartInstances[name] = null;
  }
}


// ─────────────────────────────────────────────
//  Section Navigation
// ─────────────────────────────────────────────
const SECTION_META = {
  monitor:  { title: 'Live Monitor',     subtitle: 'Real-time microgrid energy overview' },
  forecast: { title: 'Energy Forecast',  subtitle: 'AI-predicted hourly production' },
  fault:    { title: 'Fault Alerts',     subtitle: 'Anomaly detection & system health' },
  reports:  { title: 'Reports',          subtitle: 'Summary statistics & recommendations' },
  settings: { title: 'Settings',         subtitle: 'API connection & preferences' },
};

function showSection(name) {
  // Update nav active state
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.section === name);
  });

  // Show/hide sections
  document.querySelectorAll('.section').forEach(el => {
    el.classList.toggle('active', el.id === `section-${name}`);
  });

  // Update page title
  const meta = SECTION_META[name] || {};
  document.getElementById('page-title').textContent   = meta.title    || name;
  document.getElementById('page-subtitle').textContent = meta.subtitle || '';

  return false;
}


// ─────────────────────────────────────────────
//  Utilities
// ─────────────────────────────────────────────
function setVal(id, val) {
  const el = document.getElementById(id);
  if (el) { el.textContent = val ?? '—'; el.classList.add('animate-in'); }
}


// ─────────────────────────────────────────────
//  Keyboard: Enter key triggers prediction
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('city-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') runPrediction();
  });

  // Initial API check
  checkAPIStatus();
  // Recheck every 30 seconds
  setInterval(checkAPIStatus, 30000);

  // Pre-load a demo prediction for Delhi to show on startup
  setTimeout(() => {
    document.getElementById('city-input').value = 'Delhi';
    runPrediction();
  }, 600);
});
