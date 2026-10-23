/* Servings (components/dish_info.html): type a number or use − and +.
   On Overview the amounts change at once, in the page, as services/recipe_v2/view.fmt_amount writes them; the links
   to the other pages get the new number, and those pages are fetched in the background so they open fast.
   Anywhere else the form loads the page for that many servings. */
(function () {
  'use strict';
  const form = document.querySelector('[data-servings-form]');
  if (!form) return;
  const input = form.querySelector('[data-servings-input]');
  const page = document.querySelector('[data-instant-servings]');
  const clamp = n => Math.max(1, Math.min(24, Math.round(n) || 1));

  // As view.frac and view.fmt_amount in Python
  function frac(v) {
    let whole = Math.floor(v + 1e-9);
    const rem = v - whole;
    const marks = [[0, ''], [0.25, '¼'], [1 / 3, '⅓'], [0.5, '½'], [2 / 3, '⅔'], [0.75, '¾'], [1, '']];
    let best = marks.reduce((a, m) => Math.abs(rem - m[0]) < Math.abs(rem - a[0]) ? m : a);
    if (best[0] === 1) { whole += 1; best = [0, '']; }
    return ((whole ? String(whole) : '') + best[1]) || '0';
  }
  const units = page ? JSON.parse(page.dataset.units || '{}') : {};
  // Python's round(): a half goes to the even number (52.5 -> 52), so the page shows what the server would
  const round = x => (Math.abs(x % 1) === 0.5 ? 2 * Math.round(x / 2) : Math.round(x));
  function fmt(amount, unit) {
    if (unit === 'g' || unit === 'ml') {
      const n = amount >= 100 ? round(amount / 10) * 10 : amount >= 10 ? round(amount / 5) * 5 : round(amount * 10) / 10;
      return `${n} ${unit}`;
    }
    const n = frac(amount);
    if (!unit || unit === 'piece') return n;
    const names = units[unit] || [unit, unit];
    return `${n} ${amount > 1 ? names[1] : names[0]}`;
  }

  let shown = page ? Number(page.dataset.instantServings) : null;
  let warm;
  function setServings(n) {
    n = clamp(n);
    input.value = n;
    if (!page) { form.requestSubmit ? form.requestSubmit() : form.submit(); return; }
    const factor = n / shown;
    document.querySelectorAll('[data-amounts]').forEach(el => {
      const raw = JSON.parse(el.dataset.amounts);
      el.dataset.amounts = JSON.stringify(raw.map(([a, u]) => [a * factor, u]));
      el.textContent = raw.map(([a, u]) => fmt(a * factor, u)).join(' + ');
    });
    shown = n;
    document.querySelectorAll('[data-servings-label]').forEach(el => { el.textContent = n; });
    // The links to Prep, Cook, Make and the print sheet, and this page's own address, carry the new number
    document.querySelectorAll('a[href*="servings="]').forEach(a => {
      const url = new URL(a.href, location.href);
      url.searchParams.set('servings', n);
      a.href = url.pathname + url.search;
    });
    const here = new URL(location.href);
    here.searchParams.set('servings', n);
    history.replaceState(null, '', here.pathname + here.search);
    // Build the next pages for this number while you read, so they open fast
    clearTimeout(warm);
    warm = setTimeout(() => {
      document.querySelectorAll('.flowbar a:not([aria-current]), .next a.go').forEach(a => {
        fetch(a.href, { credentials: 'same-origin' }).catch(() => {});
      });
    }, 900);
  }

  form.addEventListener('click', e => {
    const b = e.target.closest('[data-step]');
    if (b) setServings(Number(input.value) + Number(b.dataset.step));
  });
  input.addEventListener('change', () => setServings(Number(input.value)));
  form.addEventListener('submit', e => { if (page) { e.preventDefault(); setServings(Number(input.value)); } });
})();
