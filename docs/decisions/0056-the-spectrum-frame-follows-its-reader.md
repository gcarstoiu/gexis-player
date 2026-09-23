# ADR-0056 — The spectrum frame is the size its reader expects

**Status:** **Proposed**, built and running on the device so George can look
at it. **Date:** 2026-09-23
**Raised by:** [Finding 051](../findings/051-the-spectrum-pipe-and-the-bars-must-agree.md),
which found the flashing George reported was a framing fault I had
introduced hours earlier
**Relates to:** [ADR-0011](0011-meter-data-three-transports.md) (the relay
and its three transports), [ADR-0015](0015-skin-renderer-peppymeter-format.md)
and [Finding 049](../findings/049-the-spectrum-draws-more-bars-than-it-has-room-for.md)
(how many bars a skin draws)

## Context

Three numbers have to agree and two of them are not ours:

- **peppyalsa** measures a fixed number of bands, `spectrum_size` in
  `/etc/alsa/conf.d/output.conf`. It is 30, and changing it means reopening
  the PCM, which means stopping the renderers.
- **A skin** draws as many bars as its own artwork has room for — 20, 21 or
  22 across both installed packs, never 30.
- **The pipe between them carries bytes.** PeppySpectrum reads
  `4 × size` of them at a time and keeps a read only if it got exactly that
  many, so a record of any other length is read across its own boundaries
  and every bar shows a different band each refresh.

Before Finding 049 the skin's count *was* 30 for every skin, so the three
agreed by accident while the bars overflowed their frames. Fixing the
overflow broke the agreement.

## Decision

**The relay writes the spectrum frame at the size its reader expects, and
learns that size from the reader's own configuration.**

- `FifoPassthrough` reads `size` from the spectrum engine's `config.txt` —
  the file the driver already rewrites on every skin change — and re-reads
  it only when the file changes.
- It folds its 30 bands into that many, **taking each group's peak**. A bar
  stands for the loudest thing in its range; a mean would pull every
  doubled band down and make the display quieter than the music.
- **It never folds upward.** Asked for more values than it has, it writes
  what it has. That cannot happen — the count is capped at the band count
  where it is computed — and inventing bands would be worse than the
  mismatch.
- **The WebSocket and HTTP consumers keep all 30.** The fold is the pipe's,
  because the pipe is what has a frame size; the panel draws its own
  visualiser and should have every measurement.

## Consequences

- **peppyalsa stays at 30 bands.** No skin change touches ALSA, nothing
  reopens the PCM, and the measurement keeps its resolution whatever a skin
  chooses to draw.
- **A skin that draws 22 bars shows 22 peaks of 30 bands** — eight bars
  cover two bands each and fourteen cover one. That unevenness is inherent
  to any non-integer ratio and is not visible on a bar display.
- **The relay now depends on a file the driver writes**, across two
  services. It degrades to "change nothing" if the file is missing or
  unreadable, which is the old behaviour, so a broken read cannot make the
  screen worse than it was.
- **`spectrum_consumer_config` is a new key** in `core.toml`'s `Config`. It
  is a path, not a preference, and is **not** proposed for ADR-0022's
  inventory.

## Alternatives considered

- **Set `spectrum_size` per skin in the ALSA config.** Rejected: skins
  rotate per track, and each change would have to stop every renderer and
  reopen the device.
- **Narrow the bars so 30 fit.** Rejected, as in Finding 049: the bar is a
  sprite the skin's author drew at a fixed size.
- **Draw 20 bars everywhere and set the pipe to 20.** Rejected: it is the
  blanket cut in resolution George ruled out, and it would still leave the
  pipe at 30 bands unless peppyalsa were reconfigured too.
- **Frame the pipe ourselves, with a header or a delimiter.** Rejected: the
  reader is PeppySpectrum and it is not ours. The frame has to be what it
  already expects.

## Open

- **How fast the spectrum should feel.** `smoothing_factor` is 90 today
  (about 110 ms, against the 17 ms that shipped). A guess at a middle, and
  George has not yet seen a correctly framed spectrum at any other value.
