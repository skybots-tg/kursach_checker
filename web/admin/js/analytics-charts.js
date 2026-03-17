/* Analytics charts — Chart.js rendering + menu heatmap + events breakdown + retention */

let _chartInstances = {};

function destroyChart(id) {
  if (_chartInstances[id]) {
    _chartInstances[id].destroy();
    delete _chartInstances[id];
  }
}

function createChart(canvasId, config) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  _chartInstances[canvasId] = new Chart(ctx, config);
}

/* ---- Activity chart (DAU + events) ---- */
function renderActivityChart(data) {
  const labels = data.map(d => {
    const parts = d.date.split('-');
    return parts[2] + '.' + parts[1];
  });
  createChart('chart-activity', {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'DAU',
          data: data.map(d => d.dau),
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59,130,246,0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 2,
          pointHoverRadius: 5,
          borderWidth: 2,
          yAxisID: 'y',
        },
        {
          label: 'События',
          data: data.map(d => d.events),
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34,197,94,0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 2,
          pointHoverRadius: 5,
          borderWidth: 2,
          yAxisID: 'y1',
        },
      ],
    },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } } },
      scales: {
        y: { position: 'left', beginAtZero: true, title: { display: true, text: 'DAU' }, grid: { color: '#f1f5f9' } },
        y1: { position: 'right', beginAtZero: true, title: { display: true, text: 'События' }, grid: { display: false } },
        x: { grid: { display: false } },
      },
    },
  });
}

/* ---- New users chart ---- */
function renderNewUsersChart(data) {
  const labels = data.map(d => {
    const parts = d.date.split('-');
    return parts[2] + '.' + parts[1];
  });
  createChart('chart-new-users', {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Новые пользователи',
        data: data.map(d => d.count),
        backgroundColor: 'rgba(245,158,11,0.6)',
        borderColor: '#f59e0b',
        borderWidth: 1,
        borderRadius: 4,
        barPercentage: 0.7,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
        x: { grid: { display: false } },
      },
    },
  });
}

/* ========== MENU HEATMAP TAB ========== */

