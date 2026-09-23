# ADR-0058 — How the visualisation moves is three settings

**Status:** **Accepted and built**, 2026-09-23. George: *"Add these as
settings for me to tweak as I please for both meters and spectrum. 3
settings if I am not mistaken. Can you put them inside settings display,
visualisation, but under a submenu called meters and spectrum tweaks?"*
**Date:** 2026-09-23
**Relates to:** [ADR-0011](0011-meter-data-three-transports.md) (the
transports), [ADR-0022](0022-settings.md) (the inventory),
[ADR-0055](0055-which-output-the-device-plays-to.md) (`output.conf` is
rewritten per output), [Finding 051](../findings/051-the-spectrum-pipe-and-the-bars-must-agree.md)
and [Finding 052](../findings/052-the-spectrum-pipe-had-no-frames-in-it.md)
(where these numbers were found and measured)

## Context

Three numbers decide how the visualisation *moves*, as opposed to what it
measures. All three shipped as constants nobody could reach, and a day of
George looking at the screen produced a different verdict on each of them:
*"the vu meters feel too fast"*, *"too slow now"*, *"the spectrum is almost
flashing"*. They are a matter of taste and the device's owner is the one
with the taste.

They live in two files belonging to two other programs, and neither program
re-reads its file.

## Decision

**Three rows under a new group in Display → Visualization, "Meters and
spectrum tweaks".**

| row | unit | default | what it is underneath |
| --- | --- | --- | --- |
| **Spectrum smoothing** | % | 90 | peppyalsa's `smoothing_factor` |
| **Needle fall time** | ms | 400 | peppyalsa's `decay_ms` |
| **Needle smoothing** | ms | 240 | PeppyMeter's `smooth.buffer.size` |

- **A group, not a nested page.** Every cluster in Settings is a `group`
  heading — Panel, Home screen, Idle screen, LMS, Bluetooth — and the
  registry has no other kind of nesting. This is the same shape as all of
  them.
- **Spectrum smoothing stays a percentage**, because that is literally what
  it is: how much of each bar's previous height is kept on every block. It
  could be shown as a time constant, but the block rate is the ALSA
  period's, so the milliseconds would change with the sample rate and the
  number would be a lie at 96 kHz. The row's note carries the measured
  times at 44.1 kHz instead — 50 settles in about 30 ms, 90 in 200 ms, 97
  in 0.7 s.
- **The two meter rows are milliseconds**, because both are times and stay
  times. `smooth.buffer.size` is a count of samples PeppyMeter reads every
  40 ms, so the row is the window and the count is derived — rounded to the
  nearest step, with a floor of one sample, because a buffer of zero turns
  the averaging *off* rather than shortening it.

**Applying them costs something, and each row says so.**

- `spectrum_smoothing` and `meter_fall` are peppyalsa's, and peppyalsa is
  configured in `/etc/alsa/conf.d/output.conf`. ALSA reads that when a PCM
  is *opened*, so the renderers are stopped, the file is rewritten and they
  are restarted — the same path an output switch takes, and for the same
  reason. **It stops whatever is playing.**
- `meter_smoothing` is PeppyMeter's, which reads its config once at start,
  so the visualiser restarts. Only when the file actually changed: the
  writer returns whether it wrote, and an unchanged file does not restart
  anything.

## Consequences

- **`output.conf` gains a second reason to be rewritten.** It was the
  output's file; it is now also the tuning's. `outputs.render` takes a
  `Tuning`, defaulting to what the image ships, and `_switch_output` passes
  the current settings so a switch does not quietly reset them.
- **The defaults are the shipped values and the test says so**, which is
  what keeps the template and the image's own `output.conf` from drifting
  apart.
- **A converted chain keeps the scope definition and attaches nothing.**
  On HDMI there is no meter at all, so these rows write numbers nothing
  reads. Harmless, and cheaper than a fourth conditional in the template.
- **Three rows join ADR-0022's inventory as `[R]`**, on George's own ask.
- **Nothing here changes what the visualisation measures** — the band
  count, the pipe, the 30 bands and the volume tracking are all elsewhere.

## Alternatives considered

- **A nested settings page.** Rejected for now: it is navigation the
  Settings screen has never had, for three rows. Offered to George.
- **Expose the raw `smooth.buffer.size` count.** Rejected: "6" means
  nothing to the person choosing it, and the 40 ms step is ours to know.
- **Apply the peppyalsa numbers without restarting the renderers.**
  Not possible: ALSA reads the config at open, and the running scope keeps
  what it was given.
- **A fourth row for how far the meters follow the volume**
  ([ADR-0057](0057-the-meters-follow-the-volume.md)'s
  `METER_VOLUME_TRACKING`). Not added: George said three, and that one is
  still an Open rather than a taste.

## Open

- **Whether the defaults are right.** 90 / 400 / 240 are where the day
  ended, not where anyone has settled.
