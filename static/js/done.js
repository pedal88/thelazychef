/* The celebration when the last step is ticked off (templates/recipe_v2_make.html, #sheet-done). static/js/steps.js
   says "steps:finished" with how long the cooking took; the sheet opens with a burst of confetti, the dish and the
   time. A signed-in cook saves "I made this" (POST /api/interactions/recipe/<id>/cooked, which counts the times) and
   the stars, comment and photos (static/js/feedback.js). "Cook it again" unticks the steps (steps.js). */
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
  const fb = made && window.Feedback ? window.Feedback.attach(form) : null;
  const still = matchMedia('(prefers-reduced-motion: reduce)');
  let saved = false;
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

  async function open(minutes) {
    sub.textContent = took(minutes);
    saved = false;
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
  // "Cook it again" unticks the steps (steps.js, on the same click) and goes back to them
  dialog.addEventListener('click', e => { if (e.target.closest('[data-steps-reset]')) dialog.close(); });
  dialog.addEventListener('close', () => burst.replaceChildren());

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
      await fb.save();
      saved = true;
      tell(!n ? 'Saved. Thank you.' : n === 1 ? 'Saved. It is in your Made list now.' : `Saved. That was your ${nth(n)} time.`);
      saveBtn.textContent = 'Close';
      saveBtn.disabled = false;
    } catch (err) {
      tell('Something went wrong. Please try again.', true);
      saveBtn.disabled = false;
    }
  });
})();
