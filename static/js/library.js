/* The recipe list (templates/recipes_list.html): a chip or the order shows the recipes at once, "Made it" toggles,
   and the feedback drawer (stars, a comment and photos, static/js/feedback.js). In the admins' layout trial the
   dropdowns apply when they close and the filter drawer with its button. */
(function () {
  'use strict';

  // Filters: a change loads the list for it; empty choices are left out of the address
  const form = document.querySelector('[data-lib-form]');
  if (form) {
    form.classList.add('is-live');
    form.addEventListener('change', e => {
      const t = e.target;
      if (!t.matches('input[type=checkbox], input[type=radio], select')) return;
      if (t.closest('[data-lv-drawer]')) return;  // the drawer applies with its button
      const pill = t.closest('[data-lv-pill]');
      if (pill && t.type === 'checkbox') { pill.dataset.changed = '1'; return; }  // applies when the pill closes
      form.requestSubmit();
    });

    // Layout trial 1: one dropdown open at a time; it closes on a click outside, and applies what changed
    const pills = [...form.querySelectorAll('[data-lv-pill]')];
    pills.forEach(p => p.addEventListener('toggle', () => {
      if (p.open) pills.forEach(o => { if (o !== p) o.open = false; });
      else if (p.dataset.changed) form.requestSubmit();
    }));
    document.addEventListener('click', e => {
      if (!e.target.closest('[data-lv-pill]')) pills.forEach(p => { p.open = false; });
    });

    // Layout trial 3: the drawer with the filters
    const drawer = form.querySelector('[data-lv-drawer]');
    if (drawer) {
      form.querySelector('[data-lv-open]').addEventListener('click', () => drawer.showModal());
      drawer.querySelector('[data-lv-close]').addEventListener('click', () => drawer.close());
      drawer.addEventListener('click', e => { if (e.target === drawer) drawer.close(); });  // the backdrop
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
