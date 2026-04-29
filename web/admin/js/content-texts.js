/* Content — Texts tab: key-value texts + menu-item message editor */

// Служебный пункт меню (payload) для сообщений, отправляемых перед
// приветствием на /start. Показываем его в этой вкладке отдельной карточкой.
const START_PAYLOAD = '__start__';

// Ключ системного текста приветствия — редактируется на вкладке
// «Системные тексты», но мы прокидываем туда быструю кнопку из карточки /start.
const WELCOME_TEXT_KEY = 'bot.welcome';

let _textsMenuItems = [];
let _textsStartItem = null;

async function loadContentTexts() {
  const [texts, menuItems] = await Promise.all([
    api('GET', '/admin/content/texts'),
    api('GET', '/admin/content/menu'),
  ]);
  _textsStartItem = menuItems.find(m => m.payload === START_PAYLOAD) || null;
  _textsMenuItems = menuItems.filter(
    m => m.item_type === 'text' && m.payload !== START_PAYLOAD,
  );
  renderContentPage(renderTextsTab(texts), '');
}

function renderTextsTab(texts) {
  let html = renderTextsTable(texts);
  html += renderStartMessages();
  html += renderMenuMessages();
  return html;
}

/* ---------- Key-value texts table ---------- */

function renderTextsTable(list) {
  if (!list.length) return '';
  return `
  <h3 class="section-heading">Системные тексты</h3>
  <div class="card" style="padding:0;overflow:hidden">
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
  } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
}

/* ---------- /start messages section ---------- */

function renderStartMessages() {
  if (!_textsStartItem) {
    return `<div class="section-heading-wrap">
      <h3 class="section-heading">Стартовое сообщение (/start)</h3>
    </div>
    <div class="card"><p class="form-hint" style="text-align:center;margin:0">
      Служебный пункт не найден. Раскатите миграцию
      <code>0013_start_media_item</code>.
    </p></div>`;
  }
  const m = _textsStartItem;
  return `<div class="section-heading-wrap">
    <h3 class="section-heading">Стартовое сообщение (/start)</h3>
  </div>
  <div class="msg-card card" id="msg-card-${m.id}">
    <div class="msg-card-header" onclick="toggleMsgCard(${m.id})">
      <div class="msg-card-title">🏠 <strong>Сообщения перед приветствием</strong></div>
      <span class="msg-card-count" id="msg-count-${m.id}">...</span>
      <span class="msg-card-arrow">${iconSvg('chevronDown', 16)}</span>
    </div>
    <div class="msg-card-body" id="msg-body-${m.id}" style="display:none">
      <p class="form-hint" style="margin-top:0">
        Эти сообщения отправятся <strong>до</strong> приветствия при команде /start.
        Подойдут видео-кружок, фото, GIF или дополнительный текст —
        нажмите «Добавить сообщение» и выберите нужный тип.
      </p>
      <div id="msg-list-${m.id}" class="msg-list">${loadingHtml()}</div>
      <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:10px">
        <button class="btn btn-secondary btn-sm" onclick="showAddMessage(${m.id})">
          ${iconSvg('plus', 14)} Добавить сообщение
        </button>
        <button class="btn btn-ghost btn-sm" onclick="editStartWelcomeText()"
          title="Открыть редактор приветствия (bot.welcome) на вкладке «Системные тексты»">
          ${iconSvg('edit', 14)} Изменить текст приветствия
        </button>
      </div>
    </div>
  </div>`;
}

/* ---------- Menu-item messages section ---------- */

function renderMenuMessages() {
  if (!_textsMenuItems.length) {
    return `<div class="section-heading-wrap">
      <h3 class="section-heading">Сообщения меню</h3>
    </div>
    <div class="card"><p class="form-hint" style="text-align:center;margin:0">
      Создайте пункт меню с типом «Текст» во вкладке Меню, чтобы настроить сообщения.
    </p></div>`;
  }
  let html = `<div class="section-heading-wrap">
    <h3 class="section-heading">Сообщения меню</h3>
  </div>`;
  _textsMenuItems.forEach(m => {
    const icon = m.icon ? escHtml(m.icon) + ' ' : '';
    html += `<div class="msg-card card" id="msg-card-${m.id}">
      <div class="msg-card-header" onclick="toggleMsgCard(${m.id})">
        <div class="msg-card-title">${icon}<strong>${escHtml(m.title)}</strong></div>
        <span class="msg-card-count" id="msg-count-${m.id}">...</span>
        <span class="msg-card-arrow">${iconSvg('chevronDown', 16)}</span>
      </div>
      <div class="msg-card-body" id="msg-body-${m.id}" style="display:none">
        <div id="msg-list-${m.id}" class="msg-list">${loadingHtml()}</div>
        <button class="btn btn-secondary btn-sm" style="margin-top:10px"
          onclick="showAddMessage(${m.id})">
          ${iconSvg('plus', 14)} Добавить сообщение
        </button>
      </div>
    </div>`;
  });
  return html;
}

async function toggleMsgCard(itemId) {
  const body = document.getElementById('msg-body-' + itemId);
  const isOpen = body.style.display !== 'none';
  body.style.display = isOpen ? 'none' : 'block';
  if (!isOpen) await loadMessages(itemId);
}

async function loadMessages(itemId) {
  const list = document.getElementById('msg-list-' + itemId);
  const count = document.getElementById('msg-count-' + itemId);
  try {
    const msgs = await api('GET', `/admin/content/menu/${itemId}/messages`);
    count.textContent = msgs.length + ' шт.';
    if (!msgs.length) {
      list.innerHTML = '<p class="form-hint" style="text-align:center">Нет сообщений</p>';
      return;
    }
    list.innerHTML = msgs.map((msg, i) => renderMessageItem(msg, itemId, i, msgs.length)).join('');
  } catch (err) {
    list.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function sanitizeTgHtml(raw) {
  if (!raw) return '';
  const allowed = ['b', 'i', 'u', 's', 'a', 'code', 'pre', 'em', 'strong'];
  const div = document.createElement('div');
  div.innerHTML = raw;
  function walk(node) {
    for (const child of Array.from(node.childNodes)) {
      if (child.nodeType === 1) {
        const tag = child.tagName.toLowerCase();
        if (!allowed.includes(tag)) {
          const text = document.createTextNode(child.textContent);
          node.replaceChild(text, child);
        } else {
          walk(child);
        }
      }
    }
  }
  walk(div);
  return div.innerHTML;
}

function renderMessageItem(msg, itemId, idx, total) {
  const typeLabels = {
    text: 'Текст', photo: 'Фото', video: 'Видео', video_note: 'Кружок',
    audio: 'Аудио', document: 'Файл', animation: 'GIF',
  };
  const preview = msg.message_type === 'text'
    ? sanitizeTgHtml((msg.text || '').substring(0, 120))
    : (msg.file_name ? escHtml(msg.file_name) : typeLabels[msg.message_type] || msg.message_type);
  const moveUp = idx > 0
    ? `<button class="btn btn-icon btn-sm" title="Вверх" onclick="moveMessage(${itemId},${msg.id},-1)">&#9650;</button>` : '';
  const moveDown = idx < total - 1
    ? `<button class="btn btn-icon btn-sm" title="Вниз" onclick="moveMessage(${itemId},${msg.id},1)">&#9660;</button>` : '';

  return `<div class="msg-item" data-id="${msg.id}">
    <div class="msg-item-info">
      <span class="badge badge-info">${typeLabels[msg.message_type] || msg.message_type}</span>
      <span class="msg-preview">${preview}</span>
    </div>
    <div class="msg-item-actions">
      ${moveUp}${moveDown}
      <button class="btn btn-icon btn-sm" title="Редактировать" onclick="showEditMessage(${itemId},${msg.id})">
        ${iconSvg('edit', 14)}
      </button>
      <button class="btn btn-icon btn-sm" title="Удалить" onclick="deleteMessage(${itemId},${msg.id})">
        ${iconSvg('trash', 14)}
      </button>
    </div>
  </div>`;
}

