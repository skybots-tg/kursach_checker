/* Products — full CRUD */

registerPage('products', loadProducts);

async function loadProducts() {
  const page = $('page-products');
  page.innerHTML = loadingHtml();
  try {
    const list = await api('GET', '/admin/products');
    renderProducts(list);
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderProducts(list) {
  $('page-products').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Продукты и цены</h1>
        <p class="page-subtitle">Управление тарифами и кредитами</p>
      </div>
      <button class="btn btn-primary" onclick="showProductModal()">
        ${iconSvg('plus', 16)} Добавить продукт
      </button>
    </div>
    ${list.length ? productTable(list) : emptyHtml('Нет продуктов', 'Создайте первый продукт')}`;
}

function productTable(list) {
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th>
          <th>Название</th>
          <th>Цена</th>
          <th>Валюта</th>
          <th>Кредитов</th>
          <th>Статус</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(p => `<tr>
            <td>${p.id}</td>
            <td><strong>${escHtml(p.name)}</strong></td>
            <td>${p.price}</td>
            <td>${escHtml(p.currency || 'RUB')}</td>
            <td><span class="badge badge-primary">${p.credits_amount}</span></td>
            <td>${p.active ? '<span class="badge badge-success">Активен</span>' : '<span class="badge badge-gray">Неактивен</span>'}</td>
            <td class="actions-cell">
              <button class="btn btn-icon btn-sm" title="Редактировать" onclick='showProductModal(${JSON.stringify(p)})'>
                ${iconSvg('edit', 15)}
              </button>
              <button class="btn btn-icon btn-sm" title="Удалить" onclick="deleteProduct(${p.id})">
                ${iconSvg('trash', 15)}
              </button>
            </td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function showProductModal(p) {
  const isEdit = !!p;
  const body = `
    <div class="form-group">
      <label class="form-label">Название</label>
      <input class="form-input" id="prod-name" value="${isEdit ? escHtml(p.name) : ''}">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="form-label">Цена</label>
        <input class="form-input" type="number" id="prod-price" value="${isEdit ? p.price : ''}" min="0" step="1">
      </div>
      <div class="form-group">
        <label class="form-label">Валюта</label>
        <input class="form-input" id="prod-currency" value="${isEdit ? escHtml(p.currency || 'RUB') : 'RUB'}">
      </div>
    </div>
    <div class="form-group">
      <label class="form-label">Кредитов за покупку</label>
      <input class="form-input" type="number" id="prod-credits" value="${isEdit ? p.credits_amount : ''}" min="1">
    </div>
    <div class="toggle" style="border:none;padding-top:4px">
      <div class="toggle-info"><div class="toggle-title">Активен</div></div>
      <label class="switch">
        <input type="checkbox" id="prod-active" ${!isEdit || p.active ? 'checked' : ''}>
        <span class="slider"></span>
      </label>
    </div>`;
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="saveProduct(${isEdit ? p.id : 'null'})">${isEdit ? 'Сохранить' : 'Создать'}</button>`;
  openModal(isEdit ? 'Редактировать продукт' : 'Новый продукт', body, footer);
}

async function saveProduct(id) {
  const data = {
    name: getVal('prod-name').trim(),
    price: parseFloat(getVal('prod-price')) || 0,
    currency: getVal('prod-currency').trim() || 'RUB',
    credits_amount: parseInt(getVal('prod-credits')) || 1,
    active: isChecked('prod-active'),
  };
  if (!data.name) { toast('Введите название', 'error'); return; }
  try {
    if (id) await api('PUT', `/admin/products/${id}`, data);
    else await api('POST', '/admin/products', data);
    closeModal();
    toast(id ? 'Продукт обновлён' : 'Продукт создан', 'success');
    loadProducts();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

async function deleteProduct(id) {
  if (!confirm('Удалить продукт #' + id + '?')) return;
  try {
    await api('DELETE', `/admin/products/${id}`);
    toast('Продукт удалён', 'success');
    loadProducts();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

window.showProductModal = showProductModal;
window.saveProduct = saveProduct;
window.deleteProduct = deleteProduct;
