(function () {
  'use strict';

  var appEl = document.getElementById('app');

  function pluralize(n, one, few, many) {
    var abs = Math.abs(n) % 100;
    var last = abs % 10;
    if (abs > 10 && abs < 20) return n + ' ' + many;
    if (last > 1 && last < 5) return n + ' ' + few;
    if (last === 1) return n + ' ' + one;
    return n + ' ' + many;
  }

  // ---- Auth ----

  var token = localStorage.getItem('miniapp_token');
  var currentUser = null;

  var tg = window.Telegram && window.Telegram.WebApp;
  if (tg) {
    tg.expand();
    tg.ready();
  }

  async function authenticateWithTelegram() {
    if (!tg || !tg.initData) return false;
    try {
      var res = await fetch('/api/auth/telegram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ init_data: tg.initData }),
      });
      if (res.ok) {
        var data = await res.json();
        token = data.access_token;
        localStorage.setItem('miniapp_token', token);
        return true;
      }
    } catch (_) {}
    return false;
  }

  async function ensureAuth() {
    if (token) return;
    await authenticateWithTelegram();
  }

  function apiError(status, detail) {
    var err = new Error(detail);
    err.status = status;
    return err;
  }

  async function api(path) {
    var headers = {};
    if (token) headers['Authorization'] = 'Bearer ' + token;
    var res = await fetch('/api' + path, { headers: headers });
    if (!res.ok) {
      var detail = 'HTTP ' + res.status;
      try { var body = await res.json(); if (body.detail) detail = body.detail; } catch (_) {}
      throw apiError(res.status, detail);
    }
    return res.json();
  }

  async function apiPost(path, body) {
    var headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    var res = await fetch('/api' + path, { method: 'POST', headers: headers, body: JSON.stringify(body) });
    if (!res.ok) {
      var detail = 'HTTP ' + res.status;
      try { var b = await res.json(); if (b.detail) detail = b.detail; } catch (_) {}
      throw apiError(res.status, detail);
    }
    return res.json();
  }

  async function apiUpload(path, formData) {
    var headers = {};
    if (token) headers['Authorization'] = 'Bearer ' + token;
    var res = await fetch('/api' + path, { method: 'POST', headers: headers, body: formData });
    if (!res.ok) {
      var detail = 'HTTP ' + res.status;
      try { var b = await res.json(); if (b.detail) detail = b.detail; } catch (_) {}
      throw apiError(res.status, detail);
    }
    return res.json();
  }

  async function getMe() {
    if (!currentUser) {
      try {
        currentUser = await api('/auth/me');
      } catch (e) {
        if (e.status === 401 || e.status === 403) {
          token = null;
          localStorage.removeItem('miniapp_token');
          currentUser = null;
          if (await authenticateWithTelegram()) {
            try { currentUser = await api('/auth/me'); } catch (_) {}
          }
        }
      }
    }
    return currentUser;
  }

  // ---- Utils ----

  function fmtDate(iso) {
    if (!iso) return '\u2014';
    return new Date(iso).toLocaleString('ru-RU', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false,
    });
  }

  function statusLabel(s) {
    return { queued: 'В очереди', running: 'Проверяется', done: 'Готово',
      error: 'Ошибка', pending: 'Ожидание', paid: 'Оплачено',
      failed: 'Ошибка', cancelled: 'Отменён' }[s] || s;
  }

  function statusCls(s) {
    if (s === 'done' || s === 'paid') return 'fixed';
    if (s === 'error' || s === 'failed' || s === 'cancelled') return 'error';
    return 'warning';
  }

  function icons() { if (window.lucide) lucide.createIcons(); }

  function esc(str) {
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  var _pageTimer = null;
  function clearPageTimer() {
    if (_pageTimer) { clearTimeout(_pageTimer); _pageTimer = null; }
  }

  function dlUrl(fileId) {
    return '/api/files/' + fileId + '/download?token=' + encodeURIComponent(token || '');
  }

  /** Русские подписи для отчёта проверки (серьёзность и категория из rules engine). */
  var REPORT_SEVERITY_RU = {
    error: 'Ошибка',
    warning: 'Предупреждение',
    advice: 'Совет',
    off: 'Не проверялось',
  };

  var REPORT_CATEGORY_RU = {
    internal: 'Система',
    file: 'Файл',
    integrity: 'Целостность документа',
    context_extraction: 'Определение курса и авторов',
    work_formats: 'Формат работы',
    layout: 'Поля и страница',
    typography: 'Шрифт и абзацы',
    structure: 'Структура работы',
    volume: 'Объём текста',
    bibliography: 'Список источников',
    footnotes: 'Сноски',
    objects: 'Таблицы и рисунки',
    heading_formatting: 'Заголовки',
    page_numbering: 'Нумерация страниц',
    toc: 'Оглавление',
    captions: 'Подписи к объектам',
    autofix: 'Автоисправление',
    summary: 'Итог',
  };

  function findingSeverityRu(sev) {
    return (sev && REPORT_SEVERITY_RU[sev]) || sev || '';
  }

  function findingCategoryRu(cat) {
    if (!cat) return '';
    return REPORT_CATEGORY_RU[cat] || cat;
  }

  function findingSeverityChipClass(sev) {
    if (sev === 'error') return 'error';
    if (sev === 'warning') return 'warning';
    if (sev === 'advice') return 'advice';
    return 'fixed';
  }

  function renderReport(report) {
    if (!report || !report.findings || !report.findings.length) return '';
    return '<div class="section-label" style="margin-top:14px">Замечания</div>' +
      '<div class="chips" style="margin-bottom:8px">' +
        '<span class="chip error">' + report.summary_errors + ' ошибок</span>' +
        '<span class="chip warning">' + report.summary_warnings + ' предупр.</span>' +
        '<span class="chip fixed">' + report.summary_autofixed + ' исправлено</span>' +
      '</div>' +
      report.findings.map(function (f) {
        var catRu = findingCategoryRu(f.category);
        return '<div class="glass list-card finding-item">' +
          '<div class="list-card-row">' +
            '<span class="chip ' + findingSeverityChipClass(f.severity) + '">' + esc(findingSeverityRu(f.severity)) + '</span>' +
            (catRu ? '<span style="font-size:11px;color:var(--text-muted)">' + esc(catRu) + '</span>' : '') +
          '</div>' +
          '<div class="finding-title">' + esc(f.title) + '</div>' +
          (f.expected ? '<div class="finding-rec">Ожидалось: ' + esc(f.expected) + '</div>' : '') +
          (f.found ? '<div class="finding-rec" style="color:var(--text-muted)">Факт: ' + esc(f.found) + '</div>' : '') +
          (f.recommendation ? '<div class="finding-rec">' + esc(f.recommendation) + '</div>' : '') +
        '</div>';
      }).join('');
  }

  // ---- Toast ----

  var _toastContainer = null;

  function showToast(msg, type) {
    if (!_toastContainer) {
      _toastContainer = document.createElement('div');
      _toastContainer.className = 'toast-container';
      document.body.appendChild(_toastContainer);
    }
    var iconName = type === 'success' ? 'check-circle-2' : type === 'error' ? 'alert-circle' : 'info';
    var el = document.createElement('div');
    el.className = 'toast ' + (type || 'info');
    el.innerHTML = '<i data-lucide="' + iconName + '"></i><span>' + esc(msg) + '</span>';
    _toastContainer.appendChild(el);
    icons();
    setTimeout(function () {
      el.classList.add('toast-exit');
      setTimeout(function () { el.remove(); }, 300);
    }, 4000);
  }

  // ---- Balance live-update ----

  function refreshBalanceUI(newCredits) {
    if (newCredits == null) return;
    var statVal = document.querySelector('.stat-value');
    if (statVal) statVal.textContent = newCredits;
    var bannerVal = document.querySelector('.credits-banner-value');
    if (bannerVal) bannerVal.textContent = newCredits;
    var bannerLabel = document.querySelector('.credits-banner-label');
    if (bannerLabel) {
      bannerLabel.textContent =
        pluralize(newCredits, 'проверка', 'проверки', 'проверок').replace(/^\d+\s/, '') + ' доступно';
    }
  }

  var _paymentPollTimer = null;
  var _paymentPollStart = 0;
  var PAYMENT_POLL_TIMEOUT = 10 * 60 * 1000;

  function stopPaymentPoll() {
    if (_paymentPollTimer) { clearTimeout(_paymentPollTimer); _paymentPollTimer = null; }
  }

  function pollOrderStatus(orderId) {
    stopPaymentPoll();
    _paymentPollStart = Date.now();

    async function tick() {
      if (Date.now() - _paymentPollStart > PAYMENT_POLL_TIMEOUT) {
        stopPaymentPoll();
        return;
      }
      try {
        var res = await api('/orders/' + orderId + '/status');
        if (res.status === 'paid') {
          stopPaymentPoll();
          currentUser = null;
          var me = await getMe();
          var added = res.credits_added || 0;
          showToast(
            'Оплата прошла! +' + pluralize(added, 'проверка', 'проверки', 'проверок'),
            'success'
          );
          refreshBalanceUI(me ? me.credits_available : null);
          return;
        }
      } catch (_) {}
      _paymentPollTimer = setTimeout(tick, 3000);
    }

    tick();
  }

  // ---- Visibility change — refresh balance on tab focus ----

  var _visDebounce = null;
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) return;
    if (_visDebounce) clearTimeout(_visDebounce);
    _visDebounce = setTimeout(async function () {
      var oldCredits = currentUser ? currentUser.credits_available : null;
      currentUser = null;
      var me = await getMe();
      if (me && oldCredits != null && me.credits_available !== oldCredits) {
        var diff = me.credits_available - oldCredits;
        if (diff > 0) {
          showToast(
            'Баланс обновлён: +' + pluralize(diff, 'проверка', 'проверки', 'проверок'),
            'success'
          );
        }
        refreshBalanceUI(me.credits_available);
      }
    }, 1000);
  });

  // ---- Router ----

  var _routes = [];

  function updateNav(path) {
    document.querySelectorAll('#bottom-nav a').forEach(function (a) {
      var href = a.getAttribute('href');
      var active = path === href || (href === '/history' && path.indexOf('/checks/') === 0);
      a.classList.toggle('active', active);
    });
  }

  async function navigate(path, push) {
    clearPageTimer();
    if (push) history.pushState(null, '', path);
    updateNav(path);
    for (var i = 0; i < _routes.length; i++) {
      var m = path.match(_routes[i].re);
      if (m) { await _routes[i].fn(m); return; }
    }
    if (_routes.length && _routes[0].fn) await _routes[0].fn(['/']);
  }

  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href');
    if (!href || href.indexOf('http') === 0 || href.charAt(0) === '#' || href.indexOf('/api/') === 0) return;
    if (a.hasAttribute('download') || a.target === '_blank') return;
    e.preventDefault();
    navigate(href, true);
  });

  window.addEventListener('popstate', function () { navigate(location.pathname, false); });

  // ---- Public API for pages.js ----

  window.App = {
    el: appEl,
    api: api,
    apiPost: apiPost,
    apiUpload: apiUpload,
    getMe: getMe,
    resetUser: function () { currentUser = null; },
    icons: icons,
    esc: esc,
    fmtDate: fmtDate,
    statusLabel: statusLabel,
    statusCls: statusCls,
    dlUrl: dlUrl,
    renderReport: renderReport,
    pluralize: pluralize,
    navigate: navigate,
    tg: tg,
    showToast: showToast,
    pollOrderStatus: pollOrderStatus,
    refreshBalanceUI: refreshBalanceUI,
    setPageTimer: function (t) { _pageTimer = t; },
    clearPageTimer: clearPageTimer,
    start: function (routes) {
      _routes = routes;
      ensureAuth().then(function () { navigate(location.pathname, false); });
    },
  };
})();
