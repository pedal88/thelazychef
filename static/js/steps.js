/* The one-page flow's two screens (templates/recipe_v2_make.html): the overview, and cooking at #cook, which hides
   the site's top bar and footer; the back button or × goes back. And the step list on the cooking screen
   (templates/components/step_list.html).
   Tap a step to tick it off; the first step not ticked is marked as the next one. A step with waiting time has a
   button that starts its timer: the running timers stand in a line above the list and the views, and when the
   time is up the timer turns red, beeps and vibrates (static/js/kitchen.js). A step that uses what was standing
   ends its timer. The view menu at the bottom swaps the list for the timeline, the metro map or the river delta,
   which mark the next step. The ticks and timers are kept on this device per recipe, apart from cooking mode's; the chosen view for
   all recipes. The Bowls button shows how many bowls are ready (the board in the sheet is static/js/ready.js). */
(function () {
  'use strict';
  const page = document.querySelector('.make[data-recipe]');
  const list = page && page.querySelector('.slist');
  if (!list) return;
  const { beep, ring, wake, leftMin, fmtLeft, esc } = window.Kitchen;
  const KEY = `steps:${page.dataset.recipe}`, VIEW = 'one-page-view';
  const $ = s => page.querySelector(s), $$ = s => [...page.querySelectorAll(s)];
  const rows = $$('.st[data-st]');
  const byId = Object.fromEntries(rows.map(r => [r.dataset.st, r]));

  let st = { done: [], runs: [] };
  try { Object.assign(st, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch (e) { /* start afresh */ }
  st.done = (st.done || []).filter(id => byId[id]);
  st.runs = (st.runs || []).filter(r => byId[r.step] && r.end > Date.now() - 3 * 3600e3);
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) { /* kept for this visit only */ } };
  const runOf = id => st.runs.find(r => r.step === id);

  function render() {
    const done = new Set(st.done);
    const next = rows.find(r => !done.has(r.dataset.st));
    rows.forEach(r => {
      const on = done.has(r.dataset.st);
      r.classList.toggle('is-done', on);
      r.classList.toggle('is-next', r === next);
      r.querySelector('.st-tick').setAttribute('aria-pressed', String(on));
      const n = r.querySelector('.n');
      n.textContent = on ? '✓' : n.dataset.n;
    });
    marks(next ? next.dataset.st : null);
    runs();
    save();
  }

  /* The timers: a line of chips above the list, and the step's own button */
  function runs() {
    const line = $('[data-runs]');
    line.hidden = !st.runs.length;
    line.innerHTML = st.runs.map(r => {
      const fin = Date.now() >= r.end;
      return `<span class="tm${fin ? ' fin' : ''}"><button type="button" data-run-go="${esc(r.step)}">${esc(r.label)} <b>${fmtLeft(r)}</b></button>`
        + `<button type="button" class="tm-x" data-run-stop="${esc(r.step)}" aria-label="Stop the timer for ${esc(r.label)}">×</button></span>`;
    }).join('');
    rows.forEach(row => {
      const b = row.querySelector('[data-start]');
      if (!b) return;
      const r = runOf(row.dataset.st);
      b.classList.toggle('running', !!r);
      b.querySelector('span').textContent = !r ? `Start ${row.dataset.passive} min`
        : Date.now() >= r.end ? 'Time is up' : `${leftMin(r)} min left`;
    });
  }

  function tick(row) {
    const id = row.dataset.st, i = st.done.indexOf(id);
    if (i >= 0) st.done.splice(i, 1);
    else {
      st.done.push(id);
      // The water has boiled once the pasta is in: a step that used what was standing ends its timer
      const used = (row.dataset.after || '').split(' ');
      st.runs = st.runs.filter(r => !used.includes(r.step));
    }
    render();
  }

  function start(row) {
    if (runOf(row.dataset.st)) return;
    st.runs.push({ step: row.dataset.st, label: row.dataset.label, end: Date.now() + row.dataset.passive * 60e3, rang: false });
    render();
  }

  /* The next step, marked in the timeline, the metro map and the delta */
  function marks(id) {
    $$('.vpanel .cur').forEach(e => e.classList.remove('cur'));
    if (id) {
      $$(`.vpanel [data-step="${id}"], .vpanel [data-station="${id}"]`).forEach(e => e.classList.add('cur'));
      const seg = $(`.vpanel .fx-seg[data-step="${id}"]`);
      if (seg) seg.closest('.g2-node').classList.add('cur');
    }
    const tl = $('.tl'), status = $('[data-tl-status]');
    if (!tl) return;
    const total = +tl.dataset.total, tlRows = $$('.tl-row[data-step]'), here = tlRows.find(r => r.dataset.step === id);
    const m = !id ? total : here ? +here.dataset.start : 0;
    $('.nowline').style.setProperty('--x', (m / total).toFixed(4));
    const doing = tlRows.filter(r => +r.dataset.start <= m && m < +r.dataset.aend).map(r => r.dataset.short);
    const nxt = tlRows.find(r => +r.dataset.start > m);
    if (status) status.innerHTML = `<b>Minute ${m} of ${total} in the plan.</b> `
      + (doing.length ? `Next up: ${esc(doing.join(', '))}. ` : '')
      + (nxt ? `Then: ${esc(nxt.dataset.short.toLowerCase())} at minute ${nxt.dataset.start}.` : 'The food is ready.');
  }

  /* The view menu: the list is the default; the choice is remembered for all recipes */
  const menu = $('.vmenu-list'), menuBtn = $('[data-view-menu]');
  function openMenu(on) {
    if (!menu) return;
    menu.hidden = !on;
    menuBtn.setAttribute('aria-expanded', String(on));
  }
  function view(v) {
    const items = $$('[data-view]');
    if (!items.some(b => b.dataset.view === v)) v = 'steps';
    items.forEach(b => b.setAttribute('aria-checked', String(b.dataset.view === v)));
    const label = $('[data-view-label]'), item = items.find(b => b.dataset.view === v);
    if (label && item) label.textContent = item.textContent;
    $$('.vpanel').forEach(p => { p.hidden = p.dataset.panel !== v; });
    openMenu(false);
    try { localStorage.setItem(VIEW, v); } catch (e) { /* remembered for this visit only */ }
    if (v === 'delta') dispatchEvent(new Event('resize'));  // the delta lays itself out once it can be seen
  }

  /* The two screens. Cooking has its own address (#cook), so the back button, a reload and a shared link work */
  const cook = document.getElementById('cook');
  let overviewY = 0;
  function cooking(on) {
    if (!cook) return;
    const was = !cook.hidden;
    if (on && !was) overviewY = scrollY;
    document.documentElement.classList.toggle('cooking', on);
    cook.hidden = !on;
    if (on && !was) { scrollTo(0, 0); wake(); dispatchEvent(new Event('resize')); }
    if (!on && was) scrollTo(0, overviewY);
    openMenu(false);
  }
  function startCooking() {
    if (location.hash !== '#cook') history.pushState({ cook: true }, '', '#cook');
    cooking(true);
  }
  function stopCooking() {
    if (history.state && history.state.cook) history.back();  // popstate shows the overview
    else { history.replaceState(null, '', location.pathname + location.search); cooking(false); }
  }
  addEventListener('popstate', () => cooking(location.hash === '#cook'));

  /* How many bowls are ready, on the Bowls button, after static/js/ready.js has painted them */
  function bowls() {
    const count = $('[data-bowl-count]');
    if (!count) return;
    const all = $$('#sheet-bowls section > .board > [data-bowl]');
    count.textContent = `${all.filter(b => b.classList.contains('is-ready')).length}/${all.length}`;
  }

  page.addEventListener('click', e => {
    beep(true); wake();
    const t = e.target;
    if (t.closest('[data-cook-open]')) { e.preventDefault(); startCooking(); return; }
    if (t.closest('[data-cook-close]')) { stopCooking(); return; }
    if (t.closest('[data-view-menu]')) { openMenu(menu.hidden); return; }
    if (menu && !menu.hidden && !t.closest('.vmenu')) openMenu(false);
    const go = t.closest('[data-run-go]'), stop = t.closest('[data-run-stop]');
    if (stop) { st.runs = st.runs.filter(r => r.step !== stop.dataset.runStop); render(); return; }
    if (go) {
      const row = byId[go.dataset.runGo];
      view('steps');
      if (row) row.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
      return;
    }
    if (t.closest('[data-view]')) { view(t.closest('[data-view]').dataset.view); return; }
    if (t.closest('[data-steps-reset]')) { st = { done: [], runs: [] }; render(); return; }
    const row = t.closest('.st[data-st]');
    if (!row) { setTimeout(bowls); return; }
    if (t.closest('[data-start]')) { start(row); return; }
    if (t.closest('a')) return;  // a link in a step is followed, not a tick
    tick(row);
  });

  setInterval(() => {
    let rang = false;
    st.runs.forEach(r => { if (!r.rang && Date.now() >= r.end) { r.rang = rang = true; ring(); } });
    if (rang) render(); else if (st.runs.length) runs();
  }, 1000);

  /* The bowls over the whole screen, scaled down until everything fits without scrolling. Below MIN the text
     gets too small to read in a kitchen, so it stops there and scrolls. Again when a bowl is opened or closed,
     and when the window changes. Closes on ×, Esc or a drag down. */
  const sheet = document.getElementById('sheet-bowls'), MIN = 0.55;
  function fit() {
    const box = sheet && sheet.querySelector('[data-fit]'), inner = box && box.firstElementChild;
    if (!inner || !sheet.open) return;
    const fits = z => { inner.style.zoom = z; return inner.getBoundingClientRect().height <= box.clientHeight + 1; };
    box.classList.remove('scrolls');
    if (!fits(1)) {
      // The largest size that fits: a smaller board gets more columns, so the height does not follow the size
      let lo = MIN, hi = 1;
      if (fits(MIN)) {
        for (let k = 0; k < 7; k++) { const mid = (lo + hi) / 2; if (fits(mid)) lo = mid; else hi = mid; }
      }
      inner.style.zoom = lo;
    }
    box.classList.toggle('scrolls', inner.getBoundingClientRect().height > box.clientHeight + 1);
  }
  if (sheet) {
    let y0 = null;
    sheet.addEventListener('touchstart', e => {
      const box = sheet.querySelector('[data-fit]');
      y0 = !box.classList.contains('scrolls') || box.scrollTop <= 0 ? e.touches[0].clientY : null;
    }, { passive: true });
    sheet.addEventListener('touchend', e => {
      if (y0 !== null && e.changedTouches[0].clientY - y0 > 90) sheet.close();
      y0 = null;
    });
    sheet.addEventListener('toggle', () => requestAnimationFrame(fit), true);  // a bowl opened or closed
    sheet.addEventListener('close', bowls);
    document.addEventListener('click', e => { if (e.target.closest('[data-sheet="sheet-bowls"]')) requestAnimationFrame(fit); });
    let t;
    addEventListener('resize', () => { clearTimeout(t); t = setTimeout(fit, 120); });
  }

  document.addEventListener('keydown', e => { if (e.key === 'Escape') openMenu(false); });

  try { view(localStorage.getItem(VIEW)); } catch (e) { view('steps'); }
  // Prep and Cook lead here as #prep and #cook: both open the cooking screen, #prep with the bowls
  if (location.hash === '#cook' || location.hash === '#prep') {
    const bowlsFirst = location.hash === '#prep';
    // The overview goes underneath in the history, so × and the back button lead to it, not off the page
    history.replaceState(null, '', location.pathname + location.search);
    history.pushState({ cook: true }, '', '#cook');
    cooking(true);
    if (bowlsFirst && sheet && sheet.showModal) { sheet.showModal(); requestAnimationFrame(fit); }
  }
  wake();
  render();
  bowls();
})();
