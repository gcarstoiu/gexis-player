# ADR-0057 — The meters show what comes out, not what went in

**Status:** **Accepted and built**, 2026-09-23. George: *"Shouldn't the vu
meters and spectrum amplitude be based on volume? And only on fixed volume
be like it is now?"* and, on the proposal: *"Both should follow… Let's do
both and see."*
**Date:** 2026-09-23
**Relates to:** [ADR-0011](0011-meter-data-three-transports.md) (the relay),
[ADR-0009](0009-logical-output-device.md) (`pcm.output`),
[ADR-0046](0046-fixed-output-hides-the-slider.md) (fixed output),
[ADR-0054](0054-one-curve-and-the-renderers-own-number.md) (the 60 dB curve)

## Context

`pcm.output` is a `type meter` over the card, and the DAC attenuates in
hardware **after** it. So the needles and the bars have always shown the
recording at the level it was mastered, and turning the volume down changed
nothing on the screen. George, looking at it: *"everything looks maxed out
with some lines just jumping a bit. Not the way it should be."*

A real amplifier's meters are output meters. Its needles fall when you turn
it down.

## Decision

**Both the VU level and the spectrum are attenuated by the dB the device is
currently cutting, before anything is published.**

- The daemon writes that number — one line, positive dB, 0 for none — to
  `/run/gexis/attenuation`, from `_report_hardware_level`, which is the one
  funnel every hardware level change already passes through: our own writes
  and the ones `alsactl monitor` sees.
- The meter service reads it, re-reading only when the file changes, and
  applies it to every consumer: the FIFO PeppyMeter and PeppySpectrum read,
  the WebSocket the panel draws from, and the HTTP target.
- **The two scales are different and are treated differently.** peppyalsa's
  meter level is linear amplitude, so attenuation is a multiplication by
  `10^(−dB/20)`. Its spectrum is logarithmic — `100·log10(magnitude)/4.82`,
  where a unit is 0.963 dB — so attenuation is a subtraction. Treating them
  alike would put the bars in the wrong place at every volume but full.
- **Fixed output needs no special case.** There the DAC sits at full scale,
  so the published attenuation is 0 and the meters show the source — which
  is exactly what George asked for, arrived at by arithmetic rather than a
  branch.

## Consequences

- **Measured on the device**, with one track playing and the attenuation
  set to three values:

  | cutting | VU mean | VU peak | bands mean | bands peak |
  | --- | --- | --- | --- | --- |
  | 0 dB | 53.8 | 100 | 51.6 | 69 |
  | 20 dB | 5.1 | 10 | 29.4 | 48 |
  | 54 dB | 0.0 | 0 | 0.7 | 12 |

- **The needles die well before the slider does, so they follow a third of
  it.** The volume curve spans 60 dB
  ([ADR-0054](0054-one-curve-and-the-renderers-own-number.md)) and George
  has ruled that out of scope: *"For sure we will not narrow the volume
  curve though - that stays in place as is."* Applied one-for-one, 60 dB is
  three times what a VU dial is drawn for — the faces in both packs run
  from −20 to about +3 — so the needle reaches the bottom stop at about 40%
  on the slider and the rest of the travel shows nothing. George saw it:
  *"The vu meters are a bit quiet on the bottom part."*

  **`METER_VOLUME_TRACKING` maps the volume's full travel onto the dial's
  full travel** rather than onto three of them: 20 dB of dial over 60 dB of
  volume, so the meters fall by a third of the dB.

  | panel | cutting | needle, 1:1 | needle, a third | bar (from 60) |
  | --- | --- | --- | --- | --- |
  | 100% | 0 dB | 100% | 100% | 60 |
  | 80% | 5.2 dB | 55% | 82% | 58 |
  | 60% | 11.6 dB | 26% | 64% | 56 |
  | 40% | 20.2 dB | 10% | 46% | 53 |
  | 20% | 33.2 dB | 2% | 28% | 49 |
  | 10% | 43.3 dB | 0.7% | 19% | 45 |

  It is the one number that decides how far they fall. **A candidate for
  ADR-0022's inventory, and not on it** — George's call.

- **The spectrum falls far more slowly than the VU**, because it is
  logarithmic: 20 dB costs the bars 21 of 100 units and the needle 90% of
  its travel. The two will not look like they are doing the same thing.

- **A meter that cannot read the file shows the source**, which is what it
  did before this record. A stale file cannot outlive a level change: the
  daemon writes on every one.

- **`attenuation_path` is a new `Config` key**, pinned to `volume.py`'s
  constant by a test (LESSONS case 20: a declaration and the thing it
  declares are two files). It is a path, not a preference, and is **not**
  proposed for ADR-0022's inventory.

## Alternatives considered

- **Read the DAC from the meter service.** Rejected: it would duplicate the
  dB scale, and that scale is the HiFiBerry's — the headphone jack's control
  has its own, and the meter service does not track which output is in use.
- **Scale by the panel's percentage instead of by dB.** It would keep the
  needles alive at low volume, which may well be what George prefers, but it
  is not what an output meter shows and it would make the number on the
  screen depend on which renderer last set the level. Left as the Open.
- **VU follows, spectrum does not.** Offered and declined: *"Both should
  follow."*

## Open

- ~~**Whether 60 dB of travel is too much for a meter to follow honestly.**~~
  **Answered 2026-09-23: it is.** George ruled out narrowing the volume
  curve, so the meters take the shallower law — a third of the dB, which is
  the dial's own 20 dB over the volume's 60. Whether a third is the right
  third is what he is looking at now.
- **Whether the spectrum should follow the same fraction as the VU.** It
  does today, for one law rather than two. Its scale is logarithmic and four
  times as wide, so the same fraction moves the bars far less than the
  needle — at 20 dB of cut the needle loses a fifth of its travel and the
  bars a tenth of their height. They will not look like they are doing the
  same thing.