/* ---------- Message form (create / edit) ---------- */

// Telegram не принимает подпись для video_note («кружок»).
const NO_CAPTION_TYPES = new Set(['video_note']);

const MSG_TYPE_ACCEPT = {
  photo: 'image/*',
  video: 'video/*',
  video_note: 'video/*',
  audio: 'audio/*',
  animation: 'image/gif,video/*',
  document: '*/*',
};

function messageFormHtml(msg) {
  const t = msg?.message_type || 'text';
  const isMedia = t !== 'text';
  const noCaption = NO_CAPTION_TYPES.has(t);
  const accept = MSG_TYPE_ACCEPT[t] || '*/*';
  return `
    <div class="form-group">
      <label class="form-label">Тип сообщения</label>
      <select class="form-select" id="msg-type" onchange="onMsgTypeChange()">
        <option value="text" ${t === 'text' ? 'selected' : ''}>Текст</option>
        <option value="photo" ${t === 'photo' ? 'selected' : ''}>🖼️ Фото</option>
        <option value="video" ${t === 'video' ? 'selected' : ''}>🎬 Видео</option>
        <option value="video_note" ${t === 'video_note' ? 'selected' : ''}>⚫ Кружок</option>
        <option value="audio" ${t === 'audio' ? 'selected' : ''}>🎵 Аудио</option>
        <option value="document" ${t === 'document' ? 'selected' : ''}>📎 Файл</option>
        <option value="animation" ${t === 'animation' ? 'selected' : ''}>🎞️ GIF</option>
      </select>
    </div>
    <div id="msg-media-wrap" style="display:${isMedia ? 'block' : 'none'}">
      <div class="form-group">
        <label class="form-label">Файл</label>
        <input type="file" class="form-input" id="msg-file" accept="${accept}">
        ${msg?.file_name ? `<div class="form-hint">Текущий: ${escHtml(msg.file_name)}</div>` : ''}
        <div class="form-hint" id="msg-file-hint" style="display:${noCaption ? 'block' : 'none'}">
          Кружок должен быть квадратным видео до 60 сек. Подпись не поддерживается.
        </div>
      </div>
    </div>
    <div id="msg-text-wrap" style="display:${noCaption ? 'none' : 'block'}">
      <div class="form-group">
        <label class="form-label">${isMedia ? 'Подпись' : 'Текст сообщения'}</label>
        <div class="rt-toolbar">
          <button type="button" class="rt-btn" onclick="rtWrap('msg-text','<b>','</b>')" title="Жирный"><b>B</b></button>
          <button type="button" class="rt-btn" onclick="rtWrap('msg-text','<i>','</i>')" title="Курсив"><i>I</i></button>
          <button type="button" class="rt-btn" onclick="rtWrap('msg-text','<u>','</u>')" title="Подчёркнутый"><u>U</u></button>
          <button type="button" class="rt-btn" onclick="rtInsertLink('msg-text')" title="Ссылка">🔗</button>
        </div>
        <textarea class="form-textarea" id="msg-text" rows="5" oninput="updateMsgPreview()">${escHtml(msg?.text || '')}</textarea>
        <div class="form-hint">Поддерживается HTML: &lt;b&gt;, &lt;i&gt;, &lt;u&gt;, &lt;a href="..."&gt;</div>
        <div class="form-hint">
          Доступные переменные:
          <code>{ref_link}</code> — персональная реф-ссылка пользователя,
          <code>{credits}</code> или <code>{N}</code> — количество оставшихся попыток.
        </div>
      </div>
      <div class="form-group">
        <label class="form-label">Предпросмотр</label>
        <div id="msg-preview-box" class="msg-preview-box" style="border:1px solid var(--border);border-radius:8px;padding:10px 14px;min-height:40px;background:var(--bg-subtle);line-height:1.5">${sanitizeTgHtml(msg?.text || '')}</div>
      </div>
    </div>`;
}

