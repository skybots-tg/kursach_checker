/* Broadcast Editor — text + media + audience + test send */

window._currentBroadcast = null;
window._currentBcMessage = null;
let _audienceDebounce = null;

let _bcEditorLoading = false;

async function openBroadcastEditor(broadcastId) {
  if (_bcEditorLoading) return;
  _bcEditorLoading = true;
  $('page-broadcasts').innerHTML = loadingHtml();
  try {
    const data = await api('GET', `/admin/broadcasts/${broadcastId}`);
    _currentBroadcast = data;

    if (data.status === 'draft' && data.messages?.length > 1) {
      for (let i = 1; i < data.messages.length; i++) {
        await api('DELETE', `/admin/broadcasts/${broadcastId}/messages/${data.messages[i].id}`);
      }
      data.messages = data.messages.slice(0, 1);
    }

    window._currentBcMessage = data.messages?.[0] || null;

    if (!window._currentBcMessage && data.status === 'draft') {
      const fd = new FormData();
      fd.append('message_type', 'text');
      fd.append('text', '');
      window._currentBcMessage = await apiUpload(
        'POST', `/admin/broadcasts/${broadcastId}/messages`, fd,
      );
    }

    renderBroadcastEditor();
    if (data.status === 'draft') bcFetchAudienceCount();
  } catch (err) {
    $('page-broadcasts').innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  } finally {
    _bcEditorLoading = false;
  }
}

function renderBroadcastEditor() {
  const b = _currentBroadcast;
  const isDraft = b.status === 'draft';
  const msg = window._currentBcMessage;
  const hasMedia = msg && msg.message_type !== 'text';
    const mediaType = hasMedia ? msg.message_type : '';
    const noCaption = mediaType === 'video_note';
  const segment = b.target_segment || { type: 'all' };

  $('page-broadcasts').innerHTML = `
    <div class="page-header">
      <div style="display:flex;align-items:center;gap:12px">
        <button class="btn btn-ghost" onclick="navigateTo('broadcasts')">${iconSvg('arrowLeft')}</button>
        <div>
          <input class="bc-title-input" id="bc-title" value="${escHtml(b.title)}"
                 ${isDraft ? '' : 'disabled'} onchange="saveBroadcastTitle()" placeholder="Название рассылки">
          <p class="page-subtitle" style="margin-top:4px">${statusBadge(b.status)}
            ${b.status === 'sent' ? `<span style="margin-left:8px;font-size:12px;color:var(--text-muted)">${formatDate(b.sent_at)}</span>` : ''}</p>
        </div>
      </div>
      ${isDraft ? `<div style="display:flex;gap:8px">
        <button class="btn btn-ghost" onclick="bcOpenTestModal()">${iconSvg('send')} Тест</button>
        <button class="btn btn-primary" onclick="confirmSendBroadcast(${b.id})">${iconSvg('send')} Отправить</button>
      </div>` : ''}
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
      ${noCaption ? '' : `<div class="bc-section">
        <div class="bc-section-header">
          ${hasMedia ? 'Подпись' : 'Текст сообщения'}
          ${hasMedia ? '<span class="bc-section-hint">до 1024 символов</span>' : ''}
        </div>
        <div class="bc-text-block" contenteditable="${isDraft}" id="bc-msg-text"
          data-placeholder="${hasMedia ? 'Подпись к медиа (необязательно)…' : 'Введите текст сообщения…'}"
          onblur="onMsgTextBlur()">${msg?.text || ''}</div>
      </div>`}
      <div class="bc-section">
        <div class="bc-section-header">Медиа <span class="bc-section-hint">необязательно</span></div>
        ${isDraft ? bcMediaTypeSelector(mediaType) : (hasMedia ? bcMediaTypeLabel(mediaType) : '')}
        <div id="bc-media-zone">${bcRenderMediaZone(isDraft, mediaType, msg)}</div>
      </div>
      <div class="bc-section">
        <div class="bc-section-header">Аудитория</div>
        ${bcRenderAudienceSection(isDraft, segment)}
      </div>
    </div>`;

  if (isDraft) setupFloatingToolbar();
  if (b.status === 'sending') pollBroadcastStatus(b.id);
}

// ---- Audience Section ----

const _segmentLabels = {
  all: 'Все пользователи',
  paid: 'Оплачивали',
  viewers: 'Только смотрели',
  unpaid_invoice: 'Создали счёт, но не оплатили',
  recent: 'Зарегистрировались недавно',
};

