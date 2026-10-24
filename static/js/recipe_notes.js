/* Admin notes on a recipe (templates/components/recipe_notes.html), in the floating admin chip.
   Saves without leaving the page, so the place in cooking mode and the timers stay, and adds where on the page
   the note was written: on Cook and in the one-page flow the step on screen. An unsaved note is kept on this
   device until it is saved, so a reload (other servings, another look) does not lose it. */
(function () {
  'use strict';
  const draftKey = box => `note-draft:${box.dataset.recipeId}`;

  function where(box) {
    const page = box.dataset.page;
    if (document.querySelector('.make')) {  // the one-page flow: the overview, or cooking at the next step
      if (!document.documentElement.classList.contains('cooking')) return `${page} · overview`;
      const next = document.querySelector('.st.is-next');
      return next ? `${page} · cooking · step ${next.querySelector('.n').dataset.n} (${next.dataset.label})` : `${page} · cooking`;
    }
    const card = document.querySelector('.cook .card[data-step]:not([hidden])');
    if (card && (page === 'cook' || page === 'make')) return `${page} · step ${card.dataset.no} (${card.dataset.label})`;
    return page;
  }

  function prepare(box) {
    if (!box) return;
    const text = box.querySelector('[data-note-form] textarea');
    try { if (text && !text.value) text.value = localStorage.getItem(draftKey(box)) || ''; } catch (e) { /* no draft */ }
    const shown = box.querySelector('[data-note-where]');
    if (shown) shown.textContent = where(box);
  }

  async function send(form, box) {
    const res = await fetch(form.action, { method: 'POST', body: new FormData(form), headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin' });
    if (!res.ok) throw new Error(res.status);
    const html = await res.text();
    const tmp = document.createElement('div');
    tmp.innerHTML = html.trim();
    const fresh = tmp.firstElementChild;
    box.replaceWith(fresh);
    prepare(fresh);
    return fresh;
  }

  document.addEventListener('submit', async e => {
    const form = e.target.closest('[data-note-form], [data-note-done]');
    if (!form) return;
    e.preventDefault();
    const box = form.closest('[data-notes]');
    const adding = form.hasAttribute('data-note-form');
    const draft = adding ? form.text.value : null;
    if (adding) {
      if (!draft.trim()) return;
      form.place.value = where(box);
      try { localStorage.removeItem(draftKey(box)); } catch (err) { /* nothing kept */ }
    }
    const button = form.querySelector('button[type="submit"]');
    if (button) button.disabled = true;
    try {
      const fresh = await send(form, box);
      if (adding) {
        const saved = fresh.querySelector('[data-note-where]');
        if (saved) saved.textContent = 'Saved';
        fresh.querySelector('[data-note-form] textarea').focus();
      }
    } catch (err) {
      if (button) button.disabled = false;
      if (draft) try { localStorage.setItem(draftKey(box), draft); } catch (e2) { /* not kept */ }
      const shown = box.querySelector('[data-note-where]');
      if (shown) shown.textContent = 'Not saved. Try again.';
    }
  });

  document.addEventListener('input', e => {
    const box = e.target.closest('[data-notes]');
    if (!box || !e.target.matches('[data-note-form] textarea')) return;
    try { localStorage.setItem(draftKey(box), e.target.value); } catch (err) { /* not kept */ }
    const shown = box.querySelector('[data-note-where]');
    if (shown) shown.textContent = where(box);
  });

  document.addEventListener('keydown', e => {
    // Cmd or Ctrl + Enter saves
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && e.target.matches('[data-note-form] textarea')) {
      e.preventDefault();
      e.target.form.requestSubmit();
    }
  });

  document.addEventListener('click', async e => {
    const copy = e.target.closest('[data-note-copy]');
    if (!copy) return;
    const text = copy.closest('[data-notes]').querySelector('[data-note-text]').value;
    try {
      await navigator.clipboard.writeText(text);
      copy.textContent = 'Copied';
    } catch (err) {
      window.prompt('Copy the notes:', text);  // no clipboard access (http, or not allowed)
    }
    setTimeout(() => { copy.textContent = 'Copy for Claude'; }, 2000);
  });

  // Where the note will be written updates when the chip opens: the step on screen may have changed
  document.addEventListener('toggle', e => {
    if (e.target.matches && e.target.matches('[data-trial]') && e.target.open) prepare(e.target.querySelector('[data-notes]'));
  }, true);
  prepare(document.querySelector('[data-notes]'));
})();
