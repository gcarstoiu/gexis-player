<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **First use: setup (part 1) and make it yours (part 2)** (ADR-0149;
  Phase 14, `ph-first-use`). `mode` p1 is setup, on the setup network;
  p2 is part 2, at the player's own address.

  GENERATED from Claude Design's `Setup Prototype.dc.html` (first-use
  hand-off) by `tools/design/gen_personalise.py`: the frame's markup and
  inline styles converted mechanically, the prototype's own logic -
  screens, paths, copy, Back and Next - kept verbatim, with the documented
  replacements where the prototype simulates what the player does. Change
  the design, then generate again; do not restyle by hand.
-->
<script>
  import { onMount } from 'svelte';
  import mark from '../assets/gexis-mark.svg';
  import lyrionIcon from '../assets/icon-lyrion.svg';
  import spotifyIcon from '../assets/icon-spotify.png';
  import btIcon from '../assets/icon-bluetooth.png';
  import calmWall from '../assets/personalise/calm.webp';
  import colourfulWall from '../assets/personalise/colourful.webp';
  import psychedelicWall from '../assets/personalise/psychedelic.webp';
  import PanelMini from './personalise/PanelMini.svelte';
  import PhoneDeviceList from './personalise/PhoneDeviceList.svelte';
  import { loadSettings, settingValues, settingsDevice, listItems, listAction, writeSetting } from '../lib/settings.js';
  import { pairing, components, settling, answerPairing, personaliseLater } from '../lib/state.js';
  import { SvelteSet } from 'svelte/reactivity';

  //: `mode`: 'p1' (setup, over the setup network or the cable) or 'p2' (make it
  //: yours, from the home network). `setup`: `/state`'s setup, in part 1.
  let { mode = 'p2', setup = null, onclose } = $props();

  //: The prototype's runtime (`support.js`) gives its Component React's
  //: setState; this is that, over Svelte state, so the design's logic below
  //: runs as written.
  class DCLogic {
    setState(u, cb) {
      const next = typeof u === 'function' ? u(this.state) : u;
      if (next) Object.assign(this.state, next);
      if (cb) cb();
    }
  }

  // ===== The design's logic, from Setup Prototype.dc.html =====

const C = { music: '#b0bcc4', lyr: '#9fb4e8', fold: '#f2a48f', browse: '#8fd9a8', spo: '#7ed6bc', bt: '#d8c88f', scr: '#c8a2d8', idle: '#e8a0b4', stby: '#8fc4d8', ext: '#a8d68f', plex: '#e0a758', rev: '#7ed6bc' };
const SEL = 'rgba(126,214,188,0.1)', SELB = 'rgba(126,214,188,0.45)', OFF = 'rgba(255,255,255,0.05)', OFFB = 'rgba(233,238,242,0.1)', RING = 'rgba(233,238,242,0.42)', MUTE = 'rgba(233,238,242,0.6)';
const TAGS = { ok: ['rgba(126,214,188,0.14)', '#7ed6bc'], warn: ['rgba(224,167,88,0.14)', '#e0a758'], plain: ['rgba(233,238,242,0.08)', 'rgba(233,238,242,0.72)'] };
const TONES = { info: ['#8fc4d8', OFF, OFFB], ok: ['#7ed6bc', OFF, OFFB], warn: ['#e0a758', 'rgba(224,167,88,0.08)', 'rgba(224,167,88,0.45)'] };
const LETTER = { plex: 'P', viz: 'V', clk: 'C', stby: 'S', besz: 'B', lib: 'M', fold: 'F', browse: 'B', ext: '+' };
const BTYPES = ['List', 'Note', 'Field', 'Status', 'P', 'Btn', 'Pics', 'Where', 'Split', 'Seg', 'Pick', 'Num', 'Code', 'Party', 'Dev', 'Prog', 'Cast', 'Sum', 'Clock', 'Addr', 'Iv', 'Head', 'Rule'];
const noop = () => {};
const SRCN = { lyr: 'Lyrion', spo: 'Spotify', bt: 'Bluetooth', plex: 'Plexamp' };
const tagOf = tag => {
  if (!tag) return { tagDisplay: 'none', tag: '', tagBg: 'transparent', tagInk: '#e9eef2' };
  const [text, tone] = Array.isArray(tag) ? tag : [tag, 'plain'];
  return { tagDisplay: 'block', tag: text, tagBg: TAGS[tone][0], tagInk: TAGS[tone][1] };
};
function row(o) {
  const k = o.k, radio = k === 'radio', net = k === 'net', ghost = k === 'ghost', sel = (radio || net || k === 'chk') && o.on;
  const img = ['lyr', 'spo', 'bt'].includes(o.icon), letter = LETTER[o.icon] || '';
  const bar = n => n <= (o.lvl || 0) ? '#8fc4d8' : 'rgba(233,238,242,0.22)';
  return Object.assign({
    label: o.label, labelInk: ghost ? MUTE : '#e9eef2', note: o.note || '', noteDisplay: o.note ? 'block' : 'none', meta: o.meta || '', metaDisplay: o.meta ? 'block' : 'none',
    onClick: o.fn || noop, cursor: o.fn ? 'pointer' : 'default',
    bg: ghost ? 'transparent' : sel ? SEL : OFF, border: ghost ? 'rgba(233,238,242,0.3)' : sel ? SELB : OFFB, bs: ghost ? 'dashed' : 'solid',
    radioDisplay: radio || net ? 'flex' : 'none', ring: sel ? '#7ed6bc' : RING, dotDisplay: sel ? 'block' : 'none',
    iconDisplay: img || letter ? 'flex' : 'none', isLyr: o.icon === 'lyr', isSpo: o.icon === 'spo', isBt: o.icon === 'bt', letter, letterDisplay: letter && !img ? 'flex' : 'none',
    barsDisplay: net ? 'flex' : 'none', b1: bar(1), b2: bar(2), b3: bar(3), b4: bar(4),
    togDisplay: k === 'tog' ? 'block' : 'none', togBg: o.on ? '#7ed6bc' : 'rgba(233,238,242,0.07)', togBorder: o.on ? '#7ed6bc' : 'rgba(233,238,242,0.18)',
    knobLeft: o.on ? '31px' : '3px', knobBg: o.on ? '#0d151c' : 'rgba(233,238,242,0.55)',
    chkDisplay: k === 'chk' ? 'flex' : 'none', boxBg: sel ? '#7ed6bc' : 'transparent', chevDisplay: k === 'hub' ? 'block' : 'none',
    srcs: (o.srcs || []).map(x => ({ isLyr: x === 'lyr', isSpo: x === 'spo', isBt: x === 'bt', isPlex: x === 'plex', name: SRCN[x] })), srcDisplay: o.srcs ? 'flex' : 'none',
    foot: o.foot || '', footMeta: o.footMeta || '', footDisplay: o.foot ? 'flex' : 'none', footDot: o.footDot || '#7ed6bc'
  }, tagOf(o.tag));
}
function block(b) {
  const o = { head: b.head || '', headDisplay: b.head ? 'block' : 'none' };
  BTYPES.forEach(t => { o['is' + t] = b.t === t; });
  if (b.t === 'List') o.rows = b.rows.map(row);
  if (b.t === 'Note') { const c = TONES[b.tone]; Object.assign(o, { bar: c[0], bg: c[1], border: c[2], title: b.title || '', titleDisplay: b.title ? 'block' : 'none', text: b.text }); }
  if (b.t === 'Field') Object.assign(o, { label: b.label, value: b.value, onChange: b.fn || noop, ph: b.ph || '', type: b.type || 'text', hint: b.hint || '', hintDisplay: b.hint ? 'block' : 'none', ro: !!b.ro, op: b.ro ? '0.45' : '1', cur: b.ro ? 'not-allowed' : 'text' });
  if (b.t === 'Code') Object.assign(o, { label: b.label, code: b.code, text: b.text });
  if (b.t === 'Party') Object.assign(o, { marks: b.marks, status: b.status });
  if (b.t === 'Status') { const f = b.field; Object.assign(o, { act: b.act || '', onAct: b.actFn || noop, actDisplay: b.act ? 'block' : 'none', fieldDisplay: f ? 'flex' : 'none', fLabel: f ? f.label : '', fValue: f ? f.value : '', fPh: f ? f.ph || '' : '', fOnChange: f ? f.fn : noop, fHint: f ? f.hint || '' : '' }); }
  if (b.t === 'Status') Object.assign(o, { text: b.text, meta: b.meta || '', metaDisplay: b.meta ? 'block' : 'none', spinDisplay: b.state === 'spin' ? 'block' : 'none', doneDisplay: b.state === 'ok' ? 'flex' : 'none', noneDisplay: b.state === 'none' ? 'block' : 'none' });
  if (b.t === 'P' || b.t === 'Head') o.text = b.text;
  if (b.t === 'Btn') Object.assign(o, { label: b.label, onClick: b.fn || noop });
  if (b.t === 'Pics') {
    const rows = b.layout === 'rows';
    const g3 = b.layout === 'grid3';
    o.cols = rows ? 'minmax(0,1fr)' : g3 ? 'repeat(3,minmax(0,1fr))' : 'repeat(2,minmax(0,1fr))';
    o.items = b.items.map(p => Object.assign({
      kind: p.kind, marks: p.marks || [], rpm: p.rpm || 33, label: p.label, note: p.note || '', noteDisplay: p.note ? 'block' : 'none', onClick: p.fn,
      bg: p.on ? 'rgba(143,217,168,0.1)' : OFF, border: p.on ? 'rgba(143,217,168,0.5)' : OFFB, wire: p.on ? '#8fd9a8' : 'rgba(233,238,242,0.18)',
      ring: p.on ? '#7ed6bc' : RING, dot: p.on ? 'block' : 'none',
      lfs: g3 ? '13px' : '15px', dir: rows ? 'row' : 'column', mw: rows ? '46%' : '100%', gap: rows ? '14px' : '10px', ai: rows ? 'center' : 'stretch', lpr: rows ? '30px' : '4px'
    }, tagOf(p.tag)));
  }
  if (b.t === 'Where') o.items = [['here', 'On this player'], ['pc', 'On a computer or NAS']].map(w => { const on = w[0] === b.sel, far = w[0] === 'pc';
    return { label: w[1], onClick: () => b.fn(w[0]), bg: on ? SEL : OFF, border: on ? SELB : OFFB, ring: on ? '#7ed6bc' : RING, dot: on ? 'block' : 'none', wire: on ? '#9fb4e8' : 'rgba(233,238,242,0.4)', isHere: !far, isFar: far }; });
  if (b.t === 'Split') Object.assign(o, { lhead: b.lhead, rhead: b.rhead, left: b.left.map(t => ({ t })), right: b.right.map(t => ({ t })) });
  if (b.t === 'Seg') o.opts = b.opts.map((x, i) => ({ label: x, onClick: () => b.fn(i), bg: i === b.on ? b.accent : 'transparent', ink: i === b.on ? '#0d151c' : '#e9eef2' }));
  if (b.t === 'Pick') { const multi = Array.isArray(b.sel); o.multiDisplay = multi ? 'inline' : 'none'; o.items = b.opts.map(x => { const on = multi ? b.sel.includes(x) : x === b.sel;
    return multi ? { label: x, onClick: () => b.fn(x), radius: '10px', bg: on ? 'rgba(233,238,242,0.08)' : 'transparent', ink: '#e9eef2', border: on ? b.accent : 'rgba(233,238,242,0.22)', boxDisplay: 'flex', boxBg: on ? b.accent : 'transparent', boxBorder: on ? b.accent : 'rgba(233,238,242,0.45)', tick: on ? '✓' : '' }
      : { label: x, onClick: () => b.fn(x), radius: '999px', bg: on ? b.accent : OFF, ink: on ? '#0d151c' : '#e9eef2', border: on ? b.accent : 'rgba(233,238,242,0.14)', boxDisplay: 'none', boxBg: 'transparent', boxBorder: 'transparent', tick: '' }; }); }
  if (b.t === 'Num') o.items = b.items.map((x, i) => { const st = x[1]; return { n: st === 'done' ? '✓' : String(i + 1), t: x[0], bg: st === 'done' ? '#7ed6bc' : 'transparent', ring: st === 'done' ? '#7ed6bc' : st === 'now' ? '#d8c88f' : 'rgba(233,238,242,0.3)', ink: st === 'done' ? '#0d151c' : st === 'now' ? '#d8c88f' : MUTE, tc: st === 'next' ? MUTE : '#e9eef2' }; });
  if (b.t === 'Dev') { o.items = b.items.map(d => ({ name: d.name, meta: d.meta, metaInk: /just now/.test(d.meta) ? '#7ed6bc' : MUTE, onForget: d.fn })); o.empty = b.empty; o.emptyDisplay = b.items.length ? 'none' : 'flex'; }
  if (b.t === 'Prog') Object.assign(o, { label: b.label, meta: b.meta || (b.pct >= 100 ? 'Done' : Math.round(b.pct) + '%'), pct: b.pct + '%', ink: b.pct >= 100 ? '#7ed6bc' : C.plex,
    st: b.st || '', stDisplay: b.st ? 'flex' : 'none', stTick: b.stOk ? '✓' : '', stBg: b.stOk ? '#7ed6bc' : 'transparent', stBorder: b.stOk ? '#7ed6bc' : 'rgba(233,238,242,0.45)' });
  if (b.t === 'Cast') Object.assign(o, { device: b.device, text: b.text });
  if (b.t === 'Sum') o.rows = b.rows.map(r => ({ what: r[0], value: r[1], onClick: r[2] || noop, actDisplay: r[2] ? 'block' : 'none' }));
  if (b.t === 'Iv') Object.assign(o, { items: b.items, noneDisplay: b.noneDisplay, addOp: b.addOp, onAdd: b.onAdd });
  if (b.t === 'Clock' || b.t === 'Addr') Object.assign(o, { label: b.label, value: b.value, time: b.time || '' });
  return o;
}
const R = (label, note, on, fn, x) => Object.assign({ k: 'radio', label, note, on, fn }, x);
const T = (label, note, on, fn, x) => Object.assign({ k: 'tog', label, note, on, fn }, x);
const K = (label, note, on, fn) => ({ k: 'chk', label, note, on, fn });
const HB = (label, meta, fn, x) => Object.assign({ k: 'hub', label, meta, fn }, x);
const list = (rows, head) => ({ t: 'List', rows, head });
const note = (tone, title, text) => ({ t: 'Note', tone, title, text });
const field = (label, value, fn, x) => Object.assign({ t: 'Field', label, value, fn }, x);
const status = (state, text, meta) => ({ t: 'Status', state, text, meta });
const P = text => ({ t: 'P', text });
const head = text => ({ t: 'Head', text });
const btn = (label, fn) => ({ t: 'Btn', label, fn });
const pics = (head, items, layout) => ({ t: 'Pics', head, items, layout });
const seg = (head, opts, on, accent, fn) => ({ t: 'Seg', head, opts, on, accent, fn });
const pick = (head, opts, sel, accent, fn) => ({ t: 'Pick', head, opts, sel, accent, fn });
const num = items => ({ t: 'Num', items });
const prog = (label, pct, meta, st, stOk) => ({ t: 'Prog', label, pct, meta, st, stOk });
const sum = (rows, head) => ({ t: 'Sum', rows, head });

