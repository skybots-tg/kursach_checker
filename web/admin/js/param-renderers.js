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

/* ---- Course Year Regex Builder ---- */
function parseCourseYearRegex(val) {
  if (!val) return null;
  const m = val.match(/^\(\?i\)\\b\(\[(\d)-(\d)\]\)\\s\*(.+?)\\b$/);
  if (m) return { min: +m[1], max: +m[2], keyword: m[3], ci: true };
  const m2 = val.match(/^\\b\(\[(\d)-(\d)\]\)\\s\*(.+?)\\b$/);
  if (m2) return { min: +m2[1], max: +m2[2], keyword: m2[3], ci: false };
  return null;
}

function buildCourseYearRegex(min, max, keyword, ci) {
  let rx = ci ? '(?i)' : '';
  rx += '\\b([' + min + '-' + max + '])\\s*' + keyword + '\\b';
  return rx;
}

function courseYearPreview(min, max, kw) {
  const lo = Math.min(min, max), hi = Math.max(min, max);
  const parts = [];
  for (let i = lo; i <= hi; i++) parts.push('\u00ab' + i + ' ' + kw + '\u00bb');
  return parts.join(', ');
}

function renderCourseYearBuilder(blockIndex, path, value) {
  const p = parseCourseYearRegex(value) || { min: 2, max: 6, keyword: '\u043a\u0443\u0440\u0441', ci: true };
  const id = 'blk-' + blockIndex + '-cyr';
  const opts = function(sel) {
    return [1,2,3,4,5,6].map(function(n) {
      return '<option value="' + n + '"' + (n === sel ? ' selected' : '') + '>' + n + '</option>';
    }).join('');
  };

  return `<fieldset class="tpl-param-group">
    <legend>${escHtml(PARAM_LABELS.course_year_regex || 'Course year pattern')}${helpIcon('course_year_regex')}</legend>
    <div class="regex-builder-desc">\u0421\u0438\u0441\u0442\u0435\u043c\u0430 \u0438\u0449\u0435\u0442 \u043d\u043e\u043c\u0435\u0440 \u043a\u0443\u0440\u0441\u0430 \u0432 \u0442\u0435\u043a\u0441\u0442\u0435 \u0434\u043e\u043a\u0443\u043c\u0435\u043d\u0442\u0430 \u043f\u043e \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u043c \u043f\u0440\u0430\u0432\u0438\u043b\u0430\u043c:</div>
    <div class="regex-builder-row">
      <div class="form-group compact">
        <label class="form-label">\u041a\u0443\u0440\u0441 \u043e\u0442</label>
        <select class="form-select" id="${id}-min"
                onchange="onCourseYearBuilderChange(${blockIndex},'${path}')">
          ${opts(p.min)}
        </select>
      </div>
      <span class="regex-builder-sep">&mdash;</span>
      <div class="form-group compact">
        <label class="form-label">\u041a\u0443\u0440\u0441 \u0434\u043e</label>
        <select class="form-select" id="${id}-max"
                onchange="onCourseYearBuilderChange(${blockIndex},'${path}')">
          ${opts(p.max)}
        </select>
      </div>
    </div>
    <div class="form-group">
      <label class="form-label">\u041a\u043b\u044e\u0447\u0435\u0432\u043e\u0435 \u0441\u043b\u043e\u0432\u043e \u0440\u044f\u0434\u043e\u043c \u0441 \u043d\u043e\u043c\u0435\u0440\u043e\u043c</label>
      <input class="form-input" id="${id}-kw" value="${escHtml(p.keyword)}"
             onchange="onCourseYearBuilderChange(${blockIndex},'${path}')">
      <div class="form-hint">\u0421\u043b\u043e\u0432\u043e, \u0441\u0442\u043e\u044f\u0449\u0435\u0435 \u0440\u044f\u0434\u043e\u043c \u0441 \u0446\u0438\u0444\u0440\u043e\u0439 \u043a\u0443\u0440\u0441\u0430 \u043d\u0430 \u0442\u0438\u0442\u0443\u043b\u044c\u043d\u043e\u043c \u043b\u0438\u0441\u0442\u0435</div>
    </div>
    <div class="toggle">
      <div class="toggle-info"><div class="toggle-title">\u0411\u0435\u0437 \u0443\u0447\u0451\u0442\u0430 \u0440\u0435\u0433\u0438\u0441\u0442\u0440\u0430</div></div>
      <label class="switch">
        <input type="checkbox" id="${id}-ci" ${p.ci ? 'checked' : ''}
               onchange="onCourseYearBuilderChange(${blockIndex},'${path}')">
        <span class="slider"></span>
      </label>
    </div>
    <div class="regex-preview" id="${id}-preview">
      <span class="regex-preview-label">\u041d\u0430\u0439\u0434\u0451\u0442 \u0432 \u0442\u0435\u043a\u0441\u0442\u0435:</span> ${courseYearPreview(p.min, p.max, p.keyword)}
    </div>
  </fieldset>`;
}

