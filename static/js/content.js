/* Pages made of blocks (templates/page.html, docs/CONTENT.md).
   Carry on cooking (templates/blocks/continue.html): the dish you are in the middle of on this device. static/js/steps.js
   keeps each recipe's ticks under "steps:<id>" with meta (title, image, the next step, when you last ticked: at); the
   newest one with some steps done and some left, touched in the last 12 hours, is shown, with a running timer. × hides
   it until you tick another step.
   Interactive (templates/blocks/interactive.html): the frame takes the height its page reports (routes/content_routes.RESIZE). */
(function () {
  'use strict';
  const FRESH = 12 * 3600e3;

  function inProgress() {
    let best = null;
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (!/^steps:\d+$/.test(key)) continue;
        const st = JSON.parse(localStorage.getItem(key) || '{}'), m = st.meta || {};
        const done = (st.done || []).length;
        if (!m.at || Date.now() - m.at > FRESH || !done || !m.total || done >= m.total || m.hidden === m.at) continue;
        if (!best || m.at > best.st.meta.at) best = { id: key.slice(6), key, st };
      }
    } catch (e) { /* no storage here: nothing to carry on with */ }
    return best;
  }

  const box = document.querySelector('[data-continue]');
  if (box) {
    // An empty block leaves no gap: the section around it goes too
    const section = box.closest('.blk') || box;
    const show = on => { box.hidden = !on; section.hidden = !on; };
    show(false);
    const found = inProgress();
    if (found) {
      const { id, key, st } = found, m = st.meta, q = s => box.querySelector(s);
      q('[data-cont-link]').href = `/recipe/${id}#cook`;
      q('[data-cont-title]').textContent = m.title || 'Your dish';
      q('[data-cont-step]').textContent = m.next ? `Step ${m.next.n} of ${m.total} · ${m.next.label}` : `${st.done.length} of ${m.total} steps done`;
      q('[data-cont-bar]').style.width = `${Math.round(100 * st.done.length / m.total)}%`;
      if (m.img) {
        const img = document.createElement('img');
        img.src = m.img;
        img.alt = '';
        q('[data-cont-img]').append(img);
      }
      const run = (st.runs || []).filter(r => r.end > Date.now() - 600e3).sort((a, b) => a.end - b.end)[0];
      if (run) {
        const left = Math.ceil((run.end - Date.now()) / 60e3);
        q('[data-cont-run]').textContent = left > 0 ? `${run.label}: ${left} min left` : `${run.label}: time is up`;
        q('[data-cont-run]').hidden = false;
      }
      q('[data-cont-hide]').addEventListener('click', () => {
        show(false);
        try { st.meta.hidden = m.at; localStorage.setItem(key, JSON.stringify(st)); } catch (e) { /* hidden for this visit */ }
      });
      show(true);
    }
  }

  // The frames of interactives: as tall as their page, told by the page itself
  const frames = [...document.querySelectorAll('iframe[data-embed]')];
  if (frames.length) {
    addEventListener('message', e => {
      const frame = frames.find(f => f.contentWindow === e.source);
      const h = e.data && e.data.lazyEmbed && +e.data.height;
      if (frame && h > 0) frame.style.height = `${Math.min(h, 6000)}px`;
    });
  }
})();
