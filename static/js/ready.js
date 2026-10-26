/* Prep (templates/recipe_v2_ready.html): one tap marks a bowl (on its number), a tile, a task or a piece of equipment
   as ready; a tap elsewhere on a bowl opens it.
   The ticks are kept on this device, per recipe. Only the bowls count towards the meter: they are what you make.
   On the one-page flow (templates/recipe_v2_make.html) a bowl that prep steps fill (data-steps) has no tick of its
   own: it is ready when those steps are ticked off, and a tap on it ticks them off or back on. static/js/steps.js
   keeps the steps and tells this page ("steps:done"); this page asks it to tick ("ready:steps"). The button under the
   bowls marks those not ticked yet as ready and starts the cooking ("ready:go"). */
(function () {
  'use strict';
  const page = document.querySelector('.ready[data-recipe]');
  if (!page) return;
  const key = `ready:${page.dataset.recipe}`;
  let done;
  try { done = new Set((localStorage.getItem(key) || '').split(' ').filter(Boolean)); } catch (e) { done = new Set(); }
  const save = () => { try { localStorage.setItem(key, [...done].join(' ')); } catch (e) { /* private mode: ticks last for the visit */ } };
  let stepsDone = null;  // the steps ticked off on the cooking screen, once static/js/steps.js has said
  const stepsOf = el => { const b = el.closest('[data-bowl]'); return b && b.dataset.steps ? b.dataset.steps.split(' ') : []; };
  const linked = el => !!stepsDone && stepsOf(el).length > 0;
  const isOn = el => linked(el) ? stepsOf(el).every(s => stepsDone.has(s)) : done.has(el.dataset.tick);
  const tell = (name, detail) => page.dispatchEvent(new CustomEvent(name, { detail }));
  // The bowls for now: not the ones for later, until the wait they are for has started (static/js/steps.js marks it)
  const nowBowls = () => [...page.querySelectorAll('section > .board > [data-bowl], .later.is-now [data-bowl]')];

  function paint() {
    page.querySelectorAll('[data-tick]').forEach(b => {
      const on = isOn(b);
      b.setAttribute('aria-pressed', String(on));
      const no = b.querySelector('.bno');
      if (no) no.textContent = on ? '✓' : no.dataset.no;
      const bowl = b.closest('[data-bowl]');
      if (bowl) bowl.classList.toggle('is-ready', on);
    });
    const bowls = nowBowls();
    const n = bowls.filter(b => b.classList.contains('is-ready')).length;
    const bar = page.querySelector('.meter span'), count = page.querySelector('[data-count]');
    if (bar) bar.style.width = `${(n / Math.max(1, bowls.length)) * 100}%`;
    if (count) count.innerHTML = bowls.length && n === bowls.length
      ? '<b>All the bowls are ready.</b> Now the heat can go on.' : `${n} of ${bowls.length} bowls ready`;
  }

  page.addEventListener('steps:done', e => { stepsDone = new Set(e.detail); paint(); });

  page.addEventListener('click', e => {
    if (e.target.closest('[data-reset]')) { done.clear(); save(); paint(); tell('ready:change'); return; }
    if (e.target.closest('[data-bowls-go]')) {
      const steps = [];
      nowBowls().forEach(b => {
        const t = b.querySelector('[data-tick]');
        if (linked(t)) steps.push(...stepsOf(t)); else done.add(t.dataset.tick);
      });
      save();
      paint();
      tell('ready:steps', { steps, on: true });
      tell('ready:go');
      return;
    }
    const b = e.target.closest('[data-tick]');
    if (!b) return;
    // The tick in a bowl's summary must not also open or close the bowl
    if (b.closest('summary')) e.preventDefault();
    if (linked(b)) { tell('ready:steps', { steps: stepsOf(b), on: !isOn(b) }); return; }
    done.has(b.dataset.tick) ? done.delete(b.dataset.tick) : done.add(b.dataset.tick);
    save();
    paint();
    tell('ready:change');
  });
  paint();
})();
