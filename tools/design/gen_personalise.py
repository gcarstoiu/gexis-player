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
# Getting ready's scene is PanelMini's flow (above, in the script's
# replacements): the Party block's drawing gives way to it.
i = markup.index("{#if b.isParty}")
j = markup.index("{/if}", i)
assert "{#if" not in markup[i + 15:j], "the Party block has no conditions inside"
markup = markup[:i] + "{#if b.isParty}\n                  <PanelMini kind=\"flow\" marks={b.marks} status={b.status} />\n                " + markup[j:]
# **A password can be shown while it is typed** (George, 2026-10-18: "Had to
# rewrite the password multiple times because i was afraid I misspelled"):
# the design's field gets an eye on its right when it holds a password.
a2 = """<input type={b.type} value={b.value} placeholder={b.ph} oninput={b.onChange} readonly={b.ro} style="width:100%;height:56px;border-radius:14px;background:rgba(8,12,16,0.6);border:1px solid rgba(233,238,242,0.18);padding:0 18px;"""
assert markup.count(a2) == 1, "the field's input"
i = markup.index(a2)
j = markup.index("/>", i) + 2
inp = markup[i:j].replace("<input type={b.type}", "<input type={b.type === 'password' && pwShown ? 'text' : b.type}").replace(
    "padding:0 18px;", "padding:0 {b.type === 'password' ? '60px' : '18px'} 0 18px;")
markup = markup[:i] + """<div style="position:relative;">""" + inp + """{#if b.type === 'password'}<button type="button" aria-label={pwShown ? 'Hide the password' : 'Show the password'} aria-pressed={pwShown} onclick={() => (pwShown = !pwShown)} style="position:absolute;right:6px;top:5px;width:46px;height:46px;border:0;border-radius:12px;background:transparent;color:rgba(233,238,242,0.7);display:grid;place-items:center;cursor:pointer;"><svg viewBox="0 0 24 24" aria-hidden="true" style="width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" />{#if pwShown}<path d="M4 4l16 16" />{/if}</svg></button>{/if}</div>""" + markup[j:]
# The previews carry the Touchpad step's pointer (PanelMini's `pointer`).
for which in ("V.pv", "V.sidePv"):
    tag = f"phone={{{which}.phone}} />"
    assert markup.count(tag) == 1, tag
    markup = markup.replace(tag, f"phone={{{which}.phone}} pointer={{{which}.pointer}} />")
# A Split with nothing on its right (a backup's sections, ADR-0131 amended
# 2026-10-18) is the left column alone: the design's ticked list.
right = '<div style="padding:14px;background:rgba(255,255,255,0.03);display:flex;flex-direction:column;gap:9px;border-top:1px solid rgba(233,238,242,0.1);">'
assert markup.count(right) == 1, "Split's right column"
i = markup.index(right)
j = markup.index("{/each}", i)
j = markup.index("</div>", j) + len("</div>")
markup = markup[:i] + "{#if b.right.length}" + markup[i:j] + "{/if}" + markup[j:]
# The tick box is a tap target of its own when the row opens something
# else (`onTick`), 48 px square around the 24 px box.
box = '<span style="width:24px;height:24px;border-radius:7px;box-sizing:border-box;flex-shrink:0;align-items:center;justify-content:center;display:{o.chkDisplay};background:{o.boxBg};border:2px solid {o.ring};">'
assert markup.count(box) == 1, "the tick box"
i = markup.index(box)
j = markup.index("</span>", markup.index("</span>", i) + 7) + 7
inner = markup[i:j].replace("display:{o.chkDisplay};", "display:flex;")
markup = (markup[:i] + '<span onclick={(e) => { if (o.onTick) { e.stopPropagation(); o.onTick(); } }} style="display:{o.chkDisplay};padding:12px;margin:-12px;flex-shrink:0;">'
          + inner + "</span>" + markup[j:])
# A long list of folders scrolls inside itself, about six rows high, so the
# Add button under it stays in reach (George, 2026-10-18: 499 folders meant
# scrolling "an apparently endless screen" to it). The rows' own wrapper.
li = markup.index("{#if b.isList}")
ea = markup.index("{#each b.rows as o}", li)
depth, k = 0, ea
while True:  # the {/each} that closes this one, past any inside the row
    nxt_open, nxt_close = markup.find("{#each", k + 1), markup.find("{/each}", k + 1)
    if nxt_open != -1 and nxt_open < nxt_close:
        depth, k = depth + 1, nxt_open
    elif depth:
        depth, k = depth - 1, nxt_close
    else:
        ee = nxt_close + len("{/each}")
        break