const P1N = ['Network', 'Start', 'Name', 'Time', 'Output', 'Screen', 'Review'], P1B = ['Network', 'Start', 'Output', 'Screen', 'Review'];
const P1C = { Network: '#8fc4d8', Start: '#b0bcc4', Name: '#e8a0b4', Time: '#c8a2d8', Output: '#7ed6bc', Screen: '#8fd9a8', Review: '#f2a48f' };
const P1AT = { p1net: 'Network', p1start: 'Start', p1backup: 'Start', p1name: 'Name', p1clock: 'Time', p1output: 'Output', p1screen: 'Screen', p1review: 'Review', p1restore: 'Review' };
const P2M = { listen: ['Listen', C.music], mix: ['Listen', C.music], lyrion: ['Lyrion', C.lyr], folders: ['Folders', C.fold], plexamp: ['Plexamp', C.plex], browse: ['Browse', C.browse], spotify: ['Spotify', C.spo], bluetooth: ['Bluetooth', C.bt], touchpad: ['Touchpad', C.ext], visualiser: ['Visualiser', C.scr], idle: ['When idle', C.idle], wait: ['While it waits', C.idle], standby: ['Standby', C.stby], plexsign: ['Plex sign-in', C.plex], review: ['Review', C.rev] };
const LABEL = { p1welcome: 'Welcome', p1net: 'Network', p1start: 'New player or backup', p1backup: 'Upload a backup', p1name: 'Name', p1clock: 'Clock', p1output: 'Output', p1screen: 'Screen', p1review: 'Check it over', p1join: 'Joining the network', p1restore: 'Check it over', p1restored: 'Restoring', listen: 'How will you listen?', mix: 'My own mix', lyrion: 'Where Lyrion runs', folders: 'Where your music is', plexamp: 'Plexamp', browse: 'Browse', spotify: 'Spotify', bluetooth: 'Bluetooth', touchpad: 'Touchpad', visualiser: 'Visualiser', idle: 'When idle', wait: 'While it waits', standby: 'Standby', plexsign: 'Plex sign-in', review: 'Your setup', done: 'Getting ready', later: 'Kept the defaults' };
const CODES = { p1welcome: '1.0', p1net: '1.1', p1start: '1.2', p1name: '1.3', p1clock: '1.4', p1output: '1.5', p1screen: '1.6', p1review: '1.7', p1join: '1.8', p1backup: '1.2b', p1restore: '1.7b', p1restored: '1.8b', listen: '5A0', mix: '4A1m', lyrion: '5A2', folders: '5A3', plexamp: 'X1', browse: '5A4', spotify: '5A5', bluetooth: '5A6', touchpad: '5A6t', visualiser: '5A7', idle: '5A8', wait: '5A8w', standby: '5A9', plexsign: 'X2', review: '5A10', done: 'End', later: 'End' };
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], HOURS = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0')), QUARTERS = ['00', '15', '30', '45'];
const daysSaid = days => { const on = DAYS.filter(d => days.includes(d)); return on.length === 7 ? 'every day' : on.join() === 'Mon,Tue,Wed,Thu,Fri' ? 'Mon–Fri' : on.join() === 'Sat,Sun' ? 'weekends' : on.join(', '); };
const ivSaid = ivs => !ivs.length ? 'None' : ivs.length > 1 ? ivs.length + ' times' : ivs[0].from + '–' + ivs[0].until + ' · ' + daysSaid(ivs[0].days);
const KNAV = { ext: 'lib', simple: 'simple', off: 'now' };
const NAV = [['ext', 'Extended', 'Full Lyrion navigation, including apps.'], ['simple', 'Simple', 'Library browse, artists, playlists and radio from Lyrion.'], ['off', 'Off', 'Only what’s playing.']];
const SKINS = [['vu', 'VU meters'], ['viz', 'Spectrum'], ['vs', 'VU meters + spectrum'], ['turn', 'Turntables'], ['tape', 'Tapes'], ['all', 'All']];
const ANIM = { turn: ['Animate turntables', 'The record turns and the tonearm follows the track.'], tape: ['Animate tapes', 'The reels turn.'], all: ['Animate turntables and tapes', 'Records and reels turn.'] };
const PLACES = [['folder', 'Music folder', 'On the player, shared on your network.'], ['usb', 'USB drive', 'Plugged into the player.'], ['share', 'Network share', 'A folder on a NAS or a computer.']];
const NETS = [['Studio 5G', 'Secured', 4], ['Studio', 'Secured', 4], ['Guest', 'Open', 2]];
const OUTS = [['HiFiBerry DAC+ HD', ['Recommended', 'ok']], ['Headphones'], ['HDMI 0'], ['HDMI 1']];
const SCRL = { panel: 'Waveshare 10.1″ (B)', other: 'Another screen', headless: 'Headless' };
const BGS = ['Gexis wallpapers', 'Artist pictures', 'Black'], WBGS = ['Gexis wallpapers', 'Black'], STYLES = ['Calm', 'Colourful', 'Psychedelic'];
const PHOTOS = [['dac', '1 DAC', 'https://images.unsplash.com/photo-1707820356995-4b439f50dc29?fm=jpg&q=70&w=1600&auto=format&fit=crop'], ['vu', '2 VU', 'https://images.unsplash.com/photo-1645030327860-bbba1dec8898?fm=jpg&q=70&w=1600&auto=format&fit=crop'], ['deck', '3 Deck', 'https://images.unsplash.com/photo-1624729946372-a655fdb2d8aa?fm=jpg&q=70&w=1600&auto=format&fit=crop'], ['driver', '4 Driver', 'https://images.unsplash.com/photo-1597183739841-5ca26ab0a604?fm=jpg&q=70&w=1600&auto=format&fit=crop'], ['amp', '5 Amp', 'https://images.unsplash.com/photo-1562146388-3b7b2aa615d8?fm=jpg&q=70&w=1600&auto=format&fit=crop']];
const WALLS = { Calm: calmWall, Colourful: colourfulWall, Psychedelic: psychedelicWall };
const PIXA = note('info', '', 'A free Pixabay key unlocks more wallpapers. Add it later in Settings → Display.');
const PHONES = ['George’s iPhone', 'Anna’s Pixel 8', 'Kitchen iPad'];
const FLOWS = [['A', 'Lyrion found', 'A Lyrion server is on the network and is found. Pick My music + streaming, and Lyrion and Folders drop out.'], ['B', 'Plex + streaming', 'No Lyrion on the network. Pick Plex + streaming. Plexamp downloads once you say so, and the Plex sign-in follows straight after.'], ['C', 'Lyrion not found', 'No Lyrion on the network. Pick My music + streaming. Lyrion installs on this player or points at another machine, then Folders.']];
const slug = n => (n || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 63);
const mmss = n => Math.floor(n / 60) + ':' + String(n % 60).padStart(2, '0');
const uniq = a => a.filter((x, i) => a.indexOf(x) === i);
function init(flow, startAt, wide) {
  return { flow, startAt, wide, screen: startAt === 'p2' ? 'listen' : 'p1welcome', ret: null,
    net: 'Studio 5G', pw: 'studio-5g-pass', start: 'new', uploaded: false, name: 'Living Room', fmt: 0, output: 'HiFiBerry DAC+ HD', scr: 'panel',
    lyrState: 'idle', preset: null, presetTouched: false, mix: { lyr: true, plex: false, spo: true, bt: true },
    lyrWhere: 'here', lyrAddrOpen: false, lyrAddr: '', places: { folder: true, usb: false, share: false }, shares: [], shareStep: null, shareSrv: null, shareUser: '', sharePw: '', shareAddr: '', shareAU: '', shareAP: '',
    plexOn: false, plexPct: 0, claimOpened: false, claim: '', plexState: 'code', plexSkipped: false,
    browse: 'ext', spotify: true, bt: true, btPhase: null, btLeft: 180, reqLeft: 30, trusted: [], everPaired: false,
    vizOn: true, vizAfter: '10 min', skin: 'vu', animate: true, rpm: 0,
    idleOn: true, bg: 'Gexis wallpapers', styles: ['Calm', 'Colourful'], wallStyle: 'Calm', listenPic: 'dac', clock: true, weather: false, loc: '',
    waitClock: true, waitBg: 'Gexis wallpapers', standby: false, ivs: [{ from: '23:00', until: '07:00', days: DAYS.slice() }], ivPick: null,
    skipped: {}, inst: 0 };
}

class Component extends DCLogic {

  d(s) {
    const lyr = s.preset === 'mine' || (s.preset === 'custom' && s.mix.lyr), plex = s.preset === 'plex' || (s.preset === 'custom' && s.mix.plex);
    const spo = s.preset !== 'custom' || s.mix.spo, bt = s.preset !== 'custom' || s.mix.bt, headless = s.scr === 'headless';
    return { lyr, plex, spo, bt, headless, wait: !lyr || s.browse === 'off', here: lyr && s.lyrState !== 'found' && s.lyrWhere === 'here',
      marks: [lyr && 'lyr', plex && 'plex', spo && 'spo', bt && 'bt'].filter(Boolean) };
  }
  p1Path(s) { return s.start === 'new' ? ['p1welcome', 'p1net', 'p1start', 'p1name', 'p1clock', 'p1output', 'p1screen', 'p1review', 'p1join'] : ['p1welcome', 'p1net', 'p1start', 'p1backup', 'p1output', 'p1screen', 'p1restore', 'p1restored']; }
  ivBlock(s) {
    const A = '#7ed6bc', ON = { bg: 'rgba(126,214,188,0.16)', border: A, ink: A }, LINE = 'rgba(233,238,242,0.1)', FILL = 'rgba(233,238,242,0.07)';
    const up = (i, f) => this.setState(st => ({ ivs: st.ivs.map((x, k) => k === i ? Object.assign({}, x, f(x)) : x) }));
    const items = s.ivs.map((iv, i) => {
      const pk = s.ivPick && s.ivPick.i === i ? s.ivPick.which : null, [hh, mm] = pk ? iv[pk].split(':') : [];
      const setT = (part, v) => up(i, x => { const [a, b] = x[pk].split(':'); return { [pk]: part === 'h' ? v + ':' + b : a + ':' + v }; });
      const cell = (label, sel, fn) => Object.assign({ label, onTap: fn, weight: sel ? 700 : 400 }, sel ? ON : { bg: FILL, border: LINE, ink: 'rgba(233,238,242,0.82)' });
      return {
        onRemove: () => this.setState(st => { const ivs = st.ivs.filter((_, k) => k !== i); return { ivPick: null, ivs, standby: ivs.length ? st.standby : false }; }),
        times: [['from', 'From'], ['until', 'Until']].map(([w, label]) => ({ label, value: iv[w], border: pk === w ? A : LINE, ink: pk === w ? A : '#e9eef2', onTap: () => this.setState({ ivPick: pk === w ? null : { i, which: w } }) })),
        pickDisplay: pk ? 'flex' : 'none',
        hours: HOURS.map(x => cell(x, x === hh, () => setT('h', x))),
        quarters: QUARTERS.map(x => cell(':' + x, x === mm, () => setT('m', x))),
        days: DAYS.map(d => { const sel = iv.days.includes(d);
          return Object.assign({ label: d, onTap: () => { if (sel && iv.days.length === 1) return; up(i, x => ({ days: sel ? x.days.filter(y => y !== d) : DAYS.filter(y => y === d || x.days.includes(y)) })); } },
            sel ? ON : { bg: FILL, border: LINE, ink: 'rgba(233,238,242,0.72)' }); })
      };
    });
    return { t: 'Iv', items, noneDisplay: items.length ? 'none' : 'block', addOp: items.length >= 6 ? 0.45 : 1,
      onAdd: () => { if (items.length < 6) this.setState(st => ({ ivPick: null, ivs: st.ivs.concat([{ from: '22:00', until: '06:00', days: DAYS.slice() }]) })); } };
  }
  p2Path(s) {
    const d = this.d(s), p = ['listen'];
    if (s.preset === 'custom') p.push('mix');
    if (d.lyr && s.lyrState !== 'found') { p.push('lyrion'); if (s.lyrWhere === 'here') p.push('folders'); }
    if (d.lyr && !d.headless) p.push('browse');
    if (d.plex) { p.push('plexamp'); if (!s.plexSkipped) p.push('plexsign'); }
    if (d.spo) p.push('spotify');
    if (d.bt) p.push('bluetooth');
    if (!d.headless) p.push('touchpad', 'visualiser', ...(d.wait ? ['wait'] : []), 'idle', 'standby');
    return p;
  }
  path() { const s = this.state; return s.screen.startsWith('p1') ? this.p1Path(s) : this.p2Path(s); }

  go(id, ret) { this.setState({ screen: id, ret: ret || null }, () => this.enter(id)); }
  enter(id) {
    const s = this.state;
    if (id === 'bluetooth' && !s.btPhase) this.setState({ btPhase: 'disc', btLeft: 180 });
    if (id === 'p1join' || id === 'p1restored') live.finish1(id);
    if (id === 'done') live.finish();
    if (id === 'later') live.later();
    if (id === 'bluetooth') live.trusted();
    if (id === 'folders') live.loadShares();
  }
  restart(over) {
    clearTimeout(this.t1); clearTimeout(this.t2);
    const s = this.state, n = Object.assign(init(s.flow, s.startAt, s.wide), { listenPic: s.listenPic }, over || {});
    n.screen = n.startAt === 'p2' ? 'listen' : 'p1welcome';
    this.setState(n, () => this.enter(this.state.screen));
  }
  advance(skipped) {
    const s = this.state, d = this.d(s), u = { skipped: Object.assign({}, s.skipped, { [s.screen]: skipped }) };
    this.setState(u);
    if (['p1net', 'p1start', 'p1backup', 'p1name', 'p1clock', 'p1output', 'p1screen'].includes(s.screen)) { const p = this.p1Path(s); live.save(s, s.ret || p[p.indexOf(s.screen) + 1] || s.screen); }
    if (s.ret) {
      if (s.ret === 'review' && ['listen', 'mix', 'lyrion', 'plexamp'].includes(s.screen)) {
        const p = this.p2Path(s), nx = p.slice(p.indexOf(s.screen) + 1).find(x => ['mix', 'lyrion', 'folders', 'browse', 'plexamp', 'plexsign'].includes(x));
        if (nx) return this.go(nx, 'review');
      }
      return this.go(s.ret);
    }
    if (s.screen === 'review') return this.go('done');
    if (['done', 'later', 'p1restored'].includes(s.screen)) return live.close();
    const p = this.path(), i = p.indexOf(s.screen);
    if (i >= 0 && i < p.length - 1) this.go(p[i + 1]);
    else if (i === p.length - 1 && !s.screen.startsWith('p1')) this.go('done');
  }
  next() { this.advance(false); }
  skip() { this.advance(true); }
  back() { const s = this.state; if (s.ret) return this.go(s.ret); const p = this.path(), i = p.indexOf(s.screen); if (i > 0) this.go(p[i - 1]); }
  tick() {
    const s = this.state, u = {};
    if (Object.keys(u).length) this.setState(u);
  }
  phone(s) { return PHONES.find(p => !s.trusted.some(t => t.name === p)) || PHONES[0]; }
  accept() { live.answer(true); }

  sims(s) {
    const L = [], add = (label, fn) => L.push({ label, onClick: fn });
    if (s.screen === 'p1join') add('The player answers', () => this.go('listen'));
    if (s.screen === 'bluetooth' && s.bt && s.btPhase === 'disc') add('A phone asks to pair', () => this.setState({ btPhase: 'request', reqLeft: 30 }));
    if (s.screen === 'bluetooth' && s.btPhase === 'request') add('Let the request run out', () => this.setState({ btPhase: 'disc' }));
    if ((s.screen === 'plexamp' || s.screen === 'plexsign') && s.plexOn && s.plexPct < 100) add('Finish the download', () => this.setState({ plexPct: 100 }));
    if (s.screen === 'plexsign' && s.plexPct >= 100 && s.plexState === 'code') add('The claim code runs out', () => this.setState({ plexState: 'expired', claim: '' }));
    if (s.screen === 'done' && s.inst < 100) add('Finish installing', () => this.setState({ inst: 100 }));
    return L;
  }