function onCourseYearBuilderChange(blockIndex, path) {
  const id = 'blk-' + blockIndex + '-cyr';
  const min = parseInt(document.getElementById(id + '-min').value);
  const max = parseInt(document.getElementById(id + '-max').value);
  const kw = document.getElementById(id + '-kw').value.trim() || '\u043a\u0443\u0440\u0441';
  const ci = document.getElementById(id + '-ci').checked;
  const lo = Math.min(min, max), hi = Math.max(min, max);
  onParamChange(blockIndex, path, buildCourseYearRegex(lo, hi, kw, ci), 'string');
  const prev = document.getElementById(id + '-preview');
  if (prev) prev.innerHTML = '<span class="regex-preview-label">\u041d\u0430\u0439\u0434\u0451\u0442 \u0432 \u0442\u0435\u043a\u0441\u0442\u0435:</span> ' + courseYearPreview(lo, hi, kw);
}

/* ---- Caption Pattern Builder (figure / table) ---- */
const CAPTION_DEFAULTS = {
  figure_pattern: { word: '\u0420\u0438\u0441\u0443\u043d\u043e\u043a', startOfLine: true, requireDesc: true },
  table_pattern:  { word: '\u0422\u0430\u0431\u043b\u0438\u0446\u0430', startOfLine: true, requireDesc: true },
};

function parseCaptionPattern(val) {
  if (!val) return null;
  const m = val.match(/^(\^?)(.+?)\\s\+\\d\+\\s\*\[\u2014\u2013\-\]\\s\*(\\S)?$/);
  if (m) return { word: m[2], startOfLine: m[1] === '^', requireDesc: !!m[3] };
  return null;
}

function buildCaptionPattern(word, startOfLine, requireDesc) {
  let rx = startOfLine ? '^' : '';
  rx += word + '\\s+\\d+\\s*[\u2014\u2013-]\\s*';
  if (requireDesc) rx += '\\S';
  return rx;
}

function captionPreviewHtml(word, requireDesc) {
  const desc = requireDesc ? '\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435' : '...';
  return '\u00ab' + word + ' 1 \u2014 ' + desc + '\u00bb';
}

