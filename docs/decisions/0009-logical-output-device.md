# ADR-0009 — The logical `output` device

**Status:** Accepted
**Date:** 2026-09-04

## Context

ADR-0008 chose direct ALSA and recorded a reversal condition. A reversal is only
cheap if renderers are not bound to a concrete device.

moOde solves the same problem with `_audioout`: every renderer targets one
logical name, and `_sndaloop.conf` swaps what sits behind it by adding and
removing trailing underscores from `pcm.!_audioout__`, driven by a job from
`snd-config.php`. The rename mechanism is crude, but the pattern is validated by
a shipping product (Finding 001).

## Decision

**Every renderer targets a logical ALSA device named `output`. Nothing
references `hw:` directly. Nothing references a card index.**

The device name is part of the renderer plugin contract, not a convention.

Current definition:

```
pcm.output {
    type meter
    slave.pcm "hw:sndrpihifiberry"
    scopes.0 peppyalsa
}
```

## Card index is never used

Verified: the DAC2 HD is card **3** on a stock Raspberry Pi OS Lite image and
card **2** on moOde, because stock `config.txt` carries `dtparam=audio=on`,
which adds an onboard device at index 0. Loading `snd-aloop` added a further
card without displacing it, but that was a post-boot load and ordering under
`/etc/modules` was not tested.

moOde hardcodes `card 2` and `plughw:2,0` and gets away with it by regenerating
those files. We do not regenerate, so we use `hw:sndrpihifiberry`.

## Consequences

- Adopting PipeWire becomes a one-file change rather than a renderer migration.
- Inserting or removing the metering tap, changing DSP, or switching to a
  loopback for testing are all config changes invisible to renderers.
- The definition of `output` becomes a single point of failure and a single
  point of audit. For a bit-perfect claim that is an advantage: there is exactly
  one file to inspect.
- Plugins written by third parties cannot accidentally bypass the tap or the
  arbitration model by opening the card directly — or rather, if they do, it is
  a contract violation that can be detected.

## Note

`type plug` must not appear in the `output` chain. It converts silently when
formats do not match, which would defeat the bit-perfect claim without any
visible symptom. Renderers are configured to match the hardware format instead.
moOde's chain has `plug` at the top and is not bit-perfect as configured; ours
deliberately does not.