  screenDef(s, d) {
    const set = u => this.setState(u), flip = k => () => this.setState(st => ({ [k]: !st[k] }));
    const nm = s.name.trim() || 'the player', sl = slug(s.name) || 'gexis', time = live.time(s.fmt);
    const city = (s.loc.split(',')[0] || '').trim() || s.town || 'Berlin';
    const pv = x => d.headless ? null : Object.assign({ head: nm + '’s screen', time, place: city, player: nm }, x);
    const waitLook = { kind: 'wait', marks: d.marks, clock: s.waitClock, black: s.waitBg === 'Black' };
    const idleLook = s.idleOn ? { kind: 'clock', clock: s.clock, weather: s.weather, black: s.bg === 'Black', bg: s.bg === 'Artist pictures' ? 'artist' : 'wall', wallSrc: WALLS[s.wallStyle] } : d.wait ? waitLook : { kind: KNAV[s.browse] };
    const look = d.lyr ? { kind: KNAV[s.browse] } : waitLook;
    const styles = pick('Wallpaper styles', STYLES, s.styles, C.idle, x => this.setState(st => {
      const on = st.styles.includes(x);
      if (on && st.styles.length === 1) return null;
      const styles = on ? st.styles.filter(y => y !== x) : st.styles.concat([x]), i = STYLES.indexOf(x);
      const ws = !on ? x : st.wallStyle !== x ? st.wallStyle : STYLES.slice(i + 1).concat(STYLES.slice(0, i)).find(y => styles.includes(y)) || x;
      return { styles, wallStyle: ws };
    }));
    const SK = { alt: 'Skip' };
    switch (s.screen) {
      case 'p1welcome': return { hero: true, crumb: 'First-time setup', title: 'Set up gexis', sub: s.overLan ? 'This page talks only to the player, over your network. This part gets the player working; what it plays and shows comes after.' : 'You are connected to the player’s own Wi-Fi. This part gets the player working; what it plays and shows comes after, from your home Wi-Fi.',
        blocks: [note('info', 'About a minute', 'Network, name, time, output and screen. Every answer can be changed later in Settings.'), ...(s.overLan ? [] : [note('warn', 'Keep mobile data off', 'Until this part finishes. With it on, your phone may try to reach this page over mobile data, where the player cannot be found.')])], foot: { next: 'Start' } };
      case 'p1net': { const chosen = s.nets.find(n => n.name === s.net), sec = s.other ? true : chosen ? chosen.secured : false, blocks = [];
        if (s.joinError) blocks.push(note('warn', 'Could not join ' + s.joinError.ssid, (s.joinError.reason || '') + ' Type the password again.'));
        if (s.overLan) blocks.push(note('info', 'Connected by cable', 'The player is on your network already. Choose a Wi-Fi network as well, or go on without one.'));
        if (s.scan === 'scanning' && !s.nets.length) blocks.push(status('spin', 'Looking for networks'));
        else if (!s.nets.length) blocks.push(note('info', 'No networks found', 'Move the player closer to your router and tap Scan again, or choose Other network to type one in.'));
        blocks.push(list([...s.nets.map(n => ({ k: 'net', label: n.name, meta: n.secured ? 'Secured' : 'Open', lvl: n.bars, on: !s.other && s.net === n.name, fn: () => set({ net: n.name, other: false, pw: '', hasPw: false }) })),
          { k: 'net', label: 'Other network', meta: 'Hidden, typed by its name', lvl: 0, on: s.other, fn: () => set({ other: true, net: s.otherName, pw: '' }) }]));
        if (s.other) blocks.push(field('Network name', s.otherName, e => set({ otherName: e.target.value, net: e.target.value })));
        if ((chosen || s.other) && sec) blocks.push(field('Password for ' + (s.net || 'the network'), s.pw, e => set({ pw: e.target.value }), { type: 'password', hint: s.hasPw && !s.pw ? 'Kept from before. Type it again to change it.' : '' }));
        blocks.push(btn('Scan again', () => live.rescan()));
        const ok = s.overLan && !s.net ? true : !!s.net && (!sec || s.pw.length >= 8 || (s.hasPw && !s.pw));
        return { title: 'Join your network', sub: 'The player has one radio, so it can host this page or use your network, never both.', blocks, foot: { nextOff: !ok } }; }
      case 'p1start': return { title: 'New player or backup?', sub: 'A backup brings back everything the player had, so there is less to ask.',
        blocks: [list([R('Set up a new player', 'Four more questions now; the rest from your home Wi-Fi.', s.start === 'new', () => set({ start: 'new' })), R('Restore a backup', 'Upload a backup file from this phone.', s.start === 'backup', () => set({ start: 'backup' }))])] };
      case 'p1backup': { const b = s.backup, blocks = [btn(b ? 'Choose another file' : 'Choose a file', () => live.pickBackup())];
        if (s.uploading !== null) blocks.push(status('spin', 'Uploading and checking', Math.round(s.uploading * 100) + '%'));
        if (s.uploadError) blocks.push(note('warn', '', s.uploadError));
        if (b && s.uploading === null) blocks.push(list([{ k: 'plain', label: (b.settings?.device_name || b.name || 'A gexis backup') + (s.backupMade ? ' · ' + s.backupMade : ''), note: 'Uploaded and checked.' + (b.newer ? ' Made by a newer version of gexis: settings this version does not know wait until it is updated.' : ''), meta: (b.brings || []).join(' · ') || 'Settings only', tag: ['Ready', 'ok'] }]));
        return { title: 'Upload a backup', sub: 'A backup file saved from Settings → System → Back up now, on this phone or in its files.', blocks, foot: { nextOff: !b || s.uploading !== null } }; }
      case 'p1name': return { title: 'Name the player', sub: 'One name for everything. Pick one you will recognise in a list of speakers.',
        blocks: [field('Device name', s.name, e => set({ name: e.target.value }), { ph: 'Living Room', hint: 'Letters, numbers and hyphens become the address; the name keeps its capitals everywhere else.' }), sum([['Address', 'http://' + sl + '.local'], ['In speaker lists', nm]], 'Becomes')], foot: { nextOff: slug(s.name).length < 2 } };
      case 'p1clock': { const z = s.tz, region = z && z.includes('/') ? z.split('/')[0] : '', place = z ? z.split('/').pop().replace(/_/g, ' ') + (region ? ' · ' + region : '') : 'Not detected', blocks = [];
        blocks.push({ t: 'Clock', label: s.tzMode === 'hand' ? 'Chosen by hand' : 'Read from this phone', value: place, time: live.timeIn(z, s.fmt) });
        if (s.tzMode !== 'hand') blocks.push(btn('Choose by hand', () => set({ tzMode: 'hand', tzRegion: region || null })));
        else if (!s.tzRegion) blocks.push(list(live.regions().map(r => HB(r, '', () => set({ tzRegion: r }))), 'Region'));
        else blocks.push(list(live.cities(s.tzRegion).map(c => R(c.split('/').slice(1).join(' / ').replace(/_/g, ' ') || c, '', s.tz === c, () => set({ tz: c }))), s.tzRegion), btn('Another region', () => set({ tzRegion: null })));
        blocks.push(seg('Clock format', ['24 h', '12 h'], s.fmt, P1C.Time, i => set({ fmt: i })));
        return { title: 'Set the clock', sub: 'The idle screen is mostly a clock, so this is worth getting right.', blocks, foot: { nextOff: !s.tz } }; }
      case 'p1output': { const hw = live.hasHw(s.output), short = (s.output || 'This output').split(' — ')[0];
        return { title: 'Choose the output', sub: 'What the player sends audio to, and how its volume is set.', blocks: [list(s.outputs.map(o => R(o, s.outNotes[o] || '', s.output === o, () => live.pickOutput(o), { tag: o === s.recommended ? ['Recommended', 'ok'] : null }))),
        ...(live.noBoard() ? [note('info', 'A DAC board not in the list?', 'A board without its own identity shows up once it is chosen in Settings → Audio → Sound card board, after setup.')] : []),
        ...(s.output ? [list(['Hardware', 'Software', 'Fixed'].map(v => v === 'Hardware' && !hw ? { k: 'ghost', label: v, note: short + ' has no volume control of its own.' } : R(v, s.volNotes[v] || '', s.volume === v, () => set({ volume: v }))), 'Volume')] : []),
        ...(s.output && s.volume === 'Fixed' ? [note('warn', 'Fixed volume', 'Full level from the moment setup finishes, and the panel cannot lower it. Turn your amplifier down first.')] : [])], foot: { nextOff: !s.output || !s.volume } }; }
      case 'p1screen': { const info = s.screenInfo || {}, sug = info.suggested, rows = [], blocks = [];
        if (sug) rows.push(R(sug.maker + ' ' + live.short(sug), sug.width + ' × ' + sug.height + ' · ' + (sug.family === 'bar' ? 'Bar' : 'Standard') + ' layout', s.scr === 'panel', () => set({ scr: 'panel', scPick: sug.label }), { tag: sug.tested ? ['Tested', 'ok'] : null }));
        rows.push(R('Another screen', s.scr === 'other' && s.scPick ? live.labelOf(s.scPick) : 'Pick the model from a list.', s.scr === 'other', () => set({ scr: 'other', scPick: null })));
        rows.push(R('Headless', 'No local screen. The display stays off and nothing is drawn.', s.scr === 'headless', () => set({ scr: 'headless' })));
        if (info.failed) blocks.push(note('warn', 'The list of screens did not arrive', 'Your phone may have dropped off the setup Wi-Fi for a moment.'), btn('Try again', () => live.loadScreens()));
        blocks.push(list(rows));
        if (s.scr === 'other' && !s.scMaker) blocks.push(list(live.makers().map(m => HB(m.name, m.n + (m.n === 1 ? ' model' : ' models'), () => set({ scMaker: m.name }))), 'Makers'));
        else if (s.scr === 'other') blocks.push(list(live.models(s.scMaker).map(m => R(live.short(m), m.width + ' × ' + m.height + ' · ' + (m.family === 'bar' ? 'Bar' : 'Standard') + ' layout', s.scPick === m.label, () => set({ scPick: m.label }), { tag: m.tested ? ['Tested', 'ok'] : null })), s.scMaker), btn('Another maker', () => set({ scMaker: null })));
        if (s.scr === 'headless') blocks.push(note('info', 'Fewer questions later', 'With no screen, part 2 skips how to browse on it, the visualiser, the idle screen and standby.'),
          note('warn', 'Without a screen', 'The setup network always uses the password gexis-setup. If the player starts and cannot reach your Wi-Fi, it opens that network again: join it from your phone, then open 10.42.0.1:8090.'));
        else if (s.scPick && live.asksKeep(s.scPick)) blocks.push(note('info', 'Then, on the player’s screen', 'When setup finishes the player restarts on this screen and asks Keep this screen?. If nobody answers Keep within two minutes, it goes back.'));
        return { title: 'Is this your screen?', sub: sug ? 'What the screen reports matches this model. It sets the layout and the visualiser skins.' : 'Choose the model, or Headless. It sets the layout and the visualiser skins.', blocks, foot: { nextOff: !(s.scr === 'headless' || s.scPick) } }; }
      case 'p1review': { const ch = id => () => this.go(id, 'p1review');
        return { title: 'Check it over', sub: s.net ? 'Finishing moves the player to ' + s.net + '.' : 'Finishing writes all of this to the player.', blocks: [sum([['Network', s.net || 'Cable only', ch('p1net')], ['Name', nm + ' · ' + sl + '.local', ch('p1name')], ['Time', (s.tz || 'Not set') + ' · ' + (s.fmt ? '12 h' : '24 h'), ch('p1clock')], ['Output', s.output ? s.output + ' · ' + s.volume + ' volume' : 'Not set', ch('p1output')], ['Screen', s.scr === 'headless' ? 'Headless' : live.labelOf(s.scPick), ch('p1screen')]]),
          note('info', 'Then, on your home Wi-Fi', 'How you listen and what the screen shows. A few questions, each with a default.'), ...(s.problem ? [note('warn', '', s.problem)] : [])], foot: { next: 'Finish and connect' } }; }
      case 'p1join': return { hero: true, crumb: 'Almost done', title: s.net ? nm + ' is joining ' + s.net : nm + ' is set up',
        blocks: [P(s.net ? 'This page came from the player’s own Wi-Fi, so it stops here. Put this phone back on ' + s.net + ', then open:' : 'Open the player at its address:'), { t: 'Addr', label: 'Open in any browser', value: 'http://' + sl + '.local:8090' }, status('spin', 'Waiting for ' + nm + (s.net ? ' on ' + s.net : '')),
          ...(s.keepQ ? [note('warn', 'Then go to the player’s screen', 'It restarts on the screen you chose and asks whether to keep it. Tap Keep on the screen within two minutes, or it goes back to how it was.')] : []),
          ...(s.scr === 'headless' ? [note('warn', 'Write the address down', 'Nothing is drawn on the device, so this address is the only way in.')] : []),
          note('ok', '', 'When the player answers, this page carries on into making it yours.' + (s.scr === 'headless' ? '' : ' The player’s screen shows a code for it too.'))], foot: { hide: true } };
      case 'p1restore': { const ch = id => () => this.go(id, 'p1restore'), b = (s.backup && s.backup.settings) || {}, en = (s.backup && s.backup.enabled) || [];
        const listens = [b.lms_enabled !== false && 'Lyrion', b.spotify_enabled !== false && 'Spotify', b.bt_enabled !== false && 'Bluetooth'].filter(Boolean).join(' · ') || 'Nothing';
        const installed = [...en.map(live.pluginName), b.visualiser_skins ? 'Visualiser skins' : null].filter(Boolean).join(' · ') || 'Nothing';
        const renamed = !!b.device_name && s.name.trim() !== b.device_name.trim(), left = (s.backup && s.backup.identities) || [];
        return { title: 'Check it over', sub: 'Everything else comes from the backup.', blocks: [sum([['Network', s.net || 'Cable only', ch('p1net')], ['Name', nm + ' · ' + sl + '.local', ch('p1name')], ['Output', s.output ? s.output + ' · ' + s.volume + ' volume' : 'Not set', ch('p1output')], ['Screen', s.scr === 'headless' ? 'Headless' : live.labelOf(s.scPick), ch('p1screen')]]),
          ...(renamed ? [list([K('A second player', left.length ? 'The player the backup came from keeps its own ' + left.join(', ') + '; this one starts without them.' : 'The player the backup came from keeps what is its own.', s.second, () => live.second(!s.second))])] : []),
          sum([['Time', (b.timezone || '—') + ' · ' + (b.clock_format || '24 h')], ['Listens to', listens], ['Installed', installed]], 'From the backup'),
          note('info', 'Nothing more to ask', 'The player restores, joins ' + (s.net || 'your network') + ' and downloads again what the backup had installed.'), ...(s.problem ? [note('warn', '', s.problem)] : [])], foot: { next: 'Restore and connect' } }; }
      case 'p1restored': { const bn = nm, bs = sl;
        return { hero: true, crumb: 'Almost done', title: bn + ' is restoring', blocks: [status('spin', 'Restoring, then joining ' + (s.net || 'your network')), P('Put this phone back on ' + (s.net || 'your network') + '. The player opens at http://' + bs + '.local:8090 when it is back.'),
          ...(s.keepQ ? [note('warn', 'Then go to the player’s screen', 'It restarts on the screen you chose and asks whether to keep it. Tap Keep on the screen within two minutes, or it goes back to how it was.')] : [])], foot: { back: false, next: 'Done' } }; }

      case 'listen': { const st = s.lyrState, found = st === 'found', pk = p => () => set({ preset: p, presetTouched: true });
        const stat = null;
        const lfoot = { back: false, alt: 'Do it later', altFn: () => this.go('later'), nextOff: !s.preset };
          const mine = R('My music + streaming', '', s.preset === 'mine', pk('mine'), Object.assign({ srcs: ['lyr', 'spo', 'bt'] }, found ? { foot: 'Lyrion found on ' + s.net, footMeta: s.lyrMeta } : st === 'none' ? { foot: 'No Lyrion found on ' + s.net, footMeta: 'Set it up on the next screen', footDot: 'rgba(233,238,242,0.4)' } : {}));
          const rest = [R('Plex + streaming', '', s.preset === 'plex', pk('plex'), { srcs: ['plex', 'spo', 'bt'] }),
            R('Streaming only', '', s.preset === 'stream', pk('stream'), { srcs: ['spo', 'bt'] })];
          const own = R('My own mix', 'Choose from any of these on the next screen.', s.preset === 'custom', pk('custom'), { srcs: ['lyr', 'plex', 'spo', 'bt'] });
          const lpv = s.wide ? { kind: 'flow', head: '' } : null;
          return { title: 'How will you listen?', sub: 'Pick the closest. Change anything after.', pv: lpv, foot: lfoot, blocks: [...(stat ? [stat] : []), list([mine, ...rest]), list([own], 'Or mix your own')] };
      }
      case 'mix': { const m = k => () => this.setState(st => ({ mix: Object.assign({}, st.mix, { [k]: !st.mix[k] }) }));
        return { title: 'My own mix', blocks: [list([T('Lyrion', 'Browse your files on the screen.', s.mix.lyr, m('lyr'), { icon: 'lyr' }), T('Plexamp', 'Your Plex library, from its app.', s.mix.plex, m('plex'), { icon: 'plex' }), { k: 'ghost', label: 'Library service', note: 'The next one lands here.', tag: 'Next phase' }], 'Your own music'),
          list([T('Spotify', '', s.mix.spo, m('spo'), { icon: 'spo' }), T('Bluetooth', '', s.mix.bt, m('bt'), { icon: 'bt' })], 'Streaming')] }; }
      case 'lyrion': { const here = s.lyrWhere === 'here';
        const nf = Object.assign(status('none', 'No Lyrion found on ' + s.net), s.lyrAddrOpen ? { field: { label: 'Server address', value: s.lyrAddr, fn: e => set({ lyrAddr: e.target.value }), ph: '192.0.2.31:9000', hint: nm + ' checks it before going on.' } } : { act: 'Add its address', actFn: () => set({ lyrAddrOpen: true }) });
        return { title: 'Where should Lyrion run?', blocks: [nf, { t: 'Where', sel: s.lyrWhere, fn: w => set({ lyrWhere: w }) },
          here ? { t: 'Split', lhead: nm + ' does', left: ['Installs Lyrion', 'Adds your folders', 'Runs the first scan'], rhead: 'Later, in Lyrion', right: ['Rescan after adding music', 'Everything else'] }
            : { t: 'Split', lhead: nm + ' does', left: ['Finds it and plays from it'], rhead: 'You, on that machine', right: ['Install Lyrion', 'Add your music', 'Run the scans'] },
          ...(here ? [] : [{ t: 'Addr', label: 'Get Lyrion at', value: 'lyrion.org' }])], foot: SK }; }
      case 'folders': { const tg = k => () => this.setState(st => ({ places: Object.assign({}, st.places, { [k]: !st.places[k] }) })), extra = [];
        if (s.places.share) { const ss = s.shareStep, srv = s.shareSrv, addShare = (address, user, password) => live.addShare(address, user, password);
          const scan = () => live.scanShares();
          if (s.shares.length && !ss) extra.push(list(s.shares.map(a => ({ k: 'plain', label: a.name, note: a.where, tag: ['Added', 'ok'] })), 'Network shares'));
          if (!ss) extra.push(btn(s.shares.length ? 'Add another share' : 'Add a network share', scan));
          else if (ss === 'scan') extra.push(status('spin', 'Looking for shares', 'Servers that announce themselves answer within a few seconds.'));
          else if (ss === 'list') extra.push(list(s.shareServers.map(v => HB(v.name, v.server?.host || '', () => live.showShares(v), { icon: 'fold' })), 'Network shares'),
            P('Not in the list? Some servers do not announce themselves - add the share by its address.'), btn('Add by address', () => set({ shareStep: 'addr' })), btn('Cancel', () => set({ shareStep: null })));
          else if (ss === 'login') extra.push(note('info', 'Sign in to ' + srv, 'It shows its shares only to a user it knows. The same user and password are used to mount the one you choose.'),
            field('User', s.shareUser, e => set({ shareUser: e.target.value }), { ph: 'george' }), field('Password', s.sharePw, e => set({ sharePw: e.target.value }), { type: 'password' }),
            btn('Show shares', () => live.showShares(s.shareSrvItem, s.shareUser.trim(), s.sharePw)), btn('Back', () => set({ shareStep: 'list' })));
          else if (ss === 'browse') extra.push(list(s.shareFound.map(f => HB(f.name, f.address, () => addShare(f.address, s.shareUser.trim() || null, s.sharePw || null), { icon: 'fold' })), 'Shares on ' + srv),
            P('Tap one to add it.'), btn('Back', () => set({ shareStep: 'list' })));
          else if (ss === 'addr') extra.push(note('info', 'Add a share', 'A folder on a NAS or a computer. SMB needs a user and password; NFS needs only the address.'),
            field('Address', s.shareAddr, e => set({ shareAddr: e.target.value }), { ph: '//nas/music or nas:/music' }), field('User (SMB)', s.shareAU, e => set({ shareAU: e.target.value })), field('Password (SMB)', s.shareAP, e => set({ shareAP: e.target.value }), { type: 'password' }),
            btn('Add', () => { if (s.shareAddr.trim()) addShare(s.shareAddr.trim(), s.shareAU.trim() || null, s.shareAP || null); }), btn('Back', () => set({ shareStep: 'list' })));
          if (s.shareError) extra.push(note('warn', '', s.shareError));
        }
        return { title: 'Where is your music?', sub: 'Pick all that apply.', blocks: [list(PLACES.map(p => K(p[1], p[2], p[0] === 'share' ? s.places.share : true, p[0] === 'share' ? tg(p[0]) : undefined)), 'Lyrion reads'), ...extra, P('These become Lyrion’s music folders when it installs.')], foot: SK }; }
      case 'plexamp': {
        const sub = 'Your Plex library, played on ' + nm + '.';
        if (s.plexOn) return { title: 'Plexamp', sub, blocks: [prog(s.plexPct >= 100 ? 'Plexamp is in' : 'Downloading Plexamp', s.plexPct)] };
        return { title: 'Plexamp', sub, blocks: [list([{ k: 'plain', label: 'Plexamp', note: 'From Plex', icon: 'plex' }]), num([['Download Plexamp', 'next'], ['Sign in to Plex with a claim code', 'next']]), P('Skip, and add Plexamp later from Settings → Plugins.')],
          foot: { alt: 'Skip', altFn: () => this.setState({ plexSkipped: true, plexState: 'later' }, () => this.skip()), next: 'Download', nextFn: () => this.setState({ plexOn: true, plexSkipped: false }, () => { live.downloadPlex(); this.next(); }), keep: true } };
      }
      case 'browse': return { title: 'Browse on the screen', sub: 'A Lyrion app on your phone works with any of these.', pv: pv({ kind: KNAV[s.browse] }), blocks: [list(NAV.map(n => R(n[1], n[2], s.browse === n[0], () => set({ browse: n[0] }))))], foot: SK };
      case 'spotify': return { title: 'Spotify', sub: 'Built in. ' + nm + ' appears in the Spotify app on your phone.', blocks: [list([T('Spotify Connect', '', s.spotify, flip('spotify'), { icon: 'spo' })]), ...(s.spotify ? [{ t: 'Cast', device: nm, text: 'Tap the devices icon, then ' + nm + '.' }] : [])], foot: SK };
      case 'bluetooth': {
        const ph = s.pairDevice || 'A phone', sub = 'Any phone can play to ' + nm + ' over Bluetooth. Pair one now, or later from Settings.';
        const en = list([T('Enabled', '', s.bt, () => this.setState(st => ({ bt: !st.bt, btPhase: !st.bt ? 'disc' : st.btPhase, btLeft: !st.bt ? 180 : st.btLeft })), { icon: 'bt' })]);
        const devs = s.everPaired ? [{ t: 'Dev', items: s.trusted.map(t => ({ name: t.name, meta: t.meta, fn: () => live.forget(t) })), empty: 'No phones paired yet.' }] : [];
        if (!s.bt) return { title: 'Bluetooth', sub, blocks: [en, note('info', '', 'Phones can’t find ' + nm + '. Turn it on any time in Settings → Bluetooth.')], foot: SK };
        if (s.btPhase === 'request') return { title: 'Bluetooth', sub, blocks: [{ t: 'Code', label: ph + ' wants to pair', code: s.pairCode, text: 'Check it matches your phone, then accept.' }],
          foot: { alt: 'Decline', altFn: () => live.answer(false), next: 'Accept', nextFn: () => this.accept(), keep: true } };
        if (s.btPhase === 'paired') { const last = s.trusted[s.trusted.length - 1];
          return { title: 'Bluetooth', sub, blocks: [en, ...(last ? [status('ok', last.name + ' is paired')] : []), ...devs, btn('Pair another phone', () => set({ btPhase: 'disc', btLeft: 180 }))] }; }
        return { title: 'Bluetooth', sub, blocks: [en, status('spin', 'Waiting for a phone', 'Tap ' + nm + ' in its Bluetooth list'), ...devs], foot: SK };
      }
      case 'touchpad': return { title: 'Touchpad on your phone', sub: 'In the phone’s volume sheet: move a pointer on ' + nm + '’s screen, tap, type, scroll with two fingers and pinch to zoom.', pv: pv({ kind: 'lib', pointer: s.touchpad }),
        blocks: [list([T('Phone touchpad', '', s.touchpad, flip('touchpad'))]), note('info', 'More in Settings', s.touchpad ? 'Display → Touchpad: Pointer speed, how far the pointer moves for a finger’s movement, and Pointer style, a dot or an arrow.' : 'Display → Touchpad turns it on again, with its pointer speed and style.')], foot: SK };
      case 'visualiser': { const k = s.skin, a = ANIM[k], rpm = s.rpm ? 45 : 33;
        return { title: 'While music plays', sub: 'What the screen shows with the music.', pv: pv(s.vizOn ? { kind: k, rpm, animate: s.animate } : { kind: d.lyr ? KNAV[s.browse] : 'now' }),
          blocks: [list([T('Visualiser', 'Takes the screen while music plays.', s.vizOn, flip('vizOn'), { icon: 'viz' })]), ...(s.vizOn ? [
            pick('Starts after', ['2 min', '10 min', '30 min'], s.vizAfter, C.scr, x => set({ vizAfter: x })),
            pics('Skins', SKINS.map(x => ({ kind: x[0], label: x[1], on: k === x[0], rpm, fn: () => set({ skin: x[0] }) })), 'grid3'),
            ...(a ? [list([T(a[0], a[1], s.animate, flip('animate'))])] : []),
            ...((k === 'turn' || k === 'all') && s.animate ? [seg('Record speed', ['33 rpm', '45 rpm'], s.rpm, C.scr, i => set({ rpm: i }))] : []),
            note('info', '', 'How each skin moves and reacts to the music is in Settings → Display → Visualiser.')] : [])], foot: SK }; }
      case 'idle': { const gx = s.bg === 'Gexis wallpapers';
        return { title: 'When nothing plays', sub: 'What the screen shows after a while with no music and no touch.', pv: pv(idleLook),
          blocks: [list([T('Idle screen', 'After 5 min with no music.', s.idleOn, flip('idleOn'), { icon: 'clk' })]), ...(s.idleOn ? [
            pick('Background', BGS, s.bg, C.idle, x => set({ bg: x })), ...(gx ? [styles, PIXA] : []),
            list([T('Clock', '', s.clock, flip('clock')), T('Weather', '', s.weather, flip('weather'))]),
            ...(s.weather ? [field('Weather location', s.loc, e => set({ loc: e.target.value }), { ph: 'e.g. Lisbon, Portugal' })] : [])] : [])], foot: Object.assign({}, SK, { nextOff: s.idleOn && s.weather && !s.loc.trim() }) }; }
      case 'wait': return { title: 'While it waits', sub: 'The screen shows the sources over a picture until something plays.', pv: pv(waitLook),
        blocks: [list([T('Clock', 'Time, date and the player’s name.', s.waitClock, flip('waitClock'), { icon: 'clk' })]), pick('Background', WBGS, s.waitBg, C.idle, x => set({ waitBg: x })), ...(s.waitBg === 'Gexis wallpapers' ? [styles, PIXA] : [])], foot: SK };
      case 'standby': return { title: 'Off at night?', sub: 'The screen turns off at set hours when nothing plays.', pv: pv(s.standby ? { kind: 'off' } : idleLook),
        blocks: [list([T('Night standby', 'The screen turns off.', s.standby, () => this.setState(st => ({ standby: !st.standby, ivPick: null, ivs: !st.standby && !st.ivs.length ? [{ from: '22:00', until: '06:00', days: DAYS.slice() }] : st.ivs })), { icon: 'stby' })]), ...(s.standby ? [this.ivBlock(s)] : [])], foot: SK };
      case 'plexsign': {
        const later = () => this.setState({ plexState: 'later' }, () => this.skip());
        const done = s.plexPct >= 100, dl = prog(done ? 'Plexamp is installed' : 'Downloading Plexamp', s.plexPct), sub = 'Get a claim code from plex.tv while Plexamp downloads, then paste it here.';
        const skipP = P('Or skip, and sign in later from Settings → Plugins → Plexamp.' + (done ? '' : ' The download carries on.'));
        const open = btn('Open plex.tv/claim', () => { window.open('https://plex.tv/claim', '_blank', 'noopener'); set({ claimOpened: true, plexState: s.plexState === 'expired' ? 'code' : s.plexState }); });
        if (s.plexState === 'ok') return { title: 'Sign in to Plex', sub, blocks: [dl, open, note('info', '', 'Paste the claim code here within four minutes.'), field('Claim code', s.claim, noop, { ro: true }), status('ok', nm + ' is on your Plex account', 'Plexamp signed in'), P('Open Plexamp on your phone and pick ' + nm + ' as the player.')] };
        if (!done) return { title: 'Sign in to Plex', sub, blocks: [dl, open, note('info', '', 'A claim code lasts four minutes. Paste it here once Plexamp is installed.'), field('Claim code', '', noop, { ph: 'Opens once Plexamp is installed', ro: true }), skipP], foot: { alt: 'Skip', altFn: later, next: 'Claim', nextOff: true, keep: true } };
        const code = field('Claim code', s.claim, e => set({ claim: e.target.value }), { ph: 'claim-…' });
        const blocks = s.plexState === 'expired' ? [dl, note('warn', 'That code has run out', 'Claim codes last four minutes. Get a new one and paste it straight away.'), open, code]
          : [dl, open, note('info', '', 'Paste the claim code here within four minutes.'), code, skipP];
        return { title: 'Sign in to Plex', sub, blocks, foot: { alt: 'Skip', altFn: later, next: 'Claim', nextFn: () => { if (s.claim.trim()) live.claim(s.claim.trim()); }, nextOff: !s.claim.trim(), keep: true } };
      }
      case 'review': {
        const sk = id => s.skipped[id] ? ['Skipped', 'plain'] : null, op = id => () => this.go(id, 'review'), rows = [];
        const music = s.preset === 'mine' ? (s.lyrState === 'found' ? 'Lyrion · found on ' + s.net : s.lyrWhere === 'here' ? 'Lyrion, on this player' : 'Lyrion, on another machine') : s.preset === 'stream' ? 'Streaming only' : s.preset === 'plex' ? 'Plexamp' : [d.lyr && 'Lyrion', d.plex && 'Plexamp'].filter(Boolean).join(' · ') || 'No library';
        rows.push(HB('Music', music, op('listen'), { icon: d.lyr ? 'lyr' : d.plex ? 'plex' : 'lib' }));
        if (d.here) rows.push(HB('Folders', PLACES.filter(p => s.places[p[0]]).map(p => p[1]).join(' · ') || 'None yet', op('folders'), { icon: 'fold', tag: sk('folders') }));
        if (d.lyr && !d.headless) rows.push(HB('Browse', NAV.find(n => n[0] === s.browse)[1], op('browse'), { icon: 'browse', tag: sk('browse') }));
        if (d.plex) { const px = !s.plexOn ? ['Not installed · later, from Settings', ['Skipped', 'plain']] : s.plexState === 'ok' ? ['Signed in', ['Signed in', 'ok']] : s.plexState === 'later' ? [(s.plexPct < 100 ? 'Downloading' : 'Installed') + ' · sign in later', ['Later', 'warn']] : ['Not signed in', null];
          rows.push(HB('Plex', px[0], op(s.plexOn ? 'plexsign' : 'plexamp'), { icon: 'plex', tag: px[1] })); }
        if (d.spo) rows.push(HB('Spotify', s.spotify ? 'On' : 'Off', op('spotify'), { icon: 'spo', tag: sk('spotify') }));
        if (d.bt) rows.push(HB('Bluetooth', !s.bt ? 'Off' : s.trusted.length ? s.trusted.map(t => t.name).join(' · ') : 'On · no phone yet', op('bluetooth'), { icon: 'bt', tag: s.trusted.length && s.bt ? ['Paired', 'ok'] : sk('bluetooth') }));
        if (!d.headless) {
          rows.push(HB('Visualiser', s.vizOn ? SKINS.find(x => x[0] === s.skin)[1] : 'Off', op('visualiser'), { icon: 'viz', tag: sk('visualiser') }));
          if (d.wait) rows.push(HB('While it waits', [s.waitBg, s.waitClock && 'Clock'].filter(Boolean).join(' · '), op('wait'), { icon: 'clk', tag: sk('wait') }));
          rows.push(HB('When idle', s.idleOn ? [s.bg, s.clock && 'Clock', s.weather && 'Weather'].filter(Boolean).join(' · ') : 'Off', op('idle'), { icon: 'clk', tag: sk('idle') }));
          rows.push(HB('Standby', s.standby ? ivSaid(s.ivs) : 'Off', op('standby'), { icon: 'stby', tag: sk('standby') }));
        }
        return { title: 'Your setup', sub: 'Tap a row to change it.', pv: pv(Object.assign({}, look, { head: nm + '’s screen' })), blocks: [list(rows), ...(d.here ? [P('Lyrion installs and scans your folders when you finish.')] : [])], foot: { next: 'Finish' } };
      }
      case 'done': { const items = [];
        if (s.finishError) items.push(note('warn', 'Not saved yet', s.finishError));
        if (d.here) { const lp = live.pct(live.component('lyrion-server.enabled', 'lyrion')), ld = lp >= 100;
          items.push(head('Lyrion'), prog(ld ? 'Installed' : 'Installing', lp, null, ld ? 'Folders added, scan started' : '', true));
          if (ld) items.push(note('info', '', 'A large library can take hours to scan. Music shows up as Lyrion finds it.')); }
        if (d.plex && s.plexOn) { const pd = s.plexPct >= 100, ok = s.plexState === 'ok';
          items.push(head('Plexamp'), prog(pd ? 'Installed' : 'Downloading', s.plexPct, null, pd ? (ok ? 'Signed in to Plex' : 'Not signed in yet') : '', ok));
          if (pd) items.push(note('info', '', ok ? 'Your Plex library plays from the Plexamp app.' : 'Sign in from Settings → Plexamp when you’re ready.')); }
        if (!d.headless && s.vizOn) { const vp = live.pct('skins');
          items.push(head('Visualiser'), prog(vp >= 100 ? 'Installed' : 'Installing skins', vp, null, vp >= 100 ? 'Skins ready' : '', true));
          if (vp >= 100) items.push(note('info', '', 'The visualiser starts after ' + s.vizAfter + ' of music.')); }
        if (live.failed()) items.push(note('warn', 'Something did not finish', 'Try it again from Settings → Plugins. Everything else is set.'));
        const waiting = !s.finished || (d.here && live.pct(live.component('lyrion-server.enabled', 'lyrion')) < 100) || (d.plex && s.plexOn && s.plexPct < 100) || (!d.headless && s.vizOn && live.pct('skins') < 100);
        const state = s.finishError ? 'busy' : live.failed() ? 'warn' : waiting ? 'busy' : 'done';
        return { hero: true, crumb: 'Make it yours', title: state === 'done' ? nm + ' is ready' : state === 'warn' ? nm + ' is nearly ready' : 'Getting ' + nm + ' ready', blocks: [{ t: 'Party', marks: d.marks, status: state }, ...items, { t: 'Rule' }, note('ok', '', 'Everything you set up here can be run again or changed in Settings → System → Personalise.')], foot: s.finishError ? { back: false, next: 'Try again', nextFn: () => live.finish() } : { back: false, next: 'Close' } }; }
      case 'later': return { hero: true, crumb: 'Make it yours', title: 'Kept the defaults', blocks: [P(s.first ? 'Spotify and Bluetooth are on, and nothing else is installed.' : 'Nothing was changed.'), note('ok', '', 'All of it is in Settings → System → Personalise.')], foot: { back: false, next: 'Close' } };
    }
    return { title: '', blocks: [] };
  }

