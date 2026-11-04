/* The ingredients page (templates/pantry_management.html): a tap on an ingredient opens its sheet. The cards come and go
   with the search (static/js/library.js), so the page listens, not the cards. */
(function () {
  'use strict';
  const sheet = document.querySelector('[data-ing-sheet]');
  if (!sheet) return;
  const url = id => sheet.dataset.url.replace('/0/', `/${id}/`);
  let asked = 0;

  document.addEventListener('click', async e => {
    const card = e.target.closest('[data-ing]');
    if (!card) return;
    const mine = ++asked;
    try {
      const resp = await fetch(url(card.dataset.ing));
      if (!resp.ok) throw new Error(String(resp.status));
      const html = await resp.text();
      if (mine !== asked) return;
      sheet.innerHTML = html;
      sheet.showModal();
    } catch (err) {
      console.error('Could not open the ingredient', err);
    }
  });

  sheet.addEventListener('click', e => {
    if (e.target === sheet || e.target.closest('[data-ing-close]')) sheet.close();  // the backdrop, or the ×
  });
})();
