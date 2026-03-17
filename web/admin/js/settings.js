/* Settings — DOC converter + system settings */

registerPage('settings', loadSettings);

async function loadSettings() {
  const page = $('page-settings');
  page.innerHTML = loadingHtml();
  try {
    const cfg = await api('GET', '/admin/settings/doc-converter');
    renderSettings(cfg);
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderSettings(cfg) {
  $('page-settings').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Настройки системы</h1>
        <p class="page-subtitle">Системные параметры и интеграции</p>
      </div>
    </div>

    <div class="card">
      <div class="card-header"><h3 class="card-title">Конвертер DOC → DOCX</h3></div>
      <p class="card-desc">Настройте команду конвертации .doc-файлов через LibreOffice headless или совместимый конвертер.</p>
      <div id="dc-alert-area"></div>

      <div class="toggle">
        <div class="toggle-info">
          <div class="toggle-title">Конвертер включён</div>
          <div class="toggle-desc">Разрешить автоматическую конвертацию DOC → DOCX</div>
        </div>
        <label class="switch">
          <input type="checkbox" id="dc-enabled" ${cfg.enabled ? 'checked' : ''}>
          <span class="slider"></span>
        </label>
      </div>

      <div class="form-group" style="margin-top:16px">
        <label class="form-label">Шаблон команды</label>
        <input class="form-input" id="dc-command" value="${escHtml(cfg.command_template || '')}"
          placeholder='soffice --headless --convert-to docx --outdir "{outdir}" "{input}"'>
        <div class="form-hint">Используйте плейсхолдеры <code>{outdir}</code> и <code>{input}</code></div>
      </div>

      <div class="form-group">
        <label class="form-label">Таймаут (секунд)</label>
        <input class="form-input" type="number" id="dc-timeout" value="${cfg.timeout_sec ?? 60}" min="5" max="600">
      </div>

      <div class="actions">
        <button class="btn btn-primary" onclick="saveDocConverter()">Сохранить</button>
        <button class="btn btn-secondary" onclick="testDocConverter()">Проверить конвертер</button>
      </div>

      <div id="dc-test-result" style="margin-top:14px"></div>
    </div>`;
}

async function saveDocConverter() {
  const area = $('dc-alert-area');
  try {
    await api('PUT', '/admin/settings/doc-converter', {
      enabled: isChecked('dc-enabled'),
      command_template: getVal('dc-command'),
      timeout_sec: parseInt(getVal('dc-timeout')) || 60,
    });
    if (area) area.innerHTML = '<div class="alert success">Настройки конвертера сохранены</div>';
    toast('Настройки сохранены', 'success');
  } catch (err) {
    if (area) area.innerHTML = `<div class="alert error">Ошибка: ${escHtml(err.message)}</div>`;
    toast('Ошибка: ' + err.message, 'error');
  }
}

async function testDocConverter() {
  const el = $('dc-test-result');
  if (el) el.innerHTML = '<div class="alert info">Проверяю конвертер…</div>';
  try {
    const result = await api('POST', '/admin/settings/doc-converter/test');
    if (!el) return;
    if (result.ok) {
      el.innerHTML = `<div class="alert success">Конвертер работает${result.converter_version ? ': ' + escHtml(result.converter_version) : ''}</div>`;
    } else {
      el.innerHTML = `<div class="alert error">${escHtml(result.message)}</div>`;
    }
  } catch (err) {
    if (el) el.innerHTML = `<div class="alert error">Ошибка: ${escHtml(err.message)}</div>`;
  }
}

window.saveDocConverter = saveDocConverter;
window.testDocConverter = testDocConverter;
