/* Users — list, search, detail with related entities, edit, credits */

registerPage('users', loadUsers);

let _usersData = [];
let _usersPage = 1;
let _userDetailData = null;
let _userDetailTab = 'orders';

async function loadUsers(query) {
  const page = $('page-users');
  page.innerHTML = loadingHtml();
  try {
    const url = query ? `/admin/users?q=${encodeURIComponent(query)}` : '/admin/users';
    _usersData = await api('GET', url);
    _usersPage = 1;
    renderUsers(query);
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderUsers(query) {
  $('page-users').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Пользователи</h1>
        <p class="page-subtitle">Все зарегистрированные пользователи (${_usersData.length})</p>
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
    <div id="users-table-area"></div>`;
  renderUsersTable();
}

function renderUsersTable() {
  const paged = paginate(_usersData, _usersPage);
  _usersPage = paged.page;
  const area = $('users-table-area');
  if (!area) return;
  area.innerHTML = paged.items.length
    ? usersTable(paged.items) + paginationHtml(paged, 'usersGoPage')
    : emptyHtml('Пользователи не найдены', 'Попробуйте другой запрос');
}

function usersGoPage(p) { _usersPage = p; renderUsersTable(); }

function usersTable(list) {
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th><th>Telegram ID</th><th>Имя</th>
          <th>Username</th><th>Кредиты</th><th>Регистрация</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(u => `<tr>
            <td data-label="ID">${u.id}</td>
            <td data-label="Telegram ID"><code>${u.telegram_id}</code></td>
            <td data-label="Имя">${escHtml(u.first_name || '—')}</td>
            <td data-label="Username">${u.username ? `@${escHtml(u.username)}` : '—'}</td>
            <td data-label="Кредиты"><span class="badge badge-primary">${u.credits_available ?? 0}</span></td>
            <td data-label="Регистрация" style="white-space:nowrap">${formatDate(u.created_at)}</td>
            <td data-label="" class="actions-cell">
              <button class="btn btn-icon btn-sm" title="Подробнее" onclick="viewUserDetail(${u.id})">
                ${iconSvg('eye', 15)}
              </button>
              <button class="btn btn-icon btn-sm" title="Кредиты" onclick="showCreditsModal(${u.id}, ${u.credits_available ?? 0})">
                ${iconSvg('coins', 15)}
              </button>
              <button class="btn btn-icon btn-sm" title="Удалить полностью"
                onclick="confirmDeleteUser(${u.id})">
                ${iconSvg('trash', 15)}
              </button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function searchUsers() {
  loadUsers(getVal('users-search').trim() || undefined);
}

/* ---- User Detail Page ---- */

async function viewUserDetail(id) {
  const hash = '#users/' + id;
  if (location.hash !== hash) history.replaceState(null, '', hash);
  const page = $('page-users');
  page.innerHTML = loadingHtml();
  try {
    const [user, allOrders, allChecks] = await Promise.all([
      api('GET', `/admin/users/${id}`),
      api('GET', '/admin/orders'),
      api('GET', '/admin/checks'),
    ]);
    const orders = allOrders.filter(o => (o.user_id ?? o.user?.id) === id);
    const checks = allChecks.filter(c => (c.user_id ?? c.user?.id) === id);
    _userDetailData = { user, orders, checks };
    _userDetailTab = 'orders';
    renderUserDetail();
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderUserDetail() {
  const { user: u, orders, checks } = _userDetailData;
  const tab = _userDetailTab;
  const paidTotal = orders
    .filter(o => o.status === 'paid')
    .reduce((s, o) => s + (o.amount || 0), 0);

  $('page-users').innerHTML = `
    <div class="page-header">
      <div>
        <button class="btn btn-ghost btn-sm" onclick="backToUserList()" style="margin-bottom:8px">
          ${iconSvg('arrowLeft', 14)} Назад к списку
        </button>
        <h1 class="page-title">${u.username ? '@' + escHtml(u.username) : escHtml(u.first_name || 'Пользователь #' + u.id)}</h1>
        <p class="page-subtitle">ID ${u.id} · Telegram ${u.telegram_id}</p>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-secondary btn-sm" onclick="showCreditsModal(${u.id}, ${u.credits_available ?? 0})">
          ${iconSvg('coins', 14)} Кредиты
        </button>
        <button class="btn btn-ghost btn-sm" onclick="showEditUserModal(${u.id})">
          ${iconSvg('edit', 14)} Редактировать
        </button>
        <button class="btn btn-danger btn-sm"
          onclick="confirmDeleteUser(${u.id})">
          ${iconSvg('trash', 14)} Удалить
        </button>
      </div>
    </div>

    <div class="card" style="margin-bottom:20px">
      <div class="detail-grid">
        <div><div class="detail-label">Telegram ID</div><div class="detail-value"><code>${u.telegram_id}</code></div></div>
        <div><div class="detail-label">Имя</div><div class="detail-value">${escHtml(u.first_name || '—')}</div></div>
        <div><div class="detail-label">Username</div><div class="detail-value">${u.username ? '@' + escHtml(u.username) : '—'}</div></div>
        <div><div class="detail-label">Кредиты</div><div class="detail-value"><span class="badge badge-primary">${u.credits_available ?? 0}</span></div></div>
        <div><div class="detail-label">Регистрация</div><div class="detail-value">${formatDate(u.created_at)}</div></div>
        <div><div class="detail-label">Последний вход</div><div class="detail-value">${formatDate(u.last_login_at)}</div></div>
      </div>
    </div>

    <div class="stats-grid" style="margin-bottom:20px">
      <div class="card stat-card">
        <div class="stat-icon blue">${iconSvg('coins', 20)}</div>
        <div class="stat-val">${orders.length}</div>
        <div class="stat-label">Заказов</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon green">${iconSvg('fileCheck', 20)}</div>
        <div class="stat-val">${checks.length}</div>
        <div class="stat-label">Проверок</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon yellow">${iconSvg('coins', 20)}</div>
        <div class="stat-val">${paidTotal}</div>
        <div class="stat-label">Оплачено</div>
      </div>
    </div>

    <div class="tabs">
      <button class="tab-btn${tab === 'orders' ? ' active' : ''}" onclick="switchUserTab('orders')">Заказы (${orders.length})</button>
      <button class="tab-btn${tab === 'checks' ? ' active' : ''}" onclick="switchUserTab('checks')">Проверки (${checks.length})</button>
    </div>

    ${tab === 'orders' ? userOrdersList(orders) : userChecksList(checks)}`;
}

function switchUserTab(tab) {
  _userDetailTab = tab;
  renderUserDetail();
}

function userOrdersList(orders) {
  if (!orders.length) return emptyHtml('Нет заказов', 'У пользователя пока нет заказов');
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th><th>Продукт</th><th>Сумма</th>
          <th>Статус</th><th>Дата</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${orders.map(o => `<tr>
            <td data-label="ID">${o.id}</td>
            <td data-label="Продукт">${o.product ? entityTag('product', o.product.id, o.product.name) : '—'}</td>
            <td data-label="Сумма"><strong>${o.amount ?? '—'}</strong></td>
            <td data-label="Статус">${statusBadge(o.status)}</td>
            <td data-label="Дата" style="white-space:nowrap">${formatDate(o.created_at)}</td>
            <td data-label="" class="actions-cell">
              <button class="btn btn-icon btn-sm" title="Подробнее" onclick="viewOrder(${o.id})">
                ${iconSvg('eye', 15)}
              </button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function userChecksList(checks) {
  if (!checks.length) return emptyHtml('Нет проверок', 'У пользователя нет загруженных курсовых');
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th><th>ГОСТ</th><th>Статус</th>
          <th>Загружено</th><th>Завершено</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${checks.map(c => `<tr>
            <td data-label="ID">${c.id}</td>
            <td data-label="ГОСТ">${c.gost ? entityTag('gost', c.gost.id, c.gost.name) : '—'}</td>
            <td data-label="Статус">${statusBadge(c.status)}</td>
            <td data-label="Загружено" style="white-space:nowrap">${formatDate(c.created_at)}</td>
            <td data-label="Завершено" style="white-space:nowrap">${formatDate(c.finished_at)}</td>
            <td data-label="" class="actions-cell">
              <button class="btn btn-icon btn-sm" title="Подробнее" onclick="viewCheck(${c.id})">
                ${iconSvg('eye', 15)}
              </button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

/* ---- Edit Modal ---- */

async function showEditUserModal(id) {
  try {
    const u = await api('GET', `/admin/users/${id}`);
    const body = `
      <div class="form-group">
        <label class="form-label">Имя</label>
        <input class="form-input" id="user-edit-name" value="${escHtml(u.first_name || '')}">
      </div>
      <div class="form-group">
        <label class="form-label">Username</label>
        <input class="form-input" id="user-edit-username" value="${escHtml(u.username || '')}">
      </div>`;
    const footer = `
      <button class="btn btn-ghost" onclick="closeModal()">Закрыть</button>
      <button class="btn btn-primary" onclick="updateUser(${id})">Сохранить</button>`;
    openModal('Редактировать пользователя', body, footer);
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
    if (_userDetailData && _userDetailData.user.id === id) viewUserDetail(id);
    else loadUsers();
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
    if (_userDetailData && _userDetailData.user.id === userId) viewUserDetail(userId);
    else loadUsers();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

function backToUserList() {
  _userDetailData = null;
  history.replaceState(null, '', '#users');
  loadUsers();
}

/* ---- Delete user ---- */

function confirmDeleteUser(userId) {
  const u = (_usersData || []).find(x => x.id === userId)
    || (_userDetailData && _userDetailData.user && _userDetailData.user.id === userId
        ? _userDetailData.user : null);
  const rawLabel = u ? (u.username || u.first_name) : null;
  const safeLabel = rawLabel && String(rawLabel).trim() ? String(rawLabel) : ('#' + userId);
  const body = `
    <p>Вы собираетесь <strong>полностью удалить</strong> пользователя
       <strong>${escHtml(safeLabel)}</strong> (ID ${userId}).</p>
    <p>Будут удалены: записи о рефералах (где он инвайтер или приглашённый),
       баланс кредитов и история операций, заказы и платежи Prodamus,
       все проверки и их логи, файлы и аналитика.</p>
    <p style="color:var(--danger,#c53030)"><strong>Действие необратимо.</strong>
       Используйте для удаления тестовых аккаунтов.</p>
    <div class="form-group" style="margin-top:12px">
      <label class="form-label">Чтобы подтвердить, введите <code>УДАЛИТЬ</code>:</label>
      <input class="form-input" id="user-delete-confirm" autocomplete="off" placeholder="УДАЛИТЬ">
    </div>`;
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-danger" onclick="deleteUser(${userId})">Удалить навсегда</button>`;
  openModal('Полное удаление пользователя', body, footer);
}

async function deleteUser(userId) {
  const phrase = (getVal('user-delete-confirm') || '').trim();
  if (phrase !== 'УДАЛИТЬ') {
    toast('Введите слово УДАЛИТЬ для подтверждения', 'error');
    return;
  }
  try {
    await api('DELETE', `/admin/users/${userId}`);
    closeModal();
    toast('Пользователь удалён', 'success');
    if (_userDetailData && _userDetailData.user.id === userId) {
      backToUserList();
    } else {
      loadUsers();
    }
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

registerEntityHandler('users', (sub) => viewUserDetail(parseInt(sub)), true);

window.searchUsers = searchUsers;
window.usersGoPage = usersGoPage;
window.viewUserDetail = viewUserDetail;
window.switchUserTab = switchUserTab;
window.showEditUserModal = showEditUserModal;
window.updateUser = updateUser;
window.showCreditsModal = showCreditsModal;
window.setUserCredits = setUserCredits;
window.backToUserList = backToUserList;
window.confirmDeleteUser = confirmDeleteUser;
window.deleteUser = deleteUser;
