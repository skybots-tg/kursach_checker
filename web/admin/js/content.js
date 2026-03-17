/* Content — bot texts + menu items management */

registerPage('content', loadContent);

let _contentTab = 'texts';

async function loadContent() {
  const page = $('page-content');
  page.innerHTML = loadingHtml();
  try {
    if (_contentTab === 'texts') await loadContentTexts();
    else await loadContentMenu();
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

async function loadContentTexts() {
  const list = await api('GET', '/admin/content/texts');
  renderContentPage(list, null);
}

async function loadContentMenu() {
  const list = await api('GET', '/admin/content/menu');
  renderContentPage(null, list);
}

function renderContentPage(texts, menu) {
  const isTexts = _contentTab === 'texts';
  $('page-content').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Контент бота</h1>
        <p class="page-subtitle">Тексты, меню и сообщения бота</p>
      </div>
      ${!isTexts ? `<button class="btn btn-primary" onclick="showAddMenuItem()">
        ${iconSvg('plus', 16)} Пункт меню
      </button>` : ''}
    </div>
    <div class="tabs">
      <button class="tab-btn ${isTexts ? 'active' : ''}" onclick="switchContentTab('texts')">Тексты</button>
      <button class="tab-btn ${!isTexts ? 'active' : ''}" onclick="switchContentTab('menu')">Меню</button>
    </div>
    ${isTexts ? renderTexts(texts || []) : renderMenu(menu || [])}`;
}

function renderTexts(list) {
  if (!list.length) return emptyHtml('Нет текстов', 'Добавьте первый текстовый контент');
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>Ключ</th>
          <th>Значение</th>
          <th>Обновлено</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(t => `<tr>
            <td><code>${escHtml(t.key)}</code></td>
            <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escHtml(t.value || '')}</td>
            <td style="white-space:nowrap">${formatDate(t.updated_at)}</td>
            <td class="actions-cell">
              <button class="btn btn-icon btn-sm" title="Редактировать" onclick="editText('${escHtml(t.key)}', \`${escHtml(t.value || '')}\`)">
                ${iconSvg('edit', 15)}
              </button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function renderMenu(list) {
  if (!list.length) return emptyHtml('Нет пунктов меню', 'Добавьте первый пункт');
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th>
          <th>Заголовок</th>
          <th>Тип</th>
          <th>Позиция</th>
          <th>Статус</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(m => `<tr>
            <td>${m.id}</td>
            <td><strong>${escHtml(m.title)}</strong></td>
            <td>${escHtml(m.item_type || '—')}</td>
            <td>${m.position ?? '—'}</td>
            <td>${m.active ? '<span class="badge badge-success">Активен</span>' : '<span class="badge badge-gray">Скрыт</span>'}</td>
            <td class="actions-cell">
              <button class="btn btn-icon btn-sm" title="Редактировать" onclick='showEditMenuItem(${JSON.stringify(m)})'>
                ${iconSvg('edit', 15)}
              </button>
              <button class="btn btn-icon btn-sm" title="Удалить" onclick="deleteMenuItem(${m.id})">
                ${iconSvg('trash', 15)}
              </button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function switchContentTab(tab) {
  _contentTab = tab;
  loadContent();
}

function editText(key, value) {
  const body = `
    <div class="form-group">
      <label class="form-label">Ключ</label>
      <input class="form-input" value="${escHtml(key)}" disabled>
    </div>
    <div class="form-group">
      <label class="form-label">Значение</label>
      <textarea class="form-textarea" id="text-value" rows="6">${escHtml(value)}</textarea>
    </div>`;
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="saveText('${escHtml(key)}')">Сохранить</button>`;
  openModal('Редактировать текст', body, footer);
}

async function saveText(key) {
  try {
    await api('PUT', `/admin/content/texts/${key}`, { value: getVal('text-value') });
    closeModal();
    toast('Текст сохранён', 'success');
    loadContent();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

function menuItemForm(m) {
  return `
    <div class="form-group">
      <label class="form-label">Заголовок</label>
      <input class="form-input" id="mi-title" value="${m ? escHtml(m.title) : ''}">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="form-label">Тип</label>
        <select class="form-select" id="mi-type">
          <option value="text" ${m?.item_type === 'text' ? 'selected' : ''}>Текст</option>
          <option value="link" ${m?.item_type === 'link' ? 'selected' : ''}>Ссылка</option>
          <option value="callback" ${m?.item_type === 'callback' ? 'selected' : ''}>Callback</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Позиция</label>
        <input class="form-input" type="number" id="mi-position" value="${m?.position ?? 0}" min="0">
      </div>
    </div>
    <div class="form-group">
      <label class="form-label">Иконка</label>
      <input class="form-input" id="mi-icon" value="${m ? escHtml(m.icon || '') : ''}" placeholder="emoji или код иконки">
    </div>
    <div class="form-group">
      <label class="form-label">Payload</label>
      <textarea class="form-textarea" id="mi-payload" rows="3">${m ? escHtml(m.payload || '') : ''}</textarea>
    </div>
    <div class="toggle" style="border:none;padding-top:4px">
      <div class="toggle-info"><div class="toggle-title">Активен</div></div>
      <label class="switch">
        <input type="checkbox" id="mi-active" ${!m || m.active ? 'checked' : ''}>
        <span class="slider"></span>
      </label>
    </div>`;
}

function showAddMenuItem() {
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="createMenuItem()">Создать</button>`;
  openModal('Новый пункт меню', menuItemForm(null), footer);
}

function showEditMenuItem(m) {
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="updateMenuItem(${m.id})">Сохранить</button>`;
  openModal('Редактировать пункт', menuItemForm(m), footer);
}

function getMenuItemData() {
  return {
    title: getVal('mi-title').trim(),
    icon: getVal('mi-icon').trim() || null,
    item_type: getVal('mi-type'),
    payload: getVal('mi-payload').trim() || null,
    position: parseInt(getVal('mi-position')) || 0,
    active: isChecked('mi-active'),
  };
}

async function createMenuItem() {
  const data = getMenuItemData();
  if (!data.title) { toast('Введите заголовок', 'error'); return; }
  try {
    await api('POST', '/admin/content/menu', data);
    closeModal();
    toast('Пункт создан', 'success');
    loadContent();
  } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
}

async function updateMenuItem(id) {
  const data = getMenuItemData();
  if (!data.title) { toast('Введите заголовок', 'error'); return; }
  try {
    await api('PUT', `/admin/content/menu/${id}`, data);
    closeModal();
    toast('Пункт обновлён', 'success');
    loadContent();
  } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
}

async function deleteMenuItem(id) {
  if (!confirm('Удалить пункт меню #' + id + '?')) return;
  try {
    await api('DELETE', `/admin/content/menu/${id}`);
    toast('Пункт удалён', 'success');
    loadContent();
  } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
}

window.switchContentTab = switchContentTab;
window.editText = editText;
window.saveText = saveText;
window.showAddMenuItem = showAddMenuItem;
window.showEditMenuItem = showEditMenuItem;
window.createMenuItem = createMenuItem;
window.updateMenuItem = updateMenuItem;
window.deleteMenuItem = deleteMenuItem;
