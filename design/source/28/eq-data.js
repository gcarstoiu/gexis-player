// Phase 20, the equaliser: bands, presets and the combined curve.
// Presets are ADR-0162's starting values, low band to high. The curve is
// the sum of ten peaking biquads (RBJ cookbook, one octave wide, Q = sqrt 2)
// at 48 kHz, which is what CamillaDSP's GraphicEqualizer runs; the headroom
// is its highest point rounded up to 0.5 dB (ADR-0162 D3).
(function () {
  var BANDS = ['31', '63', '125', '250', '500', '1k', '2k', '4k', '8k', '16k'];
  var CENTRES = BANDS.map(function (_, i) { return 31.25 * Math.pow(2, i); });
  var PRESETS = [
    { k: 'flat', name: 'Flat', g: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] },
    { k: 'rock', name: 'Rock', g: [4, 3, 2, 0, -1, -1, 0, 2, 3, 4] },
    { k: 'pop', name: 'Pop', g: [-1, 0, 2, 3, 2, 0, -1, -1, 0, 1] },
    { k: 'jazz', name: 'Jazz', g: [3, 2, 1, 2, -1, -1, 0, 1, 2, 3] },
    { k: 'classical', name: 'Classical', g: [3, 2, 1, 0, 0, 0, 0, -1, -1, -2] },
    { k: 'electronic', name: 'Electronic', g: [4, 4, 1, 0, -2, 1, 0, 1, 3, 4] },
    { k: 'hiphop', name: 'Hip-hop', g: [5, 4, 1, 2, -1, -1, 1, -1, 2, 3] },
    { k: 'acoustic', name: 'Acoustic', g: [3, 3, 2, 1, 1, 1, 2, 3, 2, 1] },
    { k: 'vocal', name: 'Vocal', g: [-2, -1, -1, 0, 2, 3, 3, 2, 0, -1] },
    { k: 'late', name: 'Late night', g: [5, 4, 2, 0, 0, 0, 0, 1, 2, 3] }
  ];
  // the owner's own: sample names and settings, for the drawing only
  var OWN = [
    { k: 'evening', name: 'Evening', g: [2, 2, 1, 0, 0, -1, -1, 0, 1, 1] },
    { k: 'kitchen', name: 'Kitchen radio', g: [-3, -2, 0, 1, 2, 2, 1, 0, -1, -2] },
    { k: 'records', name: 'Old records', g: [1, 1, 0, 0, 1, 2, 1, -1, -3, -5] }
  ];
  var OWN_MORE = ['Sunday', 'Party', 'Headphones', 'Podcasts', 'Bright', 'Warm', 'Night bus'];
  var OWN_FULL = OWN.concat(OWN_MORE.map(function (n, i) {
    return { k: 'more' + i, name: n, g: [i % 3, 1, 0, 0, 0, 0, 0, 1, (i % 2) * 2, 1] };
  }));
  var OUTPUTS = {
    dac: { short: 'DAC', name: 'HiFiBerry DAC+ HD' },
    hdmi: { short: 'HDMI', name: 'HDMI · Samsung TV' },
    optical: { short: 'Optical', name: 'Optical · HiFiBerry Digi+' }
  };
  var FS = 48000, Q = Math.SQRT2;

  function bandDb(f0, gain, f) {
    if (!gain) return 0;
    var A = Math.pow(10, gain / 40);
    var w0 = 2 * Math.PI * f0 / FS;
    var al = Math.sin(w0) / (2 * Q), c = Math.cos(w0);
    var b0 = 1 + al * A, b1 = -2 * c, b2 = 1 - al * A;
    var a0 = 1 + al / A, a1 = -2 * c, a2 = 1 - al / A;
    var w = 2 * Math.PI * f / FS;
    var cw = Math.cos(w), sw = Math.sin(w), c2 = Math.cos(2 * w), s2 = Math.sin(2 * w);
    var nr = b0 + b1 * cw + b2 * c2, ni = -(b1 * sw + b2 * s2);
    var dr = a0 + a1 * cw + a2 * c2, di = -(a1 * sw + a2 * s2);
    return 10 * Math.log10((nr * nr + ni * ni) / (dr * dr + di * di));
  }
  function at(g, f) {
    var s = 0;
    for (var i = 0; i < 10; i++) s += bandDb(CENTRES[i], g[i], f);
    return s;
  }
  // n points from half an octave below the first band to 20 kHz
  var OCT_END = Math.log(20000 / 31.25) / Math.LN2;
  function curve(g, n) {
    n = n || 121;
    var out = [];
    for (var j = 0; j < n; j++) {
      var oct = -0.5 + ((OCT_END + 0.5) * j) / (n - 1);
      out.push({ oct: oct, db: at(g, 31.25 * Math.pow(2, oct)) });
    }
    return out;
  }
  function headroom(g) {
    var peak = 0;
    curve(g, 241).forEach(function (p) { if (p.db > peak) peak = p.db; });
    return peak <= 0.05 ? 0 : Math.ceil(peak * 2 - 0.1) / 2;
  }
  // an SVG path for the curve in a box: column width cw, zero at y0, px per dB
  function path(g, cw, y0, perDb, top, bottom) {
    var pts = curve(g);
    var line = pts.map(function (p, i) {
      var x = (p.oct + 0.5) * cw;
      var y = Math.max(top, Math.min(bottom, y0 - p.db * perDb));
      return (i ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1);
    }).join(' ');
    var w = (10 * cw).toFixed(1);
    var end = ((OCT_END + 0.5) * cw).toFixed(1);
    return { line: line, area: line + ' L' + end + ' ' + y0 + ' L0 ' + y0 + ' Z' };
  }
  function fmt(v) { return v > 0 ? '+' + v : v < 0 ? '\u2212' + Math.abs(v) : '0'; }
  function dbText(h) { return (h % 1 ? h.toFixed(1) : String(h)) + ' dB'; }

  window.EQ = { BANDS: BANDS, CENTRES: CENTRES, PRESETS: PRESETS, OWN: OWN, OWN_FULL: OWN_FULL, OUTPUTS: OUTPUTS,
    at: at, curve: curve, headroom: headroom, path: path, fmt: fmt, dbText: dbText };
})();
