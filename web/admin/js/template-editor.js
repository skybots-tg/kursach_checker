/* Template Editor — accordion block editor with human-readable Russian UI.
   Uses tag-input.js for arrays and param-renderers.js for complex params. */

const SEVERITY_OPTIONS = [
  { value: 'error', label: 'Ошибка', badge: 'danger' },
  { value: 'warning', label: 'Предупреждение', badge: 'warn' },
  { value: 'advice', label: 'Совет', badge: 'info' },
  { value: 'off', label: 'Не проверять', badge: 'gray' },
];
const SEVERITY_LABELS = { error: 'Ошибка', warning: 'Предупреждение', advice: 'Совет', off: 'Не проверять' };
const SEVERITY_BADGE = { error: 'danger', warning: 'warn', advice: 'info', off: 'gray' };

const BLOCK_DESCRIPTIONS = {
  passport: 'Основная информация о шаблоне',
  file_intake: 'Форматы файлов, размер, конвертация .doc',
  context_extraction: 'Автоопределение курса и числа авторов из документа',
  work_formats: 'Академический / проектный формат, групповая работа',
  structure: 'Обязательные разделы и порядок их следования',
  volume: 'Подсчёт объёма текста в авторских листах',
  bibliography: 'Количество источников, иноязычные, свежесть',
  layout: 'Формат страницы, поля, допуски',
  typography: 'Шрифт, размер, интервалы, выравнивание, отступы',
  footnotes: 'Параметры оформления сносок',
  objects: 'Таблицы, рисунки, встроенность объектов',
  integrity: 'Режим правок, комментарии, защита паролем',
  autofix: 'Какие параметры исправлять автоматически',
  reporting: 'Строгость итоговой оценки',
  demo_test: 'Прогон проверки на тестовом файле',
};

const PARAM_LABELS = {
  allowed_extensions: 'Разрешённые форматы файлов',
  max_size_mb: 'Максимальный размер файла (МБ)',
  doc_policy: 'Политика для .doc файлов',
  detect_course_year: 'Определять курс из документа',
  detect_authors_count: 'Определять число авторов',
  course_year_regex: 'Регулярное выражение для курса',
  authors_labels: 'Метки для поиска авторов',
  allowed_formats: 'Разрешённые форматы работы',
  max_authors: 'Максимум авторов',
  allowed_for_course_years: 'Доступные курсы',
  required_sections_in_order: 'Обязательные разделы (по порядку)',
  author_sheet_chars_with_spaces: 'Знаков в 1 авторском листе',
  min_author_sheets_default: 'Минимум авторских листов',
  min_total_sources: 'Минимум источников',
  require_foreign_sources: 'Требовать иноязычные источники',
  recent_window_years_max: 'Окно давности (лет)',
  margins_mm: 'Поля страницы (мм)',
  tolerance_mm: 'Допуск расхождения (мм)',
  top: 'Верхнее', bottom: 'Нижнее', left: 'Левое', right: 'Правое',
  body: 'Параметры основного текста',
  font: 'Шрифт', size_pt: 'Размер (пт)',
  line_spacing: 'Межстрочный интервал',
  first_line_indent_mm: 'Абзацный отступ (мм)',
  required: 'Обязательны',
  forbid_linked_media: 'Запретить ссылочные медиа',
  require_embedded_objects: 'Требовать встроенные объекты',
  forbid_track_changes: 'Запретить режим правок',
  forbid_comments: 'Запретить комментарии',
  forbid_password_protection: 'Запретить защиту паролем',
  normalize_alignment: 'Исправлять выравнивание',
  normalize_line_spacing: 'Исправлять межстрочный интервал',
  normalize_first_line_indent: 'Исправлять абзацный отступ',
  normalize_spacing_before_after: 'Исправлять интервалы до/после абзаца',
  normalize_font: 'Исправлять шрифт',
  space_before_pt: 'Интервал перед абзацем (пт)',
  space_after_pt: 'Интервал после абзаца (пт)',
  academic: 'Академический формат',
  project_creative: 'Проектно-творческий формат',
};