function onMsgTypeChange() {
  const type = getVal('msg-type');
  const isMedia = type !== 'text';
  const noCaption = NO_CAPTION_TYPES.has(type);
  document.getElementById('msg-media-wrap').style.display = isMedia ? 'block' : 'none';
  document.getElementById('msg-text-wrap').style.display = noCaption ? 'none' : 'block';
  const fileInput = document.getElementById('msg-file');
  if (fileInput) fileInput.accept = MSG_TYPE_ACCEPT[type] || '*/*';
  const hint = document.getElementById('msg-file-hint');
  if (hint) hint.style.display = noCaption ? 'block' : 'none';
  const label = document.querySelector('#msg-text-wrap .form-label');
  if (label) label.textContent = isMedia ? 'Подпись' : 'Текст сообщения';
}

/* Rich-text helpers */

function rtWrap(textareaId, openTag, closeTag) {
  const ta = document.getElementById(textareaId);
  if (!ta) return;
  const start = ta.selectionStart;
  const end = ta.selectionEnd;
  const sel = ta.value.substring(start, end);
  const replacement = openTag + sel + closeTag;
  ta.setRangeText(replacement, start, end, 'select');
  ta.focus();
  updateMsgPreview();
}

function rtInsertLink(textareaId) {
  const ta = document.getElementById(textareaId);
  if (!ta) return;
  const url = prompt('Введите URL:');
  if (!url) return;
  const start = ta.selectionStart;
  const end = ta.selectionEnd;
  const sel = ta.value.substring(start, end) || 'текст ссылки';
  const replacement = `<a href="${url}">${sel}</a>`;
  ta.setRangeText(replacement, start, end, 'select');
  ta.focus();
  updateMsgPreview();
}

