/* Universities — list + create */

registerPage('universities', loadUniversities);

async function loadUniversities() {
  const page = $('page-universities');
  page.innerHTML = loadingHtml();
  try {
    const list = await api('GET', '/universities');
    renderUniversities(list);
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderUniversities(list) {
  $('page-universities').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">ВУЗы и программы</h1>
        <p class="page-subtitle">Управление списком университетов</p>
      </div>
      <button class="btn btn-primary" onclick="showAddUniversity()">
        ${iconSvg('plus', 16)} Добавить ВУЗ
      </button>
    </div>
    ${list.length ? universityTable(list) : emptyHtml('Нет университетов', 'Добавьте первый ВУЗ')}`;
}

function universityTable(list) {
  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th>
          <th>Название</th>
          <th>Статус</th>
        </tr></thead>
        <tbody>
          ${list.map(u => `<tr>
            <td>${u.id}</td>
            <td><strong>${escHtml(u.name)}</strong></td>
            <td>${u.active ? '<span class="badge badge-success">Активен</span>' : '<span class="badge badge-gray">Неактивен</span>'}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function showAddUniversity() {
  const body = `
    <div class="form-group">
      <label class="form-label">Название ВУЗа</label>
      <input class="form-input" id="uni-name" placeholder="Например: МГУ им. Ломоносова">
    </div>`;
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="createUniversity()">Создать</button>`;
  openModal('Новый ВУЗ', body, footer);
}

async function createUniversity() {
  const name = getVal('uni-name').trim();
  if (!name) { toast('Введите название', 'error'); return; }
  try {
    await api('POST', '/universities', { name, active: true });
    closeModal();
    toast('ВУЗ создан', 'success');
    loadUniversities();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

window.showAddUniversity = showAddUniversity;
window.createUniversity = createUniversity;
