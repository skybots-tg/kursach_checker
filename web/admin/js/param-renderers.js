/* Param Renderers — human-readable controls for complex template parameters.
   Replaces raw JSON editing with intuitive Russian-language UI. */

const _tagInputInstances = {};

const DOC_POLICY_OPTIONS = [
  { value: 'convert', label: 'Конвертировать в .docx автоматически' },
  { value: 'reject', label: 'Отклонить файл' },
];

const FORMAT_LABELS = {
  academic: 'Академический формат',
  project_creative: 'Проектно-творческий формат',
};

const COURSE_LABELS = {
  1: '1 курс', 2: '2 курс', 3: '3 курс',
  4: '4 курс', 5: '5 курс', 6: '6 курс',
};

const SECTION_PRESETS = [
  { id: 'title_page', label: 'Титульный лист' },
  { id: 'table_of_contents', label: 'Содержание (оглавление)' },
  { id: 'introduction', label: 'Введение' },
  { id: 'main_body', label: 'Основная часть' },
  { id: 'conclusion', label: 'Заключение' },
  { id: 'bibliography', label: 'Список источников' },
  { id: 'appendix', label: 'Приложения' },
];

/* ---- Select for doc_policy ---- */
function renderDocPolicySelect(blockIndex, path, currentValue) {
  const fieldId = `blk-${blockIndex}-${path.replace(/\./g, '-')}`;
  const options = DOC_POLICY_OPTIONS.map(o =>
    `<option value="${o.value}" ${currentValue === o.value ? 'selected' : ''}>${o.label}</option>`
  ).join('');

  return `<div class="form-group">
    <label class="form-label">${PARAM_LABELS.doc_policy || 'Политика для .doc файлов'}${helpIcon('doc_policy')}</label>
    <select class="form-select" id="${fieldId}"
            onchange="onParamChange(${blockIndex},'${path}',this.value,'string')">
      ${options}
    </select>
  </div>`;
}

/* ---- Tag input for simple arrays ---- */
function renderTagArray(blockIndex, path, items, label, opts = {}) {
  const fieldId = `blk-${blockIndex}-${path.replace(/\./g, '-')}`;
  const tagId = `tag-${fieldId}`;
  const placeholder = opts.placeholder || 'Введите значение и нажмите Enter';
  const hint = opts.hint || '';
  const parseValue = opts.parseValue || null;

  requestAnimationFrame(() => {
    const inst = createTagInput({
      id: tagId,
      items: items || [],
      placeholder,
      parseValue,
      onUpdate(newItems) {
        onParamChange(blockIndex, path, newItems, 'raw');
      },
    });
    inst.render();
    _tagInputInstances[tagId] = inst;
  });

  return `<div class="form-group">
    <label class="form-label">${escHtml(label)}${helpIcon(path.split('.').pop())}</label>
    <div class="tag-input-wrap" id="${tagId}"></div>
  </div>`;
}

/* ---- Checkboxes for allowed_formats ---- */
function renderFormatCheckboxes(blockIndex, path, selected) {
  const items = Object.entries(FORMAT_LABELS).map(([val, label]) => {
    const checked = (selected || []).includes(val) ? 'checked' : '';
    return `<label class="checkbox-card">
      <input type="checkbox" value="${val}" ${checked}
             onchange="onFormatCheckboxChange(${blockIndex},'${path}')">
      <span class="checkbox-card-label">${escHtml(label)}</span>
    </label>`;
  }).join('');

  return `<div class="form-group">
    <label class="form-label">${PARAM_LABELS.allowed_formats || 'Разрешённые форматы работы'}${helpIcon('allowed_formats')}</label>
    <div class="checkbox-cards" id="fmt-checks-${blockIndex}-${path.replace(/\./g,'-')}">${items}</div>
  </div>`;
}

function onFormatCheckboxChange(blockIndex, path) {
  const container = document.getElementById(`fmt-checks-${blockIndex}-${path.replace(/\./g,'-')}`);
  if (!container) return;
  const checked = [...container.querySelectorAll('input:checked')].map(cb => cb.value);
  onParamChange(blockIndex, path, checked, 'raw');
}

