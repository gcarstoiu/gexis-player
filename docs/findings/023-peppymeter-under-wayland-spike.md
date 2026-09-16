# Finding 023 — PeppyMeter runs under Wayland on `gexis`, undecorated and fullscreen not yet attempted

**Date:** 2026-09-16
**Question:** ADR-0026 says the Peppy screen is a native process; Finding 007
left "real frame-rate/CPU cost on `gexis` hardware" unestablished, and
`docs/reference/peppymeter-fork-on-moode.md` describes a Volumio wrapper that
sets `DISPLAY=:0`. Can stock PeppyMeter draw on this panel at all, given the
kiosk is labwc on Wayland with no X server?
**System:** `gexis`, running the current image
(`v0.2.1-146-ge89d8bb`), Chromium kiosk live throughout. Stock
`foonerd/PeppyMeter` at HEAD, unmodified code, in `/tmp/spike`. Skins: the
1280x800 set shipped in `foonerd/peppy_screensaver` — **not** the Gelo5
corpus ADR-0015 describes, which this project does not have.

## Result

**It runs and it draws.** `SDL_VIDEODRIVER=wayland` with
`WAYLAND_DISPLAY=wayland-0`, started over SSH as `pi` against the running
labwc session. Screenshot taken on the device with `grim`: the skin's
background renders, the two linear meters animate bottom-right, and the
"Remaining Time" label draws.

| measured | value |
|---|---|
| CPU, three samples 3 s apart | 17.0 %, 14.2 %, 12.3 % of one core |
| RSS | 145 MB |
| Chromium at the same moment | 117 % and 67 % of a core, two processes |

No X server, no Xwayland, no code change: the Volumio wrapper's `DISPLAY=:0`
is a property of that wrapper, not of PeppyMeter.

## What this does not establish

- **Not fullscreen.** labwc drew it as a decorated window titled "pygame
  window", inset within the panel. Fullscreen and undecorated is a
  compositor rule or an SDL flag; neither was attempted here, so ADR-0026's
  "labwc-mediated screen ownership" is still unverified.
- **No frame rate was measured.** CPU is not frames; the config asks for 30
  fps and nothing checked whether it achieves it.
- **No audio was playing**, so the meters were animating on whatever the
  peppyalsa FIFO carried at rest, not on real signal.
- **Not the project's skins.** The Gelo5 corpus ADR-0015 is written against
  is not in this repository; these are the wrapper's own 1280x800 templates.
- **Spectrum was not run** — PeppyMeter only. `PeppySpectrum`, the
  combination in one process, and the cwd trap the reference document
  describes were all out of scope.
- **Sustained behaviour unknown.** Two runs of 25-30 s each.

## Device drift this created

`python3-pygame` (pulling SDL2) and `grim` were installed on `gexis` by hand
and are **not in the image**. Phase 5 will add pygame to the image properly;
until it does, `gexis` differs from what `make image` produces, which is
exactly what the tier-3 environment assertion in `docs/DEVELOPMENT.md` exists
to catch. `/tmp/spike` disappears on reboot.


## Follow-up, same day

With the visualisation service built, PeppyMeter was pointed at our
passthrough pipe (`/tmp/gexis-peppymeter`) instead of peppyalsa's and
rendered live audio from it — the needle deflecting with the music, screenshot
taken on the device. CPU 28.9 % of one core at that moment, higher than this
finding's 12-17 %, with the meter actually moving rather than at rest. Still
a decorated window; fullscreen ownership remains unverified.