  renderVals() {
    const s = this.state, d = this.d(s), sc = this.screenDef(s, d), p1 = s.screen.startsWith('p1'), W = s.wide;
    let rail = null, at = -1, accent = '#7ed6bc', stepName = '';
    if (p1 && P1AT[s.screen]) { rail = s.start === 'new' ? P1N : P1B; stepName = P1AT[s.screen]; at = rail.indexOf(stepName); accent = P1C[stepName]; }
    else if (P2M[s.screen]) { rail = uniq(this.p2Path(s).map(x => P2M[x][0])); stepName = P2M[s.screen][0]; at = rail.indexOf(stepName); accent = P2M[s.screen][1]; }
    const crumb = sc.crumb || (s.ret === 'review' ? 'Review · ' + stepName : s.ret ? 'Check it over · ' + stepName : rail && at >= 0 ? 'Step ' + (at + 1) + ' of ' + rail.length : 'Make it yours');
    const f = sc.foot || {}, ret = !!s.ret, pathIdx = this.path().indexOf(s.screen);
    const foot = {
      display: f.hide ? 'none' : 'flex', onBack: () => this.back(),
      backDisplay: ret || (f.back !== false && pathIdx > 0) ? 'block' : 'none',
      alt: f.alt || '', altDisplay: f.alt && (!ret || f.keep) ? 'block' : 'none', onAlt: f.altFn || (() => this.skip()),
      next: ret && !f.keep ? 'Save' : f.next || (!p1 && !ret && pathIdx >= 0 && pathIdx === this.path().length - 1 ? 'Finish' : 'Next'), nextOp: f.nextOff ? 0.4 : 1, nextCursor: f.nextOff ? 'default' : 'pointer',
      onNext: f.nextOff ? noop : f.nextFn || (() => this.next())
    };
    const pv = sc.pv || null;
    const looks = d.lyr ? { kind: KNAV[s.browse] } : { kind: 'wait', marks: d.marks, clock: s.waitClock, black: s.waitBg === 'Black' };
    const sidePv = pv || (p1 ? { kind: 'setup', head: 'The player’s screen' } : d.headless ? null : Object.assign({ head: (s.name.trim() || 'The player') + '’s screen', time: s.fmt ? '9:04 pm' : '21:04', player: s.name }, looks));
    const nav = id => {
      const on = id === s.screen, c = P1AT[id] ? P1C[P1AT[id]] : P2M[id] ? P2M[id][1] : '#7ed6bc';
      return { label: LABEL[id], code: CODES[id] || '', c, onClick: () => this.go(id), bg: on ? 'rgba(233,238,242,0.09)' : 'transparent', ink: on ? '#e9eef2' : 'rgba(233,238,242,0.66)', fw: on ? 700 : 500 };
    };
    const p2 = s.start === 'new' ? this.p2Path(s).concat(['done']) : [];
    let code = CODES[s.screen] || '';
    if (s.screen === 'listen' && s.lyrState === 'found') code = '5A1';
    if (s.screen === 'bluetooth') code = { request: 'P2', paired: 'P3', timeout: 'P4' }[s.btPhase] || '5A6';
    if (s.screen === 'visualiser') code = { turn: '5A7t', tape: '5A7c' }[s.skin] || '5A7';
    if (s.screen === 'plexsign') code = s.plexPct < 100 ? 'X2–' : s.plexState === 'ok' ? 'X4' : s.plexState === 'expired' ? 'X3' : 'X2';
    const sims = this.sims(s);
    const optOf = (opts, cur, fn) => opts.map(o => ({ label: o[1], onClick: () => fn(o[0]), bg: cur === o[0] ? '#e9eef2' : 'transparent', ink: cur === o[0] ? '#0d151c' : '#e9eef2' }));
    return {
      flows: FLOWS.map(x => { const on = s.flow === x[0]; return { id: x[0], title: x[1], text: x[2], onClick: () => this.restart({ flow: x[0] }), bg: on ? 'rgba(242,164,143,0.08)' : OFF, border: on ? 'rgba(242,164,143,0.55)' : OFFB, badgeBg: on ? '#f2a48f' : 'rgba(233,238,242,0.1)', badgeInk: on ? '#0d151c' : '#e9eef2' }; }),
      startOpts: optOf([['p1', 'Part 1'], ['p2', 'Part 2']], s.startAt, v => this.restart({ startAt: v })),
      layoutOpts: optOf([[false, 'Phone'], [true, 'Wide']], s.wide, v => this.setState({ wide: v })),
      listenPvOpts: optOf(PHOTOS.map(x => [x[0], x[1]]), s.listenPic, v => this.setState({ listenPic: v })),
      showListenPvOpts: false,
      sims, hasSims: sims.length > 0, onRestart: () => this.restart(),
      navGroups: [{ title: 'Part 1 · over gexis-setup', items: this.p1Path(s).map(nav) }].concat(p2.length ? [{ title: 'Part 2 · on ' + s.net, items: p2.map(nav) }] : []),
      code, navLabel: LABEL[s.screen] || '',
      fw: '100%', fh: '100%', rad: '0px', headPad: W ? '30px 36px 0' : '28px 20px 0', bodyPad: W ? '24px 36px 28px' : '24px 20px 22px', colGap: W ? '48px' : '0px', leftDisplay: W ? 'flex' : 'none',
      crumb, accent, prog: rail && at >= 0 ? Math.round((at + 0.65) / rail.length * 100) + '%' : '0%', progDisplay: rail && at >= 0 ? 'block' : 'none',
      eyebrowDisplay: stepName ? 'flex' : 'none', stepName, title: sc.title, tSize: sc.hero ? '30px' : '26px', sub: sc.sub || '', subDisplay: sc.sub ? 'block' : 'none',
      pv: pv || {}, hasInlinePv: !W && !!pv, sidePv: sidePv || {}, hasSidePv: W && !!sidePv, noSidePv: W && !sidePv,
      blocks: (sc.blocks || []).map(block), foot, scrollRef: this.scrollRef
    };
  }
}

  // ===== The player =====

  //: Part 2's own state, with what the prototype simulated filled in by
  //: the player: its name, clock, network, the Lyrion search, Plexamp's
  //: download, a phone asking to pair, the network shares, the downloads.
  let st = $state(Object.assign(init('A', mode === 'p1' ? 'p1' : 'p2', false), {
    first: true, nameSaved: false, second: true, touchpad: true,
    volume: 'Hardware', volHw: {}, volNotes: {}, town: '', net: 'your network', lyrMeta: '', lyrServer: null, pairDevice: '', pairCode: '',
    shareServers: [], shareFound: [], shareSrvItem: null, shareError: null, finishError: null, finished: null,
    plugins: [], tick: 0, ready: false,
    // Part 1's own.
    nets: [], scan: 'scanning', other: false, otherName: '', hasPw: false, joinError: null, overLan: false,
    backup: null, backupMade: '', uploading: null, uploadError: null, tz: null, tzMode: 'auto', tzRegion: null, zones: [],
    outputs: [], outNotes: {}, recommended: null, screenInfo: null, scMaker: null, scPick: null, keepQ: false, problem: null, offered: []
  }));
  const comp = new Component();
  comp.state = st;
  let refs = $state({});

  const pctOf = (item) => !item ? 0 : item.state === 'done' ? 100
    : item.total ? Math.min(99, Math.round(((item.received ?? 0) / item.total) * 100))
      : item.share != null ? Math.min(99, Math.round(item.share * 100)) : 2;

  //: The downloads the settling record has listed since Finish.
  const seenIds = new SvelteSet();
  let waitedOut = $state(false);
  $effect(() => {
    for (const i of $settling?.items ?? []) if (!seenIds.has(i.id)) seenIds.add(i.id);
  });

  //: What the design's logic calls on the player.
  const live = {
    time(fmt) {
      st.tick;
      const d = new Date(), h = d.getHours(), m = String(d.getMinutes()).padStart(2, '0');
      return fmt ? `${h % 12 || 12}:${m} ${h < 12 ? 'am' : 'pm'}` : `${String(h).padStart(2, '0')}:${m}`;
    },
    component(row, fallback) { return st.plugins.find((p) => p.row === row)?.component ?? fallback; },
    pct(id) {
      const item = $settling?.items?.find((i) => i.id === id);
      if (item) return pctOf(item);
      //: **Waiting until the player has listed it**: Finish answers with
      //: what it will follow, and the settling record that lists it comes
      //: a moment later over the state socket. Not yet listed is not yet
      //: done - else the page says ready, then busy. Seen and gone is done;
      //: never listed within 30 s counts as done too, so a lost update
      //: cannot hold the page.
      if (st.finished?.waiting?.includes(id) && !seenIds.has(id) && !waitedOut) return 0;
      // Not followed: nothing to download (already in), or settled and gone.
      return st.finished ? 100 : 0;
    },
    failed() { return !!$settling?.items?.some((i) => i.state === 'failed'); },
    async finish() {
      st.finishError = null;
      try {
        const r = await fetch('/personalise/finish', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ settings: answersAsSettings(st) })
        });
        const body = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(body.error ?? `HTTP ${r.status}`);
        st.finished = body;
        setTimeout(() => (waitedOut = true), 30000);
      } catch (err) {
        console.warn('personalise: finish failed:', err?.message);
        st.finishError = "The player didn't take the answers. Check this phone is on the player's network, then try again.";
      }
    },
    later() { personaliseLater().catch(() => {}); },
    async trusted() {
      const got = await listItems('bt_trusted');
      st.trusted = (got.items ?? []).map((i) => ({ name: i.name, meta: i.meta || 'Paired', address: i.address }));
      st.everPaired = st.trusted.length > 0;
    },
    async forget(t) {
      await listAction('bt_trusted', { name: t.address ?? t.name, action: 'forget' });
      live.trusted();
    },
    answer(accept) {
      answerPairing(accept).catch(() => {});
      if (!accept) st.btPhase = 'disc';
    },
    async loadShares() {
      const got = await listItems('lyrion-server.shares');
      const items = got.items ?? [];
      st.shares = items.filter((i) => !i.server).map((i) => ({ name: i.name, where: i.meta || '' }));
      st.shareServers = items.filter((i) => i.server);
    },
    async scanShares() {
      st.shareStep = 'scan';
      st.shareError = null;
      await live.loadShares();
      if (st.shareStep === 'scan') st.shareStep = 'list';
    },
    async showShares(item, user = null, password = null) {
      st.shareError = null;
      st.shareSrv = item.name;
      st.shareSrvItem = item;
      const r = await listAction('lyrion-server.shares', { name: item.name, action: 'browse', server: item.server, user, password });
      if (r.login) {
        st.shareStep = 'login';
        if (user) st.shareError = 'That user or password was not accepted.';
        return;
      }
      if (!r.ok) {
        st.shareError = r.error ?? 'Could not read its shares.';
        return;
      }
      st.shareFound = r.items ?? [];
      st.shareStep = 'browse';
    },
    async addShare(address, user, password) {
      st.shareError = null;
      const r = await listAction('lyrion-server.shares', { name: address, action: 'add', user: user ?? (address.startsWith('//') ? 'guest' : null), password: password ?? null });
      if (!r.ok) {
        st.shareError = r.error ?? 'Could not add it. Check the address and try again.';
        return;
      }
      Object.assign(st, { shareStep: null, shareAddr: '', shareAU: '', shareAP: '', shareUser: '', sharePw: '' });
      live.loadShares();
    },
    async downloadPlex() {
      const r = await writeSetting('plexamp.enabled', true);
      if (!r.ok) st.plexOn = false;
    },
    async claim(code) {
      const r = await writeSetting('plexamp.claim_token', code);
      if (r.ok) st.plexState = 'ok';
      else Object.assign(st, { plexState: 'expired', claim: '' });
    },

    // ----- Part 1 -----------------------------------------------------------
    async rescan() {
      st.scan = 'scanning';
      try { st.nets = (await json('/setup/networks')).items ?? []; } catch { st.nets = []; }
      st.scan = 'done';
    },
    async loadScreens() {
      try { st.screenInfo = await json('/setup/screen'); } catch { st.screenInfo = { suggested: null, models: [], failed: true }; }
    },
    timeIn(zone, fmt) {
      st.tick;
      try {
        return new Intl.DateTimeFormat('en-GB', { hour: fmt ? 'numeric' : '2-digit', minute: '2-digit', hour12: !!fmt, timeZone: zone || undefined }).format(new Date()).replace(/\s?([AP]M)$/i, (m, x) => ' ' + x.toLowerCase());
      } catch { return '--:--'; }
    },
    regions() { return [...new Set(st.zones.map((z) => (z.includes('/') ? z.split('/')[0] : z)))]; },
    cities(region) { return st.zones.filter((z) => (z.includes('/') ? z.split('/')[0] : z) === region); },
    noBoard() {
      const own = ['Headphones (3.5 mm)', 'HDMI 1', 'HDMI 2'];
      return st.outputs.length > 0 && st.outputs.every((o) => own.includes(o.split(' — ')[0]));
    },
    short(m) { return m.model.replace(/\s*\(\d+x\d+\)\s*$/, '') || m.model; },
    labelOf(label) {
      const m = (st.screenInfo?.models ?? []).find((x) => x.label === label) ?? (st.screenInfo?.suggested?.label === label ? st.screenInfo.suggested : null);
      return m ? `${m.maker} ${live.short(m)} · ${m.width} × ${m.height}` : label ? String(label).replace('/', ' ') : 'Not chosen';
    },
    makers() {
      const all = st.screenInfo?.models ?? [];
      return [...new Set(all.map((m) => m.maker))].map((name) => ({ name, n: all.filter((m) => m.maker === name).length }));
    },
    models(maker) { return (st.screenInfo?.models ?? []).filter((m) => m.maker === maker); },
    asksKeep(label) {
      const m = (st.screenInfo?.models ?? []).find((x) => x.label === label) ?? st.screenInfo?.suggested;
      return !!m && !(st.screenInfo?.unchanged ?? []).includes(m.id);
    },
    //: Whether an output has a volume control of its own: without one,
    //: Hardware cannot be had (ADR-0127 §2). Unknown counts as having one.
    hasHw(option) { return st.volHw[option] !== false; },
    //: The output chosen, and a volume type it can take.
    pickOutput(option) {
      st.output = option;
      if (st.volume === 'Hardware' && !live.hasHw(option)) st.volume = 'Software';
    },
    pluginName(id) { return st.offered.find((p) => p.id === id)?.name ?? id; },
    pickBackup() {
      const input = Object.assign(document.createElement('input'), { type: 'file' });
      input.onchange = () => input.files?.[0] && live.upload(input.files[0]);
      input.click();
    },
    upload(file) {
      st.uploadError = null;
      st.uploading = 0;
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `/setup/backup?name=${encodeURIComponent(file.name)}`);
      xhr.setRequestHeader('Content-Type', 'application/octet-stream');
      xhr.upload.onprogress = (e) => { if (e.lengthComputable) st.uploading = e.loaded / e.total; };
      xhr.onload = () => {
        let body = {};
        try { body = JSON.parse(xhr.responseText); } catch { /* not JSON */ }
        st.uploading = null;
        if (xhr.status >= 200 && xhr.status < 300) setBackup(body.backup ?? null);
        else st.uploadError = body.error ?? 'The file did not reach the player. Try again.';
      };
      xhr.onerror = () => {
        st.uploading = null;
        st.uploadError = "The file did not reach the player. Your phone may have dropped off the player's Wi-Fi for a moment.";
      };
      xhr.send(file);
    },
    //: One step's answers, as the old page sent them: the core takes a
    //: network sent again as a new try and drops the last join's error.
    answers(s, id) {
      switch (id) {
        case 'p1net': {
          const chosen = s.nets.find((n) => n.name === s.net), sec = s.other ? true : chosen ? chosen.secured : false;
          const a = { ssid: s.net || null, hidden: !!s.other };
          if (s.pw) a.password = s.pw;
          else if (s.net && !sec) a.password = null;
          return a;
        }
        case 'p1start': return { start: s.start === 'backup' ? 'restore' : 'new' };
        case 'p1name': st.nameSaved = true; return { name: s.name.trim() };
        case 'p1clock': return { timezone: s.tz, clock: s.fmt ? '12 h' : '24 h' };
        case 'p1output': return { output: s.output, volume: s.volume };
        case 'p1screen': return s.scr === 'headless' ? { headless: true } : s.scPick ? { headless: false, screen: s.scPick } : {};
        default: return {};
      }
    },
    //: Each step saved on the player as it is left (ADR-0104 §4: a page that
    //: drops resumes where it was), with the step it goes to.
    save(s, to) {
      const a = { ...live.answers(s, s.screen), step: to };
      json('/setup/answers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(a) })
        .then((saved) => { st.hasPw = !!saved.has_password; if (s.screen === 'p1net') { st.pw = ''; st.joinError = saved.error ?? null; } })
        .catch((err) => { st.problem = err.message; });
    },
    //: The design's Done on Restoring: the player's address, where it opens
    //: once it is back.
    close() {
      if (mode === 'p1') { window.location.href = home(); return; }
      onclose?.();
    },
    //: ADR-0131 as amended (George, 2026-10-08): a backup restored under
    //: another name can start a second player.
    second(on) {
      st.second = on;
      json('/setup/answers', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ second_player: on }) }).catch(() => {});
    },
    async finish1(id) {
      st.problem = null;
      try {
        const told = await json('/setup/finish', { method: 'POST' });
        st.keepQ = !!told?.keep_question;
        waitForHome();
      } catch (err) {
        st.problem = err.message;
        comp.go(id === 'p1restored' ? 'p1restore' : 'p1review');
      }
    }
  };

  async function json(url, opts) {
    const r = await fetch(url, opts);
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(body.error || `${url}: ${r.status}`);
    return body;
  }
  function setBackup(b) {
    st.backup = b;
    //: A restore opens on the backup's name; a name typed in setup wins.
    if (b?.settings?.device_name && !st.nameSaved) st.name = b.settings.device_name;
    st.backupMade = b?.made ? new Date(b.made * 1000).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '';
  }
  //: **The page carries on into part 2** (the design's p1join): once this page's
  //: own player has gone from the setup network, it asks the player's new
  //: address until it answers, and opens it there - where part 2 is owed.
  function home() {
    return `http://${slug(st.name) || 'gexis'}.local:8090`;
  }
  function waitForHome() {
    const target = home();
    //: Over the cable the page's own address keeps answering: the player
    //: is given the time its restart takes, then asked at its new address.
    let gone = false;
    if (st.overLan) setTimeout(() => (gone = true), 15000);
    const timer = setInterval(async () => {
      if (!gone) {
        try { await fetch('/setup/status', { cache: 'no-store' }); } catch { gone = true; }
        return;
      }
      try {
        await fetch(`${target}/surface`, { mode: 'no-cors', cache: 'no-store' });
        clearInterval(timer);
        window.location.href = `${target}/`;
      } catch { /* not there yet */ }
    }, 4000);
  }

  //: Part 1's start: the answers kept on the player (a page that dropped, or
  //: a failed join), the networks, the screen, the outputs, the time zones.
  async function loadPart1() {
    let saved = {}, rows = {};
    try { saved = await json('/setup/answers'); } catch { /* a fresh start */ }
    try {
      const walk = (o) => {
        if (Array.isArray(o)) o.forEach(walk);
        else if (o && typeof o === 'object') { if (o.key && o.type) rows[o.key] = o; Object.values(o).forEach(walk); }
      };
      walk(await json('/settings'));
    } catch { /* defaults */ }
    await live.loadScreens();
    try { st.offered = await json('/setup/plugins'); } catch { st.offered = []; }
    const zones = rows.timezone?.options ?? [];
    let phoneTz = null;
    try { phoneTz = Intl.DateTimeFormat().resolvedOptions().timeZone || null; } catch { /* none */ }
    let tz = saved.timezone ?? (setup?.needed ? phoneTz : rows.timezone?.value) ?? phoneTz;
    if (tz && zones.length && !zones.includes(tz)) tz = null;
    const outputs = rows.output_device?.options ?? [];
    try { for (const o of await json('/setup/outputs')) st.volHw[o.option] = o.hardware; } catch { /* all offered */ }
    const sug = st.screenInfo?.suggested;
    const scPick = saved.headless ? null : saved.screen ?? (setup?.needed ? null : rows.screen?.value ?? null) ?? sug?.label ?? null;
    Object.assign(st, {
      overLan: setup?.network === 'online',
      name: saved.name ?? rows.device_name?.value ?? 'gexis', zones, tz, tzMode: tz ? 'auto' : 'hand',
      fmt: (saved.clock ?? rows.clock_format?.value ?? '24 h') === '12 h' ? 1 : 0,
      outputs, outNotes: rows.output_device?.optionNotes ?? {}, recommended: rows.output_device?.value ?? outputs[0] ?? null,
      output: saved.output ?? rows.output_device?.value ?? outputs[0] ?? null,
      volume: saved.volume ?? rows.output_mode?.value ?? 'Hardware',
      //: Settings' notes, without the sentence it adds about the output in
      //: use now: in setup the output is still being chosen.
      volNotes: Object.fromEntries(Object.entries(rows.output_mode?.optionNotes ?? {})
        .map(([k, v]) => [k, String(v).replace(/\s*DSD files play natively on [^.]*\./, '')])),
      scr: saved.headless ? 'headless' : scPick && sug && scPick === sug.label ? 'panel' : scPick ? 'other' : sug ? 'panel' : 'other',
      scPick, scMaker: null,
      start: saved.start === 'restore' ? 'backup' : 'new',
      net: saved.ssid ?? '', other: !!saved.hidden, otherName: saved.hidden ? saved.ssid ?? '' : '', pw: '',
      hasPw: !!saved.has_password, joinError: saved.error ?? null,
      nameSaved: saved.name != null, second: saved.second_player ?? true
    });
    if (saved.backup) setBackup(saved.backup);
    if (st.volume === 'Hardware' && !live.hasHw(st.output)) st.volume = 'Software';
    const p1 = ['p1welcome', 'p1net', 'p1start', 'p1backup', 'p1name', 'p1clock', 'p1output', 'p1screen', 'p1review', 'p1restore'];
    st.screen = st.joinError ? 'p1net' : p1.includes(saved.step) ? saved.step : 'p1welcome';
    st.ready = true;
    live.rescan();
  }

  //: **The answers as settings** (ADR-0149): only what part 2 asked, and
  //: plugins only ever switched on - a preset that leaves one out must not
  //: uninstall what the player has (decided 2026-10-18).
  function answersAsSettings(s) {
    const d = comp.d(s);
    const o = { spotify_enabled: d.spo && s.spotify, bt_enabled: d.bt && s.bt, lms_enabled: d.lyr };
    if (d.lyr) {
      if (s.lyrState === 'found' && s.lyrServer) o.lms_server = s.lyrServer;
      else if (s.lyrAddrOpen && s.lyrAddr.trim()) o.lms_server = s.lyrAddr.trim();
      else if (d.here && $settingsDevice.address) o.lms_server = `${$settingsDevice.address}:9000`;
      if (!d.headless) {
        o.lms_extended_nav = s.browse === 'ext';
        o.lms_library = s.browse !== 'off';
      }
    }
    if (d.here) o['lyrion-server.enabled'] = true;
    if (d.plex && s.plexOn) o['plexamp.enabled'] = true;
    if (!d.headless) {
      const loc = s.loc.trim();
      Object.assign(o, {
        visualiser_skins: s.vizOn, viz_timeout: parseInt(s.vizAfter, 10), skin_corpus: SKINS.find((x) => x[0] === s.skin)[1],
        skin_motion: s.animate, record_speed: s.rpm ? '45 rpm' : '33 rpm',
        waiting_clock: s.waitClock, waiting_background: s.waitBg, waiting_wallpaper_styles: [...s.styles],
        idle_enabled: s.idleOn, idle_background: s.bg, wallpaper_styles: [...s.styles], idle_clock: s.clock,
        idle_weather: s.weather && !!loc, standby_schedule: s.standby && s.ivs.length > 0,
        standby_times: s.ivs.map((iv) => ({ from: iv.from, until: iv.until, days: [...iv.days] }))
      });
      if (loc) o.weather_location = loc;
      o.phone_touchpad = s.touchpad;
    }
    return o;
  }

  //: **Asked again from Settings, the page starts from what the player has**;
  //: a new player starts from the design's own defaults (`init`).
  function fromSettings(v) {
    const after = [2, 10, 30].reduce((a, b) => (Math.abs(b - (Number(v.viz_timeout) || 10)) < Math.abs(a - (Number(v.viz_timeout) || 10)) ? b : a));
    const styles = (Array.isArray(v.wallpaper_styles) ? v.wallpaper_styles : []).filter((x) => STYLES.includes(x));
    Object.assign(st, {
      browse: v.lms_library === false ? 'off' : v.lms_extended_nav ? 'ext' : 'simple',
      spotify: v.spotify_enabled !== false, bt: v.bt_enabled !== false,
      vizOn: v.visualiser_skins === true, vizAfter: `${after} min`,
      skin: (SKINS.find((x) => x[1] === v.skin_corpus) ?? SKINS[0])[0], animate: v.skin_motion !== false, rpm: v.record_speed === '45 rpm' ? 1 : 0,
      waitClock: v.waiting_clock !== false, waitBg: v.waiting_background === 'Black' ? 'Black' : 'Gexis wallpapers',
      styles: styles.length ? styles : ['Calm'], wallStyle: styles[0] ?? 'Calm',
      idleOn: v.idle_enabled === true, bg: BGS.includes(v.idle_background) ? v.idle_background : 'Gexis wallpapers',
      clock: v.idle_clock !== false, weather: v.idle_weather === true && !!v.weather_location,
      standby: v.standby_schedule === true, touchpad: v.phone_touchpad !== false
    });
    if (Array.isArray(v.standby_times) && v.standby_times.length) st.ivs = v.standby_times.map((iv) => ({ ...iv, days: [...iv.days] }));
  }

  let seeded = false;
  $effect(() => {
    const v = $settingValues;
    if (mode !== 'p2' || seeded || !st.ready || !Object.keys(v).length) return;
    seeded = true;
    Object.assign(st, {
      name: $settingsDevice.name || v.device_name || 'gexis', fmt: v.clock_format === '12 h' ? 1 : 0,
      scr: v.headless === true ? 'headless' : 'panel', loc: v.weather_location ?? '',
      net: typeof v.wifi === 'string' && v.wifi ? v.wifi : 'your network',
      town: String(v.timezone ?? '').split('/').pop().replace(/_/g, ' '),
      plexOn: v['plexamp.enabled'] === true, plexPct: v['plexamp.enabled'] === true ? 100 : 0
    });
    if (!st.first) fromSettings(v);
  });
  $effect(() => { if ($settingsDevice.name) st.name = $settingsDevice.name; });

  // Plexamp's download, live (ADR-0100).
  $effect(() => {
    const c = $components?.plexamp;
    if (!st.plexOn || !c) return;
    st.plexPct = c.state === 'installed' ? 100 : Math.max(st.plexPct, pctOf({ ...c, state: c.state === 'installed' ? 'done' : c.state }));
  });
  // A phone asking to pair, answered on this page (ADR-0045).
  $effect(() => {
    const p = $pairing;
    if (p?.state === 'asking') {
      const c = String(p.code ?? '');
      Object.assign(st, { btPhase: 'request', pairDevice: p.device ?? 'A phone', pairCode: c.length === 6 ? `${c.slice(0, 3)} ${c.slice(3)}` : c });
    } else if (p?.state === 'accepted' && st.btPhase === 'request') {
      st.btPhase = 'paired';
      setTimeout(() => live.trusted(), 1200);
    } else if (!p && st.btPhase === 'request') {
      st.btPhase = 'disc';
    }
  });
  // The prototype's scroll to the top on a new screen.
  $effect(() => {
    st.screen;
    if (refs.scrollRef) refs.scrollRef.scrollTop = 0;
  });

  onMount(() => {
    loadSettings();
    const wide = () => (st.wide = window.innerWidth >= 900);
    wide();
    window.addEventListener('resize', wide);
    const clock = setInterval(() => (st.tick += 1), 20000);
    if (mode === 'p1') {
      loadPart1();
      //: The page says it is still open (ADR-0104): the player keeps its
      //: setup network while it is in use.
      const here = setInterval(() => { if (document.visibilityState === 'visible') fetch('/setup/status').catch(() => {}); }, 60000);
      return () => { window.removeEventListener('resize', wide); clearInterval(clock); clearInterval(here); };
    }
    (async () => {
      try {
        const r = await fetch('/personalise');
        if (r.ok) {
          const got = await r.json();
          st.first = got.first !== false;
          st.plugins = got.plugins ?? [];
        }
      } catch { /* a first run is assumed */ }
      st.ready = true;
      const found = ((await listItems('lms_server')).items ?? []).filter((i) => !String(i.meta ?? '').startsWith('This player'));
      const server = found.find((i) => i.state === 'current') ?? found[0];
      if (server) {
        const address = server.address ?? server.name;
        Object.assign(st, { lyrState: 'found', lyrServer: address, lyrMeta: server.name !== address ? `${server.name} · ${address}` : address });
      } else st.lyrState = 'none';
    })();
    return () => {
      window.removeEventListener('resize', wide);
      clearInterval(clock);
    };
  });

  const V = $derived(comp.renderVals());
