/* Checks — journal with stats, entity tags, pagination, detail */

registerPage('checks', loadChecks);

let _checksData = [];
let _checksPage = 1;

async function loadChecks() {
  const page = $('page-checks');
  page.innerHTML = loadingHtml();
  try {
    const [list, stats] = await Promise.all([
      api('GET', '/admin/checks'),
      api('GET', '/admin/checks/stats/summary'),
    ]);
    _checksData = list;
    _checksPage = 1;
    renderChecks(stats);
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderChecks(stats) {
  $('page-checks').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Проверки</h1>
        <p class="page-subtitle">Журнал всех проверок документов</p>
      </div>
    </div>

    <div class="stats-grid">
      <div class="card stat-card">
        <div class="stat-icon blue">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/></svg>
        </div>
        <div class="stat-val">${stats.total ?? 0}</div>
        <div class="stat-label">Всего проверок</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon green">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <div class="stat-val">${stats.done ?? 0}</div>
        <div class="stat-label">Завершено</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon red">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        </div>
        <div class="stat-val">${stats.errors ?? 0}</div>
        <div class="stat-label">С ошибками</div>
      </div>
    </div>

    <div class="toolbar">
      <select class="filter-select" id="checks-filter" onchange="filterChecks()">
        <option value="">Все статусы</option>
        <option value="queued">В очереди</option>
        <option value="running">Выполняется</option>
        <option value="done">Готово</option>
        <option value="error">Ошибка</option>
      </select>
      <button class="btn btn-secondary btn-sm" onclick="loadChecks()">
        ${iconSvg('refresh', 14)} Обновить
      </button>
    </div>

    <div id="checks-table-area"></div>`;
  renderChecksTable();
}

function renderChecksTable() {
  const paged = paginate(_checksData, _checksPage);
  _checksPage = paged.page;
  const area = $('checks-table-area');
  if (!area) return;
  area.innerHTML = paged.items.length
    ? checksTable(paged.items) + paginationHtml(paged, 'checksGoPage')
    : emptyHtml('Нет проверок', 'Проверки появятся после первого запуска');
}

function checksGoPage(p) { _checksPage = p; renderChecksTable(); }

function checksTable(list) {
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th><th>Пользователь</th><th>ГОСТ</th>
          <th>Статус</th><th>Создано</th><th>Завершено</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(c => `<tr>
            <td data-label="ID">${c.id}</td>
            <td data-label="Пользователь">${c.user
              ? entityTag('user', c.user_id || c.user.id, c.user.username ? '@' + c.user.username : c.user.first_name || 'user')
              : '—'}</td>
            <td data-label="ГОСТ">${c.gost
              ? entityTag('gost', c.gost.id, c.gost.name)
              : '—'}</td>
            <td data-label="Статус">${statusBadge(c.status)}</td>
            <td data-label="Создано" style="white-space:nowrap">${formatDate(c.created_at)}</td>
            <td data-label="Завершено" style="white-space:nowrap">${formatDate(c.finished_at)}</td>
            <td data-label="" class="actions-cell">
              <button class="btn btn-icon btn-sm" title="Подробнее" onclick="viewCheck(${c.id})">
                ${iconSvg('eye', 15)}
              </button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

async function filterChecks() {
  const status = getVal('checks-filter');
  try {
    const url = status ? `/admin/checks?status=${status}` : '/admin/checks';
    const [list, stats] = await Promise.all([
      api('GET', url),
      api('GET', '/admin/checks/stats/summary'),
    ]);
    _checksData = list;
    _checksPage = 1;
    renderChecks(stats);
    if (status) setVal('checks-filter', status);
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

async function viewCheck(id) {
  try {
    const data = await api('GET', `/admin/checks/${id}`);
    const c = data.check || {};
    const files = data.files || {};
    const logs = data.worker_logs || [];

    const fileRow = (label, f) => f
      ? `<div><strong>${label}:</strong> ${escHtml(f.name)} (${(f.size / 1024).toFixed(1)} KB)
          <a href="/api/files/${f.id}/download" class="btn btn-sm btn-secondary" style="margin-left:8px">${iconSvg('download', 12)} Скачать</a></div>`
      : `<div><strong>${label}:</strong> —</div>`;

    const body = `
      <div style="display:flex;flex-direction:column;gap:14px">
        <div class="form-row">
          <div><div class="form-label">Статус</div>${statusBadge(c.status)}</div>
          <div><div class="form-label">Создано</div>${formatDate(c.created_at)}</div>
        </div>
        ${c.user_id ? `<div>
          <div class="form-label">Пользователь</div>
          <div>${entityTag('user', c.user_id, '#' + c.user_id)}</div>
        </div>` : ''}
        ${c.gost_id || c.gost ? `<div>
          <div class="form-label">ГОСТ</div>
          <div>${c.gost ? entityTag('gost', c.gost.id || c.gost_id, c.gost.name) : entityTag('gost', c.gost_id, '#' + c.gost_id)}</div>
        </div>` : ''}
        <div>
          <div class="form-label" style="margin-bottom:6px">Файлы</div>
          ${fileRow('Исходный', files.input)}
          ${fileRow('Отчёт', files.report)}
          ${fileRow('Результат', files.output)}
        </div>
        ${logs.length ? `
          <div>
            <div class="form-label" style="margin-bottom:8px">Worker логи (${logs.length})</div>
            <div style="max-height:200px;overflow-y:auto;font-size:12px;font-family:monospace;background:#f8fafc;padding:12px;border-radius:8px">
              ${logs.map(l => `<div style="margin-bottom:4px">
                <span style="color:${l.level === 'error' ? 'var(--danger)' : l.level === 'warning' ? 'var(--warn)' : 'var(--text-muted)'}">[${escHtml(l.level)}]</span>
                ${escHtml(l.message)}
                <span style="color:var(--text-muted);font-size:10px">${formatDate(l.created_at)}</span>
              </div>`).join('')}
            </div>
          </div>` : ''}
      </div>`;
    openModal(`Проверка #${id}`, body, `<button class="btn btn-ghost" onclick="closeModal()">Закрыть</button>`);
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

window.checksGoPage = checksGoPage;
window.filterChecks = filterChecks;
window.viewCheck = viewCheck;
