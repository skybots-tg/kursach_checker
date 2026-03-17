/* Users — list, search, detail, edit, credits */

registerPage('users', loadUsers);

async function loadUsers(query) {
  const page = $('page-users');
  page.innerHTML = loadingHtml();
  try {
    const url = query ? `/admin/users?q=${encodeURIComponent(query)}` : '/admin/users';
    const list = await api('GET', url);
    renderUsers(list, query);
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderUsers(list, query) {
  $('page-users').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Пользователи</h1>
        <p class="page-subtitle">Все зарегистрированные пользователи (${list.length})</p>
      </div>
    </div>
    <div class="toolbar">
      <input class="search-input" id="users-search" placeholder="Поиск по имени или username…"
        value="${query ? escHtml(query) : ''}"
        onkeydown="if(event.key==='Enter')searchUsers()">
      <button class="btn btn-secondary btn-sm" onclick="searchUsers()">
        ${iconSvg('search', 14)} Найти
      </button>
    </div>
    ${list.length ? usersTable(list) : emptyHtml('Пользователи не найдены', query ? 'Попробуйте другой запрос' : 'Пока нет пользователей')}`;
}

function usersTable(list) {
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th>
          <th>Telegram ID</th>
          <th>Имя</th>
          <th>Username</th>
          <th>Кредиты</th>
          <th>Регистрация</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(u => `<tr>
            <td>${u.id}</td>
            <td><code>${u.telegram_id}</code></td>
            <td>${escHtml(u.first_name || '—')}</td>
            <td>${u.username ? `@${escHtml(u.username)}` : '—'}</td>
            <td><span class="badge badge-primary">${u.credits_available ?? 0}</span></td>
            <td style="white-space:nowrap">${formatDate(u.created_at)}</td>
            <td class="actions-cell">
              <button class="btn btn-icon btn-sm" title="Подробнее" onclick="viewUser(${u.id})">
                ${iconSvg('eye', 15)}
              </button>
              <button class="btn btn-icon btn-sm" title="Кредиты" onclick="showCreditsModal(${u.id}, ${u.credits_available ?? 0})">
                ${iconSvg('coins', 15)}
              </button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function searchUsers() {
  const q = getVal('users-search').trim();
  loadUsers(q || undefined);
}

async function viewUser(id) {
  try {
    const u = await api('GET', `/admin/users/${id}`);
    const body = `
      <div style="display:flex;flex-direction:column;gap:14px">
        <div class="form-row">
          <div><div class="form-label">ID</div>${u.id}</div>
          <div><div class="form-label">Telegram ID</div><code>${u.telegram_id}</code></div>
        </div>
        <div class="form-row">
          <div><div class="form-label">Имя</div>${escHtml(u.first_name || '—')}</div>
          <div><div class="form-label">Username</div>${u.username ? '@' + escHtml(u.username) : '—'}</div>
        </div>
        <div class="form-row">
          <div><div class="form-label">Кредиты</div><span class="badge badge-primary">${u.credits_available ?? 0}</span></div>
          <div><div class="form-label">Последний вход</div>${formatDate(u.last_login_at)}</div>
        </div>
        <div><div class="form-label">Регистрация</div>${formatDate(u.created_at)}</div>
        <div class="section-sep"></div>
        <div class="form-group">
          <label class="form-label">Имя (редактировать)</label>
          <input class="form-input" id="user-edit-name" value="${escHtml(u.first_name || '')}">
        </div>
        <div class="form-group">
          <label class="form-label">Username (редактировать)</label>
          <input class="form-input" id="user-edit-username" value="${escHtml(u.username || '')}">
        </div>
      </div>`;
    const footer = `
      <button class="btn btn-ghost" onclick="closeModal()">Закрыть</button>
      <button class="btn btn-primary" onclick="updateUser(${id})">Сохранить</button>`;
    openModal(`Пользователь #${id}`, body, footer);
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

async function updateUser(id) {
  try {
    await api('PUT', `/admin/users/${id}`, {
      first_name: getVal('user-edit-name').trim() || null,
      username: getVal('user-edit-username').trim() || null,
    });
    closeModal();
    toast('Пользователь обновлён', 'success');
    loadUsers();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

function showCreditsModal(userId, current) {
  const body = `
    <div class="form-group">
      <label class="form-label">Текущий баланс: <strong>${current}</strong></label>
      <input class="form-input" type="number" id="user-credits-val" value="${current}" min="0">
      <div class="form-hint">Введите новое количество кредитов</div>
    </div>`;
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="setUserCredits(${userId})">Установить</button>`;
  openModal('Управление кредитами', body, footer);
}

async function setUserCredits(userId) {
  const val = parseInt(getVal('user-credits-val'));
  if (isNaN(val) || val < 0) { toast('Введите корректное значение', 'error'); return; }
  try {
    await api('PUT', `/admin/users/${userId}/credits`, { credits_available: val });
    closeModal();
    toast('Кредиты обновлены', 'success');
    loadUsers();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

window.searchUsers = searchUsers;
window.viewUser = viewUser;
window.updateUser = updateUser;
window.showCreditsModal = showCreditsModal;
window.setUserCredits = setUserCredits;
