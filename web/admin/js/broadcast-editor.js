/* Broadcast Editor — Notion-like block editor */

let _currentBroadcast = null;
window._editorBlocks = [];
let _dragBlockId = null;

async function openBroadcastEditor(broadcastId) {
  $('page-content').innerHTML = loadingHtml();
  try {
    const data = await api('GET', `/admin/broadcasts/${broadcastId}`);
    _currentBroadcast = data;
    window._editorBlocks = data.messages || [];
    renderBroadcastEditor();
  } catch (err) {
    $('page-content').innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderBroadcastEditor() {
  const b = _currentBroadcast;
  const isDraft = b.status === 'draft';

  $('page-content').innerHTML = `
    <div class="page-header">
      <div style="display:flex;align-items:center;gap:12px">
        <button class="btn btn-ghost" onclick="switchContentTab('broadcasts')">${iconSvg('arrowLeft')}</button>
        <div>
          <input class="bc-title-input" id="bc-title" value="${escHtml(b.title)}"
                 ${isDraft ? '' : 'disabled'} onchange="saveBroadcastTitle()" placeholder="Название рассылки">
          <p class="page-subtitle" style="margin-top:4px">${statusBadge(b.status)}
            ${b.status === 'sent' ? `<span style="margin-left:8px;font-size:12px;color:var(--text-muted)">${formatDate(b.sent_at)}</span>` : ''}</p>
        </div>
      </div>
      ${isDraft ? `<button class="btn btn-primary" onclick="confirmSendBroadcast(${b.id})">${iconSvg('send')} Отправить</button>` : ''}
    </div>
    ${b.status === 'sending' ? `
      <div class="bc-progress-bar" id="bc-progress">
        <div class="bc-progress-text">Отправка… ${b.sent_count + b.failed_count} / ${b.total_users}</div>
        <div class="bc-progress-track"><div class="bc-progress-fill" style="width:${b.total_users ? Math.round((b.sent_count + b.failed_count) / b.total_users * 100) : 0}%"></div></div>
      </div>` : ''}
    ${b.status === 'sent' ? `
      <div class="bc-stats-row">
        <div class="bc-stat"><div class="bc-stat-val">${b.total_users}</div><div class="bc-stat-label">Всего</div></div>
        <div class="bc-stat bc-stat-ok"><div class="bc-stat-val">${b.sent_count}</div><div class="bc-stat-label">Доставлено</div></div>
        <div class="bc-stat bc-stat-err"><div class="bc-stat-val">${b.failed_count}</div><div class="bc-stat-label">Ошибок</div></div>
      </div>` : ''}
    <div class="bc-editor" id="bc-editor">
      <div class="bc-blocks" id="bc-blocks"></div>
      ${isDraft ? `<button class="bc-add-btn" onclick="showBlockTypeMenu(event)">${iconSvg('plus')} Добавить блок</button>` : ''}
    </div>`;

  renderEditorBlocks();
  if (isDraft) { setupFloatingToolbar(); initBlockDrag(); }
  if (b.status === 'sending') pollBroadcastStatus(b.id);
}

// ---- Render Blocks ----

function renderEditorBlocks() {
  const container = $('bc-blocks');
  if (!container) return;
  const isDraft = _currentBroadcast?.status === 'draft';
  const blocks = window._editorBlocks;

  if (!blocks.length) {
    container.innerHTML = isDraft
      ? emptyHtml('Пусто', 'Добавьте первый блок сообщения')
      : emptyHtml('Нет сообщений', '');
    return;
  }

  const typeLabels = { text: 'Текст', photo: 'Фото', video: 'Видео', document: 'Файл', audio: 'Аудио', animation: 'GIF' };
  const mediaIcons = { photo: '🖼️', video: '🎬', audio: '🎵', document: '📎', animation: '🎞️' };

  container.innerHTML = blocks.map(block => {
    const label = typeLabels[block.message_type] || block.message_type;
    const isMedia = block.message_type !== 'text';

    let content = '';
    if (!isMedia) {
      content = `<div class="bc-text-block" contenteditable="${isDraft}" data-msg-id="${block.id}"
        data-placeholder="Введите текст сообщения…" onblur="onBlockBlur(${block.id}, this)">${block.text || ''}</div>`;
    } else {
      const accept = { photo: 'image/*', video: 'video/*', audio: 'audio/*', animation: 'image/gif' }[block.message_type] || '*/*';
      if (block.file_name) {
        content += `<div class="bc-file-info">
          <span class="bc-file-icon">${mediaIcons[block.message_type] || '📎'}</span>
          <span class="bc-file-name">${escHtml(block.file_name)}</span>
          ${isDraft ? `<button class="btn btn-sm btn-ghost" onclick="reuploadBlockFile(${block.id})">Заменить</button>` : ''}
        </div>`;
      } else if (isDraft) {
        content += `<div class="bc-upload-zone" onclick="$('bc-file-${block.id}').click()"
          ondragover="event.preventDefault();this.classList.add('drag-over')"
          ondragleave="this.classList.remove('drag-over')"
          ondrop="dropBlockFile(event,${block.id})">
          <input type="file" id="bc-file-${block.id}" style="display:none" accept="${accept}"
                 onchange="uploadBlockFile(${block.id},this.files[0])">
          ${iconSvg('download', 24)}
          <span>Нажмите или перетащите файл</span>
        </div>`;
      } else {
        content += '<div class="bc-no-file">Файл не прикреплён</div>';
      }
      content += `<div class="bc-text-block bc-caption" contenteditable="${isDraft}" data-msg-id="${block.id}"
        data-placeholder="Подпись (необязательно)…" onblur="onBlockBlur(${block.id}, this)">${block.text || ''}</div>`;
    }

    return `<div class="bc-block" data-block-id="${block.id}" draggable="${isDraft}">
      ${isDraft ? '<div class="bc-block-handle" title="Перетащить">⠿</div>' : ''}
      <div class="bc-block-body">
        <div class="bc-block-type-label">${label}</div>
        ${content}
      </div>
      ${isDraft ? `<button class="bc-block-del" onclick="deleteBlock(${block.id})" title="Удалить">${iconSvg('trash', 14)}</button>` : ''}
    </div>`;
  }).join('');
}

// ---- Block CRUD ----

async function addBlock(type) {
  hideBlockTypeMenu();
  const fd = new FormData();
  fd.append('message_type', type);
  fd.append('text', '');
  try {
    const msg = await apiUpload('POST', `/admin/broadcasts/${_currentBroadcast.id}/messages`, fd);
    window._editorBlocks.push(msg);
    renderEditorBlocks();
    initBlockDrag();
    setTimeout(() => {
      const el = document.querySelector(`[data-msg-id="${msg.id}"]`);
      if (el) el.focus();
    }, 50);
  } catch (err) { toast(err.message, 'error'); }
}

async function deleteBlock(msgId) {
  if (!confirm('Удалить этот блок?')) return;
  try {
    await api('DELETE', `/admin/broadcasts/${_currentBroadcast.id}/messages/${msgId}`);
    window._editorBlocks = window._editorBlocks.filter(b => b.id !== msgId);
    renderEditorBlocks();
    initBlockDrag();
    toast('Блок удалён', 'success');
  } catch (err) { toast(err.message, 'error'); }
}

function onBlockBlur(msgId, el) {
  const block = window._editorBlocks.find(b => b.id === msgId);
  if (!block) return;
  const newText = cleanForTelegram(el.innerHTML);
  if (newText === (block.text || '')) return;
  block.text = newText;
  const fd = new FormData();
  fd.append('message_type', block.message_type);
  fd.append('text', newText);
  fd.append('parse_mode', block.parse_mode || 'HTML');
  apiUpload('PUT', `/admin/broadcasts/${_currentBroadcast.id}/messages/${block.id}`, fd)
    .catch(err => toast('Ошибка сохранения: ' + err.message, 'error'));
}

async function uploadBlockFile(msgId, file) {
  if (!file) return;
  const block = window._editorBlocks.find(b => b.id === msgId);
  const fd = new FormData();
  fd.append('message_type', block?.message_type || 'document');
  fd.append('text', block?.text || '');
  fd.append('file', file);
  try {
    const updated = await apiUpload('PUT', `/admin/broadcasts/${_currentBroadcast.id}/messages/${msgId}`, fd);
    const idx = window._editorBlocks.findIndex(b => b.id === msgId);
    if (idx !== -1) window._editorBlocks[idx] = updated;
    renderEditorBlocks();
    initBlockDrag();
    toast('Файл загружен', 'success');
  } catch (err) { toast(err.message, 'error'); }
}

function dropBlockFile(e, msgId) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  const file = e.dataTransfer?.files?.[0];
  if (file) uploadBlockFile(msgId, file);
}

function reuploadBlockFile(msgId) {
  const tmp = document.createElement('input');
  tmp.type = 'file';
  tmp.onchange = () => uploadBlockFile(msgId, tmp.files[0]);
  tmp.click();
}

async function saveBroadcastTitle() {
  const title = $('bc-title')?.value;
  if (!title || !_currentBroadcast || title === _currentBroadcast.title) return;
  try {
    await api('PUT', `/admin/broadcasts/${_currentBroadcast.id}`, { title });
    _currentBroadcast.title = title;
  } catch (err) { toast(err.message, 'error'); }
}

// ---- Block Type Menu ----

function showBlockTypeMenu(e) {
  hideBlockTypeMenu();
  const rect = e.currentTarget.getBoundingClientRect();
  const menu = document.createElement('div');
  menu.className = 'bc-type-menu';
  menu.id = 'bc-type-menu';
  menu.innerHTML = [
    ['text', '📝', 'Текст'],
    ['photo', '🖼️', 'Фото'],
    ['video', '🎬', 'Видео'],
    ['document', '📎', 'Файл / Документ'],
    ['audio', '🎵', 'Аудио'],
    ['animation', '🎞️', 'GIF / Анимация'],
  ].map(([t, icon, label]) =>
    `<button class="bc-type-menu-item" onclick="addBlock('${t}')"><span>${icon}</span> ${label}</button>`
  ).join('');
  document.body.appendChild(menu);
  menu.style.left = Math.min(rect.left, window.innerWidth - 220) + 'px';
  menu.style.top = (rect.bottom + 4) + 'px';
  setTimeout(() => document.addEventListener('click', hideBlockTypeMenu, { once: true }), 10);
}

function hideBlockTypeMenu() { $('bc-type-menu')?.remove(); }

// ---- Drag & Drop ----

function initBlockDrag() {
  const c = $('bc-blocks');
  if (!c) return;
  c.ondragstart = e => {
    const bl = e.target.closest('.bc-block');
    if (!bl) return;
    _dragBlockId = parseInt(bl.dataset.blockId);
    bl.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
  };
  c.ondragend = e => {
    e.target.closest?.('.bc-block')?.classList.remove('dragging');
    c.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
    _dragBlockId = null;
  };
  c.ondragover = e => {
    e.preventDefault();
    const bl = e.target.closest('.bc-block');
    if (!bl || parseInt(bl.dataset.blockId) === _dragBlockId) return;
    c.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
    bl.classList.add('drag-over');
  };
  c.ondrop = async e => {
    e.preventDefault();
    const target = e.target.closest('.bc-block');
    if (!target || !_dragBlockId) return;
    const tid = parseInt(target.dataset.blockId);
    if (tid === _dragBlockId) return;
    const fi = window._editorBlocks.findIndex(b => b.id === _dragBlockId);
    const ti = window._editorBlocks.findIndex(b => b.id === tid);
    if (fi === -1 || ti === -1) return;
    const [moved] = window._editorBlocks.splice(fi, 1);
    window._editorBlocks.splice(ti, 0, moved);
    renderEditorBlocks();
    initBlockDrag();
    try {
      await api('POST', `/admin/broadcasts/${_currentBroadcast.id}/messages/reorder`, {
        ids_in_order: window._editorBlocks.map(b => b.id),
      });
    } catch (err) { toast(err.message, 'error'); }
  };
}

// ---- Floating Toolbar ----

function setupFloatingToolbar() {
  $('bc-toolbar')?.remove();
  const tb = document.createElement('div');
  tb.className = 'bc-toolbar';
  tb.id = 'bc-toolbar';
  tb.style.display = 'none';
  tb.innerHTML = `
    <button class="tb-btn" onmousedown="fmtCmd(event,'bold')" title="Жирный (Ctrl+B)"><b>B</b></button>
    <button class="tb-btn" onmousedown="fmtCmd(event,'italic')" title="Курсив (Ctrl+I)"><i>I</i></button>
    <button class="tb-btn" onmousedown="fmtCmd(event,'underline')" title="Подчёркнутый (Ctrl+U)"><u>U</u></button>
    <button class="tb-btn" onmousedown="fmtCmd(event,'strikeThrough')" title="Зачёркнутый"><s>S</s></button>
    <span class="tb-sep"></span>
    <button class="tb-btn tb-btn-code" onmousedown="fmtCode(event)" title="Код">&lt;/&gt;</button>
    <button class="tb-btn" onmousedown="fmtLink(event)" title="Ссылка">🔗</button>`;
  document.body.appendChild(tb);
  document.addEventListener('selectionchange', positionToolbar);
}

function positionToolbar() {
  const tb = $('bc-toolbar');
  if (!tb) return;
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed || !sel.rangeCount) { tb.style.display = 'none'; return; }
  const anchor = sel.anchorNode;
  const textBlock = (anchor?.nodeType === 3 ? anchor.parentElement : anchor)?.closest?.('.bc-text-block');
  if (!textBlock) { tb.style.display = 'none'; return; }
  const rect = sel.getRangeAt(0).getBoundingClientRect();
  tb.style.display = 'flex';
  tb.style.left = Math.max(8, rect.left + rect.width / 2 - tb.offsetWidth / 2) + 'px';
  tb.style.top = Math.max(8, rect.top - 44) + 'px';
}

