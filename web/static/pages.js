(function () {
  'use strict';

  var A = window.App;
  var appEl = A.el;

  // ---- Page: Home ----

  async function pageHome() {
    document.title = 'Проверка оформления';
    var me = await A.getMe();
    var credits = me ? me.credits_available : '\u2014';
    appEl.innerHTML =
      '<section class="glass hero hero-compact">' +
        '<div class="hero-icon"><i data-lucide="file-search"></i></div>' +
        '<h1 class="gradient-text">Проверка оформления</h1>' +
        '<p>Загрузите DOCX \u2014 получите отчёт по ГОСТу и методичке вуза</p>' +
      '</section>' +
      '<div class="credits-banner">' +
        '<div class="credits-banner-left">' +
          '<i data-lucide="zap" class="credits-banner-icon"></i>' +
          '<span class="credits-banner-value">' + credits + '</span>' +
          '<span class="credits-banner-label">' + A.pluralize(credits, 'проверка', 'проверки', 'проверок').replace(/^\d+\s/, '') + ' доступно</span>' +
        '</div>' +
        '<a href="/profile" class="credits-banner-topup">Пополнить</a>' +
      '</div>' +
      '<div class="section-label">Как это работает</div>' +
      '<section class="glass steps-list">' +
        '<div class="step"><div class="step-num">1</div><div class="step-body"><div class="step-title">Загрузите файл</div><div class="step-desc">Курсовая или ВКР в формате DOCX</div></div></div>' +
        '<div class="step"><div class="step-num">2</div><div class="step-body"><div class="step-title">Автопроверка</div><div class="step-desc">Система проверяет оформление по правилам</div></div></div>' +
        '<div class="step"><div class="step-num">3</div><div class="step-body"><div class="step-title">Получите отчёт</div><div class="step-desc">Подробный список замечаний с рекомендациями</div></div></div>' +
      '</section>' +
      '<div class="btn-group">' +
        '<a href="' + (credits <= 0 ? '/profile' : '/check') + '" class="btn btn-primary"><i data-lucide="sparkles"></i> Начать проверку <i data-lucide="arrow-right" style="opacity:.6"></i></a>' +
        '<a href="/demo" class="btn btn-secondary"><i data-lucide="play"></i> Посмотреть демо-отчёт</a>' +
      '</div>' +
      '<div class="section-label">Преимущества</div>' +
      '<section class="glass features-list">' +
        '<div class="feature-row"><div class="feature-icon blue"><i data-lucide="shield-check"></i></div><div class="feature-text"><div class="feature-title">По ГОСТу</div><div class="feature-desc">Проверка по актуальным стандартам</div></div></div>' +
        '<div class="feature-row"><div class="feature-icon green"><i data-lucide="zap"></i></div><div class="feature-text"><div class="feature-title">Быстро</div><div class="feature-desc">Результат за несколько секунд</div></div></div>' +
        '<div class="feature-row"><div class="feature-icon purple"><i data-lucide="graduation-cap"></i></div><div class="feature-text"><div class="feature-title">По методичке</div><div class="feature-desc">Правила именно вашего вуза</div></div></div>' +
      '</section>';
    A.icons();
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
    A.icons();

    var checks = [], orders = [];
    try {
      var results = await Promise.all([A.api('/checks'), A.api('/orders')]);
      checks = results[0];
      orders = results[1];
    } catch (e) {
      document.getElementById('tab-content').innerHTML =
        '<div class="empty-state glass"><i data-lucide="alert-circle"></i><p>' + A.esc(e.message) + '</p></div>';
      A.icons();
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
                '<span class="chip ' + A.statusCls(c.status) + '">' + A.statusLabel(c.status) + '</span>' +
              '</div>' +
              '<div class="list-card-meta">Создано: ' + A.fmtDate(c.created_at) +
                (c.finished_at ? ' \xB7 Завершено: ' + A.fmtDate(c.finished_at) : '') +
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
                '<span class="list-card-title">' + A.esc(o.product || 'Заказ #' + o.id) + '</span>' +
                '<span class="chip ' + A.statusCls(o.status) + '">' + A.statusLabel(o.status) + '</span>' +
              '</div>' +
              '<div class="list-card-meta">' + o.amount + ' \u20BD \xB7 ' + A.fmtDate(o.created_at) +
                (o.paid_at ? ' \xB7 Оплачено: ' + A.fmtDate(o.paid_at) : '') +
              '</div>' +
            '</div>';
          }).join('');
        }
      }
      A.icons();
    }

    tabBtns.forEach(function (btn) { btn.addEventListener('click', function () { showTab(btn.dataset.tab); }); });
    showTab('checks');
  }

  // ---- Page: Profile ----

  async function pageProfile() {
    document.title = 'Профиль — Проверка оформления';
    appEl.innerHTML = '<div class="loading-spinner"><i data-lucide="loader-2" class="spin"></i><span>Загрузка\u2026</span></div>';
    A.icons();

    var me = await A.getMe();
    if (!me) {
      appEl.innerHTML = '<div class="empty-state glass"><i data-lucide="user-x"></i><p>Не удалось загрузить профиль</p></div>';
      A.icons();
      return;
    }

    var products = [];
    try { products = await A.api('/products'); } catch (_) {}

    var displayName = me.first_name
      ? A.esc(me.first_name) + (me.username ? ' (@' + A.esc(me.username) + ')' : '')
      : A.esc(me.username || 'Пользователь');

    var productsHtml = '';
    if (products.length) {
      productsHtml =
        '<div class="section-label">Пополнить баланс</div>' +
        products.map(function (p) {
          return '<div class="glass list-card product-card">' +
            '<div class="list-card-row">' +
              '<span class="list-card-title">' + A.esc(p.name) + '</span>' +
              '<span class="product-price">' + p.price + ' ' + A.esc(p.currency || '\u20BD') + '</span>' +
            '</div>' +
            '<div class="list-card-meta">' + A.pluralize(p.credits_amount, 'проверка', 'проверки', 'проверок') +
              (p.description ? ' \xB7 ' + A.esc(p.description) : '') +
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
          var res = await A.apiPost('/payments/create', { product_id: productId });
          if (res.payment_url) {
            if (A.tg && A.tg.openLink) A.tg.openLink(res.payment_url);
            else window.open(res.payment_url, '_blank');
          }
          if (res.order_id) {
            A.pollOrderStatus(res.order_id);
          }
        } catch (e) {
          A.showToast('Ошибка: ' + e.message, 'error');
        } finally {
          btn.disabled = false;
          btn.innerHTML = '<i data-lucide="credit-card"></i> Оплатить';
          A.icons();
        }
      });
    });
    A.icons();
  }

  // ---- Page: Check ----

  async function pageCheck() {
    document.title = 'Новая проверка — Проверка оформления';
    var me = await A.getMe();
    var credits = me ? me.credits_available : 0;

    appEl.innerHTML =
      '<div class="section-label">Новая проверка</div>' +
      '<section class="glass check-form">' +
        '<div class="check-field"><label class="check-label">ВУЗ</label>' +
          '<select id="sel-uni" class="check-select"><option value="">Загрузка\u2026</option></select></div>' +
        '<div class="check-field"><label class="check-label">Шаблон проверки</label>' +
          '<select id="sel-tpl" class="check-select" disabled><option value="">Сначала выберите вуз</option></select>' +
          '<div id="tpl-hint" class="check-field-hint" style="display:none;margin-top:6px;font-size:12px;color:var(--text-muted);line-height:1.4"></div></div>' +
        '<div class="check-field"><label class="check-label">ГОСТ / стиль (опционально)</label>' +
          '<select id="sel-gost" class="check-select"><option value="">Автоматически по шаблону</option></select></div>' +
        '<div class="check-field"><label class="check-label">Файл работы (DOC/DOCX, до 20 МБ)</label>' +
          '<div id="upload-wrap">' +
            '<div class="upload-area" id="upload-area"><i data-lucide="upload-cloud"></i><span>Нажмите, чтобы выбрать файл</span></div>' +
            '<div class="file-card" id="file-card" style="display:none">' +
              '<div class="file-card-icon"><i data-lucide="file-text"></i></div>' +
              '<div class="file-card-info"><span class="file-card-name" id="file-card-name"></span>' +
                '<span class="file-card-size" id="file-card-size"></span></div>' +
              '<button type="button" class="file-card-remove" id="file-card-remove" title="Удалить"><i data-lucide="x"></i></button>' +
            '</div>' +
          '</div>' +
          '<input type="file" id="file-input" accept=".doc,.docx" style="display:none"></div>' +
        '<div style="font-size:12px;color:var(--text-muted);margin-top:2px">Доступно: <b>' + A.pluralize(credits, 'проверка', 'проверки', 'проверок') + '</b></div>' +
        '<div id="check-err" style="display:none;margin-top:8px;font-size:12px;color:var(--danger)"></div>' +
        '<button id="btn-start" class="btn btn-primary" style="margin-top:14px">' +
          '<i data-lucide="sparkles"></i> Запустить проверку и списать 1 кредит</button>' +
      '</section>';
    A.icons();

    var selUni = document.getElementById('sel-uni');
    var selTpl = document.getElementById('sel-tpl');
    var selGost = document.getElementById('sel-gost');
    var fileInput = document.getElementById('file-input');
    var uploadArea = document.getElementById('upload-area');
    var fileCard = document.getElementById('file-card');
    var fileCardName = document.getElementById('file-card-name');
    var fileCardSize = document.getElementById('file-card-size');
    var btnStart = document.getElementById('btn-start');
    var errEl = document.getElementById('check-err');
    var tplHintEl = document.getElementById('tpl-hint');
    var chosenFile = null, versionId = null;

    function showErr(msg) { errEl.textContent = msg; errEl.style.display = msg ? 'block' : 'none'; }
    function showTplHint(msg) {
      if (!tplHintEl) return;
      tplHintEl.textContent = msg || '';
      tplHintEl.style.display = msg ? 'block' : 'none';
    }
    function updateBtn() { /* state tracked via chosenFile & versionId */ }

    try {
      var refs = await Promise.all([A.api('/universities'), A.api('/gosts')]);
      selUni.innerHTML = '<option value="">Выберите вуз</option>' +
        refs[0].map(function (u) { return '<option value="' + u.id + '">' + A.esc(u.name) + '</option>'; }).join('');
      if (refs[1].length) {
        selGost.innerHTML = '<option value="">Автоматически по шаблону</option>' +
          refs[1].map(function (g) { return '<option value="' + g.id + '">' + A.esc(g.name) + '</option>'; }).join('');
      }
    } catch (e) { showErr('Не удалось загрузить справочники: ' + e.message); }

    selUni.addEventListener('change', async function () {
      versionId = null; selTpl.disabled = true; updateBtn(); showTplHint('');
      selTpl.innerHTML = '<option value="">Загрузка\u2026</option>';
      if (!selUni.value) {
        selTpl.innerHTML = '<option value="">Сначала выберите вуз</option>';
        return;
      }
      try {
        var tpls = await A.api('/templates?university_id=' + encodeURIComponent(selUni.value));
        selTpl.disabled = false;
        if (!tpls.length) {
          selTpl.innerHTML = '<option value="">\u2014 нет шаблонов \u2014</option>';
          showTplHint(
            'Для этого ВУЗа нет опубликованных шаблонов. В админке: шаблон должен быть «Опубликован» и привязан к этому ВУЗу (тот же, что в списке).'
          );
          return;
        }
        selTpl.innerHTML = '<option value="">Выберите шаблон</option>' +
          tpls.map(function (t) {
            return '<option value="' + t.id + '">' + A.esc(t.name) + ' \xB7 ' + A.esc(t.type_work) + (t.year ? ' \xB7 ' + A.esc(t.year) : '') + '</option>';
          }).join('');
      } catch (e) {
        selTpl.innerHTML = '<option value="">Ошибка загрузки</option>';
        showErr(e.message);
      }
    });

    selTpl.addEventListener('change', async function () {
      versionId = null; updateBtn();
      if (!selTpl.value) return;
      try {
        var blocks = await A.api('/templates/' + selTpl.value + '/blocks');
        versionId = blocks.version_id;
        updateBtn();
      } catch (e) { showErr('Не удалось загрузить версию шаблона'); }
    });

    uploadArea.addEventListener('click', function () { fileInput.click(); });

    function showFile(f) {
      chosenFile = f;
      fileCardName.textContent = f.name;
      fileCardSize.textContent = (f.size / (1024 * 1024)).toFixed(1) + ' МБ';
      uploadArea.style.display = 'none';
      fileCard.style.display = 'flex';
      A.icons(); updateBtn();
    }
    function clearFile() {
      chosenFile = null;
      fileInput.value = '';
      fileCard.style.display = 'none';
      uploadArea.style.display = 'flex';
      updateBtn();
    }

    document.getElementById('file-card-remove').addEventListener('click', function (e) {
      e.stopPropagation();
      clearFile();
    });

    fileInput.addEventListener('change', function () {
      var f = fileInput.files && fileInput.files[0];
      if (!f) return;
      if (!/\.(doc|docx)$/i.test(f.name)) { showErr('Поддерживаются только файлы DOC/DOCX'); return; }
      if (f.size > 20 * 1024 * 1024) { showErr('Файл слишком большой (макс. 20 МБ)'); return; }
      showErr('');
      showFile(f);
    });

    btnStart.addEventListener('click', async function () {
      if (!selUni.value) { A.showToast('Выберите вуз', 'error'); return; }
      if (!versionId) { A.showToast('Выберите шаблон проверки', 'error'); return; }
      if (!chosenFile) { A.showToast('Прикрепите файл работы', 'error'); return; }
      if (credits <= 0) { A.showToast('Нет доступных проверок', 'error'); A.navigate('/profile', true); return; }
      showErr(''); btnStart.disabled = true;
      btnStart.textContent = 'Загружаем файл\u2026';
      try {
        var fd = new FormData(); fd.append('file', chosenFile);
        var uploaded = await A.apiUpload('/checks/upload', fd);
        btnStart.textContent = 'Запускаем проверку\u2026';
        var qs = 'template_version_id=' + versionId + '&input_file_id=' + uploaded.file_id;
        if (selGost.value) qs += '&gost_id=' + selGost.value;
        var check = await A.apiPost('/checks/start?' + qs, {});
        A.navigate('/checks/' + check.check_id, true);
      } catch (e) {
        showErr('Ошибка: ' + e.message);
        btnStart.disabled = false;
        btnStart.innerHTML = '<i data-lucide="sparkles"></i> Запустить проверку и списать 1 кредит';
        A.icons();
      }
    });
  }

  // ---- Page: Demo ----

  async function pageDemo() {
    document.title = 'Демо-отчёт — Проверка оформления';
    appEl.innerHTML = '<div class="section-label">Демо-отчёт</div>' +
      '<div class="loading-spinner"><i data-lucide="loader-2" class="spin"></i><span>Загрузка\u2026</span></div>';
    A.icons();
    try {
      var check = await A.api('/demo');
      appEl.innerHTML =
        '<div class="section-label">Демо-отчёт</div>' +
        '<section class="glass list-card">' +
          '<div class="list-card-row"><span class="list-card-title">Пример проверки</span><span class="chip fixed">Готово</span></div>' +
          '<div class="list-card-meta">Ниже — реальный пример отчёта по работе</div>' +
          (check.output_file_id ? '<a href="' + A.dlUrl(check.output_file_id) + '" target="_blank" class="btn btn-secondary btn-sm" style="margin-top:10px"><i data-lucide="download"></i> Скачать пример работы</a>' : '') +
        '</section>' +
        A.renderReport(check.report) +
        '<a href="/" class="btn btn-secondary" style="margin-top:10px"><i data-lucide="arrow-left"></i> На главную</a>';
    } catch (e) {
      appEl.innerHTML = '<div class="section-label">Демо-отчёт</div>' +
        '<div class="empty-state glass"><i data-lucide="alert-circle"></i><p>' + A.esc(e.message) + '</p></div>' +
        '<a href="/" class="btn btn-secondary" style="margin-top:10px"><i data-lucide="arrow-left"></i> На главную</a>';
    }
    A.icons();
  }

  // ---- Page: Check Result (with auto-polling) ----

  async function pageCheckResult(id) {
    document.title = 'Результат #' + id + ' — Проверка оформления';
    appEl.innerHTML = '<div class="loading-spinner"><i data-lucide="loader-2" class="spin"></i><span>Загрузка\u2026</span></div>';
    A.icons();

    function render(check) {
      var inProgress = check.status === 'queued' || check.status === 'running';
      appEl.innerHTML =
        '<div class="section-label">Результат проверки #' + check.id + '</div>' +
        '<section class="glass list-card">' +
          '<div class="list-card-row">' +
            '<span class="list-card-title">Проверка #' + check.id + '</span>' +
            '<span class="chip ' + A.statusCls(check.status) + '">' + A.statusLabel(check.status) + '</span>' +
          '</div>' +
          '<div class="list-card-meta">' +
            'Создано: ' + A.fmtDate(check.created_at) +
            (check.finished_at ? ' \xB7 Завершено: ' + A.fmtDate(check.finished_at) : '') +
          '</div>' +
          (check.output_file_id
            ? '<a href="' + A.dlUrl(check.output_file_id) + '" target="_blank" class="btn btn-secondary btn-sm" style="margin-top:10px"><i data-lucide="download"></i> Скачать исправленный</a>'
            : '') +
        '</section>' +
        (inProgress
          ? '<div class="loading-spinner"><i data-lucide="loader-2" class="spin"></i><span>Проверяется, подождите\u2026</span></div>'
          : '') +
        A.renderReport(check.report) +
        '<a href="/history" class="btn btn-secondary" style="margin-top:10px"><i data-lucide="arrow-left"></i> Назад к истории</a>';
      A.icons();
    }

    async function poll() {
      try {
        var check = await A.api('/checks/' + id);
        render(check);
        if (check.status === 'queued' || check.status === 'running') {
          A.setPageTimer(setTimeout(poll, 3000));
        }
      } catch (e) {
        appEl.innerHTML =
          '<div class="empty-state glass"><i data-lucide="alert-circle"></i><p>Ошибка: ' + A.esc(e.message) + '</p></div>' +
          '<a href="/history" class="btn btn-secondary" style="margin-top:10px"><i data-lucide="arrow-left"></i> Назад</a>';
        A.icons();
      }
    }

    await poll();
  }

  // ---- Register routes & start ----

  A.start([
    { re: /^\/$/, fn: pageHome },
    { re: /^\/history$/, fn: pageHistory },
    { re: /^\/profile$/, fn: pageProfile },
    { re: /^\/check$/, fn: pageCheck },
    { re: /^\/demo$/, fn: pageDemo },
    { re: /^\/checks\/(\d+)$/, fn: function (m) { return pageCheckResult(m[1]); } },
  ]);
})();