async function renderMenuTab(container) {
  const data = await api('GET', '/admin/analytics/menu-heatmap?days=30');
  if (!data.length) {
    container.innerHTML = emptyHtml('Нет данных о меню', 'Клики по пунктам меню ещё не записаны');
    return;
  }
  const maxClicks = Math.max(...data.map(d => d.clicks));
  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Популярность пунктов меню (30 дней)</h3>
      </div>
      <div class="heatmap-list">
        <div class="heatmap-row" style="font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:0.05em;color:var(--text-muted)">
          <div>Пункт меню</div><div></div><div style="text-align:right">Кликов</div><div style="text-align:right">Юзеров</div>
        </div>
        ${data.map(d => {
          const pct = maxClicks > 0 ? Math.round(d.clicks / maxClicks * 100) : 0;
          return `<div class="heatmap-row">
            <div class="heatmap-title">${escHtml(d.title || '#' + d.menu_item_id)}</div>
            <div class="heatmap-bar-wrap"><div class="heatmap-bar" style="width:${pct}%"></div></div>
            <div class="heatmap-count">${d.clicks}</div>
            <div class="heatmap-users">${d.unique_users}</div>
          </div>`;
        }).join('')}
      </div>
    </div>`;
}

/* ========== EVENTS BREAKDOWN TAB ========== */

async function renderEventsTab(container) {
  const data = await api('GET', '/admin/analytics/event-breakdown?days=7');
  if (!data.length) {
    container.innerHTML = emptyHtml('Нет событий', 'За последние 7 дней нет записанных событий');
    return;
  }

  container.innerHTML = `
    <div class="chart-grid">
      <div class="card chart-card">
        <div class="card-header"><h3 class="card-title">Распределение событий (7 дней)</h3></div>
        <canvas id="chart-events-pie"></canvas>
      </div>
      <div class="card">
        <div class="card-header"><h3 class="card-title">Детализация по типам</h3></div>
        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>Тип</th><th>Категория</th><th>Количество</th></tr></thead>
          <tbody>
            ${data.map(d => `<tr>
              <td data-label="Тип">${escHtml(eventTypeLabel(d.event_type))}</td>
              <td data-label="Категория"><span class="badge badge-${categoryBadge(d.category)}">${escHtml(d.category)}</span></td>
              <td data-label="Кол-во" style="font-weight:600">${d.count}</td>
            </tr>`).join('')}
          </tbody>
        </table></div>
      </div>
    </div>`;

  renderEventsPieChart(data);
}

function categoryBadge(cat) {
  return { lifecycle: 'success', navigation: 'info', action: 'warn', message: 'primary', system: 'gray' }[cat] || 'gray';
}

function renderEventsPieChart(data) {
  const colors = [
    '#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6',
    '#06b6d4', '#ec4899', '#14b8a6', '#f97316', '#6366f1',
    '#84cc16', '#a855f7',
  ];
  createChart('chart-events-pie', {
    type: 'doughnut',
    data: {
      labels: data.map(d => eventTypeLabel(d.event_type)),
      datasets: [{
        data: data.map(d => d.count),
        backgroundColor: data.map((_, i) => colors[i % colors.length]),
        borderWidth: 2,
        borderColor: '#fff',
      }],
    },
    options: {
      responsive: true,
      cutout: '60%',
      plugins: {
        legend: { position: 'right', labels: { usePointStyle: true, padding: 10, font: { size: 12 } } },
      },
    },
  });
}

/* ========== RETENTION TAB ========== */

async function renderRetentionTab(container) {
  const data = await api('GET', '/admin/analytics/retention?weeks=8');

  container.innerHTML = `
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Удержание по недельным когортам</h3>
      </div>
      <div class="card-desc">Процент пользователей, вернувшихся после первой недели</div>
      <div class="chart-grid" style="margin-bottom:16px">
        <div class="chart-card card" style="margin-bottom:0">
          <canvas id="chart-retention"></canvas>
        </div>
      </div>
      <div class="table-wrap">
        <table class="retention-table">
          <thead><tr>
            <th>Неделя</th><th>Начало когорты</th><th>Размер когорты</th><th>Вернулось</th><th>% удержания</th>
          </tr></thead>
          <tbody>
            ${data.map(d => `<tr>
              <td>W${d.week}</td>
              <td>${d.cohort_start}</td>
              <td>${d.cohort_size}</td>
              <td>${d.returned}</td>
              <td><span class="retention-cell" style="background:${retentionColor(d.rate)}">${d.rate}%</span></td>
            </tr>`).join('')}
          </tbody>
        </table>
      </div>
    </div>`;

  renderRetentionChart(data);
}

function retentionColor(rate) {
  if (rate >= 50) return 'rgba(34,197,94,0.2)';
  if (rate >= 30) return 'rgba(34,197,94,0.12)';
  if (rate >= 15) return 'rgba(245,158,11,0.15)';
  if (rate > 0) return 'rgba(239,68,68,0.1)';
  return '#f8fafc';
}

function renderRetentionChart(data) {
  const labels = data.map(d => 'W' + d.week);
  createChart('chart-retention', {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Размер когорты',
          data: data.map(d => d.cohort_size),
          backgroundColor: 'rgba(59,130,246,0.5)',
          borderColor: '#3b82f6',
          borderWidth: 1,
          borderRadius: 4,
          yAxisID: 'y',
        },
        {
          label: '% удержания',
          data: data.map(d => d.rate),
          type: 'line',
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34,197,94,0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 4,
          pointHoverRadius: 6,
          borderWidth: 2,
          yAxisID: 'y1',
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } } },
      scales: {
        y: { position: 'left', beginAtZero: true, title: { display: true, text: 'Когорта' }, grid: { color: '#f1f5f9' } },
        y1: { position: 'right', beginAtZero: true, max: 100, title: { display: true, text: '%' }, grid: { display: false } },
        x: { grid: { display: false } },
      },
    },
  });
}

/* ---- Expose ---- */
window.renderActivityChart = renderActivityChart;
window.renderNewUsersChart = renderNewUsersChart;
window.renderMenuTab = renderMenuTab;
window.renderEventsTab = renderEventsTab;
window.renderRetentionTab = renderRetentionTab;
