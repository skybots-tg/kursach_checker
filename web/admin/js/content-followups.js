/* Content — Follow-ups (Дожимы) tab: editing reminder messages for inactive users */

let _followupMessages = [];
let _followupStats = {};

async function loadFollowups() {
  const [messages, stats] = await Promise.all([
    api('GET', '/admin/content/followups'),
    api('GET', '/admin/content/followups/stats'),
  ]);
  _followupMessages = messages;
  _followupStats = stats;
  renderContentPage(renderFollowupsTab(), '');
}

function renderFollowupsTab() {
  let html = renderFollowupStats();
  html += renderFollowupCards();
  return html;
}

function renderFollowupStats() {
  const s = _followupStats;
  return `
  <div class="stats-grid" style="margin-bottom:24px">
    <div class="stat-card">
      <div class="stat-value">${s.total_users || 0}</div>
      <div class="stat-label">Всего в цепочке</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${s.active_chains || 0}</div>
      <div class="stat-label">Активные цепочки</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${s.converted || 0}</div>
      <div class="stat-label">Конвертированы</div>
    </div>
  </div>`;
}

function renderFollowupCards() {
  if (!_followupMessages.length) {
    return '<div class="alert">Нет настроенных follow-up сообщений. Выполните миграцию БД.</div>';
  }

  return _followupMessages.map(msg => {
    const stepLabels = {1: 'Сообщение 1', 2: 'Сообщение 2', 3: 'Сообщение 3'};
    const delayLabel = formatDelay(msg.delay_minutes);
    const photoCount = (msg.photo_paths || []).length;
    const albumBadge = msg.is_album ? '<span class="badge badge-info">Альбом</span>' : '';
    const activeBadge = msg.active
      ? '<span class="badge badge-success">Активно</span>'
      : '<span class="badge badge-muted">Отключено</span>';

    return `
    <div class="card" style="margin-bottom:16px; padding:20px">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px">
        <div>
          <h3 style="margin:0">${stepLabels[msg.step] || 'Шаг ' + msg.step}</h3>
          <span class="text-muted" style="font-size:13px">Отправка через ${delayLabel} после предыдущего</span>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          ${activeBadge}
          ${albumBadge}
          ${photoCount ? '<span class="badge">' + photoCount + ' фото</span>' : ''}
          <button class="btn btn-sm btn-primary" onclick="editFollowup(${msg.step})">Редактировать</button>
        </div>
      </div>
      <div style="background:var(--bg-secondary, #f7f8fa); border-radius:8px; padding:12px; font-size:13px; max-height:200px; overflow:auto; white-space:pre-wrap">${escHtml(msg.text || '(пусто)')}</div>
      ${msg.button_text ? `<div style="margin-top:8px"><span class="badge badge-info">Кнопка: ${escHtml(msg.button_text)}</span> → <code style="font-size:12px">${escHtml(msg.button_url || '')}</code></div>` : ''}
    </div>`;
  }).join('');
}

function formatDelay(minutes) {
  if (minutes < 60) return minutes + ' мин';
  if (minutes < 1440) return Math.round(minutes / 60) + ' ч';
  return Math.round(minutes / 1440) + ' дн';
}

function editFollowup(step) {
  const msg = _followupMessages.find(m => m.step === step);
  if (!msg) return;

  const stepLabels = {1: 'Сообщение 1 (первое напоминание)', 2: 'Сообщение 2 (подписка на канал)', 3: 'Сообщение 3 (отзывы)'};

  const body = `
    <div class="form-group">
      <label class="form-label">Задержка (минуты)</label>
      <input class="form-input" id="fu-delay" type="number" value="${msg.delay_minutes}">
      <small class="form-hint">15 мин = 15, 10 часов = 600, 24 часа = 1440</small>
    </div>
    <div class="form-group">
      <label class="form-label">Текст сообщения (HTML)</label>
      <textarea class="form-textarea" id="fu-text" rows="10" style="font-family:monospace;font-size:12px">${escHtml(msg.text || '')}</textarea>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div class="form-group">
        <label class="form-label">Текст кнопки</label>
        <input class="form-input" id="fu-btn-text" value="${escHtml(msg.button_text || '')}">
      </div>
      <div class="form-group">
        <label class="form-label">URL кнопки</label>
        <input class="form-input" id="fu-btn-url" value="${escHtml(msg.button_url || '')}">
      </div>
    </div>
    <div class="form-group">
      <label class="form-label">Фото (пути, по одному на строку)</label>
      <textarea class="form-textarea" id="fu-photos" rows="4" style="font-family:monospace;font-size:12px">${escHtml((msg.photo_paths || []).join('\n'))}</textarea>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      <div class="form-group">
        <label class="form-label"><input type="checkbox" id="fu-album" ${msg.is_album ? 'checked' : ''}> Отправить как альбом</label>
      </div>
      <div class="form-group">
        <label class="form-label"><input type="checkbox" id="fu-active" ${msg.active ? 'checked' : ''}> Активно</label>
      </div>
    </div>`;

  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="saveFollowup(${step})">Сохранить</button>`;

  openModal(stepLabels[step] || 'Шаг ' + step, body, footer);
}

async function saveFollowup(step) {
  const delay = parseInt($('fu-delay').value) || 15;
  const text = $('fu-text').value;
  const btnText = $('fu-btn-text').value || null;
  const btnUrl = $('fu-btn-url').value || null;
  const photos = $('fu-photos').value.split('\n').map(s => s.trim()).filter(Boolean);
  const isAlbum = $('fu-album').checked;
  const active = $('fu-active').checked;

  try {
    await api('PUT', `/admin/content/followups/${step}`, {
      delay_minutes: delay,
      text,
      button_text: btnText,
      button_url: btnUrl,
      photo_paths: photos,
      is_album: isAlbum,
      active,
    });
    closeModal();
    showToast('Сохранено');
    await loadFollowups();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

window.loadFollowups = loadFollowups;
window.editFollowup = editFollowup;
window.saveFollowup = saveFollowup;
