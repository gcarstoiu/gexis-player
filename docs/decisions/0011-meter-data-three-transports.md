# ADR-0011 — Meter data on three transports from one service

**Status:** Accepted
**Date:** 2026-09-04
**Supersedes:** ADR-0005 (VU metering via PipeWire monitor ports)

## Context

ADR-0005 proposed taking meter data from PipeWire monitor ports and rejected the
moOde approach — an ALSA plugin in the chain — on the grounds that it binds
metering to one output path. ADR-0008 removed PipeWire, so that route is gone.

The original objection does not apply to our design. Every renderer writes to
`output` (ADR-0009), and peppyalsa sits behind `output`, so the tap is
renderer-independent by construction.

Separately, the Peppy screen renderer is undecided in one respect: in-browser
JavaScript is the chosen path (ADR-0014), but PeppyMeter itself and foonerd's
Volumio screensaver remain viable fallbacks. Committing the data transport to
whichever renderer wins would make that reversal expensive.

## Decision

**One visualisation service reads the peppyalsa FIFOs and publishes on three
transports:**

| Transport | Consumer |
|---|---|
| WebSocket | the in-browser skin renderer (primary) |
| PeppyMeter HTTP | unmodified PeppyMeter, droppable in as a plugin |
| peppyalsa FIFO | compatibility with anything expecting the original pipes |

PeppyMeter supports both sending volume data to remote web servers and receiving
it over HTTP; `config.txt` has sections for both. Volumio's peppy_screensaver
uses this for its Remote Display Server mode.

## Parameters

Taken from moOde's working configuration (Finding 001):

```
decay_ms 400
meter "/tmp/peppymeter"          meter_max 100      meter_show 0
spectrum "/tmp/peppyspectrum"    spectrum_max 100   spectrum_size 30
logarithmic_frequency 1          logarithmic_amplitude 1
smoothing_factor 50              window 3
```

Values scale 0-100. Spectrum is 30 bands. Two named pipes.

**The FIFO byte format is not yet determined.** It is needed to read the pipes,
and a `hexdump` with a stream running will settle it.

## Consequences

- The renderer choice for the Peppy screen stays reversible at the cost of two
  extra publishers.
- peppyalsa does not block when the FIFOs have no reader (Finding 002), so the
  service can attach and detach without stalling audio. No startup ordering
  dependency.
- **Meters show programme level, not output level.** moOde taps after `softvol`,
  so its needles drop with the volume; it maintains `/tmp/peppy_gain_db` and a
  gain log, apparently to compensate. Our hardware volume is applied inside the
  DAC, downstream of the tap, so our needles will not move when volume changes.
  Arguably more correct. It is a visible behaviour difference from moOde and is
  deliberate.

## Logged alternative — computing levels ourselves

The visualisation service could compute RMS and FFT itself rather than reading
peppyalsa. That would free us from peppyalsa's `decay_ms`, smoothing and 0-100
scale, and **would remove `type meter` from the audio path entirely**,
sidestepping the tail defect in Finding 003.

It requires our own tap, whose shape is unknown — writing a scope plugin, or
something else.

Not adopted. Recorded so the option is not lost, and because the Finding 003
defect may eventually force the question.
