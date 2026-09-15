# ADR-0034 — Panel volume: slider over −45…0 dB, shown as slider position; mute restores the prior level

**Status:** Accepted
**Date:** 2026-09-15
**Raised by:** Phase 4 step 4e — criterion 8 left the slider's travel open
**Amends:** `docs/DEVELOPMENT.md` Phase 4 criterion 8 — what the number means

## Problem

The DAC control is dB-linear: 240 steps of 0.5 dB (ADR-0018). A slider mapped
straight onto it puts every usable level in the top quarter — halfway is
−60 dB. Criterion 8 had settled that the UI *displays* a percentage of the
hardware control, and left how the slider travels open.

## Decision

**Travel spans −45 dB to 0 dB, linear in dB, and the bottom of travel is
silence** (raw 0). −45 dB is the effective span LMS's and Spotify's own
sliders already settled on (Findings 009, 010), so the panel's slider behaves
like the phone apps.

**The number shown is the slider position, not the hardware percentage**
(George, 2026-09-15, option C). Halfway reads 50 % and is −22.5 dB. This
reverses criterion 8's "displayed as a percentage of the hardware control".
The backend owns the scale: `volume.percent` in `/state` and `POST /volume`
both speak slider position, so every surface agrees. `raw` and `db` stay
published. A hardware level quieter than −45 dB but not silent — reachable by
a manual `amixer` write or an unmanaged renderer — shows as 0 %.

**Mute is a backend command, and unmute returns to the level before mute**
(George, 2026-09-15). Mute remembers the current level and writes silence;
unmute writes the remembered level back. `volume.muted` is published.

**Any other change to the level ends mute.** A phone raising the volume, the
panel slider, or a renderer's remembered level being restored on takeover all
move the level off silence; mute is then over, and unmute has nothing to
restore. The alternative — a muted flag that survives someone else turning
the volume up — would show "muted" over audible music, which ADR-0010's
accountability rule forbids.

## Not decided here

- Whether mute propagates to the renderer's own app (a phone's slider). It
  does not today: panel writes go through `VolumeBridge.write_hardware`,
  whose echo suppression deliberately keeps them from bouncing out.
- Fixed output mode (ADR-0018) is still unbuilt; the design hides the slider
  in that mode.

## Settings

ADR-0022's "Volume slider travel curve" row stops being a decision owed: the
span is decided and hardcoded. Mute adds no setting.