function fmtCmd(e, cmd) { e.preventDefault(); document.execCommand(cmd); }

function fmtCode(e) {
  e.preventDefault();
  const sel = window.getSelection();
  if (!sel?.rangeCount) return;
  const range = sel.getRangeAt(0);
  const parent = range.commonAncestorContainer;
  const codeEl = (parent.nodeType === 3 ? parent.parentElement : parent)?.closest('code');
  if (codeEl) {
    codeEl.replaceWith(document.createTextNode(codeEl.textContent));
  } else {
    try { const code = document.createElement('code'); range.surroundContents(code); } catch { /* multi-element */ }
  }
}

function fmtLink(e) {
  e.preventDefault();
  const url = prompt('URL ссылки:');
  if (url) document.execCommand('createLink', false, url);
}

// ---- HTML Sanitization for Telegram ----

function cleanForTelegram(html) {
  if (!html) return '';
  const div = document.createElement('div');
  div.innerHTML = html;
  return _tgNode(div).trim();
}

function _tgNode(node) {
  let out = '';
  for (const c of node.childNodes) {
    if (c.nodeType === 3) {
      out += c.textContent.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    } else if (c.nodeType === 1) {
      const t = c.tagName.toLowerCase(), inner = _tgNode(c);
      if (t === 'b' || t === 'strong') out += '<b>' + inner + '</b>';
      else if (t === 'i' || t === 'em') out += '<i>' + inner + '</i>';
      else if (t === 'u') out += '<u>' + inner + '</u>';
      else if (t === 's' || t === 'strike' || t === 'del') out += '<s>' + inner + '</s>';
      else if (t === 'code') out += '<code>' + inner + '</code>';
      else if (t === 'pre') out += '<pre>' + inner + '</pre>';
      else if (t === 'a') out += `<a href="${c.getAttribute('href') || ''}">${inner}</a>`;
      else if (t === 'br') out += '\n';
      else if (t === 'div' || t === 'p') { if (out && !out.endsWith('\n')) out += '\n'; out += inner; }
      else out += inner;
    }
  }
  return out;
}

