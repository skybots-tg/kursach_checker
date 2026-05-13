/* Broadcast Editor — text + media files + buttons + audience + schedule */

window._currentBroadcast = null;
window._currentBcMessage = null;
window._bcFiles = [];
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
    window._bcFiles = data.files || [];

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
  const isDraft = b.status === 'draft' || b.status === 'scheduled';
  const isScheduled = b.status === 'scheduled';
  const msg = window._currentBcMessage;
  const segment = b.target_segment || { type: 'all' };

  let headerBtns = '';
  if (isDraft) {
    headerBtns = `<div style="display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn btn-ghost" onclick="bcOpenTestModal()">${iconSvg('send')} Тест</button>
      ${isScheduled
        ? `<button class="btn btn-ghost btn-danger-ghost" onclick="bcCancelSchedule(${b.id})">Отменить расписание</button>
           <button class="btn btn-primary" onclick="confirmSendBroadcast(${b.id})">${iconSvg('send')} Отправить сейчас</button>`
        : `<button class="btn btn-ghost" onclick="bcOpenScheduleModal()">${iconSvg('clock')} Запланировать</button>
           <button class="btn btn-primary" onclick="confirmSendBroadcast(${b.id})">${iconSvg('send')} Отправить</button>`
      }
    </div>`;
  }

  $('page-broadcasts').innerHTML = `
    <div class="page-header">
      <div style="display:flex;align-items:center;gap:12px">
        <button class="btn btn-ghost" onclick="navigateTo('broadcasts')">${iconSvg('arrowLeft')}</button>
        <div>
          <input class="bc-title-input" id="bc-title" value="${escHtml(b.title)}"
                 ${isDraft ? '' : 'disabled'} onchange="saveBroadcastTitle()" placeholder="Название рассылки">
          <p class="page-subtitle" style="margin-top:4px">${statusBadge(b.status)}
            ${isScheduled && b.scheduled_at ? `<span class="bc-sched-badge">${bcFormatSchedule(b.scheduled_at, b.admin_timezone)}</span>` : ''}
            ${b.status === 'sent' ? `<span style="margin-left:8px;font-size:12px;color:var(--text-muted)">${formatDate(b.sent_at)}</span>` : ''}</p>
        </div>
      </div>
      ${headerBtns}
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
      <div class="bc-section">
        <div class="bc-section-header">Текст сообщения
          ${_bcFiles.length > 0 ? '<span class="bc-section-hint">до 1024 символов (подпись к медиа)</span>' : ''}
        </div>
        <div class="bc-text-block" contenteditable="${isDraft}" id="bc-msg-text"
          data-placeholder="Введите текст сообщения…"
          onblur="onMsgTextBlur()">${msg?.text || ''}</div>
      </div>
      <div class="bc-section">
        <div class="bc-section-header">Медиа <span class="bc-section-hint">до 10 файлов (фото, видео, документы)</span></div>
        <div id="bc-files-zone">${bcRenderFilesZone(isDraft)}</div>
      </div>
      <div class="bc-section">
        <div class="bc-section-header">Кнопки <span class="bc-section-hint">inline-кнопки под сообщением</span></div>
        <div id="bc-buttons-zone">${bcRenderButtonsZone(isDraft, msg)}</div>
      </div>
      <div class="bc-section">
        <div class="bc-section-header">Аудитория</div>
        ${bcRenderAudienceSection(isDraft, segment)}
      </div>
    </div>`;

  if (isDraft) setupFloatingToolbar();
  if (b.status === 'sending') pollBroadcastStatus(b.id);
}

// ---- Files Zone (multiple) ----