function bcRenderAudienceSection(isDraft, segment) {
  const segType = segment.type || 'all';
  const needsDates = segType === 'unpaid_invoice' || segType === 'recent';
  const segOpts = Object.entries(_segmentLabels)
    .map(([k, v]) => `<option value="${k}" ${segType === k ? 'selected' : ''}>${v}</option>`)
    .join('');

  let html = '';
  if (isDraft) {
    html += `<select id="bc-segment-type" onchange="onSegmentTypeChange()" class="bc-media-select">${segOpts}</select>`;
    if (needsDates) {
      html += `<div class="bc-date-row">
        <label>С <input type="date" id="bc-seg-from" value="${segment.date_from || ''}" onchange="onSegmentDatesChange()"></label>
        <label>По <input type="date" id="bc-seg-to" value="${segment.date_to || ''}" onchange="onSegmentDatesChange()"></label>
      </div>`;
    }
  } else {
    html += `<div class="bc-media-type-badge">${_segmentLabels[segType] || segType}</div>`;
  }
  html += `<div class="bc-audience-counter" id="bc-audience-counter">
    <span class="bc-audience-spinner"></span> Подсчёт…
  </div>`;
  return html;
}

async function onSegmentTypeChange() {
  const segType = $('bc-segment-type')?.value || 'all';
  const segment = { type: segType };
  _currentBroadcast.target_segment = segment;
  await api('PUT', `/admin/broadcasts/${_currentBroadcast.id}`, { target_segment: segment });
  renderBroadcastEditor();
  bcFetchAudienceCount();
}

async function onSegmentDatesChange() {
  const segType = $('bc-segment-type')?.value || 'all';
  const segment = {
    type: segType,
    date_from: $('bc-seg-from')?.value || undefined,
    date_to: $('bc-seg-to')?.value || undefined,
  };
  _currentBroadcast.target_segment = segment;
  await api('PUT', `/admin/broadcasts/${_currentBroadcast.id}`, { target_segment: segment });
  bcFetchAudienceCountDebounced();
}

function bcFetchAudienceCountDebounced() {
  clearTimeout(_audienceDebounce);
  _audienceDebounce = setTimeout(bcFetchAudienceCount, 400);
}

async function bcFetchAudienceCount() {
  const el = $('bc-audience-counter');
  if (!el) return;
  const segment = _currentBroadcast?.target_segment || { type: 'all' };
  try {
    const data = await api('POST', '/admin/broadcasts/audience/count', { segment });
    if (!$('bc-audience-counter')) return;
    $('bc-audience-counter').innerHTML = `<b>${data.total}</b> получателей`
      + (data.total !== data.active ? ` <span class="bc-audience-active">(${data.active} активных)</span>` : '');
  } catch {
    if (el) el.innerHTML = '<span style="color:var(--danger)">Ошибка подсчёта</span>';
  }
}

// ---- Test Send Modal ----

let _testSelectedUsers = [];

function bcOpenTestModal() {
  _testSelectedUsers = [];
  openModal('Тестовая отправка', `
    <p style="margin-bottom:12px;color:var(--text-muted)">Найдите пользователей и отправьте им сообщение для проверки. Статус рассылки не изменится.</p>
    <input class="form-input" id="bc-test-search" placeholder="Поиск по имени или username…"
      oninput="bcSearchTestUsers()" autocomplete="off">
    <div id="bc-test-results" class="bc-test-results"></div>
    <div id="bc-test-selected" class="bc-test-selected"></div>
  `, `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" id="bc-test-send-btn" onclick="bcDoTestSend()" disabled>Отправить тест</button>
  `);
}

let _testSearchDebounce = null;
function bcSearchTestUsers() {
  clearTimeout(_testSearchDebounce);
  _testSearchDebounce = setTimeout(async () => {
    const q = $('bc-test-search')?.value?.trim();
    const el = $('bc-test-results');
    if (!el || !q || q.length < 2) { if (el) el.innerHTML = ''; return; }
    try {
      const users = await api('GET', `/admin/users?q=${encodeURIComponent(q)}&limit=10`);
      el.innerHTML = (users.items || users).map(u => {
        const checked = _testSelectedUsers.some(s => s.telegram_id === u.telegram_id);
        const name = escHtml(u.first_name || '') + (u.username ? ` @${escHtml(u.username)}` : '');
        return `<label class="bc-test-user ${checked ? 'selected' : ''}">
          <input type="checkbox" ${checked ? 'checked' : ''} onchange="bcToggleTestUser(${u.telegram_id}, '${escHtml(u.first_name || '')}', '${escHtml(u.username || '')}', this.checked)">
          <span>${name}</span> <span class="bc-test-tgid">${u.telegram_id}</span>
        </label>`;
      }).join('') || '<div style="padding:8px;color:var(--text-muted)">Не найдено</div>';
    } catch { el.innerHTML = '<div style="padding:8px;color:var(--danger)">Ошибка поиска</div>'; }
  }, 300);
}

