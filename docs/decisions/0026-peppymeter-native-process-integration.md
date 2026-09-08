# ADR-0026 — Peppy screen: native PeppyMeter process, always-on, labwc-mediated screen ownership

**Status:** Accepted (screen-ownership mechanism confirmed by George
2026-09-08; the compositor-side implementation detail flagged below is
unverified and needs research before it's built)
**Date:** 2026-09-08
**Relates to:** ADR-0014 (distinct screens), ADR-0015 (skin format, amended
2026-09-08), ADR-0016 (plugins as separate processes), ADR-0019 (Peppy
screen lifecycle, amended 2026-09-08), ADR-0025 (GPL v3)
**Evidence:** Finding 007 (licence, NEON, skin-format confirmations)

## Context

George decided to adopt foonerd's PeppyMeter/PeppySpectrum fork — the
engine and skin rendering, not a browser reimplementation of it (see
Finding 007 for the research, ADR-0025 for the resulting licence
decision). That's final; it is not reopened here.

It does, however, conflict with three existing ADRs that were built on the
opposite premise. ADR-0015 chose in-browser CSS rendering specifically
*because* it's cheaper than PeppyMeter's own CPU blitting. ADR-0019's
entire pre-rendering design rests on "there is no process to start and no
compositor handoff... because the renderer is in the browser." Running
foonerd's actual pygame/SDL2 engine cannot happen inside the Chromium DOM
— it is a separate GUI process by construction, using a different
rendering toolkit entirely. Both ADRs have been amended to point here
rather than silently contradicted.

One thing the reversal does *not* break: ADR-0011 already treated
"PeppyMeter itself... dropped in as a plugin" as a live fallback and built
a PeppyMeter-HTTP transport for exactly this case. That transport isn't
implemented yet (Phase 5 hasn't been built — confirmed, no WebSocket
publisher or visualisation service exists in `core/src` yet), but the
ALSA/FIFO side already is (`image/stage-gexis/00-alsa/files/output.conf`).
**Meter levels need no new design.** Playback *metadata* is the real gap —
foonerd's handlers expect Volumio's socket.io `pushState` events; we have
none of that.

## Decision

**PeppyMeter/PeppySpectrum run as an always-on native process
(`gexis-peppy.service`), pre-rendering continuously in the background, with
the physical screen handed to it or to Chromium by the compositor (labwc)
on command from the core daemon.**

This was chosen over two alternatives (see "Rejected" below) specifically
to preserve ADR-0019's "no process to start, only a state change"
principle — the mechanism changes from DOM visibility to compositor
stacking, but the shape (pre-render ahead, then just show it) survives.

### Process architecture

- `gexis-peppy.service`: a Python process built from the vendored
  `PeppyMeter`/`PeppySpectrum` engine modules plus the adapted
  `volumio_*.py` handlers (meters + spectrum only — see Scope below),
  running under `pygame`/SDL2 with `SDL_VIDEODRIVER=wayland`, connecting to
  labwc as a normal Wayland client.
- Starts at boot alongside the Chromium kiosk, stays running for the life
  of the session. Never restarts on track change, renderer change, or
  screen switch — only a full crash restarts it (systemd `Restart=on-failure`).
- Pre-renders/composites the next track's skin while the current one is
  displayed, per ADR-0019's existing rotation requirement — this is
  unchanged policy, just now happening inside this process's own render
  loop instead of the browser's.
- Kept unfocused and not raised except when the Peppy screen is the active
  screen. Whether "unfocused, not raised" is enough to make it fully
  invisible (versus needing to also be minimized, moved off-screen, or
  otherwise suppressed) is compositor-specific — see the open item below.

### Screen ownership mechanism

The core daemon already knows about arbitration and renderer-takeover
events (ADR-0010) — it becomes the source of truth for which screen is
active, same as it would have been for a DOM-visibility toggle. On a
screen-switch decision (Peppy entry/exit, or ADR-0019's renderer-takeover
rule firing), it sends a show/hide command through a small IPC layer to:

1. Raise/focus the PeppyMeter window and lower/unfocus Chromium's, or the
   reverse.
2. Ensure the hidden client isn't receiving input (touch-to-exit, ADR-0019,
   must land on the visible client only).

**Unverified — needs research before this is built, not assumed:**
*exactly* how labwc exposes this. labwc does not have sway's `swaymsg`-style
scripting IPC built in. A wlroots-generic tool like `wlrctl` (activate/
toggle a client by app-id) is a plausible fit, or a small custom listener
using labwc's own config/window-rule surface, or the layer-shell protocol
if PeppyMeter is drawn as a layer-shell surface instead of a normal
top-level window. I have not verified which of these labwc actually
supports in this session — this needs a spike against the real compositor
before implementation, not a choice made from memory here. Per CLAUDE.md's
rule against characterising risk without evidence: this is flagged as
open, not sized.

### Data flow

