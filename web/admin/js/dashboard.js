/* Dashboard — KPIs + recent events */

registerPage('dashboard', loadDashboard);

async function loadDashboard() {
  const page = $('page-dashboard');
  page.innerHTML = loadingHtml();
  try {
    const data = await api('GET', '/admin/dashboard');
    renderDashboard(data);
  } catch (err) {
    page.innerHTML = `<div class="alert error">Не удалось загрузить дашборд: ${escHtml(err.message)}</div>`;
  }
}

function renderDashboard(data) {
  const kpi = data.kpi || {};
  const events = data.events || [];

  $('page-dashboard').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Дашборд</h1>
        <p class="page-subtitle">Обзор ключевых метрик системы</p>
      </div>
      <button class="btn btn-secondary btn-sm" onclick="loadDashboard()">
        ${iconSvg('refresh', 14)} Обновить
      </button>
    </div>

    <div class="stats-grid">
      <div class="card stat-card">
        <div class="stat-icon blue">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        </div>
        <div class="stat-val">${kpi.checks_today ?? 0}</div>
        <div class="stat-label">Проверок сегодня</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon green">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        </div>
        <div class="stat-val">${kpi.checks_7d ?? 0}</div>
        <div class="stat-label">Проверок за 7 дней</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon yellow">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
        </div>
        <div class="stat-val">${kpi.payments_today ?? 0}</div>
        <div class="stat-label">Платежей сегодня</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon red">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
        </div>
        <div class="stat-val">${kpi.payments_7d ?? 0}</div>
        <div class="stat-label">Платежей за 7 дней</div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Последние события</h3>
      </div>
      ${events.length ? renderEventList(events) : emptyHtml('Нет событий', 'Аудит-лог пока пуст')}
    </div>`;
}

function renderEventList(events) {
  return `<div class="event-list">${events.map(e => `
    <div class="event-item">
      <div class="event-dot"></div>
      <div class="event-text">
        <strong>${escHtml(humanAction(e.action))}</strong>
        ${e.entity_type ? ` — ${escHtml(humanEntity(e.entity_type))}` : ''}
        ${e.entity_id ? ` #${escHtml(String(e.entity_id))}` : ''}
      </div>
      <span class="event-time">${formatDate(e.created_at)}</span>
    </div>`).join('')}
  </div>`;
}
