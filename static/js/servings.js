/* Servings (components/dish_info.html): type a number or use − and +, and the page loads for that many servings.
   The server writes every amount (services/measures.py), in the reader's measuring system, so the page has no
   copy of that here. */
(function () {
  'use strict';
  const form = document.querySelector('[data-servings-form]');
  if (!form) return;
  const input = form.querySelector('[data-servings-input]');
  const clamp = n => Math.max(1, Math.min(24, Math.round(n) || 1));

  function setServings(n) {
    input.value = clamp(n);
    form.requestSubmit ? form.requestSubmit() : form.submit();
  }

  form.addEventListener('click', e => {
    const b = e.target.closest('[data-step]');
    if (b) setServings(Number(input.value) + Number(b.dataset.step));
  });
  input.addEventListener('change', () => setServings(Number(input.value)));
})();
