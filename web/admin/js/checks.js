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
    const rs = data.report_summary;

    const fileRow = (label, f) => f
      ? `<div><strong>${label}:</strong> ${escHtml(f.name)} (${(f.size / 1024).toFixed(1)} KB)
          <a href="/api/files/${f.id}/download" class="btn btn-sm btn-secondary" style="margin-left:8px">${iconSvg('download', 12)} Скачать</a></div>`
      : `<div><strong>${label}:</strong> —</div>`;

    const reportSection = rs ? `
      <div>
        <div class="form-label" style="margin-bottom:8px">Результат проверки</div>
        <div style="display:flex;gap:16px;flex-wrap:wrap">
          <div style="text-align:center;padding:8px 14px;background:#fef2f2;border-radius:8px;min-width:80px">
            <div style="font-size:20px;font-weight:700;color:var(--danger)">${rs.errors}</div>
            <div style="font-size:11px;color:var(--text-muted)">Ошибок</div>
          </div>
          <div style="text-align:center;padding:8px 14px;background:#fffbeb;border-radius:8px;min-width:80px">
            <div style="font-size:20px;font-weight:700;color:var(--warn)">${rs.warnings}</div>
            <div style="font-size:11px;color:var(--text-muted)">Предупр.</div>
          </div>
          <div style="text-align:center;padding:8px 14px;background:#f0fdf4;border-radius:8px;min-width:80px">
            <div style="font-size:20px;font-weight:700;color:var(--success)">${rs.fixed}</div>
            <div style="font-size:11px;color:var(--text-muted)">Исправл.</div>
          </div>
          <div style="text-align:center;padding:8px 14px;background:#f8fafc;border-radius:8px;min-width:80px">
            <div style="font-size:20px;font-weight:700;color:var(--text-secondary)">${rs.findings_count}</div>
            <div style="font-size:11px;color:var(--text-muted)">Всего</div>
          </div>
        </div>
        ${rs.check_errors && rs.check_errors.length ? `
          <div style="margin-top:10px;padding:10px;background:#fef2f2;border-radius:8px;border:1px solid #fecaca">
            <div style="font-size:12px;font-weight:600;color:var(--danger);margin-bottom:4px">Внутренние ошибки проверок:</div>
            ${rs.check_errors.map(e => `<div style="font-size:12px;color:var(--danger)">• ${escHtml(e)}</div>`).join('')}
          </div>` : ''}
      </div>` : '';

    const errorLogs = logs.filter(l => l.level === 'error');
    const warnLogs = logs.filter(l => l.level === 'warning');
    const infoLogs = logs.filter(l => l.level === 'info');

    const logColor = level => level === 'error' ? 'var(--danger)' : level === 'warning' ? 'var(--warn)' : 'var(--text-muted)';
    const logBg = level => level === 'error' ? '#fef2f2' : level === 'warning' ? '#fffbeb' : '#f8fafc';

    const body = `
      <div style="display:flex;flex-direction:column;gap:14px">
        <div class="form-row">
          <div><div class="form-label">Статус</div>${statusBadge(c.status)}</div>
          <div><div class="form-label">Создано</div>${formatDate(c.created_at)}</div>
          <div><div class="form-label">Завершено</div>${formatDate(c.finished_at)}</div>
        </div>
        ${c.user_id ? `<div>
          <div class="form-label">Пользователь</div>
          <div>${c.user ? entityTag('user', c.user_id, c.user.username ? '@' + c.user.username : '#' + c.user_id) : entityTag('user', c.user_id, '#' + c.user_id)}</div>
        </div>` : ''}
        ${c.gost_id || c.gost ? `<div>
          <div class="form-label">ГОСТ</div>
          <div>${c.gost ? entityTag('gost', c.gost.id || c.gost_id, c.gost.name) : entityTag('gost', c.gost_id, '#' + c.gost_id)}</div>
        </div>` : ''}
        ${reportSection}
        <div>
          <div class="form-label" style="margin-bottom:6px">Файлы</div>
          ${fileRow('Исходный', files.input)}
          ${fileRow('Отчёт', files.report)}
          ${fileRow('Результат', files.output)}
        </div>
        ${logs.length ? `
          <div>
            <div class="form-label" style="margin-bottom:8px">Логи проверки (${logs.length})</div>
            <div style="max-height:300px;overflow-y:auto;font-size:12px;font-family:monospace;border-radius:8px;border:1px solid #e2e8f0">
              ${logs.map(l => `<div style="padding:6px 12px;background:${logBg(l.level)};border-bottom:1px solid #e2e8f0">
                <span style="color:${logColor(l.level)};font-weight:600">[${escHtml(l.level)}]</span>
                <span style="white-space:pre-wrap">${escHtml(l.message)}</span>
                <span style="color:var(--text-muted);font-size:10px;float:right">${formatDate(l.created_at)}</span>
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