function showAddMessage(itemId) {
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="createMessage(${itemId})">Создать</button>`;
  openModal('Новое сообщение', messageFormHtml(null), footer);
}

async function showEditMessage(itemId, msgId) {
  try {
    const msgs = await api('GET', `/admin/content/menu/${itemId}/messages`);
    const msg = msgs.find(m => m.id === msgId);
    if (!msg) { toast('Сообщение не найдено', 'error'); return; }
    const footer = `
      <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
      <button class="btn btn-primary" onclick="updateMessage(${itemId},${msgId})">Сохранить</button>`;
    openModal('Редактировать сообщение', messageFormHtml(msg), footer);
  } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
}

async function createMessage(itemId) {
  try {
    const fd = buildMessageFormData();
    await apiUpload('POST', `/admin/content/menu/${itemId}/messages`, fd);
    closeModal();
    toast('Сообщение создано', 'success');
    await loadMessages(itemId);
  } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
}

async function updateMessage(itemId, msgId) {
  try {
    const fd = buildMessageFormData();
    await apiUpload('PUT', `/admin/content/menu/${itemId}/messages/${msgId}`, fd);
    closeModal();
    toast('Сообщение обновлено', 'success');
    await loadMessages(itemId);
  } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
}

async function deleteMessage(itemId, msgId) {
  if (!confirm('Удалить сообщение?')) return;
  try {
    await api('DELETE', `/admin/content/menu/${itemId}/messages/${msgId}`);
    toast('Сообщение удалено', 'success');
    await loadMessages(itemId);
  } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
}

async function moveMessage(itemId, msgId, direction) {
  try {
    const msgs = await api('GET', `/admin/content/menu/${itemId}/messages`);
    const ids = msgs.map(m => m.id);
    const idx = ids.indexOf(msgId);
    if (idx < 0) return;
    const newIdx = idx + direction;
    if (newIdx < 0 || newIdx >= ids.length) return;
    [ids[idx], ids[newIdx]] = [ids[newIdx], ids[idx]];
    await api('POST', `/admin/content/menu/${itemId}/messages/reorder`, { ids_in_order: ids });
    await loadMessages(itemId);
  } catch (err) { toast('Ошибка: ' + err.message, 'error'); }
}

function buildMessageFormData() {
  const type = getVal('msg-type');
  const fd = new FormData();
  fd.append('message_type', type);
  // video_note не поддерживает подпись — отправляем пустой текст.
  fd.append('text', NO_CAPTION_TYPES.has(type) ? '' : getVal('msg-text'));
  fd.append('parse_mode', 'HTML');
  const fileInput = document.getElementById('msg-file');
  if (fileInput?.files?.length) {
    fd.append('file', fileInput.files[0]);
  }
  return fd;
}

function updateMsgPreview() {
  const box = document.getElementById('msg-preview-box');
  if (box) box.innerHTML = sanitizeTgHtml(getVal('msg-text'));
}

async function editStartWelcomeText() {
  if (typeof loadSystemTexts !== 'function' || typeof editSystemText !== 'function') {
    toast('Не удалось открыть редактор приветствия', 'error');
    return;
  }
  _contentTab = 'system';
  history.replaceState(null, '', '#content/system');
  try {
    await loadSystemTexts();
  } catch (err) {
    toast('Ошибка загрузки системных текстов: ' + err.message, 'error');
    return;
  }
  editSystemText(WELCOME_TEXT_KEY);
}

/* ---------- Expose ---------- */
window.loadContentTexts = loadContentTexts;
window.editStartWelcomeText = editStartWelcomeText;
window.sanitizeTgHtml = sanitizeTgHtml;
window.updateMsgPreview = updateMsgPreview;
window.editText = editText;
window.saveText = saveText;
window.toggleMsgCard = toggleMsgCard;
window.showAddMessage = showAddMessage;
window.showEditMessage = showEditMessage;
window.createMessage = createMessage;
window.updateMessage = updateMessage;
window.deleteMessage = deleteMessage;
window.moveMessage = moveMessage;
window.onMsgTypeChange = onMsgTypeChange;
window.rtWrap = rtWrap;
window.rtInsertLink = rtInsertLink;
