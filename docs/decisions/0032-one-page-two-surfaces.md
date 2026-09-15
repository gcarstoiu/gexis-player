# ADR-0032 — One page, two surfaces: the panel gets everything, a remote browser gets settings

**Status:** Accepted
**Date:** 2026-09-15
**Raised by:** George, reviewing a Claude Design proposal
**Amends:** `docs/DEVELOPMENT.md` Phase 4 criterion 5 (clarified, not broken),
`docs/ARCHITECTURE.md`'s one-codebase line

## The problem

The interface is designed against a fixed 1280x800 artboard and was not built
to be progressive. Served unchanged to a phone it would look broken.

Claude Design proposed a **split by capability**: the panel keeps playback and
browsing; the phone gets settings, Wi-Fi setup, pairing and the typing-heavy
library paths, plus a compact now-playing strip. Deliberately not parity.

## Decision

**Not that split. The inverse, which is simpler and stronger:**

- **The panel renders everything**, settings included. It remains
  self-sufficient.
- **A remote browser renders only the settings surface.** No now-playing
  strip, no browse, no transport (George, 2026-09-15: *"No strip…just
  settings"*).
- **It is the same page on both** (George, 2026-09-15). One codebase, one
  served page; the phone renders a subset of it.

### Why the inverse is better than the proposal

The split-by-capability version would have made some functions phone-only, and
**the phone exists only while the LAN does**. If Wi-Fi breaks, the phone cannot
reach the device at all and the panel is the only surface left — so anything
needed to recover the device must never live solely on the phone. Under
capability-split that had to be enforced as a rule and policed. Under this
decision the problem does not arise: the panel has everything, so nothing is
phone-only, and the phone is pure convenience.

The right frame for self-sufficiency is not parity. **The panel does not need
the phone's conveniences; it needs to be able to recover the device.** It can.

## Settings is one responsive component

`Settings.dc.html`, no fixed widths, imported by the panel into the area its
settings overlay occupies now and served standalone to a phone. One file, one
inventory, one set of row types — **a setting added once appears on both.**

**The breakpoint is measured, not declared.** The component observes its own
mount width, because it is embedded on the panel and standalone on the phone;
a viewport media query would be wrong in the embedded case.

- **≥ 720px** — the current two-pane layout: category rail left, rows right.
- **< 720px** — the rail becomes the first screen (the seven groups) and
  tapping one pushes its rows with a back button. Rows unchanged, full width.

Row-level reflow (long values dropping under the label rather than squeezing
it) is CSS container queries; the JS observer handles only the structural mode
switch. Chromium 152 is pinned on the panel and supports both.

Verified 2026-09-15: the design's seven groups match ADR-0022's inventory
groups exactly.

## Scope of the mock

**Every inventory row renders for now, including the 22 that are `[N]` or
`[?]`** — George, 2026-09-15: *"Everything is rendered for now. The settings
page will go through several iterations before it is settled."* The amber
"decision still owed" marks are how an unconfirmed placeholder is spotted, and
they are driven from ADR-0022's `[R]/[H]/[N]/[?]` marks rather than
hand-placed. **They are build-time scaffolding and must never ship lit** —
Phase 9 criterion 4 already requires that no unwired UI survives unjustified,
and these marks are the generated list that check assumes exists.

**Row types are not defined here.** They are settled when the settings work
itself starts (George, 2026-09-15: *"We are not there yet. Now we are just
mocking everything up."*). The settings HTTP API will be built to match the
vocabulary the design settles on, not the reverse.

## What does not change

- **No search, no input fields.** The designs continue to avoid them
  (George, 2026-09-15: *"Nothing changes"*). So
  [0030](0030-library-typed-radio-slimbrowse.md)'s decision to render no search
  stands, and [0029](0029-text-entry-on-every-surface.md) is untouched. A
  phone-only search was newly *possible* under this decision and was declined.
- **[0020](0020-library-browse-tree.md)'s second branch stays retired.** It
  covers "exists but cannot be operated here, show it and say where." Nothing
  here is shown-but-not-operable: the panel has everything, and the phone shows
  only what it can operate.
- **[0028](0028-ui-serving-and-command-channel.md) is unaffected.** `/state`
  is publish-only aggregated state and commands are REST; neither knows nor
  needs to know which surface is asking. **The backend barely participates in
  this decision** — it is a rendering concern.

## Phase 4 criterion 5 is satisfied, not broken

The criterion reads *"Same page served to a remote browser and renders
correctly."* An earlier reading of this proposal had it breaking that and
needing a rewrite. It does not: the same page **is** served. What is clarified
is "renders correctly" — on a remote browser that means the settings surface,
correctly laid out at phone width, not the panel interface shrunk.

## Unresolved

**How the page knows which surface it is on.** Two candidates, and this is an
implementation detail deliberately left open while the design is still being
mocked:

- **Source address.** The panel always arrives on loopback; a phone arrives
  from the LAN. Verified 2026-09-14 in `gexis-core`'s access log
  (`127.0.0.1 … "GET / HTTP/1.1" 200`). Unambiguous and independent of screen
  size, but the client cannot see its own source address — the server would
  have to mark the served page.
- **Width.** Simple and client-side, but a landscape tablet can be 1280 wide
  and would get the panel interface.

Source address is the more reliable signal; width is the cheaper one. Decide
when the component lands.

## Consequence for the design work

Only the settings screen needs to be progressive. Every other screen stays at
the fixed 1280x800 artboard, because no other screen is ever served to a phone.
That is the whole practical benefit of this decision, and it is why the inverse
was worth taking over the proposal.
