/* Core module — API client, navigation, helpers, toast, modal */

const API = '/api';
const TOKEN_KEY = 'admin_token';

function getToken() { return localStorage.getItem(TOKEN_KEY) || ''; }
function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }
function clearToken() { localStorage.removeItem(TOKEN_KEY); }

function headers() {
  return { 'Content-Type': 'application/json', Authorization: 'Bearer ' + getToken() };
}

async function api(method, path, body, _retries = 1) {
  const opts = { method, headers: headers() };
  if (body !== undefined) opts.body = JSON.stringify(body);
  let res;
  try {
    res = await fetch(API + path, opts);
  } catch (netErr) {
    if (_retries > 0) {
      await new Promise(r => setTimeout(r, 1500));
      return api(method, path, body, _retries - 1);
    }
    throw new Error('Сервер недоступен. Проверьте соединение и попробуйте снова.');
  }
  if (res.status === 401) {
    clearToken();
    showLoginModal();
    throw new Error('Требуется авторизация');
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.headers.get('content-length') === '0') return {};
  return res.json();
}

/* ---- Navigation ---- */
const pageLoaders = {};

function registerPage(id, loader) {
  pageLoaders[id] = loader;
}

function navigateTo(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(a => a.classList.remove('active'));

  const page = document.getElementById('page-' + pageId);
  if (page) page.classList.add('active');

  const link = document.querySelector(`.nav-link[data-page="${pageId}"]`);
  if (link) link.classList.add('active');

  const topTitle = document.getElementById('topbar-title');
  if (topTitle && link) topTitle.textContent = link.dataset.label || link.textContent.trim();

  if (location.hash !== '#' + pageId) history.replaceState(null, '', '#' + pageId);

  if (pageLoaders[pageId]) pageLoaders[pageId]();

  if (window.onboardingCheck) onboardingCheck(pageId);

  closeSidebar();
}

document.addEventListener('click', e => {
  const a = e.target.closest('.nav-link[data-page]');
  if (!a) return;
  e.preventDefault();
  navigateTo(a.dataset.page);
});

/* ---- Mobile Sidebar ---- */
function openSidebar() {
  document.querySelector('.sidebar')?.classList.add('open');
  document.querySelector('.sidebar-overlay')?.classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeSidebar() {
  document.querySelector('.sidebar')?.classList.remove('open');
  document.querySelector('.sidebar-overlay')?.classList.remove('active');
  document.body.style.overflow = '';
}

/* ---- Toast ---- */
let toastContainer;
function ensureToastContainer() {
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container';
    document.body.appendChild(toastContainer);
  }
}

function toast(msg, type = 'info') {
  ensureToastContainer();
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  toastContainer.appendChild(el);
  setTimeout(() => {
    el.classList.add('toast-exit');
    el.addEventListener('animationend', () => el.remove());
  }, 3500);
}

