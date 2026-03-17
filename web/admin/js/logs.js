/* Logs / Audit — shows events from dashboard endpoint */

registerPage('logs', loadLogs);

async function loadLogs() {
  const page = $('page-logs');
  page.innerHTML = loadingHtml();
  try {
    const data = await api('GET', '/admin/dashboard');
    renderLogs(data.events || []);
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderLogs(events) {
  $('page-logs').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Логи и аудит</h1>
        <p class="page-subtitle">Последние 20 действий администраторов</p>
      </div>
      <button class="btn btn-secondary btn-sm" onclick="loadLogs()">
        ${iconSvg('refresh', 14)} Обновить
      </button>
    </div>
    ${events.length ? logsTable(events) : emptyHtml('Нет событий', 'Аудит-лог пока пуст')}`;
}

function logsTable(events) {
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th>
          <th>Действие</th>
          <th>Объект</th>
          <th>ID</th>
          <th>Дата</th>
        </tr></thead>
        <tbody>
          ${events.map(e => `<tr>
            <td>${e.id}</td>
            <td><strong>${escHtml(humanAction(e.action))}</strong></td>
            <td>${escHtml(humanEntity(e.entity_type))}</td>
            <td><code>${escHtml(String(e.entity_id || '—'))}</code></td>
            <td style="white-space:nowrap">${formatDate(e.created_at)}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}
