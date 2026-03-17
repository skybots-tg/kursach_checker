/* Checks — journal with stats, list, detail */

registerPage('checks', loadChecks);

async function loadChecks() {
  const page = $('page-checks');
  page.innerHTML = loadingHtml();
  try {
    const [list, stats] = await Promise.all([
      api('GET', '/admin/checks'),
      api('GET', '/admin/checks/stats/summary'),
    ]);
    renderChecks(list, stats);
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderChecks(list, stats) {
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

    ${list.length ? checksTable(list) : emptyHtml('Нет проверок', 'Проверки появятся после первого запуска')}`;
}

function checksTable(list) {
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th>
          <th>Пользователь</th>
          <th>ГОСТ</th>
          <th>Статус</th>
          <th>Создано</th>
          <th>Завершено</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(c => `<tr>
            <td>${c.id}</td>
            <td>${c.user ? `@${escHtml(c.user.username || '')}` : '—'}</td>
            <td>${c.gost ? escHtml(c.gost.name) : '—'}</td>
            <td>${statusBadge(c.status)}</td>
            <td style="white-space:nowrap">${formatDate(c.created_at)}</td>
            <td style="white-space:nowrap">${formatDate(c.finished_at)}</td>
            <td class="actions-cell">
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
    renderChecks(list, stats);
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

window.filterChecks = filterChecks;
window.viewCheck = viewCheck;