</script>


<div style="position:fixed;inset:0;height:100dvh;background:#0c1014;color:#e9eef2;font-family:'Nunito Sans Variable','Nunito Sans','Avenir Next','Segoe UI',system-ui,sans-serif;">
    <div style="position:relative;flex-shrink:0;overflow:hidden;background:#101a21;box-sizing:border-box;display:flex;flex-direction:column;width:{V.fw};height:{V.fh};border-radius:{V.rad};">
      <div style="position:absolute;inset:0;background:#37505f;"></div>
      <div style="position:absolute;inset:0;background:radial-gradient(130% 105% at 20% 42%,rgba(20,33,42,0.72),rgba(13,21,28,0.96));"></div>

      <div style="position:relative;flex-shrink:0;display:flex;flex-direction:column;padding:{V.headPad};">
        <div style="display:flex;align-items:center;gap:16px;min-width:0;">
          <img src={mark} alt="" width="34" height="34" style="width:34px;height:34px;flex-shrink:0;display:block;">
          <div style="flex:1;min-width:0;font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{V.crumb}</div>
        </div>
        <div style="height:3px;border-radius:2px;background:rgba(233,238,242,0.1);margin-top:22px;overflow:hidden;display:{V.progDisplay};">
          <div style="height:100%;transition:width 300ms ease;width:{V.prog};background:{V.accent};"></div>
        </div>
      </div>

      <div style="position:relative;flex:1;min-height:0;display:flex;padding:{V.bodyPad};gap:{V.colGap};">
        <div style="width:calc(50% - 24px);flex-shrink:0;flex-direction:column;justify-content:center;gap:12px;display:{V.leftDisplay};">
          {#if V.hasSidePv}
            <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);">{V.sidePv.head}</div>
            <PanelMini kind={V.sidePv.kind} marks={V.sidePv.marks} time={V.sidePv.time} place={V.sidePv.place} player={V.sidePv.player} weather={V.sidePv.weather} bg={V.sidePv.bg} wallSrc={V.sidePv.wallSrc} photo={V.sidePv.photo} clock={V.sidePv.clock} black={V.sidePv.black} rpm={V.sidePv.rpm} animate={V.sidePv.animate} secs={V.sidePv.secs} phone={V.sidePv.phone} pointer={V.sidePv.pointer} />
          {/if}
          {#if V.noSidePv}
            <div style="aspect-ratio:16/10;border-radius:12px;border:2px dashed rgba(233,238,242,0.2);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;padding:24px;box-sizing:border-box;text-align:center;">
              <div style="font-size:18px;font-weight:700;">No screen on this player</div>
              <div style="font-size:14px;line-height:1.45;color:rgba(233,238,242,0.6);max-width:34ch;text-wrap:pretty;">Headless was chosen in part 1, so part 2 skips Browse and the three screen questions.</div>
            </div>
          {/if}
        </div>

        <div style="flex:1;min-width:0;display:flex;flex-direction:column;">
          <div bind:this={refs.scrollRef} style="flex:1;min-height:0;overflow-y:auto;scrollbar-width:none;display:flex;flex-direction:column;gap:22px;padding:2px 0 12px;">
            <div style="align-items:center;gap:11px;font-family:'IBM Plex Mono','Courier New',monospace;font-size:13px;letter-spacing:0.2em;text-transform:uppercase;flex-shrink:0;display:{V.eyebrowDisplay};color:{V.accent};">
              <span style="width:9px;height:9px;border-radius:50%;flex-shrink:0;display:block;background:{V.accent};"></span>
              <span>{V.stepName}</span>
              <span style="flex:1;height:1px;background:rgba(233,238,242,0.1);display:block;"></span>
            </div>
            <div style="flex-shrink:0;">
              <div style="font-weight:800;letter-spacing:-0.015em;line-height:1.15;text-wrap:pretty;font-size:{V.tSize};">{V.title}</div>
              <div style="font-size:16px;line-height:1.5;color:rgba(233,238,242,0.66);margin-top:8px;text-wrap:pretty;display:{V.subDisplay};">{V.sub}</div>
            </div>

            {#if V.hasInlinePv}
              <div style="display:flex;flex-direction:column;gap:10px;flex-shrink:0;">
                <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);">{V.pv.head}</div>
                <PanelMini kind={V.pv.kind} marks={V.pv.marks} time={V.pv.time} place={V.pv.place} player={V.pv.player} weather={V.pv.weather} bg={V.pv.bg} wallSrc={V.pv.wallSrc} photo={V.pv.photo} clock={V.pv.clock} black={V.pv.black} rpm={V.pv.rpm} animate={V.pv.animate} secs={V.pv.secs} phone={V.pv.phone} pointer={V.pv.pointer} />
              </div>
            {/if}

            {#each V.blocks as b}
              <div style="display:flex;flex-direction:column;flex-shrink:0;">

                {#if b.isList}
                  <div style="display:flex;flex-direction:column;gap:6px;">
                    <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);padding:4px 2px;display:{b.headDisplay};">{b.head}</div>
                    {#each b.rows as o}
                      <div onclick={o.onClick} style="display:flex;flex-wrap:wrap;align-items:center;gap:14px;min-height:64px;padding:12px 16px;border-radius:14px;box-sizing:border-box;transition:background 150ms,border-color 150ms;cursor:{o.cursor};background:{o.bg};border:1px {o.bs} {o.border};">
                        <span style="width:24px;height:24px;border-radius:50%;flex-shrink:0;box-sizing:border-box;align-items:center;justify-content:center;display:{o.radioDisplay};border:2px solid {o.ring};">
                          <span style="width:11px;height:11px;border-radius:50%;background:#7ed6bc;display:{o.dotDisplay};"></span>
                        </span>
                        <span style="width:40px;height:40px;border-radius:12px;background:rgba(233,238,242,0.07);border:1px solid rgba(233,238,242,0.12);box-sizing:border-box;flex-shrink:0;align-items:center;justify-content:center;display:{o.iconDisplay};">
                          {#if o.isLyr}<img src={lyrionIcon} alt="" style="display:block;width:28px;height:21px;">{/if}
                          {#if o.isSpo}<img src={spotifyIcon} alt="" style="display:block;width:22px;height:22px;">{/if}
                          {#if o.isBt}<img src={btIcon} alt="" style="display:block;width:22px;height:22px;">{/if}
                          <span style="width:22px;height:22px;border-radius:50%;border:2px solid rgba(233,238,242,0.7);box-sizing:border-box;align-items:center;justify-content:center;font-size:11px;font-weight:800;display:{o.letterDisplay};">{o.letter}</span>
                        </span>
                        <span style="flex:1;min-width:0;">
                          <span style="display:block;font-size:17px;font-weight:600;text-wrap:pretty;color:{o.labelInk};">{o.label}</span>
                          <span style="font-size:14px;line-height:1.4;color:rgba(233,238,242,0.6);margin-top:3px;text-wrap:pretty;display:{o.noteDisplay};">{o.note}</span>
                          <span style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:13px;letter-spacing:0.04em;margin-top:3px;color:rgba(233,238,242,0.6);display:{o.metaDisplay};">{o.meta}</span>
                          <span style="flex-wrap:wrap;gap:6px;margin-top:9px;display:{o.srcDisplay};">
                            {#each o.srcs as sx}
                              <span style="display:flex;align-items:center;gap:7px;height:30px;padding:0 11px 0 7px;border-radius:999px;background:rgba(233,238,242,0.07);border:1px solid rgba(233,238,242,0.12);box-sizing:border-box;font-size:13px;font-weight:600;color:rgba(233,238,242,0.85);">
                                {#if sx.isLyr}<img src={lyrionIcon} alt="" style="display:block;width:20px;height:15px;">{/if}
                                {#if sx.isSpo}<img src={spotifyIcon} alt="" style="display:block;width:16px;height:16px;">{/if}
                                {#if sx.isBt}<img src={btIcon} alt="" style="display:block;width:16px;height:16px;">{/if}
                                {#if sx.isPlex}<span style="width:16px;height:16px;border-radius:50%;border:2px solid rgba(233,238,242,0.7);box-sizing:border-box;display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:800;">P</span>{/if}
                                <span>{sx.name}</span>
                              </span>
                            {/each}
                          </span>
                        </span>
                        <span style="order:9;flex-basis:100%;align-items:baseline;flex-wrap:wrap;column-gap:10px;row-gap:2px;padding-top:10px;border-top:1px solid rgba(233,238,242,0.1);display:{o.footDisplay};">
                          <span style="display:flex;align-items:center;gap:8px;font-size:13px;font-weight:600;color:rgba(233,238,242,0.75);"><span style="width:7px;height:7px;border-radius:50%;background:{o.footDot};flex-shrink:0;"></span>{o.foot}</span>
                          <span style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;color:rgba(233,238,242,0.5);">{o.footMeta}</span>
                        </span>
                        <span style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;padding:4px 8px;border-radius:6px;flex-shrink:0;display:{o.tagDisplay};background:{o.tagBg};color:{o.tagInk};">{o.tag}</span>
                        <span style="align-items:flex-end;gap:3px;height:18px;flex-shrink:0;display:{o.barsDisplay};">
                          <span style="width:4px;height:6px;border-radius:1px;display:block;background:{o.b1};"></span>
                          <span style="width:4px;height:10px;border-radius:1px;display:block;background:{o.b2};"></span>
                          <span style="width:4px;height:14px;border-radius:1px;display:block;background:{o.b3};"></span>
                          <span style="width:4px;height:18px;border-radius:1px;display:block;background:{o.b4};"></span>
                        </span>
                        <span style="width:58px;height:30px;border-radius:999px;flex-shrink:0;position:relative;box-sizing:border-box;transition:background 150ms;display:{o.togDisplay};background:{o.togBg};border:1px solid {o.togBorder};">
                          <span style="position:absolute;top:2px;width:24px;height:24px;border-radius:50%;display:block;transition:left 150ms;left:{o.knobLeft};background:{o.knobBg};"></span>
                        </span>
                        <span style="width:24px;height:24px;border-radius:7px;box-sizing:border-box;flex-shrink:0;align-items:center;justify-content:center;display:{o.chkDisplay};background:{o.boxBg};border:2px solid {o.ring};">
                          <span style="width:11px;height:6px;border-left:2.5px solid #0d151c;border-bottom:2.5px solid #0d151c;transform:rotate(-45deg);margin-top:-3px;display:{o.dotDisplay};"></span>
                        </span>
                        <span style="width:11px;height:11px;border-right:2.5px solid rgba(233,238,242,0.42);border-top:2.5px solid rgba(233,238,242,0.42);transform:rotate(45deg);flex-shrink:0;margin-right:4px;display:{o.chevDisplay};"></span>
                      </div>
                    {/each}
                  </div>
                {/if}

                {#if b.isNote}
                  <div style="display:flex;align-items:flex-start;gap:14px;padding:14px 16px;border-radius:16px;box-sizing:border-box;background:{b.bg};border:1px solid {b.border};">
                    <span style="width:4px;align-self:stretch;border-radius:2px;flex-shrink:0;display:block;background:{b.bar};"></span>
                    <span style="flex:1;min-width:0;">
                      <span style="font-size:16px;font-weight:600;margin-bottom:4px;display:{b.titleDisplay};">{b.title}</span>
                      <span style="display:block;font-size:15px;line-height:1.45;color:rgba(233,238,242,0.7);text-wrap:pretty;">{b.text}</span>
                    </span>
                  </div>
                {/if}

                {#if b.isField}
                  <div style="display:flex;flex-direction:column;gap:8px;">
                    <span style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);">{b.label}</span>
                    <input type={b.type} value={b.value} placeholder={b.ph} oninput={b.onChange} readonly={b.ro} style="width:100%;height:56px;border-radius:14px;background:rgba(8,12,16,0.6);border:1px solid rgba(233,238,242,0.18);padding:0 18px;box-sizing:border-box;font-family:'IBM Plex Mono','Courier New',monospace;font-size:16px;color:#e9eef2;outline:none;opacity:{b.op};cursor:{b.cur};" />
                    <span style="font-size:14px;line-height:1.4;color:rgba(233,238,242,0.6);text-wrap:pretty;display:{b.hintDisplay};">{b.hint}</span>
                  </div>
                {/if}

                {#if b.isStatus}
                  <div style="display:flex;flex-direction:column;gap:12px;box-sizing:border-box;border-radius:14px;padding:12px 14px;background:rgba(255,255,255,0.05);border:1px solid rgba(233,238,242,0.1);">
                  <div style="display:flex;align-items:center;gap:14px;">
                    <div style="width:30px;height:30px;border-radius:50%;box-sizing:border-box;border:3px solid rgba(233,238,242,0.14);border-top-color:#7ed6bc;animation:fuSpin 900ms linear infinite;flex-shrink:0;display:{b.spinDisplay};"></div>
                    <span style="width:30px;height:30px;border-radius:50%;background:rgba(126,214,188,0.16);flex-shrink:0;align-items:center;justify-content:center;display:{b.doneDisplay};"><span style="width:12px;height:7px;border-left:2.5px solid #7ed6bc;border-bottom:2.5px solid #7ed6bc;transform:rotate(-45deg);margin-top:-3px;display:block;"></span></span>
                    <span style="width:30px;height:30px;border-radius:50%;border:2px dashed rgba(233,238,242,0.4);box-sizing:border-box;flex-shrink:0;display:{b.noneDisplay};"></span>
                    <span style="flex:1;display:flex;flex-direction:column;gap:2px;min-width:0;"><span style="font-size:16px;font-weight:700;text-wrap:pretty;">{b.text}</span><span style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:13px;color:rgba(233,238,242,0.6);display:{b.metaDisplay};">{b.meta}</span></span>
                    <span onclick={b.onAct} style="flex-shrink:0;padding:8px 14px;border-radius:999px;background:rgba(233,238,242,0.07);border:1px solid rgba(233,238,242,0.16);font-size:13px;font-weight:700;white-space:nowrap;cursor:pointer;display:{b.actDisplay};">{b.act}</span>
                  </div>
                  <div style="flex-direction:column;gap:8px;padding-left:44px;display:{b.fieldDisplay};">
                    <span style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);">{b.fLabel}</span>
                    <input type="text" value={b.fValue} placeholder={b.fPh} oninput={b.fOnChange} style="width:100%;height:52px;border-radius:12px;background:rgba(8,12,16,0.6);border:1px solid rgba(233,238,242,0.18);padding:0 16px;box-sizing:border-box;font-family:'IBM Plex Mono','Courier New',monospace;font-size:16px;color:#e9eef2;outline:none;" />
                    <span style="font-size:14px;line-height:1.4;color:rgba(233,238,242,0.6);text-wrap:pretty;">{b.fHint}</span>
                  </div>
                  </div>
                {/if}

                {#if b.isRule}
                  <div style="margin-top:14px;height:1px;background:rgba(233,238,242,0.1);"></div>
                {/if}

                {#if b.isHead}
                  <div style="margin-top:14px;padding-top:18px;border-top:1px solid rgba(233,238,242,0.1);font-size:19px;font-weight:800;color:#e9eef2;">{b.text}</div>
                {/if}

                {#if b.isP}
                  <div style="font-size:16px;line-height:1.5;color:rgba(233,238,242,0.72);text-wrap:pretty;">{b.text}</div>
                {/if}

                {#if b.isBtn}
                  <div onclick={b.onClick} style="align-self:flex-start;padding:12px 22px;border-radius:999px;background:rgba(233,238,242,0.07);border:1px solid rgba(233,238,242,0.16);font-size:15px;font-weight:700;box-sizing:border-box;cursor:pointer;">{b.label}</div>
                {/if}

                {#if b.isPics}
                  <div style="display:flex;flex-direction:column;gap:10px;">
                    <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);display:{b.headDisplay};">{b.head}</div>
                    <div style="display:grid;gap:10px;grid-template-columns:{b.cols};">
                      {#each b.items as p}
                        <div onclick={p.onClick} style="position:relative;border-radius:16px;box-sizing:border-box;display:flex;cursor:pointer;padding:10px;transition:background 150ms,border-color 150ms;background:{p.bg};border:1px solid {p.border};flex-direction:{p.dir};gap:{p.gap};align-items:{p.ai};">
                          <div style="flex-shrink:0;width:{p.mw};">
                            <PanelMini kind={p.kind} marks={p.marks} wire={p.wire} rpm={p.rpm} />
                          </div>
                          <div style="flex:1;min-width:0;padding:0 4px 4px;padding-right:{p.lpr};">
                            <div style="font-size:{p.lfs};font-weight:700;line-height:1.3;text-wrap:pretty;">{p.label}</div>
                            <div style="font-size:13px;line-height:1.4;color:rgba(233,238,242,0.6);margin-top:4px;text-wrap:pretty;display:{p.noteDisplay};">{p.note}</div>
                            <div style="margin-top:8px;display:{p.tagDisplay};"><span style="display:inline-block;font-family:'IBM Plex Mono','Courier New',monospace;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;padding:4px 8px;border-radius:6px;background:{p.tagBg};color:{p.tagInk};">{p.tag}</span></div>
                          </div>
                          <span style="position:absolute;top:16px;right:16px;width:22px;height:22px;border-radius:50%;box-sizing:border-box;background:#0d151c;display:flex;align-items:center;justify-content:center;border:2px solid {p.ring};"><span style="width:10px;height:10px;border-radius:50%;background:#7ed6bc;display:{p.dot};"></span></span>
                        </div>
                      {/each}
                    </div>
                  </div>
                {/if}

                {#if b.isWhere}
                  <div style="display:flex;flex-direction:column;gap:10px;">
                    {#each b.items as w}
                      <div onclick={w.onClick} style="padding:12px;border-radius:16px;box-sizing:border-box;display:flex;align-items:center;gap:14px;cursor:pointer;transition:background 150ms,border-color 150ms;background:{w.bg};border:1px solid {w.border};">
                        <div style="width:128px;height:84px;flex-shrink:0;border-radius:10px;background:rgba(8,12,16,0.5);display:flex;align-items:center;justify-content:center;">
                          {#if w.isHere}
                            <div style="display:flex;flex-direction:column;align-items:center;">
                              <div style="width:78px;height:49px;border-radius:6px;box-sizing:border-box;border:2px solid {w.wire};background:#0d151b;box-shadow:0 6px 12px -6px rgba(0,0,0,0.8);display:flex;align-items:center;justify-content:center;gap:7px;">
                                <img src={lyrionIcon} alt="" style="width:22px;height:17px;display:block;">
                                <div style="display:flex;flex-direction:column;gap:3px;"><div style="width:22px;height:2px;border-radius:1px;background:rgba(233,238,242,0.45);"></div><div style="width:16px;height:2px;border-radius:1px;background:rgba(233,238,242,0.3);"></div><div style="width:19px;height:2px;border-radius:1px;background:rgba(233,238,242,0.3);"></div><div style="width:13px;height:2px;border-radius:1px;background:rgba(233,238,242,0.3);"></div></div>
                              </div>
                                                            <span style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:9px;letter-spacing:0.14em;text-transform:uppercase;color:rgba(233,238,242,0.6);margin-top:6px;">This player</span>
                            </div>
                          {/if}
                          {#if w.isFar}
                            <div style="display:flex;align-items:flex-end;gap:4px;">
                              <div style="display:flex;flex-direction:column;align-items:center;">
                                <div style="width:42px;height:28px;border-radius:5px;box-sizing:border-box;border:2px solid {w.wire};background:#0d151b;display:flex;align-items:flex-end;justify-content:center;gap:2px;padding-bottom:5px;"><div style="width:3px;height:6px;background:#7ed6bc;border-radius:1px;"></div><div style="width:3px;height:11px;background:#7ed6bc;border-radius:1px;"></div><div style="width:3px;height:8px;background:#7ed6bc;border-radius:1px;"></div><div style="width:3px;height:13px;background:#7ed6bc;border-radius:1px;"></div></div>
                                
                                <span style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:9px;letter-spacing:0.08em;text-transform:uppercase;color:rgba(233,238,242,0.6);margin-top:6px;">Player</span>
                              </div>
                              <div style="width:10px;border-top:2px dashed rgba(233,238,242,0.4);margin-bottom:35px;"></div>
                              <div style="display:flex;flex-direction:column;align-items:center;">
                                <div style="width:30px;height:44px;border-radius:5px;box-sizing:border-box;border:2px solid {w.wire};background:#0d151b;display:flex;flex-direction:column;align-items:center;gap:3px;padding-top:5px;">
                                  <img src={lyrionIcon} alt="" style="width:16px;height:12px;display:block;margin-bottom:2px;">
                                  <div style="width:20px;height:5px;border-radius:2px;background:rgba(233,238,242,0.12);display:flex;align-items:center;justify-content:flex-end;padding-right:2px;box-sizing:border-box;"><div style="width:3px;height:3px;border-radius:50%;background:#7ed6bc;"></div></div><div style="width:20px;height:5px;border-radius:2px;background:rgba(233,238,242,0.12);display:flex;align-items:center;justify-content:flex-end;padding-right:2px;box-sizing:border-box;"><div style="width:3px;height:3px;border-radius:50%;background:#7ed6bc;"></div></div><div style="width:20px;height:5px;border-radius:2px;background:rgba(233,238,242,0.12);display:flex;align-items:center;justify-content:flex-end;padding-right:2px;box-sizing:border-box;"><div style="width:3px;height:3px;border-radius:50%;background:#7ed6bc;"></div></div>
                                </div>
                                <span style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:9px;letter-spacing:0.08em;text-transform:uppercase;color:rgba(233,238,242,0.6);margin-top:6px;white-space:nowrap;">PC · NAS</span>
                              </div>
                            </div>
                          {/if}
                        </div>
                        <span style="width:20px;height:20px;border-radius:50%;flex-shrink:0;box-sizing:border-box;display:flex;align-items:center;justify-content:center;border:2px solid {w.ring};"><span style="width:9px;height:9px;border-radius:50%;background:#7ed6bc;display:{w.dot};"></span></span>
                        <span style="font-size:15px;font-weight:700;line-height:1.25;">{w.label}</span>
                      </div>
                    {/each}
                  </div>
                {/if}

                {#if b.isSplit}
                  <div style="display:grid;grid-template-columns:minmax(0,1fr);border-radius:16px;overflow:hidden;border:1px solid rgba(233,238,242,0.1);">
                    <div style="padding:14px;background:rgba(126,214,188,0.07);display:flex;flex-direction:column;gap:9px;">
                      <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#7ed6bc;">{b.lhead}</div>
                      {#each b.left as i}
                        <div style="display:flex;gap:8px;align-items:flex-start;font-size:14px;line-height:1.35;">
                          <span style="width:16px;height:16px;border-radius:50%;background:#7ed6bc;flex-shrink:0;display:flex;align-items:center;justify-content:center;margin-top:1px;"><span style="width:7px;height:4px;border-left:2px solid #0d151c;border-bottom:2px solid #0d151c;transform:rotate(-45deg);margin-top:-2px;display:block;"></span></span>
                          <span>{i.t}</span>
                        </div>
                      {/each}
                    </div>
                    <div style="padding:14px;background:rgba(255,255,255,0.03);display:flex;flex-direction:column;gap:9px;border-top:1px solid rgba(233,238,242,0.1);">
                      <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:11px;letter-spacing:0.16em;text-transform:uppercase;color:#e0a758;">{b.rhead}</div>
                      {#each b.right as i}
                        <div style="display:flex;gap:8px;align-items:flex-start;font-size:14px;line-height:1.35;">
                          <span style="width:16px;height:16px;border-radius:50%;border:2px solid #e0a758;box-sizing:border-box;flex-shrink:0;display:block;margin-top:1px;"></span>
                          <span>{i.t}</span>
                        </div>
                      {/each}
                    </div>
                  </div>
                {/if}

                {#if b.isSeg}
                  <div style="display:flex;flex-direction:column;gap:10px;">
                    <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);display:{b.headDisplay};">{b.head}</div>
                    <div style="display:flex;gap:4px;padding:4px;border-radius:999px;background:rgba(255,255,255,0.05);border:1px solid rgba(233,238,242,0.1);">
                      {#each b.opts as x}
                        <span onclick={x.onClick} style="flex:1;text-align:center;padding:11px 8px;border-radius:999px;font-size:15px;font-weight:700;cursor:pointer;transition:background 150ms;background:{x.bg};color:{x.ink};">{x.label}</span>
                      {/each}
                    </div>
                  </div>
                {/if}

                {#if b.isPick}
                  <div style="display:flex;flex-direction:column;gap:10px;">
                    <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);display:{b.headDisplay};">{b.head}<span style="display:{b.multiDisplay};color:rgba(233,238,242,0.45);">&#32;· pick any</span></div>
                    <div style="display:flex;flex-wrap:wrap;gap:8px;">
                      {#each b.items as c}
                        <span onclick={c.onClick} style="display:flex;align-items:center;gap:9px;padding:10px 16px;border-radius:{c.radius};font-size:15px;font-weight:700;box-sizing:border-box;cursor:pointer;transition:background 150ms;background:{c.bg};color:{c.ink};border:1px solid {c.border};"><span style="display:{c.boxDisplay};align-items:center;justify-content:center;width:18px;height:18px;border-radius:5px;box-sizing:border-box;flex-shrink:0;font-size:13px;font-weight:800;line-height:1;color:#0d151c;background:{c.boxBg};border:1.5px solid {c.boxBorder};">{c.tick}</span>{c.label}</span>
                      {/each}
                    </div>
                  </div>
                {/if}

                {#if b.isParty}
                  <PanelMini kind="flow" marks={b.marks} status={b.status} />
                {/if}

                {#if b.isCode}
                  <div style="display:flex;flex-direction:column;align-items:center;gap:14px;padding:24px 16px;border-radius:14px;background:rgba(255,255,255,0.05);border:1px solid rgba(233,238,242,0.1);box-sizing:border-box;text-align:center;">
                    <span style="font-size:16px;font-weight:700;text-wrap:pretty;">{b.label}</span>
                    <span style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:40px;font-weight:600;letter-spacing:0.12em;color:#e9eef2;">{b.code}</span>
                    <div style="display:flex;align-items:center;gap:10px;">
                      <div style="width:18px;height:18px;border-radius:50%;box-sizing:border-box;border:2px solid rgba(233,238,242,0.14);border-top-color:#7ed6bc;animation:fuSpin 900ms linear infinite;flex-shrink:0;"></div>
                      <span style="font-size:14px;line-height:1.4;color:rgba(233,238,242,0.6);text-wrap:pretty;">{b.text}</span>
                    </div>
                  </div>
                {/if}

                {#if b.isNum}
                  <div style="display:flex;flex-direction:column;gap:12px;">
                    {#each b.items as n}
                      <div style="display:flex;align-items:center;gap:14px;">
                        <span style="width:30px;height:30px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;box-sizing:border-box;background:{n.bg};color:{n.ink};border:2px solid {n.ring};">{n.n}</span>
                        <span style="font-size:16px;line-height:1.35;font-weight:600;text-wrap:pretty;color:{n.tc};">{n.t}</span>
                      </div>
                    {/each}
                  </div>
                {/if}

                {#if b.isDev}
                  <div style="display:flex;flex-direction:column;gap:6px;">
                    <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);padding:4px 2px;">Trusted devices</div>
                    {#each b.items as it}
                      <div style="display:flex;align-items:center;gap:16px;min-height:66px;padding:12px 18px;border-radius:14px;box-sizing:border-box;background:rgba(255,255,255,0.05);border:1px solid rgba(233,238,242,0.1);">
                        <span style="flex:1;min-width:0;display:block;">
                          <span style="display:block;font-size:17px;font-weight:600;color:#e9eef2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{it.name}</span>
                          <span style="display:block;font-family:'IBM Plex Mono','Courier New',monospace;font-size:13px;letter-spacing:0.04em;margin-top:4px;color:{it.metaInk};">{it.meta}</span>
                        </span>
                        <span onclick={it.onForget} style="flex-shrink:0;height:44px;padding:0 18px;border-radius:12px;background:rgba(224,167,88,0.14);border:1px solid rgba(224,167,88,0.4);display:flex;align-items:center;font-family:'IBM Plex Mono','Courier New',monospace;font-size:13px;font-weight:600;letter-spacing:0.14em;text-transform:uppercase;color:#e0a758;cursor:pointer;">Forget</span>
                      </div>
                    {/each}
                    <div style="flex-direction:column;align-items:center;gap:14px;padding:22px 20px;display:{b.emptyDisplay};">
                      <span style="width:58px;height:58px;border-radius:50%;border:2px dashed rgba(233,238,242,0.28);display:block;"></span>
                      <span style="font-size:16px;line-height:1.45;color:rgba(233,238,242,0.62);text-align:center;text-wrap:pretty;max-width:36ch;">{b.empty}</span>
                    </div>
                  </div>
                {/if}

                {#if b.isProg}
                  <div style="display:flex;flex-direction:column;gap:10px;padding:14px 16px;border-radius:14px;box-sizing:border-box;background:rgba(255,255,255,0.05);border:1px solid rgba(233,238,242,0.1);">
                    <div style="display:flex;align-items:baseline;gap:12px;">
                      <span style="flex:1;min-width:0;font-size:16px;font-weight:700;">{b.label}</span>
                      <span style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:13px;flex-shrink:0;color:{b.ink};">{b.meta}</span>
                    </div>
                    <div style="height:6px;border-radius:3px;background:rgba(233,238,242,0.1);overflow:hidden;"><div style="height:100%;border-radius:3px;transition:width 900ms linear;background:{b.ink};width:{b.pct};"></div></div>
                    <div style="align-items:center;gap:8px;padding-top:2px;display:{b.stDisplay};">
                      <span style="width:16px;height:16px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;line-height:1;background:{b.stBg};color:#0d151c;border:1.5px solid {b.stBorder};box-sizing:border-box;">{b.stTick}</span>
                      <span style="font-size:14px;color:rgba(233,238,242,0.8);">{b.st}</span>
                    </div>
                  </div>
                {/if}

                {#if b.isCast}
                  <div style="display:flex;flex-direction:column;gap:10px;">
                    <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);">In the Spotify app, on your phone</div>
                    <div style="position:relative;width:100%;height:250px;">
                      <PhoneDeviceList device={b.device} />
                    </div>
                    <div style="font-size:15px;line-height:1.45;color:rgba(233,238,242,0.75);text-wrap:pretty;">{b.text}</div>
                  </div>
                {/if}

                {#if b.isSum}
                  <div style="display:flex;flex-direction:column;gap:10px;">
                    <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);display:{b.headDisplay};">{b.head}</div>
                    <div style="display:flex;flex-direction:column;gap:1px;border-radius:16px;overflow:hidden;border:1px solid rgba(233,238,242,0.1);">
                      {#each b.rows as r}
                        <div style="display:flex;align-items:center;gap:12px;padding:11px 14px;min-height:34px;background:rgba(255,255,255,0.04);">
                          <span style="flex-shrink:0;width:96px;font-size:14px;color:rgba(233,238,242,0.6);">{r.what}</span>
                          <span style="flex:1;min-width:0;font-size:15px;font-weight:600;text-wrap:pretty;overflow-wrap:anywhere;">{r.value}</span>
                          <span onclick={r.onClick} style="flex-shrink:0;padding:6px 12px;border-radius:999px;background:rgba(233,238,242,0.07);border:1px solid rgba(233,238,242,0.16);font-size:13px;font-weight:700;cursor:pointer;display:{r.actDisplay};">Change</span>
                        </div>
                      {/each}
                    </div>
                  </div>
                {/if}

                {#if b.isClock}
                  <div style="display:flex;align-items:center;gap:16px;padding:20px;border-radius:16px;background:rgba(255,255,255,0.05);border:1px solid rgba(233,238,242,0.1);box-sizing:border-box;">
                    <div style="flex:1;min-width:0;">
                      <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);">{b.label}</div>
                      <div style="font-size:22px;font-weight:700;margin-top:8px;">{b.value}</div>
                    </div>
                    <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:28px;font-weight:600;">{b.time}</div>
                  </div>
                {/if}

                {#if b.isAddr}
                  <div style="padding:16px 18px;border-radius:16px;background:rgba(255,255,255,0.05);border:1px solid rgba(233,238,242,0.1);box-sizing:border-box;">
                    <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);">{b.label}</div>
                    <div style="font-family:'IBM Plex Mono','Courier New',monospace;font-weight:600;margin-top:8px;font-size:19px;word-break:break-all;">{b.value}</div>
                  </div>
                {/if}

                {#if b.isIv}
                  <div style="display:flex;flex-direction:column;gap:12px;">
                    <span style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);">Standby times</span>
                    {#each b.items as iv}
                      <div style="position:relative;display:flex;flex-direction:column;gap:12px;padding:14px 16px;border-radius:16px;background:rgba(255,255,255,0.04);border:1px solid rgba(233,238,242,0.1);box-sizing:border-box;">
                        <div onclick={iv.onRemove} style="position:absolute;top:8px;right:8px;width:44px;height:44px;display:grid;place-items:center;border-radius:50%;border:1px solid rgba(233,238,242,0.1);background:rgba(233,238,242,0.07);color:rgba(233,238,242,0.72);box-sizing:border-box;cursor:pointer;"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M7 7l10 10M17 7L7 17"></path></svg></div>
                        <div style="display:flex;flex-direction:column;gap:8px;padding-right:56px;">
                          {#each iv.times as t}
                            <div style="display:flex;align-items:center;gap:12px;">
                              <span style="min-width:56px;font-family:'IBM Plex Mono','Courier New',monospace;font-size:12px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(233,238,242,0.6);">{t.label}</span>
                              <div onclick={t.onTap} style="min-width:104px;min-height:48px;padding:0 16px;box-sizing:border-box;display:flex;align-items:center;justify-content:center;border-radius:12px;border:1px solid {t.border};background:rgba(233,238,242,0.07);color:{t.ink};font-size:22px;font-weight:600;font-variant-numeric:tabular-nums;cursor:pointer;">{t.value}</div>
                            </div>
                          {/each}
                        </div>
                        <div style="flex-direction:column;gap:8px;display:{iv.pickDisplay};">
                          <div style="display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px;">
                            {#each iv.hours as c}
                              <div onclick={c.onTap} style="min-height:44px;display:flex;align-items:center;justify-content:center;border-radius:12px;border:1px solid {c.border};background:{c.bg};color:{c.ink};font-size:16px;font-weight:{c.weight};font-variant-numeric:tabular-nums;box-sizing:border-box;cursor:pointer;">{c.label}</div>
                            {/each}
                          </div>
                          <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;">
                            {#each iv.quarters as c}
                              <div onclick={c.onTap} style="min-height:44px;display:flex;align-items:center;justify-content:center;border-radius:12px;border:1px solid {c.border};background:{c.bg};color:{c.ink};font-size:16px;font-weight:{c.weight};font-variant-numeric:tabular-nums;box-sizing:border-box;cursor:pointer;">{c.label}</div>
                            {/each}
                          </div>
                        </div>
                        <div style="display:flex;flex-wrap:wrap;gap:6px;">
                          {#each iv.days as d}
                            <div onclick={d.onTap} style="min-width:50px;min-height:44px;padding:0 10px;box-sizing:border-box;display:flex;align-items:center;justify-content:center;border-radius:22px;border:1px solid {d.border};background:{d.bg};color:{d.ink};font-size:15px;font-weight:600;cursor:pointer;">{d.label}</div>
                          {/each}
                        </div>
                      </div>
                    {/each}
                    <span style="color:rgba(233,238,242,0.6);display:{b.noneDisplay};">No standby times yet.</span>
                    <div onclick={b.onAdd} style="min-height:52px;display:flex;align-items:center;justify-content:center;border-radius:16px;border:1px dashed rgba(233,238,242,0.1);color:#e9eef2;font-size:16px;font-weight:600;box-sizing:border-box;cursor:pointer;opacity:{b.addOp};">Add standby time</div>
                  </div>
                {/if}

              </div>
            {/each}
          </div>

          <div style="align-items:center;gap:10px;flex-shrink:0;padding-top:14px;display:{V.foot.display};">
            <div onclick={V.foot.onBack} style="padding:12px 20px;border-radius:999px;background:rgba(233,238,242,0.07);border:1px solid rgba(233,238,242,0.16);font-size:15px;font-weight:700;box-sizing:border-box;flex-shrink:0;cursor:pointer;display:{V.foot.backDisplay};">Back</div>
            <div onclick={V.foot.onAlt} style="padding:12px 20px;border-radius:999px;background:rgba(233,238,242,0.07);border:1px solid rgba(233,238,242,0.16);font-size:15px;font-weight:700;box-sizing:border-box;flex-shrink:0;white-space:nowrap;cursor:pointer;display:{V.foot.altDisplay};">{V.foot.alt}</div>
            <div onclick={V.foot.onNext} style="flex:1;text-align:center;padding:17px 18px;border-radius:999px;box-sizing:border-box;font-size:17px;font-weight:800;color:#0d151c;white-space:nowrap;transition:background 200ms,opacity 200ms;background:{V.accent};opacity:{V.foot.nextOp};cursor:{V.foot.nextCursor};">{V.foot.next}</div>
          </div>
        </div>
      </div>
    </div>
</div>