/* ---- Per-format number fields (max_authors) ---- */
function renderPerFormatNumbers(blockIndex, path, obj, label, hint) {
  const fields = Object.entries(FORMAT_LABELS).map(([key, fmtLabel]) => {
    const val = (obj && obj[key]) != null ? obj[key] : '';
    const fid = `blk-${blockIndex}-${path.replace(/\./g,'-')}-${key}`;
    return `<div class="form-group compact">
      <label class="form-label">${escHtml(fmtLabel)}</label>
      <input class="form-input" type="number" id="${fid}" value="${val}" step="1" min="1"
             onchange="onPerFormatNumChange(${blockIndex},'${path}')">
    </div>`;
  }).join('');

  return `<fieldset class="tpl-param-group">
    <legend>${escHtml(label)}${helpIcon(path.split('.').pop())}</legend>
    <div class="per-format-fields" id="pfn-${blockIndex}-${path.replace(/\./g,'-')}">${fields}</div>
  </fieldset>`;
}

function onPerFormatNumChange(blockIndex, path) {
  const result = {};
  Object.keys(FORMAT_LABELS).forEach(key => {
    const fid = `blk-${blockIndex}-${path.replace(/\./g,'-')}-${key}`;
    const el = document.getElementById(fid);
    if (el && el.value !== '') result[key] = parseInt(el.value) || 0;
  });
  onParamChange(blockIndex, path, result, 'raw');
}

/* ---- Per-format tag arrays (allowed_for_course_years) ---- */
function renderPerFormatCourses(blockIndex, path, obj) {
  const groups = Object.entries(FORMAT_LABELS).map(([key, fmtLabel]) => {
    const items = (obj && obj[key]) || [];
    const tagId = `tag-pfcr-${blockIndex}-${path.replace(/\./g,'-')}-${key}`;

    requestAnimationFrame(() => {
      const inst = createTagInput({
        id: tagId,
        items: items.map(Number),
        placeholder: 'Номер курса (2, 3…)',
        parseValue: (s) => { const n = parseInt(s); return (n >= 1 && n <= 6) ? n : null; },
        onUpdate() { syncPerFormatCourses(blockIndex, path); },
      });
      inst.render();
      _tagInputInstances[tagId] = inst;
    });

    return `<div class="form-group compact">
      <label class="form-label">${escHtml(fmtLabel)}</label>
      <div class="tag-input-wrap" id="${tagId}"></div>
    </div>`;
  }).join('');

  return `<fieldset class="tpl-param-group">
    <legend>${PARAM_LABELS.allowed_for_course_years || 'Доступные курсы'}${helpIcon('allowed_for_course_years')}</legend>
    ${groups}
  </fieldset>`;
}

function syncPerFormatCourses(blockIndex, path) {
  const result = {};
  Object.keys(FORMAT_LABELS).forEach(key => {
    const tagId = `tag-pfcr-${blockIndex}-${path.replace(/\./g,'-')}-${key}`;
    const inst = _tagInputInstances[tagId];
    if (inst) result[key] = inst.getTags();
  });
  onParamChange(blockIndex, path, result, 'raw');
}

/* ---- Section list (required_sections_in_order) ---- */
function renderSectionsList(blockIndex, path, sections) {
  const items = (sections || []).map((sec, i) => renderSectionItem(blockIndex, path, sec, i)).join('');

  return `<div class="form-group">
    <label class="form-label">${PARAM_LABELS.required_sections_in_order || 'Обязательные разделы'}${helpIcon('required_sections_in_order')}</label>
    <div class="sections-list" id="seclist-${blockIndex}-${path.replace(/\./g,'-')}">${items}</div>
    <button type="button" class="btn btn-secondary btn-sm" style="margin-top:10px"
            onclick="addSectionItem(${blockIndex},'${path}')">
      ${iconSvg('plus', 14)} Добавить раздел
    </button>
  </div>`;
}

function renderSectionItem(blockIndex, path, sec, idx) {
  const secId = sec.id || '';
  const titles = (sec.titles_any_of || []).join(', ');
  const containerId = `seclist-${blockIndex}-${path.replace(/\./g,'-')}`;
  const tagId = `tag-sec-${blockIndex}-${idx}`;

  requestAnimationFrame(() => {
    const inst = createTagInput({
      id: tagId,
      items: sec.titles_any_of || [],
      placeholder: 'Возможные названия раздела',
      onUpdate(newTitles) {
        updateSectionTitles(blockIndex, path, idx, newTitles);
      },
    });
    inst.render();
    _tagInputInstances[tagId] = inst;
  });

  return `<div class="section-item" data-idx="${idx}">
    <div class="section-item-handle" title="Перетащить для изменения порядка">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="9" cy="6" r="1.5"/><circle cx="15" cy="6" r="1.5"/>
        <circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/>
        <circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="18" r="1.5"/>
      </svg>
    </div>
    <div class="section-item-body">
      <div class="section-item-row">
        <span class="section-item-num">${idx + 1}</span>
        <input class="form-input section-id-input" value="${escHtml(secId)}"
               placeholder="ID раздела (например: introduction)"
               onchange="updateSectionId(${blockIndex},'${path}',${idx},this.value)">
        <button type="button" class="btn btn-icon btn-sm section-remove"
                title="Удалить раздел"
                onclick="removeSectionItem(${blockIndex},'${path}',${idx})">
          ${iconSvg('trash', 14)}
        </button>
      </div>
      <div class="section-titles-wrap">
        <label class="form-label" style="font-size:12px;margin-bottom:4px">
          Допустимые названия раздела в документе
        </label>
        <div class="tag-input-wrap" id="${tagId}"></div>
      </div>
    </div>
  </div>`;
}

