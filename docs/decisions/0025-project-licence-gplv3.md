# ADR-0025 — gexis-player is licensed GPL v3

**Status:** Accepted
**Date:** 2026-09-08
**Relates to:** ADR-0015 (skin renderer format), ADR-0016 (plugins as
separate processes)
**Decided by:** George

## Context

gexis-player had no stated licence. Finding 007 established, by reading
source headers rather than repo badges, that the skin renderer we're
adopting (foonerd's PeppyMeter fork — see Finding 007) requires vendoring
two GPL v3 engines:

- `foonerd/PeppyMeter` — GPLv3, full text in `LICENSE`. Every inspected
  source file (`circular.py`, `needlefactory.py`) carries a header
  asserting GPLv3.
- `foonerd/PeppySpectrum` — GPLv3, same form. Confirmed on the file
  inspected (`spectrumutil.py`-equivalent).

Both derive from project-owner's original PeppyMeter/PeppySpectrum, GPLv3
throughout.

The `volumio_*.py` handlers that do the actual per-track rendering
(`volumio_basic.py`, `volumio_spectrum.py`, `volumio_configfileparser.py`,
`volumio_indicators.py`, `volumio_compositor.py`) live inside
`foonerd/peppy_screensaver`, which is MIT-licensed at the repo level. But
those specific files carry no licence header of their own — only copyright
lines — and they import directly from the GPLv3 engines' modules
(`configfileparser`, `spectrum.spectrum`, `spectrumutil`,
`spectrumconfigparser`). They do not function without those imports. The
MIT badge on the repository they physically sit in covers foonerd's own
plugin-glue code (index.js, UIConfig.json, the Volumio-specific install
machinery — none of which we're taking); it does not cover the handlers,
which are only meaningful as part of the combined work with the GPLv3
engine.

## Decision

**gexis-player is licensed GPL v3.**

This is a personal project. The copyleft obligation costs nothing we would
otherwise want, and vendoring the engines is the entire point of the
adopt-the-fork decision — there is no competing goal it trades against.

## Why

We vendor `foonerd/PeppyMeter` and `foonerd/PeppySpectrum`, both GPL v3,
confirmed by reading source headers rather than repo badges (Finding 007).
The `volumio_*.py` handlers sit in the MIT-badged `peppy_screensaver` repo
but carry no licence header of their own and function only by importing
the GPL engine's modules — so the combined work is GPL v3 regardless of
that badge. A GPL v3 project can vendor and distribute this cleanly; a
permissively-licensed one could not, without either re-licensing under GPL
anyway at the point of distribution or not vendoring the engine at all —
which was the entire point of adopting the fork instead of writing our own
renderer.

## What this commits us to

- **Source availability.** Anyone who receives a binary (a flashed image,
  a built package) must be able to get the source of the combined work —
  including build scripts and configuration, not just application code.
  `image/pi-gen` and `image/stage-gexis` are part of what "source" means
  here, not just `core/` and whatever UI code ships.
- **Same rights downstream.** Recipients get the same rights we have: to
  run, study, modify, and redistribute, under the same terms. We cannot
  hand someone a more restrictive licence on top of what we received.
- **Irreversibility once distributed.** GPL v3 is not something we can
  quietly step back from later. Once a GPL-licensed combined work has been
  distributed, taking the project proprietary would mean removing the
  vendored engine entirely and rewriting whatever it did — exactly the
  scope-expansion the decision to adopt the fork (rather than write our
  own renderer) was made to avoid. This is accepted because there is no
  future in which this project intends to go proprietary; if that ever
  changes, it changes by rewriting the renderer, not by relicensing
  around it.

## What was not chosen

**Running the meter engine as a separate process, communicating over a
socket.** ADR-0016 already establishes separate-process plugins with an
IPC contract as this project's general pattern for extending
functionality; the same shape was available here — run PeppyMeter as its
own OS process, feed it data over a socket or pipe, and treat the GPL
binary as an aggregated component rather than a combined work.

This would have weakened the derivation argument (GPL's combined-work
test looks at more than process boundaries, but a socket boundary is at
least a more defensible aggregation claim than importing GPL modules
directly) and would have kept a permissive licence available for the rest
of the project.

**Rejected.** A permissive licence has no value for this project — nobody
downstream is blocked by GPL v3 on a personal Pi build, and there is no
proprietary product on the horizon it would protect. The process-boundary
engineering (a second long-running process, a supervised lifecycle per
ADR-0016's "plugin lifecycle becomes the supervisor's problem," a wire
protocol for what is currently an in-process render loop) is real work
that buys nothing here. Recorded so a later reader — including a future
session tempted to "clean this up" — knows the separate-process shape was
considered and turned down on purpose, not overlooked.

## Consequence for the engine's process shape

This decision does not by itself decide whether PeppyMeter runs in-process
or as a separate process for *architectural* reasons (crash isolation,
fault containment — ADR-0016's actual rationale for plugins). It only
settles that a separate process was not chosen *for licensing reasons*.
The integration approach (proposed separately, following this ADR) is free
to run PeppyMeter as its own process if crash isolation or another
non-licensing reason calls for it; it just can't be sold as a way to keep
part of the project permissively licensed, because that argument does not
hold up in the section above.
