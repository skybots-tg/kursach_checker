/* Content — System Texts tab: editable bot messages with friendly labels */

let _systemTexts = [];

async function loadSystemTexts() {
  _systemTexts = await api('GET', '/admin/content/system-texts');
  renderContentPage(renderSystemTextsTab(), '');
}

function renderSystemTextsTab() {
  if (!_systemTexts.length) {
    return '<div class="card"><p class="form-hint" style="text-align:center;margin:0">Системные тексты не найдены</p></div>';
  }

  const groups = {};
  _systemTexts.forEach(t => {
    const g = t.group || 'Прочее';
    if (!groups[g]) groups[g] = [];
    groups[g].push(t);
  });

  let html = `
    <div class="system-texts-intro card" style="margin-bottom:16px;padding:14px 18px">
      <p style="margin:0;font-size:13px;color:var(--text-secondary)">
        Здесь можно изменить все сообщения, которые бот отправляет пользователям.
        Если текст не задан, используется значение по умолчанию.
        В текстах можно использовать переменные в фигурных скобках, например <code>{check_id}</code>.
      </p>
    </div>`;

  for (const [group, items] of Object.entries(groups)) {
    html += `<h3 class="section-heading">${escHtml(group)}</h3>`;
    html += '<div class="system-texts-group">';
    items.forEach(t => {
      const isOverridden = t.current_value !== null && t.current_value !== undefined;
      const displayValue = isOverridden ? t.current_value : t.default;
      const statusBadge = isOverridden
        ? '<span class="badge badge-success" style="font-size:10px">Изменён</span>'
        : '<span class="badge badge-neutral" style="font-size:10px">По умолчанию</span>';

      const varsHtml = t.variables && t.variables.length
        ? `<div class="st-vars">Переменные: ${t.variables.map(v => '<code>{' + escHtml(v) + '}</code>').join(', ')}</div>`
        : '';

      html += `
        <div class="card st-card" data-key="${escHtml(t.key)}">
          <div class="st-header">
            <div class="st-title-row">
              <strong class="st-label">${escHtml(t.label)}</strong>
              ${statusBadge}
              ${t.supports_html ? '<span class="badge badge-info" style="font-size:10px">HTML</span>' : ''}
            </div>
            <div class="st-description">${escHtml(t.description)}</div>
            ${varsHtml}
          </div>
          <div class="st-preview">
            <div class="st-preview-text">${t.supports_html ? sanitizeTgHtml(displayValue) : escHtml(displayValue)}</div>
          </div>
          <div class="st-actions">
            <button class="btn btn-secondary btn-sm" onclick="editSystemText('${escHtml(t.key)}')">
              ${iconSvg('edit', 14)} Редактировать
            </button>
            ${isOverridden ? `<button class="btn btn-ghost btn-sm" onclick="resetSystemText('${escHtml(t.key)}')" title="Вернуть значение по умолчанию">Сбросить</button>` : ''}
          </div>
        </div>`;
    });
    html += '</div>';
  }

  return html;
}

function editSystemText(key) {
  const item = _systemTexts.find(t => t.key === key);
  if (!item) return;

  const currentValue = item.current_value !== null && item.current_value !== undefined
    ? item.current_value
    : item.default;

  const varsHelp = item.variables && item.variables.length
    ? `<div class="form-hint" style="margin-bottom:8px">
        Доступные переменные: ${item.variables.map(v => '<code>{' + escHtml(v) + '}</code>').join(', ')}
       </div>`
    : '';

  const htmlHelp = item.supports_html
    ? `<div class="form-hint">Поддерживается HTML: &lt;b&gt;, &lt;i&gt;, &lt;u&gt;, &lt;a href="..."&gt;</div>`
    : '';

  const body = `
    <div class="form-group">
      <label class="form-label">${escHtml(item.label)}</label>
      <p class="form-hint" style="margin-top:0">${escHtml(item.description)}</p>
    </div>
    ${varsHelp}
    <div class="form-group">
      <label class="form-label">Текст сообщения</label>
      ${item.supports_html ? `
        <div class="rt-toolbar">
          <button type="button" class="rt-btn" onclick="rtWrap('st-value','<b>','</b>')" title="Жирный"><b>B</b></button>
          <button type="button" class="rt-btn" onclick="rtWrap('st-value','<i>','</i>')" title="Курсив"><i>I</i></button>
          <button type="button" class="rt-btn" onclick="rtWrap('st-value','<u>','</u>')" title="Подчёркнутый"><u>U</u></button>
          <button type="button" class="rt-btn" onclick="rtInsertLink('st-value')" title="Ссылка">🔗</button>
        </div>
      ` : ''}
      <textarea class="form-textarea" id="st-value" rows="6" oninput="updateStPreview(${item.supports_html})">${escHtml(currentValue)}</textarea>
      ${htmlHelp}
    </div>
    <div class="form-group">
      <label class="form-label">Предпросмотр</label>
      <div id="st-preview-box" class="msg-preview-box" style="border:1px solid var(--border);border-radius:8px;padding:10px 14px;min-height:40px;background:var(--bg-subtle);line-height:1.6;white-space:pre-wrap">
        ${item.supports_html ? sanitizeTgHtml(currentValue) : escHtml(currentValue)}
      </div>
    </div>
    <div class="form-group">
      <details>
        <summary style="cursor:pointer;font-size:12px;color:var(--text-muted)">Значение по умолчанию</summary>
        <div class="msg-preview-box" style="margin-top:6px;border:1px solid var(--border);border-radius:8px;padding:10px 14px;background:var(--bg-subtle);line-height:1.6;white-space:pre-wrap;font-size:12px;color:var(--text-muted)">
          ${item.supports_html ? sanitizeTgHtml(item.default) : escHtml(item.default)}
        </div>
      </details>
    </div>`;

  const footer = `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="saveSystemText('${escHtml(key)}')">Сохранить</button>`;
  openModal('Редактировать текст', body, footer);
}

function updateStPreview(supportsHtml) {
  const box = document.getElementById('st-preview-box');
  const val = getVal('st-value');
  if (box) {
    box.innerHTML = supportsHtml ? sanitizeTgHtml(val) : escHtml(val);
  }
}

async function saveSystemText(key) {
  try {
    const value = getVal('st-value');
    await api('PUT', `/admin/content/texts/${encodeURIComponent(key)}`, { value });
    closeModal();
    toast('Текст сохранён', 'success');
    loadContent();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

async function resetSystemText(key) {
  const item = _systemTexts.find(t => t.key === key);
  if (!item) return;
  if (!confirm(`Вернуть текст «${item.label}» к значению по умолчанию?`)) return;
  try {
    await api('PUT', `/admin/content/texts/${encodeURIComponent(key)}`, { value: item.default });
    toast('Текст сброшен к значению по умолчанию', 'success');
    loadContent();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

/* ---------- Expose ---------- */
window.loadSystemTexts = loadSystemTexts;
window.editSystemText = editSystemText;
window.saveSystemText = saveSystemText;
window.resetSystemText = resetSystemText;
window.updateStPreview = updateStPreview;
