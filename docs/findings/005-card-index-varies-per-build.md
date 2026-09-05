# Finding 005 — card index varies per build, even with identical hardware

**Date:** 2026-09-05
**System:** three separate systems, same DAC hardware (HiFiBerry DAC2 HD):
`rig` (hand-built), moOde (SD card 2), `gexis` (pi-gen image, Phase 0).
**Question:** Does the DAC's ALSA card index stay constant across builds?
**Answer:** No.

---

## Observation

Made incidentally during Phase 0 hardware acceptance testing, not a designed
experiment. The HiFiBerry DAC2 HD enumerates as:

| System | Build | Card index |
|---|---|---|
| `rig` | hand-configured Raspberry Pi OS Lite | 3 |
| moOde | SD card 2, reference install | 2 |
| `gexis` | pi-gen image, Phase 0 (this project) | 1 |

Three different indices for the same DAC model, and not a coincidence of a
shared build process — `rig` was configured by hand, moOde is a separate
distribution's own build, and `gexis` was flashed from this project's
`make image` output.

## Why this happens

Not investigated to a mechanism — ADR-0009 already made the index
irrelevant to the product, so root-causing the exact probe order wasn't
necessary to act on this finding. Plausible cause, stated as inference:
card index is assigned in kernel driver-probe order, which depends on what
other sound devices exist and when their drivers load — `dtparam=audio=on`'s
onboard device, USB audio if present, module load timing — differences
unrelated to the DAC itself and invisible from user-facing configuration.

## What this confirms

This is the exact failure mode ADR-0009 exists to prevent. Had the `output`
device definition referenced `hw:2` or `hw:3` on the assumption that "the
DAC is always the same card," `gexis` would have opened the wrong device —
onboard audio, if present, or nothing — while reading as correct in review.
`hw:sndrpihifiberry` was correct on all three systems without modification,
which is the point of the rule, not a coincidence of this particular test.

## Scope

Three systems, one index reading each, at one point in time. Not tested:
whether a single system's own index is stable across its own reboots or
kernel updates — plausible it is not, for the same reason it differs across
systems. Not a claim that card index is *random*, only that it is not safe
to assume, predict, or hardcode.