function renderCaptionPatternBuilder(blockIndex, path, value, paramKey) {
  const def = CAPTION_DEFAULTS[paramKey] || { word: '', startOfLine: true, requireDesc: true };
  const p = parseCaptionPattern(value) || def;
  const id = 'blk-' + blockIndex + '-cap-' + paramKey.replace(/_/g, '');
  const lbl = PARAM_LABELS[paramKey] || paramKey;

  return `<fieldset class="tpl-param-group">
    <legend>${escHtml(lbl)}${helpIcon(paramKey)}</legend>
    <div class="regex-builder-desc">\u0421\u0438\u0441\u0442\u0435\u043c\u0430 \u043f\u0440\u043e\u0432\u0435\u0440\u044f\u0435\u0442 \u0444\u043e\u0440\u043c\u0430\u0442 \u043f\u043e\u0434\u043f\u0438\u0441\u0438 \u043f\u043e \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u043c \u043f\u0440\u0430\u0432\u0438\u043b\u0430\u043c:</div>
    <div class="form-group">
      <label class="form-label">\u041d\u0430\u0447\u0430\u043b\u044c\u043d\u043e\u0435 \u0441\u043b\u043e\u0432\u043e \u043f\u043e\u0434\u043f\u0438\u0441\u0438</label>
      <input class="form-input" id="${id}-word" value="${escHtml(p.word)}"
             onchange="onCaptionBuilderChange(${blockIndex},'${path}','${paramKey}')">
      <div class="form-hint">\u0421\u043b\u043e\u0432\u043e \u043f\u0435\u0440\u0435\u0434 \u043d\u043e\u043c\u0435\u0440\u043e\u043c (\u043d\u0430\u043f\u0440\u0438\u043c\u0435\u0440, \u0420\u0438\u0441\u0443\u043d\u043e\u043a \u0438\u043b\u0438 \u0422\u0430\u0431\u043b\u0438\u0446\u0430)</div>
    </div>
    <div class="toggle">
      <div class="toggle-info"><div class="toggle-title">\u041f\u043e\u0434\u043f\u0438\u0441\u044c \u0434\u043e\u043b\u0436\u043d\u0430 \u043d\u0430\u0447\u0438\u043d\u0430\u0442\u044c\u0441\u044f \u0441 \u043d\u0430\u0447\u0430\u043b\u0430 \u0441\u0442\u0440\u043e\u043a\u0438</div></div>
      <label class="switch">
        <input type="checkbox" id="${id}-sol" ${p.startOfLine ? 'checked' : ''}
               onchange="onCaptionBuilderChange(${blockIndex},'${path}','${paramKey}')">
        <span class="slider"></span>
      </label>
    </div>
    <div class="toggle">
      <div class="toggle-info"><div class="toggle-title">\u041e\u0431\u044f\u0437\u0430\u0442\u0435\u043b\u0435\u043d \u0442\u0435\u043a\u0441\u0442 \u043e\u043f\u0438\u0441\u0430\u043d\u0438\u044f \u043f\u043e\u0441\u043b\u0435 \u0440\u0430\u0437\u0434\u0435\u043b\u0438\u0442\u0435\u043b\u044f</div></div>
      <label class="switch">
        <input type="checkbox" id="${id}-rd" ${p.requireDesc ? 'checked' : ''}
               onchange="onCaptionBuilderChange(${blockIndex},'${path}','${paramKey}')">
        <span class="slider"></span>
      </label>
    </div>
    <div class="regex-preview" id="${id}-preview">
      <span class="regex-preview-label">\u041e\u0436\u0438\u0434\u0430\u0435\u043c\u044b\u0439 \u0444\u043e\u0440\u043c\u0430\u0442:</span> ${captionPreviewHtml(p.word, p.requireDesc)}
    </div>
  </fieldset>`;
}

function onCaptionBuilderChange(blockIndex, path, paramKey) {
  const id = 'blk-' + blockIndex + '-cap-' + paramKey.replace(/_/g, '');
  const word = document.getElementById(id + '-word').value.trim() || CAPTION_DEFAULTS[paramKey].word;
  const sol = document.getElementById(id + '-sol').checked;
  const rd = document.getElementById(id + '-rd').checked;
  onParamChange(blockIndex, path, buildCaptionPattern(word, sol, rd), 'string');
  const prev = document.getElementById(id + '-preview');
  if (prev) prev.innerHTML = '<span class="regex-preview-label">\u041e\u0436\u0438\u0434\u0430\u0435\u043c\u044b\u0439 \u0444\u043e\u0440\u043c\u0430\u0442:</span> ' + captionPreviewHtml(word, rd);
}

/* ---- Routing: choose the best renderer for a param ---- */
function getSpecialRenderer(blockKey, paramKey, value, blockIndex, path) {
  if (paramKey === 'doc_policy' && typeof value === 'string')
    return renderDocPolicySelect(blockIndex, path, value);

  if (paramKey === 'course_year_regex' && typeof value === 'string')
    return renderCourseYearBuilder(blockIndex, path, value);

  if ((paramKey === 'figure_pattern' || paramKey === 'table_pattern') && typeof value === 'string')
    return renderCaptionPatternBuilder(blockIndex, path, value, paramKey);

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
window.onCourseYearBuilderChange = onCourseYearBuilderChange;
window.onCaptionBuilderChange = onCaptionBuilderChange;