function bcToggleTestUser(telegramId, firstName, username, checked) {
  if (checked) {
    if (!_testSelectedUsers.some(u => u.telegram_id === telegramId)) {
      _testSelectedUsers.push({ telegram_id: telegramId, first_name: firstName, username });
    }
  } else {
    _testSelectedUsers = _testSelectedUsers.filter(u => u.telegram_id !== telegramId);
  }
  bcRenderTestSelected();
}

function bcRenderTestSelected() {
  const el = $('bc-test-selected');
  const btn = $('bc-test-send-btn');
  if (!el) return;
  if (!_testSelectedUsers.length) {
    el.innerHTML = '';
    if (btn) btn.disabled = true;
    return;
  }
  if (btn) btn.disabled = false;
  el.innerHTML = '<div class="bc-test-chips">' + _testSelectedUsers.map(u => {
    const name = u.first_name + (u.username ? ` @${u.username}` : '');
    return `<span class="bc-test-chip">${escHtml(name)} <button onclick="bcToggleTestUser(${u.telegram_id},'','',false);bcSearchTestUsers()">×</button></span>`;
  }).join('') + '</div>';
}

async function bcDoTestSend() {
  if (!_testSelectedUsers.length || !_currentBroadcast) return;
  const ids = _testSelectedUsers.map(u => u.telegram_id);
  try {
    const res = await api('POST', `/admin/broadcasts/${_currentBroadcast.id}/test-send`, { telegram_ids: ids });
    closeModal();
    toast(`Тест отправлен: ${res.sent} доставлено, ${res.failed} ошибок`, res.failed ? 'warning' : 'success');
  } catch (err) { toast(err.message, 'error'); }
}

// ---- Media Section ----

const _mediaLabels = {
  photo: 'Фото', video: 'Видео', video_note: 'Кружок',
  document: 'Документ', audio: 'Аудио', animation: 'GIF',
};
const _mediaIcons = {
  photo: '🖼️', video: '🎬', video_note: '⚫', audio: '🎵',
  document: '📎', animation: '🎞️',
};

function bcMediaTypeSelector(mediaType) {
  const opts = [['', 'Без медиа'], ['photo', '🖼️ Фото'], ['video', '🎬 Видео'],
    ['video_note', '⚫ Кружок'], ['document', '📎 Документ'], ['audio', '🎵 Аудио'],
    ['animation', '🎞️ GIF']];
  return `<div class="bc-media-type-row">
    <select id="bc-media-type" onchange="onMediaTypeChange()" class="bc-media-select">
      ${opts.map(([v, l]) => `<option value="${v}" ${mediaType === v ? 'selected' : ''}>${l}</option>`).join('')}
    </select>
  </div>`;
}

function bcMediaTypeLabel(mediaType) {
  if (!mediaType) return '';
  return `<div class="bc-media-type-row">
    <span class="bc-media-type-badge">${_mediaIcons[mediaType] || ''} ${_mediaLabels[mediaType] || mediaType}</span>
  </div>`;
}

function bcRenderMediaZone(isDraft, mediaType, msg) {
  if (!mediaType) {
    return isDraft ? '<div class="bc-no-media-hint">Выберите тип, чтобы прикрепить файл</div>' : '';
  }
  const noCaptionHint = mediaType === 'video_note'
    ? '<div class="bc-no-media-hint" style="margin-bottom:8px">Кружок не поддерживает подпись</div>' : '';
  const accept = { photo: 'image/*', video: 'video/*', video_note: 'video/*', audio: 'audio/*', animation: 'image/gif' }[mediaType] || '*/*';
  if (msg?.file_name) {
    let html = noCaptionHint + `<div class="bc-file-info">
      <span class="bc-file-icon">${_mediaIcons[mediaType] || '📎'}</span>
      <span class="bc-file-name">${escHtml(msg.file_name)}</span>`;
    if (isDraft) html += `<button class="btn btn-sm btn-ghost" onclick="bcReuploadFile()">Заменить</button>`;
    return html + '</div>';
  }
  if (isDraft) {
    return noCaptionHint + `<div class="bc-upload-zone" onclick="$('bc-file-input').click()"
      ondragover="event.preventDefault();this.classList.add('drag-over')"
      ondragleave="this.classList.remove('drag-over')" ondrop="bcDropFile(event)">
      <input type="file" id="bc-file-input" style="display:none" accept="${accept}" onchange="bcUploadFile(this.files[0])">
      ${iconSvg('download', 24)} <span>Нажмите или перетащите файл</span></div>`;
  }
  return '<div class="bc-no-file">Файл не прикреплён</div>';
}

