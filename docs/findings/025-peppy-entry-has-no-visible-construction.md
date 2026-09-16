# Finding 025 — Raising the Peppy screen shows no construction; labwc's mechanism is `wlr-foreign-toplevel-management`

**Date:** 2026-09-16
**Question:** Phase 5 criterion 4 — "entry from now playing shows no
construction, measured, not asserted" — and ADR-0026's compositor mechanism,
which that record left unverified.
**System:** `gexis` on the current image, Chromium kiosk running throughout,
music playing. Stock PeppyMeter (unmodified) from `/tmp/spike`, `no.frame =
True`, 1280x800, fed by our visualisation service's passthrough pipe.
`wlrctl` 0.2.2 (Debian), labwc 0.20.1 / wlroots 0.20.2.

## Mechanism

labwc implements `wlr-foreign-toplevel-management`, so an outside process can
hide and raise a window without the application cooperating:

```
wlrctl toplevel minimize title:"pygame window"   # hides it, Chromium shows again
wlrctl toplevel focus    title:"pygame window"   # raises it over Chromium
```

Both were observed to work. ADR-0026's "raised and hidden by labwc, not by the
browser" is now verified rather than assumed, and `wlrctl` is the tool — no
patch to PeppyMeter, no X.

## Measured — 10 rounds of minimize, wait, raise

| | |
|---|---|
| capture cost of `grim` itself, nothing changing | **32 ms** per capture |
| raise to first observation showing the meter | **54-75 ms**, median ~60 |
| captures needed before the screen had changed | **1, every round** |

The first capture after the raise already showed the meter in all ten rounds,
so the number above is dominated by the cost of looking — one `wlrctl`
invocation plus one `grim`. Nothing was ever caught mid-construction.

**Completeness, checked separately:** a background region captured on the
first frame after the raise is **byte-identical** to the same region two
seconds later, and differs from the pre-raise screen. So the frame that
appears is the finished one, not a partial paint that settles afterwards.

**Why it is ready:** minimized, the process keeps running at **8.2-8.5 %** of
one core. It is not restarted on entry — which is precisely ADR-0019's
"pre-rendered and hidden, never constructed on demand", now true of a process
rather than a DOM.

## Not established

- **Not the project's skins.** The wrapper's 1280x800 template again, not
  Gelo5's corpus, which is in `skins/` as config only — the images are not on
  the device yet.
- **No systemd unit.** PeppyMeter was started by hand over SSH; nothing
  covers crash, restart, or ordering against the kiosk.
- **Entry is not wired to anything.** The UI's Visualization button still does
  nothing (`data-unwired="phase-5"`); this measured the compositor mechanism,
  not the product's entry path.
- **Exit on touch is untested** (ADR-0019), as is the unattended-playback
  timer (ADR-0036).
- **`wlrctl` is not in the image** — installed by hand, like pygame and grim
  (Finding 023's device drift).
- Window matching was by title `pygame window`, which is SDL's default and
  not something we have chosen deliberately yet.
