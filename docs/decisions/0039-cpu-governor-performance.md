# ADR-0039 — The CPU governor is `performance`, set by a unit in the image

**Status:** Accepted
**Date:** 2026-09-17
**Raised by:** George, during the Phase 7 step 4 panel checks: *"in what CPU
governor is the Raspberry Pi operating? If not performance, switch to
performance and make sure it survives a reboot and reflash."*

## Context

The panel's screen changes and the New Music strip did not feel smooth to
George (step 4c). Sizing artwork to what is drawn and cutting the mask work
did not visibly help, which left the question of what the CPU is doing while
a screen animates.

Measured on `gexis`, 2026-09-17, on the Phase 6 image:

| | |
|---|---|
| governor | `ondemand` (Raspberry Pi OS default) |
| range | 600 MHz – 1800 MHz |
| SoC temperature, idle-ish | 66.2 °C |
| `vcgencmd get_throttled` | `0x80000` — the soft temperature limit **has** been reached at some point since boot (not currently throttled) |

`ondemand` raises the clock only after it sees load. A 140 ms screen
animation, or one flick of a horizontally scrolling strip, is exactly the
kind of short burst that can finish before the governor has responded.

## Decision

**The governor is `performance` on every policy, set at boot by
`gexis-cpu-governor.service`**, installed and enabled by
`image/stage-gexis/03-core` so a reflash keeps it, and enabled on the
running device so a reboot keeps it. `image/verify-image.sh` checks both the
unit file and its enablement, like every other unit.

Measured immediately after the switch: all four cores at 1800 MHz, 67.2 °C.

## What this costs

- **Heat and power.** The clock no longer drops to 600 MHz when idle. The
  soft temperature limit had already been reached on this device *before*
  the change, so the headroom was not large to begin with. Nothing here is a
  thermal measurement over time: **see Unverified.**
- **Nothing else is pinned.** GPU clocks, `force_turbo` and the voltage are
  untouched; this is the kernel's cpufreq policy only.

## Alternatives not taken

- **`ondemand` with a lower `up_threshold`.** Keeps some idle saving, but it
  is another tuning knob to justify, and George asked for `performance`.
- **`force_turbo=1` in `config.txt`.** Pins the clock below the kernel
  entirely, sets the warranty bit on some models, and does not answer a
  scheduling question the governor already answers.
- **Setting it from `gexis-core`.** The daemon would then own a machine-wide
  policy that has nothing to do with arbitration, and a core restart would
  become a moment where the policy could change.

## Unverified — do not treat as settled

- **Whether it makes the panel smoother.** George's check. The measurements
  above say what the CPU is doing, not what the screen looks like.
- **Steady-state temperature under playback with the screen busy**, and
  whether the soft limit is reached more often. One reading a minute after
  the switch (67.2 °C against 66.2 °C) is not a thermal result.
- **Idle power draw.** Not measured; this device has no meter on it.
- **Whether the audio path benefits at all.** Plausible, unmeasured.
