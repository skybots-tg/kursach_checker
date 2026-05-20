/* UTM tracking links — create, copy, view stats */

registerPage('utm', loadUtm);

let _utmStats = null;
let _utmDaily = [];
let _utmDays = 30;
let _utmTab = 'overview';

async function loadUtm() {
  const page = $('page-utm');
  page.innerHTML = loadingHtml();
  try {
    await refreshUtm();
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

async function refreshUtm() {
  const [stats, daily] = await Promise.all([
    api('GET', `/admin/utm/stats?days=${_utmDays}`),
    api('GET', `/admin/utm/daily?days=${_utmDays}`),
  ]);
  _utmStats = stats;
  _utmDaily = daily;
  renderUtm();
}

function renderUtm() {
  const stats = _utmStats || {};
  const sources = stats.sources || [];

  $('page-utm').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">UTM-ссылки</h1>
        <p class="page-subtitle">Рекламные метки для отслеживания источников трафика</p>
      </div>
      <button class="btn btn-primary btn-sm" onclick="openUtmGenerator()">
        ${iconSvg('plus', 14)} Создать ссылку
      </button>
    </div>

    <div class="toolbar" style="margin-bottom:16px">
      <select class="filter-select" onchange="utmChangeDays(this.value)">
        <option value="7"${_utmDays === 7 ? ' selected' : ''}>7 дней</option>
        <option value="14"${_utmDays === 14 ? ' selected' : ''}>14 дней</option>
        <option value="30"${_utmDays === 30 ? ' selected' : ''}>30 дней</option>
        <option value="90"${_utmDays === 90 ? ' selected' : ''}>90 дней</option>
        <option value="365"${_utmDays === 365 ? ' selected' : ''}>Год</option>
      </select>
      <button class="btn btn-secondary btn-sm" onclick="refreshUtm()">
        ${iconSvg('refresh', 14)} Обновить
      </button>
    </div>

    ${utmStatsGrid(stats)}

    <div class="analytics-tabs" style="margin-top:20px">
      <button class="analytics-tab${_utmTab === 'overview' ? ' active' : ''}" onclick="switchUtmTab('overview')">Сводка</button>
      <button class="analytics-tab${_utmTab === 'chart' ? ' active' : ''}" onclick="switchUtmTab('chart')">График</button>
    </div>
    <div id="utm-content"></div>
  `;
  switchUtmTab(_utmTab);
}

function switchUtmTab(tab) {
  _utmTab = tab;
  document.querySelectorAll('#page-utm .analytics-tab').forEach(t => {
    t.classList.toggle('active', t.textContent.trim() === {overview:'Сводка', chart:'График'}[tab]);
  });
  const c = $('utm-content');
  if (!c) return;
  if (tab === 'overview') renderUtmTable(c);
  else if (tab === 'chart') renderUtmChart(c);
}

function utmStatsGrid(stats) {
  return `<div class="stats-grid">
    <div class="card stat-card">
      <div class="stat-icon blue">${iconSvg('link', 20)}</div>
      <div class="stat-val">${(stats.sources || []).length}</div>
      <div class="stat-label">Активных меток</div>
    </div>
    <div class="card stat-card">
      <div class="stat-icon green">${iconSvg('users', 20)}</div>
      <div class="stat-val">${stats.total_utm_users ?? 0}</div>
      <div class="stat-label">Пришли по меткам</div>
    </div>
    <div class="card stat-card">
      <div class="stat-icon yellow">${iconSvg('users', 20)}</div>
      <div class="stat-val">${stats.total_organic_users ?? 0}</div>
      <div class="stat-label">Органические</div>
    </div>
    <div class="card stat-card">
      <div class="stat-icon blue">${iconSvg('percent', 20)}</div>
      <div class="stat-val">${utmPercent(stats)}%</div>
      <div class="stat-label">Доля UTM</div>
    </div>
  </div>`;
}

function utmPercent(stats) {
  const total = (stats.total_utm_users || 0) + (stats.total_organic_users || 0);
  if (!total) return 0;
  return Math.round((stats.total_utm_users || 0) / total * 100);
}

function renderUtmTable(container) {
  const sources = (_utmStats || {}).sources || [];
  if (!sources.length) {
    container.innerHTML = emptyHtml(
      'Нет данных по UTM',
      'Создайте ссылку с меткой и поделитесь ей — статистика появится здесь'
    );
    return;
  }

  container.innerHTML = `<div class="card" style="padding:0;overflow:hidden;margin-top:12px">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>Метка (utm_source)</th>
          <th>Пользователей</th>
          <th>Первый приход</th>
          <th>Последний приход</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${sources.map(s => utmRow(s)).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function utmRow(s) {
  return `<tr>
    <td data-label="Метка"><code style="background:var(--bg-hover);padding:2px 8px;border-radius:4px;font-weight:600">${escHtml(s.utm_source)}</code></td>
    <td data-label="Пользователей"><strong>${s.total_users}</strong></td>
    <td data-label="Первый приход" style="white-space:nowrap">${formatDate(s.first_seen)}</td>
    <td data-label="Последний приход" style="white-space:nowrap">${formatDate(s.last_seen)}</td>
    <td data-label="" class="actions-cell">
      <button class="btn btn-ghost btn-sm" onclick="utmCopyLink('${escHtml(s.utm_source)}')" title="Скопировать ссылку">
        ${iconSvg('copy', 14)} Ссылка
      </button>
      <button class="btn btn-ghost btn-sm" onclick="utmViewUsers('${escHtml(s.utm_source)}')" title="Список пользователей">
        ${iconSvg('eye', 14)} Юзеры
      </button>
    </td>
  </tr>`;
}

function renderUtmChart(container) {
  container.innerHTML = `<div class="card chart-card" style="margin-top:12px">
    <div class="card-header"><h3 class="card-title">Новые пользователи по источникам</h3></div>
    <canvas id="chart-utm-daily"></canvas>
  </div>`;

  const data = _utmDaily || [];
  if (!data.length) return;

  const dates = [...new Set(data.map(d => d.date))].sort();
  const sourcesSet = [...new Set(data.map(d => d.source))];

  const palette = [
    '#6366f1','#22c55e','#f59e0b','#ef4444','#3b82f6',
    '#ec4899','#14b8a6','#a855f7','#f97316','#06b6d4',
  ];

  const bySource = {};
  data.forEach(d => {
    if (!bySource[d.source]) bySource[d.source] = {};
    bySource[d.source][d.date] = d.count;
  });

  const datasets = sourcesSet.map((src, i) => ({
    label: src === '__organic__' ? 'Органика' : src,
    data: dates.map(dt => bySource[src]?.[dt] || 0),
    borderColor: palette[i % palette.length],
    backgroundColor: palette[i % palette.length] + '33',
    fill: true,
    tension: 0.3,
  }));

  const canvas = document.getElementById('chart-utm-daily');
  if (!canvas) return;
  new Chart(canvas, {
    type: 'line',
    data: { labels: dates, datasets },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } },
      },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
      },
    },
  });
}

