# ADR-0093 — We do not build or patch the renderers

**Status:** **Accepted — immovable.** George, 2026-09-26: *"We will not build our
own squeezelite or golibrespot now or ever - this you can record as an immovable
decision."*
**Date:** 2026-09-26
**Raised by:** [Finding 091](../findings/091-play-on-a-powered-off-lms-player.md)
and [ADR-0091](0091-a-plugin-renderer-is-taken-off-the-device.md)'s amendment,
which both named a quick-retry patch as the one lever that would remove a gap.

## Decision

**squeezelite and go-librespot are taken as their upstreams ship them** -
squeezelite from the distribution's package, go-librespot as the pinned upstream
release binary (ADR-0021's pins). We do not build either from source, and we do
not carry patches to either. **Not now and not later: this is not a deferral.**

A defect that only a change inside one of them would fix is solved around it -
by arbitration, by configuration they expose, by their APIs, or by the protocol
that drives them - or reported upstream. "Patch the renderer" is not an option
to present.

## Why

George's call, recorded as he made it. The reasons it rests on are the ones this
project already works by: a renderer we build is one we maintain, on every
upstream release, for the life of the device; the image pins what upstream
published, so what ships is what upstream shipped (ADR-0021, and Phase 11's
criterion 2 for plugins); and a fork is the kind of hidden dependency
`fetch-cached.sh` refuses for the build cache.

## Consequences

- **Finding 091's 5 s** (squeezelite's fixed retry after a busy open) and
  **ADR-0091's residual race** (go-librespot giving up on a busy open) must be
  answered some other way. Leaving them as they are is not acceptable either
  (George, same message).
- Plugins are unaffected: `gexis-plexamp` is ours by design, and Plexamp itself
  is taken as its upstream ships it, which this record already covers in spirit.

## Reversal conditions

None. George recorded it as immovable.