function updateSectionId(blockIndex, path, idx, value) {
  const sections = getNestedValue(_editBlocks[blockIndex].params, path);
  if (sections && sections[idx]) {
    sections[idx].id = value.trim();
    onParamChange(blockIndex, path, sections, 'raw');
  }
}

function updateSectionTitles(blockIndex, path, idx, newTitles) {
  const sections = getNestedValue(_editBlocks[blockIndex].params, path);
  if (sections && sections[idx]) {
    sections[idx].titles_any_of = newTitles;
    onParamChange(blockIndex, path, sections, 'raw');
  }
}

function addSectionItem(blockIndex, path) {
  const sections = getNestedValue(_editBlocks[blockIndex].params, path) || [];
  sections.push({ id: '', titles_any_of: [] });
  onParamChange(blockIndex, path, sections, 'raw');
  rerenderBlockBody(blockIndex);
}

function removeSectionItem(blockIndex, path, idx) {
  const sections = getNestedValue(_editBlocks[blockIndex].params, path);
  if (!sections) return;
  sections.splice(idx, 1);
  onParamChange(blockIndex, path, sections, 'raw');
  rerenderBlockBody(blockIndex);
}

function getNestedValue(obj, path) {
  return path.split('.').reduce((o, k) => (o && o[k] !== undefined ? o[k] : undefined), obj);
}

/* ---- Regex field with description ---- */
function renderRegexField(blockIndex, path, value, label) {
  const fieldId = `blk-${blockIndex}-${path.replace(/\./g, '-')}`;
  return `<div class="form-group">
    <label class="form-label">${escHtml(label)}${helpIcon(path.split('.').pop())}</label>
    <input class="form-input mono-input" id="${fieldId}" value="${escHtml(value || '')}"
           onchange="onParamChange(${blockIndex},'${path}',this.value,'string')">
  </div>`;
}

/* ---- Routing: choose the best renderer for a param ---- */
function getSpecialRenderer(blockKey, paramKey, value, blockIndex, path) {
  if (paramKey === 'doc_policy' && typeof value === 'string')
    return renderDocPolicySelect(blockIndex, path, value);

  if (paramKey === 'course_year_regex' && typeof value === 'string')
    return renderRegexField(blockIndex, path, value, PARAM_LABELS[paramKey] || paramKey);

  if (paramKey === 'allowed_formats' && Array.isArray(value))
    return renderFormatCheckboxes(blockIndex, path, value);

  if (paramKey === 'max_authors' && typeof value === 'object' && !Array.isArray(value))
    return renderPerFormatNumbers(blockIndex, path, value,
      PARAM_LABELS[paramKey] || 'Максимум авторов',
      'Максимальное количество авторов для каждого формата работы');

  if (paramKey === 'allowed_for_course_years' && typeof value === 'object' && !Array.isArray(value))
    return renderPerFormatCourses(blockIndex, path, value);

  if (paramKey === 'required_sections_in_order' && Array.isArray(value))
    return renderSectionsList(blockIndex, path, value);

  if (Array.isArray(value) && value.every(v => typeof v === 'string' || typeof v === 'number')) {
    const label = PARAM_LABELS[paramKey] || paramKey;
    const isNumeric = value.length > 0 && value.every(v => typeof v === 'number');
    return renderTagArray(blockIndex, path, value, label, {
      parseValue: isNumeric ? (s => { const n = parseFloat(s); return isNaN(n) ? null : n; }) : null,
    });
  }

  return null;
}

/* ---- Expose globally ---- */
window.getSpecialRenderer = getSpecialRenderer;
window.onFormatCheckboxChange = onFormatCheckboxChange;
window.onPerFormatNumChange = onPerFormatNumChange;
window.updateSectionId = updateSectionId;
window.addSectionItem = addSectionItem;
window.removeSectionItem = removeSectionItem;
