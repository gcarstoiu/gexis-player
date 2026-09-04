# ADR-0017 — The core daemon is Python

**Status:** Accepted
**Date:** 2026-09-04

## Decision

**The core state daemon and its services — visualisation, enrichment, lyrics —
are written in Python.**

## Rationale

- Mature ALSA and D-Bus bindings, which is most of what the core does: mixer
  control, BlueZ signals, subscribing to ALSA ctl events.
- The surrounding ecosystem is Python. PeppyMeter, PeppySpectrum and the Volumio
  screensaver are all Python, so their formats and conventions are directly
  readable.
- Development speed matters more than runtime speed for this workload. The core
  handles events and proxies lists; it is not in the audio path.

## Why the language choice is low-risk here

ADR-0016 put plugins in separate processes with an IPC contract, so **this
choice does not propagate.** Plugins can be written in anything. Had plugins
been in-process modules, choosing Python for the core would have bound every
future renderer adapter to Python, and the decision would have carried far more
weight.

## Consequences

- The core is not in the audio path. Renderers write to `output` directly; the
  core only decides who is allowed to. Python's performance characteristics
  therefore do not bear on playback.
- **The library proxy is in Python and is in the interactive path.** Every list
  scroll passes through it (ADR-0020). Aggressive in-RAM caching is required, in
  line with the principle of spending the hardware on responsiveness.
- Packaging into a flashable image must pin the interpreter and dependency
  versions. A moving Python version is a reproducibility hazard for an image
  build.

## Not decided here

The web UI framework, and whether any component is later rewritten in a compiled
language if measurement demands it. Neither is blocked by this decision.