const PARAM_HINTS = {
  allowed_extensions: 'Список форматов, которые система примет. Рекомендуется .docx как основной формат',
  max_size_mb: 'Файлы тяжелее этого значения будут отклонены при загрузке',
  doc_policy: 'Как поступить, если пользователь загрузит файл в старом формате .doc',
  detect_course_year: 'Система попробует определить курс студента по тексту титульного листа',
  detect_authors_count: 'Система попробует определить количество авторов по титульному листу',
  course_year_regex: 'Регулярное выражение для извлечения номера курса. Менять только если стандартный шаблон не работает',
  authors_labels: 'Ключевые слова для поиска авторов на титульном листе (например: «Выполнил», «Студент»)',
  allowed_formats: 'Какие форматы работ допустимы: академический (классическая структура) или проектный',
  max_authors: 'Максимальное число авторов для каждого формата. Для групповых работ — больше 1',
  allowed_for_course_years: 'На каком курсе какой формат доступен студентам',
  required_sections_in_order: 'Обязательные разделы работы. Система проверит наличие и порядок следования',
  author_sheet_chars_with_spaces: 'Сколько знаков с пробелами = 1 авторский лист. Стандарт — 40 000',
  min_author_sheets_default: 'Минимальный объём работы. Работы меньшего объёма получат замечание',
  min_total_sources: 'Минимальное число источников в списке литературы. Обычно 15–30 для курсовых',
  require_foreign_sources: 'Обязательно ли наличие иностранных источников в библиографии',
  recent_window_years_max: 'За сколько лет источники считаются актуальными. Более старые — устаревшими',
  margins_mm: 'Размеры полей страницы в мм. Стандарт: верх 20, низ 20, лево 30, право 15',
  tolerance_mm: 'На сколько мм поля могут отклоняться от заданных. Обычно 1–2 мм',
  top: 'Верхнее поле страницы в миллиметрах',
  bottom: 'Нижнее поле страницы в миллиметрах',
  left: 'Левое поле (обычно больше из-за подшивки)',
  right: 'Правое поле страницы в миллиметрах',
  body: 'Настройки форматирования основного текста (не заголовков)',
  font: 'Название шрифта основного текста. Стандарт — Times New Roman',
  size_pt: 'Размер шрифта в пунктах. Стандарт для основного текста — 14 пт',
  line_spacing: 'Межстрочный интервал. Стандарт — 1.5 (полуторный)',
  first_line_indent_mm: 'Отступ первой строки абзаца. Стандарт — 12.5 мм (1.25 см)',
  required: 'Обязательны ли сноски в работе',
  forbid_linked_media: 'Запретить вставку изображений по ссылке — все медиа должны быть встроены',
  require_embedded_objects: 'Все объекты (таблицы, рисунки) должны быть встроены в документ',
  forbid_track_changes: 'Запретить наличие неприменённых правок (Track Changes)',
  forbid_comments: 'Запретить наличие комментариев в финальном документе',
  forbid_password_protection: 'Документ не должен быть защищён паролем',
  normalize_alignment: 'Автоматически устанавливать выравнивание текста по ширине',
  normalize_line_spacing: 'Автоматически исправлять межстрочный интервал',
  normalize_first_line_indent: 'Автоматически исправлять абзацный отступ',
  normalize_spacing_before_after: 'Автоматически убирать лишние интервалы до/после абзацев',
  normalize_font: 'Автоматически исправлять шрифт и его размер',
  space_before_pt: 'Интервал перед абзацем в пунктах. Обычно 0',
  space_after_pt: 'Интервал после абзаца в пунктах. Обычно 0',
};

const META_HINTS = {
  name: 'Уникальное имя шаблона. Обычно включает ВУЗ, тип работы и год',
  uni: 'Университет, для которого предназначен шаблон. Определяет набор ГОСТов',
  year: 'Учебный год, для которого актуален шаблон',
  type: 'Тип работы: курсовая, дипломная, реферат, ВКР и т.д.',
};

function helpIcon(key, hints) {
  const text = (hints || PARAM_HINTS)[key];
  if (!text) return '';
  return `<span class="param-help" data-help="${escHtml(text)}">?</span>`;
}

/* ---- Editor State ---- */
let _editTplId = null;
let _editTplMeta = null;
let _editBlocks = [];
let _editVersionNum = 0;

