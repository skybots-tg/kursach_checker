/* Onboarding tour engine — spotlight, tooltip, navigation, persistence */

(function () {
  const STORAGE_KEY = 'onboarding_done';
  const SKIP_ALL_KEY = 'onboarding_skip_all';
  const SPOTLIGHT_PAD = 8;
  const TOOLTIP_GAP = 14;
  const AUTO_DELAY = 700;

  const _tourSteps = {};
  let _active = false;
  let _pageId = null;
  let _steps = [];
  let _idx = 0;

  let _overlay = null;
  let _spotlight = null;
  let _tooltip = null;
  let _resizeRaf = 0;

  /* ---- Persistence ---- */

  function getDone() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; } catch { return {}; }
  }

  function markDone(pageId) {
    const d = getDone();
    d[pageId] = true;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(d));
  }

  function isSkipAll() {
    return localStorage.getItem(SKIP_ALL_KEY) === '1';
  }

  function setSkipAll() {
    localStorage.setItem(SKIP_ALL_KEY, '1');
  }

  function resetOnboarding() {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(SKIP_ALL_KEY);
  }

  /* ---- Registration ---- */

  function registerTourSteps(pageId, steps) {
    _tourSteps[pageId] = steps;
  }

  /* ---- DOM creation ---- */

  function createElements() {
    if (_overlay) return;

    _overlay = document.createElement('div');
    _overlay.className = 'onboarding-overlay';
    _overlay.addEventListener('click', handleOverlayClick);

    _spotlight = document.createElement('div');
    _spotlight.className = 'onboarding-spotlight';

    _tooltip = document.createElement('div');
    _tooltip.className = 'onboarding-tooltip';

    document.body.appendChild(_overlay);
    document.body.appendChild(_spotlight);
    document.body.appendChild(_tooltip);
  }

  function removeElements() {
    _overlay?.remove();
    _spotlight?.remove();
    _tooltip?.remove();
    _overlay = _spotlight = _tooltip = null;
  }

  function handleOverlayClick(e) {
    if (e.target === _overlay) nextStep();
  }

  /* ---- Positioning ---- */

  function positionSpotlight(rect) {
    const s = _spotlight.style;
    s.top = (rect.top - SPOTLIGHT_PAD) + 'px';
    s.left = (rect.left - SPOTLIGHT_PAD) + 'px';
    s.width = (rect.width + SPOTLIGHT_PAD * 2) + 'px';
    s.height = (rect.height + SPOTLIGHT_PAD * 2) + 'px';
  }

  function positionTooltip(rect, preferred) {
    const tw = _tooltip.offsetWidth;
    const th = _tooltip.offsetHeight;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const pad = SPOTLIGHT_PAD;

    const fits = {
      bottom: (rect.bottom + pad + TOOLTIP_GAP + th) < vh,
      top: (rect.top - pad - TOOLTIP_GAP - th) > 0,
      right: (rect.right + pad + TOOLTIP_GAP + tw) < vw,
      left: (rect.left - pad - TOOLTIP_GAP - tw) > 0,
    };

    const order = [preferred, 'bottom', 'top', 'right', 'left'];
    let pos = order.find(p => fits[p]) || 'bottom';

    let top, left;
    switch (pos) {
      case 'bottom':
        top = rect.bottom + pad + TOOLTIP_GAP;
        left = rect.left - pad;
        break;
      case 'top':
        top = rect.top - pad - TOOLTIP_GAP - th;
        left = rect.left - pad;
        break;
      case 'right':
        top = rect.top - pad;
        left = rect.right + pad + TOOLTIP_GAP;
        break;
      case 'left':
        top = rect.top - pad;
        left = rect.left - pad - TOOLTIP_GAP - tw;
        break;
    }

    left = Math.max(12, Math.min(left, vw - tw - 12));
    top = Math.max(12, Math.min(top, vh - th - 12));

    const s = _tooltip.style;
    s.top = top + 'px';
    s.left = left + 'px';
    _tooltip.setAttribute('data-pos', pos);
  }

  /* ---- Rendering ---- */

  function renderStep() {
    if (!_active || _idx >= _steps.length) { endTour(); return; }

    const step = _steps[_idx];
    const pageEl = document.getElementById('page-' + _pageId);
    const target = pageEl
      ? pageEl.querySelector(step.target) || document.querySelector(step.target)
      : document.querySelector(step.target);

    if (!target) {
      if (_idx < _steps.length - 1) { _idx++; renderStep(); }
      else endTour();
      return;
    }

    target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    requestAnimationFrame(() => {
      const rect = target.getBoundingClientRect();
      positionSpotlight(rect);
      renderTooltipContent();
      positionTooltip(rect, step.position || 'bottom');
    });
  }

  function renderTooltipContent() {
    const step = _steps[_idx];
    const total = _steps.length;
    const isLast = _idx === total - 1;
    const isFirst = _idx === 0;
    const pct = (((_idx + 1) / total) * 100).toFixed(0);

    _tooltip.innerHTML = `
      <div class="onboarding-progress">
        <div class="onboarding-progress-bar">
          <div class="onboarding-progress-fill" style="width:${pct}%"></div>
        </div>
        <span class="onboarding-progress-label">Шаг ${_idx + 1} из ${total}</span>
      </div>
      <h4 class="onboarding-title">${escHtml(step.title)}</h4>
      <p class="onboarding-text">${escHtml(step.text)}</p>
      <div class="onboarding-actions">
        ${isFirst
          ? ''
          : '<button class="onboarding-btn onboarding-btn-secondary" data-ob="prev">Назад</button>'
        }
        <div class="onboarding-actions-spacer"></div>
        ${isLast
          ? ''
          : '<button class="onboarding-btn onboarding-btn-secondary" data-ob="skip">Пропустить</button>'
        }
        <button class="onboarding-btn onboarding-btn-primary" data-ob="${isLast ? 'finish' : 'next'}">
          ${isLast ? 'Готово!' : 'Далее'}
        </button>
      </div>
      <button class="onboarding-skip-all" data-ob="skipAll">Больше не показывать обучение</button>
    `;

    _tooltip.querySelectorAll('[data-ob]').forEach(btn => {
      btn.addEventListener('click', handleAction);
    });
  }

  function handleAction(e) {
    const action = e.currentTarget.dataset.ob;
    switch (action) {
      case 'next':   nextStep(); break;
      case 'prev':   prevStep(); break;
      case 'skip':   nextStep(); break;
      case 'finish': endTour();  break;
      case 'skipAll': skipAll(); break;
    }
  }

  /* ---- Navigation ---- */

  function nextStep() {
    _idx++;
    if (_idx >= _steps.length) endTour();
    else renderStep();
  }

  function prevStep() {
    if (_idx > 0) { _idx--; renderStep(); }
  }

  function endTour() {
    if (!_active) return;
    _active = false;
    if (_pageId) markDone(_pageId);
    removeElements();
    window.removeEventListener('resize', onResize);
    window.removeEventListener('keydown', onKeyDown);
    _pageId = null;
    _steps = [];
    _idx = 0;
  }

  function skipAll() {
    setSkipAll();
    endTour();
    if (window.toast) toast('Обучение отключено. Вы можете вызвать его снова кнопкой «?» в шапке.', 'info');
  }

  /* ---- Resize / keyboard ---- */

  function onResize() {
    cancelAnimationFrame(_resizeRaf);
    _resizeRaf = requestAnimationFrame(() => {
      if (_active) renderStep();
    });
  }

  function onKeyDown(e) {
    if (!_active) return;
    if (e.key === 'Escape') { endTour(); return; }
    if (e.key === 'ArrowRight') { nextStep(); return; }
    if (e.key === 'ArrowLeft') { prevStep(); return; }
  }

  /* ---- Public API ---- */

  function startTour(pageId) {
    if (_active) endTour();
    const steps = _tourSteps[pageId];
    if (!steps || !steps.length) return;

    _pageId = pageId;
    _steps = steps;
    _idx = 0;
    _active = true;

    createElements();
    window.addEventListener('resize', onResize);
    window.addEventListener('keydown', onKeyDown);
    renderStep();
  }

  function onboardingCheck(pageId) {
    if (isSkipAll()) return;
    const done = getDone();
    if (done[pageId]) return;
    if (!_tourSteps[pageId]) return;
    setTimeout(() => {
      if (location.hash === '#' + pageId || (pageId === 'dashboard' && !location.hash)) {
        startTour(pageId);
      }
    }, AUTO_DELAY);
  }

  function restartCurrentTour() {
    const pageId = (location.hash || '#dashboard').replace('#', '');
    startTour(pageId);
  }

  /* ---- Expose globally ---- */
  window.registerTourSteps = registerTourSteps;
  window.startTour = startTour;
  window.onboardingCheck = onboardingCheck;
  window.restartCurrentTour = restartCurrentTour;
  window.resetOnboarding = resetOnboarding;
})();
