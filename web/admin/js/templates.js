/* Templates — list, create, view blocks, new version, publish */

registerPage('templates', loadTemplates);

let _universities = [];
let _gosts = [];

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
    renderTemplates(list);
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderTemplates(list) {
  $('page-templates').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Шаблоны проверок</h1>
        <p class="page-subtitle">Конструктор шаблонов для различных типов работ</p>
      </div>
      <button class="btn btn-primary" onclick="showAddTemplate()">
        ${iconSvg('plus', 16)} Новый шаблон
      </button>
    </div>
    ${list.length ? templateTable(list) : emptyHtml('Нет шаблонов', 'Создайте первый шаблон проверки')}`;
}

function templateTable(list) {
  const uniMap = {};
  _universities.forEach(u => uniMap[u.id] = u.name);

  return `<div class="card" style="padding:0;overflow:hidden">
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr>
          <th>ID</th>
          <th>Название</th>
          <th>ВУЗ</th>
          <th>Тип работы</th>
          <th>Год</th>
          <th>Статус</th>
          <th style="text-align:right">Действия</th>
        </tr></thead>
        <tbody>
          ${list.map(t => `<tr>
            <td>${t.id}</td>
            <td><strong>${escHtml(t.name)}</strong></td>
            <td>${escHtml(uniMap[t.university_id] || '—')}</td>
            <td>${escHtml(t.type_work || '—')}</td>
            <td>${escHtml(t.year || '—')}</td>
            <td>${statusBadge(t.status)}</td>
            <td class="actions-cell">
              <button class="btn btn-icon btn-sm" title="Блоки" onclick="viewTemplateBlocks(${t.id})">
                ${iconSvg('eye', 15)}
              </button>
              ${t.status === 'draft' ? `<button class="btn btn-sm btn-success" onclick="publishTemplate(${t.id})">Опубликовать</button>` : ''}
            </td>
          </tr>`).join('')}
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

async function viewTemplateBlocks(id) {
  try {
    const data = await api('GET', `/templates/${id}/blocks`);
    const blocks = data.blocks || [];
    const body = blocks.length
      ? `<div class="rule-list">${blocks.map(b => `
          <div class="rule-item">
            <div class="ri-info">
              <div class="ri-title">${escHtml(b.title || b.key)}</div>
              <div class="ri-desc">Ключ: ${escHtml(b.key)}</div>
            </div>
            <span class="badge ${b.enabled ? 'badge-success' : 'badge-gray'}">${b.enabled ? 'Вкл' : 'Выкл'}</span>
            <span class="badge badge-${b.severity === 'error' ? 'danger' : b.severity === 'warning' ? 'warn' : 'info'}">${escHtml(b.severity)}</span>
          </div>`).join('')}</div>`
      : emptyHtml('Нет блоков', 'Версия не содержит блоков');
    openModal(`Блоки шаблона #${id} (v${data.version_number})`, body, '');
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

window.showAddTemplate = showAddTemplate;
window.createTemplate = createTemplate;
window.viewTemplateBlocks = viewTemplateBlocks;
window.publishTemplate = publishTemplate;
