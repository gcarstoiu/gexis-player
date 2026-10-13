# ADR-0146 — The meters follow the volume visibly, with a gain of their own

**Status:** **Accepted** — 2026-10-13. George: *"I think we need to go back to
having the spectrum and the view meters depending on the volume ... for fixed,
it should stay like it is now. Also in settings for visualization tweaks
subcategory, we should add a gain setting, which would push the spectrum or
view meters higher."* On the proposal: bars full, needles half; a gain from
−10 to +20 dB, default 0; the row added to the inventory.
**Amends:** [ADR-0057](0057-the-meters-follow-the-volume.md) (how far the
meters follow), [ADR-0058](0058-the-visualisations-ballistics-are-settings.md)
(a fourth tweak row), [ADR-0022](0022-settings.md) (the inventory).

## Context

ADR-0057 has the meters follow the dB the device cuts, and Fixed show the
recording. Read on the devices on 2026-10-13, two things made that look like
nothing:

1. **They followed a third of the cut** (`METER_VOLUME_TRACKING`). The volume
   curve cuts 5.2 dB at 80 % and 11.6 dB at 60 %, so at the levels people
   listen at the needles moved 2-4 dB and the bars 2-4 points out of 100.
2. **After every start, nothing said what the volume was.** The cut is
   written to `/run/gexis/attenuation` only when the level changes, and
   `/run` is empty after a boot. Until a renderer or the slider moved the
   volume, the meters showed the recording at full level. The bar and
   guestpi had no file at all; on sofapi the start-up level (−5.25 dB) was
   logged 29 s before the file was written, when Lyrion took over.
   And switching a USB DAC without a control of its own to Fixed left the
   last cut in the file, so its meters stayed lowered in Fixed.

## Decision

1. **Software and Hardware: the bars follow the whole cut, the needles
   half of it.** A bar unit is 0.963 dB, so the bars drop a point per dB:
   about 21 of 100 at 40 % volume. The needles follow half the dB: 74 % of
   their travel at 80 %, 51 % at 60 %, 32 % at 40 %, 15 % at 20 %. Full on
   the needles would leave them at 10 % by 40 % volume, which George
   found too quiet in September (ADR-0057).
2. **Fixed is unchanged**: the device cuts nothing, so the meters show the
   recording.
3. **The cut is published at every start and on every change of volume
   type**, from the level the core reads at start; Fixed publishes 0,
   whether or not the output has a control of its own.
4. **A Gain row**, fourth under *Display → Visualization → Visualiser
   tweaks*: −10 to +20 dB, steps of 1 dB, default 0. One gain for the
   needles and the bars, in every volume type, Fixed included. It adds to
   what the meters show after the volume: +6 dB doubles a needle's
   reading and lifts each bar 6 points. Values past the top are drawn at
   the top. It changes at once; nothing restarts.
5. **How it reaches the meters**: the core writes the gain to
   `/run/gexis/meter-gain`, at start and on every change, beside the
   attenuation; the meter service re-reads it only when the file changes,
   as it does the attenuation. A missing or unreadable file is 0 dB.

## Consequences

- At the usual listening levels the meters now visibly fall as the volume
  comes down, and the spectrum more than the needles.
- A quiet recording, or listening low, can be lifted with the gain; a loud
  master can be calmed with a negative one.
- How strongly the needles follow became a row the same day (the
  amendment below); the bars' share stays fixed in the code.

## Unverified

When written: how it looks on each panel, which is George's look.

## Amended 2026-10-13: the needles' share is a setting

George, the same day: *"Can you add a setting also [in] visualisation tweaks
for switching to a real amp behaviour ... the setting would have two options -
the one you are currently implementing and the real amp behaviour."*

- **A row, *Needles follow the volume***, under *Visualiser tweaks*, before
  *Gain*: **Half the drop** (default, §1) or **Like a real amplifier** - the
  needles follow the whole cut, as the bars do: 55 % of their travel at 80 %
  volume, 26 % at 60 %, 10 % at 40 %.
- The bars follow the whole cut in both; Fixed is unchanged.
- It reaches the meter service as Gain does: the core writes the fraction
  (0.50 or 1.00) to `/run/gexis/meter-follow` at start and on every change; a
  missing file is half. It applies at once.
- ADR-0022's inventory: the row is `[N]`, in place of the `[H]` entry above.
