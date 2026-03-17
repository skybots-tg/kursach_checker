(function () {
  'use strict';

  var appEl = document.getElementById('app');

  // ---- Auth ----

  var token = localStorage.getItem('miniapp_token');
  var currentUser = null;

  async function ensureAuth() {
    if (token) return;
    var tg = window.Telegram && window.Telegram.WebApp;
    if (!tg || !tg.initData) return;
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
      }
    } catch (_) {}
  }

  async function api(path) {
    var headers = {};
    if (token) headers['Authorization'] = 'Bearer ' + token;
    var res = await fetch('/api' + path, { headers: headers });
    if (!res.ok) {
      var detail = 'HTTP ' + res.status;
      try { var body = await res.json(); if (body.detail) detail = body.detail; } catch (_) {}
      throw new Error(detail);
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
      throw new Error(detail);
    }
    return res.json();
  }

  async function getMe() {
    if (!currentUser) {
      try { currentUser = await api('/auth/me'); } catch (_) {}
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

  // ---- Page: Home ----

  async function pageHome() {
    document.title = 'Проверка оформления';
    var me = await getMe();
    var credits = me ? me.credits_available : '\u2014';
    var name = me ? (me.username || me.first_name || 'ID ' + me.telegram_id) : '\u2014';
    appEl.innerHTML =
      '<section class="glass hero">' +
        '<div class="hero-icon"><i data-lucide="file-search"></i></div>' +
        '<h1 class="gradient-text">Проверка оформления</h1>' +
        '<p>Загрузите DOCX \u2014 получите подробный отчёт по ГОСТу и методичке вуза за секунды</p>' +
      '</section>' +
      '<div class="stats-row">' +
        '<div class="stat-card accent">' +
          '<div class="stat-icon"><i data-lucide="zap"></i></div>' +
          '<div class="stat-value">' + credits + '</div>' +
          '<div class="stat-label">Доступно проверок</div>' +
        '</div>' +
        '<div class="stat-card">' +
          '<div class="stat-icon"><i data-lucide="user"></i></div>' +
          '<div class="stat-value stat-value-sm">' + esc(name) + '</div>' +
          '<div class="stat-label">Telegram</div>' +
        '</div>' +
      '</div>' +
      '<div class="section-label">Как это работает</div>' +
      '<section class="glass steps-list">' +
        '<div class="step"><div class="step-num">1</div><div class="step-body"><div class="step-title">Загрузите файл</div><div class="step-desc">Курсовая или ВКР в формате DOCX</div></div></div>' +
        '<div class="step"><div class="step-num">2</div><div class="step-body"><div class="step-title">Автопроверка</div><div class="step-desc">Система проверяет оформление по правилам</div></div></div>' +
        '<div class="step"><div class="step-num">3</div><div class="step-body"><div class="step-title">Получите отчёт</div><div class="step-desc">Подробный список замечаний с рекомендациями</div></div></div>' +
      '</section>' +
      '<div class="btn-group">' +
        '<a href="/check" class="btn btn-primary"><i data-lucide="sparkles"></i> Начать проверку <i data-lucide="arrow-right" style="opacity:.6"></i></a>' +
        '<a href="/demo" class="btn btn-secondary"><i data-lucide="play"></i> Посмотреть демо-отчёт</a>' +
      '</div>' +
      '<div class="section-label">Преимущества</div>' +
      '<section class="glass features-list">' +
        '<div class="feature-row"><div class="feature-icon blue"><i data-lucide="shield-check"></i></div><div class="feature-text"><div class="feature-title">По ГОСТу</div><div class="feature-desc">Проверка по актуальным стандартам</div></div></div>' +
        '<div class="feature-row"><div class="feature-icon green"><i data-lucide="zap"></i></div><div class="feature-text"><div class="feature-title">Быстро</div><div class="feature-desc">Результат за несколько секунд</div></div></div>' +
        '<div class="feature-row"><div class="feature-icon purple"><i data-lucide="graduation-cap"></i></div><div class="feature-text"><div class="feature-title">По методичке</div><div class="feature-desc">Правила именно вашего вуза</div></div></div>' +
      '</section>';
    icons();
  }

  // ---- Page: History ----

  async function pageHistory() {
    document.title = 'История — Проверка оформления';
    appEl.innerHTML =
      '<div class="section-label">История</div>' +
      '<div class="page-tabs">' +
        '<button class="tab-btn active" data-tab="checks">Проверки</button>' +
        '<button class="tab-btn" data-tab="orders">Оплаты</button>' +
      '</div>' +
      '<div id="tab-content"><div class="loading-spinner"><i data-lucide="loader-2" class="spin"></i><span>Загрузка\u2026</span></div></div>';
    icons();

    var checks = [], orders = [];
    try {
      var results = await Promise.all([api('/checks'), api('/orders')]);
      checks = results[0];
      orders = results[1];
    } catch (e) {
      document.getElementById('tab-content').innerHTML =
        '<div class="empty-state glass"><i data-lucide="alert-circle"></i><p>' + esc(e.message) + '</p></div>';
      icons();
      return;
    }

    var tabContent = document.getElementById('tab-content');
    var tabBtns = appEl.querySelectorAll('.tab-btn');

    function showTab(tab) {
      tabBtns.forEach(function (b) { b.classList.toggle('active', b.dataset.tab === tab); });
      if (tab === 'checks') {
        if (!checks.length) {
          tabContent.innerHTML = '<div class="empty-state glass"><i data-lucide="inbox"></i><p>Проверок пока не было</p></div>';
        } else {
          tabContent.innerHTML = checks.map(function (c) {
            return '<a href="/checks/' + c.id + '" class="glass list-card">' +
              '<div class="list-card-row">' +
                '<span class="list-card-title">Проверка #' + c.id + '</span>' +
                '<span class="chip ' + statusCls(c.status) + '">' + statusLabel(c.status) + '</span>' +
              '</div>' +
              '<div class="list-card-meta">Создано: ' + fmtDate(c.created_at) +
                (c.finished_at ? ' \xB7 Завершено: ' + fmtDate(c.finished_at) : '') +
              '</div>' +
            '</a>';
          }).join('');
        }
      } else {
        if (!orders.length) {
          tabContent.innerHTML = '<div class="empty-state glass"><i data-lucide="inbox"></i><p>Оплат пока не было</p></div>';
        } else {
          tabContent.innerHTML = orders.map(function (o) {
            return '<div class="glass list-card">' +
              '<div class="list-card-row">' +
                '<span class="list-card-title">' + esc(o.product || 'Заказ #' + o.id) + '</span>' +
                '<span class="chip ' + statusCls(o.status) + '">' + statusLabel(o.status) + '</span>' +
              '</div>' +
              '<div class="list-card-meta">' + o.amount + ' \u20BD \xB7 ' + fmtDate(o.created_at) +
                (o.paid_at ? ' \xB7 Оплачено: ' + fmtDate(o.paid_at) : '') +
              '</div>' +
            '</div>';
          }).join('');
        }
      }
      icons();
    }

    tabBtns.forEach(function (btn) { btn.addEventListener('click', function () { showTab(btn.dataset.tab); }); });
    showTab('checks');
  }

  // ---- Page: Profile ----

  async function pageProfile() {
    document.title = 'Профиль — Проверка оформления';
    appEl.innerHTML = '<div class="loading-spinner"><i data-lucide="loader-2" class="spin"></i><span>Загрузка\u2026</span></div>';
    icons();

    var me = await getMe();
    if (!me) {
      appEl.innerHTML = '<div class="empty-state glass"><i data-lucide="user-x"></i><p>Не удалось загрузить профиль</p></div>';
      icons();
      return;
    }

    var products = [];
    try { products = await api('/products'); } catch (_) {}

    var displayName = me.first_name
      ? esc(me.first_name) + (me.username ? ' (@' + esc(me.username) + ')' : '')
      : esc(me.username || 'Пользователь');

    var productsHtml = '';
    if (products.length) {
      productsHtml =
        '<div class="section-label">Пополнить баланс</div>' +
        products.map(function (p) {
          return '<div class="glass list-card product-card">' +
            '<div class="list-card-row">' +
              '<span class="list-card-title">' + esc(p.name) + '</span>' +
              '<span class="product-price">' + p.price + ' ' + esc(p.currency || '\u20BD') + '</span>' +
            '</div>' +
            '<div class="list-card-meta">' + p.credits_amount + ' проверок' +
              (p.description ? ' \xB7 ' + esc(p.description) : '') +
            '</div>' +
            '<button class="btn btn-primary btn-sm" data-buy="' + p.id + '">' +
              '<i data-lucide="credit-card"></i> Оплатить' +
            '</button>' +
          '</div>';
        }).join('');
    }

    appEl.innerHTML =
      '<div class="section-label">Профиль</div>' +
      '<section class="glass profile-card">' +
        '<div class="profile-avatar"><i data-lucide="user"></i></div>' +
        '<div class="profile-name">' + displayName + '</div>' +
        '<div class="profile-sub">Telegram ID: ' + me.telegram_id + '</div>' +
      '</section>' +
      '<div class="stats-row">' +
        '<div class="stat-card accent" style="grid-column:1/-1">' +
          '<div class="stat-icon"><i data-lucide="zap"></i></div>' +
          '<div class="stat-value">' + (me.credits_available != null ? me.credits_available : 0) + '</div>' +
          '<div class="stat-label">Доступно проверок</div>' +
        '</div>' +
      '</div>' +
      productsHtml +
      '<div class="section-label">Поддержка</div>' +
      '<section class="glass" style="padding:16px">' +
        '<p style="font-size:13px;color:var(--text-secondary);margin:0">' +
          'Если что-то пошло не так с оплатой или проверкой, напишите в поддержку через Telegram\u2011бота.' +
        '</p>' +
      '</section>';

    appEl.querySelectorAll('[data-buy]').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        var productId = Number(btn.dataset.buy);
        btn.disabled = true;
        btn.textContent = 'Переходим\u2026';
        try {
          var res = await apiPost('/payments/create', { product_id: productId });
          if (res.payment_url) window.open(res.payment_url, '_blank');
        } catch (e) {
          alert('Ошибка: ' + e.message);
        } finally {
          btn.disabled = false;
          btn.innerHTML = '<i data-lucide="credit-card"></i> Оплатить';
          icons();
        }
      });
    });
    icons();
  }

  // ---- Page: Check (stub) ----

  async function pageCheck() {
    document.title = 'Новая проверка — Проверка оформления';
    appEl.innerHTML =
      '<div class="section-label">Новая проверка</div>' +
      '<section class="glass" style="padding:24px;text-align:center">' +
        '<div class="hero-icon"><i data-lucide="upload"></i></div>' +
        '<p style="color:var(--text-secondary);margin:12px 0 0">Загрузка файла для проверки</p>' +
        '<p style="color:var(--text-muted);font-size:13px;margin:4px 0 0">Страница в разработке</p>' +
      '</section>';
    icons();
  }

  // ---- Page: Demo (stub) ----

  async function pageDemo() {
    document.title = 'Демо-отчёт — Проверка оформления';
    appEl.innerHTML =
      '<div class="section-label">Демо-отчёт</div>' +
      '<section class="glass" style="padding:24px;text-align:center">' +
        '<div class="hero-icon"><i data-lucide="play"></i></div>' +
        '<p style="color:var(--text-secondary);margin:12px 0 0">Пример результата проверки</p>' +
        '<p style="color:var(--text-muted);font-size:13px;margin:4px 0 0">Страница в разработке</p>' +
      '</section>';
    icons();
  }

  // ---- Page: Check Result ----

  async function pageCheckResult(id) {
    document.title = 'Результат #' + id + ' — Проверка оформления';
    appEl.innerHTML = '<div class="loading-spinner"><i data-lucide="loader-2" class="spin"></i><span>Загрузка\u2026</span></div>';
    icons();

    try {
      var check = await api('/checks/' + id);
      var reportHtml = '';
      if (check.report && check.report.findings && check.report.findings.length) {
        reportHtml =
          '<div class="section-label" style="margin-top:14px">Замечания</div>' +
          '<div class="chips" style="margin-bottom:8px">' +
            '<span class="chip error">' + check.report.summary_errors + ' ошибок</span>' +
            '<span class="chip warning">' + check.report.summary_warnings + ' предупр.</span>' +
            '<span class="chip fixed">' + check.report.summary_autofixed + ' исправлено</span>' +
          '</div>' +
          check.report.findings.map(function (f) {
            return '<div class="glass list-card finding-item">' +
              '<div class="list-card-row">' +
                '<span class="chip ' + (f.severity === 'error' ? 'error' : f.severity === 'warning' ? 'warning' : 'fixed') + '">' + esc(f.severity) + '</span>' +
                '<span style="font-size:11px;color:var(--text-muted)">' + esc(f.category || '') + '</span>' +
              '</div>' +
              '<div class="finding-title">' + esc(f.title || f.rule_id) + '</div>' +
              (f.recommendation ? '<div class="finding-rec">' + esc(f.recommendation) + '</div>' : '') +
            '</div>';
          }).join('');
      }

      appEl.innerHTML =
        '<div class="section-label">Результат проверки #' + check.id + '</div>' +
        '<section class="glass list-card">' +
          '<div class="list-card-row">' +
            '<span class="list-card-title">Проверка #' + check.id + '</span>' +
            '<span class="chip ' + statusCls(check.status) + '">' + statusLabel(check.status) + '</span>' +
          '</div>' +
          '<div class="list-card-meta">' +
            'Создано: ' + fmtDate(check.created_at) +
            (check.finished_at ? ' \xB7 Завершено: ' + fmtDate(check.finished_at) : '') +
          '</div>' +
          (check.output_file_id
            ? '<a href="/api/files/' + check.output_file_id + '/download" target="_blank" class="btn btn-secondary btn-sm" style="margin-top:10px"><i data-lucide="download"></i> Скачать исправленный</a>'
            : '') +
        '</section>' +
        reportHtml +
        '<a href="/history" class="btn btn-secondary" style="margin-top:10px"><i data-lucide="arrow-left"></i> Назад к истории</a>';
    } catch (e) {
      appEl.innerHTML =
        '<div class="empty-state glass"><i data-lucide="alert-circle"></i><p>Ошибка: ' + esc(e.message) + '</p></div>' +
        '<a href="/history" class="btn btn-secondary" style="margin-top:10px"><i data-lucide="arrow-left"></i> Назад</a>';
    }
    icons();
  }

  // ---- Router ----

  var routes = [
    { re: /^\/$/, fn: pageHome },
    { re: /^\/history$/, fn: pageHistory },
    { re: /^\/profile$/, fn: pageProfile },
    { re: /^\/check$/, fn: pageCheck },
    { re: /^\/demo$/, fn: pageDemo },
    { re: /^\/checks\/(\d+)$/, fn: function (m) { return pageCheckResult(m[1]); } },
  ];

  function updateNav(path) {
    document.querySelectorAll('#bottom-nav a').forEach(function (a) {
      var href = a.getAttribute('href');
      var active = path === href || (href === '/history' && path.indexOf('/checks/') === 0);
      a.classList.toggle('active', active);
    });
  }

  async function navigate(path, push) {
    if (push) history.pushState(null, '', path);
    updateNav(path);
    for (var i = 0; i < routes.length; i++) {
      var m = path.match(routes[i].re);
      if (m) { await routes[i].fn(m); return; }
    }
    await pageHome();
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

  ensureAuth().then(function () { navigate(location.pathname, false); });
})();