function bcRenderFilesZone(isDraft) {
  const files = window._bcFiles || [];
  let html = '';

  if (files.length > 0) {
    html += '<div class="bc-files-grid">';
    for (const f of files) {
      const icon = _mediaIcons[f.media_type] || '📎';
      html += `<div class="bc-file-card" data-id="${f.id}">
        ${f.media_type === 'photo' ? `<div class="bc-file-thumb" style="background-image:url('/api/admin/file-preview?path=${encodeURIComponent(f.file_path)}')"></div>` : `<div class="bc-file-thumb bc-file-thumb-icon">${icon}</div>`}
        <div class="bc-file-card-name" title="${escHtml(f.file_name)}">${escHtml(f.file_name)}</div>
        ${isDraft ? `<button class="bc-file-card-del" onclick="bcDeleteFile(${f.id})" title="Удалить">&times;</button>` : ''}
      </div>`;
    }
    html += '</div>';
  }

  if (isDraft && files.length < 10) {
    html += `<div class="bc-upload-zone" onclick="$('bc-files-input').click()"
      ondragover="event.preventDefault();this.classList.add('drag-over')"
      ondragleave="this.classList.remove('drag-over')" ondrop="bcDropFiles(event)">
      <input type="file" id="bc-files-input" style="display:none" multiple accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.zip,.rar" onchange="bcUploadFiles(this.files)">
      ${iconSvg('download', 24)} <span>${files.length > 0 ? 'Добавить ещё файлы' : 'Нажмите или перетащите файлы'}</span>
      <span class="bc-upload-hint">${files.length}/10</span>
    </div>`;
  } else if (!isDraft && files.length === 0) {
    html += '<div class="bc-no-media-hint">Файлы не прикреплены</div>';
  }

  return html;
}

async function bcUploadFiles(fileList) {
  if (!fileList?.length || !_currentBroadcast) return;
  const maxToAdd = 10 - (_bcFiles?.length || 0);
  const filesToUpload = Array.from(fileList).slice(0, maxToAdd);
  if (!filesToUpload.length) {
    toast('Максимум 10 файлов', 'warning');
    return;
  }

  for (const file of filesToUpload) {
    try {
      const fd = new FormData();
      fd.append('file', file);
      const newFile = await apiUpload('POST', `/admin/broadcasts/${_currentBroadcast.id}/files`, fd);
      _bcFiles.push(newFile);
    } catch (err) {
      toast(`Ошибка загрузки ${file.name}: ${err.message}`, 'error');
    }
  }

  const zone = $('bc-files-zone');
  if (zone) zone.innerHTML = bcRenderFilesZone(true);
  toast(`Загружено файлов: ${filesToUpload.length}`, 'success');
}

function bcDropFiles(e) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  const files = e.dataTransfer?.files;
  if (files?.length) bcUploadFiles(files);
}

async function bcDeleteFile(fid) {
  if (!_currentBroadcast) return;
  try {
    await api('DELETE', `/admin/broadcasts/${_currentBroadcast.id}/files/${fid}`);
    _bcFiles = _bcFiles.filter(f => f.id !== fid);
    const zone = $('bc-files-zone');
    if (zone) zone.innerHTML = bcRenderFilesZone(true);
    toast('Файл удалён', 'success');
  } catch (err) {
    toast(err.message, 'error');
  }
}

const _mediaIcons = {
  photo: '🖼️', video: '🎬', video_note: '⚫', audio: '🎵',
  document: '📎', animation: '🎞️',
};

// ---- Buttons Zone ----

function bcRenderButtonsZone(isDraft, msg) {
  const buttons = msg?.buttons_json || [];
  let html = '<div class="bc-buttons-preview" id="bc-btns-preview">';

  if (buttons.length > 0) {
    let currentRow = [];
    for (let i = 0; i < buttons.length; i++) {
      const btn = buttons[i];
      if (btn.same_row && currentRow.length > 0) {
        currentRow.push({ ...btn, idx: i });
      } else {
        if (currentRow.length > 0) {
          html += bcRenderButtonRow(currentRow, isDraft);
        }
        currentRow = [{ ...btn, idx: i }];
      }
    }
    if (currentRow.length > 0) {
      html += bcRenderButtonRow(currentRow, isDraft);
    }
  }

  html += '</div>';

  if (isDraft) {
    html += `<div class="bc-btn-add-row">
      <button class="btn btn-sm btn-ghost" onclick="bcAddButton()">+ Добавить кнопку</button>
    </div>`;
  }
  return html;
}

