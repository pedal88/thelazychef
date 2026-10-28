/* Feedback on a recipe: the stars, comment and photos of templates/components/feedback_fields.html, loaded from
   /api/interactions/recipe/<id> and saved to /api/interactions/recipe/<id>/feedback. Used by the recipe list's
   drawer (static/js/library.js) and the celebration after the last step (static/js/done.js).
   Feedback.attach(form) returns { open(id), save(), say(text, error) }; open clears the form and fills in what was
   saved before, and resolves with the stored interaction (made_count, last_made_at, …) or null. */
(function () {
  'use strict';
  const sprite = (document.querySelector('svg.icon use') || { getAttribute: () => '' }).getAttribute('href').split('#')[0];
  const icon = name => `<svg class="icon" aria-hidden="true" focusable="false"><use href="${sprite}#i-${name}"/></svg>`;

  function attach(form) {
    const stars = [...form.querySelectorAll('.fb-stars label')];
    const photos = form.querySelector('[data-fb-photos]');
    const fresh = form.querySelector('[data-fb-new]');
    const keptBox = form.querySelector('[data-fb-kept]');
    const status = form.querySelector('[data-fb-status]');
    let recipeId = null;
    let kept = [];  // photos saved before that are to stay

    const paint = n => stars.forEach((label, i) => label.classList.toggle('on', i < n));
    const rating = () => Number((form.querySelector('input[name=rating]:checked') || {}).value || 0);
    stars.forEach((label, i) => {
      label.addEventListener('mouseenter', () => paint(i + 1));
      label.addEventListener('mouseleave', () => paint(rating()));
    });
    form.addEventListener('change', e => { if (e.target.name === 'rating') paint(rating()); });

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
      status.hidden = !text;
    }

    async function open(id) {
      recipeId = id;
      form.reset();
      paint(0);
      fresh.replaceChildren();
      kept = [];
      showKept();
      say('');
      try {
        const data = await (await fetch(`/api/interactions/recipe/${recipeId}`)).json();
        if (data.rating) {
          const r = form.querySelector(`input[name=rating][value="${data.rating}"]`);
          if (r) r.checked = true;
          paint(data.rating);
        }
        if (data.comment) form.elements.comment.value = data.comment;
        kept = [...(data.user_photos || [])];
        showKept();
        return data;
      } catch (err) {
        console.error('Could not load the feedback', err);
        return null;
      }
    }

    async function save() {
      const body = new FormData(form);
      body.set('keep_photos', JSON.stringify(kept));
      const data = await (await fetch(`/api/interactions/recipe/${recipeId}/feedback`, { method: 'POST', body })).json();
      if (!data.success) throw new Error('not saved');
    }

    return { open, save, say };
  }

  window.Feedback = { attach, icon };
})();
