# ADR-0009 — The logical `output` device

**Status:** Accepted
**Date:** 2026-09-04
**Amended:** 2026-09-05 — the definition was incomplete, not just its
implementation. See "The `ctl` half" below.

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

ctl.output {
    type hw
    card sndrpihifiberry
}
```

## The `ctl` half

The original record showed only `pcm.output` and was wrong to. **The
indirection is the device name, not the PCM block** — a renderer that opens
the mixer through a card index or a raw `hw:` name has bypassed ADR-0009
exactly as much as one that opens the wrong PCM. Hardware volume control,
mute, and any other mixer access resolve through the *control* interface,
not the playback data path, so `output` needed a `ctl` definition as much
as a `pcm` one from the start.

This went unnoticed until Phase 2, because nothing before Phase 2 opened a
mixer through `output` — Finding 002's testing addressed `hw:sndrpihifiberry`
directly. squeezelite's `-V DAC` was the first thing to actually exercise
this half, and its mixer resolution defaults to a ctl device matching the
PCM name it was given (`-O` defaults to `-o`'s value) — not through the PCM's
`slave.pcm` chain, so there was no ctl device named `output` for it to find.

Consequence, confirmed by reading squeezelite's source (ADR-0018 has the
detail): this doesn't fail loudly. It fails silently into software volume.
An ADR that only ever showed the `pcm` half would let this gap get
reintroduced by anyone implementing from the record rather than the current
file.

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
