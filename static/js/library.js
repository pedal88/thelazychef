/* The recipe list (templates/recipes_list.html): a chip or the order shows the recipes at once, "Made it" toggles,
   and the feedback drawer (stars, a comment and photos) saves to /api/interactions/recipe/<id>/feedback. In the
   admins' layout trial the dropdowns apply when they close and the filter drawer with its button. */
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

  const sprite = (document.querySelector('svg.icon use') || { getAttribute: () => '' }).getAttribute('href').split('#')[0];
  const icon = name => `<svg class="icon" aria-hidden="true" focusable="false"><use href="${sprite}#i-${name}"/></svg>`;

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
  if (!dialog) return;
  const fbForm = dialog.querySelector('[data-fb-form]');
  const stars = [...dialog.querySelectorAll('.fb-stars label')];
  const photos = dialog.querySelector('[data-fb-photos]');
  const fresh = dialog.querySelector('[data-fb-new]');
  const keptBox = dialog.querySelector('[data-fb-kept]');
  const status = dialog.querySelector('[data-fb-status]');
  const save = dialog.querySelector('.fb-save');
  let recipeId = null;
  let kept = [];  // photos saved before that are to stay

  function paint(n) {
    stars.forEach((label, i) => label.classList.toggle('on', i < n));
  }
  const rating = () => Number((fbForm.querySelector('input[name=rating]:checked') || {}).value || 0);
  stars.forEach((label, i) => {
    label.addEventListener('mouseenter', () => paint(i + 1));
    label.addEventListener('mouseleave', () => paint(rating()));
  });
  fbForm.addEventListener('change', e => { if (e.target.name === 'rating') paint(rating()); });

  function thumb(src, onRemove) {
    const box = document.createElement('div');
    box.className = 'fb-thumb';
    const img = document.createElement('img');
    img.src = src;
    img.alt = '';
    box.append(img);
    if (onRemove) {
      const x = document.createElement('button');
      x.type = 'button';
      x.setAttribute('aria-label', 'Remove the photo');
      x.innerHTML = icon('close');
      x.addEventListener('click', onRemove);
      box.append(x);
    }
    return box;
  }
  function showKept() {
    keptBox.replaceChildren(...kept.map((url, i) => thumb(url, () => { kept.splice(i, 1); showKept(); })));
  }
  photos.addEventListener('change', () => {
    fresh.replaceChildren(...[...photos.files].slice(0, 5).map(f => thumb(URL.createObjectURL(f))));
  });

  function say(text, error) {
    status.textContent = text;
    status.classList.toggle('is-error', !!error);
    status.hidden = false;
  }

  document.addEventListener('click', async e => {
    const btn = e.target.closest('[data-feedback]');
    if (!btn) return;
    e.preventDefault();
    recipeId = btn.dataset.feedback;
    fbForm.reset();
    paint(0);
    fresh.replaceChildren();
    kept = [];
    showKept();
    status.hidden = true;
    save.disabled = false;
    dialog.querySelector('[data-fb-title]').textContent = btn.dataset.title;
    dialog.showModal();
    try {
      const data = await (await fetch(`/api/interactions/recipe/${recipeId}`)).json();
      if (data.rating) {
        const r = fbForm.querySelector(`input[name=rating][value="${data.rating}"]`);
        if (r) r.checked = true;
        paint(data.rating);
      }
      if (data.comment) fbForm.elements.comment.value = data.comment;
      kept = [...(data.user_photos || [])];
      showKept();
    } catch (err) {
      console.error('Could not load the feedback', err);
    }
  });

  dialog.querySelectorAll('[data-fb-close]').forEach(b => b.addEventListener('click', () => dialog.close()));
  dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });  // the backdrop

  fbForm.addEventListener('submit', async e => {
    e.preventDefault();
    save.disabled = true;
    const body = new FormData(fbForm);
    body.set('keep_photos', JSON.stringify(kept));
    try {
      const data = await (await fetch(`/api/interactions/recipe/${recipeId}/feedback`, { method: 'POST', body })).json();
      if (!data.success) throw new Error('not saved');
      say('Saved. Thank you.');
      setTimeout(() => dialog.close(), 1200);
    } catch (err) {
      say('Something went wrong. Please try again.', true);
      save.disabled = false;
    }
  });
})();
