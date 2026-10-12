# ADR-0124 — Software volume, the owner's choice

> **Amended by [ADR-0127](0127-one-volume-row.md) (2026-10-07):** Output mode and Software volume are one row, *Volume* - Hardware, Software or Fixed. On an output with no volume control of its own, Hardware is greyed and Software takes its place; Fixed is no longer forced there.

**Status:** **Accepted** — George, 2026-10-07 (*"All good. Agreed with your proposal"*, the rows, the 60 s safeguard and the wording included): *"software volume as an option
for the user (completely his choice and can apply for example to hdmi devices
- we make it clear it is not bit perfect and it is his decision)"*; then
*"C. On any output. Users choice in the end, but with some clear notes that
bit perfect doesn't apply anymore. Spotify and Bluetooth too."* Its row is in ADR-0022's inventory.
**Builds on:** [ADR-0018](0018-volume-and-output-modes.md) (Variable and
Fixed), [ADR-0009](0009-logical-output-device.md) (one named output),
[ADR-0085](0085-the-alsa-default-is-our-output.md), [ADR-0055](0055-which-output-the-device-plays-to.md).

## Context

Every source plays through one ALSA device, `output`: a meter tap (the
visualiser's levels) over the card itself. Volume is the card's own hardware
control, after the tap - Lyrion's, Spotify's and Bluetooth's sliders all move
it - so the meters show the music as it arrives, at any volume. An output with
no volume control of its own (HDMI, some USB DACs) plays at a fixed level:
the panel says *Fixed* and offers no slider.

## Decision

1. **[N] Software volume** - *Audio*, after *Output mode*; a toggle, **off by
   default**, offered for **every output** (George: *"on any output"*). On, the
   player sets the level by scaling the samples itself, instead of the card's
   control - or, on an output without one, where there was none.
2. **The note says it plainly**, on the row and in a confirmation the first
   time it is turned on: *"The player changes the level by recalculating the
   sound. Playback is no longer bit-perfect, at any volume below 100 %. Use it
   for an output with no volume control of its own, such as HDMI, or if you
   prefer it. Off restores bit-perfect playback."* The output's row stops
   saying *bit-perfect* while it is on.
3. **Where it sits in the chain:** `meter → softvol → card`. The meter tap
   stays first, so the visualiser shows the music as it arrives, exactly as
   with hardware volume today; the software stage is after it. On HDMI it
   sits before the conversion HDMI needs (IEC958) - verified (Finding 115).
4. **Every source uses it** (George: *"Spotify and Bluetooth too"*): the core
   bridges each renderer's volume to the software control instead of the
   card's - Lyrion's dummy mixer, Spotify's mixer, Bluetooth's D-Bus volume -
   the same bridges, a different target. *Maximum volume* and *Volume curve*
   apply as they do now.
5. **Output mode stays:** *Fixed* still means full level for an amplifier
   that sets the volume; software volume applies to *Variable*.

## Consequences

- Below 100 % the samples are recalculated (ALSA's `softvol`, 24-bit headroom
  on the DAC2 HD): not bit-perfect, which the row says. **At 100 % (0 dB) it
  passes every sample unchanged - measured** (Finding 115: 18 runs, 0 samples
  changed in value).
- **On HDMI it sits in front of `plug`:** `softvol → plug → card`, measured
  (Finding 115); there is no meter on that chain, as before.
- The card's own control is left at its maximum while software volume is on,
  and given back its level when it is turned off.
- A takeover's *Starting volume* (Spotify) applies to whichever control is in
  use.

## Built 2026-10-07 (step 1)

- **The stage:** `meter → softvol → card`, or `softvol → plug → card` on
  HDMI; one control for `output` and squeezelite's `output_wait`, made on the
  output's own card as `Gexis Playback Volume` - `Gexis` to the simple-mixer
  calls the core uses. Its scale is -90..0 dB in 0.25 dB steps (361 values).
- **The level is the player's to keep:** ALSA makes a `softvol` control at
  0 dB when its PCM first opens, so the core makes it itself (open and close,
  nothing played) and sets the saved level before any renderer opens the
  output; the level is saved a second after it settles. **The card's own
  control is parked at 0 dB only once the software level has read back** -
  found on `guestpi`: the control addressed by the wrong name took no writes,
  the card was parked anyway, and a phone played at full level for about two
  minutes.
- **Switched in place**, as an output change is (no restart of the core):
  on, the heard level becomes the software level; off, the card's own control
  is given it first. Measured on `guestpi` (silent at 0 %): the level carried
  both ways, -26.0 dB before and after a core restart and back on the card
  when switched off; silence at 44.1/96/192 kHz through both PCMs at their own
  rate and format; a Lyrion FLAC through the chain with squeezelite reporting
  no errors.
- **The confirmation is asked each time it is switched on**, not only the
  first (decision 2 said the first): it is the mechanism every warned switch
  uses, and the safer of the two.
- **Not yet tried:** HDMI through the player's own switch (Finding 115 tried
  the chain by hand); a full reboot, where ALSA makes the control afresh;
  Spotify and Bluetooth driving it (they go through the same path as Lyrion).

## Amended 2026-10-12 (final code review)

- **Levels carry across a change of scale through dB.** A raw number means
  something only on its own scale (-20 dB is 200 on the DAC2 HD, 280 on the
  software stage). On a change of output or of volume type, the level shown,
  Mute's and the one before Fixed were replayed as raw numbers: muted in
  Software at -20 dB, switched to Hardware and unmuted, the DAC2 HD was
  written its top. They are now carried through dB, never above 0 dB, and
  silence stays silence (`carry_raw`). In Hardware the new card is given the
  level shown.
- **Silence is the bottom of the control's own range**, not raw 0. True of
  the DAC2 HD (0..240), but the Pi's headphone jack runs -10239..400, where
  raw 0 is 0 dB: Mute, a renderer's 0 and the slider's 0 % wrote full scale
  there. A single-value (`Mono:`) control, such as the jack's, is now read
  as well.
- **A change of output restarts renderer plugins too** (Plexamp plays through
  the same output and kept the old card), and only the sources that are
  switched on.

## Amended 2026-10-12 (George's answers)

- **The saved level is set before the renderers start**
  ([ADR-0140](0140-the-software-volume-is-set-before-the-renderers-start.md),
  built 2026-10-12). The core starts after the renderers, so after a power
  cut a renderer resuming by itself could play its first second through the
  software stage at the 0 dB ALSA makes it with. `gexis-softvol-restore.service`
  now writes the level first, by the same rule as the core
  (`softvol_boot.start_level`: the remembered level, else the card's own,
  else -30 dB); the core still sets it when it runs.