async function openTemplateEditor(id) {
  const page = $('page-templates');
  page.innerHTML = loadingHtml();
  try {
    const [tpl, data] = await Promise.all([
      api('GET', `/templates/${id}`),
      api('GET', `/templates/${id}/blocks`),
    ]);
    _editTplId = id;
    _editTplMeta = tpl;
    _editBlocks = JSON.parse(JSON.stringify(data.blocks || []));
    _editVersionNum = data.version_number;
    renderEditor();
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderEditor() {
  const uniOpts = _universities.map(u =>
    `<option value="${u.id}" ${_editTplMeta.university_id === u.id ? 'selected' : ''}>${escHtml(u.name)}</option>`
  ).join('');
  const blocksHtml = _editBlocks.map((b, i) => renderBlock(b, i)).join('');

  $('page-templates').innerHTML = `
    <div class="tpl-editor-header">
      <button class="btn btn-ghost" onclick="backToTemplateList()">
        ${iconSvg('arrowLeft', 16)} Назад к списку
      </button>
      <div class="tpl-editor-title-row">
        <div>
          <h1 class="page-title">${escHtml(_editTplMeta.name)}</h1>
          <p class="page-subtitle">Версия ${_editVersionNum} · ${statusBadge(_editTplMeta.status)}</p>
        </div>
        <button class="btn btn-primary" onclick="saveTemplateChanges()">
          ${iconSvg('save', 16)} Сохранить
        </button>
      </div>
    </div>

    <div class="card" style="margin-bottom:20px">
      <div class="card-header" style="cursor:pointer" onclick="toggleMetaSection()">
        <div class="card-title">Метаданные шаблона</div>
        <span id="meta-chevron" style="transition:transform 0.2s">${iconSvg('chevronDown', 16)}</span>
      </div>
      <div id="tpl-meta-body">
        <div class="form-group">
          <label class="form-label">Название шаблона${helpIcon('name', META_HINTS)}</label>
          <input class="form-input" id="edit-tpl-name" value="${escHtml(_editTplMeta.name)}">
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">ВУЗ${helpIcon('uni', META_HINTS)}</label>
            <select class="form-select" id="edit-tpl-uni">${uniOpts}</select>
          </div>
          <div class="form-group">
            <label class="form-label">Год${helpIcon('year', META_HINTS)}</label>
            <input class="form-input" id="edit-tpl-year" value="${escHtml(_editTplMeta.year || '')}">
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Тип работы${helpIcon('type', META_HINTS)}</label>
          <input class="form-input" id="edit-tpl-type" value="${escHtml(_editTplMeta.type_work || '')}">
        </div>
        <div class="toggle" style="border:none;padding-top:4px">
          <div class="toggle-info"><div class="toggle-title">Активен</div></div>
          <label class="switch">
            <input type="checkbox" id="edit-tpl-active" ${_editTplMeta.active ? 'checked' : ''}>
            <span class="slider"></span>
          </label>
        </div>
      </div>
    </div>

    <h2 style="font-size:16px;font-weight:700;margin-bottom:14px">Блоки проверки</h2>
    <div class="tpl-blocks-list">${blocksHtml}</div>
    <div style="padding:20px 0;text-align:right">
      <button class="btn btn-primary" onclick="saveTemplateChanges()">
        ${iconSvg('save', 16)} Сохранить изменения
      </button>
    </div>`;
}

/* ---- Block Accordion ---- */
function renderBlock(block, index) {
  const desc = BLOCK_DESCRIPTIONS[block.key] || '';
  const sevLabel = SEVERITY_LABELS[block.severity] || block.severity;
  const sevBadge = SEVERITY_BADGE[block.severity] || 'gray';

  const sevOptions = SEVERITY_OPTIONS.map(o =>
    `<option value="${o.value}" ${block.severity === o.value ? 'selected' : ''}>${o.label}</option>`
  ).join('');
  const paramsHtml = renderParams(block.params, index, '', block.key);

  return `
    <div class="tpl-block card" data-index="${index}">
      <div class="tpl-block-header" onclick="toggleBlockAccordion(${index})">
        <span class="tpl-block-num">${index + 1}</span>
        <div class="tpl-block-info">
          <div class="tpl-block-title">${escHtml(block.title)}</div>
          <div class="tpl-block-desc">${escHtml(desc)}</div>
        </div>
        <span class="badge badge-${sevBadge}" id="sev-badge-${index}">${escHtml(sevLabel)}</span>
        <label class="switch" onclick="event.stopPropagation()">
          <input type="checkbox" ${block.enabled ? 'checked' : ''}
                 onchange="onBlockToggle(${index}, this.checked)">
          <span class="slider"></span>
        </label>
        <span class="tpl-block-chevron" id="block-chevron-${index}">${iconSvg('chevronDown', 16)}</span>
      </div>
      <div class="tpl-block-body" id="block-body-${index}" style="display:none">
        <div class="form-group">
          <label class="form-label">Строгость</label>
          <select class="form-select" onchange="onSeverityChange(${index}, this.value)">${sevOptions}</select>
          <div class="form-hint">Определяет, насколько серьёзно расценивается нарушение этого правила</div>
        </div>
        ${paramsHtml
          ? `<div class="tpl-params-section"><div class="form-label" style="margin-bottom:12px;font-size:14px">Параметры</div>${paramsHtml}</div>`
          : '<div class="form-hint" style="padding:8px 0">Нет настраиваемых параметров</div>'}
      </div>
    </div>`;
}

/* ---- Param Rendering ---- */
function renderParams(params, blockIndex, prefix, blockKey) {
  if (!params || Object.keys(params).length === 0) return '';
  return Object.entries(params).map(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return renderParamField(key, value, blockIndex, path, blockKey);
  }).join('');
}

function renderParamField(key, value, blockIndex, path, blockKey) {
  const special = getSpecialRenderer(blockKey, key, value, blockIndex, path);
  if (special) return special;

  const label = PARAM_LABELS[key] || key;
  const help = helpIcon(key);
  const fieldId = `blk-${blockIndex}-${path.replace(/\./g, '-')}`;

  if (typeof value === 'boolean') {
    return `<div class="toggle">
      <div class="toggle-info">
        <div class="toggle-title">${escHtml(label)}${help}</div>
      </div>
      <label class="switch">
        <input type="checkbox" id="${fieldId}" ${value ? 'checked' : ''}
               onchange="onParamChange(${blockIndex},'${path}',this.checked,'bool')">
        <span class="slider"></span>
      </label>
    </div>`;
  }
  if (typeof value === 'number') {
    return `<div class="form-group">
      <label class="form-label">${escHtml(label)}${help}</label>
      <input class="form-input" type="number" id="${fieldId}" value="${value}" step="any"
             onchange="onParamChange(${blockIndex},'${path}',this.value,'number')">
    </div>`;
  }
  if (typeof value === 'string') {
    return `<div class="form-group">
      <label class="form-label">${escHtml(label)}${help}</label>
      <input class="form-input" id="${fieldId}" value="${escHtml(value)}"
             onchange="onParamChange(${blockIndex},'${path}',this.value,'string')">
    </div>`;
  }
  if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
    const entries = Object.entries(value);
    const allSimple = entries.every(([, v]) =>
      typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean'
    );
    if (allSimple && entries.length <= 8) {
      const inner = entries.map(([k, v]) =>
        renderParamField(k, v, blockIndex, `${path}.${k}`, blockKey)
      ).join('');
      return `<fieldset class="tpl-param-group"><legend>${escHtml(label)}${help}</legend>${inner}</fieldset>`;
    }
  }
  return `<div class="form-group">
    <label class="form-label">${escHtml(label)}${help}</label>
    <input class="form-input" id="${fieldId}" value="${escHtml(String(value))}"
           onchange="onParamChange(${blockIndex},'${path}',this.value,'string')">
  </div>`;
}

