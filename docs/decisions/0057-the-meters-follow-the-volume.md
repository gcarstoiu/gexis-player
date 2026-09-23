# ADR-0057 — The meters show what comes out, not what went in

**Status:** **Accepted and built**, 2026-09-23. George: *"Shouldn't the vu
meters and spectrum amplitude be based on volume? And only on fixed volume
be like it is now?"* and, on the proposal: *"Both should follow… Let's do
both and see."*
**Date:** 2026-09-23
**Relates to:** [ADR-0011](0011-meter-data-three-transports.md) (the relay),
[ADR-0009](0009-alsa-device-indirection.md) (`pcm.output`),
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

- **The needles die well before the slider does, and that is the thing to
  look at.** The volume curve spans 60 dB
  ([ADR-0054](0054-one-curve-and-the-renderers-own-number.md)), so the
  panel's percentage costs the VU a great deal very quickly:

  | panel | cutting | needle reads |
  | --- | --- | --- |
  | 100% | 0 dB | full scale |
  | 80% | 5.2 dB | 55% |
  | 60% | 11.6 dB | 26% |
  | 50% | 15.5 dB | 17% |
  | 40% | 20.2 dB | 10% |
  | 30% | 25.9 dB | 5% |
  | 20% | 33.2 dB | 2% |

  This is what an output meter does, and it is also how a real VU dial is
  marked — 0 VU sits at about three quarters of the arc and −20 near the
  left stop. Whether it is what George wants to look at is his, and is the
  Open below.

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

- **Whether 60 dB of travel is too much for a meter to follow honestly.**
  At 40% on the panel the needles are at a tenth of scale. If that reads as
  broken rather than quiet, the remedy is not in this record — it is either
  a shallower law for the meters alone, or a narrower volume curve.
