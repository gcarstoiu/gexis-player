# ADR-0140 — The software volume is set before the renderers start

**Status:** **Accepted** — 2026-10-12. George, on the final code review's
open question (*"Do it now"*).
**Amends:** [ADR-0124](0124-software-volume.md)'s start-up; boot ordering of
the core's units.

## Context

With *Volume* on Software (any output with no control of its own - HDMI
above all), the level is the software stage's (`softvol`), which ALSA
creates at 0 dB and the core sets once it runs. `gexis-core.service` starts
*after* Squeezelite, go-librespot and bluealsa-aplay. After a power cut
while Lyrion was playing, the server resumes the player as Squeezelite
connects (ADR-0022's *Playback when the device starts* pauses it, but only
once the core runs): the first second or so can play through the software
stage at 0 dB, full scale, before the saved level is written. Found by the
final code review (Finding 119, volume-main-12); not measured on a device.

## Decision

1. **A small boot step sets the saved software level before any renderer
   starts**: a oneshot unit, ordered before the renderer units (Squeezelite,
   go-librespot, bluealsa-aplay and the renderer plugins), which writes the
   level the core keeps for the software stage onto its control - only when
   *Volume* is Software, and doing nothing otherwise.
2. **It never stops a boot and never writes louder than the core would**: a
   missing card, store or control is logged and the step ends successfully;
   the value written is the stored one, as the core would write it.
3. **The core still sets the level when it runs**, as before; the step only
   closes the gap before it.

## Consequences

- One more unit at boot, measured in milliseconds; installed by the image
  and by updates (the package that carries the core's units).
- The technical guide's audio path and boot order describe it.
