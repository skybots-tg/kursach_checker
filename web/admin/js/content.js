/* Content — page shell, tab switching between Menu and Texts */

registerPage('content', loadContent);

let _contentTab = 'menu';

async function loadContent() {
  const page = $('page-content');
  page.innerHTML = loadingHtml();
  try {
    if (_contentTab === 'texts') await loadContentTexts();
    else await loadContentMenu();
  } catch (err) {
    page.innerHTML = `<div class="alert error">${escHtml(err.message)}</div>`;
  }
}

function renderContentPage(bodyHtml, actionBtn) {
  const isTexts = _contentTab === 'texts';
  $('page-content').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Контент бота</h1>
        <p class="page-subtitle">Тексты, меню и сообщения бота</p>
      </div>
      ${actionBtn || ''}
    </div>
    <div class="tabs">
      <button class="tab-btn ${!isTexts ? 'active' : ''}" onclick="switchContentTab('menu')">Меню</button>
      <button class="tab-btn ${isTexts ? 'active' : ''}" onclick="switchContentTab('texts')">Тексты</button>
    </div>
    ${bodyHtml}`;
}

function switchContentTab(tab) {
  _contentTab = tab;
  loadContent();
}

window.switchContentTab = switchContentTab;
window.renderContentPage = renderContentPage;
window.loadContent = loadContent;
