# Finding 070 — The panel with LMS off

**Date:** 2026-09-25
**Question:** Does [ADR-0079](../decisions/0079-with-lms-off-the-panel-is-two-screens.md)
hold on the panel — the waiting screen, the settings corner, Now Playing as
the root — and what does every-source-off look like?
**Scope:** `gexis`, the panel's own 1280 × 800 screen, Chromium
153.0.8010.47, core and `ui/dist` rsynced from `phase-8-plan`. Screenshots
over CDP, taps dispatched the same way. Six states, each reached by writing
the real settings rows through `/settings`, never by forcing the UI.

## Result

| state | what the panel shows |
|---|---|
| LMS off, Spotify playing | **Now Playing as the root.** Left button is the sliders glyph, not the tiles glyph. No mini strip. The artist line is a name, not a link |
| LMS off, nothing playing, Spotify + Bluetooth on | **The waiting marks at 1.8×**, centred, settings icon top right |
| LMS off, nothing playing, Bluetooth only | The same, one mark |
| LMS off, every source off | **"No sources — every source is switched off. Settings, top right."** The icon is still there |
| settings icon tapped | Settings opens |
| Settings' back tapped | back to the waiting screen, not to a library |
| LMS on again | the library root returns, with no restart |

**The marks are downscales, not upscales.** `icon-spotify.png` is 539 × 539
and `icon-bluetooth.png` 181 × 244; at 1.8× the footer's sizes they render at
68 px and 83 px, so the promotion costs nothing in sharpness.

## The bug this found

**Switching off the active renderer left it active forever.** With Spotify
playing and `spotify_enabled` set to false, `go-librespot` stopped, the audio
stopped — and Now Playing went on showing its track, its artwork and its
progress bar indefinitely.

The cause is [ADR-0077](../decisions/0077-a-source-that-is-off-is-not-running.md)'s
own gate: the adapter's watch is cancelled when the row goes off, so the
`inactive` event that normally releases the device never arrives. **Nobody was
left to report the release.** `_apply_renderer` now says it — one
`supervisor.relinquish`, which is ignored unless that renderer is still the
active one, so it is safe whatever was holding the device.

**It was invisible until this screen existed.** Nothing in ADR-0077's own
hardware pass looked at what the panel said afterwards: the units were checked,
the availability was checked, the arbitration refusal was checked, and the
published `active` was not. A renderer that is off reporting itself unavailable
*and still active* is a contradiction the state payload was happy to carry.

## What this did not test

- **The phone.** Its now-playing view is not this screen and was not looked at.
- **LMS off while LMS is the active renderer.** Spotify was the case that
  happened to be playing; the fix is not renderer-specific, but only Spotify's
  path was walked.
- **Whether 1.8× is the right factor.** It is a judgement, not a measurement:
  two services come to 680 px of the width and about 300 px of the height on a
  1280 × 800 panel, which is what "scaled, not stretched" was taken to mean.
- **Turning LMS off from a library screen deeper than the root.** Every run
  started from the root or from Now Playing.