/* ---- State Updates ---- */
function onBlockToggle(index, checked) {
  _editBlocks[index].enabled = checked;
}

function onSeverityChange(index, value) {
  _editBlocks[index].severity = value;
  const badge = document.getElementById(`sev-badge-${index}`);
  if (badge) {
    badge.textContent = SEVERITY_LABELS[value] || value;
    badge.className = `badge badge-${SEVERITY_BADGE[value] || 'gray'}`;
  }
}

function setNestedValue(obj, path, value) {
  const keys = path.split('.');
  let cur = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    if (!(keys[i] in cur)) cur[keys[i]] = {};
    cur = cur[keys[i]];
  }
  cur[keys[keys.length - 1]] = value;
}

function onParamChange(blockIndex, path, rawValue, type) {
  let value;
  switch (type) {
    case 'bool': value = !!rawValue; break;
    case 'number': value = parseFloat(rawValue); break;
    case 'array': value = rawValue.split(',').map(s => s.trim()).filter(Boolean); break;
    case 'raw': value = rawValue; break;
    default: value = rawValue;
  }
  setNestedValue(_editBlocks[blockIndex].params, path, value);
}

/* ---- Re-render a single block body (for section add/remove) ---- */
function rerenderBlockBody(blockIndex) {
  const block = _editBlocks[blockIndex];
  const body = document.getElementById(`block-body-${blockIndex}`);
  if (!body || !block) return;

  const sevOptions = SEVERITY_OPTIONS.map(o =>
    `<option value="${o.value}" ${block.severity === o.value ? 'selected' : ''}>${o.label}</option>`
  ).join('');
  const paramsHtml = renderParams(block.params, blockIndex, '', block.key);

  body.innerHTML = `
    <div class="form-group">
      <label class="form-label">Строгость</label>
      <select class="form-select" onchange="onSeverityChange(${blockIndex}, this.value)">${sevOptions}</select>
      <div class="form-hint">Определяет, насколько серьёзно расценивается нарушение этого правила</div>
    </div>
    ${paramsHtml
      ? `<div class="tpl-params-section"><div class="form-label" style="margin-bottom:12px;font-size:14px">Параметры</div>${paramsHtml}</div>`
      : '<div class="form-hint" style="padding:8px 0">Нет настраиваемых параметров</div>'}`;
  body.style.display = 'block';
}