/* ---- Modal ---- */
function openModal(title, bodyHtml, footerHtml) {
  closeModal();
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'active-modal';
  overlay.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <h3 class="modal-title">${title}</h3>
        <button class="modal-close" onclick="closeModal()">${iconSvg('x')}</button>
      </div>
      <div class="modal-body">${bodyHtml}</div>
      ${footerHtml ? `<div class="modal-footer">${footerHtml}</div>` : ''}
    </div>`;
  overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });
  document.body.appendChild(overlay);
}

function closeModal() {
  document.getElementById('active-modal')?.remove();
}

/* ---- Login Modal ---- */
function showLoginModal() {
  const body = `
    <div class="form-group">
      <label class="form-label">Логин</label>
      <input class="form-input" id="login-user" autocomplete="username">
    </div>
    <div class="form-group">
      <label class="form-label">Пароль</label>
      <input class="form-input" id="login-pass" type="password" autocomplete="current-password">
    </div>
    <div id="login-error" class="alert error" style="display:none"></div>`;
  const footer = `<button class="btn btn-primary" onclick="doLogin()">Войти</button>`;
  openModal('Авторизация', body, footer);
}

async function doLogin() {
  const login = document.getElementById('login-user')?.value;
  const password = document.getElementById('login-pass')?.value;
  const errEl = document.getElementById('login-error');
  try {
    const data = await fetch(API + '/admin/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ login, password }),
    }).then(r => {
      if (!r.ok) throw new Error('Неверный логин или пароль');
      return r.json();
    });
    setToken(data.access_token);
    closeModal();
    toast('Авторизация успешна', 'success');
    navigateTo('dashboard');
  } catch (err) {
    if (errEl) {
      errEl.style.display = 'flex';
      errEl.textContent = err.message;
    }
  }
}

/* ---- DOM Helpers ---- */
function $(id) { return document.getElementById(id); }
function setChecked(id, val) { const el = $(id); if (el) el.checked = !!val; }
function isChecked(id) { const el = $(id); return el ? el.checked : false; }
function setVal(id, val) { const el = $(id); if (el) el.value = val ?? ''; }
function getVal(id) { const el = $(id); return el ? el.value : ''; }
function setText(id, val) { const el = $(id); if (el) el.textContent = val ?? '—'; }

function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour12: false })
    + ' ' + d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', hour12: false });
}

const ACTION_LABELS = {
  'content.menu.create':    'Создание пункта меню',
  'content.menu.update':    'Обновление пункта меню',
  'content.menu.delete':    'Удаление пункта меню',
  'content.menu.reorder':   'Изменение порядка меню',
  'content.text.upsert':    'Обновление текста бота',
  'content.upsert':         'Обновление контента',
  'content.message.create': 'Создание сообщения',
  'content.message.update': 'Обновление сообщения',
  'content.message.delete': 'Удаление сообщения',
  'content.message.reorder':'Изменение порядка сообщений',
  'template.create':        'Создание шаблона',
  'template.version.create':'Новая версия шаблона',
  'template.update':        'Обновление шаблона',
  'template.publish':       'Публикация шаблона',
  'product.create':         'Создание продукта',
  'product.update':         'Обновление продукта',
  'product.delete':         'Удаление продукта',
  'update':                 'Обновление настроек',
};

const ENTITY_LABELS = {
  'content_menu_item':   'Пункт меню',
  'content_menu':        'Меню',
  'bot_content':         'Контент бота',
  'menu_item_message':   'Сообщение',
  'template':            'Шаблон',
  'product':             'Продукт',
  'system_settings':     'Системные настройки',
  'user':                'Пользователь',
  'university':          'ВУЗ',
  'gost':                'ГОСТ',
  'order':               'Заказ',
  'check':               'Проверка',
  'demo':                'Демо',
};

function humanAction(action) {
  return ACTION_LABELS[action] || action;
}

function humanEntity(entityType) {
  return ENTITY_LABELS[entityType] || entityType;
}

function statusBadge(status) {
  const map = {
    paid: ['Оплачен', 'success'], created: ['Создан', 'info'],
    failed: ['Ошибка', 'danger'], cancelled: ['Отменён', 'gray'],
    queued: ['В очереди', 'info'], running: ['Выполняется', 'warn'],
    done: ['Готово', 'success'], error: ['Ошибка', 'danger'],
    draft: ['Черновик', 'gray'], published: ['Опубликован', 'success'],
  };
  const [label, cls] = map[status] || [status, 'gray'];
  return `<span class="badge badge-${cls}">${escHtml(label)}</span>`;
}

function loadingHtml() {
  return '<div class="loading-center"><div class="spinner"></div>Загрузка…</div>';
}

function emptyHtml(title, desc) {
  return `<div class="empty-state">
    ${iconSvg('inbox', 48)}
    <div class="empty-title">${title}</div>
    <div class="empty-desc">${desc || ''}</div>
  </div>`;
}

/* ---- Icon Helper ---- */
const ICONS = {
  x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  edit: '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4Z"/>',
  trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  search: '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  inbox: '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
  coins: '<circle cx="8" cy="8" r="6"/><path d="M18.09 10.37A6 6 0 1 1 10.34 18"/><path d="M7 6h1v4"/><path d="m16.71 13.88.7.71-2.82 2.82"/>',
  menu: '<line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="18" x2="20" y2="18"/>',
  chevronDown: '<polyline points="6 9 12 15 18 9"/>',
  arrowLeft: '<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>',
  save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
  refresh: '<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
  chevronLeft: '<polyline points="15 18 9 12 15 6"/>',
  chevronRight: '<polyline points="9 18 15 12 9 6"/>',
  fileCheck: '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><path d="m9 15 2 2 4-4"/>',
};

function iconSvg(name, size = 18) {
  const inner = ICONS[name] || '';
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${inner}</svg>`;
}