markup = markup[:ea] + '<div style="display:flex;flex-direction:column;gap:6px;{b.scrollStyle}">' + markup[ea:ee] + "</div>" + markup[ee:]
# A subgroup heading, as Settings draws one (`.subhead`: a dot, the name in
# mono capitals in its colour, a rule to the edge) - George, 2026-10-18:
# the groups of Where is your music? named "like the Settings subgroups".
rule_at = markup.index("{#if b.isRule}")
markup = markup[:rule_at] + ("""{#if b.isSub}
                  <div style="display:flex;align-items:center;gap:14px;padding:22px 2px 8px;">
                    <span style="width:9px;height:9px;border-radius:50%;flex-shrink:0;background:{b.accent};"></span>
                    <span style="font-family:'IBM Plex Mono','Courier New',monospace;font-size:13px;letter-spacing:0.2em;text-transform:uppercase;flex-shrink:0;color:{b.accent};">{b.text}</span>
                    <span style="flex:1;height:1px;background:rgba(233,238,242,0.1);"></span>
                  </div>
                {/if}

                """) + markup[rule_at:]
# The Dev block's heading is the block's own (George, 2026-10-18: added
# shares get the Forget paired phones have), "Trusted devices" by default.
assert markup.count(">Trusted devices<") == 1
markup = markup.replace(">Trusted devices<", ">{b.head}<")
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
rep("""          if (s.shares.length && !ss) extra.push(list(s.shares.map(a => ({ k: 'plain', label: a.name, note: a.where, tag: ['Added', 'ok'] })), 'Network shares'));""",
    """          if (s.shares.length && !ss) extra.push({ t: 'Dev', head: 'Added', items: s.shares.map(a => ({ name: a.name, meta: a.where, fn: () => live.forgetShare(a.address) })), empty: '' });""")
# A row that both opens (the row) and ticks (its box): folders on shares
# and drives (George, 2026-10-18, "Tick several").
rep("sel = (radio || net || k === 'chk') && o.on;", "sel = (radio || net || k === 'chk' || k === 'pick') && o.on;")
rep("onClick: o.fn || noop, cursor: o.fn ? 'pointer' : 'default',", "onClick: o.fn || (k === 'pick' ? o.tick : null) || noop, onTick: k === 'pick' && o.fn ? o.tick : null, cursor: o.fn || o.tick ? 'pointer' : 'default',")
rep("chkDisplay: k === 'chk' ? 'flex' : 'none',", "chkDisplay: k === 'chk' || k === 'pick' ? 'flex' : 'none',")
rep("chevDisplay: k === 'hub' ? 'block' : 'none'", "chevDisplay: k === 'hub' || (k === 'pick' && o.fn) ? 'block' : 'none'")
rep("const BTYPES = ['List',", "const BTYPES = ['Sub', 'List',")
rep("  if (b.t === 'List') o.rows = b.rows.map(row);", "  if (b.t === 'List') { o.rows = b.rows.map(row); o.scrollStyle = b.rows.length > 6 ? 'max-height:430px;overflow-y:auto;overscroll-behavior:contain;padding-right:4px;' : ''; }")
rep("  if (b.t === 'P' || b.t === 'Head') o.text = b.text;", "  if (b.t === 'P' || b.t === 'Head') o.text = b.text;\n  if (b.t === 'Sub') { o.text = b.text; o.accent = b.accent; }")
rep("  if (b.t === 'Dev') { o.items = ", "  if (b.t === 'Dev') { o.head = b.head || 'Trusted devices'; o.items = ")
rep("    if (id === 'done') this.setState({ inst: 0 });", "    if (id === 'done') live.finish();\n    if (id === 'later') live.later();\n    if (id === 'bluetooth') live.trusted();\n    if (id === 'folders') { live.loadShares(); live.loadUsb(); live.loadSpace(); }")
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
# Folders (ADR-0115 decisions 20-23, George 2026-10-18): the three switches,
# each followed by its own actions with a rule between the sources (George:
# "Look again" for USB must not sit under the network share), each group
# headed as its row is named in Settings -> Lyrion Server (George: "a name
# similar to what we have in settings for subgroups");
# as designed, none on ("Nothing should be preselected"), and with USB drives
# on, the drives plugged in, each browsed for the folders Lyrion reads. With
# nothing chosen the line under the list says Lyrion starts empty.
rep("return { title: 'Where is your music?', sub: 'Pick all that apply.', blocks: [list(PLACES.map(p => K(p[1], p[2], s.places[p[0]], tg(p[0]))), 'Lyrion reads'), ...extra, P('These become Lyrion’s music folders when it installs.')]",
    "return { title: 'Where is your music?', sub: 'Pick all that apply.', blocks: [sub('Music folder'), list([placeRow(PLACES[0])], ''), sub('USB drives'), list([placeRow(PLACES[1])], ''), ...usbBlocks, sub('Network shares'), list([placeRow(PLACES[2])], ''), ...extra, { t: 'Rule' }, (s.places.folder || s.places.usb || s.places.share) ? P('These become Lyrion’s music folders when it installs.') : note('info', 'Nothing chosen yet', 'Lyrion then starts with no music. Locations can be added later in Settings → Sources → Lyrion Server.')]")
