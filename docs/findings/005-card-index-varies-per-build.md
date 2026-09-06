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

## Update, 2026-09-06 — same machine, same image, different rebuild: also varies

Answers the open scope question above, on `gexis` specifically: not
"reboot," but "rebuild" — a fresh `make image` of the same
`phase-2b-arbitration` source, reflashed onto the same hardware.

| Build | Card index |
|---|---|
| Phase 0 (original) | 1 |
| Phase 2b (this rebuild, same source, same hardware) | 2 |

This is a **stronger** version of the finding than the one above: it isn't
only that different systems assign different indices, but that rebuilding
and reflashing *the same system* can too. Nothing in the build pins probe
order, so there is no reason to expect it to hold constant even between
two builds nominally producing "the same" image. Still not root-caused to
a mechanism (see "Why this happens" above — same reasoning applies, and
still isn't necessary to act on given ADR-0009). Reinforces, rather than
changes, the existing rule: `hw:sndrpihifiberry`, never an index, anywhere
— including in ad hoc test/debug commands run by hand during hardware
sessions, not only in shipped config.
