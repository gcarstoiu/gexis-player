# Finding 006 — Bluetooth volume is hardware above ~96%, something else below it

**Date:** 2026-09-07
**System:** `gexis`, Phase 2b build, A2DP sink via `bluealsa-aplay`.
**Question:** Does Bluetooth's AVRCP volume control move the same hardware
mixer LMS and Spotify do, the way ADR-0018 assumes for "one global control
shared by all renderers"?
**Answer:** Only part of the way down. Below roughly raw 230/240 (96%,
-5dB), it does not.

---

## Observation

Two mixer readings during a single Bluetooth playback session, phone
volume slider dragged from roughly the middle toward zero:

- At the top of the range (and while the mixer read 230/240, its
  apparent floor), volume tracked the slider normally.
- Continuing to drag down, the sound kept getting audibly quieter, but
  the hardware mixer **stayed at 230/240 across two separate readings**.

Something is attenuating the signal that isn't this mixer. The
`ctl.output` / `pcm.output` arrangement (ADR-0009) is specifically meant
to make the hardware mixer the *only* attenuation point reachable from a
renderer — if `bluealsa-aplay` (or a plugin it uses) is applying gain in
software below this floor, that arrangement doesn't cover this path, and
nobody had checked it until this session.

## What this confirms, separately

**Bluetooth's mapping to the hardware mixer is also badly non-linear
where it does apply**, one more data point alongside LMS's own mapping
(Finding still pending write-up, HANDOFF.md):

| Renderer | Reported/slider level | Hardware raw | dB |
|---|---|---|---|
| LMS | "mixer volume" 30/100 | 170/240 | — |
| Bluetooth | ~50% (slider) | 230/240 | -5dB |

Half of Bluetooth's slider travel (50%→100%) spans only 5dB — the top
half of the slider is nearly inert and the bottom half (whatever is
producing the audible drop below 230) is a cliff by comparison. A user
dragging the slider hears nothing for a while, then a jump.

**At 100% volume, Bluetooth and Spotify sound the same** — ruling out a
simple fixed attenuation offset on the Bluetooth path. Whatever is
happening is curve-shaped, not a constant.

## Not established

- **Which component applies the attenuation below the mixer floor.**
  Candidates, none checked: `bluealsa-aplay` itself, an ALSA plugin
  layer it goes through, or something in `bluez-alsa`'s own AVRCP-to-PCM
  volume handling. `libasound2-plugin-bluez` is installed
  (`image/stage-gexis/02-renderers/00-packages` pulls in
  `bluez-alsa-utils`, which depends on it) and is a candidate but not
  confirmed.
- **Whether this is A2DP-transport software scaling** (each frame
  attenuated before encode) **or something downstream of decode on our
  side.** Meaningfully different questions for bit-perfection: the
  former is upstream of the DAC in a way ADR-0018 already accepts as
  outside our control for a lossy codec; the latter would be exactly the
  kind of undisclosed attenuation ADR-0009's `output` indirection exists
  to prevent.
- **Whether the floor (~230/240) is fixed or itself derived from
  something.** Only two readings, both near the same value.

## Scope

Two mixer readings, one audible change, one Bluetooth session, one
phone. Not the kind of repeated, controlled measurement Findings 002-004
are. Enough to say "something other than the hardware mixer is
attenuating Bluetooth volume below ~96%," not enough to say what, or to
rule out something specific to this phone or this session.

## Update, 2026-09-08 — a candidate mechanism, not yet confirmed

A separate defect diagnosed the same later session:
`bluealsa-aplay --pcm=output` alone (no `--mixer-device`/`--mixer-name`)
logged `Couldn't open ALSA mixer: Mixer element not found`, looking for
ALSA's own defaults (`name=default elem=Master`), which don't exist on
this image. Fixed by adding `--mixer-device=output --mixer-name=DAC`
(`image/stage-gexis/02-renderers/files/bluealsa-aplay-override.conf`).

`bluealsa-aplay --help` documents `--volume=auto|mixer|none|software`,
defaulting to `auto`. A failed mixer lookup is a plausible reason `auto`
would have fallen back to `software` for the *entire* range, which
would be a different, larger claim than this finding's original
"partial, below ~96%" one — possibly all of Bluetooth's volume was
software before this fix, not just the bottom of the range. **Not
confirmed** — the mixer-args fix hasn't been re-tested against this
finding's original observation yet. Check on the next hardware pass
before revising the finding's own answer above.

## Consequence for criterion 5

The per-renderer volume-memory decision (HANDOFF.md, 2026-09-07:
restore each renderer's own volume when it becomes active) is
deliberately scoped to LMS and Spotify only, not Bluetooth — restoring a
remembered *hardware mixer* value for Bluetooth would only be correct
for the fraction of its range that the hardware mixer actually governs.
Extending per-renderer memory to Bluetooth needs this finding resolved
first, not guessed around.
