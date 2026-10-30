/* Editing the note from last time in the sheet's Your note (#more-mine, components/overview_layouts.html): Edit shows
   the feedback fields (static/js/feedback.js) filled in with what was saved, the stars, the comment and the photos.
   Save stores them and loads the page again, so the note card, the stars and the photo show the new note. */
(function () {
  'use strict';
  const page = document.querySelector('.make[data-recipe]');
  const box = document.querySelector('[data-mine-note]');
  if (!page || !box || !window.Feedback) return;
  const form = box.querySelector('[data-mine-form]');
  const view = box.querySelector('[data-mine-view]');
  const edit = box.querySelector('[data-mine-edit]');
  const saveBtn = form.querySelector('[type=submit]');
  const fb = window.Feedback.attach(form);
  const editing = on => { form.hidden = !on; view.hidden = on; edit.hidden = on; };

  edit.addEventListener('click', async () => {
    editing(true);
    await fb.open(page.dataset.recipe);
    const text = form.elements.comment;
    text.focus();
    text.setSelectionRange(text.value.length, text.value.length);  // to add to the end of the note
  });
  box.querySelector('[data-mine-cancel]').addEventListener('click', () => editing(false));

  form.addEventListener('submit', async e => {
    e.preventDefault();
    saveBtn.disabled = true;
    try {
      const missed = await fb.save();
      if (!missed) { location.reload(); return; }
      fb.say(`Saved. ${missed}`, true);
    } catch (err) {
      fb.say(err.friendly || 'Something went wrong. Please try again.', true);
    }
    saveBtn.disabled = false;
  });
})();