function bcRenderButtonRow(rowBtns, isDraft) {
  let html = '<div class="bc-btn-row">';
  for (const btn of rowBtns) {
    html += `<div class="bc-inline-btn">
      <span class="bc-inline-btn-text" title="${escHtml(btn.url || '')}">${escHtml(btn.text || 'Кнопка')}</span>
      ${isDraft ? `<button class="bc-inline-btn-edit" onclick="bcEditButton(${btn.idx})">✎</button>
        <button class="bc-inline-btn-del" onclick="bcRemoveButton(${btn.idx})">&times;</button>` : ''}
    </div>`;
  }
  html += '</div>';
  return html;
}

function bcAddButton() {
  openModal('Добавить кнопку', `
    <div class="bc-btn-form">
      <label>Текст кнопки<input class="form-input" id="bc-btn-text" placeholder="Перейти" maxlength="64"></label>
      <label>URL<input class="form-input" id="bc-btn-url" placeholder="https://..." type="url"></label>
      <label class="bc-btn-samerow-label">
        <input type="checkbox" id="bc-btn-samerow"> В один ряд с предыдущей
      </label>
    </div>
  `, `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="bcSaveNewButton()">Добавить</button>
  `);
}

async function bcSaveNewButton() {
  const text = $('bc-btn-text')?.value?.trim();
  const url = $('bc-btn-url')?.value?.trim();
  const sameRow = $('bc-btn-samerow')?.checked || false;
  if (!text || !url) { toast('Заполните текст и URL', 'error'); return; }

  const msg = window._currentBcMessage;
  if (!msg) return;
  const buttons = [...(msg.buttons_json || [])];
  const entry = { text, url };
  if (sameRow && buttons.length > 0) entry.same_row = true;
  buttons.push(entry);

  await bcSaveButtons(buttons);
  closeModal();
}

function bcEditButton(idx) {
  const msg = window._currentBcMessage;
  if (!msg) return;
  const buttons = msg.buttons_json || [];
  const btn = buttons[idx];
  if (!btn) return;

  openModal('Редактировать кнопку', `
    <div class="bc-btn-form">
      <label>Текст кнопки<input class="form-input" id="bc-btn-text" value="${escHtml(btn.text || '')}" maxlength="64"></label>
      <label>URL<input class="form-input" id="bc-btn-url" value="${escHtml(btn.url || '')}" type="url"></label>
      <label class="bc-btn-samerow-label">
        <input type="checkbox" id="bc-btn-samerow" ${btn.same_row ? 'checked' : ''}> В один ряд с предыдущей
      </label>
    </div>
  `, `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="bcSaveEditButton(${idx})">Сохранить</button>
  `);
}

async function bcSaveEditButton(idx) {
  const text = $('bc-btn-text')?.value?.trim();
  const url = $('bc-btn-url')?.value?.trim();
  const sameRow = $('bc-btn-samerow')?.checked || false;
  if (!text || !url) { toast('Заполните текст и URL', 'error'); return; }

  const msg = window._currentBcMessage;
  if (!msg) return;
  const buttons = [...(msg.buttons_json || [])];
  buttons[idx] = { text, url };
  if (sameRow && idx > 0) buttons[idx].same_row = true;

  await bcSaveButtons(buttons);
  closeModal();
}

async function bcRemoveButton(idx) {
  const msg = window._currentBcMessage;
  if (!msg) return;
  const buttons = [...(msg.buttons_json || [])];
  buttons.splice(idx, 1);
  await bcSaveButtons(buttons);
}

