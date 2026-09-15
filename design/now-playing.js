/* Progress interpolation.
   position arrives at an unreliable rate and differs by source, so the client
   advances the bar itself from the last published position and transport, and
   re-anchors whenever a new state message lands. Transform-free: only a CSS
   custom property and two text nodes change, which a Pi 4 handles at 1 Hz.

   In the Svelte port, call anchor(el, position, duration, transport) from the
   /state subscription; nothing here needs to persist across messages. */
(function () {
  var fmt = function (s) {
    s = Math.max(0, Math.floor(s));
    return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
  };

  document.querySelectorAll('.progress[data-position]').forEach(function (el) {
    var base = parseFloat(el.dataset.position);
    var dur = parseFloat(el.dataset.duration);
    var playing = el.closest('.screen').dataset.transport === 'playing';
    var t0 = performance.now();

    var tick = function () {
      var pos = playing ? base + (performance.now() - t0) / 1000 : base;
      if (dur) pos = Math.min(pos, dur);
      el.querySelector('.progress__fill').style.setProperty('--pos', (dur ? pos / dur * 100 : 0) + '%');
      el.querySelector('[data-elapsed]').textContent = fmt(pos);
      el.querySelector('[data-remaining]').textContent = '-' + fmt(dur - pos);
      if (playing) setTimeout(tick, 500);
    };
    tick();
  });
})();
