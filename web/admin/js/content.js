/* Content — page shell, tab switching between Menu, Texts, System Texts & Broadcasts */

registerPage('content', loadContent);

let _contentTab = 'menu';

async function loadContent() {
  const { sub } = parseHash();

  if (sub && sub.startsWith('broadcasts/')) {
    const bid = parseInt(sub.split('/')[1]);
    if (bid) {
      _contentTab = 'broadcasts';
      await openBroadcastEditor(bid);
      return;
    }
  }

  if (sub && ['menu', 'texts', 'system', 'broadcasts'].includes(sub)) _contentTab = sub;
  const page = $('page-content');
  page.innerHTML = loadingHtml();
  try {
    if (_contentTab === 'texts') await loadContentTexts();
    else if (_contentTab === 'system') await loadSystemTexts();
    else if (_contentTab === 'broadcasts') await loadBroadcasts();
    else await loadContentMenu();
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderContentPage(bodyHtml, actionBtn) {
  $('page-content').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Контент бота</h1>
        <p class="page-subtitle">Тексты, меню и сообщения бота</p>
      </div>
      ${actionBtn || ''}
    </div>
    <div class="tabs">
      <button class="tab-btn ${_contentTab === 'menu' ? 'active' : ''}" onclick="switchContentTab('menu')">Меню</button>
      <button class="tab-btn ${_contentTab === 'texts' ? 'active' : ''}" onclick="switchContentTab('texts')">Тексты</button>
      <button class="tab-btn ${_contentTab === 'system' ? 'active' : ''}" onclick="switchContentTab('system')">Системные тексты</button>
      <button class="tab-btn ${_contentTab === 'broadcasts' ? 'active' : ''}" onclick="switchContentTab('broadcasts')">Рассылки</button>
    </div>
    ${bodyHtml}`;
}

function switchContentTab(tab) {
  _contentTab = tab;
  history.replaceState(null, '', '#content/' + tab);
  loadContent();
}

window.switchContentTab = switchContentTab;
window.renderContentPage = renderContentPage;
window.loadContent = loadContent;
