/* Content — Menu tab: visual keyboard grid, drag-and-drop, CRUD */

// Служебные payload, которые не показываются в визуальной сетке меню —
// они управляются отдельно во вкладке «Тексты».
const RESERVED_MENU_PAYLOADS = new Set(['__start__']);

let _menuItems = [];
let _dragItem = null;
let _extraButtonMeta = null;

async function loadContentMenu() {
  const all = await api('GET', '/admin/content/menu');
  _menuItems = all.filter(m => !RESERVED_MENU_PAYLOADS.has(m.payload));
  const actionBtn = `<button class="btn btn-primary" onclick="showAddMenuItem()">
    ${iconSvg('plus', 16)} Пункт меню
  </button>`;
  renderContentPage(renderMenuGrid(), actionBtn);
}

async function _ensureExtraButtonMeta() {
  if (_extraButtonMeta) return _extraButtonMeta;
  try {
    _extraButtonMeta = await api('GET', '/admin/content/menu/extra-buttons');
  } catch (err) {
    console.error('Failed to load extra-buttons meta', err);
    _extraButtonMeta = [];
  }
  return _extraButtonMeta;
}

/* ---------- Visual grid (Telegram-style keyboard) ---------- */

function groupByRows(items) {
  const rows = {};
  items.forEach(m => {
    const r = m.row ?? 0;
    if (!rows[r]) rows[r] = [];
    rows[r].push(m);
  });
  Object.values(rows).forEach(arr => arr.sort((a, b) => (a.col ?? 0) - (b.col ?? 0)));
  return Object.keys(rows)
    .map(Number)
    .sort((a, b) => a - b)
    .map(r => ({ row: r, items: rows[r] }));
}

function renderMenuGrid() {
  if (!_menuItems.length) {
    return emptyHtml('Нет пунктов меню', 'Добавьте первый пункт');
  }
  const rows = groupByRows(_menuItems);
  const maxRow = rows.length ? rows[rows.length - 1].row : 0;

  let html = '<div class="menu-grid">';
  rows.forEach(({ row, items }) => {
    html += `<div class="menu-row" data-row="${row}"
      ondragover="menuDragOver(event)" ondrop="menuDrop(event, ${row})">`;
    items.forEach(m => {
      const cls = m.active ? '' : ' menu-btn-inactive';
      const icon = m.icon ? escHtml(m.icon) + ' ' : '';
      html += `<div class="menu-btn${cls}" draggable="true"
        data-id="${m.id}" data-row="${m.row}" data-col="${m.col}"
        ondragstart="menuDragStart(event, ${m.id})"
        ondragend="menuDragEnd(event)"
        onclick="menuBtnClick(event, ${m.id})">
        <span class="menu-btn-label">${icon}${escHtml(m.title)}</span>
        <span class="menu-btn-grip">${iconSvg('menu', 14)}</span>
      </div>`;
    });
    html += `<div class="menu-dropzone menu-add-in-row"
      onclick="showAddMenuItem(${row}, ${items.length})" title="Добавить кнопку">
      ${iconSvg('plus', 18)}
    </div>`;
    html += '</div>';
  });
  html += `<div class="menu-row menu-new-row"
    ondragover="menuDragOver(event)" ondrop="menuDrop(event, ${maxRow + 1})">
    <div class="menu-dropzone menu-add-new-row"
      onclick="showAddMenuItem(${maxRow + 1}, 0)">
      ${iconSvg('plus', 16)} <span>Новый ряд</span>
    </div>
  </div>`;
  html += '</div>';
  return html;
}

/* ---------- Drag-and-drop ---------- */

function menuDragStart(e, id) {
  _dragItem = id;
  e.target.classList.add('dragging');
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', String(id));
}

function menuDragEnd(e) {
  _dragItem = null;
  e.target.classList.remove('dragging');
  document.querySelectorAll('.menu-row.drag-over').forEach(el => el.classList.remove('drag-over'));
}

function menuDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  const row = e.currentTarget;
  if (!row.classList.contains('drag-over')) {
    document.querySelectorAll('.menu-row.drag-over').forEach(el => el.classList.remove('drag-over'));
    row.classList.add('drag-over');
  }
}

async function menuDrop(e, targetRow) {
  e.preventDefault();
  document.querySelectorAll('.menu-row.drag-over').forEach(el => el.classList.remove('drag-over'));
  if (!_dragItem) return;

  const dragId = _dragItem;
  _dragItem = null;

  const item = _menuItems.find(m => m.id === dragId);
  if (!item) return;

  const dropX = e.clientX;
  const rowEl = e.currentTarget;
  const btns = Array.from(rowEl.querySelectorAll('.menu-btn'));
  let newCol = 0;
  for (const btn of btns) {
    const rect = btn.getBoundingClientRect();
    if (btn.dataset.id === String(dragId)) continue;
    if (dropX > rect.left + rect.width / 2) {
      newCol = parseInt(btn.dataset.col) + 1;
    }
  }

  item.row = targetRow;
  item.col = newCol;

  recalcPositions();
  await saveMenuLayout();
}

