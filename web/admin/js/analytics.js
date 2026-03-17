/* Analytics page — overview, user detail, event feed */

registerPage('analytics', loadAnalytics);

let _analyticsTab = 'overview';
let _analyticsUsersPage = 1;
let _analyticsUsersFilter = null;
let _analyticsUsersSort = 'last_active';

async function loadAnalytics() {
  const page = $('page-analytics');
  page.innerHTML = loadingHtml();
  renderAnalyticsTabs(page);
  await switchAnalyticsTab(_analyticsTab);
}

function renderAnalyticsTabs(container) {
  const tabs = [
    { id: 'overview', label: 'Обзор' },
    { id: 'users', label: 'Пользователи' },
    { id: 'menu', label: 'Меню' },
    { id: 'events', label: 'Типы событий' },
    { id: 'retention', label: 'Удержание' },
  ];
  container.innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Аналитика</h1>
        <p class="page-subtitle">Детальная статистика активности пользователей</p>
      </div>
      <button class="btn btn-secondary btn-sm" onclick="loadAnalytics()">
        ${iconSvg('refresh', 14)} Обновить
      </button>
    </div>
    <div class="analytics-tabs">
      ${tabs.map(t => `<button class="analytics-tab${t.id === _analyticsTab ? ' active' : ''}" onclick="switchAnalyticsTab('${t.id}')">${t.label}</button>`).join('')}
    </div>
    <div id="analytics-content">${loadingHtml()}</div>`;
}

async function switchAnalyticsTab(tabId) {
  _analyticsTab = tabId;
  document.querySelectorAll('.analytics-tab').forEach(t => {
    t.classList.toggle('active', t.textContent.trim() === {
      overview: 'Обзор', users: 'Пользователи', menu: 'Меню',
      events: 'Типы событий', retention: 'Удержание',
    }[tabId]);
  });
  const container = $('analytics-content');
  if (!container) return;
  container.innerHTML = loadingHtml();
  try {
    if (tabId === 'overview') await renderOverviewTab(container);
    else if (tabId === 'users') await renderUsersTab(container);
    else if (tabId === 'menu') await renderMenuTab(container);
    else if (tabId === 'events') await renderEventsTab(container);
    else if (tabId === 'retention') await renderRetentionTab(container);
  } catch (err) {
    container.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

/* ========== OVERVIEW TAB ========== */

async function renderOverviewTab(container) {
  const [overview, activity, newUsers, sessions] = await Promise.all([
    api('GET', '/admin/analytics/overview'),
    api('GET', '/admin/analytics/activity-chart?days=30'),
    api('GET', '/admin/analytics/new-users-chart?days=30'),
    api('GET', '/admin/analytics/sessions?days=7'),
  ]);

  container.innerHTML = `
    <div class="kpi-grid">
      ${kpiCard('Всего пользователей', overview.total_users, 'blue')}
      ${kpiCard('Активных сегодня', overview.active_today, 'green')}
      ${kpiCard('Активных за неделю', overview.active_week, 'green')}
      ${kpiCard('Активных за месяц', overview.active_month, 'blue')}
      ${kpiCard('Новых сегодня', overview.new_users_today, 'yellow')}
      ${kpiCard('Новых за неделю', overview.new_users_week, 'yellow')}
      ${kpiCard('Заблокировали бота', overview.blocked_users, 'red')}
      ${kpiCard('Удалённые аккаунты', overview.deleted_accounts, 'red')}
      ${kpiCard('Событий сегодня', overview.events_today, 'blue')}
      ${kpiCard('Событий всего', overview.total_events, 'blue')}
      ${kpiCard('Сессий за 7д', sessions.total_sessions, 'green')}
      ${kpiCard('Событий/сессию', sessions.avg_events_per_session, 'green')}
    </div>
    <div class="chart-grid">
      <div class="card chart-card">
        <div class="card-header"><h3 class="card-title">DAU и события (30 дней)</h3></div>
        <canvas id="chart-activity"></canvas>
      </div>
      <div class="card chart-card">
        <div class="card-header"><h3 class="card-title">Новые пользователи (30 дней)</h3></div>
        <canvas id="chart-new-users"></canvas>
      </div>
    </div>`;

  renderActivityChart(activity);
  renderNewUsersChart(newUsers);
}

function kpiCard(label, value, color) {
  return `<div class="card kpi-card">
    <div class="kpi-val" style="color: var(--${color === 'blue' ? 'accent' : color === 'green' ? 'success' : color === 'red' ? 'danger' : 'warn'})">${value ?? 0}</div>
    <div class="kpi-label">${label}</div>
  </div>`;
}

/* ========== USERS TAB ========== */

async function renderUsersTab(container) {
  const perPage = 50;
  const offset = (_analyticsUsersPage - 1) * perPage;
  let url = `/admin/analytics/users?limit=${perPage}&offset=${offset}&sort=${_analyticsUsersSort}`;
  if (_analyticsUsersFilter) url += `&status=${_analyticsUsersFilter}`;

  const data = await api('GET', url);

  container.innerHTML = `
    <div class="toolbar">
      <select class="filter-select" onchange="analyticsFilterUsers(this.value)">
        <option value=""${!_analyticsUsersFilter ? ' selected' : ''}>Все</option>
        <option value="active"${_analyticsUsersFilter === 'active' ? ' selected' : ''}>Активные</option>
        <option value="blocked"${_analyticsUsersFilter === 'blocked' ? ' selected' : ''}>Заблокировали</option>
        <option value="deleted"${_analyticsUsersFilter === 'deleted' ? ' selected' : ''}>Удалённые</option>
        <option value="inactive"${_analyticsUsersFilter === 'inactive' ? ' selected' : ''}>Неактивные</option>
      </select>
      <select class="filter-select" onchange="analyticsSortUsers(this.value)">
        <option value="last_active"${_analyticsUsersSort === 'last_active' ? ' selected' : ''}>По активности</option>
        <option value="total_events"${_analyticsUsersSort === 'total_events' ? ' selected' : ''}>По событиям</option>
        <option value="created"${_analyticsUsersSort === 'created' ? ' selected' : ''}>По дате регистрации</option>
      </select>
      <span style="font-size:12px;color:var(--text-muted)">Всего: ${data.total}</span>
    </div>
    ${data.items.length ? renderUsersTable(data.items) : emptyHtml('Нет пользователей', '')}
    ${analyticsUsersPagination(data.total, perPage)}`;
}

function renderUsersTable(users) {
  return `<div class="table-wrap"><table class="data-table">
    <thead><tr>
      <th>ID</th><th>Telegram</th><th>Имя</th><th>Username</th>
      <th>Статус</th><th>Последняя активность</th><th>Событий</th><th>Сессий</th><th></th>
    </tr></thead>
    <tbody>
      ${users.map(u => `<tr>
        <td data-label="ID">${u.id}</td>
        <td data-label="TG ID">${u.telegram_id}</td>
        <td data-label="Имя">${escHtml(u.first_name || '—')}</td>
        <td data-label="Username">${u.username ? '@' + escHtml(u.username) : '—'}</td>
        <td data-label="Статус">${userStatusBadge(u)}</td>
        <td data-label="Последняя активность">${formatDate(u.last_active_at)}</td>
        <td data-label="Событий">${u.total_events}</td>
        <td data-label="Сессий">${u.total_sessions}</td>
        <td data-label=""><button class="btn btn-ghost btn-sm" onclick="viewUserEvents(${u.id}, '${escHtml(u.first_name || u.username || '#' + u.id)}')">${iconSvg('eye', 14)} Лог</button></td>
      </tr>`).join('')}
    </tbody>
  </table></div>`;
}

function userStatusBadge(u) {
  if (u.is_deleted) return '<span class="badge status-deleted">Удалён</span>';
  if (u.is_blocked) return '<span class="badge status-blocked">Заблокировал</span>';
  if (!u.is_active) return '<span class="badge status-inactive">Неактивен</span>';
  return '<span class="badge status-active">Активен</span>';
}

function analyticsUsersPagination(total, perPage) {
  const totalPages = Math.ceil(total / perPage) || 1;
  if (totalPages <= 1) return '';
  const pages = [];
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || (i >= _analyticsUsersPage - 2 && i <= _analyticsUsersPage + 2)) {
      pages.push(i);
    } else if (pages.length && pages[pages.length - 1] !== '…') {
      pages.push('…');
    }
  }
  return `<div class="pagination">
    ${pages.map(p => p === '…'
      ? '<span class="pg-dots">…</span>'
      : `<button class="pg-btn${p === _analyticsUsersPage ? ' active' : ''}" onclick="analyticsUsersGoPage(${p})">${p}</button>`
    ).join('')}
    <span class="pg-info">${total} записей</span>
  </div>`;
}

function analyticsUsersGoPage(p) {
  _analyticsUsersPage = p;
  switchAnalyticsTab('users');
}

function analyticsFilterUsers(val) {
  _analyticsUsersFilter = val || null;
  _analyticsUsersPage = 1;
  switchAnalyticsTab('users');
}

function analyticsSortUsers(val) {
  _analyticsUsersSort = val;
  _analyticsUsersPage = 1;
  switchAnalyticsTab('users');
}

/* ========== USER EVENT LOG ========== */

async function viewUserEvents(userId, userName) {
  const events = await api('GET', `/admin/analytics/users/${userId}/events?limit=200`);
  const body = events.length
    ? `<div class="timeline">${events.map(e => {
        const icon = { lifecycle: '🔄', navigation: '📍', action: '⚡', message: '💬', system: '⚙️' }[e.event_category] || '📌';
        const dataStr = e.event_data ? Object.entries(e.event_data).map(([k, v]) => `${k}: ${v}`).join(', ') : '';
        return `<div class="timeline-item">
          <div class="timeline-dot ${e.event_category}">${icon}</div>
          <div class="timeline-content">
            <div class="timeline-type">${escHtml(eventTypeLabel(e.event_type))}</div>
            ${dataStr ? `<div class="timeline-data">${escHtml(dataStr)}</div>` : ''}
            <div class="timeline-time">${formatDate(e.created_at)}</div>
          </div>
        </div>`;
      }).join('')}</div>`
    : emptyHtml('Нет событий', 'У этого пользователя пока нет записанных действий');

  openModal(`Лог действий — ${userName}`, `<div style="max-height:60vh;overflow-y:auto">${body}</div>`, '');
}

function eventTypeLabel(t) {
  const map = {
    bot_start: 'Старт бота', menu_click: 'Клик по меню', nav_home: 'Главное меню',
    command: 'Команда', callback_query: 'Callback', message_sent: 'Сообщение',
    bot_blocked: 'Заблокировал бота', bot_unblocked: 'Разблокировал бота',
    account_deleted: 'Удалил аккаунт', miniapp_open: 'Открыл Mini App',
    check_started: 'Начал проверку', check_completed: 'Проверка завершена',
    file_uploaded: 'Загрузил файл', payment_started: 'Начал оплату',
    payment_completed: 'Оплата завершена',
  };
  return map[t] || t;
}

/* ========== EXPOSE GLOBALLY ========== */
window.loadAnalytics = loadAnalytics;
window.switchAnalyticsTab = switchAnalyticsTab;
window.analyticsUsersGoPage = analyticsUsersGoPage;
window.analyticsFilterUsers = analyticsFilterUsers;
window.analyticsSortUsers = analyticsSortUsers;
window.viewUserEvents = viewUserEvents;
