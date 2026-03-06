/* Admin SPA — routing + API calls for Autofix & Settings pages */

const API = '/api';
const TOKEN_KEY = 'admin_token';

function getToken() {
  return localStorage.getItem(TOKEN_KEY) || '';
}

function headers() {
  return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() };
}

async function api(method, path, body) {
  const opts = { method, headers: headers() };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

/* ---- Navigation ---- */
function navigateTo(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('#sidebar-menu a').forEach(a => a.classList.remove('active'));

  const page = document.getElementById('page-' + pageId);
  if (page) page.classList.add('active');

  const link = document.querySelector(`#sidebar-menu a[data-page="${pageId}"]`);
  if (link) link.classList.add('active');

  if (pageId === 'autofix') loadAutofixPage();
  if (pageId === 'settings') loadSettingsPage();
}

document.getElementById('sidebar-menu').addEventListener('click', e => {
  const a = e.target.closest('a[data-page]');
  if (!a) return;
  e.preventDefault();
  navigateTo(a.dataset.page);
});

/* ---- Autofix page ---- */
async function loadAutofixPage() {
  try {
    const [rules, config, stats] = await Promise.all([
      api('GET', '/admin/autofix/rules'),
      api('GET', '/admin/autofix/config'),
      api('GET', '/admin/autofix/stats'),
    ]);
    renderAutofixRules(rules);
    populateAutofixConfig(config);
    renderAutofixStats(stats);
  } catch (err) {
    console.warn('Autofix load:', err.message);
  }
}

function renderAutofixRules(data) {
  const fixable = document.getElementById('af-fixable-list');
  const notFixable = document.getElementById('af-notfixable-list');
  fixable.innerHTML = (data.fixable || []).map(r => ruleItem(r, true)).join('');
  notFixable.innerHTML = (data.not_fixable || []).map(r => ruleItem(r, false)).join('');
}

function ruleItem(r, safe) {
  const badge = safe
    ? '<span class="badge safe">Безопасно</span>'
    : '<span class="badge unsafe">Не автоисправляется</span>';
  const status = r.default_enabled
    ? '<span class="badge on">Вкл</span>'
    : '<span class="badge off">Выкл</span>';
  return `<div class="rule-item">
    <div class="ri-info"><div class="ri-title">${r.title}</div><div class="ri-desc">${r.description}</div></div>
    ${badge} ${status}
  </div>`;
}

function populateAutofixConfig(cfg) {
  const d = cfg.defaults || {};
  const s = cfg.safety_limits || {};
  setChecked('af-enabled', d.enabled);
  setChecked('af-alignment', d.normalize_alignment);
  setChecked('af-spacing', d.normalize_line_spacing);
  setChecked('af-indent', d.normalize_first_line_indent);
  setChecked('af-before-after', d.normalize_spacing_before_after);
  setChecked('af-font', d.normalize_font);
  setVal('af-space-before', d.space_before_pt);
  setVal('af-space-after', d.space_after_pt);
  setChecked('af-skip-headings', s.skip_headings);
  setChecked('af-skip-tables', s.skip_tables);
  setChecked('af-skip-toc', s.skip_toc);
  setChecked('af-skip-footnotes', s.skip_footnotes);
  setVal('af-max-changes', s.max_changes_per_document);
}

function renderAutofixStats(stats) {
  setText('af-stat-total', stats.total_checks_with_autofix);
  setText('af-stat-items', stats.total_autofixed_items);
  setText('af-stat-avg', stats.avg_fixes_per_check);
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
    showAlert('af-defaults-form', 'Дефолты сохранены', 'success');
  } catch (err) {
    showAlert('af-defaults-form', 'Ошибка: ' + err.message, 'error');
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
    showAlert('af-safety-form', 'Ограничения сохранены', 'success');
  } catch (err) {
    showAlert('af-safety-form', 'Ошибка: ' + err.message, 'error');
  }
}

/* ---- Settings page ---- */
async function loadSettingsPage() {
  try {
    const cfg = await api('GET', '/admin/settings/doc-converter');
    setChecked('dc-enabled', cfg.enabled);
    setVal('dc-command', cfg.command_template || '');
    setVal('dc-timeout', cfg.timeout_sec || 60);
  } catch (err) {
    console.warn('Settings load:', err.message);
  }
}

async function saveDocConverter() {
  const area = document.getElementById('dc-alert-area');
  try {
    await api('PUT', '/admin/settings/doc-converter', {
      enabled: isChecked('dc-enabled'),
      command_template: getVal('dc-command'),
      timeout_sec: parseInt(getVal('dc-timeout')) || 60,
    });
    area.innerHTML = alertHtml('Настройки конвертера сохранены', 'success');
  } catch (err) {
    area.innerHTML = alertHtml('Ошибка: ' + err.message, 'error');
  }
}

async function testDocConverter() {
  const el = document.getElementById('dc-test-result');
  el.innerHTML = '<div class="alert info">Проверяю конвертер…</div>';
  try {
    const result = await api('POST', '/admin/settings/doc-converter/test');
    if (result.ok) {
      el.innerHTML = alertHtml(
        'Конвертер работает' + (result.converter_version ? ': ' + result.converter_version : ''),
        'success'
      );
    } else {
      el.innerHTML = alertHtml(result.message, 'error');
    }
  } catch (err) {
    el.innerHTML = alertHtml('Ошибка: ' + err.message, 'error');
  }
}

/* ---- Helpers ---- */
function setChecked(id, val) { const el = document.getElementById(id); if (el) el.checked = !!val; }
function isChecked(id) { const el = document.getElementById(id); return el ? el.checked : false; }
function setVal(id, val) { const el = document.getElementById(id); if (el) el.value = val ?? ''; }
function getVal(id) { const el = document.getElementById(id); return el ? el.value : ''; }
function setText(id, val) { const el = document.getElementById(id); if (el) el.textContent = val ?? '—'; }

function alertHtml(msg, type) {
  return `<div class="alert ${type}">${msg}</div>`;
}

function showAlert(containerId, msg, type) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const existing = container.querySelector('.alert');
  if (existing) existing.remove();
  container.insertAdjacentHTML('afterbegin', alertHtml(msg, type));
  setTimeout(() => {
    const a = container.querySelector('.alert');
    if (a) a.remove();
  }, 4000);
}

/* expose to inline onclick handlers */
window.saveAutofixDefaults = saveAutofixDefaults;
window.saveAutofixSafety = saveAutofixSafety;
window.saveDocConverter = saveDocConverter;
window.testDocConverter = testDocConverter;