function recalcPositions() {
  const rows = groupByRows(_menuItems);
  rows.forEach(({ items }, ri) => {
    items.forEach((m, ci) => {
      m.row = ri;
      m.col = ci;
    });
  });
}

async function saveMenuLayout() {
  try {
    const items = _menuItems.map(m => ({ id: m.id, row: m.row, col: m.col }));
    await api('POST', '/admin/content/menu/reorder', { items });
    await loadContentMenu();
  } catch (err) {
    toast('Ошибка сохранения: ' + err.message, 'error');
    await loadContentMenu();
  }
}

/* ---------- Context menu on click ---------- */

function menuBtnClick(e, id) {
  e.stopPropagation();
  if (e.target.closest('.menu-btn-grip')) return;

  closeContextMenu();
  const item = _menuItems.find(m => m.id === id);
  if (!item) return;

  const rect = e.currentTarget.getBoundingClientRect();
  const menu = document.createElement('div');
  menu.className = 'context-menu';
  menu.id = 'menu-ctx';
  menu.style.top = (rect.bottom + 4) + 'px';
  menu.style.left = rect.left + 'px';

  const toggleLabel = item.active ? 'Скрыть' : 'Показать';
  menu.innerHTML = `
    <button class="ctx-item" onclick="ctxEditItem(${id})">
      ${iconSvg('edit', 14)} Редактировать
    </button>
    <button class="ctx-item" onclick="ctxToggleItem(${id}, ${!item.active})">
      ${iconSvg('eye', 14)} ${toggleLabel}
    </button>
    <button class="ctx-item ctx-danger" onclick="ctxDeleteItem(${id})">
      ${iconSvg('trash', 14)} Удалить
    </button>`;
  document.body.appendChild(menu);

  setTimeout(() => document.addEventListener('click', closeContextMenu, { once: true }), 10);
}

function closeContextMenu() {
  document.getElementById('menu-ctx')?.remove();
}

async function ctxEditItem(id) {
  closeContextMenu();
  const item = _menuItems.find(m => m.id === id);
  if (item) showEditMenuItem(item);
}

async function ctxToggleItem(id, active) {
  closeContextMenu();
  try {
    const item = _menuItems.find(m => m.id === id);
    if (!item) return;
    const data = {
      title: item.title, icon: item.icon, item_type: item.item_type,
      payload: item.payload, row: item.row, col: item.col, active,
      extra_buttons: Array.isArray(item.extra_buttons) ? item.extra_buttons : [],
    };
    await api('PUT', `/admin/content/menu/${id}`, data);
    toast(active ? 'Пункт показан' : 'Пункт скрыт', 'success');
    loadContent();
  } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
}

async function ctxDeleteItem(id) {
  closeContextMenu();
  if (!confirm('Удалить пункт меню #' + id + '?')) return;
  try {
    await api('DELETE', `/admin/content/menu/${id}`);
    toast('Пункт удалён', 'success');
    loadContent();
  } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
}

/* ---------- Menu item form (create / edit) ---------- */

function menuItemForm(m) {
  const isText = (!m && true) || m?.item_type === 'text';
  const isLink = m?.item_type === 'link';
  const enabled = new Set(Array.isArray(m?.extra_buttons) ? m.extra_buttons : []);
  const meta = Array.isArray(_extraButtonMeta) ? _extraButtonMeta : [];
  const extraRows = meta.length
    ? meta.map(b => `
        <div class="toggle" style="border:none">
          <div class="toggle-info">
            <div class="toggle-title">${escHtml(b.label)}${b.available ? '' : ' <span class="badge badge-gray" style="font-size:10px;vertical-align:middle;margin-left:4px">пока не настроено</span>'}</div>
            <div class="toggle-sub">${escHtml(b.hint || '')}</div>
          </div>
          <label class="switch">
            <input type="checkbox" data-extra-btn="${escHtml(b.code)}"
              ${enabled.has(b.code) ? 'checked' : ''}
              ${b.available ? '' : 'disabled'}>
            <span class="slider"></span>
          </label>
        </div>
      `).join('')
    : '<div class="form-hint">Список кнопок не загрузился. Обновите страницу.</div>';

  return `
    <div class="form-group">
      <label class="form-label">Заголовок</label>
      <input class="form-input" id="mi-title" value="${m ? escHtml(m.title) : ''}">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="form-label">Тип</label>
        <select class="form-select" id="mi-type" onchange="onMenuTypeChange()">
          <option value="text" ${m?.item_type === 'text' || !m ? 'selected' : ''}>Текст</option>
          <option value="link" ${m?.item_type === 'link' ? 'selected' : ''}>Ссылка</option>
          <option value="callback" ${m?.item_type === 'callback' ? 'selected' : ''}>Callback</option>
        </select>
      </div>
      <div class="form-group">
        <label class="form-label">Иконка</label>
        <input class="form-input" id="mi-icon" value="${m ? escHtml(m.icon || '') : ''}"
          placeholder="emoji, напр. 📋">
      </div>
    </div>
    <div id="mi-payload-wrap">
      ${payloadFieldHtml(m?.item_type || 'text', m?.payload)}
    </div>
    <div class="toggle" style="border:none;padding-top:4px">
      <div class="toggle-info"><div class="toggle-title">Активен</div></div>
      <label class="switch">
        <input type="checkbox" id="mi-active" ${!m || m.active ? 'checked' : ''}>
        <span class="slider"></span>
      </label>
    </div>
    <h4 class="form-section-title">Дополнительные кнопки под сообщением</h4>
    <div class="form-hint" style="margin:-4px 0 8px">
      Когда пользователь откроет этот пункт меню, выбранные кнопки покажутся прямо под сообщением.
    </div>
    <div id="mi-extra-buttons" class="extra-buttons-list">${extraRows}</div>
    <input type="hidden" id="mi-row" value="${m?.row ?? ''}">
    <input type="hidden" id="mi-col" value="${m?.col ?? ''}">`;
}