// ---- Poll Status ----

function pollBroadcastStatus(broadcastId) {
  const iv = setInterval(async () => {
    try {
      const data = await api('GET', `/admin/broadcasts/${broadcastId}/status`);
      Object.assign(_currentBroadcast, data);
      if (data.status !== 'sending') {
        clearInterval(iv);
        renderBroadcastEditor();
        toast(data.status === 'sent' ? 'Рассылка отправлена!' : 'Ошибка при отправке',
          data.status === 'sent' ? 'success' : 'error');
        return;
      }
      const el = $('bc-progress');
      if (el) {
        const done = data.sent_count + data.failed_count;
        el.querySelector('.bc-progress-text').textContent = `Отправка… ${done} / ${data.total_users}`;
        el.querySelector('.bc-progress-fill').style.width =
          (data.total_users ? Math.round(done / data.total_users * 100) : 0) + '%';
      }
    } catch { /* ignore polling errors */ }
  }, 2000);
}

window.openBroadcastEditor = openBroadcastEditor;
window.saveBroadcastTitle = saveBroadcastTitle;
window.onBlockBlur = onBlockBlur;
window.addBlock = addBlock;
window.deleteBlock = deleteBlock;
window.uploadBlockFile = uploadBlockFile;
window.dropBlockFile = dropBlockFile;
window.reuploadBlockFile = reuploadBlockFile;
window.showBlockTypeMenu = showBlockTypeMenu;
window.hideBlockTypeMenu = hideBlockTypeMenu;
window.fmtCmd = fmtCmd;
window.fmtCode = fmtCode;
window.fmtLink = fmtLink;
