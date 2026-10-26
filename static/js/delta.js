/* The river delta in the browser (templates/components/delta.html, services/recipe_v2/delta.py).
   The server decides the drawing; this places the cells portrait or landscape, scales the drawing to fit,
   draws hand-drawn arrows between the cells and keeps the ticked-off steps on this device.
   Ported from docs/prototypes/stor-skjerm.html (skFit, fitBoth, drawArrows). */
(function () {
  'use strict';
  const PAGE = { portrait: [718, 1047], landscape: [1047, 718] }; // A4 with 10 mm margins, in CSS pixels
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode: the page works without it */ } },
  };

  function seeded(seed) {
    let x = 7;
    for (const c of seed) x = (x * 31 + c.charCodeAt(0)) | 0;
    return () => { x = (x * 1103515245 + 12345) & 0x7fffffff; return x / 0x7fffffff; };
  }

  /* A cubic curve with a little tremble, drawn twice, and an open arrow head along the last stretch */
  function handCurve([x0, y0], [x1, y1], [x2, y2], [x3, y3], seed) {
    const R = seeded(seed), j = (a = 1.5) => (R() - 0.5) * 2 * a;
    const d = a => `M${x0 + j(a)} ${y0 + j(a)} C${x1 + j(a * 2)} ${y1 + j(a * 2)} ${x2 + j(a * 2)} ${y2 + j(a * 2)} ${x3 + j(a * 0.6)} ${y3 + j(a * 0.6)}`;
    const ax = x3 - x2, ay = y3 - y2, al = Math.hypot(ax, ay) || 1, ux = ax / al, uy = ay / al, hl = 10 + j(1.2), hw = 5.5 + j(0.8);
    const head = `M${x3 - ux * hl + uy * hw} ${y3 - uy * hl - ux * hw} L${x3} ${y3} L${x3 - ux * hl - uy * hw + j()} ${y3 - uy * hl + ux * hw + j()}`;
    return `<path class="pa" d="${d(1.2)}"/><path class="pa pa2" d="${d(2.2)}"/><path class="pa" d="${head}"/>`;
  }

  function drawArrows(box, horiz) {
    const svg = box.querySelector('.sk-arrows'), B = box.getBoundingClientRect(), k = +(box.dataset.scale || 1);
    const bw = B.width / k, bh = B.height / k;
    svg.setAttribute('viewBox', `0 0 ${bw} ${bh}`); svg.setAttribute('width', bw); svg.setAttribute('height', bh);
    const rect = el => { const R = el.getBoundingClientRect();
      return { l: (R.left - B.left) / k, t: (R.top - B.top) / k, r: (R.right - B.left) / k, b: (R.bottom - B.top) / k,
               cx: ((R.left + R.right) / 2 - B.left) / k, cy: ((R.top + R.bottom) / 2 - B.top) / k }; };
    const all = [...box.querySelectorAll('[data-n]')];
    let out = '';
    JSON.parse(box.dataset.edges || '[]').forEach(([f, t]) => {
      const F0 = box.querySelector(`[data-n="${f}"]`), T0 = box.querySelector(`[data-n="${t}"]`);
      if (!F0 || !T0) return;
      const F = rect(F0), T = rect(T0), seed = f + t;
      // Each arrow in its own group, so the page can colour it (the main river; a step done, static/js/steps.js)
      const main = F0.classList.contains('main') && T0.classList.contains('main');
      const g = d => `<g class="ed${main ? ' main' : ''}" data-f="${f}" data-t="${t}">${d}</g>`;
      /* A bend is only used when no other cell lies where it would run */
      const clear = (a, b, c, d) => { const os = all.filter(e => e !== F0 && e !== T0).map(rect);
        for (let i = 1; i < 24; i++) { const u = i / 24, v = 1 - u;
          const x = v * v * v * a[0] + 3 * v * v * u * b[0] + 3 * v * u * u * c[0] + u * u * u * d[0];
          const y = v * v * v * a[1] + 3 * v * v * u * b[1] + 3 * v * u * u * c[1] + u * u * u * d[1];
          if (os.some(o => x > o.l - 6 && x < o.r + 6 && y > o.t - 6 && y < o.b + 6)) return false; }
        return true; };
      if (horiz) {
        const y3 = Math.max(T.t + 14, Math.min(T.b - 14, F.cy)), gap = T.l - F.r, dy = y3 - F.cy, p3 = [T.l - 5, y3];
        const room = dy > 0 ? y3 - F.b : F.t - y3;
        if (room > 24 && Math.abs(dy) > gap * 0.8) {
          const p0 = [F.r - Math.min(36, (F.r - F.l) / 3), dy > 0 ? F.b + 3 : F.t - 3];
          const c1 = [p0[0], p0[1] + (p3[1] - p0[1]) * 0.62], c2 = [p3[0] - (p3[0] - p0[0]) * 0.62, p3[1]];
          if (clear(p0, c1, c2, p3)) { out += g(handCurve(p0, c1, c2, p3, seed)); return; }
        }
        const p0 = [F.r + 3, F.cy], dx = Math.max(14, (p3[0] - p0[0]) * 0.5);
        const c2 = Math.abs(p3[1] - p0[1]) > (p3[0] - p0[0]) * 0.8 ? [p3[0] - (p3[0] - p0[0]) * 0.3, p3[1] - (p3[1] - p0[1]) * 0.3] : [p3[0] - dx, p3[1]];
        out += g(handCurve(p0, [p0[0] + dx, p0[1]], c2, p3, seed));
      } else {
        const x3 = Math.max(T.l + 16, Math.min(T.r - 16, F.cx)), gap = T.t - F.b, dx = x3 - F.cx, p3 = [x3, T.t - 5];
        const room = dx > 0 ? x3 - F.r : F.l - x3;
        if (room > 24 && Math.abs(dx) > gap * 1.2) {
          const p0 = [dx > 0 ? F.r + 3 : F.l - 3, F.b - Math.min(24, (F.b - F.t) / 3)];
          const c1 = [p0[0] + (p3[0] - p0[0]) * 0.62, p0[1]], c2 = [p3[0], p3[1] - (p3[1] - p0[1]) * 0.62];
          if (clear(p0, c1, c2, p3)) { out += g(handCurve(p0, c1, c2, p3, seed)); return; }
        }
        const p0 = [F.cx, F.b + 3], dy = Math.max(14, (p3[1] - p0[1]) * 0.5);
        const c2 = Math.abs(p3[0] - p0[0]) > (p3[1] - p0[1]) * 1.2 ? [p3[0] - (p3[0] - p0[0]) * 0.3, p3[1] - (p3[1] - p0[1]) * 0.3] : [p3[0], p3[1] - dy];
        out += g(handCurve(p0, [p0[0], p0[1] + dy], c2, p3, seed));
      }
    });
    svg.innerHTML = out;
  }

  /* Landscape when the space is wide and low, portrait when it is tall; the reader's choice wins */
  function horizontal(section, wrap) {
    const print = document.body.dataset.print;
    if (print) return print === 'landscape';
    const chosen = section.querySelector('[data-orient]') && store.get('delta-orient');  // a side view has no choice
    if (chosen) return chosen === 'landscape';
    if (section.closest('.dl-panel') && innerWidth >= 1000) return true;  // the cooking screen: lying, beside the card too
    const availH = Math.max(320, innerHeight - 120);
    return wrap.clientWidth >= 700 && wrap.clientWidth / availH > 1.15;
  }

  function layout(section) {
    const wrap = section.querySelector('.dl-wrap'), box = section.querySelector('.skv');
    const horiz = horizontal(section, wrap), maxD = +box.dataset.maxDepth, leaves = +box.dataset.leaves;
    box.classList.toggle('horiz', horiz);
    box.classList.toggle('vert', !horiz);
    box.style.gridTemplateColumns = horiz ? `repeat(${maxD + 1}, max-content)` : `repeat(${leaves}, minmax(min-content, 1fr))`;
    box.style.gridTemplateRows = horiz ? `repeat(${leaves}, auto)` : `repeat(${maxD + 1}, auto)`;
    box.querySelectorAll('.g2-cell').forEach(c => {
      const d = +c.dataset.depth, a = +c.dataset.from + 1, b = +c.dataset.to + 1, line = maxD - d + 1;
      c.style.gridColumn = horiz ? `${line}` : `${a} / ${b}`;
      c.style.gridRow = horiz ? `${a} / ${b}` : `${line}`;
    });
    section.querySelectorAll('[data-orient]').forEach(b => b.setAttribute('aria-pressed', String((b.dataset.orient === 'landscape') === horiz)));
    fit(section, box, wrap);
    drawArrows(box, horiz);
    section.dispatchEvent(new CustomEvent('delta:drawn', { bubbles: true }));
  }

  /* Scale down until the drawing fits the width (and on screen the height below its top), never under 60–75 % */
  function fit(section, box, wrap) {
    const page = PAGE[document.body.dataset.print];
    Object.assign(box.style, { transform: '', zoom: '', marginBottom: '', marginRight: '', marginLeft: '', width: 'max-content' });
    // The arrows of the last drawing would count in its size: measure without them (drawArrows draws them again)
    const svg = box.querySelector('.sk-arrows');
    svg.removeAttribute('width'); svg.removeAttribute('height'); svg.removeAttribute('viewBox');
    // Its natural width; portrait on a screen also spreads its columns over the width there is
    const natW = Math.max(box.scrollWidth, page || box.classList.contains('horiz') ? 0 : wrap.clientWidth - 8);
    box.style.width = `${natW}px`;
    const natH = box.scrollHeight; // after the width is fixed: narrower columns wrap into a taller drawing
    const availW = (page ? page[0] : wrap.clientWidth) - 8;
    // On the cooking screen the room below its top, less the strip along the bottom (static/js/steps.js)
    const panel = !page && innerWidth >= 1000 && section.closest('.dl-panel');
    const strip = panel && panel.classList.contains('strip') ? panel.querySelector('.side-card').offsetHeight + 16 : 0;
    const availH = page ? page[1] - (box.getBoundingClientRect().top - section.getBoundingClientRect().top) - 60
      : panel ? Math.max(300, panel.getBoundingClientRect().bottom - box.getBoundingClientRect().top - strip - 24)
      : Math.max(360, innerHeight - 140);
    const floor = page ? 0.6 : innerWidth < 700 ? 0.6 : section.closest('.dl-panel') ? 0.65 : 0.75;
    const sc = Math.max(floor, Math.min(page ? 1.4 : 1, availW / natW, availH / natH));
    box.dataset.scale = sc;
    if (page) { // zoom also shrinks the space the drawing takes, so the browser does not shrink the whole sheet
      box.style.zoom = sc;
      box.style.marginLeft = `${Math.max(0, (availW - natW * sc) / 2) / sc}px`;
    } else {
      box.style.transformOrigin = '0 0';
      box.style.transform = `scale(${sc})`;
      box.style.marginBottom = `${-natH * (1 - sc)}px`;
      box.style.marginRight = `${-natW * (1 - sc)}px`;
    }
    const note = section.querySelector('.dl-scale');
    if (note) note.textContent = sc < 0.95 && !page ? `shown at ${Math.round(sc * 100)} %` : '';
  }

  /* Ticked-off steps, per recipe, on this device. On the one-page flow's cooking screen the steps' own ticks are
     used instead (static/js/steps.js deltaFlow), so the delta and the list never disagree. */
  function ticks(section) {
    section.querySelectorAll('.fx-no').forEach(b => { b.dataset.no = b.textContent; });
    if (section.closest('[data-delta-flow]')) return;
    const key = `delta:${section.dataset.recipe}`;
    const done = new Set((store.get(key) || '').split(' ').filter(Boolean));
    const paint = () => {
      section.querySelectorAll('.fx-seg').forEach(seg => {
        const on = done.has(seg.dataset.step), btn = seg.querySelector('.fx-no');
        seg.classList.toggle('done', on);
        btn.classList.toggle('ok', on);
        btn.setAttribute('aria-pressed', String(on));
        btn.textContent = on ? '✓' : btn.dataset.no;
      });
      section.querySelectorAll('.g2-node').forEach(n => {
        const segs = [...n.querySelectorAll('.fx-seg')];
        n.classList.toggle('done', segs.length > 0 && segs.every(s => done.has(s.dataset.step)));
      });
    };
    section.addEventListener('click', e => {
      const b = e.target.closest('[data-tick]');
      if (!b) return;
      done.has(b.dataset.tick) ? done.delete(b.dataset.tick) : done.add(b.dataset.tick);
      store.set(key, [...done].join(' '));
      paint();
    });
    paint();
  }

  function init(section) {
    ticks(section);
    section.querySelectorAll('[data-orient]').forEach(b => b.addEventListener('click', () => {
      store.set('delta-orient', b.dataset.orient);
      layout(section);
    }));
    const go = () => layout(section);
    go();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(go);
    let t;
    addEventListener('resize', () => { clearTimeout(t); t = setTimeout(go, 150); });
    // Fit again whenever the drawing or its room changes size without a window resize: shown after being hidden
    // (another view was chosen), a font or an image arriving, a column getting narrower. Without this the frame
    // kept the height of an earlier fit and cut off the bottom of the drawing.
    if ('ResizeObserver' in window) {
      const wrap = section.querySelector('.dl-wrap'), box = section.querySelector('.skv');
      const size = () => `${wrap.clientWidth}:${box.offsetWidth}x${box.offsetHeight}`;
      let seen = '';
      const ro = new ResizeObserver(() => {
        if (size() === seen) return;
        clearTimeout(t);
        t = setTimeout(() => { go(); seen = size(); }, 80);
      });
      ro.observe(wrap);
      ro.observe(box);
    }
    if (document.body.dataset.print && document.body.dataset.autoprint) {
      (document.fonts ? document.fonts.ready : Promise.resolve()).then(() => setTimeout(() => { go(); print(); }, 300));
    }
  }

  document.querySelectorAll('.delta').forEach(init);
})();
