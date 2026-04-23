/* Referrals — referral program stats, list, manage */

registerPage('referrals', loadReferrals);

let _referralsData = [];
let _referralsStats = null;
let _referralsPage = 1;
let _referralsStatus = 'all';
let _referralsQuery = '';

async function loadReferrals() {
  const page = $('page-referrals');
  page.innerHTML = loadingHtml();
  try {
    await refreshReferrals();
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

async function refreshReferrals() {
  const listQuery = new URLSearchParams();
  if (_referralsStatus && _referralsStatus !== 'all') {
    listQuery.set('status', _referralsStatus);
  }
  if (_referralsQuery) {
    listQuery.set('q', _referralsQuery);
  }
  const qs = listQuery.toString();
  const listUrl = qs ? `/admin/referrals?${qs}` : '/admin/referrals';

  const [data, stats] = await Promise.all([
    api('GET', listUrl),
    api('GET', '/admin/referrals/stats'),
  ]);
  _referralsData = data;
  _referralsStats = stats;
  renderReferrals();
}

function renderReferrals() {
  const stats = _referralsStats || {};
  const q = _referralsQuery;

  $('page-referrals').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Реферальная программа</h1>
        <p class="page-subtitle">
          Приглашения, выданные бонусы и топ-инвайтеры.
          За каждого друга, зашедшего в бота по реф-ссылке, инвайтер
          сразу получает +${stats.bonus_per_referral ?? '?'} бесплатное пользование.
        </p>
      </div>
    </div>

    ${referralsStatsGrid(stats)}

    <div class="toolbar" style="margin-top:16px">
      <input class="search-input" id="ref-search"
        placeholder="Поиск по имени или username…"
        value="${q ? escHtml(q) : ''}"
        onkeydown="if(event.key==='Enter')searchReferrals()">
      <button class="btn btn-secondary btn-sm" onclick="searchReferrals()">
        ${iconSvg('search', 14)} Найти
      </button>
      <div class="tabs" style="margin-left:auto">
        <button class="tab-btn${_referralsStatus === 'all' ? ' active' : ''}" onclick="filterReferrals('all')">
          Все (${stats.total ?? 0})
        </button>
        <button class="tab-btn${_referralsStatus === 'pending' ? ' active' : ''}" onclick="filterReferrals('pending')">
          Ожидают (${stats.pending ?? 0})
        </button>
        <button class="tab-btn${_referralsStatus === 'granted' ? ' active' : ''}" onclick="filterReferrals('granted')">
          Выдан (${stats.granted ?? 0})
        </button>
      </div>
    </div>

    <div id="referrals-table-area"></div>

    ${topInvitersCard(stats.top_inviters || [])}
  `;

  renderReferralsTable();
}

function referralsStatsGrid(stats) {
  return `<div class="stats-grid">
    <div class="card stat-card">
      <div class="stat-icon blue">${iconSvg('coins', 20)}</div>
      <div class="stat-val">${stats.total ?? 0}</div>
      <div class="stat-label">Всего приглашений</div>
    </div>
    <div class="card stat-card">
      <div class="stat-icon green">${iconSvg('fileCheck', 20)}</div>
      <div class="stat-val">${stats.granted ?? 0}</div>
      <div class="stat-label">Выдано бонусов</div>
    </div>
    <div class="card stat-card">
      <div class="stat-icon yellow">${iconSvg('refresh', 20)}</div>
      <div class="stat-val">${stats.pending ?? 0}</div>
      <div class="stat-label">Без выданного бонуса</div>
    </div>
    <div class="card stat-card">
      <div class="stat-icon blue">${iconSvg('coins', 20)}</div>
      <div class="stat-val">${stats.bonuses_total ?? 0}</div>
      <div class="stat-label">Всего начислено кредитов</div>
    </div>
  </div>`;
}

function renderReferralsTable() {
  const paged = paginate(_referralsData, _referralsPage);
  _referralsPage = paged.page;
  const area = $('referrals-table-area');
  if (!area) return;
  area.innerHTML = paged.items.length
    ? referralsTable(paged.items) + paginationHtml(paged, 'referralsGoPage')
    : emptyHtml('Записей нет', 'Пока никто не привёл друга по реф-ссылке');
}

function referralsGoPage(p) {
  _referralsPage = p;
  renderReferralsTable();
}

function userTag(user) {
  if (!user) return '—';
  const label = user.username
    ? '@' + user.username
    : (user.first_name || ('#' + user.id));
  return entityTag('user', user.id, label);
}

function referralsTable(list) {
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th>
          <th>Инвайтер</th>
          <th>Приглашённый</th>
          <th>Статус</th>
          <th>Бонус</th>
          <th>Создано</th>
          <th>Бонус выдан</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(r => referralRow(r)).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function referralRow(r) {
  const statusCls = r.status === 'granted' ? 'success' : 'warn';
  const statusTxt = r.status === 'granted' ? 'Выдан' : 'Ожидает';
  return `<tr>
    <td data-label="ID">${r.id}</td>
    <td data-label="Инвайтер">${userTag(r.inviter)}</td>
    <td data-label="Приглашённый">${userTag(r.invited)}</td>
    <td data-label="Статус"><span class="badge badge-${statusCls}">${statusTxt}</span></td>
    <td data-label="Бонус">${r.bonus_amount ? ('+' + r.bonus_amount) : '—'}</td>
    <td data-label="Создано" style="white-space:nowrap">${formatDate(r.created_at)}</td>
    <td data-label="Бонус выдан" style="white-space:nowrap">${formatDate(r.bonus_granted_at)}</td>
    <td data-label="" class="actions-cell">
      ${r.status === 'pending'
        ? `<button class="btn btn-primary btn-sm" onclick="grantReferralBonus(${r.id})" title="Начислить бонус вручную">
             ${iconSvg('coins', 14)} Выдать
           </button>`
        : ''}
      <button class="btn btn-icon btn-sm" title="Удалить" onclick="deleteReferral(${r.id})">
        ${iconSvg('trash', 15)}
      </button>
    </td>
  </tr>`;
}

function topInvitersCard(top) {
  if (!top.length) return '';
  return `<div class="card" style="margin-top:20px">
    <h3 style="margin:0 0 12px 0">Топ-инвайтеры</h3>
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>#</th><th>Пользователь</th>
          <th>Приглашено</th><th>Начислено кредитов</th>
        </tr></thead>
        <tbody>
          ${top.map((t, i) => `<tr>
            <td data-label="#">${i + 1}</td>
            <td data-label="Пользователь">${userTag(t.user)}</td>
            <td data-label="Приглашено"><strong>${t.invited_count}</strong></td>
            <td data-label="Начислено кредитов">${t.bonus_total}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function searchReferrals() {
  _referralsQuery = (getVal('ref-search') || '').trim();
  _referralsPage = 1;
  refreshReferrals().catch(err => toast('Ошибка: ' + err.message, 'error'));
}

function filterReferrals(status) {
  _referralsStatus = status;
  _referralsPage = 1;
  refreshReferrals().catch(err => toast('Ошибка: ' + err.message, 'error'));
}

async function grantReferralBonus(id) {
  const body = `
    <p>Начислить реферальный бонус инвайтеру вручную? Укажите количество кредитов (по умолчанию — стандартный бонус).</p>
    <div class="form-group">
      <label class="form-label">Количество кредитов</label>
      <input class="form-input" type="number" id="ref-grant-amount"
        value="${_referralsStats?.bonus_per_referral ?? 1}" min="1">
    </div>`;
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="confirmGrantReferral(${id})">Начислить</button>`;
  openModal('Ручная выдача бонуса', body, footer);
}

async function confirmGrantReferral(id) {
  const val = parseInt(getVal('ref-grant-amount'), 10);
  if (isNaN(val) || val <= 0) {
    toast('Укажите корректное количество кредитов', 'error');
    return;
  }
  try {
    await api('POST', `/admin/referrals/${id}/grant`, { bonus_amount: val });
    closeModal();
    toast('Бонус начислен', 'success');
    await refreshReferrals();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

async function deleteReferral(id) {
  if (!confirm('Удалить запись о реферале? Начисленный бонус при этом НЕ откатывается.')) return;
  try {
    await api('DELETE', `/admin/referrals/${id}`);
    toast('Запись удалена', 'success');
    await refreshReferrals();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

window.searchReferrals = searchReferrals;
window.filterReferrals = filterReferrals;
window.referralsGoPage = referralsGoPage;
window.grantReferralBonus = grantReferralBonus;
window.confirmGrantReferral = confirmGrantReferral;
window.deleteReferral = deleteReferral;
