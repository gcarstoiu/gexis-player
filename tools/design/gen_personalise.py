"""FirstUsePage.svelte from Claude Design's Setup Prototype.dc.html.
The frame's markup is converted mechanically (dc2svelte); the prototype's
script is kept verbatim apart from the replacements below, each one where
the prototype simulates what the player really does."""
import re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from dc2svelte import convert
D = ROOT / "design/source/14-first-use"
UI = ROOT / "ui/src/screens"
src = (D / "Setup Prototype.dc.html").read_text()
lines = src.split("\n")
frame = "\n".join(lines[121:543])          # the phone frame, lines 122-543
assert frame.lstrip().startswith('<div style="position:relative;flex-shrink:0;overflow:hidden;background:#101a21'), frame[:120]
imports = {'gexis-mark.svg': 'mark', 'icon-lyrion.svg': 'lyrionIcon', 'icon-spotify.png': 'spotifyIcon', 'icon-bluetooth.png': 'btIcon'}
markup = convert(frame, imports)
# The prototype draws a phone; the page IS the phone: the frame's own
# border and shadow are the mock-up's, not the design's.
markup = markup.replace('border:1px solid rgba(233,238,242,0.14);box-shadow:0 30px 60px rgba(0,0,0,0.45);', '', 1)
js = src[src.index('data-dc-script>') + len('data-dc-script>'):src.rindex('</script>')]
R = []
def rep(a, b, n=1):
    global js
    assert js.count(a) == n, (a[:80], js.count(a))
    js = js.replace(a, b)
    R.append(a.split("\n")[0][:70])

# Images are the player's copies.
rep("const WALLS = { Calm: 'wallpapers/calm/c148381086.webp', Colourful: 'art/pd-kandinsky7.jpg', Psychedelic: 'art/pd-starry.jpg' };",
    "const WALLS = { Calm: calmWall, Colourful: colourfulWall, Psychedelic: psychedelicWall };")
# The network the player is on, not the mock-up's.
rep("['folder', 'Music folder', 'On the player, shared on Studio 5G.']", "['folder', 'Music folder', 'On the player, shared on your network.']")
# Lifecycle: Svelte's, below.
rep("  state = init('A', 'p1', false);\n  scrollRef = React.createRef();\n", "")
rep("  componentDidMount() { this.iv = setInterval(() => this.tick(), 1000); this.enter(this.state.screen); }\n", "")
rep("  componentWillUnmount() { clearInterval(this.iv); clearTimeout(this.t1); clearTimeout(this.t2); }\n", "")
rep("  componentDidUpdate(pp, ps) { if (ps && ps.screen !== this.state.screen && this.scrollRef.current) this.scrollRef.current.scrollTop = 0; }\n", "")
# The Lyrion search is real and has run; Getting ready writes the answers;
# Kept the defaults puts part 2 off on the player.
rep("    if (id === 'listen' && s.lyrState === 'idle') this.setState({ lyrState: s.flow === 'A' ? 'found' : 'none' });\n", "")
rep("    if (id === 'done') this.setState({ inst: 0 });", "    if (id === 'done') live.finish();\n    if (id === 'later') live.later();\n    if (id === 'bluetooth') live.trusted();\n    if (id === 'folders') live.loadShares();")
# Close leaves the page.
rep("    if (['done', 'later', 'p1restored'].includes(s.screen)) return this.restart();", "    if (['done', 'later', 'p1restored'].includes(s.screen)) return live.close();")
# No simulation clock: Plexamp's download and the pairing come from the player.
rep("""    if (s.plexOn && s.plexPct < 100) u.plexPct = Math.min(100, s.plexPct + 6);
    if (s.btPhase === 'request') { if (s.reqLeft <= 1) u.btPhase = 'disc'; else u.reqLeft = s.reqLeft - 1; }
    if (s.screen === 'done' && s.inst < 100) u.inst = Math.min(100, s.inst + 7);
""", "")
rep("""  accept() { const s = this.state, ph = this.phone(s); this.setState({ btPhase: 'paired', everPaired: true, trusted: s.trusted.map(t => ({ name: t.name, meta: 'Paired today' })).concat([{ name: ph, meta: 'Connected just now' }]) }); }""",
    """  accept() { live.answer(true); }""")
