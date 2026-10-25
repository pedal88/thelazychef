/* The one-page flow's two screens (templates/recipe_v2_make.html): the overview, and cooking at #cook, which hides
   the site's top bar and footer; the back button or × goes back. And the step list on the cooking screen
   (templates/components/step_list.html).
   The number ticks a step off; the first step not ticked is the next one, and shows everything. The other steps
   show one line and open on a tap, or all of them with the small details button at the bottom right
   (remembered for all recipes). A tap on a step in the timeline, the metro map or the delta opens the same card in a sheet, with its
   tick and timer. A step with waiting time has a
   button that starts its timer: the running timers stand in a line above the list and the views, and when the
   time is up the timer turns red, beeps and vibrates (static/js/kitchen.js). A step that uses what was standing
   ends its timer. The view menu at the bottom swaps the list for the timeline, the metro map or the river delta,
   which mark the next step. The ticks and timers are kept on this device per recipe, apart from cooking mode's; the chosen view for
   all recipes. The Bowls button shows how many bowls are ready (the board in the sheet is static/js/ready.js). */
(function () {
  'use strict';
  const page = document.querySelector('.make[data-recipe]');
  const lists = page ? [...page.querySelectorAll('[data-slist]')] : [];  // two with the step layout trial "phases"
  if (!lists.length) return;
  const { beep, ring, wake, leftMin, fmtLeft, esc } = window.Kitchen;
  const KEY = `steps:${page.dataset.recipe}`, VIEW = 'one-page-view', DETAILS = 'one-page-details';
  const $ = s => page.querySelector(s), $$ = s => [...page.querySelectorAll(s)];
  const rows = $$('.st[data-st]');
  const byId = Object.fromEntries(rows.map(r => [r.dataset.st, r]));

  let st = { done: [], runs: [] };
  try { Object.assign(st, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch (e) { /* start afresh */ }
  st.done = (st.done || []).filter(id => byId[id]);
  st.runs = (st.runs || []).filter(r => byId[r.step] && r.end > Date.now() - 3 * 3600e3);
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) { /* kept for this visit only */ } };
  const runOf = id => st.runs.find(r => r.step === id);
  const nextId = () => { const done = new Set(st.done), r = rows.find(x => !done.has(x.dataset.st)); return r ? r.dataset.st : null; };
  const opened = new Set();  // steps opened with a tap, for this visit
  let all = false;           // "Show all details"
  try { all = localStorage.getItem(DETAILS) === 'all'; } catch (e) { /* the steps in focus */ }

  function render() {
    const done = new Set(st.done);
    const next = rows.find(r => !done.has(r.dataset.st));
    rows.forEach(r => {
      const on = done.has(r.dataset.st);
      r.classList.toggle('is-done', on);
      r.classList.toggle('is-next', r === next);
      r.classList.toggle('is-open', opened.has(r.dataset.st));
      r.querySelector('.st-tick').setAttribute('aria-pressed', String(on));
      const n = r.querySelector('.n');
      n.textContent = on ? '✓' : n.dataset.n;
    });
    lists.forEach(l => { l.classList.toggle('all', all); l.classList.toggle('focus', !all); });
    const sw = $('[data-details]');
    if (sw) {
      sw.setAttribute('aria-pressed', String(all));
      const say = all ? 'Show the step you are on' : 'Show all details';
      sw.setAttribute('aria-label', say);
      sw.title = say;
    }
    marks(next ? next.dataset.st : null);
    runs();
    deltaFlow();
    save();
    page.dispatchEvent(new Event('steps:render'));  // static/js/overview_fit.js checks the steps still fit
  }

  /* The timeline and the metro map: the step you tap in them, or else the next one, in full beside the view (on a
     wide screen) or docked at the bottom (on a phone). A second tap on the same step goes back to the next one. */
  // The step layout trial "rail" has the same card beside its list of steps (on a wide screen)
  const splits = $$('.vpanel.split, .vpanel.rail').map(panel => ({ panel, card: panel.querySelector('[data-side-card]'), pick: null, folded: false }));
  function splitRender() {
    const next = nextId();
    splits.forEach(sp => {
      if (sp.pick && st.done.includes(sp.pick)) sp.pick = null;
      const id = sp.pick || next, list = sp.card.querySelector('[data-step-card]');
      sp.panel.querySelectorAll('.sel').forEach(e => e.classList.remove('sel'));
      if (id) sp.panel.querySelectorAll(`.split-main [data-step="${id}"], .rail-main [data-st="${id}"]`).forEach(e => e.classList.add('sel'));
      sp.card.querySelector('[data-side-card-label]').textContent = !id ? 'The food is ready' : sp.pick ? 'The step you chose' : 'Next step';
      sp.card.classList.toggle('folded', sp.folded);
      sp.card.querySelector('[data-side-fold]').setAttribute('aria-expanded', String(!sp.folded));
      if (!id || !byId[id]) { list.replaceChildren(); if (sp.panel.classList.contains('rail')) railCard(sp, null, null); return; }
      const copy = byId[id].cloneNode(true);
      copy.classList.add('is-open');
      copy.classList.toggle('sc-new', sp.last !== id);  // eases in when the step changes, not on every timer tick
      sp.last = id;
      list.replaceChildren(copy);
      if (sp.panel.classList.contains('rail')) railCard(sp, id, copy);
    });
  }

  /* The card beside the steps (the rail): which step of how many, the time from it to the table, what it needs
     (its ingredients, from the pills in the text), and the step after it */
  const TOTAL = +(($('.vpanel.rail') || {}).dataset || {}).total || 0;
  function railCard(sp, id, copy) {
    const q = s => sp.card.querySelector(s), row = id && byId[id];
    q('[data-side-card-count]').textContent = row ? `Step ${row.querySelector('.n').dataset.n} of ${rows.length}` : 'The food is ready';
    const left = row && TOTAL ? TOTAL - +row.dataset.start : 0;
    q('[data-side-card-left]').textContent = !left ? '' : left >= 120 ? `About ${(left / 60).toFixed(1).replace('.0', '')} h to the table` : `About ${left} min to the table`;
    const needs = q('[data-side-card-needs]');
    needs.replaceChildren(...(copy ? [...copy.querySelectorAll('.txt .pill')] : []).map(p => {
      const li = document.createElement('li');
      li.append(...p.cloneNode(true).childNodes);
      return li;
    }));
    needs.hidden = !needs.children.length;
    const done = new Set(st.done), at = row ? rows.indexOf(row) : -1;
    const then = row && rows.slice(at + 1).find(r => !done.has(r.dataset.st) && r.dataset.st !== id);
    q('[data-side-card-then]').textContent = then ? `Then: ${then.dataset.label}` : '';
    rows.forEach(r => r.classList.toggle('is-then', r === then));  // not faded in the list (static/css/rail.css)
    q('[data-sc-done]').hidden = !row;
  }
  // Done on the card: the step it shows, then on to the next
  function cardDone(sp) {
    const id = sp.pick || nextId();
    if (!id || st.done.includes(id)) return;
    sp.pick = null;
    tick(byId[id]);
  }
  const railSplit = splits.find(sp => sp.panel.classList.contains('rail'));
  const railOn = () => railSplit && !railSplit.panel.hidden && getComputedStyle(railSplit.card).display !== 'none'
    && document.documentElement.classList.contains('cooking');

  /* The delta fills as steps are ticked off in the list, and a running timer counts down on its step */
  const dFlow = $('[data-delta-flow]');
  function deltaFlow() {
    if (!dFlow) return;
    const done = new Set(st.done);
    dFlow.querySelectorAll('.g2-node').forEach(n => {
      const segs = [...n.querySelectorAll('.fx-seg')];
      n.classList.toggle('flow-done', segs.length > 0 && segs.every(x => done.has(x.dataset.step)));
    });
    // The next step that is in the drawing (preheating the oven, say, is not)
    dFlow.querySelectorAll('.g2-node.nextup').forEach(n => n.classList.remove('nextup'));
    const up = rows.map(r => !done.has(r.dataset.st) && dFlow.querySelector(`.fx-seg[data-step="${r.dataset.st}"]`)).find(Boolean);
    if (up) up.closest('.g2-node').classList.add('nextup');
    dFlow.querySelectorAll('.sk-arrows [data-f]').forEach(g => {
      const from = dFlow.querySelector(`.g2-node[data-n="${g.dataset.f}"]`);
      g.classList.toggle('flowed', !!from && from.classList.contains('flow-done'));
    });
  }
  function deltaRuns() {
    if (!dFlow) return;
    dFlow.querySelectorAll('.fx-run').forEach(b => { if (!runOf(b.dataset.run)) b.remove(); });
    st.runs.forEach(r => {
      const seg = dFlow.querySelector(`.fx-seg[data-step="${r.step}"]`);
      if (!seg) return;
      let b = seg.querySelector('.fx-run');
      if (!b) { b = document.createElement('span'); b.className = 'fx-run'; b.dataset.run = r.step; seg.append(b); }
      b.textContent = fmtLeft(r);
      b.classList.toggle('fin', Date.now() >= r.end);
    });
  }
  if (dFlow) dFlow.addEventListener('delta:drawn', deltaFlow);

  /* A step tapped in a view: the same card as in the list, in a sheet. Filled again when it changes */
  const stepSheet = document.getElementById('sheet-step');
  let shown = null;
  function card() {
    if (!stepSheet || !stepSheet.open || !byId[shown]) return;
    const copy = byId[shown].cloneNode(true);
    copy.classList.add('is-open');
    stepSheet.querySelector('[data-step-card]').replaceChildren(copy);
  }
  function showStep(id) {
    if (!stepSheet || !byId[id]) return;
    shown = id;
    if (!stepSheet.open) stepSheet.showModal();
    card();
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
      const r = runOf(row.dataset.st), up = r && Date.now() >= r.end;
      row.querySelectorAll('[data-start]').forEach(b => {
        const mini = b.classList.contains('st-timer-mini');
        b.classList.toggle('running', !!r);
        b.querySelector('span').textContent = !r ? (mini ? `${row.dataset.passive} min` : `Start ${row.dataset.passive} min`)
          : up ? (mini ? 'Up' : 'Time is up') : (mini ? `${leftMin(r)} min` : `${leftMin(r)} min left`);
      });
    });
    card();
    splitRender();
    deltaRuns();
  }

  function tick(row) {
    const id = row.dataset.st, i = st.done.indexOf(id);
    if (i >= 0) st.done.splice(i, 1);
    else {
      opened.delete(id);
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
    const now = $('[data-mt-now]');  // the metro map: a line across it at the next step that is on the map
    if (now) {
      const done = new Set(st.done);
      const at = rows.map(r => !done.has(r.dataset.st) && $(`.mt .mt-names [data-step="${r.dataset.st}"]`)).find(Boolean);
      now.hidden = !at;
      if (at) now.style.top = `${at.dataset.y}px`;
    }
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
    const item = items.find(b => b.dataset.view === v);
    if (menuBtn && item) menuBtn.setAttribute('aria-label', `View: ${item.textContent}`);
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
    if (t.closest('[data-sc-done]')) { cardDone(splits.find(x => x.card.contains(t))); return; }
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
    if (t.closest('[data-details]')) {
      all = !all;
      try { localStorage.setItem(DETAILS, all ? 'all' : 'focus'); } catch (err) { /* for this visit only */ }
      openMenu(false);
      render();
      return;
    }
    if (t.closest('[data-steps-reset]')) { st = { done: [], runs: [] }; opened.clear(); render(); return; }
    const fold = t.closest('[data-side-fold]');
    if (fold) { const sp = splits.find(x => x.card.contains(fold)); sp.folded = !sp.folded; splitRender(); return; }
    // A step in the timeline or the metro map, or in the list beside the card (the trial "rail", when the card
    // is shown): shown beside it
    const railRow = !t.closest('.st-tick, [data-start]') && t.closest('.rail-main .st[data-st]');
    const railSp = railRow && splits.find(x => x.panel.contains(railRow));
    const pick = t.closest('.split-main [data-step]') || (railSp && getComputedStyle(railSp.card).display !== 'none' && railRow);
    if (pick) {
      const sp = splits.find(x => x.panel.contains(pick)), id = pick.dataset.step || pick.dataset.st;
      sp.pick = sp.pick === id ? null : id;
      splitRender();
      return;
    }
    // A step in the timeline, the metro map or the delta (the delta's own numbers still tick there)
    const hit = !t.closest('.fx-no') && t.closest('.vpanel:not([data-panel="steps"]) [data-step], .vpanel [data-station]');
    if (hit) { showStep(hit.dataset.step || hit.dataset.station); return; }
    const node = !t.closest('.fx-no') && t.closest('[data-delta-flow] .g2-node');  // anywhere on a step in the delta
    const seg = node && node.querySelector('.fx-seg[data-step]');
    if (seg) { showStep(seg.dataset.step); return; }
    const row = t.closest('.st[data-st]');
    if (!row) { setTimeout(bowls); return; }
    if (t.closest('[data-start]')) { start(row); return; }
    if (t.closest('.st-tick')) { tick(row); return; }
    if (t.closest('a') || row.closest('[data-step-card]') || all || row.classList.contains('is-next')) return;
    // Open or close another step to read it
    opened.has(row.dataset.st) ? opened.delete(row.dataset.st) : opened.add(row.dataset.st);
    render();
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

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') openMenu(false);
    // The rail: → (or space) is done and on to the next step, ← takes the last tick back
    if (!railOn() || document.querySelector('dialog[open]') || e.metaKey || e.ctrlKey || e.altKey || e.target.closest('input, textarea, select')) return;
    if (e.key === 'ArrowRight' || (e.key === ' ' && e.target === document.body)) { e.preventDefault(); cardDone(railSplit); }
    else if (e.key === 'ArrowLeft' && st.done.length) { e.preventDefault(); st.done.pop(); render(); }
  });
  // And a swipe to the left on the card, on a tablet
  if (railSplit) {
    let x0 = null, y0 = null;
    railSplit.card.addEventListener('touchstart', e => { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, { passive: true });
    railSplit.card.addEventListener('touchend', e => {
      const dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0;
      if (x0 !== null && railOn() && dx < -80 && Math.abs(dy) < 60) cardDone(railSplit);
      x0 = null;
    });
  }

  /* The admin chip (notes, look) over an open sheet too: a modal sheet lies above everything else on the page,
     so the chip moves into it while it is open and back when it closes */
  const chip = document.querySelector('[data-trial]');
  if (chip) {
    const home = document.createComment('admin chip');
    chip.before(home);
    page.querySelectorAll('dialog').forEach(d => {
      new MutationObserver(() => {
        if (d.open) d.append(chip);
        else if (chip.parentNode === d) home.after(chip);
      }).observe(d, { attributes: true, attributeFilter: ['open'] });
    });
  }

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
