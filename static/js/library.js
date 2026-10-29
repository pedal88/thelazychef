/* The recipe list (templates/recipes_list.html): the bar takes the top bar's paper once it sticks, the title opens
   the other lists, the search follows your typing, the filter drawer counts the cards as you choose and applies with
   its button, "Made it" toggles, and the feedback drawer (stars, a comment and photos, static/js/feedback.js). */
(function () {
  'use strict';

  const form = document.querySelector('[data-lib-form]');
  if (form) {
    // The bar is in the page's colour until it sticks under the top bar (a mark just above it scrolls out of view)
    const mark = document.querySelector('[data-lbar-mark]');
    if (mark && 'IntersectionObserver' in window) {
      new IntersectionObserver(([e]) => form.classList.toggle('is-stuck', !e.isIntersecting),
        { rootMargin: '-64px 0px 0px 0px' }).observe(mark);
    }

    // The list switcher under the title closes on a click outside it or on Escape
    const views = form.querySelector('[data-lbar-views]');
    if (views) {
      document.addEventListener('click', e => { if (!views.contains(e.target)) views.open = false; });
      document.addEventListener('keydown', e => { if (e.key === 'Escape') views.open = false; });
    }

    // The choices as an address, without the empty ones and the default order
    const params = () => {
      const p = new URLSearchParams();
      for (const [k, v] of new FormData(form)) if (String(v).trim() && !(k === 'sort' && v === 'new')) p.append(k, v);
      return p;
    };

    // The filter drawer
    const drawer = form.querySelector('[data-lv-drawer]');
    if (drawer) {
      // The button counts the cards as you choose, and choices that would give none are dimmed
      let counting = 0;
      const recount = async () => {
        if (!drawer.dataset.count) return;
        const mine = ++counting;
        try {
          const data = await (await fetch(`${drawer.dataset.count}?${params()}`)).json();
          if (mine !== counting) return;
          drawer.querySelector('[data-lv-n]').textContent = `${data.total} ${data.total === 1 ? 'recipe' : 'recipes'}`;
          const empty = new Set(data.empty.map(([k, v]) => `${k}=${v}`));
          drawer.querySelectorAll('.lib-chip input').forEach(input => {
            const none = !input.checked && empty.has(`${input.name}=${input.value}`);
            input.disabled = none;
            input.closest('.lib-chip').classList.toggle('is-empty', none);
          });
        } catch (err) {
          console.error('Could not count the recipes', err);
        }
      };
      drawer.addEventListener('change', recount);
      form.querySelector('[data-lv-open]').addEventListener('click', () => { drawer.showModal(); recount(); });
      drawer.querySelector('[data-lv-close]').addEventListener('click', () => drawer.close());
      drawer.addEventListener('click', e => { if (e.target === drawer) drawer.close(); });  // the backdrop
    }

    // The list follows the search as you type, without loading the page (the parts marked data-lv-swap are taken
    // from the new page)
    {
      const box = form.querySelector('input[name=q]');
      let timer = null;
      let asked = 0;
      box.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(async () => {
          const mine = ++asked;
          const url = `${form.action}?${params()}`;
          const results = document.querySelector('[data-lv-swap="results"]');
          if (results) results.setAttribute('aria-busy', 'true');
          try {
            const page = new DOMParser().parseFromString(await (await fetch(url)).text(), 'text/html');
            if (mine !== asked) return;
            page.querySelectorAll('[data-lv-swap]').forEach(fresh => {
              const old = document.querySelector(`[data-lv-swap="${fresh.dataset.lvSwap}"]`);
              if (old) old.replaceWith(document.importNode(fresh, true));
            });
            history.replaceState(null, '', url);
          } catch (err) {
            console.error('Could not search', err);
            if (results) results.removeAttribute('aria-busy');
          }
        }, 350);
      });
    }
    form.addEventListener('search', () => form.requestSubmit());  // the search field's clear button
    form.addEventListener('submit', () => {
      form.querySelectorAll('input, select').forEach(el => {
        if ((el.name === 'sort' && el.value === 'new') || (el.type !== 'checkbox' && el.type !== 'radio' && !el.value.trim())
            || (el.type === 'radio' && el.checked && !el.value)) el.disabled = true;
      });
    });
  }

  // Made it
  document.addEventListener('click', async e => {
    const btn = e.target.closest('[data-made]');
    if (!btn) return;
    e.preventDefault();  // on a card the button sits in its link
    btn.disabled = true;
    try {
      const resp = await fetch(`/api/interactions/recipe/${btn.dataset.made}/made`, { method: 'PATCH' });
      const data = await resp.json();
      if (data.success) btn.setAttribute('aria-pressed', data.is_made ? 'true' : 'false');
    } catch (err) {
      console.error('Could not mark the recipe as made', err);
    } finally {
      btn.disabled = false;
    }
  });

  // Feedback
  const dialog = document.getElementById('feedback');
  if (!dialog || !window.Feedback) return;
  const fbForm = dialog.querySelector('[data-fb-form]');
  const fb = window.Feedback.attach(fbForm);
  const save = dialog.querySelector('.fb-save');

  document.addEventListener('click', e => {
    const btn = e.target.closest('[data-feedback]');
    if (!btn) return;
    e.preventDefault();  // on a card the button sits in its link
    save.disabled = false;
    dialog.querySelector('[data-fb-title]').textContent = btn.dataset.title;
    dialog.showModal();
    fb.open(btn.dataset.feedback);
  });

  dialog.querySelectorAll('[data-fb-close]').forEach(b => b.addEventListener('click', () => dialog.close()));
  dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });  // the backdrop

  fbForm.addEventListener('submit', async e => {
    e.preventDefault();
    save.disabled = true;
    try {
      await fb.save();
      fb.say('Saved. Thank you.');
      setTimeout(() => dialog.close(), 1200);
    } catch (err) {
      fb.say('Something went wrong. Please try again.', true);
      save.disabled = false;
    }
  });
})();
