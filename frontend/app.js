const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;
const API = '';

let ws = null;
let allNews = [];
let activeFilter = 'all';
let fundamentalsData = [];

// ─── WebSocket ───────────────────────────────────────────────
function connectWS() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    document.getElementById('ws-status').className = 'ws-dot connected';
    document.getElementById('ws-status').title = 'Připojeno';
  };

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    switch (msg.type) {
      case 'fundamentals': renderWatchlist(msg.data); break;
      case 'news':         renderNews(msg.data); break;
      case 'macro':        renderMacro(msg.data); break;
      case 'alert':        addAlert(msg.data); break;
      case 'alerts':       renderAlerts(msg.data); break;
    }
    document.getElementById('last-update').textContent = '↻ ' + new Date().toLocaleTimeString();
  };

  ws.onclose = () => {
    document.getElementById('ws-status').className = 'ws-dot disconnected';
    setTimeout(connectWS, 3000);
  };

  ws.onerror = () => ws.close();
}

// ─── Watchlist ────────────────────────────────────────────────
function renderWatchlist(stocks) {
  fundamentalsData = stocks;
  const el = document.getElementById('watchlist-table');
  if (!stocks || !stocks.length) {
    el.innerHTML = '<div class="loading">Žádná data</div>';
    return;
  }

  el.innerHTML = stocks.map(s => {
    if (s.error) return `<div class="stock-row"><span class="stock-ticker">${s.ticker}</span><span class="muted">Error</span></div>`;

    const chg = s.change_pct || 0;
    const chgClass = chg > 0 ? 'positive' : chg < 0 ? 'negative' : 'neutral';
    const chgSign = chg > 0 ? '+' : '';

    const pe = s.pe_ratio ? s.pe_ratio.toFixed(1) : 'N/A';
    const eps = s.eps ? s.eps.toFixed(2) : 'N/A';
    const rev = s.revenue_growth ? (s.revenue_growth * 100).toFixed(1) + '%' : 'N/A';

    const rec = (s.recommendation || '').toLowerCase();
    let signalClass = 'signal-hold', signalText = 'DRŽET';
    if (rec.includes('buy') || rec.includes('strong_buy')) { signalClass = 'signal-buy'; signalText = 'KOUPIT'; }
    if (rec.includes('sell') || rec.includes('underperform')) { signalClass = 'signal-sell'; signalText = 'PRODAT'; }

    return `
    <div class="stock-row" onclick="showModal('${s.ticker}')">
      <span class="stock-ticker">${s.ticker}</span>
      <span class="stock-price">$${(s.price || 0).toFixed(2)}</span>
      <span class="stock-change ${chgClass}">${chgSign}${chg.toFixed(2)}%</span>
      <div class="stock-fundamentals">
        <div class="fund-item">P/E <span>${pe}</span></div>
        <div class="fund-item">EPS <span>$${eps}</span></div>
        <div class="fund-item">Růst tržeb <span>${rev}</span></div>
      </div>
      <span class="stock-signal ${signalClass}">${signalText}</span>
    </div>`;
  }).join('');

  updateMarketStatus(stocks);
}

function updateMarketStatus(stocks) {
  const valid = stocks.filter(s => s.change_pct != null);
  if (!valid.length) return;
  const avg = valid.reduce((a, b) => a + b.change_pct, 0) / valid.length;
  const el = document.getElementById('market-status');
  if (avg > 0.5) { el.textContent = '▲ BÝČÍ'; el.style.color = 'var(--green)'; el.style.borderColor = 'var(--green)'; }
  else if (avg < -0.5) { el.textContent = '▼ MEDVĚDÍ'; el.style.color = 'var(--red)'; el.style.borderColor = 'var(--red)'; }
  else { el.textContent = '◆ NEUTRÁLNÍ'; el.style.color = 'var(--yellow)'; el.style.borderColor = 'var(--yellow)'; }
}

