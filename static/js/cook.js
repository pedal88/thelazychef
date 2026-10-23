/* Cooking mode (templates/recipe_v2_cook.html), ported from the phone prototype (RECIPE_VISUALIZATIONS.md 9.15).
   One card at a time. A step with waiting time is started and put under "running" with a countdown, so you can go
   on; when the time is up it turns red, beeps and vibrates. The place, the timers and the choice to skip what
   Prep has done are kept on this device, per recipe. The screen is kept awake while the page is open. */
(function () {
  'use strict';
  const page = document.querySelector('.cook[data-recipe]');
  if (!page) return;
  const KEY = `cook:${page.dataset.recipe}`;
  const $ = s => page.querySelector(s), $$ = s => [...page.querySelectorAll(s)];
  const cards = $$('.card[data-step]');
  const byId = Object.fromEntries(cards.map(c => [c.dataset.step, c]));

  let st = { at: null, skip: true, runs: [], list: false, finished: false };
  try { Object.assign(st, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch (e) { /* start afresh */ }
  st.runs = (st.runs || []).filter(r => byId[r.step] && r.end > Date.now() - 3 * 3600e3);
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) { /* kept for this visit only */ } };

  const steps = () => cards.filter(c => !(st.skip && c.hasAttribute('data-ahead')));
  const index = () => { const list = steps(), k = list.findIndex(c => c.dataset.step === st.at); return k < 0 ? 0 : k; };
  const runOf = id => st.runs.find(r => r.step === id);
  const { beep, ring, wake, leftMin, fmtLeft, esc } = window.Kitchen;  // static/js/kitchen.js

  function render() {
    const list = steps(), k = index(), card = list[k];
    st.at = card ? card.dataset.step : null;
    cards.forEach(c => { c.hidden = st.list || st.finished || c !== card; });
    $('[data-finished]').hidden = !st.finished;
    $('[data-list]').hidden = !st.list;
    $('[data-skip]').checked = st.skip;
    $('[data-toggle-list]').setAttribute('aria-pressed', String(st.list));
    $('[data-toggle-list]').textContent = st.list ? 'Card' : 'Steps';
    $$('[data-row]').forEach(li => {
      li.hidden = st.skip && li.hasAttribute('data-ahead');
      const at = list.indexOf(byId[li.dataset.row]);
      li.classList.toggle('cur', li.dataset.row === st.at);
      li.classList.toggle('past', at >= 0 && at < k);
    });
    $('.prog').innerHTML = list.map((c, j) => `<i class="${c.classList.contains('cook') ? 'cook' : c.classList.contains('serve') ? 'serve' : 'prep'}${j <= k ? ' on' : ''}${j === k ? ' cur' : ''}"></i>`).join('');
    $('[data-where]').textContent = st.finished ? 'Done' : `${k + 1} of ${list.length}`;
    $('[data-prev]').disabled = k === 0 && !st.finished;
    const last = k === list.length - 1, passive = card ? +card.dataset.passive : 0;
    const btn = $('[data-advance]');
    btn.hidden = st.finished;
    btn.textContent = last ? 'Done' : passive ? (runOf(st.at) ? 'Next →' : 'Start, then next →') : 'Done, next →';
    btn.className = `btn primary ${card ? (card.classList.contains('cook') ? 'cook' : card.classList.contains('serve') ? 'serve' : 'prep') : ''}`;
    if (card) {
      const wait = (card.dataset.after || '').split(' ').map(runOf).filter(r => r && Date.now() < r.end);
      const box = card.querySelector('[data-wait]');
      box.hidden = !wait.length;
      box.textContent = wait.length ? `Waiting for ${wait.map(r => `“${r.label.toLowerCase()}”, about ${leftMin(r)} min`).join(' and ')}. Prep what you can.` : '';
      const pass = card.querySelector('[data-passbox]');
      if (pass) pass.hidden = last;
    }
    marks();
    runs();
    save();
  }

  /* The running timers, and the step standing beside the card */
  function runs() {
    $('[data-runs]').innerHTML = st.runs.length
      ? st.runs.map(r => `<button type="button" class="tm${Date.now() >= r.end ? ' fin' : ''}" data-run="${esc(r.step)}" aria-expanded="${st.open === r.step}">${esc(r.label)} <span>${fmtLeft(r)}</span></button>`).join('')
      : '<span class="muted">Nothing is standing.</span>';
    const open = runOf(st.open), box = $('[data-runbox]');
    box.hidden = !open;
    if (open) {
      $('[data-run-label]').textContent = open.label;
      $('[data-run-done]').textContent = open.done ? `Done when: ${open.done}` : '';
    }
    $$('[data-standing]').forEach(w => {
      const r = runOf(w.dataset.standing);
      w.querySelector('[data-left]').textContent = r && Date.now() < r.end ? ` · ${leftMin(r)} min left` : '';
    });
  }

  /* The step you are on, marked in the delta beside the card */
  function marks() {
    $$('.cook-side .cur').forEach(e => e.classList.remove('cur'));
    if (st.at) {
      $$(`.cook-side [data-step="${st.at}"], .cook-side [data-station="${st.at}"]`).forEach(e => e.classList.add('cur'));
      const seg = $(`.cook-side .fx-seg[data-step="${st.at}"]`);
      if (seg) seg.closest('.g2-node').classList.add('cur');
    }
    timelineAt();
    revealDelta();
  }

  /* The delta can be wider than the panel: bring the step you are on into view once it has been laid out */
  function revealDelta() {
    const node = $('.cook-side .g2-node.cur'), panel = node && node.closest('[data-panel]');
    if (node && panel && !panel.hidden) setTimeout(() => node.scrollIntoView({ block: 'nearest', inline: 'center' }), 250);
  }

  /* The red line in the timeline at the minute the plan starts the step you are on, and what happens then */
  function timelineAt() {
    const tl = $('.tl'), status = $('[data-tl-status]');
    if (!tl) return;
    const total = +tl.dataset.total, rows = $$('.tl-row[data-step]'), here = rows.find(r => r.dataset.step === st.at);
    const m = st.finished ? total : here ? +here.dataset.start : 0;
    $('.nowline').style.setProperty('--x', (m / total).toFixed(4));
    const doing = rows.filter(r => +r.dataset.start <= m && m < +r.dataset.aend).map(r => r.dataset.short);
    const standing = rows.filter(r => +r.dataset.aend <= m && m < +r.dataset.end).map(r => r.dataset.short.toLowerCase());
    const next = rows.find(r => +r.dataset.start > m);
    status.innerHTML = `<b>Minute ${m} of ${total} in the plan.</b> `
      + (doing.length ? `You are doing: ${esc(doing.join(', '))}. ` : 'Nothing to do right now. ')
      + (standing.length ? `Standing: ${esc(standing.join(', '))}. ` : '')
      + (next ? `Next: ${esc(next.dataset.short.toLowerCase())} in ${+next.dataset.start - m} min.` : 'The food is ready.');
  }

  /* The whole dish: timeline, metro map or river delta. Beside the card on a large screen, a sheet on a phone */
  const WHOLE = 'whole-dish-view', side = $('#whole');
  function showView(v) {
    const tabs = $$('[data-whole]');
    if (!tabs.length) return;
    if (!tabs.some(b => b.dataset.whole === v)) v = tabs[0].dataset.whole;
    tabs.forEach(b => b.setAttribute('aria-selected', String(b.dataset.whole === v)));
    $$('[data-panel]').forEach(p => { p.hidden = p.dataset.panel !== v; });
    try { localStorage.setItem(WHOLE, v); } catch (e) { /* remembered for this visit only */ }
    if (v === 'delta') { dispatchEvent(new Event('resize')); revealDelta(); } // the delta lays itself out once it can be seen
  }
  function openWhole(on) {
    if (!side) return;
    side.classList.toggle('open', on);
    document.documentElement.classList.toggle('whole-open', on);
    if (on) { dispatchEvent(new Event('resize')); side.querySelector('[data-whole-close]').focus(); }
    else { const b = $('[data-whole-open]'); if (b) b.focus(); }
  }
  /* Blow the chosen view up to the whole window (large screen); × or Esc goes back beside the card */
  function fullWhole(on) {
    if (!side) return;
    side.classList.toggle('full', on);
    document.documentElement.classList.toggle('whole-fullscreen', on);
    const b = $('[data-whole-full]');
    if (b) b.setAttribute('aria-pressed', String(on));
    dispatchEvent(new Event('resize'));
    revealDelta();
    (on ? side.querySelector('[data-whole-close]') : b)?.focus();
  }
  try { showView(localStorage.getItem(WHOLE)); } catch (e) { showView(null); }

  setInterval(() => {
    let rang = false;
    st.runs.forEach(r => {
      if (!r.rang && Date.now() >= r.end) {
        r.rang = rang = true;
        ring();
      }
    });
    if (rang) render(); else runs();
  }, 1000);

  function go(d) {
    const list = steps(), k = index();
    if (st.finished) { if (d < 0) st.finished = false; }
    else if (d > 0 && k >= list.length - 1) st.finished = true;
    else st.at = list[Math.max(0, Math.min(list.length - 1, k + d))].dataset.step;
    st.open = null; st.list = false;
    render();
    $('#status').scrollIntoView({ block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }
  /* The main button: a step with waiting time is started under "running" before you go on */
  function advance() {
    const list = steps(), card = list[index()];
    // A step that used what was standing ends its timer: the water has boiled once the pasta is in
    const used = (card && card.dataset.after || '').split(' ');
    st.runs = st.runs.filter(r => !used.includes(r.step));
    if (card && +card.dataset.passive && index() < list.length - 1 && !runOf(card.dataset.step)) {
      st.runs.push({ step: card.dataset.step, label: card.dataset.label, done: card.dataset.done,
                     end: Date.now() + card.dataset.passive * 60e3, rang: false });
    }
    go(1);
  }

  page.addEventListener('click', e => {
    beep(true); wake();
    const t = e.target.closest('button, input');
    if (!t) return;
    if (t.matches('[data-advance]')) advance();
    else if (t.matches('[data-prev]')) go(-1);
    else if (t.matches('[data-toggle-list]')) { st.list = !st.list; render(); }
    else if (t.matches('[data-jump]')) { st.at = t.dataset.jump; st.list = false; st.finished = false; render(); }
    else if (t.matches('[data-run]')) { st.open = st.open === t.dataset.run ? null : t.dataset.run; runs(); save(); }
    else if (t.matches('[data-run-remove]')) { st.runs = st.runs.filter(r => r.step !== st.open); st.open = null; render(); }
    else if (t.matches('[data-skip]')) { st.skip = t.checked; render(); }
    else if (t.matches('[data-restart]')) { st = { at: null, skip: st.skip, runs: [], list: false, finished: false }; render(); }
    else if (t.matches('[data-whole]')) showView(t.dataset.whole);
    else if (t.matches('[data-whole-open]')) openWhole(true);
    else if (t.matches('[data-whole-full]')) fullWhole(true);
    else if (t.matches('[data-whole-close]')) { if (side.classList.contains('full')) fullWhole(false); else openWhole(false); }
  });
  let sx = 0, sy = 0;
  page.addEventListener('touchstart', e => { if (!e.target.closest('.card')) return; sx = e.touches[0].clientX; sy = e.touches[0].clientY; }, { passive: true });
  page.addEventListener('touchend', e => {
    if (!e.target.closest('.card')) return;
    const dx = e.changedTouches[0].clientX - sx, dy = e.changedTouches[0].clientY - sy;
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) { if (dx < 0) advance(); else go(-1); }
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && side && side.classList.contains('full')) { fullWhole(false); return; }
    if (e.key === 'Escape' && side && side.classList.contains('open')) { openWhole(false); return; }
    if (st.list || e.target.closest('input, select, textarea')) return;
    if (e.key === 'ArrowRight') advance();
    if (e.key === 'ArrowLeft') go(-1);
  });
  wake();
  render();
})();
