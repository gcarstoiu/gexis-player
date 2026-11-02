/* Phase 28 sampler build. Run in the project's script runner:
     eval(await readFile('design/source/28/build.js')); await build();
   Reads the themes in themes.js and writes, per theme, a recoloured copy of
   each source design (never edits the source) and a tokens-<id>.css made by
   the same substitution over design/tokens.css. Layout is untouched: only
   colour literals, the cover veil, the weave angle, the mono family (and its
   size where the face runs small), and px corner radii change. */
async function build() {
  const w = {}; (new Function('window', await readFile('design/source/28/themes.js')))(w);
  const THEMES = w.GX_THEMES;
  const hex2 = h => { h = h.replace('#', ''); if (h.length === 3) h = h.split('').map(c => c + c).join(''); return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16)); };
  const toHex = c => '#' + c.map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('');
  const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
  const lum = c => 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  function makeMap(T) {
    const fam = {
      '233,238,242': 'ink', '238,243,247': 'ink', '244,248,251': 'ink',
      '126,214,188': 'lms', '168,229,211': 'lmsHi', '242,164,143': 'artist', '248,196,180': 'artistHi',
      '159,180,232': 'bluetooth', '143,217,168': 'spotify', '224,167,88': 'warn', '200,162,216': 'display',
      '63,90,109': 'weaveA', '46,68,83': 'weaveB', '55,80,95': 'weaveM', '13,21,28': 'ground', '13,21,27': 'ground'
    };
    const C = {};
    for (const k of ['ink', 'lms', 'artist', 'bluetooth', 'spotify', 'warn', 'display', 'weaveA', 'weaveB', 'base', 'panel', 'well', 'desk', 'onAccent']) C[k] = hex2(T[k]);
    C.lmsHi = mix(C.lms, T.light ? [0, 0, 0] : [255, 255, 255], 0.3);
    C.artistHi = mix(C.artist, T.light ? [0, 0, 0] : [255, 255, 255], 0.3);
    C.weaveM = mix(C.weaveA, C.weaveB, 0.5);
    const textA = a => T.light ? (a >= 0.45 ? Math.min(1, 0.35 + 0.65 * a) : a * 1.1) : a;
    return (rgb, a, isHex) => {
      const k = rgb.join(',');
      if (isHex) {
        const h = toHex(rgb);
        if (h === '#0d151c') return [C.onAccent, 1];
        if (h === '#101a21') return [C.base, 1];
        if (h === '#0c1014') return [C.desk, 1];
        if (h === '#16232c' || h === '#0b1218') return [C.panel, 1];
        if (h === '#17242d') return [C.well, 1];
      }
      if (fam[k]) { const f = fam[k]; if (f === 'ground') return [C.panel, a]; return [C[f], (f === 'ink' || f === 'artist' || f === 'lms') && a < 1 ? +textA(a).toFixed(3) : a]; }
      if (k === '255,255,255' && a < 1) return [C.ink, +(T.light ? a * 1.1 : a).toFixed(3)];
      if (k === '0,0,0' && a < 1) return [rgb, +(T.light ? a * 0.35 : a).toFixed(3)];
      if (Math.max(...rgb) < 75 && rgb[2] >= rgb[0] && rgb[2] > 8) return [lum(rgb) <= lum([16, 26, 33]) ? C.base : C.panel, a];
      return null;
    };
  }
  const fmt = (c, a) => `rgba(${c.map(Math.round).join(',')},${a})`;
  function recolour(text, T) {
    const map = makeMap(T);
    const veil = `radial-gradient(130% 105% at 20% 42%,rgba(${hex2(T.base)},${T.veil[0]}),rgba(${hex2(T.base)},${T.veil[1]}))`;
    text = text.split('radial-gradient(130% 105% at 20% 42%,rgba(22,36,46,0.3),rgba(14,23,30,0.86))').join(veil);
    text = text.split('radial-gradient(130% 105% at 20% 42%, rgba(22,36,46,0.3), rgba(14,23,30,0.86))').join(veil);
    text = text.replace(/repeating-linear-gradient\(38deg,\s*#3f5a6d/g, `repeating-linear-gradient(${T.weaveAngle}deg,#3f5a6d`);
    text = text.replace(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)/g, (m, r, g, b, a) => { const res = map([+r, +g, +b], a === undefined ? 1 : +a, false); return res ? (res[1] === 1 && a === undefined ? toHex(res[0]) : fmt(res[0], res[1])) : m; });
    text = text.replace(/#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F\w])/g, (m, h) => { const res = map(hex2(h), 1, true); return res ? (res[1] === 1 ? toHex(res[0]) : fmt(res[0], res[1])) : m; });
    text = text.replace(/(['"])(\d{1,3}),\s?(\d{1,3}),\s?(\d{1,3})\1/g, (m, q, r, g, b) => { const res = map([+r, +g, +b], 1, false); return res ? q + res[0].map(Math.round).join(',') + q : m; });
    text = text.split("'IBM Plex Mono'").join(T.mono).split('"IBM Plex Mono"').join(T.mono);
    if (T.monoScale !== 1) text = text.replace(/style="([^"]*)"/g, (m, s) => s.includes(T.mono) ? 'style="' + s.replace(/font-size:\s*([\d.]+)px/g, (mm, v) => 'font-size:' + Math.round(+v * T.monoScale) + 'px') + '"' : m);
    text = text.replace(/border-radius:\s*(\d+(?:\.\d+)?)px/g, (m, v) => +v >= 900 || +v < 4 ? m : 'border-radius:' + Math.max(2, Math.round(+v * T.radius)) + 'px');
    text = text.replace(/(--r-(?:sm|md|lg|xl|card)|--[\w-]*radius[\w-]*):\s*(\d+)px/g, (m, k, v) => k + ':' + (+v < 4 ? v : Math.max(2, Math.round(+v * T.radius))) + 'px');
    return text;
  }
  const SRC = { np: 'design/source/22/Now Playing.dc.html', bar: 'design/source/19/Bar Frame.dc.html', phone: 'design/source/22/Phone Remote Multiroom.dc.html', settings: 'design/source/22/Settings.dc.html' };
  // Artboard states come from the URL, so one copy serves every artboard:
  //   ?prop=value   overrides a prop          ?s_key=value  sets initial state
  //   ?call=method  calls a method on mount   ?cover=bright swaps in the bright test cover
  const QP = `
  qp() {
    if (!this.__qpo) { const o = {}, s = {}; new URLSearchParams(location.search).forEach((v, k) => { const x = v === 'true' ? true : v === 'false' ? false : (v !== '' && !isNaN(+v) ? +v : v); if (k.startsWith('s_')) s[k.slice(2)] = x; else if (k !== 'cover' && k !== 'call') o[k] = x; }); this.__qpo = o; this.__qps = s; }
    return Object.assign({}, this.props, this.__qpo);
  }
  constructor(...a) {
    super(...a); this.qp();
    const s = this.__qps, call = new URLSearchParams(location.search).get('call'), cdm = this.componentDidMount;
    if (Object.keys(s).length || call) this.componentDidMount = function () { if (Object.keys(s).length) this.setState(s); if (call && this[call]) this[call](); if (cdm) cdm.call(this); };
  }`;
  const COVER = `<script>if(/[?&]cover=bright/.test(location.search)){const f=()=>document.querySelectorAll('img[src$="album-art.webp"]').forEach(i=>i.setAttribute('src','album-art-bright.png'));new MutationObserver(f).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['src']});f();}</script>`;
  const wire = (t, id) => {
    const i = t.indexOf('<script type="text/x-dc" data-dc-script');
    let js = t.slice(i).split('this.props').join('this.qp()').replace('class Component extends DCLogic {', 'class Component extends DCLogic {' + QP);
    return t.slice(0, i).split('<dc-import name="Settings"').join('<dc-import name="' + id + '-settings"').replace('<helmet>', '<helmet>\n' + COVER) + js;
  };
  const TOK = await readFile('design/tokens.css');
  const BT = await readFile('design/marks/bluetooth.svg');
  const srcText = {}; for (const [k, f] of Object.entries(SRC)) srcText[k] = await readFile(f);
  for (const T of THEMES) {
    const link = `<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=${T.monoGF}&display=swap" />`;
    for (const [k, t0] of Object.entries(srcText)) {
      let t = recolour(t0, T).replace('<helmet>', '<helmet>\n' + link);
      if (k === 'phone') t = t.replace(/(&quot;open&quot;:\{[^}]*?&quot;default&quot;:&quot;)menu(&quot;)/, '$1none$2');
      t = wire(t, T.id).split('icon-bluetooth.png').join(T.id + '-bluetooth.svg');
      await saveFile(`design/source/28/${T.id}-${k}.dc.html`, t);
    }
    await saveFile(`design/source/28/${T.id}-bluetooth.svg`, BT.replace('#9fb4e8', T.bluetooth)); // our mark, drawn in the theme's --accent-bluetooth
    let tok = recolour(TOK, T);
    tok = tok.replace('/* gexis panel — design tokens', `/* gexis panel — theme "${T.name}", Phase 28.\n   ${T.line}\n   Generated by design/source/28/build.js from design/tokens.css: same names, new values.\n   Type scale, metrics and motion keep today’s values.\n   Alpha comments below are today’s; this theme’s figures are in Theme Spec.dc.html.\n   Mono: ${T.mono} (${T.monoLicence}); ship its woff2 in design/fonts before use.\n\n   gexis panel — design tokens`);
    tok = tok.replace('  /* ---- accents', `  /* NEW: the cover's darkening on Now Playing, a literal in code until now */\n  --cover-veil: radial-gradient(130% 105% at 20% 42%,rgba(${hex2(T.base)},${T.veil[0]}),rgba(${hex2(T.base)},${T.veil[1]}));\n\n  /* ---- accents`);
    await saveFile(`design/themes/tokens-${T.id}.css`, tok);
  }
}
