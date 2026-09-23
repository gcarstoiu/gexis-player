// gexis boot — frame renderer (sound). eval'd inside run_script.
// Geometry = Gexis Boot Screens design, option C proportions at 1280x800.
var CFG = {
  W: 1280, H: 800, GROUND: '#101a21',
  T: 115,            // tile edge (design 28 * 4.107)
  WORD: 72,          // wordmark px
  SUB: 30,           // SOUND px
  GAP_MT: 68.6,      // mark -> wordmark
  GAP_WS: 25.1       // wordmark -> SOUND
};

function trk(pts, p) {
  p *= 100;
  if (p <= pts[0][0]) return pts[0][1];
  for (var i = 1; i < pts.length; i++) {
    var a = pts[i - 1], b = pts[i];
    if (p <= b[0]) return b[0] === a[0] ? b[1] : a[1] + (b[1] - a[1]) * ((p - a[0]) / (b[0] - a[0]));
  }
  return pts[pts.length - 1][1];
}

var IV = {
  g:    [[0,0],[4,0],[10,1],[16,0],[100,0]],
  e:    [[0,0],[16,0],[22,1],[28,0],[100,0]],
  i:    [[0,0],[28,0],[34,1],[40,0],[100,0]],
  s:    [[0,0],[40,0],[46,1],[100,1]],
  word: [[0,0],[55,0],[75,1],[100,1]],
  wordY:[[0,6],[55,6],[75,0],[100,0]],   // design px, scaled
  sub:  [[0,0],[68,0],[86,1],[100,1]],
  fx:   [[0,0],[74,0],[100,1]]
};
var PL = {
  halo: [[0,.5],[8,.5],[18,1],[28,.68],[36,.86],[50,.5],[100,.5]],
  w1s:  [[0,.52],[12,.52],[74,1.9],[100,1.9]],
  w1o:  [[0,0],[12,0],[20,.48],[74,0],[100,0]],
  w2s:  [[0,.52],[26,.52],[86,1.9],[100,1.9]],
  w2o:  [[0,0],[26,0],[34,.3],[86,0],[100,0]]
};

var TILES = [
  { ch:'g', gx:-1, gy:-1, lit:'#7ed6bc', ink:'#0d2b24', k:'g' },
  { ch:'e', gx: 1, gy:-1, lit:'#e0a758', ink:'#341f02', k:'e' },
  { ch:'i', gx:-1, gy: 1, lit:'#9fb4e8', ink:'#16213d', k:'i' },
  { ch:'s', gx: 1, gy: 1, lit:'#f2a48f', ink:'#3d1509', k:'s' }
];

