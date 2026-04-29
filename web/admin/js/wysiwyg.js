/* Tiny WYSIWYG editor for Telegram-flavoured HTML.
 *
 * Создаёт визуальный редактор поверх contentEditable + кнопки тулбара.
 * Сам HTML-источник синхронизируется в скрытое <textarea> (id передаётся
 * вызывающим кодом) — чтобы вся остальная форма продолжала работать
 * без изменений (FormData, getVal и т.п.).
 *
 * Поддерживаются только теги, которые принимает Telegram Bot API в
 * parse_mode=HTML: <b>, <i>, <u>, <s>, <a href>, <code>, <pre>,
 * <blockquote> + <br>. Всё остальное вырезается при загрузке и при
 * каждом обновлении (на случай, если пользователь вставил HTML через
 * буфер).
 */

(function () {
  'use strict';

  const ALLOWED_TAGS = new Set([
    'b', 'strong', 'i', 'em', 'u', 's', 'strike', 'del',
    'a', 'code', 'pre', 'blockquote', 'br',
  ]);
  // На что нормализуем при сохранении: ключ — что встречаем, значение — во что превращаем.
  const TAG_NORMALIZE = {
    strong: 'b', em: 'i', strike: 's', del: 's',
  };

  function _sanitize(node) {
    Array.from(node.childNodes).forEach(child => {
      if (child.nodeType === Node.TEXT_NODE) return;
      if (child.nodeType !== Node.ELEMENT_NODE) {
        node.removeChild(child);
        return;
      }
      const tag = child.tagName.toLowerCase();
      if (!ALLOWED_TAGS.has(tag)) {
        // Заменяем неизвестный тег на его текстовое содержимое.
        const frag = document.createDocumentFragment();
        Array.from(child.childNodes).forEach(g => frag.appendChild(g));
        node.replaceChild(frag, child);
        // Рекурсивно обработаем то, что вложили в node.
        _sanitize(node);
        return;
      }
      // Чистим атрибуты (ссылке оставляем href).
      Array.from(child.attributes).forEach(attr => {
        if (tag === 'a' && attr.name === 'href') return;
        child.removeAttribute(attr.name);
      });
      _sanitize(child);
    });
  }

  function _normalize(node) {
    // Нормализуем альтернативные теги (strong -> b, em -> i и т.п.).
    Array.from(node.childNodes).forEach(child => {
      if (child.nodeType !== Node.ELEMENT_NODE) return;
      const tag = child.tagName.toLowerCase();
      const target = TAG_NORMALIZE[tag];
      if (target) {
        const repl = document.createElement(target);
        Array.from(child.attributes).forEach(a => repl.setAttribute(a.name, a.value));
        Array.from(child.childNodes).forEach(g => repl.appendChild(g));
        node.replaceChild(repl, child);
        _normalize(repl);
      } else {
        _normalize(child);
      }
    });
  }

  function _htmlToTelegram(html) {
    const div = document.createElement('div');
    div.innerHTML = html || '';
    _sanitize(div);
    _normalize(div);
    // Превращаем <div> и <p> в переводы строк, чтобы Telegram-парсер
    // получил привычный текст.
    Array.from(div.querySelectorAll('div, p')).forEach(el => {
      if (el.parentNode === div) {
        const before = el.previousSibling;
        if (before) div.insertBefore(document.createElement('br'), el);
        while (el.firstChild) div.insertBefore(el.firstChild, el);
        div.removeChild(el);
      }
    });
    return div.innerHTML
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/&nbsp;/g, ' ')
      .trim();
  }

  function _telegramToHtml(text) {
    // Telegram-HTML уже почти валидный; добавим <br> вместо переводов
    // строки, чтобы contentEditable показывал перенос.
    if (!text) return '';
    return text.replace(/\r/g, '').replace(/\n/g, '<br>');
  }

  function _exec(cmd, value) {
    document.execCommand(cmd, false, value || null);
  }

  function _toolbarHtml(editorId) {
    return `
      <div class="wysiwyg-toolbar" data-editor="${editorId}">
        <button type="button" class="rt-btn" data-cmd="bold" title="Жирный (Ctrl+B)"><b>B</b></button>
        <button type="button" class="rt-btn" data-cmd="italic" title="Курсив (Ctrl+I)"><i>I</i></button>
        <button type="button" class="rt-btn" data-cmd="underline" title="Подчёркнутый (Ctrl+U)"><u>U</u></button>
        <button type="button" class="rt-btn" data-cmd="strikeThrough" title="Зачёркнутый"><s>S</s></button>
        <span class="rt-sep"></span>
        <button type="button" class="rt-btn" data-cmd="link" title="Ссылка">🔗</button>
        <button type="button" class="rt-btn" data-cmd="code" title="Inline-код">&lt;/&gt;</button>
        <button type="button" class="rt-btn" data-cmd="quote" title="Цитата">❝</button>
        <span class="rt-sep"></span>
        <button type="button" class="rt-btn" data-cmd="clear" title="Убрать форматирование">⨯</button>
      </div>`;
  }

  function _wrapSelection(tag) {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;
    const range = sel.getRangeAt(0);
    if (range.collapsed) return;
    const wrapper = document.createElement(tag);
    try {
      wrapper.appendChild(range.extractContents());
      range.insertNode(wrapper);
      // Возвращаем фокус и обновим выделение на новый узел.
      sel.removeAllRanges();
      const newRange = document.createRange();
      newRange.selectNodeContents(wrapper);
      sel.addRange(newRange);
    } catch (err) {
      console.warn('wrapSelection failed', err);
    }
  }

  function attach(editorId, hiddenId, options) {
    const editor = document.getElementById(editorId);
    const hidden = document.getElementById(hiddenId);
    if (!editor || !hidden) return;

    const placeholder = (options && options.placeholder) || '';
    if (placeholder) editor.dataset.placeholder = placeholder;
    editor.contentEditable = 'true';
    editor.spellcheck = true;

    const initial = hidden.value || '';
    editor.innerHTML = _telegramToHtml(initial);
    _updateEmptyState(editor);

    function sync() {
      hidden.value = _htmlToTelegram(editor.innerHTML);
      hidden.dispatchEvent(new Event('input', { bubbles: true }));
      _updateEmptyState(editor);
    }

    editor.addEventListener('input', sync);
    editor.addEventListener('blur', sync);
    editor.addEventListener('paste', e => {
      // Принудительно вставляем как plain text, чтобы не тянуть стилевой мусор.
      e.preventDefault();
      const text = (e.clipboardData || window.clipboardData).getData('text');
      document.execCommand('insertText', false, text);
    });

    const toolbar = document.querySelector('[data-editor="' + editorId + '"]');
    if (!toolbar) return;
    toolbar.addEventListener('click', e => {
      const btn = e.target.closest('.rt-btn');
      if (!btn) return;
      e.preventDefault();
      editor.focus();
      const cmd = btn.dataset.cmd;
      if (cmd === 'link') {
        const url = prompt('Введите URL:', 'https://');
        if (url) _exec('createLink', url);
      } else if (cmd === 'code') {
        _wrapSelection('code');
      } else if (cmd === 'quote') {
        _wrapSelection('blockquote');
      } else if (cmd === 'clear') {
        _exec('removeFormat');
        // Дополнительно убираем blockquote/code/pre которые removeFormat не трогает.
        ['blockquote', 'code', 'pre'].forEach(tag => {
          const sel = window.getSelection();
          if (!sel || !sel.rangeCount) return;
          let node = sel.getRangeAt(0).startContainer;
          while (node && node !== editor) {
            if (node.nodeType === 1 && node.tagName.toLowerCase() === tag) {
              const parent = node.parentNode;
              while (node.firstChild) parent.insertBefore(node.firstChild, node);
              parent.removeChild(node);
              break;
            }
            node = node.parentNode;
          }
        });
      } else if (cmd) {
        _exec(cmd);
      }
      sync();
    });
  }

  function _updateEmptyState(editor) {
    const text = editor.innerText.trim();
    editor.dataset.empty = text ? 'false' : 'true';
  }

  function buildHtml(editorId, hiddenId, opts) {
    const placeholder = (opts && opts.placeholder) || '';
    return `
      ${_toolbarHtml(editorId)}
      <div class="wysiwyg-editor" id="${editorId}"
        data-placeholder="${(placeholder || '').replace(/"/g, '&quot;')}"></div>
      <div class="wysiwyg-mode-row">
        <span>Поддерживаются: <b>B</b>, <i>I</i>, <u>U</u>, <s>S</s>, ссылка, код, цитата.</span>
        <button type="button" class="link-btn" data-toggle-raw="${editorId}">Показать HTML-источник</button>
      </div>`;
  }

  function bindRawToggle(editorId, hiddenId) {
    const link = document.querySelector('[data-toggle-raw="' + editorId + '"]');
    if (!link) return;
    link.addEventListener('click', () => {
      const editor = document.getElementById(editorId);
      const hidden = document.getElementById(hiddenId);
      const isShown = !hidden.classList.contains('hidden-raw-textarea');
      if (isShown) {
        // Прячем raw → показываем editor.
        hidden.style.display = 'none';
        editor.style.display = '';
        editor.innerHTML = _telegramToHtml(hidden.value);
        _updateEmptyState(editor);
        link.textContent = 'Показать HTML-источник';
        hidden.classList.add('hidden-raw-textarea');
      } else {
        // Показываем raw, скрываем editor.
        hidden.value = _htmlToTelegram(editor.innerHTML);
        editor.style.display = 'none';
        hidden.style.display = '';
        hidden.style.minHeight = '160px';
        link.textContent = 'Вернуться к редактору';
        hidden.classList.remove('hidden-raw-textarea');
      }
    });
    // По умолчанию скрываем raw — показываем редактор.
    const hidden = document.getElementById(hiddenId);
    if (hidden) {
      hidden.style.display = 'none';
      hidden.classList.add('hidden-raw-textarea');
    }
  }

  window.WysiwygEditor = {
    buildHtml,
    attach,
    bindRawToggle,
    htmlToTelegram: _htmlToTelegram,
    telegramToHtml: _telegramToHtml,
  };
})();
