/* Orders — list, detail, status update */

registerPage('orders', loadOrders);

async function loadOrders() {
  const page = $('page-orders');
  page.innerHTML = loadingHtml();
  try {
    const list = await api('GET', '/admin/orders');
    renderOrders(list);
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderOrders(list) {
  $('page-orders').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Заказы и платежи</h1>
        <p class="page-subtitle">Все заказы пользователей (${list.length})</p>
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
    ${list.length ? ordersTable(list) : emptyHtml('Нет заказов', 'Пока нет ни одного заказа')}`;
}

function ordersTable(list) {
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th>
          <th>Пользователь</th>
          <th>Продукт</th>
          <th>Сумма</th>
          <th>Статус</th>
          <th>Дата</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(o => `<tr>
            <td>${o.id}</td>
            <td>${o.user ? `@${escHtml(o.user.username || '')}` : '—'}</td>
            <td>${o.product ? escHtml(o.product.name) : '—'}</td>
            <td><strong>${o.amount ?? '—'}</strong></td>
            <td>${statusBadge(o.status)}</td>
            <td style="white-space:nowrap">${formatDate(o.created_at)}</td>
            <td class="actions-cell">
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
  const page = $('page-orders');
  const tableArea = page.querySelector('.card') || page;
  try {
    const url = status ? `/admin/orders?status=${status}` : '/admin/orders';
    const list = await api('GET', url);
    renderOrders(list);
    if (status) setVal('orders-filter', status);
  } catch (err) {
    toast('Ошибка фильтрации: ' + err.message, 'error');
  }
}

async function viewOrder(id) {
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
          <div>@${escHtml(u.username || '—')} (TG: ${u.telegram_id || '—'})</div>
        </div>
        <div>
          <div class="form-label">Продукт</div>
          <div>${escHtml(p.name || '—')}</div>
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
  } catch (err) {
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

window.filterOrders = filterOrders;
window.viewOrder = viewOrder;
window.updateOrderStatus = updateOrderStatus;
