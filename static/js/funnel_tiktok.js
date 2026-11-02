// The TikTok posts page (templates/admin/funnel_tiktok.html). The slides are fetched as the page opens, because a
// phone only opens its share sheet straight after a tap, not after a wait; from there Save Images puts them in Photos.
(function () {
  function copy(button) {
    var field = document.getElementById(button.dataset.copy);
    var label = button.textContent;
    navigator.clipboard.writeText(field.value).then(function () {
      button.textContent = 'Copied';
    }, function () {
      field.select();
      button.textContent = 'Press copy';
    }).then(function () {
      setTimeout(function () { button.textContent = label; }, 2000);
    });
  }

  function slide(card, n) {
    return fetch(card.dataset.base + n + '.jpg', { credentials: 'same-origin' }).then(function (response) {
      if (!response.ok) throw new Error('slide ' + n);
      return response.blob();
    }).then(function (blob) {
      return new File([blob], 'tiktok-' + card.dataset.code + '-' + String(n).padStart(2, '0') + '.jpg',
        { type: 'image/jpeg' });
    });
  }

  function prepare(card) {
    var button = card.querySelector('[data-save]');
    var note = card.querySelector('[data-save-note]');
    function say(text) {
      note.textContent = text;
      note.hidden = false;
    }
    Promise.all(JSON.parse(card.dataset.slides).map(function (n) { return slide(card, n); })).then(function (files) {
      if (!navigator.canShare || !navigator.canShare({ files: files })) {
        button.textContent = 'Saving works on the phone';
        say('This browser cannot share files. Open this page on the iPhone, or hold each slide above to save it.');
        return;
      }
      button.disabled = false;
      button.textContent = 'Save ' + files.length + ' slides to Photos';
      button.addEventListener('click', function () {
        navigator.share({ files: files }).then(function () {
          say('Saved, if you chose Save Images. They are the newest in Photos, in order.');
        }).catch(function (error) {
          if (error.name !== 'AbortError') say('That did not work. Try again, or hold each slide above to save it.');
        });
      });
    }).catch(function () {
      button.textContent = 'Could not get the slides';
      say('Reload the page, or hold each slide above to save it.');
    });
  }

  document.querySelectorAll('[data-copy]').forEach(function (button) {
    button.addEventListener('click', function () { copy(button); });
  });
  document.querySelectorAll('[data-tiktok-post]').forEach(prepare);
})();
