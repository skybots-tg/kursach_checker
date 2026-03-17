/* Demo samples — CRUD, pagination */

registerPage('demo', loadDemo);

let _demoData = [];
let _demoPage = 1;

async function loadDemo() {
  const page = $('page-demo');
  page.innerHTML = loadingHtml();
  try {
    _demoData = await api('GET', '/admin/demo');
    _demoPage = 1;
    renderDemo();
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderDemo() {
  $('page-demo').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Демо-примеры</h1>
        <p class="page-subtitle">Управление демонстрационными образцами проверки (${_demoData.length})</p>
      </div>
      <button class="btn btn-primary" onclick="showDemoModal()">
        ${iconSvg('plus', 16)} Новый демо
      </button>
    </div>
    <div id="demo-table-area"></div>`;
  renderDemoTable();
}

function renderDemoTable() {
  const paged = paginate(_demoData, _demoPage);
  _demoPage = paged.page;
  const area = $('demo-table-area');
  if (!area) return;
  area.innerHTML = paged.items.length
    ? demoTable(paged.items) + paginationHtml(paged, 'demoGoPage')
    : emptyHtml('Нет демо-примеров', 'Создайте первый демонстрационный пример');
}

function demoGoPage(p) { _demoPage = p; renderDemoTable(); }

function demoTable(list) {
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th><th>Название</th><th>Файл ID</th>
          <th>Статус</th><th>Создано</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(d => `<tr>
            <td data-label="ID">${d.id}</td>
            <td data-label="Название"><strong>${escHtml(d.name)}</strong></td>
            <td data-label="Файл ID"><code>${d.document_file_id ?? '—'}</code></td>
            <td data-label="Статус">${d.active ? '<span class="badge badge-success">Активен</span>' : '<span class="badge badge-gray">Скрыт</span>'}</td>
            <td data-label="Создано" style="white-space:nowrap">${formatDate(d.created_at)}</td>
            <td data-label="" class="actions-cell">
              <button class="btn btn-icon btn-sm" title="Подробнее" onclick="viewDemoDetail(${d.id})">
                ${iconSvg('eye', 15)}
              </button>
              <button class="btn btn-icon btn-sm" title="Удалить" onclick="deleteDemo(${d.id})">
                ${iconSvg('trash', 15)}
              </button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function showDemoModal(d) {
  const isEdit = !!d;
  const body = `
    <div class="form-group">
      <label class="form-label">Название</label>
      <input class="form-input" id="demo-name" value="${isEdit ? escHtml(d.name) : ''}">
    </div>
    <div class="form-group">
      <label class="form-label">ID файла документа</label>
      <input class="form-input" type="number" id="demo-file-id" value="${isEdit ? (d.document_file_id ?? '') : ''}">
      <div class="form-hint">ID загруженного файла в системе</div>
    </div>
    <div class="form-group">
      <label class="form-label">Report JSON</label>
      <textarea class="form-textarea" id="demo-report" rows="5" placeholder='{}'>${isEdit && d.report_json ? JSON.stringify(d.report_json, null, 2) : ''}</textarea>
    </div>
    <div class="toggle" style="border:none;padding-top:4px">
      <div class="toggle-info"><div class="toggle-title">Активен</div></div>
      <label class="switch">
        <input type="checkbox" id="demo-active" ${!isEdit || d.active ? 'checked' : ''}>
        <span class="slider"></span>
      </label>
    </div>`;
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="saveDemo(${isEdit ? d.id : 'null'})">${isEdit ? 'Сохранить' : 'Создать'}</button>`;
  openModal(isEdit ? 'Редактировать демо' : 'Новый демо-пример', body, footer);
}

async function viewDemoDetail(id) {
  try {
    const d = await api('GET', `/admin/demo/${id}`);
    showDemoModal(d);
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

async function saveDemo(id) {
  const name = getVal('demo-name').trim();
  if (!name) { toast('Введите название', 'error'); return; }

  let reportJson = {};
  try {
    const raw = getVal('demo-report').trim();
    if (raw) reportJson = JSON.parse(raw);
  } catch { toast('Некорректный JSON', 'error'); return; }

  const data = {
    name,
    document_file_id: parseInt(getVal('demo-file-id')) || null,
    report_json: reportJson,
    active: isChecked('demo-active'),
  };

  try {
    if (id) await api('PUT', `/admin/demo/${id}`, data);
    else await api('POST', '/admin/demo', data);
    closeModal();
    toast(id ? 'Демо обновлено' : 'Демо создано', 'success');
    loadDemo();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

async function deleteDemo(id) {
  if (!confirm('Удалить демо #' + id + '?')) return;
  try {
    await api('DELETE', `/admin/demo/${id}`);
    toast('Демо удалено', 'success');
    loadDemo();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

window.demoGoPage = demoGoPage;
window.showDemoModal = showDemoModal;
window.viewDemoDetail = viewDemoDetail;
window.saveDemo = saveDemo;
window.deleteDemo = deleteDemo;