async function bcSaveButtons(buttons) {
  const msg = window._currentBcMessage;
  if (!msg || !_currentBroadcast) return;
  try {
    const updated = await api(
      'PUT',
      `/admin/broadcasts/${_currentBroadcast.id}/messages/${msg.id}/buttons`,
      { buttons_json: buttons.length ? buttons : null },
    );
    window._currentBcMessage = updated;
    const zone = $('bc-buttons-zone');
    if (zone) zone.innerHTML = bcRenderButtonsZone(true, updated);
  } catch (err) {
    toast('Ошибка сохранения кнопок: ' + err.message, 'error');
  }
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
  fd.append('buttons_json', msg.buttons_json ? JSON.stringify(msg.buttons_json) : '');
  if (file) fd.append('file', file);
  try {
    const updated = await apiUpload('PUT', `/admin/broadcasts/${_currentBroadcast.id}/messages/${msg.id}`, fd);
    window._currentBcMessage = updated;
  } catch (err) { toast('Ошибка сохранения: ' + err.message, 'error'); }
}

async function saveBroadcastTitle() {
  const title = $('bc-title')?.value;
  if (!title || !_currentBroadcast || title === _currentBroadcast.title) return;
  try {
    await api('PUT', `/admin/broadcasts/${_currentBroadcast.id}`, { title });
    _currentBroadcast.title = title;
  } catch (err) { toast(err.message, 'error'); }
}

// ---- Schedule ----

const _popularTimezones = [
  { value: 'Europe/Kaliningrad', label: 'Калининград (UTC+2)' },
  { value: 'Europe/Moscow', label: 'Москва (UTC+3)' },
  { value: 'Europe/Samara', label: 'Самара (UTC+4)' },
  { value: 'Asia/Yekaterinburg', label: 'Екатеринбург (UTC+5)' },
  { value: 'Asia/Omsk', label: 'Омск (UTC+6)' },
  { value: 'Asia/Krasnoyarsk', label: 'Красноярск (UTC+7)' },
  { value: 'Asia/Irkutsk', label: 'Иркутск (UTC+8)' },
  { value: 'Asia/Yakutsk', label: 'Якутск (UTC+9)' },
  { value: 'Asia/Vladivostok', label: 'Владивосток (UTC+10)' },
  { value: 'Asia/Magadan', label: 'Магадан (UTC+11)' },
  { value: 'Asia/Kamchatka', label: 'Камчатка (UTC+12)' },
  { value: 'Europe/Kiev', label: 'Киев (UTC+2)' },
  { value: 'Europe/Minsk', label: 'Минск (UTC+3)' },
  { value: 'Asia/Almaty', label: 'Алматы (UTC+6)' },
  { value: 'Asia/Tashkent', label: 'Ташкент (UTC+5)' },
];

