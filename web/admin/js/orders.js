/* Orders — list with entity tags, pagination, detail, status update */

registerPage('orders', loadOrders);

let _ordersData = [];
let _ordersPage = 1;

async function loadOrders() {
  const page = $('page-orders');
  page.innerHTML = loadingHtml();
  try {
    _ordersData = await api('GET', '/admin/orders');
    _ordersPage = 1;
    renderOrders();
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderOrders() {
  $('page-orders').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Заказы и платежи</h1>
        <p class="page-subtitle">Все заказы пользователей (${_ordersData.length})</p>
      </div>
    </div>
    <div class="toolbar">
      <select class="filter-select" id="orders-filter" onchange="filterOrders()">
        <option value="">Все статусы</option>
        <option value="created">Создан</option>
        <option value="paid">Оплачен</option>
        <option value="failed">Ошибка</option>
        <option value="cancelled">Отменён</option>
      </select>
      <button class="btn btn-secondary btn-sm" onclick="loadOrders()">
        ${iconSvg('refresh', 14)} Обновить
      </button>
    </div>
    <div id="orders-table-area"></div>`;
  renderOrdersTable();
}

function renderOrdersTable() {
  const paged = paginate(_ordersData, _ordersPage);
  _ordersPage = paged.page;
  const area = $('orders-table-area');
  if (!area) return;
  area.innerHTML = paged.items.length
    ? ordersTable(paged.items) + paginationHtml(paged, 'ordersGoPage')
    : emptyHtml('Нет заказов', 'Пока нет ни одного заказа');
}

function ordersGoPage(p) { _ordersPage = p; renderOrdersTable(); }

function ordersTable(list) {
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th><th>Пользователь</th><th>Продукт</th>
          <th>Сумма</th><th>Статус</th><th>Дата</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(o => `<tr>
            <td data-label="ID">${o.id}</td>
            <td data-label="Пользователь">${o.user
              ? entityTag('user', o.user_id || o.user.id, o.user.username ? '@' + o.user.username : o.user.first_name || 'user')
              : '—'}</td>
            <td data-label="Продукт">${o.product
              ? entityTag('product', o.product.id, o.product.name)
              : '—'}</td>
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

async function filterOrders() {
  const status = getVal('orders-filter');
  try {
    const url = status ? `/admin/orders?status=${status}` : '/admin/orders';
    _ordersData = await api('GET', url);
    _ordersPage = 1;
    renderOrders();
    if (status) setVal('orders-filter', status);
  } catch (err) {
    toast('Ошибка фильтрации: ' + err.message, 'error');
  }
}

async function viewOrder(id) {
  history.replaceState(null, '', '#orders/' + id);
  try {
    const data = await api('GET', `/admin/orders/${id}`);
    const o = data.order || {};
    const u = data.user || {};
    const p = data.product || {};
    const logs = data.payment_logs || [];

    const body = `
      <div style="display:flex;flex-direction:column;gap:16px">
        <div>
          <div class="form-label">Статус</div>
          <div>${statusBadge(o.status)}</div>
        </div>
        <div class="form-row">
          <div><div class="form-label">Сумма</div><div>${o.amount ?? '—'}</div></div>
          <div><div class="form-label">Дата оплаты</div><div>${formatDate(o.paid_at)}</div></div>
        </div>
        <div>
          <div class="form-label">Пользователь</div>
          <div>${u.id ? entityTag('user', u.id, u.username ? '@' + u.username : u.first_name || '#' + u.id) : '—'}</div>
        </div>
        <div>
          <div class="form-label">Продукт</div>
          <div>${p.id ? entityTag('product', p.id, p.name) : escHtml(p.name || '—')}</div>
        </div>
        ${logs.length ? `
          <div>
            <div class="form-label" style="margin-bottom:8px">Платёжные логи</div>
            ${logs.map(l => `<div class="event-item" style="padding:8px 0;border-bottom:1px solid var(--border)">
              <div class="event-dot" style="background:${l.status === 'success' ? 'var(--success)' : 'var(--warn)'}"></div>
              <div class="event-text">${escHtml(l.status)} ${l.invoice_id ? '— ' + escHtml(l.invoice_id) : ''}</div>
              <span class="event-time">${formatDate(l.created_at)}</span>
            </div>`).join('')}
          </div>` : ''}
        <div class="form-group">
          <label class="form-label">Изменить статус</label>
          <select class="form-select" id="order-new-status">
            <option value="created" ${o.status === 'created' ? 'selected' : ''}>Создан</option>
            <option value="paid" ${o.status === 'paid' ? 'selected' : ''}>Оплачен</option>
            <option value="failed" ${o.status === 'failed' ? 'selected' : ''}>Ошибка</option>
            <option value="cancelled" ${o.status === 'cancelled' ? 'selected' : ''}>Отменён</option>
          </select>
        </div>
      </div>`;
    const footer = `
      <button class="btn btn-ghost" onclick="closeModal()">Закрыть</button>
      <button class="btn btn-primary" onclick="updateOrderStatus(${id})">Обновить статус</button>`;
    openModal(`Заказ #${id}`, body, footer);
    window._modalEntityHash = true;
  } catch (err) {
    history.replaceState(null, '', '#orders');
    toast('Ошибка: ' + err.message, 'error');
  }
}

async function updateOrderStatus(id) {
  const status = getVal('order-new-status');
  try {
    await api('PUT', `/admin/orders/${id}/status`, { status });
    closeModal();
    toast('Статус обновлён', 'success');
    loadOrders();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

registerEntityHandler('orders', (sub) => viewOrder(parseInt(sub)));

window.ordersGoPage = ordersGoPage;
window.filterOrders = filterOrders;
window.viewOrder = viewOrder;
window.updateOrderStatus = updateOrderStatus;
