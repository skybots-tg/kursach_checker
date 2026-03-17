/* Logs / Audit — events with entity tags, pagination */

registerPage('logs', loadLogs);

let _logsData = [];
let _logsPage = 1;

async function loadLogs() {
  const page = $('page-logs');
  page.innerHTML = loadingHtml();
  try {
    const data = await api('GET', '/admin/dashboard');
    _logsData = data.events || [];
    _logsPage = 1;
    renderLogs();
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderLogs() {
  $('page-logs').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Логи и аудит</h1>
        <p class="page-subtitle">Последние действия администраторов (${_logsData.length})</p>
      </div>
      <button class="btn btn-secondary btn-sm" onclick="loadLogs()">
        ${iconSvg('refresh', 14)} Обновить
      </button>
    </div>
    <div id="logs-table-area"></div>`;
  renderLogsTable();
}

function renderLogsTable() {
  const paged = paginate(_logsData, _logsPage);
  _logsPage = paged.page;
  const area = $('logs-table-area');
  if (!area) return;
  area.innerHTML = paged.items.length
    ? logsTable(paged.items) + paginationHtml(paged, 'logsGoPage')
    : emptyHtml('Нет событий', 'Аудит-лог пока пуст');
}

function logsGoPage(p) { _logsPage = p; renderLogsTable(); }

function logsTable(events) {
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th><th>Действие</th><th>Объект</th>
          <th>ID объекта</th><th>Дата</th>
        </tr></thead>
        <tbody>
          ${events.map(e => `<tr>
            <td data-label="ID">${e.id}</td>
            <td data-label="Действие"><strong>${escHtml(humanAction(e.action))}</strong></td>
            <td data-label="Объект">${escHtml(humanEntity(e.entity_type))}</td>
            <td data-label="ID объекта">${e.entity_id
              ? entityTag(e.entity_type, e.entity_id, '#' + e.entity_id)
              : '—'}</td>
            <td data-label="Дата" style="white-space:nowrap">${formatDate(e.created_at)}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

window.logsGoPage = logsGoPage;