rep("places: { folder: true, usb: false, share: false }", "places: { folder: false, usb: false, share: false }, usbDrives: [], usbOpen: null, usbError: null")
rep("""      case 'folders': { const tg = k => () => this.setState(st => ({ places: Object.assign({}, st.places, { [k]: !st.places[k] }) })), extra = [];""",
    """      case 'folders': { const tg = k => () => { this.setState(st => ({ places: Object.assign({}, st.places, { [k]: !st.places[k] }) })); if (k === 'usb') live.loadUsb(); }, extra = [], usbBlocks = [];
        const sub = text => ({ t: 'Sub', text, accent: C.fold });
        const placeRow = p => p[0] === 'usb' && !s.usbDrives.length ? { k: 'ghost', label: p[1], note: 'No USB drive plugged in.' }
          : K(p[1], p[0] === 'folder' && s.musicSpace ? p[2] + ' ' + s.musicSpace + '.' : p[2], s.places[p[0]], tg(p[0]));
        // George, 2026-10-18: with no drive plugged in, USB cannot be chosen
        // (the design's ghost row) until one is, and Look again finds it.
        if (!s.usbDrives.length) usbBlocks.push(btn('Look again for a USB drive', () => live.loadUsb()));
        // George, 2026-10-18 ("Tick several"): a box on each drive and
        // folder ticks it, the row opens it; the path above goes back up;
        // one button adds what is ticked.
        else if (s.places.usb) { const o = s.usbOpen, n = live.picked('usb').length;
          if (o) usbBlocks.push(live.crumbs(o.crumbs, c => c.top ? set({ usbOpen: null }) : live.openUsb(c.drive, c.folder)),
            list(o.items.map(i => live.pickRow('usb', i, () => live.openUsb(i.drive, i.folder))), ''),
            ...(o.items.length ? [] : [P('No folders inside.')]));
          else usbBlocks.push(list(s.usbDrives.map(d => live.pickRow('usb', { name: d.name, meta: d.meta, drive: d.drive, folder: '' }, () => live.openUsb(d.drive, ''))), 'Plugged in'),
            P('Tick a drive to add all of it, or open it to tick folders inside.'));
          if (n) usbBlocks.push(btn('Add ' + n + (n === 1 ? ' folder' : ' folders'), () => live.addPicked('usb')));
          if (s.usbError) usbBlocks.push(note('warn', '', s.usbError));
        }""")
rep("""        if (s.places.share) { const ss = s.shareStep, srv = s.shareSrv, addShare = (name, where) => this.setState(st => ({ shares: st.shares.concat([{ name, where }]), shareStep: null, shareAddr: '', shareAU: '', shareAP: '' }));
          const scan = () => { set({ shareStep: 'scan' }); clearTimeout(this.t3); this.t3 = setTimeout(() => { if (this.state.shareStep === 'scan') this.setState({ shareStep: 'list' }); }, 1800); };""",
    """        if (s.places.share) { const ss = s.shareStep, srv = s.shareSrv, addShare = (address, user, password) => live.addShare(address, user, password);
          const scan = () => live.scanShares();""")