# The clock and the place: the player's.
rep("""    const nm = s.name.trim() || 'the player', sl = slug(s.name), time = s.fmt ? '9:04 pm' : '21:04';
    const city = (s.loc.split(',')[0] || '').trim() || 'Berlin';""",
    """    const nm = s.name.trim() || 'the player', sl = slug(s.name), time = live.time(s.fmt);
    const city = (s.loc.split(',')[0] || '').trim() || s.town || 'Berlin';""")
# Listen: the server the search found, by its name and address.
rep("found ? { foot: 'Lyrion found on ' + s.net, footMeta: '192.0.2.10:9000' }",
    "found ? { foot: 'Lyrion found on ' + s.net, footMeta: s.lyrMeta }")
# Folders: the Music folder and USB disks are always offered to Lyrion
# (ADR-0115): drawn ticked, as designed, and not a switch that would change
# nothing. Network shares: the player's own search, sign-in and add.
rep("return { title: 'Where is your music?', sub: 'Pick all that apply.', blocks: [list(PLACES.map(p => K(p[1], p[2], s.places[p[0]], tg(p[0]))), 'Lyrion reads')",
    "return { title: 'Where is your music?', sub: 'Pick all that apply.', blocks: [list(PLACES.map(p => K(p[1], p[2], p[0] === 'share' ? s.places.share : true, p[0] === 'share' ? tg(p[0]) : undefined)), 'Lyrion reads')")
rep("""        if (s.places.share) { const ss = s.shareStep, srv = s.shareSrv, addShare = (name, where) => this.setState(st => ({ shares: st.shares.concat([{ name, where }]), shareStep: null, shareAddr: '', shareAU: '', shareAP: '' }));
          const scan = () => { set({ shareStep: 'scan' }); clearTimeout(this.t3); this.t3 = setTimeout(() => { if (this.state.shareStep === 'scan') this.setState({ shareStep: 'list' }); }, 1800); };""",
    """        if (s.places.share) { const ss = s.shareStep, srv = s.shareSrv, addShare = (address, user, password) => live.addShare(address, user, password);
          const scan = () => live.scanShares();""")
rep("""          else if (ss === 'list') extra.push(list([['NAS', '192.0.2.24', true], ['Office-PC', '192.0.2.31', false]].map(v => HB(v[0], v[1], () => set({ shareStep: v[2] ? 'login' : 'browse', shareSrv: v[0] }), { icon: 'fold' })), 'Network shares'),""",
    """          else if (ss === 'list') extra.push(list(s.shareServers.map(v => HB(v.name, v.server?.host || '', () => live.showShares(v), { icon: 'fold' })), 'Network shares'),""")
rep("""            btn('Show shares', () => set({ shareStep: 'browse' })), btn('Back', () => set({ shareStep: 'list' })));""",
    """            btn('Show shares', () => live.showShares(s.shareSrvItem, s.shareUser.trim(), s.sharePw)), btn('Back', () => set({ shareStep: 'list' })));""")
rep("""          else if (ss === 'browse') extra.push(list(['Music', 'Archive'].map(n => HB(n, '//' + srv.toLowerCase() + '/' + n.toLowerCase(), () => addShare('//' + srv.toLowerCase() + '/' + n.toLowerCase(), 'On ' + srv), { icon: 'fold' })), 'Shares on ' + srv),""",
    """          else if (ss === 'browse') extra.push(list(s.shareFound.map(f => HB(f.name, f.address, () => addShare(f.address, s.shareUser.trim() || null, s.sharePw || null), { icon: 'fold' })), 'Shares on ' + srv),""")