**Meter levels — no new work.** PeppyMeter reads its own FIFOs or the
PeppyMeter-HTTP transport (ADR-0011) exactly as upstream does; our
existing `output.conf` already produces the data in the shape it expects.

**Metadata — new adapter, replacing foonerd's socket.io ingestion.**
`volumio_peppymeter.py`'s `pushState` listener (Volumio's socket.io on TCP
3000) is replaced with a poll loop or subscriber against gexis-core's
WebSocket (Phase 3, not yet built) plus a field-name mapper: our seven
skin fields (title, artist, album, artwork, sample rate, remaining time,
source type — ADR-0014) plus position/duration map onto the
`playinfo.*`/`albumart.*`/sample-rate/time-remaining keys the handlers
already read. This is the "main integration work" the original brief
named, and it's still true — nothing above removes it, it just clarifies
that it's metadata-only, not meters too.

### Lifecycle hardening (inherited failure modes — work around, don't fix)

Carried over from Finding 007/the original brief, restated here as
implementation requirements for `gexis-peppy.service`:

- `os._exit(0)` on "invalid meter folder name" and "cannot read
  meters.txt" exits 0 on failure. The unit needs its own health check
  (e.g. a post-start probe, or watchdog on absence of expected log lines)
  since systemd cannot tell this apart from clean shutdown. Run under
  `python3 -u` so anything printed before the exit reaches the journal.
- `config_path = os.path.join(os.getcwd(), ...)` is a CWD trap — set
  `WorkingDirectory=` explicitly in the unit.
- `duration` must arrive as `int()`. Confirmed in Finding 007 that
  `volumio_basic.py`'s current handler already casts
  (`int(meta.get("duration") or 0)`) — but our metadata adapter is new
  code, not theirs, so this needs its own explicit cast rather than
  assuming the upstream guard covers a path it was never written for.
- Change-guard: widen whatever field-change detection our adapter uses to
  include title, not just (file, state) — non-MPD sources (Spotify,
  Bluetooth) don't reliably supply a distinguishing "file" the way LMS
  does.

## Scope

**Meters and spectrum only**, per the original brief and unchanged here.
`volumio_turntable.py`, `volumio_cassette.py`, their tonearm/reel state
machines, and the backing-buffer management they need are **not**
vendored. George has not ruled on whether they're wanted; nothing above
depends on that ruling, and vendoring them now would mean carrying dead
code and a licence surface (same GPL v3 combined-work analysis, no
additional exposure, but no benefit either) for handlers we may never
enable.

### What gets vendored

From `foonerd/PeppyMeter` and `foonerd/PeppySpectrum`: the engine modules
(`circular.py`, `needlefactory.py`, `configfileparser.py`,
`spectrum.py`/`spectrumutil.py`, `spectrumconfigparser.py`, and their
dependencies within those two repos).

From `foonerd/peppy_screensaver`'s `volumio_peppymeter/`:
`volumio_basic.py`, `volumio_spectrum.py`, `volumio_configfileparser.py`,
`volumio_indicators.py`, `volumio_compositor.py`, `volumio_typeformat.py`
(format-icon/codec-badge handling), and `volumio_peppymeter.py` as the
starting point for our own coordinator (its socket.io ingestion is
replaced per "Data flow" above; its skin-type dispatch and render-loop
structure are what we're actually taking). `fonts/` (PeppyFont + DSEG7)
and the 6 bundled `format-icons/` SVGs come along; George supplies icons
for our actual sources (Spotify, Bluetooth — Finding 007's follow-up note)
separately.

Not vendored: `index.js`, `UIConfig.json`, `config.json`, `createConf.js`,
`restoreAsound.js`, `install.sh`, the SMB template-sharing machinery, the
remote-display UDP protocol, their ALSA config generation (we have our
own, ADR-0009/0018, untouched by anything vendored here), and the
turntable/cassette handlers per Scope above.

## Rejected alternatives

**Direct DRM/KMS planes, bypassing Wayland for the Peppy screen.**
Deterministic handoff with no compositor in the loop, but Chromium and
PeppyMeter would contend for DRM master — more fragile, and gives up
labwc's benefits for Chromium's own lifecycle. Not chosen.

**Start PeppyMeter fresh at Peppy-screen entry, exit it on leaving.**
Simplest to build, but directly violates ADR-0019's Must-requirement (no
visible render-in-delay) — pygame startup plus skin decode/composite is
not instant, which is exactly the case ADR-0019 was designed to avoid. Not
chosen.

## Unverified

- The labwc-side screen-ownership mechanism (see "Screen ownership
  mechanism" above) — needs a spike against the real compositor.
- Perceived latency of the raise/hide switch on real hardware — carries
  forward ADR-0019's existing unverified item (previously "visibility
  switch on an already-composited layer stack"; same question, new
  mechanism).
- CPU cost of PeppyMeter's own rendering at 1280x800 with Chromium also
  running (Finding 007, Blocker 2) — the measurement that would also
  settle the residual NEON question from Finding 007 §2.