rep("""          else if (ss === 'list') extra.push(list([['NAS', '192.0.2.24', true], ['Office-PC', '192.0.2.31', false]].map(v => HB(v[0], v[1], () => set({ shareStep: v[2] ? 'login' : 'browse', shareSrv: v[0] }), { icon: 'fold' })), 'Network shares'),""",
    """          else if (ss === 'list') extra.push(list(s.shareServers.map(v => HB(v.name, v.server?.host || '', () => live.showShares(v), { icon: 'fold' })), 'On your network'),""")
rep("""            btn('Show shares', () => set({ shareStep: 'browse' })), btn('Back', () => set({ shareStep: 'list' })));""",
    """            btn('Show shares', () => live.showShares(s.shareSrvItem, s.shareUser.trim(), s.sharePw)), btn('Back', () => set({ shareStep: 'list' })));""")
rep("""          else if (ss === 'browse') extra.push(list(['Music', 'Archive'].map(n => HB(n, '//' + srv.toLowerCase() + '/' + n.toLowerCase(), () => addShare('//' + srv.toLowerCase() + '/' + n.toLowerCase(), 'On ' + srv), { icon: 'fold' })), 'Shares on ' + srv),""",
    """          else if (ss === 'folder') { const o = s.shareFolder, n = live.picked('share').length;
            extra.push(live.crumbs(o.crumbs, c => c.server ? set({ shareStep: 'browse' }) : live.openShareFolder(c.address)),
              list(o.items.map(i => live.pickRow('share', i, () => live.openShareFolder(i.address))), ''),
              ...(o.items.length ? [] : [P('No folders inside.')]),
              ...(n ? [btn('Add ' + n + (n === 1 ? ' folder' : ' folders'), () => live.addPicked('share'))] : []),
              btn('Back to the shares', () => set({ shareStep: 'browse' }))); }
          else if (ss === 'browse') extra.push(list(s.shareFound.map(f => live.pickRow('share', { name: f.name, meta: f.address, address: f.address }, f.address.startsWith('//') ? () => live.openShareFolder(f.address) : null)), 'Shares on ' + srv),
            ...(live.picked('share').length ? [btn('Add ' + live.picked('share').length + (live.picked('share').length === 1 ? ' folder' : ' folders'), () => live.addPicked('share'))] : []),""")
# George, 2026-10-18: an SMB share opens into its folders, at any depth.
rep("P('Tap one to add it.'), btn('Back', () => set({ shareStep: 'list' })));", "P('Tick a share to add all of it, or open it to tick folders inside.'), btn('Back', () => set({ shareStep: 'list' })));")
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
# **Touchpad, before the visualiser** (George, 2026-10-18: "the touchpad
# enable or disable. No additional settings added, just a note ... saying
# where more settings around the touchpad are and what these settings are").
# Built from the design's own parts: the toggle row (T) of the Spotify step,
# an info note, and the panel preview - the library with the player's
# teal pointer gliding and tapping (PanelMini's `pointer`, below). Its colour
# is the one in the design's palette (C.ext) no step used.
rep("    if (!d.headless) p.push('visualiser', ...(d.wait ? ['wait'] : []), 'idle', 'standby');",
    "    if (!d.headless) p.push('touchpad', 'visualiser', ...(d.wait ? ['wait'] : []), 'idle', 'standby');")
rep("bluetooth: ['Bluetooth', C.bt], visualiser:", "bluetooth: ['Bluetooth', C.bt], touchpad: ['Touchpad', C.ext], visualiser:")
rep("bluetooth: 'Bluetooth', visualiser:", "bluetooth: 'Bluetooth', touchpad: 'Touchpad', visualiser:")
rep("bluetooth: '5A6', visualiser:", "bluetooth: '5A6', touchpad: '5A6t', visualiser:")
rep("      case 'visualiser': { const k = s.skin,", """      case 'touchpad': return { title: 'Touchpad on your phone', sub: 'In the phone’s volume sheet: move a pointer on ' + nm + '’s screen, tap, type, scroll with two fingers and pinch to zoom.', pv: pv({ kind: 'lib', pointer: s.touchpad }),
        blocks: [list([T('Phone touchpad', '', s.touchpad, flip('touchpad'))]), note('info', 'More in Settings', s.touchpad ? 'Display → Touchpad: Pointer speed, how far the pointer moves for a finger’s movement, and Pointer style, a dot or an arrow.' : 'Display → Touchpad turns it on again, with its pointer speed and style.')], foot: SK };
      case 'visualiser': { const k = s.skin,""")
