# ADR-0124 — Software volume, the owner's choice

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
   sits before the conversion HDMI needs (IEC958): to be verified on the
   device.
4. **Every source uses it** (George: *"Spotify and Bluetooth too"*): the core
   bridges each renderer's volume to the software control instead of the
   card's - Lyrion's dummy mixer, Spotify's mixer, Bluetooth's D-Bus volume -
   the same bridges, a different target. *Maximum volume* and *Volume curve*
   apply as they do now.
5. **Output mode stays:** *Fixed* still means full level for an amplifier
   that sets the volume; software volume applies to *Variable*.

## Consequences

- Below 100 % the samples are recalculated (ALSA's `softvol`, 24-bit headroom
  on the DAC2 HD): not bit-perfect, which the row says. At 100 % with the
  control at 0 dB it passes the samples through - to be measured, not assumed
  (Finding to follow).
- The card's own control is left at its maximum while software volume is on,
  and given back its level when it is turned off.
- A takeover's *Starting volume* (Spotify) applies to whichever control is in
  use.
