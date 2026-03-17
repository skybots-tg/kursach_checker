/* GOSTs — list + create */

registerPage('gosts', loadGosts);

async function loadGosts() {
  const page = $('page-gosts');
  page.innerHTML = loadingHtml();
  try {
    const list = await api('GET', '/gosts');
    renderGosts(list);
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderGosts(list) {
  $('page-gosts').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">ГОСТы / стили</h1>
        <p class="page-subtitle">Стандарты оформления документов</p>
      </div>
      <button class="btn btn-primary" onclick="showAddGost()">
        ${iconSvg('plus', 16)} Добавить ГОСТ
      </button>
    </div>
    ${list.length ? gostTable(list) : emptyHtml('Нет ГОСТов', 'Добавьте первый стандарт')}`;
}

function gostTable(list) {
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th>
          <th>Название</th>
          <th>Описание</th>
          <th>Статус</th>
        </tr></thead>
        <tbody>
          ${list.map(g => `<tr>
            <td>${g.id}</td>
            <td><strong>${escHtml(g.name)}</strong></td>
            <td style="color:var(--text-muted)">${escHtml(g.description || '—')}</td>
            <td>${g.active ? '<span class="badge badge-success">Активен</span>' : '<span class="badge badge-gray">Неактивен</span>'}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function showAddGost() {
  const body = `
    <div class="form-group">
      <label class="form-label">Название ГОСТа</label>
      <input class="form-input" id="gost-name" placeholder="Например: ГОСТ Р 7.0.11-2011">
    </div>
    <div class="form-group">
      <label class="form-label">Описание</label>
      <textarea class="form-textarea" id="gost-desc" rows="3" placeholder="Краткое описание стандарта"></textarea>
    </div>`;
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="createGost()">Создать</button>`;
  openModal('Новый ГОСТ', body, footer);
}

async function createGost() {
  const name = getVal('gost-name').trim();
  if (!name) { toast('Введите название', 'error'); return; }
  try {
    await api('POST', '/gosts', {
      name,
      description: getVal('gost-desc').trim() || null,
      active: true,
    });
    closeModal();
    toast('ГОСТ создан', 'success');
    loadGosts();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

window.showAddGost = showAddGost;
window.createGost = createGost;
