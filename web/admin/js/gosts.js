/* GOSTs — list + create + edit + delete (linked to university) */

registerPage('gosts', loadGosts);

let _gostUniversities = [];

async function loadGosts() {
  const page = $('page-gosts');
  page.innerHTML = loadingHtml();
  try {
    const [list, unis] = await Promise.all([
      api('GET', '/gosts'),
      api('GET', '/universities'),
    ]);
    _gostUniversities = unis;
    renderGosts(list);
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderGosts(list) {
  $('page-gosts').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">ГОСТы / стили</h1>
        <p class="page-subtitle">Стандарты оформления документов</p>
      </div>
      <button class="btn btn-primary" onclick="showAddGost()">
        ${iconSvg('plus', 16)} Добавить ГОСТ
      </button>
    </div>
    ${list.length ? gostTable(list) : emptyHtml('Нет ГОСТов', 'Добавьте первый стандарт')}`;
}

function gostTable(list) {
  const uniMap = {};
  _gostUniversities.forEach(u => uniMap[u.id] = u.name);

  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th>
          <th>Название</th>
          <th>ВУЗ</th>
          <th>Описание</th>
          <th>Статус</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(g => `<tr>
            <td>${g.id}</td>
            <td><strong>${escHtml(g.name)}</strong></td>
            <td>${escHtml(uniMap[g.university_id] || '— Общий —')}</td>
            <td style="color:var(--text-muted);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(g.description || '—')}</td>
            <td>${g.active ? '<span class="badge badge-success">Активен</span>' : '<span class="badge badge-gray">Неактивен</span>'}</td>
            <td class="actions-cell">
              <button class="btn btn-icon btn-sm" title="Редактировать" onclick="showEditGost(${g.id})">
                ${iconSvg('edit', 15)}
              </button>
              <button class="btn btn-icon btn-sm" title="Удалить" onclick="deleteGost(${g.id})">
                ${iconSvg('trash', 15)}
              </button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function gostFormHtml(g) {
  const uniOpts = `<option value="">— Общий (без ВУЗа) —</option>`
    + _gostUniversities.map(u =>
      `<option value="${u.id}" ${g && g.university_id === u.id ? 'selected' : ''}>${escHtml(u.name)}</option>`
    ).join('');

  return `
    <div class="form-group">
      <label class="form-label">Название ГОСТа</label>
      <input class="form-input" id="gost-name" value="${g ? escHtml(g.name) : ''}" placeholder="Например: ГОСТ Р 7.0.11-2011">
    </div>
    <div class="form-group">
      <label class="form-label">ВУЗ</label>
      <select class="form-select" id="gost-uni">${uniOpts}</select>
      <div class="form-hint">Привяжите ГОСТ к конкретному ВУЗу или оставьте «Общий»</div>
    </div>
    <div class="form-group">
      <label class="form-label">Описание</label>
      <textarea class="form-textarea" id="gost-desc" rows="3" placeholder="Краткое описание стандарта">${g ? escHtml(g.description || '') : ''}</textarea>
    </div>
    ${g ? `<div class="toggle" style="border:none;padding-top:4px">
      <div class="toggle-info"><div class="toggle-title">Активен</div></div>
      <label class="switch">
        <input type="checkbox" id="gost-active" ${g.active ? 'checked' : ''}>
        <span class="slider"></span>
      </label>
    </div>` : ''}`;
}

function showAddGost() {
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="createGost()">Создать</button>`;
  openModal('Новый ГОСТ', gostFormHtml(null), footer);
}

let _gostEditCache = [];

async function showEditGost(id) {
  if (!_gostEditCache.length) {
    _gostEditCache = await api('GET', '/gosts');
  }
  const g = _gostEditCache.find(x => x.id === id);
  if (!g) { toast('ГОСТ не найден', 'error'); return; }
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="updateGost(${id})">Сохранить</button>`;
  openModal('Редактировать ГОСТ', gostFormHtml(g), footer);
}

function _getGostFormData() {
  const uniVal = getVal('gost-uni');
  return {
    name: getVal('gost-name').trim(),
    description: getVal('gost-desc').trim() || null,
    university_id: uniVal ? parseInt(uniVal) : null,
    active: document.getElementById('gost-active') ? isChecked('gost-active') : true,
  };
}

async function createGost() {
  const data = _getGostFormData();
  if (!data.name) { toast('Введите название', 'error'); return; }
  try {
    await api('POST', '/gosts', data);
    closeModal();
    toast('ГОСТ создан', 'success');
    _gostEditCache = [];
    loadGosts();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

async function updateGost(id) {
  const data = _getGostFormData();
  if (!data.name) { toast('Введите название', 'error'); return; }
  try {
    await api('PUT', `/gosts/${id}`, data);
    closeModal();
    toast('ГОСТ обновлён', 'success');
    _gostEditCache = [];
    loadGosts();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

async function deleteGost(id) {
  if (!confirm('Удалить ГОСТ #' + id + '?')) return;
  try {
    await api('DELETE', `/gosts/${id}`);
    toast('ГОСТ удалён', 'success');
    _gostEditCache = [];
    loadGosts();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

window.showAddGost = showAddGost;
window.showEditGost = showEditGost;
window.createGost = createGost;
window.updateGost = updateGost;
window.deleteGost = deleteGost;
