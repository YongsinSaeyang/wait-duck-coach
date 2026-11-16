/* Common interactions work on every generated page. */
(() => {
  'use strict';
  const storageKey = 'wait-duck-notes:saved:v1';
  let saved = new Set();
  let category = 'all';
  let index = [];
  let toastTimer;
  try {
    const parsed = JSON.parse(localStorage.getItem(storageKey) || '[]');
    if (Array.isArray(parsed)) saved = new Set(parsed.filter(id => typeof id === 'string'));
  } catch { /* Reading the notebook remains possible without local storage. */ }
  const toast = message => {
    const target = document.querySelector('#toast');
    if (!target) return;
    target.textContent = message;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { target.textContent = ''; }, 2200);
  };
  const updateSaved = () => {
    document.querySelectorAll('[data-save]').forEach(button => {
      const active = saved.has(button.dataset.save);
      button.setAttribute('aria-pressed', String(active));
      button.textContent = active ? '♥ 已收藏' : '♡ 收藏';
    });
  };
  const search = document.querySelector('#search');
  const normalize = value => value.normalize('NFKC').toLocaleLowerCase('zh-TW');
  const applyFilters = () => {
    const query = normalize(search?.value.trim() || '');
    let count = 0;
    document.querySelectorAll('.library-content [data-note]').forEach(card => {
      const note = index.find(n => n.id === card.dataset.note);
      const text = note ? [note.title, note.summary, ...note.tags, note.body].join(' ') : card.textContent;
      const rightCategory = category === 'all' || (category === 'saved' ? saved.has(card.dataset.note) : (note?.category || card.querySelector('.category')?.textContent) === category);
      card.hidden = !rightCategory || !normalize(text).includes(query);
      if (!card.hidden) count += 1;
    });
    const status = document.querySelector('#result-count');
    if (status) status.textContent = '共 ' + count + ' 篇筆記';
    const empty = document.querySelector('#empty');
    if (empty) empty.hidden = count > 0;
  };
  document.addEventListener('click', event => {
    const save = event.target.closest('[data-save]');
    if (save) {
      const id = save.dataset.save;
      if (saved.has(id)) saved.delete(id); else saved.add(id);
      try {
        localStorage.setItem(storageKey, JSON.stringify([...saved]));
        toast(saved.has(id) ? '已加入這台裝置的收藏' : '已取消收藏');
      } catch { toast('這次收藏暫存在目前頁面'); }
      updateSaved();
      applyFilters();
    }
    const filter = event.target.closest('[data-category]');
    if (filter) {
      category = filter.dataset.category;
      document.querySelectorAll('[data-category]').forEach(button => button.setAttribute('aria-pressed', String(button === filter)));
      applyFilters();
    }
    if (event.target.closest('#reset')) {
      category = 'all';
      search.value = '';
      document.querySelectorAll('[data-category]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.category === 'all')));
      applyFilters();
    }
  });
  if (search) {
    search.addEventListener('input', applyFilters);
    const script = document.currentScript || document.querySelector('script[src$="site.js"]');
    const url = new URL('notes.json', script.src);
    fetch(url).then(response => {
      if (!response.ok) throw new Error('Search index unavailable');
      return response.json();
    }).then(notes => { index = notes; applyFilters(); }).catch(() => {
      toast('搜尋暫以標題、摘要和標籤比對');
    });
  }
  const decline = document.querySelector('#decline');
  if (decline) {
    const update = () => {
      const d = Number(decline.value) / 100;
      document.querySelector('#decline-value').value = decline.value + '%';
      document.querySelector('#recovery').textContent = (d / (1 - d) * 100).toFixed(2) + '%';
      document.querySelector('#recovery-formula').textContent = decline.value + '% ÷ (1 − ' + decline.value + '%)';
    };
    decline.addEventListener('input', update);
    update();
  }
  window.addEventListener('storage', event => {
    if (event.key !== storageKey) return;
    try {
      const parsed = JSON.parse(event.newValue || '[]');
      saved = new Set(Array.isArray(parsed) ? parsed.filter(x => typeof x === 'string') : []);
      updateSaved(); applyFilters();
    } catch { /* Ignore malformed storage updates. */ }
  });
  updateSaved();
})();
