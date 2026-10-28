/* The recipe list (templates/recipes_list.html): a chip or the order shows the recipes at once, "Made it" toggles,
   and the feedback drawer (stars, a comment and photos, static/js/feedback.js). */
(function () {
  'use strict';

  // Filters: a change loads the list for it; empty choices are left out of the address
  const form = document.querySelector('[data-lib-form]');
  if (form) {
    form.classList.add('is-live');
    form.addEventListener('change', e => {
      if (e.target.matches('input[type=checkbox], input[type=radio], select')) form.requestSubmit();
    });
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