// ─── News ─────────────────────────────────────────────────────
function renderNews(articles) {
  allNews = articles || [];
  document.getElementById('news-count').textContent = allNews.length;
  applyNewsFilter();
}

function filterNews(filter) {
  activeFilter = filter;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  applyNewsFilter();
}

function applyNewsFilter() {
  let filtered = allNews;
  if (activeFilter === 'HIGH') filtered = allNews.filter(n => n.is_breaking || n.ai?.impact === 'HIGH');
  else if (activeFilter === 'BULLISH') filtered = allNews.filter(n => n.ai?.sentiment === 'BULLISH');
  else if (activeFilter === 'BEARISH') filtered = allNews.filter(n => n.ai?.sentiment === 'BEARISH');

  const el = document.getElementById('news-feed');
  if (!filtered.length) {
    el.innerHTML = '<div class="loading">Žádné zprávy pro tento filtr</div>';
    return;
  }

  el.innerHTML = filtered.map(n => {
    const ai = n.ai || {};
    const sentiment = ai.sentiment || 'NEUTRAL';
    const impact = ai.impact || 'LOW';
    const action = ai.action || 'WATCH';

    let cls = '';
    if (n.is_breaking) cls = 'breaking';
    else if (sentiment === 'BULLISH') cls = 'bullish';
    else if (sentiment === 'BEARISH') cls = 'bearish';

    const tickers = (ai.affected_tickers || n.related_tickers || []).slice(0, 4);

    return `
    <div class="news-item ${cls}" onclick="window.open('${n.url}','_blank')">
      <div class="news-header">
        <div class="news-title">${n.title}</div>
        <span class="news-sentiment sent-${sentiment}">${sentiment}</span>
      </div>
      ${ai.reason ? `<div class="news-reason">${ai.reason}</div>` : ''}
      <div class="news-meta">
        <span class="news-source">${n.source}</span>
        <span class="news-time">${formatTime(n.published)}</span>
        <span class="impact-${impact}">● ${impact}</span>
        ${action !== 'WATCH' && action !== 'IGNORE' ? `<span class="action-${action}" style="font-size:10px;font-weight:700">${translateAction(action)}</span>` : ''}
      </div>
      ${tickers.length ? `<div class="news-tickers">${tickers.map(t => `<span class="ticker-tag">${t}</span>`).join('')}</div>` : ''}
    </div>`;
  }).join('');

  // Update alerts ticker
  const breaking = allNews.filter(n => n.is_breaking || n.ai?.impact === 'HIGH');
  if (breaking.length) {
    document.getElementById('alerts-bar').classList.remove('hidden');
    document.getElementById('alerts-ticker').textContent =
      '🔴 BREAKING NEWS: ' + breaking.map(n => n.title).join('  ●  ');
  }
}

// ─── Macro ────────────────────────────────────────────────────
function renderMacro(items) {
  const el = document.getElementById('macro-grid');
  if (!items || !items.length) { el.innerHTML = '<div class="loading">Žádná data</div>'; return; }

  el.innerHTML = items.map(item => {
    if (item.error) return `<div class="macro-item"><span class="macro-name">${item.name}</span><span class="muted">Error</span></div>`;

    const chg = item.change || 0;
    const chgStr = chg >= 0 ? `+${chg.toFixed(3)}` : chg.toFixed(3);
    const chgClass = chg > 0 ? 'positive' : chg < 0 ? 'negative' : 'neutral';
    const ai = item.ai || {};
    const impact = ai.nasdaq_impact || '';

    return `
    <div class="macro-item" title="${ai.reason || ''}">
      <div>
        <div class="macro-name">${item.name}</div>
        <div class="macro-value ${chgClass}">${item.value ?? 'N/A'}</div>
        <div class="macro-change ${chgClass}">${chgStr}</div>
      </div>
      <div class="macro-ai">
        ${impact ? `<div class="sent-${impact}" style="font-size:10px;font-weight:700">${impact}</div>` : ''}
        ${item.note ? `<div style="font-size:9px;color:var(--muted)">${item.note}</div>` : ''}
      </div>
    </div>`;
  }).join('');
}