/* ---- Pagination ---- */
const DEFAULT_PER_PAGE = 20;

function paginate(list, page, perPage) {
  perPage = perPage || DEFAULT_PER_PAGE;
  const total = list.length;
  const totalPages = Math.ceil(total / perPage) || 1;
  const safePage = Math.max(1, Math.min(page, totalPages));
  const start = (safePage - 1) * perPage;
  return { items: list.slice(start, start + perPage), total, totalPages, page: safePage, perPage };
}

function paginationHtml(paged, callbackName) {
  if (paged.totalPages <= 1) return '';
  const { page, totalPages, total } = paged;
  const pages = [];
  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || (i >= page - 2 && i <= page + 2)) {
      pages.push(i);
    } else if (pages.length && pages[pages.length - 1] !== '…') {
      pages.push('…');
    }
  }
  return `<div class="pagination">
    <button class="pg-btn" ${page <= 1 ? 'disabled' : `onclick="${callbackName}(${page - 1})"`}>${iconSvg('chevronLeft', 14)}</button>
    ${pages.map(p => p === '…'
      ? '<span class="pg-dots">…</span>'
      : `<button class="pg-btn${p === page ? ' active' : ''}" onclick="${callbackName}(${p})">${p}</button>`
    ).join('')}
    <button class="pg-btn" ${page >= totalPages ? 'disabled' : `onclick="${callbackName}(${page + 1})"`}>${iconSvg('chevronRight', 14)}</button>
    <span class="pg-info">${total} записей</span>
  </div>`;
}

/* ---- Entity Tag ---- */
function entityTag(type, id, label) {
  if (!id && !label) return '—';
  const display = label || '#' + id;
  if (!id) return `<span class="entity-tag entity-tag-${escHtml(type)}">${escHtml(display)}</span>`;
  return `<span class="entity-tag entity-tag-${escHtml(type)}" onclick="goToEntity('${escHtml(type)}',${id})" title="${escHtml(humanEntity(type))} #${id}">${escHtml(display)}</span>`;
}

function goToEntity(type, id) {
  const map = { user:'users', university:'universities', gost:'gosts', order:'orders', check:'checks', product:'products', template:'templates' };
  if (!map[type]) return;
  navigateTo(map[type]);
  if (!id) return;
  const fn = { user: 'viewUserDetail', order: 'viewOrder', check: 'viewCheck' };
  if (fn[type] && window[fn[type]]) setTimeout(() => window[fn[type]](id), 150);
}

/* ---- Init ---- */
function getPageFromHash() {
  const id = location.hash.replace('#', '');
  return document.getElementById('page-' + id) ? id : 'dashboard';
}

document.addEventListener('DOMContentLoaded', () => {
  if (!getToken()) showLoginModal();
  else navigateTo(getPageFromHash());
});

window.addEventListener('hashchange', () => {
  if (getToken()) navigateTo(getPageFromHash());
});

async function apiUpload(method, path, formData) {
  const opts = {
    method,
    headers: { Authorization: 'Bearer ' + getToken() },
    body: formData,
  };
  const res = await fetch(API + path, opts);
  if (res.status === 401) { clearToken(); showLoginModal(); throw new Error('Требуется авторизация'); }
  if (!res.ok) { const text = await res.text(); throw new Error(text || res.statusText); }
  if (res.headers.get('content-length') === '0') return {};
  return res.json();
}

/* expose globally */
window.api = api;
window.apiUpload = apiUpload;
window.navigateTo = navigateTo;
window.openSidebar = openSidebar;
window.closeSidebar = closeSidebar;
window.toast = toast;
window.openModal = openModal;
window.closeModal = closeModal;
window.doLogin = doLogin;
window.showLoginModal = showLoginModal;
window.registerPage = registerPage;
window.$ = $;
window.setChecked = setChecked;
window.isChecked = isChecked;
window.setVal = setVal;
window.getVal = getVal;
window.setText = setText;
window.escHtml = escHtml;
window.formatDate = formatDate;
window.statusBadge = statusBadge;
window.loadingHtml = loadingHtml;
window.emptyHtml = emptyHtml;
window.iconSvg = iconSvg;
window.humanAction = humanAction;
window.humanEntity = humanEntity;
window.paginate = paginate;
window.paginationHtml = paginationHtml;
window.entityTag = entityTag;
window.goToEntity = goToEntity;
