/* Content — Follow-ups (Дожимы) tab: editing reminder messages for inactive users */

let _followupMessages = [];
let _followupStats = {};
let _followupEligible = 0;

async function loadFollowups() {
  const [messages, stats, eligible] = await Promise.all([
    api('GET', '/admin/content/followups'),
    api('GET', '/admin/content/followups/stats'),
    api('GET', '/admin/content/followups/eligible-count'),
  ]);
  _followupMessages = messages;
  _followupStats = stats;
  _followupEligible = eligible.eligible || 0;
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
  </div>
  <div class="card" style="margin-bottom:24px; padding:16px; display:flex; align-items:center; justify-content:space-between">
    <div>
      <b>Старые юзеры без цепочки</b>
      <span class="text-muted" style="margin-left:8px">${_followupEligible} чел. (без загрузок и без дожимов)</span>
    </div>
    <button class="btn btn-sm ${_followupEligible ? 'btn-primary' : 'btn-ghost'}" onclick="enrollExistingUsers()" ${_followupEligible ? '' : 'disabled'}>
      Запустить дожимы
    </button>
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
          <button class="btn btn-sm btn-ghost" onclick="openTestSend(${msg.step})">Тест</button>
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

async function enrollExistingUsers() {
  const body = `<p>Будет запущена цепочка дожимов для <b>${_followupEligible}</b> старых юзеров, которые ещё не загружали документы и не состоят в цепочке.</p><p>Они начнут получать сообщения с шага 1.</p>`;
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="confirmEnrollExisting()">Запустить</button>`;
  openModal('Запустить дожимы для старых юзеров', body, footer);
}

async function confirmEnrollExisting() {
  try {
    const res = await api('POST', '/admin/content/followups/enroll-existing');
    closeModal();
    showToast(`Дожимы запущены для ${res.enrolled} юзеров`);
    await loadFollowups();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

/* --- Test-send: search user & send a specific follow-up --- */

let _testSendStep = null;
let _testSendTimer = null;

function openTestSend(step) {
  _testSendStep = step;
  const stepLabels = {1: 'Сообщение 1', 2: 'Сообщение 2', 3: 'Сообщение 3'};
  const body = `
    <div class="form-group">
      <label class="form-label">Поиск пользователя (имя или @username)</label>
      <input class="form-input" id="fu-test-search" placeholder="Введите имя или username..." oninput="onTestSendSearch()">
    </div>
    <div id="fu-test-results" style="max-height:250px; overflow:auto"></div>
    <div id="fu-test-selected" style="margin-top:12px"></div>`;
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Закрыть</button>`;
  openModal('Тестовая отправка — ' + (stepLabels[step] || 'Шаг ' + step), body, footer);
}

function onTestSendSearch() {
  clearTimeout(_testSendTimer);
  _testSendTimer = setTimeout(async () => {
    const q = document.getElementById('fu-test-search').value.trim();
    const container = document.getElementById('fu-test-results');
    if (q.length < 2) { container.innerHTML = '<span class="text-muted" style="font-size:13px">Введите минимум 2 символа</span>'; return; }
    try {
      const users = await api('GET', '/admin/users?q=' + encodeURIComponent(q));
      if (!users.length) { container.innerHTML = '<span class="text-muted" style="font-size:13px">Ничего не найдено</span>'; return; }
      container.innerHTML = users.slice(0, 20).map(u => `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--border, #eee)">
          <div>
            <b>${escHtml(u.first_name || '')}</b>
            ${u.username ? '<span class="text-muted">@' + escHtml(u.username) + '</span>' : ''}
            <span class="text-muted" style="font-size:12px">ID: ${u.id}, TG: ${u.telegram_id || '—'}</span>
          </div>
          <button class="btn btn-sm btn-primary" onclick="execTestSend(${u.id}, this)">Отправить</button>
        </div>`).join('');
    } catch (err) { container.innerHTML = '<span class="text-muted">' + escHtml(err.message) + '</span>'; }
  }, 350);
}

async function execTestSend(userId, btn) {
  btn.disabled = true;
  btn.textContent = '...';
  try {
    await api('POST', '/admin/content/followups/test-send', { user_id: userId, step: _testSendStep });
    btn.textContent = '✓';
    btn.classList.remove('btn-primary');
    btn.classList.add('btn-ghost');
    showToast('Отправлено');
  } catch (err) {
    btn.textContent = 'Ошибка';
    showToast(err.message, 'error');
    setTimeout(() => { btn.textContent = 'Отправить'; btn.disabled = false; }, 2000);
  }
}

window.loadFollowups = loadFollowups;
window.editFollowup = editFollowup;
window.saveFollowup = saveFollowup;
window.enrollExistingUsers = enrollExistingUsers;
window.confirmEnrollExisting = confirmEnrollExisting;
window.openTestSend = openTestSend;
window.onTestSendSearch = onTestSendSearch;
window.execTestSend = execTestSend;