# **Getting ready: the opening animation, and where things stand** (George,
# 2026-10-18: "take the animation we have at the beginning of the flow on
# wide and replace the current one, adding the status icon next to the
# panel"; "the sources from the animation should match the selection").
# The Party scene gives way to PanelMini's `flow` - the wide layout's
# *How will you listen?* - cycling through the sources chosen, with a
# badge on the panel's corner: the design's check once everything is in,
# a turning ring while anything downloads or installs, an amber ! when
# something did not finish. The title says the same.
rep("""        if (live.failed()) items.push(note('warn', 'Something did not finish', 'Try it again from Settings → Plugins. Everything else is set.'));
        return { hero: true, crumb: 'Make it yours', title: nm + ' is ready', blocks: [{ t: 'Party' },""",
    """        if (live.failed()) items.push(note('warn', 'Something did not finish', 'Try it again from Settings → Plugins. Everything else is set.'));
        const waiting = !s.finished || (d.here && live.pct(live.component('lyrion-server.enabled', 'lyrion')) < 100) || (d.plex && s.plexOn && s.plexPct < 100) || (!d.headless && s.vizOn && live.pct('skins') < 100);
        const state = s.finishError ? 'busy' : live.failed() ? 'warn' : waiting ? 'busy' : 'done';
        return { hero: true, crumb: 'Make it yours', title: state === 'done' ? nm + ' is ready' : state === 'warn' ? nm + ' is nearly ready' : 'Getting ' + nm + ' ready', blocks: [{ t: 'Party', marks: d.marks, status: state },""")
rep("""  if (b.t === 'Code') Object.assign(o, { label: b.label, code: b.code, text: b.text });""",
    """  if (b.t === 'Code') Object.assign(o, { label: b.label, code: b.code, text: b.text });
  if (b.t === 'Party') Object.assign(o, { marks: b.marks, status: b.status });""")
# **Personalise lives in Display** (George, 2026-10-18: "since most of the
# settings from Personalisation are display related, let's move the setting
# to Display category").
rep("Settings → System → Personalise", "Settings → Display → Personalise", n=2)
# **Picking the minutes closes the time picker** (George, 2026-10-18: the
# choice should be seen before going on): the time shows in its button.
rep("quarters: QUARTERS.map(x => cell(':' + x, x === mm, () => setT('m', x))),",
    "quarters: QUARTERS.map(x => cell(':' + x, x === mm, () => { setT('m', x); this.setState({ ivPick: null }); })),")
