/* Rules Library — read-only catalog from autofix endpoint */

registerPage('rules', loadRules);

async function loadRules() {
  const page = $('page-rules');
  page.innerHTML = loadingHtml();
  try {
    const data = await api('GET', '/admin/autofix/rules');
    renderRules(data);
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderRules(data) {
  const fixable = data.fixable || [];
  const notFixable = data.not_fixable || [];
  const all = [...fixable, ...notFixable];

  $('page-rules').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Библиотека правил</h1>
        <p class="page-subtitle">Каталог всех правил проверки документов (${all.length})</p>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Автоисправляемые правила (${fixable.length})</h3>
        <span class="badge badge-success">Безопасно</span>
      </div>
      ${fixable.length ? rulesList(fixable, true) : emptyHtml('Нет правил', '')}
    </div>

    <div class="card">
      <div class="card-header">
        <h3 class="card-title">Не автоисправляемые (${notFixable.length})</h3>
        <span class="badge badge-warn">Только диагностика</span>
      </div>
      ${notFixable.length ? rulesList(notFixable, false) : emptyHtml('Нет правил', '')}
    </div>`;
}

function rulesList(rules, safe) {
  return `<div class="rule-list">${rules.map(r => `
    <div class="rule-item">
      <div class="ri-info">
        <div class="ri-title">${escHtml(r.title)}</div>
        <div class="ri-desc">${escHtml(r.description)}</div>
      </div>
      <span class="badge ${r.default_enabled ? 'badge-success' : 'badge-gray'}">
        ${r.default_enabled ? 'Вкл' : 'Выкл'}
      </span>
    </div>`).join('')}</div>`;
}
