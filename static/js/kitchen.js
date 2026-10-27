/* What the step list on the cooking screen (static/js/steps.js) needs from the kitchen: the
   timers' sound and buzz, keeping the screen awake, and how the time left is written. Window.Kitchen. */
(function () {
  'use strict';
  let actx = null, lock = null;

  /* Three short beeps. Call it once with prime=true on a tap: browsers only allow sound after one */
  function beep(prime) {
    try {
      actx = actx || new (window.AudioContext || window.webkitAudioContext)();
      if (prime) return;
      [0, 0.35, 0.7].forEach(d => {
        const o = actx.createOscillator(), g = actx.createGain();
        o.frequency.value = 880; o.connect(g); g.connect(actx.destination);
        g.gain.setValueAtTime(0.2, actx.currentTime + d);
        g.gain.exponentialRampToValueAtTime(0.001, actx.currentTime + d + 0.3);
        o.start(actx.currentTime + d); o.stop(actx.currentTime + d + 0.3);
      });
    } catch (e) { /* sound is optional */ }
  }

  function ring() {
    beep(false);
    try { if (navigator.vibrate) navigator.vibrate([300, 150, 300]); } catch (e) { /* not supported */ }
  }

  /* Keep the screen on while the page is open and visible */
  async function wake() {
    try {
      if (!lock && navigator.wakeLock && document.visibilityState === 'visible') {
        lock = await navigator.wakeLock.request('screen');
        lock.addEventListener('release', () => { lock = null; });
      }
    } catch (e) { lock = null; /* the page works without it */ }
  }
  document.addEventListener('visibilitychange', wake);

  const leftMin = r => Math.max(0, Math.ceil((r.end - Date.now()) / 60e3));
  const fmtLeft = r => {
    const s = Math.max(0, Math.round((r.end - Date.now()) / 1000));
    return s ? `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}` : 'check';
  };
  const esc = t => String(t).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  window.Kitchen = { beep, ring, wake, leftMin, fmtLeft, esc };
})();