rep("""            btn('Add', () => { if (s.shareAddr.trim()) addShare(s.shareAddr.trim(), 'Added by address'); }), btn('Back', () => set({ shareStep: 'list' })));
        }""", """            btn('Add', () => { if (s.shareAddr.trim()) addShare(s.shareAddr.trim(), s.shareAU.trim() || null, s.shareAP || null); }), btn('Back', () => set({ shareStep: 'list' })));
          if (s.shareError) extra.push(note('warn', '', s.shareError));
        }""")
# Plexamp: the player's download, and what it is.
rep("{ k: 'plain', label: 'Plexamp 4.13.2', note: 'From Plex · 112 MB', icon: 'plex' }", "{ k: 'plain', label: 'Plexamp', note: 'From Plex', icon: 'plex' }")
rep("nextFn: () => this.setState({ plexOn: true, plexSkipped: false }, () => this.next()), keep: true } };",
    "nextFn: () => this.setState({ plexOn: true, plexSkipped: false }, () => { live.downloadPlex(); this.next(); }), keep: true } };")
# Bluetooth: the phone that asks, its code, and the player's own list.
rep("        const ph = this.phone(s), sub = 'Any phone can play to ' + nm", "        const ph = s.pairDevice || 'A phone', sub = 'Any phone can play to ' + nm")
rep("fn: () => this.setState(st => ({ trusted: st.trusted.filter(x => x.name !== t.name) })) })), empty: 'No phones paired yet.' }] : [];",
    "fn: () => live.forget(t) })), empty: 'No phones paired yet.' }] : [];")
rep("{ t: 'Code', label: ph + ' wants to pair', code: '418 205', text: 'Check it matches your phone, then accept.' }",
    "{ t: 'Code', label: ph + ' wants to pair', code: s.pairCode, text: 'Check it matches your phone, then accept.' }")
rep("foot: { alt: 'Decline', altFn: () => set({ btPhase: 'disc' }), next: 'Accept', nextFn: () => this.accept(), keep: true } };",
    "foot: { alt: 'Decline', altFn: () => live.answer(false), next: 'Accept', nextFn: () => this.accept(), keep: true } };")
# Plex sign-in: plex.tv opens in its own tab; the code the owner pastes goes
# to Plexamp, and a code it refuses is the design's "run out" state.
rep("        const open = btn('Open plex.tv/claim', () => set({ claimOpened: true, claim: s.claim || 'claim-q7HfK2xR9mWpL4tZ', plexState: 'code' }));",
    "        const open = btn('Open plex.tv/claim', () => { window.open('https://plex.tv/claim', '_blank', 'noopener'); set({ claimOpened: true, plexState: s.plexState === 'expired' ? 'code' : s.plexState }); });")
rep("nextFn: () => { if (s.claim.trim()) set({ plexState: 'ok' }); }, nextOff: !s.claim.trim(), keep: true } };",
    "nextFn: () => { if (s.claim.trim()) live.claim(s.claim.trim()); }, nextOff: !s.claim.trim(), keep: true } };")
# Getting ready: each install as the player follows it (ADR-0128), not a timer.
rep("""      case 'done': { const i = s.inst, items = [];
        if (d.here) { const ld = i >= 50;
          items.push(head('Lyrion'), prog(ld ? 'Installed' : 'Installing', Math.min(100, i * 2), null, ld ? 'Folders added, scan started' : '', true));""",
    """      case 'done': { const items = [];
        if (s.finishError) items.push(note('warn', 'Not saved yet', s.finishError));
        if (d.here) { const lp = live.pct(live.component('lyrion-server.enabled', 'lyrion')), ld = lp >= 100;
          items.push(head('Lyrion'), prog(ld ? 'Installed' : 'Installing', lp, null, ld ? 'Folders added, scan started' : '', true));""")