// ---- Save helpers ----

function onMsgTextBlur() {
  const msg = window._currentBcMessage;
  if (!msg) return;
  const el = $('bc-msg-text');
  if (!el) return;
  const newText = cleanForTelegram(el.innerHTML);
  if (newText === (msg.text || '')) return;
  msg.text = newText;
  bcSaveMessage();
}

async function bcSaveMessage(file) {
  const msg = window._currentBcMessage;
  if (!msg || !_currentBroadcast) return;
  const fd = new FormData();
  fd.append('message_type', msg.message_type);
  fd.append('text', msg.text || '');
  fd.append('parse_mode', msg.parse_mode || 'HTML');
  if (file) fd.append('file', file);
  try {
    const updated = await apiUpload('PUT', `/admin/broadcasts/${_currentBroadcast.id}/messages/${msg.id}`, fd);
    window._currentBcMessage = updated;
  } catch (err) { toast('Ошибка сохранения: ' + err.message, 'error'); }
}

async function onMediaTypeChange() {
  const newType = $('bc-media-type')?.value || '';
  const msg = window._currentBcMessage;
  if (!msg) return;
  msg.message_type = newType || 'text';
  msg.file_name = null;
  msg.file_path = null;
  await bcSaveMessage();
  renderBroadcastEditor();
  if (_currentBroadcast?.status === 'draft') bcFetchAudienceCount();
}

async function bcUploadFile(file) {
  if (!file || !window._currentBcMessage) return;
  const msg = window._currentBcMessage;
  const fd = new FormData();
  fd.append('message_type', msg.message_type);
  fd.append('text', msg.text || '');
  fd.append('parse_mode', msg.parse_mode || 'HTML');
  fd.append('file', file);
  try {
    const updated = await apiUpload('PUT', `/admin/broadcasts/${_currentBroadcast.id}/messages/${msg.id}`, fd);
    window._currentBcMessage = updated;
    renderBroadcastEditor();
    if (_currentBroadcast?.status === 'draft') bcFetchAudienceCount();
    toast('Файл загружен', 'success');
  } catch (err) { toast(err.message, 'error'); }
}

function bcDropFile(e) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  const file = e.dataTransfer?.files?.[0];
  if (file) bcUploadFile(file);
}

function bcReuploadFile() {
  const tmp = document.createElement('input');
  tmp.type = 'file';
  tmp.onchange = () => bcUploadFile(tmp.files[0]);
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

// ---- Floating Toolbar ----

function setupFloatingToolbar() {
  $('bc-toolbar')?.remove();
  const tb = document.createElement('div');
  tb.className = 'bc-toolbar'; tb.id = 'bc-toolbar'; tb.style.display = 'none';
  tb.innerHTML = `
    <button class="tb-btn" onmousedown="fmtCmd(event,'bold')" title="Жирный"><b>B</b></button>
    <button class="tb-btn" onmousedown="fmtCmd(event,'italic')" title="Курсив"><i>I</i></button>
    <button class="tb-btn" onmousedown="fmtCmd(event,'underline')" title="Подчёркнутый"><u>U</u></button>
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
  if (codeEl) { codeEl.replaceWith(document.createTextNode(codeEl.textContent)); }
  else { try { const code = document.createElement('code'); range.surroundContents(code); } catch { /* multi-element */ } }
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
window.onMsgTextBlur = onMsgTextBlur;
window.onMediaTypeChange = onMediaTypeChange;
window.onSegmentTypeChange = onSegmentTypeChange;
window.onSegmentDatesChange = onSegmentDatesChange;
window.bcUploadFile = bcUploadFile;
window.bcDropFile = bcDropFile;
window.bcReuploadFile = bcReuploadFile;
window.bcOpenTestModal = bcOpenTestModal;
window.bcSearchTestUsers = bcSearchTestUsers;
window.bcToggleTestUser = bcToggleTestUser;
window.bcDoTestSend = bcDoTestSend;
window.fmtCmd = fmtCmd;
window.fmtCode = fmtCode;
window.fmtLink = fmtLink;
