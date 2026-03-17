/* Tag Input — chip-style input for array values.
   Usage:
     createTagInput({ id, items, placeholder, onUpdate, parseValue })
     - id: unique DOM id
     - items: initial string[] or number[]
     - placeholder: hint text
     - onUpdate(items): callback when tags change
     - parseValue(str): optional transform before adding (e.g. parseInt)
*/

function createTagInput({ id, items = [], placeholder = '', onUpdate, parseValue }) {
  const tags = [...items];

  function render() {
    const container = document.getElementById(id);
    if (!container) return;

    const tagsHtml = tags.map((tag, i) => `
      <span class="tag-chip">
        <span class="tag-chip-text">${escHtml(String(tag))}</span>
        <button type="button" class="tag-chip-remove" data-tag-id="${id}" data-idx="${i}"
                title="Удалить">&times;</button>
      </span>
    `).join('');

    container.innerHTML = `
      <div class="tag-chips">${tagsHtml}</div>
      <input type="text" class="tag-text-input" data-tag-id="${id}"
             placeholder="${escHtml(placeholder || 'Введите и нажмите Enter или запятую')}"
             autocomplete="off">
    `;

    bindEvents(container);
  }

  function addTag(raw) {
    const trimmed = raw.trim();
    if (!trimmed) return false;
    const val = parseValue ? parseValue(trimmed) : trimmed;
    if (val === null || val === undefined || (typeof val === 'number' && isNaN(val))) return false;
    if (tags.includes(val)) return false;
    tags.push(val);
    if (onUpdate) onUpdate([...tags]);
    return true;
  }

  function removeTag(idx) {
    if (idx < 0 || idx >= tags.length) return;
    tags.splice(idx, 1);
    if (onUpdate) onUpdate([...tags]);
    render();
  }

  function bindEvents(container) {
    const input = container.querySelector('.tag-text-input');
    if (!input) return;

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        if (addTag(input.value)) {
          input.value = '';
          render();
          requestAnimationFrame(() => {
            const newInput = document.getElementById(id)?.querySelector('.tag-text-input');
            if (newInput) newInput.focus();
          });
        }
        return;
      }
      if (e.key === 'Backspace' && input.value === '' && tags.length > 0) {
        removeTag(tags.length - 1);
        requestAnimationFrame(() => {
          const newInput = document.getElementById(id)?.querySelector('.tag-text-input');
          if (newInput) newInput.focus();
        });
      }
    });

    input.addEventListener('paste', (e) => {
      e.preventDefault();
      const text = (e.clipboardData || window.clipboardData).getData('text');
      const parts = text.split(/[,;\n]+/);
      let added = false;
      parts.forEach(p => { if (addTag(p)) added = true; });
      if (added) {
        render();
        requestAnimationFrame(() => {
          const newInput = document.getElementById(id)?.querySelector('.tag-text-input');
          if (newInput) newInput.focus();
        });
      }
    });

    input.addEventListener('blur', () => {
      if (input.value.trim()) {
        if (addTag(input.value)) {
          input.value = '';
          render();
        }
      }
    });

    container.querySelectorAll('.tag-chip-remove').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.dataset.idx);
        removeTag(idx);
      });
    });

    container.addEventListener('click', (e) => {
      if (e.target === container || e.target.classList.contains('tag-chips')) {
        input.focus();
      }
    });
  }

  return { render, addTag, removeTag, getTags: () => [...tags] };
}

window.createTagInput = createTagInput;
