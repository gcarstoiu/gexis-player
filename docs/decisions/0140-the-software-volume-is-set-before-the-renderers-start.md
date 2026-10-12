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

## Built (2026-10-12)

- **The unit:** `gexis-softvol-restore.service`, `Type=oneshot`, running
  `python -m gexis_core.softvol_boot` from the core's venv. Ordered
  `After=local-fs.target sound.target gexis-factory-reset.service` and
  `Before=` squeezelite, go-librespot, bluealsa-aplay, plexamp and
  `gexis-core`; `TimeoutStartSec=15`, so a step that hangs is given up on
  rather than holding the renderers. Shipped in `gexis-core` and enabled by
  its postinst on every device, an updated one included, as
  `gexis-factory-reset.service` is.
- **What it does:** only when the volume type in force is Software (the
  stored `output_mode`, or Hardware on an output with no control of its
  own - the same `volume_mode()` the core uses), it makes the software
  control and writes the level onto `Gexis` on `output`, then reads it back.
  The settings store is opened read-only; the card's own control is never
  touched (the core still parks it at 0 dB, once its own write has read
  back). It waits up to 3 s (`CARD_WAIT_S`) for the configured card to be
  listed. A missing store, card or output, or a failure of any kind, is
  logged and the step exits 0. In Hardware or Fixed it does nothing.
- **One rule for the start level, shared with the core**
  (`softvol_boot.start_level`): the remembered level, else the card's own,
  else -30 dB. The core's `_start_software_volume()` now calls the same
  function, so the step never sets more than the core then does.
- **What it carries across a boot is only the software level ADR-0124
  already keeps.** ADR-0018's rule that nothing carries a level across a
  boot stands for everything else.
- **Uploaded renderers are not in its `Before=`** (decision 1 named renderer
  plugins): they start after the core, which sets the level itself. Plexamp
  is.
- **Checked on sofapi and the bar player:** installed, enabled, ordered
  before the renderers; in Hardware it does nothing. A power cut while
  playing in Software, the case that asked for it, was not part of that
  check.