function bcOpenScheduleModal() {
  const savedTz = _currentBroadcast?.admin_timezone || 'Europe/Moscow';
  const now = new Date();
  const minDate = now.toISOString().slice(0, 10);
  const defaultTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes() + 5).padStart(2, '0')}`;

  const tzOpts = _popularTimezones.map(tz =>
    `<option value="${tz.value}" ${savedTz === tz.value ? 'selected' : ''}>${tz.label}</option>`
  ).join('');

  openModal('Запланировать рассылку', `
    <div class="bc-schedule-form">
      <label>Дата<input type="date" class="form-input" id="bc-sched-date" min="${minDate}" value="${minDate}"></label>
      <label>Время<input type="time" class="form-input" id="bc-sched-time" value="${defaultTime}"></label>
      <label>Часовой пояс
        <select class="form-input" id="bc-sched-tz">${tzOpts}</select>
      </label>
    </div>
  `, `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="bcDoSchedule()">Запланировать</button>
  `);
}

async function bcDoSchedule() {
  const date = $('bc-sched-date')?.value;
  const time = $('bc-sched-time')?.value;
  const tz = $('bc-sched-tz')?.value;
  if (!date || !time) { toast('Укажите дату и время', 'error'); return; }

  try {
    await api('POST', `/admin/broadcasts/${_currentBroadcast.id}/schedule`, {
      scheduled_at: `${date}T${time}:00`,
      timezone: tz,
    });
    closeModal();
    toast('Рассылка запланирована', 'success');
    await openBroadcastEditor(_currentBroadcast.id);
  } catch (err) { toast(err.message, 'error'); }
}

async function bcCancelSchedule(bid) {
  if (!confirm('Отменить запланированную отправку?')) return;
  try {
    await api('POST', `/admin/broadcasts/${bid}/cancel-schedule`);
    toast('Расписание отменено', 'success');
    await openBroadcastEditor(bid);
  } catch (err) { toast(err.message, 'error'); }
}

function bcFormatSchedule(isoStr, tz) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr + 'Z');
    const opts = { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: tz || 'Europe/Moscow' };
    return d.toLocaleString('ru-RU', opts);
  } catch {
    return isoStr;
  }
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
    <button class="tb-btn" onmousedown="fmtPre(event)" title="Блок кода">PRE</button>
    <button class="tb-btn" onmousedown="fmtSpoiler(event)" title="Спойлер">👁</button>
    <button class="tb-btn" onmousedown="fmtBlockquote(event)" title="Цитата">❝</button>
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
  _wrapSelection('code');
}

function fmtPre(e) {
  e.preventDefault();
  _wrapSelection('pre');
}

function fmtSpoiler(e) {
  e.preventDefault();
  _wrapSelection('tg-spoiler');
}

function fmtBlockquote(e) {
  e.preventDefault();
  _wrapSelection('blockquote');
}

function _wrapSelection(tagName) {
  const sel = window.getSelection();
  if (!sel?.rangeCount) return;
  const range = sel.getRangeAt(0);
  const parent = range.commonAncestorContainer;
  const existing = (parent.nodeType === 3 ? parent.parentElement : parent)?.closest?.(tagName);
  if (existing) {
    existing.replaceWith(document.createTextNode(existing.textContent));
  } else {
    try {
      const el = document.createElement(tagName);
      range.surroundContents(el);
    } catch { /* multi-element selection */ }
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
      else if (t === 'tg-spoiler') out += '<tg-spoiler>' + inner + '</tg-spoiler>';
      else if (t === 'blockquote') out += '<blockquote>' + inner + '</blockquote>';
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

// ---- Exports ----
window.openBroadcastEditor = openBroadcastEditor;
window.saveBroadcastTitle = saveBroadcastTitle;
window.onMsgTextBlur = onMsgTextBlur;
window.onSegmentTypeChange = onSegmentTypeChange;
window.onSegmentDatesChange = onSegmentDatesChange;
window.bcUploadFiles = bcUploadFiles;
window.bcDropFiles = bcDropFiles;
window.bcDeleteFile = bcDeleteFile;
window.bcOpenTestModal = bcOpenTestModal;
window.bcSearchTestUsers = bcSearchTestUsers;
window.bcToggleTestUser = bcToggleTestUser;
window.bcDoTestSend = bcDoTestSend;
window.fmtCmd = fmtCmd;
window.fmtCode = fmtCode;
window.fmtPre = fmtPre;
window.fmtSpoiler = fmtSpoiler;
window.fmtBlockquote = fmtBlockquote;
window.fmtLink = fmtLink;
window.bcAddButton = bcAddButton;
window.bcEditButton = bcEditButton;
window.bcRemoveButton = bcRemoveButton;
window.bcSaveNewButton = bcSaveNewButton;
window.bcSaveEditButton = bcSaveEditButton;
window.bcOpenScheduleModal = bcOpenScheduleModal;
window.bcDoSchedule = bcDoSchedule;
window.bcCancelSchedule = bcCancelSchedule;
window.bcFormatSchedule = bcFormatSchedule;
