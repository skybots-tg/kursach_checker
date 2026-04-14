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
  const msg = window._currentBcMessage;
  if (!msg) { toast('Сообщение не создано', 'error'); return; }

  if (msg.message_type === 'text' && !msg.text) {
    toast('Введите текст сообщения', 'error');
    return;
  }
  if (msg.message_type !== 'text' && !msg.file_name) {
    toast('Прикрепите файл или выберите тип «Без медиа»', 'error');
    return;
  }

  const typeLabels = { text: 'Текст', photo: 'Фото', video: 'Видео', document: 'Документ', audio: 'Аудио', animation: 'GIF' };
  const label = typeLabels[msg.message_type] || msg.message_type;
  const summary = msg.message_type === 'text'
    ? 'Текстовое сообщение'
    : `${label}${msg.text ? ' с подписью' : ''}`;

  const segLabels = { all: 'Все пользователи', paid: 'Оплачивали', viewers: 'Только смотрели',
    unpaid_invoice: 'Создали счёт, но не оплатили', recent: 'Зарегистрировались недавно' };
  const seg = window._currentBroadcast?.target_segment || { type: 'all' };
  const segName = segLabels[seg.type] || seg.type;
  const counterEl = $('bc-audience-counter');
  const audienceInfo = counterEl ? counterEl.innerHTML : '';

  openModal('Отправить рассылку', `
    <p style="margin-bottom:12px">Рассылка будет отправлена выбранному сегменту.<br>
    <span style="color:var(--text-muted)">Тип: ${summary}</span><br>
    <span style="color:var(--text-muted)">Аудитория: ${segName}</span><br>
    <span style="color:var(--text-muted)">Получатели: ${audienceInfo}</span></p>
    <p style="color:var(--danger);font-weight:500">Это действие нельзя отменить.</p>
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
