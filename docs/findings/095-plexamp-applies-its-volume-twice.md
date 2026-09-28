# Finding 095 — Plexamp applies its volume twice

**Date:** 2026-09-27
**Question:** Finding 084
showed Plexamp's level and the core's agree in both directions, but it never
measured the output. Does Plexamp attenuate digitally as well as having its
level applied on the DAC?

**Scope:** `gexis`, Plexamp 4.13.2 with gexis-plexamp 0.2.2. One track from
George's Plex library, started through the Plex server. Plexamp's own volume
alternated between 20 and 10, six passes, 2 s of reading each after 0.8 s
to settle. **The level was read from the pre-DAC meter tap** (peppyalsa on
`pcm.output`, linear amplitude, 0-100), with the meter service stopped for the
minute so its FIFO could be read directly. Quiet levels only, because the core
applies Plexamp's reported level to the DAC. **Not measured:** the DAC's
analogue output, other Plexamp levels, or its curve's shape beyond these two
points.

## Result

| Plexamp volume | Pre-DAC level, 6 passes (the first skipped as the track ramped in) | Mean |
|---|---|---|
| 20 | 5.51 4.62 5.50 5.52 5.46 | 4.90 (all six) |
| 10 | 2.90 2.63 2.73 2.46 2.75 | 2.65 |

**Halving Plexamp's volume halves the signal before the DAC.** Plexamp
attenuates digitally, linearly in amplitude. The core then puts the same level
on the DAC's hardware mixer as well (Finding 084: *"45/100 → 204/240"*). So
every Plexamp level below 100 is attenuated twice, and the signal reaching the
DAC is not bit-perfect. ADR-0054's premise, that a renderer sends full scale
and the DAC sets the level, does not hold for Plexamp.

## What it bears on

- **Plexamp needs a decision.** The candidates are its own settings, if any
  give a fixed or external volume (not yet looked for), or leaving its volume
  to Plexamp and the DAC's to the panel.

## Is there a way to keep Plexamp at full scale? (George: "option B")

**No, not through Plexamp.** Looked for on the device, in Plexamp 4.13.2's own
files, the same day:

- **Its settings:** none about the player's output volume.
  - Its stored settings (`~/.local/share/Plexamp/Settings`) hold the volume only
    as state.
  - Its interface labels about volume are *Show Volume Control* (a flag on the
    controller's screen, `playerShowVolume`), *Use Hardware Volume* / *Link
    hardware volume to remote volume* (`remoteControlUseHardwareVolume`, a
    controller linking its own volume keys to a remote player), *Loudness
    Leveling*, *Equalizer Preamp Gain* and *DSD Gain*.
- **Its code path:** the headless player's `setVolume` calls a native module.
  In `treble.node` that is `Mixer::setVolume`, which is
  `BASS_ChannelSlideAttribute(m_mixer, BASS_ATTRIB_VOL | BASS_SLIDE_LOG, volume/100.0, ms)`,
  **a gain on its own mixer channel: sample scaling, always.** `libbass`
  carries ALSA mixer code, but this path does not use it.
- **Checked on the device:** a Plexamp volume change moved **no** control on
  the HiFiBerry card (`amixer contents`, before and after, identical).

What remains is on our side:

- **(a)** Leave Plexamp's volume to Plexamp, and the DAC's to the panel.
- **(b)** The plugin holds Plexamp's own level at 100 and puts every change on
  the DAC. Bit-perfect, one level, but the Plexamp app's slider then reads 100
  and snaps back.
- **(c)** Leave it as it is: applied twice.

**Decided (George, 2026-09-27): (c), leave it as it is.** *"Let's keep C as it
is more likely for users to use their phones to decrease or increase
volume."* One number, shared by the Plexamp app and the panel, is worth more
than loudness matching the other sources or being bit-perfect below 100. The
known cost stays: Plexamp at a given number is quieter than Spotify or LMS at
the same number, increasingly so toward the bottom of the slider.

**Revised (George, 2026-09-28): (a).** *"…we should do the same for plexamp
actually as well. My bad with the previous decision."* gexis-plexamp now
declares `volume_managed: false`, reports no level and refuses `set_volume`.
The Plexamp app's slider moves Plexamp's own gain; the panel's moves the DAC.
Released as gexis-plexamp v0.3.0 and pinned in stage `08-plexamp`. The
consequence George raised with it, a takeover landing at a level an
app-controlled source left on the DAC, was answered by *Starting volume*
(ADR-0054 §5, amended 2026-09-28).