function payloadFieldHtml(type, payload) {
  if (type === 'text') {
    return `<div class="form-hint" style="margin-top:0">
      Сообщения этой кнопки настраиваются во вкладке <strong>Тексты</strong> после создания.
    </div>`;
  }
  if (type === 'link') {
    return `<div class="form-group">
      <label class="form-label">URL</label>
      <input class="form-input" id="mi-payload" type="url"
        placeholder="https://example.com" value="${escHtml(payload || '')}">
      <div class="form-hint">Ссылка, которая откроется при нажатии на кнопку</div>
    </div>`;
  }
  return `<div class="form-group">
    <label class="form-label">Callback Data</label>
    <input class="form-input" id="mi-payload" value="${escHtml(payload || '')}"
      placeholder="my_action">
    <div class="form-hint">Идентификатор действия для обработчика бота</div>
  </div>`;
}

function onMenuTypeChange() {
  const type = getVal('mi-type');
  const oldPayload = document.getElementById('mi-payload')?.value || '';
  document.getElementById('mi-payload-wrap').innerHTML = payloadFieldHtml(type, type === 'text' ? '' : oldPayload);
}

function getMenuItemData() {
  const type = getVal('mi-type');
  const extra = Array.from(
    document.querySelectorAll('#mi-extra-buttons input[data-extra-btn]:checked'),
  ).map(el => el.dataset.extraBtn);
  return {
    title: getVal('mi-title').trim(),
    icon: getVal('mi-icon').trim() || null,
    item_type: type,
    payload: type === 'text' ? null : (getVal('mi-payload')?.trim() || null),
    row: getVal('mi-row') !== '' ? parseInt(getVal('mi-row')) : 0,
    col: getVal('mi-col') !== '' ? parseInt(getVal('mi-col')) : 0,
    active: isChecked('mi-active'),
    extra_buttons: extra,
  };
}

async function showAddMenuItem(row, col) {
  await _ensureExtraButtonMeta();
  const item = row != null ? { row, col, item_type: 'text', active: true } : null;
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="createMenuItem()">Создать</button>`;
  openModal('Новый пункт меню', menuItemForm(item), footer);
}

async function showEditMenuItem(m) {
  await _ensureExtraButtonMeta();
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="updateMenuItem(${m.id})">Сохранить</button>`;
  openModal('Редактировать пункт', menuItemForm(m), footer);
}

async function createMenuItem() {
  const data = getMenuItemData();
  if (!data.title) { toast('Введите заголовок', 'error'); return; }
  if (data.item_type === 'link' && !data.payload) { toast('Введите URL', 'error'); return; }
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
  if (data.item_type === 'link' && !data.payload) { toast('Введите URL', 'error'); return; }
  try {
    await api('PUT', `/admin/content/menu/${id}`, data);
    closeModal();
    toast('Пункт обновлён', 'success');
    loadContent();
  } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
}

/* ---------- Expose ---------- */
window.loadContentMenu = loadContentMenu;
window.showAddMenuItem = showAddMenuItem;
window.showEditMenuItem = showEditMenuItem;
window.createMenuItem = createMenuItem;
window.updateMenuItem = updateMenuItem;
window.onMenuTypeChange = onMenuTypeChange;
window.menuDragStart = menuDragStart;
window.menuDragEnd = menuDragEnd;
window.menuDragOver = menuDragOver;
window.menuDrop = menuDrop;
window.menuBtnClick = menuBtnClick;
window.closeContextMenu = closeContextMenu;
window.ctxEditItem = ctxEditItem;
window.ctxToggleItem = ctxToggleItem;
window.ctxDeleteItem = ctxDeleteItem;
