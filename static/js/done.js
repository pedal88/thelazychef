/* The celebration when the last step is ticked off (templates/recipe_v2_make.html, #sheet-done). static/js/steps.js
   says "steps:finished" with how long the cooking took; the sheet opens with a burst of confetti, the dish and the
   time. A signed-in cook saves "I made this" (POST /api/interactions/recipe/<id>/cooked, which counts the times) and
   the stars, comment and photos (static/js/feedback.js). "Cook it again" unticks the steps (steps.js); closing the
   sheet once the meal is saved unticks them too and goes back to the recipe ("steps:clear", steps.js). Made it on the
   overview and below the steps ([data-made-it]) open it at any time: most people cook without ticking every step. */
(function () {
  'use strict';
  const page = document.querySelector('.make[data-recipe]');
  const dialog = document.getElementById('sheet-done');
  if (!page || !dialog || !dialog.showModal) return;
  const id = page.dataset.recipe;
  const form = dialog.querySelector('[data-done-form]');
  const sub = dialog.querySelector('[data-done-sub]');
  const made = dialog.querySelector('[data-done-made]');
  const count = dialog.querySelector('[data-done-count]');
  const saveBtn = dialog.querySelector('[data-done-save]');
  const burst = dialog.querySelector('[data-done-burst]');
  const steps = dialog.querySelector('[data-done-steps]');
  const fb = made && window.Feedback ? window.Feedback.attach(form) : null;
  const still = matchMedia('(prefers-reduced-motion: reduce)');
  let saved = false;
  let again = false;  // "Cook it again" closes the sheet to cook, not to go back to the recipe
  // The answer below the fields, scrolled to where it can be seen
  const tell = (text, error) => { fb.say(text, error); form.querySelector('[data-fb-status]').scrollIntoView({ block: 'nearest', behavior: 'smooth' }); };

  const times = n => (n === 1 ? 'once' : n === 2 ? 'twice' : `${n} times`);
  const nth = n => n + ({ 1: 'st', 2: 'nd', 3: 'rd' }[(n % 100 > 10 && n % 100 < 14) ? 0 : n % 10] || 'th');
  const when = iso => new Date(`${iso}Z`).toLocaleDateString(undefined, { day: 'numeric', month: 'long' });

  function took(minutes) {
    const title = sub.dataset.title, plan = +sub.dataset.plan;
    if (minutes === null || minutes < 5) return `You made ${title}.`;
    const diff = plan ? minutes - plan : 0;
    const vs = !plan ? '' : Math.abs(diff) <= 2 ? ', right on the plan' : diff < 0 ? `, ${-diff} under the plan` : `, the plan said ${plan}`;
    return `You made ${title} in ${minutes} minutes${vs}.`;
  }

  function confetti() {
    if (still.matches) return;
    const colors = ['--color-accent', '--color-serve', '--color-prep', '--color-warning', '--color-cook'];
    burst.replaceChildren(...Array.from({ length: 36 }, (_, i) => {
      const bit = document.createElement('i');
      bit.style.setProperty('--x', `${Math.round((Math.random() - 0.5) * 340)}px`);
      bit.style.setProperty('--y', `${Math.round(-60 - Math.random() * 160)}px`);
      bit.style.setProperty('--r', `${Math.round(Math.random() * 720 - 360)}deg`);
      bit.style.setProperty('--d', `${(Math.random() * 0.25).toFixed(2)}s`);
      bit.style.background = `var(${colors[i % colors.length]})`;
      return bit;
    }));
  }

  async function open(minutes, early) {
    sub.textContent = took(minutes);
    steps.textContent = early ? 'Made it' : steps.dataset.all;
    saved = false;
    again = false;
    if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'Save'; }
    if (!dialog.open) dialog.showModal();
    confetti();
    if (!fb) return;
    const data = await fb.open(id);
    made.checked = true;
    const n = data ? data.made_count : 0, last = data && data.last_made_at ? new Date(`${data.last_made_at}Z`) : null;
    count.textContent = !n ? 'The first time. It goes in your Made list.'
      : last && Date.now() - last < 3 * 3600e3 ? `Counted already: ${times(n)} so far.`
      : `You have made it ${times(n)} before${data.last_made_at ? `, last on ${when(data.last_made_at)}` : ''}.`;
  }

  page.addEventListener('steps:finished', e => open(e.detail ? e.detail.minutes : null));
  document.addEventListener('click', e => { if (e.target.closest('[data-made-it]')) open(null, true); });
  // "Cook it again" unticks the steps (steps.js, on the same click) and goes back to them
  dialog.addEventListener('click', e => { if (e.target.closest('[data-steps-reset]')) { again = true; dialog.close(); } });
  dialog.addEventListener('close', () => {
    burst.replaceChildren();
    if (saved && !again) page.dispatchEvent(new CustomEvent('steps:clear'));
  });

  form.addEventListener('submit', async e => {
    e.preventDefault();
    if (!fb) return;
    if (saved) { dialog.close(); return; }
    saveBtn.disabled = true;
    try {
      let n = 0;
      if (made.checked) {
        const data = await (await fetch(`/api/interactions/recipe/${id}/cooked`, { method: 'POST' })).json();
        if (!data.success) throw new Error('not saved');
        n = data.made_count;
      }
      const missed = await fb.save();
      saved = true;
      page.dataset.noted = '1';
      const done = !n ? 'Saved. Thank you.' : n === 1 ? 'Saved. It is in your Made list now.' : `Saved. That was your ${nth(n)} time.`;
      tell(missed ? `${done} ${missed}` : done, !!missed);
      saveBtn.textContent = 'Close';
      saveBtn.disabled = false;
    } catch (err) {
      tell(err.friendly || 'Something went wrong. Please try again.', true);
      saveBtn.disabled = false;
    }
  });
  // A change after saving (a photo added or removed, the comment edited) is saved again rather than closed away
  const unsave = () => { if (saved) { saved = false; saveBtn.textContent = 'Save'; } };
  form.addEventListener('change', unsave);
  form.addEventListener('input', unsave);
})();
