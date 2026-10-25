/* The ingredients on the overview of the one-page flow as large as fits the screen
   (templates/components/overview_layouts.html, static/css/overview_layouts.css): large, roomy, normal or tight,
   the first that needs no scrolling; in C the image follows. When even tight does not fit, the list stays tight and
   scrolls (on a phone, normal). Fitted again when the screen changes size. */
(function () {
  'use strict';
  const box = document.querySelector('[data-fit-ings]');
  if (!box) return;
  const STEPS = ['large', 'roomy', 'normal', 'tight'];

  function fit() {
    if (!box.clientHeight) return;  // hidden while cooking
    for (const step of STEPS) {
      box.dataset.density = step;
      if (box.scrollHeight <= box.clientHeight + 1) return;
    }
    // A phone scrolls the list anyway; there it stays at the size that is easy to read
    if (innerWidth <= 600) box.dataset.density = 'normal';
  }

  let seen = '';
  new ResizeObserver(() => {
    if (!box.clientHeight) return;
    // The screen, and whether the site's top bar is shown; not the list itself changing size as it is fitted
    const size = innerWidth + 'x' + innerHeight + document.documentElement.classList.contains('site-menu');
    if (size === seen) return;
    seen = size;
    fit();
  }).observe(box);
  if (document.fonts) document.fonts.ready.then(fit);
})();