// ─── Alerts ───────────────────────────────────────────────────
function renderAlerts(alerts) {
  const el = document.getElementById('alerts-list');
  if (!alerts || !alerts.length) {
    el.innerHTML = '<div class="no-alerts">Zatím žádné alerty — čekám na tržní události</div>';
    return;
  }
  el.innerHTML = alerts.map(renderAlertItem).join('');
}

function addAlert(alert) {
  const el = document.getElementById('alerts-list');
  const noAlerts = el.querySelector('.no-alerts');
  if (noAlerts) el.innerHTML = '';
  el.insertAdjacentHTML('afterbegin', renderAlertItem(alert));

  // Sound notification
  try {
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    osc.connect(ctx.destination);
    osc.frequency.value = alert.sentiment === 'BEARISH' ? 300 : 600;
    osc.start();
    osc.stop(ctx.currentTime + 0.15);
  } catch {}
}

function renderAlertItem(a) {
  const tickers = (a.tickers || []).slice(0, 3);
  return `
  <div class="alert-item ${a.sentiment}">
    <div class="alert-time">${a.time} · ${a.source || ''}</div>
    <div class="alert-title">${a.title}</div>
    ${tickers.length ? `<div class="news-tickers" style="margin-top:4px">${tickers.map(t => `<span class="ticker-tag">${t}</span>`).join('')}</div>` : ''}
    <span class="alert-action action-${a.action}">${translateAction(a.action)}</span>
  </div>`;
}

// ─── Events ───────────────────────────────────────────────────
async function loadEvents() {
  try {
    const res = await fetch('/api/events');
    const events = await res.json();
    const el = document.getElementById('events-list');
    el.innerHTML = events.map(ev => `
    <div class="event-item">
      <div>
        <div class="event-name">${ev.event}</div>
        <div style="font-size:10px;color:var(--muted)">${ev.description}</div>
      </div>
      <span class="event-impact ev-${ev.impact}">${ev.impact}</span>
    </div>`).join('');
  } catch {}
}

// ─── Modal ────────────────────────────────────────────────────
function showModal(ticker) {
  const stock = fundamentalsData.find(s => s.ticker === ticker);
  if (!stock) return;

  const fmt = (v, prefix = '', suffix = '', decimals = 2) =>
    v != null ? `${prefix}${typeof v === 'number' ? v.toFixed(decimals) : v}${suffix}` : 'N/A';

  const stats = [
    ['Cena', fmt(stock.price, '$')],
    ['Změna', `${stock.change_pct >= 0 ? '+' : ''}${fmt(stock.change_pct, '', '%')}`],
    ['P/E (TTM)', fmt(stock.pe_ratio)],
    ['P/E Forward', fmt(stock.forward_pe)],
    ['EPS (TTM)', fmt(stock.eps, '$')],
    ['EPS Forward', fmt(stock.eps_next_quarter, '$')],
    ['Růst tržeb', fmt(stock.revenue_growth != null ? stock.revenue_growth * 100 : null, '', '%', 1)],
    ['Růst zisku', fmt(stock.earnings_growth != null ? stock.earnings_growth * 100 : null, '', '%', 1)],
    ['Zisková marže', fmt(stock.profit_margin != null ? stock.profit_margin * 100 : null, '', '%', 1)],
    ['Dluh/Vlastní kap.', fmt(stock.debt_to_equity)],
    ['52t. maximum', fmt(stock['52w_high'], '$')],
    ['52t. minimum', fmt(stock['52w_low'], '$')],
    ['Cíl analytiků', fmt(stock.analyst_target, '$')],
    ['Doporučení', (stock.recommendation || 'N/A').toUpperCase()],
  ];

  document.getElementById('modal-body').innerHTML = `
    <div class="modal-ticker">${stock.ticker}</div>
    <div class="modal-name">${stock.name || ''} · ${stock.sector || ''}</div>
    <div class="modal-grid">
      ${stats.map(([label, value]) => `
        <div class="modal-stat">
          <div class="modal-stat-label">${label}</div>
          <div class="modal-stat-value">${value}</div>
        </div>`).join('')}
    </div>`;

  document.getElementById('modal').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('modal').classList.add('hidden');
}