// n = 1..100
function renderFrame(n, mk) {
  var T = CFG.T, G = T * 6.5 / 28, R = T * 7.5 / 28, GL = T * 15 / 28;
  var S = T / 28;                        // design->frame scale
  var D = (2 * T + G) * Math.SQRT2;      // diamond extent
  var ringD = D * 1.163;
  var subLine = CFG.SUB * 1.29;
  var block = D + CFG.GAP_MT + CFG.WORD + CFG.GAP_WS + subLine;
  var top = (CFG.H - block) / 2, cx = CFG.W / 2, cy = top + D / 2;

  var intro = n <= 50;
  var p = intro ? (n - 1) / 50 : (n - 51) / 50;

  var fxOp  = intro ? trk(IV.fx, p) : 1;
  var halo  = intro ? 0.5 : trk(PL.halo, p);
  var wordO = intro ? trk(IV.word, p) : 1;
  var wordY = intro ? trk(IV.wordY, p) * S : 0;
  var subO  = intro ? trk(IV.sub, p) : 1;
  var lit   = intro
    ? { g: trk(IV.g, p), e: trk(IV.e, p), i: trk(IV.i, p), s: trk(IV.s, p) }
    : { g: 0, e: 0, i: 0, s: 1 };

  var c = mk(CFG.W, CFG.H), x = c.getContext('2d');
  x.fillStyle = CFG.GROUND; x.fillRect(0, 0, CFG.W, CFG.H);

  // flourish
  if (fxOp > 0.002) {
    var r = ringD / 2;
    x.save(); x.globalAlpha = fxOp;
    var g = x.createRadialGradient(cx, cy, 0, cx, cy, r);
    g.addColorStop(0, 'rgba(242,164,143,' + (0.17 * halo).toFixed(4) + ')');
    g.addColorStop(0.68, 'rgba(242,164,143,0)');
    g.addColorStop(1, 'rgba(242,164,143,0)');
    x.fillStyle = g; x.beginPath(); x.arc(cx, cy, r, 0, 7); x.fill();
    if (!intro) {
      x.lineWidth = 2 * S; x.strokeStyle = '#f2a48f';
      var waves = [[PL.w1s, PL.w1o], [PL.w2s, PL.w2o]];
      for (var w = 0; w < waves.length; w++) {
        var o = trk(waves[w][1], p);
        if (o <= 0.002) continue;
        x.globalAlpha = fxOp * o;
        x.beginPath(); x.arc(cx, cy, r * trk(waves[w][0], p), 0, 7); x.stroke();
      }
    }
    x.restore();
  }

  // tiles
  var off = (T + G) / 2, kk = Math.SQRT1_2;
  for (var t = 0; t < TILES.length; t++) {
    var d = TILES[t];
    var tx = cx + (d.gx * off - d.gy * off) * kk;
    var ty = cy + (d.gx * off + d.gy * off) * kk;
    x.save(); x.translate(tx, ty); x.rotate(Math.PI / 4);
    x.fillStyle = '#2c404f'; x.beginPath(); x.roundRect(-T/2, -T/2, T, T, R); x.fill(); x.restore();
    x.save(); x.translate(tx, ty);
    x.font = '800 ' + GL + 'px BG'; x.textAlign = 'center'; x.textBaseline = 'middle';
    x.fillStyle = '#7690a0'; x.fillText(d.ch, 0, GL * 0.03); x.restore();
    var L = lit[d.k];
    if (L > 0.002) {
      x.save(); x.globalAlpha = L; x.translate(tx, ty); x.rotate(Math.PI / 4);
      x.fillStyle = d.lit; x.beginPath(); x.roundRect(-T/2, -T/2, T, T, R); x.fill(); x.restore();
      x.save(); x.globalAlpha = L; x.translate(tx, ty);
      x.font = '800 ' + GL + 'px BG'; x.textAlign = 'center'; x.textBaseline = 'middle';
      x.fillStyle = d.ink; x.fillText(d.ch, 0, GL * 0.03); x.restore();
    }
  }

  var wordTop = top + D + CFG.GAP_MT;
  if (wordO > 0.002) {
    x.save(); x.globalAlpha = wordO;
    x.textAlign = 'center'; x.textBaseline = 'alphabetic';
    x.font = '600 ' + CFG.WORD + 'px BG';
    x.letterSpacing = (-0.01 * CFG.WORD).toFixed(2) + 'px';
    x.fillStyle = '#e8eef2';
    x.fillText('gexis', cx, wordTop + CFG.WORD * (68 / 96) + wordY);
    x.restore();
  }
  if (subO > 0.002) {
    x.save(); x.globalAlpha = subO;
    x.textAlign = 'center'; x.textBaseline = 'alphabetic';
    x.font = '600 ' + CFG.SUB + 'px DMM, monospace';
    x.letterSpacing = (CFG.SUB * 0.2).toFixed(2) + 'px';
    x.fillStyle = '#f2a48f';
    x.fillText('SOUND', cx + CFG.SUB * 0.1, wordTop + CFG.WORD + CFG.GAP_WS + subLine * 0.72);
    x.restore();
  }
  return c;
}
