# ADR-0008 — Direct ALSA, not PipeWire

**Status:** Accepted
**Date:** 2026-09-04
**Supersedes:** ADR-0002 (PipeWire as routing and arbitration layer)

## Context

ADR-0002 chose PipeWire with WirePlumber policy enforcing a single active
renderer. That decision rested on one argument: **Plexamp**. Plexamp headless is
closed-source Node.js and cannot participate in a release protocol. Under direct
ALSA it would either hold the device open or fail with `EBUSY` — and the failure
would be invisible, because it happens inside a process with no way to tell our
UI about it. Under PipeWire we could unlink it without its cooperation.

Plexamp was subsequently moved from Must to Should. The remaining Must-tier
renderers are all cooperative:

- **squeezelite** — open source, closes the device on idle via `-C <seconds>`
- **go-librespot** — open source, HTTP + WebSocket control API
- **Bluetooth** — we own the sink side entirely

A second argument emerged independently of the renderer question: **a sample-rate
change forces a DAC resync regardless of the audio layer.** Switching from a
44.1 kHz LMS track to a 48 kHz Spotify stream produces an audible gap either
way. PipeWire's instant-relink advantage was supposed to win the cross-renderer
case, and that is exactly where it evaporates.

## Decision

**Direct ALSA. No sound server.** Renderers write to a logical device; an
arbitration supervisor controls which one holds it (ADR-0010).

## Reversal condition

This decision is reversed if **a non-cooperative renderer enters Must.** Plexamp
is the named candidate. The reversal is cheap because of the `output`
indirection (ADR-0009): repoint one config file at a PipeWire PCM.

The reversal condition is stated explicitly because in future the reasoning will
not be obvious from the outcome, and someone will reasonably ask why a modern
audio stack was declined.

## Consequences

**Gained**

- Bit-perfect is provable by inspection of the ALSA chain rather than by a
  measurement campaign against a configurable graph.
- The rate shown on the now-playing screen is what the DAC receives. No hidden
  resampler is possible.
- Fewer daemons, faster boot, less to go wrong.
- The LMS multiroom risk flagged under ADR-0002 disappears. Squeezelite's sync
  algorithm depends on accurate output-latency reporting, and there is now no
  buffering layer between it and the driver.

**Lost**

- Takeover is stop → close → open, not a relink. **Unmeasured.** Likely
  dominated by DAC resync on cross-rate switches, but that is an expectation,
  not a result.
- The failure mode is worse. If a renderer will not release, the user gets
  silence with no explanation. This is mitigated by requirement, not by
  architecture: the supervisor runs a timeout ladder (polite stop → SIGTERM →
  SIGKILL) and the UI must display the handoff state.

**Also void as a consequence**

ADR-0003's two playback modes (passthrough and arbitrated) were both PipeWire
constructs and are void. They were independently void anyway: the three reasons
for an exclusive mode were DSD, precision above 24 bits, and provability. The
DAC2 HD is a 192 kHz / 24-bit part with no DSD, so the first two are unreachable
on this hardware and the third is now free.

## Evidence

Findings 002 and 003 establish that the direct ALSA chain works across all 18
format/rate combinations the card advertises and does not modify samples in the
stream interior. A tail defect is open (Finding 003) and does not affect this
decision.