document.getElementById('modal').addEventListener('click', e => {
  if (e.target === document.getElementById('modal')) closeModal();
});

// ─── Překlady ─────────────────────────────────────────────────
function translateAction(action) {
  const map = {
    'BUY_SIGNAL': '🟢 KOUPIT',
    'SELL_SIGNAL': '🔴 PRODAT',
    'WATCH': '👁 SLEDOVAT',
    'IGNORE': 'IGNOROVAT',
  };
  return map[action] || action;
}

function translateSentiment(s) {
  return { 'BULLISH': 'BÝČÍ', 'BEARISH': 'MEDVĚDÍ', 'NEUTRAL': 'NEUTRÁLNÍ' }[s] || s;
}

// ─── Helpers ──────────────────────────────────────────────────
function formatTime(str) {
  if (!str) return '';
  try {
    const d = new Date(str);
    if (isNaN(d)) return str.split('T')[0] || str;
    const diff = Date.now() - d;
    if (diff < 3600000) return 'před ' + Math.floor(diff / 60000) + ' min';
    if (diff < 86400000) return 'před ' + Math.floor(diff / 3600000) + ' hod';
    return d.toLocaleDateString();
  } catch { return str; }
}

async function refreshAll() {
  document.querySelector('.btn-refresh').textContent = '↻ ...';
  await fetch('/api/refresh');
  setTimeout(() => { document.querySelector('.btn-refresh').textContent = '↻'; }, 2000);
}

// ─── Mobile Tabs ─────────────────────────────────────────────
function showTab(name) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));

  const content = document.getElementById('tab-' + name);
  if (content) content.classList.add('active');

  const btn = document.querySelector(`[data-tab="${name}"]`);
  if (btn) btn.classList.add('active');
}

// ─── PWA Install ─────────────────────────────────────────────
let _installPrompt = null;

window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault();
  _installPrompt = e;
  document.getElementById('install-banner').classList.remove('hidden');
});

async function installPWA() {
  if (!_installPrompt) return;
  _installPrompt.prompt();
  const { outcome } = await _installPrompt.userChoice;
  if (outcome === 'accepted') {
    document.getElementById('install-banner').classList.add('hidden');
  }
  _installPrompt = null;
}

window.addEventListener('appinstalled', () => {
  document.getElementById('install-banner').classList.add('hidden');
});

// ─── Service Worker ───────────────────────────────────────────
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/sw.js')
    .then(reg => console.log('SW registered', reg.scope))
    .catch(err => console.warn('SW failed', err));
}

// ─── Notifications ────────────────────────────────────────────
async function requestNotifications() {
  if ('Notification' in window && Notification.permission === 'default') {
    await Notification.requestPermission();
  }
}

function sendNotification(title, body) {
  if (Notification.permission === 'granted') {
    new Notification(title, {
      body,
      icon: '/static/icon-192.png',
      badge: '/static/icon-192.png',
    });
  }
}

// Override addAlert to also send system notification
const _origAddAlert = addAlert;
window.addAlert = function(alert) {
  _origAddAlert(alert);
  if (document.hidden) {
    sendNotification(
      `${alert.sentiment} — ${alert.action.replace('_', ' ')}`,
      alert.title
    );
  }
};

// ─── Init ─────────────────────────────────────────────────────
connectWS();
loadEvents();
requestNotifications();
