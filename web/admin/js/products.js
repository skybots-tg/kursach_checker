/* Products — full CRUD, pagination */

registerPage('products', loadProducts);

let _productsData = [];
let _productsPage = 1;

async function loadProducts() {
  const page = $('page-products');
  page.innerHTML = loadingHtml();
  try {
    _productsData = await api('GET', '/admin/products');
    _productsPage = 1;
    renderProducts();
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderProducts() {
  $('page-products').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Продукты и цены</h1>
        <p class="page-subtitle">Управление тарифами и кредитами (${_productsData.length})</p>
      </div>
      <button class="btn btn-primary" onclick="showProductModal()">
        ${iconSvg('plus', 16)} Добавить продукт
      </button>
    </div>
    <div id="products-table-area"></div>`;
  renderProductsTable();
}

function renderProductsTable() {
  const paged = paginate(_productsData, _productsPage);
  _productsPage = paged.page;
  const area = $('products-table-area');
  if (!area) return;
  area.innerHTML = paged.items.length
    ? productTable(paged.items) + paginationHtml(paged, 'productsGoPage')
    : emptyHtml('Нет продуктов', 'Создайте первый продукт');
}

function productsGoPage(p) { _productsPage = p; renderProductsTable(); }

function productTable(list) {
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th><th>Название</th><th>Цена</th>
          <th>Валюта</th><th>Кредитов</th><th>Статус</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(p => `<tr>
            <td data-label="ID">${p.id}</td>
            <td data-label="Название"><strong>${escHtml(p.name)}</strong></td>
            <td data-label="Цена">${p.price}</td>
            <td data-label="Валюта">${escHtml(p.currency || 'RUB')}</td>
            <td data-label="Кредитов"><span class="badge badge-primary">${p.credits_amount}</span></td>
            <td data-label="Статус">${p.active ? '<span class="badge badge-success">Активен</span>' : '<span class="badge badge-gray">Неактивен</span>'}</td>
            <td data-label="" class="actions-cell">
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

window.productsGoPage = productsGoPage;
window.showProductModal = showProductModal;
window.saveProduct = saveProduct;
window.deleteProduct = deleteProduct;