/* ---- Accordion Toggles ---- */
function toggleBlockAccordion(index) {
  const body = document.getElementById(`block-body-${index}`);
  const chevron = document.getElementById(`block-chevron-${index}`);
  if (!body) return;
  const isOpen = body.style.display !== 'none';
  body.style.display = isOpen ? 'none' : 'block';
  if (chevron) chevron.style.transform = isOpen ? '' : 'rotate(180deg)';
}

function toggleMetaSection() {
  const body = document.getElementById('tpl-meta-body');
  const chevron = document.getElementById('meta-chevron');
  if (!body) return;
  const isOpen = body.style.display !== 'none';
  body.style.display = isOpen ? 'none' : 'block';
  if (chevron) chevron.style.transform = isOpen ? '' : 'rotate(180deg)';
}

/* ---- Save ---- */
async function saveTemplateChanges() {
  const metaPayload = {
    name: getVal('edit-tpl-name').trim(),
    university_id: parseInt(getVal('edit-tpl-uni')) || null,
    type_work: getVal('edit-tpl-type').trim(),
    year: getVal('edit-tpl-year').trim(),
    active: isChecked('edit-tpl-active'),
  };
  if (!metaPayload.name) { toast('Введите название шаблона', 'error'); return; }

  try {
    await api('PUT', `/templates/${_editTplId}`, metaPayload);
    await api('POST', `/templates/${_editTplId}/versions`, {
      rules: {
        blocks: _editBlocks.map(b => ({
          key: b.key,
          title: b.title,
          enabled: b.enabled,
          severity: b.severity,
          params: b.params || {},
        })),
      },
    });
    toast('Шаблон сохранён (новая версия создана)', 'success');
    loadTemplates();
  } catch (err) {
    toast('Ошибка: ' + err.message, 'error');
  }
}

function backToTemplateList() {
  _editTplId = null;
  _editBlocks = [];
  loadTemplates();
}

/* ---- Exports ---- */
window.helpIcon = helpIcon;
window.META_HINTS = META_HINTS;
window.openTemplateEditor = openTemplateEditor;
window.toggleBlockAccordion = toggleBlockAccordion;
window.toggleMetaSection = toggleMetaSection;
window.onBlockToggle = onBlockToggle;
window.onSeverityChange = onSeverityChange;
window.onParamChange = onParamChange;
window.saveTemplateChanges = saveTemplateChanges;
window.backToTemplateList = backToTemplateList;
window.rerenderBlockBody = rerenderBlockBody;
