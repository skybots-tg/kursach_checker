/* Autofix — stats, config, safety limits */

registerPage('autofix', loadAutofix);

async function loadAutofix() {
  const page = $('page-autofix');
  page.innerHTML = loadingHtml();
  try {
    const [rules, config, stats] = await Promise.all([
      api('GET', '/admin/autofix/rules'),
      api('GET', '/admin/autofix/config'),
      api('GET', '/admin/autofix/stats'),
    ]);
    renderAutofix(rules, config, stats);
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderAutofix(rules, config, stats) {
  const d = config.defaults || {};
  const s = config.safety_limits || {};

  $('page-autofix').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Автоисправления</h1>
        <p class="page-subtitle">Глобальные настройки автоматического исправления форматирования</p>
      </div>
    </div>

    <div class="stats-grid">
      <div class="card stat-card">
        <div class="stat-icon blue">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        </div>
        <div class="stat-val">${stats.total_checks_with_autofix ?? 0}</div>
        <div class="stat-label">Проверок с автоисправлениями</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon green">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
        <div class="stat-val">${stats.total_autofixed_items ?? 0}</div>
        <div class="stat-label">Всего исправлений</div>
      </div>
      <div class="card stat-card">
        <div class="stat-icon yellow">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        </div>
        <div class="stat-val">${stats.avg_fixes_per_check ?? 0}</div>
        <div class="stat-label">Среднее на проверку</div>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3 class="card-title">Автоисправляемые правила</h3></div>
      <p class="card-desc">Глобальные дефолты можно переопределить в каждом шаблоне.</p>
      <div class="rule-list" id="af-fixable-list">${(rules.fixable || []).map(r => afRuleItem(r, true)).join('')}</div>
    </div>

    <div class="card">
      <div class="card-header"><h3 class="card-title">Не автоисправляемые</h3></div>
      <p class="card-desc">Эти правила не поддерживают автоматическое исправление.</p>
      <div class="rule-list" id="af-notfixable-list">${(rules.not_fixable || []).map(r => afRuleItem(r, false)).join('')}</div>
    </div>

    <div class="card">
      <div class="card-header"><h3 class="card-title">Глобальные дефолты</h3></div>
      <p class="card-desc">Значения по умолчанию для новых шаблонов.</p>
      <div id="af-defaults-form">
        ${afToggle('af-enabled', 'Автоисправления включены', '', d.enabled)}
        ${afToggle('af-alignment', 'Выравнивание', 'Устанавливать по ширине', d.normalize_alignment)}
        ${afToggle('af-spacing', 'Межстрочный интервал', '', d.normalize_line_spacing)}
        ${afToggle('af-indent', 'Красная строка', '', d.normalize_first_line_indent)}
        ${afToggle('af-before-after', 'Интервалы до/после', '', d.normalize_spacing_before_after)}
        ${afToggle('af-font', 'Шрифт и кегль', '', d.normalize_font)}
        <div class="form-row" style="margin-top:14px">
          <div class="form-group">
            <label class="form-label">Интервал до абзаца (pt)</label>
            <input class="form-input" type="number" id="af-space-before" value="${d.space_before_pt ?? 0}" min="0" step="0.5">
          </div>
          <div class="form-group">
            <label class="form-label">Интервал после абзаца (pt)</label>
            <input class="form-input" type="number" id="af-space-after" value="${d.space_after_pt ?? 0}" min="0" step="0.5">
          </div>
        </div>
      </div>
      <div class="actions">
        <button class="btn btn-primary" onclick="saveAutofixDefaults()">Сохранить дефолты</button>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3 class="card-title">Пределы безопасности</h3></div>
      <p class="card-desc">Что категорически не трогать при автоисправлении.</p>
      <div id="af-safety-form">
        ${afToggle('af-skip-headings', 'Пропускать заголовки', '', s.skip_headings)}
        ${afToggle('af-skip-tables', 'Пропускать таблицы', '', s.skip_tables)}
        ${afToggle('af-skip-toc', 'Пропускать оглавление', '', s.skip_toc)}
        ${afToggle('af-skip-footnotes', 'Пропускать сноски', '', s.skip_footnotes)}
        <div class="form-group" style="margin-top:14px">
          <label class="form-label">Макс. исправлений на документ</label>
          <input class="form-input" type="number" id="af-max-changes" value="${s.max_changes_per_document ?? 500}" min="1">
        </div>
      </div>
      <div class="actions">
        <button class="btn btn-primary" onclick="saveAutofixSafety()">Сохранить ограничения</button>
      </div>
    </div>`;
}

function afRuleItem(r, safe) {
  return `<div class="rule-item">
    <div class="ri-info">
      <div class="ri-title">${escHtml(r.title)}</div>
      <div class="ri-desc">${escHtml(r.description)}</div>
    </div>
    <span class="badge ${safe ? 'badge-success' : 'badge-danger'}">${safe ? 'Безопасно' : 'Нет'}</span>
    <span class="badge ${r.default_enabled ? 'badge-success' : 'badge-gray'}">${r.default_enabled ? 'Вкл' : 'Выкл'}</span>
  </div>`;
}

function afToggle(id, title, desc, checked) {
  return `<div class="toggle">
    <div class="toggle-info">
      <div class="toggle-title">${title}</div>
      ${desc ? `<div class="toggle-desc">${desc}</div>` : ''}
    </div>
    <label class="switch"><input type="checkbox" id="${id}" ${checked ? 'checked' : ''}><span class="slider"></span></label>
  </div>`;
}

async function saveAutofixDefaults() {
  try {
    await api('PUT', '/admin/autofix/config/defaults', {
      enabled: isChecked('af-enabled'),
      normalize_alignment: isChecked('af-alignment'),
      normalize_line_spacing: isChecked('af-spacing'),
      normalize_first_line_indent: isChecked('af-indent'),
      normalize_spacing_before_after: isChecked('af-before-after'),
      normalize_font: isChecked('af-font'),
      space_before_pt: parseFloat(getVal('af-space-before')) || 0,
      space_after_pt: parseFloat(getVal('af-space-after')) || 0,
    });
    toast('Дефолты сохранены', 'success');
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

async function saveAutofixSafety() {
  try {
    await api('PUT', '/admin/autofix/config/safety', {
      skip_headings: isChecked('af-skip-headings'),
      skip_tables: isChecked('af-skip-tables'),
      skip_toc: isChecked('af-skip-toc'),
      skip_footnotes: isChecked('af-skip-footnotes'),
      max_changes_per_document: parseInt(getVal('af-max-changes')) || 500,
    });
    toast('Ограничения сохранены', 'success');
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

window.saveAutofixDefaults = saveAutofixDefaults;
window.saveAutofixSafety = saveAutofixSafety;