rep("""        if (!d.headless && s.vizOn) { const vp = Math.min(100, Math.round(i * 1.4));""",
    """        if (!d.headless && s.vizOn) { const vp = live.pct('skins');""")
rep("""        return { hero: true, crumb: 'Make it yours', title: nm + ' is ready', blocks: [{ t: 'Party' }, ...items, { t: 'Rule' },""",
    """        if (live.failed()) items.push(note('warn', 'Something did not finish', 'Try it again from Settings → Plugins. Everything else is set.'));
        return { hero: true, crumb: 'Make it yours', title: nm + ' is ready', blocks: [{ t: 'Party' }, ...items, { t: 'Rule' },""")
rep("""foot: { back: false, next: 'Close' } }; }
      case 'later':""", """foot: s.finishError ? { back: false, next: 'Try again', nextFn: () => live.finish() } : { back: false, next: 'Close' } }; }
      case 'later':""")
# Kept the defaults, asked again from Settings: nothing is changed, so the
# new player's sentence would not be true.
rep("""blocks: [P('Spotify and Bluetooth are on, and nothing else is installed.'),""",
    """blocks: [P(s.first ? 'Spotify and Bluetooth are on, and nothing else is installed.' : 'Nothing was changed.'),""")
# --- Part 1 (setup, over the setup network) ---------------------------------
# The address as the core makes it (`device_name.sanitise`): accents fold,
# the rest becomes hyphens, 63 is one DNS label.
rep("const slug = n => (n || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'gexis';",
    "const slug = n => (n || '').normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 63);")
rep("sl = slug(s.name), time = live.time(s.fmt);", "sl = slug(s.name) || 'gexis', time = live.time(s.fmt);")
# Part 1's screens on the player's own answers: its networks, the backup
# uploaded, the phone's zone, its outputs and screens. The cases keep the
# design's blocks and copy; what is added (a join that failed, a hidden
# network, a cable, an upload's progress, choosing a zone by hand, a screen
# list that did not arrive) is said in the design's own blocks.
a = js.index("      case 'p1welcome':"); b = js.index("\n      case 'listen':")
js = js[:a] + (HERE / "personalise-part1.js.txt").read_text().rstrip("\n") + "\n" + js[b:]
R.append("part 1's cases (personalise-part1.js.txt)")
# **A restore asks the output too** (George, 2026-10-08: "leave the two as
# mandatory steps next to WiFi"): the output, like the screen, is this
# player's hardware, which a backup from another one does not know - a 0.9.5
# restore put guestpi's DAC on a player with another one. The design's own
# Output screen, between the backup and the screen.
rep("['p1welcome', 'p1net', 'p1start', 'p1backup', 'p1screen', 'p1restore', 'p1restored']",
    "['p1welcome', 'p1net', 'p1start', 'p1backup', 'p1output', 'p1screen', 'p1restore', 'p1restored']")
rep("P1B = ['Network', 'Start', 'Screen', 'Review'];", "P1B = ['Network', 'Start', 'Output', 'Screen', 'Review'];")
# Finishing part 1 is the player's: the answers, then /setup/finish; the
# page then waits for the player at its new address (live.finish1).
rep("    if (id === 'p1join') { clearTimeout(this.t2); this.t2 = setTimeout(() => { if (this.state.screen === 'p1join') this.go('listen'); }, 4000); }",
    "    if (id === 'p1join' || id === 'p1restored') live.finish1(id);")
# Each step is saved on the player as it is left, with the step it goes to.
rep("    const s = this.state, d = this.d(s), u = { skipped: Object.assign({}, s.skipped, { [s.screen]: skipped }) };\n    this.setState(u);",
    "    const s = this.state, d = this.d(s), u = { skipped: Object.assign({}, s.skipped, { [s.screen]: skipped }) };\n    this.setState(u);\n"
    "    if (['p1net', 'p1start', 'p1backup', 'p1name', 'p1clock', 'p1output', 'p1screen'].includes(s.screen)) { const p = this.p1Path(s); live.save(s, s.ret || p[p.indexOf(s.screen) + 1] || s.screen); }")