/* ========== GENERATE LINK ========== */

function openUtmGenerator() {
  const body = `
    <div class="form-group">
      <label class="form-label">Метка (латиница, цифры, _ и -)</label>
      <input class="form-input" id="utm-tag-input" placeholder="например: vk_ads_june"
        maxlength="128" oninput="utmPreviewLink()">
      <div class="form-hint">Это значение подставляется в ?start=<метка></div>
    </div>
    <div class="form-group">
      <label class="form-label">Готовая ссылка</label>
      <div style="display:flex;gap:8px;align-items:center">
        <input class="form-input" id="utm-link-output" readonly style="flex:1;font-family:monospace">
        <button class="btn btn-secondary btn-sm" onclick="utmCopyGenerated()">
          ${iconSvg('copy', 14)}
        </button>
      </div>
    </div>
    <div class="form-group" style="margin-top:12px">
      <label class="form-label">Популярные шаблоны</label>
      <div style="display:flex;flex-wrap:wrap;gap:6px">
        ${['vk_ads', 'inst_reels', 'tg_channel', 'avito', 'yandex', 'friends'].map(t =>
          `<button class="btn btn-ghost btn-sm" onclick="utmSetTag('${t}')" style="font-size:12px">${t}</button>`
        ).join('')}
      </div>
    </div>`;
  const footer = `<button class="btn btn-ghost" onclick="closeModal()">Закрыть</button>`;
  openModal('Создать UTM-ссылку', body, footer);
  utmPreviewLink();
}

function utmSetTag(tag) {
  const el = $('utm-tag-input');
  if (el) { el.value = tag; utmPreviewLink(); }
}

async function utmPreviewLink() {
  const tag = (getVal('utm-tag-input') || '').trim();
  const output = $('utm-link-output');
  if (!output) return;
  if (!tag) { output.value = ''; return; }
  try {
    const res = await api('GET', `/admin/utm/generate?tag=${encodeURIComponent(tag)}`);
    output.value = res.link || '';
  } catch { output.value = ''; }
}

function utmCopyGenerated() {
  const val = getVal('utm-link-output');
  if (val) { navigator.clipboard.writeText(val); toast('Ссылка скопирована', 'success'); }
}

async function utmCopyLink(tag) {
  try {
    const res = await api('GET', `/admin/utm/generate?tag=${encodeURIComponent(tag)}`);
    if (res.link) { navigator.clipboard.writeText(res.link); toast('Ссылка скопирована', 'success'); }
  } catch (e) { toast('Ошибка: ' + e.message, 'error'); }
}

async function utmViewUsers(source) {
  try {
    const data = await api('GET', `/admin/utm/users?source=${encodeURIComponent(source)}&limit=100`);
    const items = data.items || [];
    const body = items.length
      ? `<div style="max-height:50vh;overflow-y:auto"><table class="data-table">
          <thead><tr><th>ID</th><th>Telegram</th><th>Имя</th><th>Username</th><th>Дата</th></tr></thead>
          <tbody>${items.map(u => `<tr>
            <td>${u.id}</td>
            <td>${u.telegram_id}</td>
            <td>${escHtml(u.first_name || '—')}</td>
            <td>${u.username ? '@' + escHtml(u.username) : '—'}</td>
            <td style="white-space:nowrap">${formatDate(u.created_at)}</td>
          </tr>`).join('')}</tbody>
        </table></div>
        <p style="margin-top:8px;font-size:12px;color:var(--text-muted)">Всего: ${data.total}</p>`
      : emptyHtml('Нет пользователей', 'По этой метке пока никто не пришёл');
    openModal(`Пользователи — ${source}`, body, `<button class="btn btn-ghost" onclick="closeModal()">Закрыть</button>`);
  } catch (e) { toast('Ошибка: ' + e.message, 'error'); }
}

function utmChangeDays(val) {
  _utmDays = parseInt(val, 10) || 30;
  refreshUtm().catch(e => toast('Ошибка: ' + e.message, 'error'));
}

/* ========== EXPOSE ========== */
window.loadUtm = loadUtm;
window.refreshUtm = refreshUtm;
window.switchUtmTab = switchUtmTab;
window.openUtmGenerator = openUtmGenerator;
window.utmSetTag = utmSetTag;
window.utmPreviewLink = utmPreviewLink;
window.utmCopyGenerated = utmCopyGenerated;
window.utmCopyLink = utmCopyLink;
window.utmViewUsers = utmViewUsers;
window.utmChangeDays = utmChangeDays;
