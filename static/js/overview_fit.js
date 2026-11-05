/* The one-page flow's lists as large as fit the screen: the ingredients on the overview
   (templates/components/overview_layouts.html, static/css/overview_layouts.css) and, on a wide screen, the steps
   on the cooking screen (templates/components/step_list.html, static/css/rail.css). Extra large (the steps, on a large
   screen), large, roomy, normal, snug (the steps) or tight, the first that needs no scrolling; in C the image follows the ingredients. When even
   tight does not fit, the list stays tight and scrolls (the ingredients on a phone stay normal). Fitted again when
   the screen changes size; the steps also when a tick makes them too tall, then only ever smaller, so the page
   does not jump while you cook. */
(function () {
  'use strict';
  const INGS = ['large', 'roomy', 'normal', 'snug', 'tight'];  // snug: the steps only
  const STEPS = ['xxl', 'xl', ...INGS];
  const fits = box => box.scrollHeight <= box.clientHeight + 1;

  function fit(box) {
    if (!box.clientHeight) return;  // hidden: the cooking screen on the overview, and the other way round
    // Under 1000 px the steps scroll above their card, at a size that is easy to tap
    if (box.hasAttribute('data-fit-steps') && innerWidth < 1000) { box.dataset.density = 'normal'; return; }
    for (const step of box.hasAttribute('data-fit-steps') ? STEPS : INGS) {
      box.dataset.density = step;
      if (fits(box)) return;
    }
    // A phone scrolls the ingredients anyway; there they stay at the size that is easy to read
    if (innerWidth <= 600 && box.hasAttribute('data-fit-ings')) box.dataset.density = 'normal';
  }

  document.querySelectorAll('[data-fit-ings], [data-fit-steps]').forEach(box => {
    let seen = '';
    new ResizeObserver(() => {
      if (!box.clientHeight) return;
      // The screen, and whether the site's top bar is shown; not the list itself changing size as it is fitted
      const size = innerWidth + 'x' + innerHeight + document.documentElement.classList.contains('site-menu');
      if (size === seen) return;
      seen = size;
      fit(box);
    }).observe(box);
    if (document.fonts) document.fonts.ready.then(() => fit(box));
    if (box.hasAttribute('data-fit-steps')) {
      const page = box.closest('[data-recipe]');
      if (page) page.addEventListener('steps:render', () => {
        let i = STEPS.indexOf(box.dataset.density);
        while (innerWidth >= 1000 && box.clientHeight && !fits(box) && i < STEPS.length - 1) box.dataset.density = STEPS[++i];
      });
    }
  });
})();
