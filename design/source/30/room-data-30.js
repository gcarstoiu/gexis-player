/* Phase 30, room correction for the full range: an invented room for the drawings. Not measured.
   Log axis 15 Hz to 20 kHz. Three positions per speaker (as built). Below 250 Hz: narrow cuts only.
   Above 250 Hz: broad corrections of at most 3 dB, up or down, to the speaker's own balance.
   Target: the bass's +3 dB rise below ~80 Hz, joined to the speaker's own slope above 250 Hz. */
(function () {
  const FMIN = 15, FMAX = 20000, N = 300;
  const F = []; for (let i = 0; i <= N; i++) F.push(FMIN * Math.pow(FMAX / FMIN, i / N));
  const L2 = Math.log2;
  const bell = (f, f0, g, w) => g * Math.exp(-Math.pow(L2(f / f0) * w, 2));
  const rise = f => 3 / (1 + Math.pow(f / 70, 4));
  const tilt = f => (f <= 250 ? 0 : -0.42 * L2(f / 250)) - (f > 15000 ? 5 * Math.pow(L2(f / 15000), 2) : 0);
  const target = f => rise(f) + tilt(f);
  const rng = seed => { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; };
  const MODES = {
    L: [[46, 13, 5], [68, -9, 8], [92, 8, 6], [118, -5, 7], [140, 4, 6], [182, 6, 6]],
    R: [[42, 11, 5], [64, -8, 8], [96, 9, 6], [122, -6, 7], [150, 3.5, 6], [176, 7, 6]]
  };
  const BROAD = {
    L: [[480, 2.8, 1.5], [1100, -1.0, 1.8], [2400, -3.0, 1.4], [5200, 2.3, 1.6], [11000, -1.8, 1.5]],
    R: [[520, 2.3, 1.5], [1300, 0.9, 1.8], [2600, -2.7, 1.4], [6000, 1.8, 1.6], [12000, -2.4, 1.5]]
  };
  const CUTS = {
    L: [[46, -14, 5], [92, -7.5, 6], [140, -3, 6], [182, -5.5, 6]],
    R: [[42, -11.5, 5], [96, -8.5, 6], [150, -2.5, 6], [176, -6.5, 6]]
  };
  const EVEN = {
    L: [[480, -2.5, 1.5], [2400, 2.5, 1.4], [5200, -2.0, 1.6], [11000, 1.5, 1.5]],
    R: [[520, -2.0, 1.5], [2600, 2.5, 1.4], [6000, -1.5, 1.6], [12000, 2.0, 1.5]]
  };
  const DIPS = { L: [68, 118], R: [64, 122] };
  const SEEDS = { L: [11, 23, 37], R: [61, 73, 87] };
  const sum = (list, f) => list.reduce((a, [f0, g, w]) => a + bell(f, f0, g, w), 0);
  function pos(ch, seed, set) {
    const r = rng(seed);
    const bs = set === 'flatbass' || set === 'flat' ? 0.2 : 1, as = set === 'flatabove' || set === 'flat' ? 0.28 : 1;
    const m = MODES[ch].map(([f0, g, w]) => [f0 * (1 + (r() - 0.5) * 0.06), g * bs * (g < 0 ? 0.5 + r() : 0.85 + r() * 0.3), w]);
    const ph = [r() * 6.28, r() * 6.28, r() * 6.28];
    return F.map(f => {
      const u = L2(f);
      const roll = f < 28 ? -18 * L2(28 / f) : 0;
      const fade = Math.min(1, Math.max(0, L2(f / 160)));
      const amp = 0.55 + 1.7 * Math.min(1, Math.max(0, L2(f / 400) / 5));
      const rip = fade * amp * (0.6 * Math.sin(u * 3.3 + ph[0]) + 0.4 * Math.sin(u * 7.1 + ph[1]) + 0.25 * Math.sin(u * 13.7 + ph[2]));
      return roll + target(f) * (f < 250 ? 0.4 : 1) + sum(m, f) + as * sum(BROAD[ch], f) + rip;
    });
  }
  const corr = (ch, set, reach) => F.map(f => (set === 'flatbass' || set === 'flat' ? 0 : sum(CUTS[ch], f)) + (reach === 'bass' || set === 'flatabove' || set === 'flat' || set === 'bassonly' ? 0 : sum(EVEN[ch], f)));
  const avg = cs => F.map((_, i) => 10 * Math.log10(cs.reduce((a, c) => a + Math.pow(10, c[i] / 10), 0) / cs.length));
  const cache = {};
  function one(ch, set, reach) {
    const positions = SEEDS[ch].map(s => pos(ch, s, set));
    const c = corr(ch, set, reach);
    return { positions, before: avg(positions), expected: avg(positions.map(p => p.map((v, i) => v + c[i]))), corr: c };
  }
  function data(ch, set, reach) {
    set = set || 'normal'; reach = reach || 'full';
    const k = ch + set + reach;
    if (cache[k]) return cache[k];
    let d;
    if (ch === 'B') {
      const l = one('L', set, reach), r = one('R', set, reach);
      d = { positions: [0, 1, 2].map(i => avg([l.positions[i], r.positions[i]])), before: avg([l.before, r.before]), expected: avg([l.expected, r.expected]) };
    } else d = one(ch, set, reach);
    const j = rng(ch === 'L' ? 5 : ch === 'R' ? 9 : 13), ph = [j() * 6.3, j() * 6.3, j() * 6.3];
    const measured = d.expected.map((v, i) => { const u = L2(F[i] / FMIN); return v + 0.45 * Math.sin(u * 2.1 + ph[0]) + 0.3 * Math.sin(u * 4.7 + ph[1]) + 0.2 * Math.sin(u * 9.3 + ph[2]); });
    const cut = (c, lim) => c.map((v, i) => (F[i] > lim ? null : v));
    const lim = set === 'bassonly' ? 252 : 1e9, alim = set === 'bassonly' || reach === 'bass' ? 262 : 1e9;
    // the chart's bass reach grows past ±15 dB in 5 dB steps, the same for every tab (as built)
    let m = 0;
    ['L', 'R'].forEach(c => { const o = one(c, set, reach); [o.before].concat(o.positions).forEach(cv => cv.forEach((v, i) => { if (F[i] >= 20 && F[i] <= 250) m = Math.max(m, Math.abs(v)); })); });
    const bassRange = Math.max(15, Math.ceil((m + 0.5) / 5) * 5);
    // the result's numbers
    let peak = 0, within = 0;
    const sm = c => c.map((_, i) => { let a = 0, n = 0; for (let k = -5; k <= 5; k++) { const v = c[i + k]; if (v != null) { a += v; n++; } } return a / n; });
    const ex = sm(d.expected), tg = F.map(target), be = sm(d.before);
    F.forEach((f, i) => { if (f >= 25 && f <= 250) peak = Math.max(peak, d.before[i] - d.expected[i]); if (f >= 300 && f <= 14000) within = Math.max(within, Math.abs(ex[i] - tg[i])); });
    let roomAbove = 0; F.forEach((f, i) => { if (f >= 300 && f <= 14000) roomAbove = Math.max(roomAbove, Math.abs(be[i] - tg[i])); });
    return (cache[k] = {
      positions: d.positions.map(p => cut(p, lim)), before: cut(d.before, lim), target: cut(tg, lim),
      expected: cut(d.expected, alim), measured: cut(measured, alim), bassRange,
      peak: Math.round(peak), within: Math.max(0.5, Math.ceil(within * 2) / 2), roomAbove: Math.ceil(roomAbove * 2) / 2
    });
  }
  const fx = (f, s) => Math.log(f / s.x0) / Math.log(s.x1 / s.x0);
  function path(c, s, w, h) {
    let d = '', pen = false;
    for (let i = 0; i < F.length; i++) {
      const f = F[i], v = c[i];
      if (v == null || f < s.x0 / 1.04 || f > s.x1 * 1.04) { pen = false; continue; }
      d += (pen ? 'L' : 'M') + (fx(f, s) * w).toFixed(1) + ',' + ((s.yr - v) / (2 * s.yr) * h).toFixed(1); pen = true;
    }
    return d;
  }
  // the area where a is above b
  function fill(a, b, s, w, h) {
    let d = '', run = [];
    const flush = () => { if (run.length > 1) d += run.map((p, k) => (k ? 'L' : 'M') + p[0] + ',' + p[1]).join('') + run.slice().reverse().map(p => 'L' + p[0] + ',' + p[2]).join('') + 'Z'; run = []; };
    for (let i = 0; i < F.length; i++) {
      const f = F[i];
      if (f < s.x0 / 1.04 || f > s.x1 * 1.04 || a[i] == null || b[i] == null || a[i] - b[i] < 0.05) { flush(); continue; }
      const x = (fx(f, s) * w).toFixed(1), y = v => ((s.yr - v) / (2 * s.yr) * h).toFixed(1);
      run.push([x, y(a[i]), y(b[i])]);
    }
    flush();
    return d;
  }
  const fmtF = f => f < 1000 ? f + ' Hz' : (f / 1000).toFixed(f < 10000 ? 1 : 0).replace(/\.0$/, '') + ' kHz';
  const fmtG = g => (g < 0 ? '−' : '+') + Math.abs(g).toFixed(1) + ' dB';
  const list = (ch, set, reach) => ({
    bass: set === 'flatbass' || set === 'flat' ? [] : CUTS[ch].map(([f, g]) => ({ f: fmtF(f), g: fmtG(g), up: false, raw: f, gain: g })),
    above: set === 'flatabove' || set === 'flat' || set === 'bassonly' || reach === 'bass' ? [] : EVEN[ch].map(([f, g]) => ({ f: fmtF(f), g: fmtG(g), up: g > 0, raw: f, gain: g }))
  });
  window.RC30 = { F, fx, data, path, fill, target, list, dips: ch => DIPS[ch], fmtF, fmtG };
})();
