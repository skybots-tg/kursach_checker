/* Templates — list, create, publish, entity tags, pagination */

registerPage('templates', loadTemplates);

let _universities = [];
let _gosts = [];
let _templatesData = [];
let _templatesPage = 1;

async function loadTemplates() {
  const page = $('page-templates');
  page.innerHTML = loadingHtml();
  try {
    const [list, unis, gosts] = await Promise.all([
      api('GET', '/templates'),
      api('GET', '/universities'),
      api('GET', '/gosts'),
    ]);
    _universities = unis;
    _gosts = gosts;
    _templatesData = list;
    _templatesPage = 1;
    renderTemplates();
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderTemplates() {
  $('page-templates').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Шаблоны проверок</h1>
        <p class="page-subtitle">Конструктор шаблонов для различных типов работ (${_templatesData.length})</p>
      </div>
      <button class="btn btn-primary" onclick="showAddTemplate()">
        ${iconSvg('plus', 16)} Новый шаблон
      </button>
    </div>
    <div id="templates-table-area"></div>`;
  renderTemplatesTable();
}

function renderTemplatesTable() {
  const paged = paginate(_templatesData, _templatesPage);
  _templatesPage = paged.page;
  const area = $('templates-table-area');
  if (!area) return;
  area.innerHTML = paged.items.length
    ? templateTable(paged.items) + paginationHtml(paged, 'templatesGoPage')
    : emptyHtml('Нет шаблонов', 'Создайте первый шаблон проверки');
}

function templatesGoPage(p) { _templatesPage = p; renderTemplatesTable(); }

function templateTable(list) {
  const uniMap = {};
  _universities.forEach(u => uniMap[u.id] = u);

  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th><th>Название</th><th>ВУЗ</th>
          <th>Тип работы</th><th>Год</th><th>Статус</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(t => {
            const uni = uniMap[t.university_id];
            return `<tr>
              <td data-label="ID">${t.id}</td>
              <td data-label="Название"><strong>${escHtml(t.name)}</strong></td>
              <td data-label="ВУЗ">${uni ? entityTag('university', uni.id, uni.name) : '—'}</td>
              <td data-label="Тип работы">${escHtml(t.type_work || '—')}</td>
              <td data-label="Год">${escHtml(t.year || '—')}</td>
              <td data-label="Статус">${statusBadge(t.status)}</td>
              <td data-label="" class="actions-cell">
                <button class="btn btn-icon btn-sm" title="Редактировать" onclick="openTemplateEditor(${t.id})">
                  ${iconSvg('edit', 15)}
                </button>
                ${t.status === 'draft' ? `<button class="btn btn-sm btn-success" onclick="publishTemplate(${t.id})">Опубликовать</button>` : ''}
              </td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>
  </div>`;
}

function showAddTemplate() {
  const uniOpts = _universities.map(u =>
    `<option value="${u.id}">${escHtml(u.name)}</option>`
  ).join('');

  const body = `
    <div class="form-group">
      <label class="form-label">Название шаблона</label>
      <input class="form-input" id="tpl-name" placeholder="Курсовая работа — МГУ 2025">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="form-label">ВУЗ</label>
        <select class="form-select" id="tpl-uni">${uniOpts}</select>
      </div>
      <div class="form-group">
        <label class="form-label">Год</label>
        <input class="form-input" id="tpl-year" placeholder="2025">
      </div>
    </div>
    <div class="form-group">
      <label class="form-label">Тип работы</label>
      <input class="form-input" id="tpl-type" placeholder="Курсовая / Диплом / Реферат">
    </div>`;
  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="createTemplate()">Создать</button>`;
  openModal('Новый шаблон', body, footer);
}

async function createTemplate() {
  const name = getVal('tpl-name').trim();
  if (!name) { toast('Введите название', 'error'); return; }
  try {
    await api('POST', '/templates', {
      university_id: parseInt(getVal('tpl-uni')) || null,
      name,
      type_work: getVal('tpl-type').trim(),
      year: getVal('tpl-year').trim(),
    });
    closeModal();
    toast('Шаблон создан', 'success');
    loadTemplates();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

async function publishTemplate(id) {
  if (!confirm('Опубликовать шаблон #' + id + '?')) return;
  try {
    await api('POST', `/templates/${id}/publish`);
    toast('Шаблон опубликован', 'success');
    loadTemplates();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

window.templatesGoPage = templatesGoPage;
window.showAddTemplate = showAddTemplate;
window.createTemplate = createTemplate;
window.publishTemplate = publishTemplate;
