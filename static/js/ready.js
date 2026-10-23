/* Prep (templates/recipe_v2_ready.html): one tap marks a bowl (on its number), a tile, a task or a piece of equipment
   as ready; a tap elsewhere on a bowl opens it.
   The ticks are kept on this device, per recipe. Only the bowls count towards the meter: they are what you make. */
(function () {
  'use strict';
  const page = document.querySelector('.ready[data-recipe]');
  if (!page) return;
  const key = `ready:${page.dataset.recipe}`;
  let done;
  try { done = new Set((localStorage.getItem(key) || '').split(' ').filter(Boolean)); } catch (e) { done = new Set(); }
  const save = () => { try { localStorage.setItem(key, [...done].join(' ')); } catch (e) { /* private mode: ticks last for the visit */ } };

  function paint() {
    page.querySelectorAll('[data-tick]').forEach(b => {
      const on = done.has(b.dataset.tick);
      b.setAttribute('aria-pressed', String(on));
      const no = b.querySelector('.bno');
      if (no) no.textContent = on ? '✓' : no.dataset.no;
      const bowl = b.closest('[data-bowl]');
      if (bowl) bowl.classList.toggle('is-ready', on);
    });
    // The bowls for now, not the ones for later
    const bowls = [...page.querySelectorAll('.ready-main > section [data-bowl]')];
    const n = bowls.filter(b => done.has(b.dataset.key)).length;
    const bar = page.querySelector('.meter span'), count = page.querySelector('[data-count]');
    if (bar) bar.style.width = `${(n / Math.max(1, bowls.length)) * 100}%`;
    if (count) count.innerHTML = bowls.length && n === bowls.length
      ? '<b>All the bowls are ready.</b> Now the heat can go on.' : `${n} of ${bowls.length} bowls ready`;
  }

  page.addEventListener('click', e => {
    if (e.target.closest('[data-reset]')) { done.clear(); save(); paint(); return; }
    const b = e.target.closest('[data-tick]');
    if (!b) return;
    // The tick in a bowl's summary must not also open or close the bowl
    if (b.closest('summary')) e.preventDefault();
    done.has(b.dataset.tick) ? done.delete(b.dataset.tick) : done.add(b.dataset.tick);
    save();
    paint();
  });
  paint();
})();
