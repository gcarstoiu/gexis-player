/* Phase 29, room correction: an invented room for the drawings. Not measured.
   Log-frequency axis 15-300 Hz, 121 points. Modes are peaks and dips; the cuts
   are peaking filters drawn as bumps on log2(f). Target: +3 dB below ~80 Hz. */
(function () {
  const FMIN = 15, FMAX = 300, N = 120;
  const F = []; for (let i = 0; i <= N; i++) F.push(FMIN * Math.pow(FMAX / FMIN, i / N));
  const bump = (f, f0, g, w) => g * Math.exp(-Math.pow(Math.log2(f / f0) * w, 2));
  const target = f => 3 / (1 + Math.pow(f / 70, 4));
  const rng = seed => { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; };
  const MODES = {
    L: [[42, 8, 5], [65, -8, 9], [87, 10, 6], [110, -5, 7], [126, 4, 6], [170, 6, 6], [215, 3, 5]],
    R: [[38, 6, 5], [62, -7, 9], [92, 9, 6], [118, -6, 7], [140, 3.5, 6], [175, 7, 6], [222, 2, 5]]
  };
  const CUTS = {
    L: [[42, -6.5, 5], [87, -8, 6], [126, -3, 6], [170, -5, 6]],
    R: [[38, -4.5, 5], [92, -7, 6], [140, -2.5, 6], [175, -5.5, 6]]
  };
  const DIPS = { L: [65, 110], R: [62, 118] };
  const SEEDS = { L: [11, 23, 37, 41, 53], R: [61, 73, 87, 91, 103] };
  function room(ch, seed, scale) {
    const r = rng(seed);
    const m = MODES[ch].map(([f0, g, w]) => [f0 * (1 + (r() - 0.5) * 0.06), g * scale * (g < 0 ? 0.4 + r() * 1.2 : 0.8 + r() * 0.4), w]);
    const roll = f => (f < 28 ? -18 * Math.log2(28 / f) : 0);
    return F.map(f => roll(f) + 1.2 + target(f) * 0.4 + m.reduce((a, [f0, g, w]) => a + bump(f, f0, g, w), 0));
  }
  const cut = (ch, c) => c.map((v, i) => v + CUTS[ch].reduce((a, [f0, g, w]) => a + bump(F[i], f0, g, w), 0));
  const avg = cs => F.map((_, i) => 10 * Math.log10(cs.reduce((a, c) => a + Math.pow(10, c[i] / 10), 0) / cs.length));
  const cache = {};
  function data(ch, flat) {
    const k = ch + (flat ? 'f' : '');
    if (cache[k]) return cache[k];
    const pos = SEEDS[ch].map(s => room(ch, s, flat ? 0.22 : 1));
    const before = avg(pos);
    const expected = flat ? before : avg(pos.map(c => cut(ch, c)));
    const j = rng(ch === 'L' ? 5 : 9), ph = [j() * 6.3, j() * 6.3, j() * 6.3];
    const measured = expected.map((v, i) => { const u = Math.log2(F[i] / FMIN); return v + 0.45 * Math.sin(u * 2.1 + ph[0]) + 0.3 * Math.sin(u * 4.7 + ph[1]) + 0.2 * Math.sin(u * 9.3 + ph[2]); });
    return (cache[k] = { pos, before, expected, measured, target: F.map(target) });
  }
  // x as a share of the width (0-1) for a frequency; y as a share of the height for a level (±15 dB)
  const fx = f => Math.log(f / FMIN) / Math.log(FMAX / FMIN);
  const vy = v => (15 - Math.max(-15, Math.min(15, v))) / 30;
  function path(curve, w, h) {
    return curve.map((v, i) => (i ? 'L' : 'M') + (fx(F[i]) * w).toFixed(1) + ',' + (vy(v) * h).toFixed(1)).join('');
  }
  // the area between two curves where the first is above the second (what the cuts take away)
  function between(a, b, w, h) {
    let d = '';
    for (let i = 0; i < F.length; i++) d += (i ? 'L' : 'M') + (fx(F[i]) * w).toFixed(1) + ',' + (vy(a[i]) * h).toFixed(1);
    for (let i = F.length - 1; i >= 0; i--) d += 'L' + (fx(F[i]) * w).toFixed(1) + ',' + (vy(Math.min(a[i], b[i])) * h).toFixed(1);
    return d + 'Z';
  }
  const fmtCut = ([f, g]) => ({ f: f + ' Hz', g: (g < 0 ? '−' : '+') + Math.abs(g).toFixed(1) + ' dB' });
  window.RC = {
    F, FMIN, FMAX, fx, vy, data, path, between, target,
    cuts: ch => CUTS[ch].map(fmtCut),
    dips: ch => DIPS[ch],
    output: { short: 'DAC', name: 'HiFiBerry DAC2 HD' },
    mic: { model: 'miniDSP UMIK-1', serial: '707-1234', typed: '707-1235' },
    measuredOn: '3 November 2026', measuredShort: '3 November',
    moves: {
      2: 'About 40 cm to the left of where your head was',
      3: 'About 40 cm to the right of where your head was',
      4: 'About 30 cm in front of where your head was, towards the speakers',
      5: 'About 30 cm behind where your head was'
    },
    // top-down drawing, viewBox 340 x 196: the five places (1 is the head)
    places: [[170, 98], [122, 98], [218, 98], [170, 64], [170, 132]]
  };
})();