# The frame: the page's own size (the prototype draws it inside a phone or a
# tablet at fixed sizes).
rep("fw: W ? '1100px' : '390px', fh: W ? '700px' : '844px', rad: W ? '22px' : '40px',", "fw: '100%', fh: '100%', rad: '0px',")
out_js = js
script = (HERE / "personalise-adapter.svelte.txt").read_text().replace("/*PROTO*/", out_js)
page = f"""<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
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
{script}

<div style="position:fixed;inset:0;height:100dvh;background:#0c1014;color:#e9eef2;font-family:'Nunito Sans Variable','Nunito Sans','Avenir Next','Segoe UI',system-ui,sans-serif;">
{markup}
</div>
"""
(UI / "FirstUsePage.svelte").write_text(page)
print("replacements:", len(R))


# --- Panel Mini and Phone Device List ---------------------------------------
pm = (D / "Panel Mini.dc.html").read_text()
helmet = re.search(r'<style>(.*?)</style>', pm, re.S).group(1)
body = pm[pm.index('</helmet>') + 9: pm.index('</x-dc>')]
pm_imports = {'artist-photo.webp': 'artistPhoto', 'gexis-mark.svg': 'mark', 'icon-bluetooth.png': 'btIcon', 'icon-lyrion.svg': 'lyrionIcon',
              'icon-spotify.png': 'spotifyIcon', 'wallpapers/calm/c148381086.webp': 'calm'}
pm_markup = convert(body, pm_imports)
logic = pm[pm.index('const KINDS'): pm.index('class Component')]
cls = pm[pm.index('class Component extends DCLogic {') + len('class Component extends DCLogic {'): pm.rindex('}', 0, pm.index('</script>', pm.index('class Component')))]
for a, b in (('  idle(p) {', '  function idle(p) {'), ('  waitHome(p) {', '  function waitHome(p) {'), ('  renderVals() {', '  function renderVals(p) {'),
             ('const p = this.props, kind', 'const kind'), ('...this.idle(p), ...this.waitHome(p)', '...idle(p), ...waitHome(p)'),
             ("p.wallSrc || 'wallpapers/calm/c148381086.webp'", 'p.wallSrc || calm')):
    assert cls.count(a) == 1, a
    cls = cls.replace(a, b)
(UI / "personalise/PanelMini.svelte").write_text(f"""<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The panel in miniature** (ADR-0149). GENERATED from Claude Design's
  `Panel Mini.dc.html` (design/source/14-first-use) by
  `tools/design/gen_personalise.py`: its markup, inline styles, keyframes
  and logic as designed. Change the design, then generate again.
-->
<script>
  import artistPhoto from '../../assets/personalise/artist-photo.webp';
  import calm from '../../assets/personalise/calm.webp';
  import mark from '../../assets/gexis-mark.svg';
  import lyrionIcon from '../../assets/icon-lyrion.svg';
  import spotifyIcon from '../../assets/icon-spotify.png';
  import btIcon from '../../assets/icon-bluetooth.png';

  let p = $props();

{logic}
{cls}
  const V = $derived(renderVals(p));
</script>

{pm_markup}
<style>
  :global {{
{helmet}
  }}
</style>
""")
dl = (D / "Phone Device List.dc.html").read_text()
(UI / "personalise/PhoneDeviceList.svelte").write_text("""<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- GENERATED from Claude Design's `Phone Device List.dc.html` (design/source/14-first-use)
     by `tools/design/gen_personalise.py`: Spotify's device list, the player in it. -->
<script>
  let { device = 'Living Room' } = $props();
  const V = $derived({ device });
</script>
""" + convert(dl[dl.index('<x-dc>') + 6: dl.index('</x-dc>')]))
print("generated FirstUsePage, PanelMini, PhoneDeviceList")
