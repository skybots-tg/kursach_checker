/* Broadcasts — standalone page: list view, create, delete, send */

registerPage('broadcasts', loadBroadcastsPage);

let _bcPage = 1;

function renderBroadcastsPage(bodyHtml, actionBtn) {
  $('page-broadcasts').innerHTML = `
    <div class="page-header">
      <div>
        <h1 class="page-title">Рассылки</h1>
        <p class="page-subtitle">Создание и отправка рассылок пользователям</p>
      </div>
      ${actionBtn || ''}
    </div>
    ${bodyHtml}`;
}

async function loadBroadcastsPage() {
  const { sub } = parseHash();

  if (sub) {
    const bid = parseInt(sub);
    if (bid) {
      await openBroadcastEditor(bid);
      return;
    }
  }

  loadBroadcastsList();
}

async function loadBroadcastsList() {
  const actionBtn = `<button class="btn btn-primary" onclick="createBroadcast()">${iconSvg('plus')} Новая рассылка</button>`;
  try {
    const list = await api('GET', '/admin/broadcasts');
    if (!list.length) {
      renderBroadcastsPage(emptyHtml('Нет рассылок', 'Создайте первую рассылку для отправки пользователям'), actionBtn);
      return;
    }
    const paged = paginate(list, _bcPage);
    let html = '<div class="bc-list">';
    for (const b of paged.items) {
      html += `
        <div class="card bc-list-item" onclick="navigateToBroadcast(${b.id})">
          <div class="bc-list-item-info">
            <div class="bc-list-item-title">${escHtml(b.title)}</div>
            <div class="bc-list-item-meta">
              ${statusBadge(b.status)}
              <span>${formatDate(b.created_at)}</span>
              ${b.status === 'sent' ? `<span>✓ ${b.sent_count} / ${b.total_users}</span>` : ''}
            </div>
          </div>
          <div class="bc-list-item-actions" onclick="event.stopPropagation()">
            ${b.status === 'draft' ? `
              <button class="btn-icon btn-sm" onclick="deleteBroadcast(${b.id})" title="Удалить">${iconSvg('trash', 16)}</button>
            ` : ''}
          </div>
        </div>`;
    }
    html += '</div>';
    html += paginationHtml(paged, 'bcPageTo');
    renderBroadcastsPage(html, actionBtn);
  } catch (err) {
    renderBroadcastsPage(`<div class="alert error">${escHtml(err.message)}</div>`);
  }
}

function bcPageTo(p) { _bcPage = p; loadBroadcastsList(); }

function navigateToBroadcast(id) {
  navigateTo('broadcasts', String(id));
}

async function createBroadcast() {
  try {
    const b = await api('POST', '/admin/broadcasts');
    toast('Рассылка создана', 'success');
    navigateToBroadcast(b.id);
  } catch (err) { toast(err.message, 'error'); }
}

async function deleteBroadcast(id) {
  if (!confirm('Удалить эту рассылку?')) return;
  try {
    await api('DELETE', `/admin/broadcasts/${id}`);
    toast('Рассылка удалена', 'success');
    loadBroadcastsList();
  } catch (err) { toast(err.message, 'error'); }
}

function confirmSendBroadcast(broadcastId) {
  const blockCount = window._editorBlocks?.length || 0;
  if (!blockCount) { toast('Добавьте хотя бы один блок', 'error'); return; }

  const hasEmpty = window._editorBlocks.some(b => {
    if (b.message_type === 'text') return !b.text;
    return !b.file_name && !b.file_path;
  });
  const warn = hasEmpty
    ? '<div class="alert warn" style="margin-bottom:12px">Некоторые блоки пустые и будут пропущены.</div>'
    : '';

  openModal('Отправить рассылку', `
    ${warn}
    <p style="margin-bottom:16px">Рассылка будет отправлена <b>всем пользователям</b> бота.<br>Это действие нельзя отменить.</p>
    <div class="bc-confirm-grid">
      <div class="bc-confirm-card">
        <div class="bc-confirm-val">${blockCount}</div>
        <div class="bc-confirm-label">Сообщений</div>
      </div>
    </div>
  `, `
    <button class="btn btn-ghost" onclick="closeModal()">Отмена</button>
    <button class="btn btn-primary" onclick="doSendBroadcast(${broadcastId})">Отправить</button>
  `);
}

async function doSendBroadcast(broadcastId) {
  closeModal();
  try {
    const res = await api('POST', `/admin/broadcasts/${broadcastId}/send`);
    toast(`Отправка начата (${res.total_users} получателей)`, 'success');
    await openBroadcastEditor(broadcastId);
  } catch (err) { toast(err.message, 'error'); }
}

window.loadBroadcastsPage = loadBroadcastsPage;
window.loadBroadcastsList = loadBroadcastsList;
window.bcPageTo = bcPageTo;
window.navigateToBroadcast = navigateToBroadcast;
window.createBroadcast = createBroadcast;
window.deleteBroadcast = deleteBroadcast;
window.confirmSendBroadcast = confirmSendBroadcast;
window.doSendBroadcast = doSendBroadcast;