# The frame: the page's own size (the prototype draws it inside a phone or a
# tablet at fixed sizes).
rep("fw: W ? '1100px' : '390px', fh: W ? '700px' : '844px', rad: W ? '22px' : '40px',", "fw: '100%', fh: '100%', rad: '0px',")
# **Getting ready says what each download is doing** (George, 2026-10-18:
# "Even if a download is at 100% but there is an install coming after then
# this should be transparent to the user. Same with starting a download"):
# each item's line, bar and right-hand word from the player's live status
# (live.stage) - starting, preparing, downloading with its MB, retrying,
# checking, installing, installed, did not finish.
a = js.index("      case 'done': { const items = [];")
b = js.index("        const state = ", a)
b = js.index("\n", b) + 1
js = js[:a] + """      case 'done': { const items = [], got = [];
        if (s.finishError) items.push(note('warn', 'Not saved yet', s.finishError));
        const show = (name, id, doneLine, doneOk, after) => { const g = live.stage(id); got.push(g);
          items.push(head(name), prog(g.label, g.pct, g.meta, g.done ? doneLine : g.line, g.done ? doneOk : false));
          if (g.done && after) items.push(note('info', '', after)); };
        if (d.here) { const any = s.places.folder || s.places.usb || s.places.share;
          show('Lyrion', live.component('lyrion-server.enabled', 'lyrion'), any ? 'Folders added, scan started' : 'Installed, no music yet', true,
            any ? 'A large library can take hours to scan. Music shows up as Lyrion finds it.' : 'Add where your music is in Settings → Sources → Lyrion Server.'); }
        if (d.plex && s.plexOn) { const ok = s.plexState === 'ok';
          show('Plexamp', live.component('plexamp.enabled', 'plexamp'), ok ? 'Signed in to Plex' : 'Not signed in yet', ok, ok ? 'Your Plex library plays from the Plexamp app.' : 'Sign in from Settings → Plexamp when you’re ready.'); }
        if (!d.headless && s.vizOn) show('Visualiser', 'skins', 'Skins ready', true, 'The visualiser starts after ' + s.vizAfter + ' of music.');
        const failedAny = got.some(g => g.failed);
        if (failedAny) items.push(note('warn', 'Something did not finish', 'Try it again from Settings → Plugins. Everything else is set.'));
        const waiting = !s.finished || got.some(g => !g.done && !g.failed);
        const state = s.finishError ? 'busy' : failedAny ? 'warn' : waiting ? 'busy' : 'done';
""" + js[b:]
R.append("Getting ready's lines from live.stage")
# **Plexamp is one screen** (George, 2026-10-18: "basically everything
# happens in one screen not two"): the download and the sign-in together,
# the download's stage at the top (live.stage), the claim code under it. And
# **signed in is asked, not assumed** ("verify if Plexamp is claimed
# unimportant if that happened during the setup flow or it was done in the
# past"): already claimed, the step says so and asks for nothing; a code
# pasted waits for Plexamp to sign in (plexState 'checking').
a = js.index("      case 'plexamp': {")
b = js.index("      case 'browse':", a)
js = js[:a] + """      case 'plexamp': {
        const sub = 'Your Plex library, played on ' + nm + '.';
        const g = live.stage(live.component('plexamp.enabled', 'plexamp')), inst = g.done;
        const dl = prog(inst ? 'Plexamp is installed' : g.label, g.pct, g.meta, inst ? '' : g.line);
        if (s.plexClaimed) return { title: 'Plexamp', sub, blocks: [dl, status('ok', nm + ' is on your Plex account', 'Signed in to Plex'), P('Open Plexamp on your phone and pick ' + nm + ' as the player.')] };
        if (!s.plexOn && !inst) return { title: 'Plexamp', sub, blocks: [list([{ k: 'plain', label: 'Plexamp', note: 'From Plex', icon: 'plex' }]), num([['Download Plexamp', 'next'], ['Sign in to Plex with a claim code', 'next']]), P('Skip, and add Plexamp later from Settings → Plugins.')],
          foot: { alt: 'Skip', altFn: () => this.setState({ plexSkipped: true, plexState: 'later' }, () => this.skip()), next: 'Download', nextFn: () => this.setState({ plexOn: true, plexSkipped: false }, () => live.downloadPlex()), keep: true } };
        const later = () => this.setState({ plexState: 'later' }, () => this.skip());
        const skipP = P('Or skip, and sign in later from Settings → Plugins → Plexamp.' + (inst ? '' : ' The download carries on.'));
        const open = btn('Open plex.tv/claim', () => { window.open('https://plex.tv/claim', '_blank', 'noopener'); set({ claimOpened: true, plexState: s.plexState === 'expired' ? 'code' : s.plexState }); });
        if (s.plexState === 'checking') return { title: 'Plexamp', sub, blocks: [dl, status('spin', 'Signing in to Plex', 'A few seconds')], foot: { alt: 'Skip', altFn: later, next: 'Next', nextOff: true, keep: true } };
        if (!inst) return { title: 'Plexamp', sub, blocks: [dl, open, note('info', '', 'A claim code lasts four minutes. Paste it here once Plexamp is installed.'), field('Claim code', '', noop, { ph: 'Opens once Plexamp is installed', ro: true }), skipP], foot: { alt: 'Skip', altFn: later, next: 'Claim', nextOff: true, keep: true } };
        const code = field('Claim code', s.claim, e => set({ claim: e.target.value }), { ph: 'claim-…' });
        const blocks = s.plexState === 'expired' ? [dl, note('warn', s.plexError ? 'The claim did not work' : 'That code has run out', s.plexError || 'Claim codes last four minutes. Get a new one and paste it straight away.'), open, code]
          : [dl, open, note('info', '', 'Get a claim code from plex.tv, then paste it here within four minutes.'), code, skipP];
        return { title: 'Plexamp', sub, blocks, foot: { alt: 'Skip', altFn: later, next: 'Claim', nextFn: () => { if (s.claim.trim()) live.claim(s.claim.trim()); }, nextOff: !s.claim.trim(), keep: true } };
      }
""" + js[b:]
a = js.index("      case 'plexsign': {")
b = js.index("      case 'review': {", a)
js = js[:a] + js[b:]
assert js.count("if (d.plex) { p.push('plexamp'); if (!s.plexSkipped) p.push('plexsign'); }") == 1
js = js.replace("if (d.plex) { p.push('plexamp'); if (!s.plexSkipped) p.push('plexsign'); }", "if (d.plex) p.push('plexamp');")
assert js.count("const ok = s.plexState === 'ok';") == 1
js = js.replace("const ok = s.plexState === 'ok';", "const ok = s.plexClaimed;")
R.append("Plexamp on one screen, signed in asked of the plugin")
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
{{#if st.shown}}
{markup}
{{/if}}
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
# **Today's date, not the design's sample** (Thursday 15 October): the
# clock beside it is the player's own.
n = pm_markup.count('>Thursday 15 October<')
assert n >= 1
pm_markup = pm_markup.replace('>Thursday 15 October<', '>{today()}<')
assert pm_markup.count('>Thursday · 15 October<') == 1
pm_markup = pm_markup.replace('>Thursday · 15 October<', ">{today(' · ')}<")
pm_extra_today = """
  function today(sep = ' ') {
    const d = new Date();
    return d.toLocaleDateString('en-GB', { weekday: 'long' }) + sep + d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long' });
  }
"""

# **The waiting screen as the panel now draws it** (George, 2026-10-18): the
# sources are the library's pulsing marks straight on the picture - no
# tiles, no plate - and the line "Start music from your phone" is gone.
for a2, b2 in (
    ('<div style="font-size:1.4844cqw;color:rgba(233,238,242,0.88);text-shadow:0 1px 12px rgba(0,0,0,0.45);">Start music from your phone</div>\n', ''),
    ('grid-template-columns:repeat({V.wCols}, minmax(0,1fr));gap:1.25cqw;', 'grid-template-columns:repeat({V.wCols}, minmax(0,1fr));gap:1.25cqw;justify-items:center;'),
    ('<div style="height:10.3125cqw;box-sizing:border-box;border-radius:1.875cqw;padding:0 1.7188cqw;display:flex;align-items:center;gap:1.4063cqw;min-width:0;background:rgba(16,26,33,0.72);border:1px solid {m.border};">',
     '<div style="display:flex;flex-direction:column;align-items:center;gap:0.9375cqw;min-width:0;max-width:100%;">'),
    ('<div style="width:5.625cqw;height:5.625cqw;flex-shrink:0;border-radius:50%;display:flex;align-items:center;justify-content:center;background:{m.markBg};">',
     '<div style="position:relative;width:5.625cqw;height:5.625cqw;flex-shrink:0;border-radius:50%;display:flex;align-items:center;justify-content:center;background:{m.markBg};"><span style="position:absolute;inset:-0.47cqw;border-radius:50%;border:0.16cqw solid {m.border};animation:npRing 2800ms ease-out infinite;"></span>'),
    ('<div style="flex:1;min-width:0;">', '<div style="min-width:0;max-width:100%;text-align:center;text-shadow:0 1px 8px rgba(0,0,0,0.6);">'),
):
    assert pm_markup.count(a2) == 1, a2[:60]
    pm_markup = pm_markup.replace(a2, b2)

# **The flow shows the sources chosen** (Getting ready): each source's turn
# is its own cycle - Lyrion, Plexamp, Spotify, Bluetooth, 3 s each over 12 s
# - and with `marks` only the chosen ones take turns, 3 s each still.
for src, delay in (("lyr", "0s"), ("plex", "-9s"), ("spo", "-6s"), ("bt", "-3s")):
    a2 = f"animation:fuCycle 12s linear {delay} infinite;"
    assert pm_markup.count(a2) == 1, a2
    pm_markup = pm_markup.replace(a2, f"animation:{{flowAnim('{src}')}};display:{{flowShow('{src}')}};")
end2 = pm_markup.rstrip().rindex("</div>")
pm_markup = pm_markup[:end2] + """  {#if p.kind === 'flow' && p.status}
    <div style="position:absolute;left:61.4cqw;top:2.9cqw;z-index:4;width:8.2cqw;height:8.2cqw;border-radius:50%;box-sizing:border-box;display:flex;align-items:center;justify-content:center;font-size:4.6cqw;font-weight:800;line-height:1;box-shadow:0 0 0 1cqw #0d151b;background:{p.status === 'done' ? '#7ed6bc' : p.status === 'warn' ? '#e0a758' : '#0d151b'};color:#0d151c;border:{p.status === 'busy' ? '0.3cqw solid rgba(126,214,188,0.55)' : 'none'};">
      {#if p.status === 'done'}✓{:else if p.status === 'warn'}!{:else}<span style="width:5cqw;height:5cqw;border-radius:50%;border:0.75cqw solid rgba(233,238,242,0.16);border-top-color:#7ed6bc;box-sizing:border-box;display:block;animation:fuSpin 0.9s linear infinite;"></span>{/if}
    </div>
  {/if}
""" + pm_markup[end2:]
helmet += """
  @keyframes fuCycle1{0%,100%{opacity:1;}}
  @keyframes fuCycle2{0%,44%{opacity:1;}50%,94%{opacity:0;}100%{opacity:1;}}
  @keyframes fuCycle3{0%,29.3%{opacity:1;}33.3%,96%{opacity:0;}100%{opacity:1;}}
"""
logic_extra = pm_extra_today + """
  // The flow's sources: all four in turn (How will you listen?), or the
  // ones chosen (Getting ready), 3 s each.
  const FLOW = ['lyr', 'plex', 'spo', 'bt'], FLOW_DELAY = { lyr: '0s', plex: '-9s', spo: '-6s', bt: '-3s' };
  function flowShow(src) { return !p.marks || p.marks.includes(src) ? 'block' : 'none'; }
  function flowAnim(src) {
    if (!p.marks) return `fuCycle 12s linear ${FLOW_DELAY[src]} infinite`;
    const chosen = FLOW.filter((x) => p.marks.includes(x)), n = chosen.length, k = chosen.indexOf(src);
    if (k < 0) return 'none';
    const name = n >= 4 ? 'fuCycle' : `fuCycle${n}`;
    return `${name} ${3 * n}s linear ${k === 0 ? 0 : 3 * k - 3 * n}s infinite`;
  }
"""
# **The phone's pointer, on the panel** (the Touchpad step's preview): the
# player's own dot (PanelPointer's: teal, a dark rim) glides over the
# library's tiles and taps - it shrinks as the real one does on a press -
# with the tap ring the design draws for a tap (fuRing's rise and fade).
# Positions are the library's (kLib): 12 % / 9 % inset, five tiles a row.
end = pm_markup.rstrip().rindex("</div>")
pm_markup = pm_markup[:end] + """  {#if p.pointer}
    <div style="position:absolute;inset:0;z-index:30;pointer-events:none;">
      <span style="position:absolute;width:4.6cqw;height:4.6cqw;margin:-2.3cqw 0 0 -2.3cqw;animation:tpMove 6.4s cubic-bezier(0.45,0,0.25,1) infinite;">
        <span style="position:absolute;inset:0;border-radius:999px;border:0.55cqw solid #7ed6bc;box-sizing:border-box;opacity:0;animation:tpRing 6.4s ease-out infinite;"></span>
        <span style="position:absolute;inset:0;border-radius:999px;background:#7ed6bc;border:0.45cqw solid #0c1014;box-sizing:border-box;animation:tpPress 6.4s ease-out infinite;"></span>
      </span>
    </div>
  {/if}
""" + pm_markup[end:]
helmet += """
  @keyframes tpMove{0%{left:74%;top:84%;}20%,32%{left:32.8%;top:27%;}50%,62%{left:67.2%;top:27%;}80%,90%{left:40%;top:82%;}100%{left:74%;top:84%;}}
  @keyframes tpPress{0%,21%,27%,51%,57%,81%,87%,100%{transform:scale(1);}24%,54%,84%{transform:scale(0.7);}}
  @keyframes tpRing{0%,23%{transform:scale(0.8);opacity:0;}24%{opacity:0.95;}36%{transform:scale(2.6);opacity:0;}53%{transform:scale(0.8);opacity:0;}54%{opacity:0.95;}66%{transform:scale(2.6);opacity:0;}83%{transform:scale(0.8);opacity:0;}84%{opacity:0.95;}96%{transform:scale(2.6);opacity:0;}100%{opacity:0;}}
"""
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

{logic}{logic_extra}
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
