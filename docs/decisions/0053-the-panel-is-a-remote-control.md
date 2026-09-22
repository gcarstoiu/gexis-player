# ADR-0053 — The panel is a remote control for what is playing, not a second volume

**Status:** **Proposed** — George asked for the model in principle (*"For
sure the remote way. That's how it should be."*, 2026-09-22) and for numbers
before implementation is approved. The numbers are
[Finding 046](../findings/046-the-remote-control-path-measured.md). **Not
started.**
**Date:** 2026-09-22
**Raised by:** George, on the built panel: *"The volume bar in the panel
still has a weird behaviour. If LMS is at 25 I expect the volume on the
panel to also 25."*
**Would amend:** [ADR-0018](0018-volume-and-output-modes.md),
[ADR-0034](0034-panel-volume-travel-and-mute.md) (what the panel's number
*is*), [ADR-0052](0052-the-volume-path.md) (which path a panel change takes)

## Context

The panel's slider and the renderer's slider are **two controls in series**.
One sound, two numbers, measured (Finding 046 §1):

| LMS says | DAC | panel says |
| --- | --- | --- |
| 100 | 0.00 dB | 100 |
| 75 | −5.50 dB | 88 |
| 50 | −17.50 dB | 61 |
| 25 | −30.00 dB | **33** |
| 10 | −38.00 dB | 16 |

Neither is wrong — they measure different things. There is simply no reading
of "the volume" under which both are true, and the device has two of them.

## Decision

**The panel's volume control is the active renderer's volume control.** Not
a conversion between two scales, not a second attenuation: the same control,
shown on another surface. The panel joins LMS's web UI, iPeng, the Spotify
app and a phone's own slider as one more thing that moves the one number.

### 1. A change on the panel is sent to the renderer, not to the DAC

| renderer | channel | measured |
| --- | --- | --- |
| LMS | the server's JSON-RPC `mixer volume N` | 16–26 ms to the control (§2) |
| Spotify | `POST /player/volume` on go-librespot | 2–5 ms (§4); **already built** |
| Bluetooth | write `gexisbtvol`; `bluealsa-aplay --volume=mixer` pushes AVRCP | the write, ~6 ms (§5); **outbound unverified — needs a phone** |

The DAC then moves the way it already does, through the existing mirror.
**No new path to the hardware is created.** The panel stops having one of
its own.

### 2. For LMS it must be the server, not the control

Measured, and it decides the design: **squeezelite does not carry an
external mixer change back to LMS** (§3 — ten seconds, no change, the
control still holding the written value). Writing the dummy directly would
leave LMS showing one number and the device at another, which is the defect
this record exists to remove.

### 3. The number shown is the renderer's own

While a renderer is active the panel displays *its* value on *its* scale.
LMS and Spotify are 0–100, which is the panel's own scale exactly; Bluetooth
is 0–127, and 0–100 → 0–127 → 0–100 round-trips to the same integer at every
point (§6). So the panel shows 0–100 throughout and never has to invent a
number.

### 4. With nothing active, the panel keeps today's behaviour

There is no remote to be. The slider writes the DAC directly and shows the
DAC's own percentage, exactly as now.

**This is the model's one seam and it is named rather than hidden:** the
number means "this device" when nothing is playing and "this renderer" when
something is. They are not the same scale. In practice the drawer is a thing
people touch while listening, but a level set at idle will not be the same
percentage once a renderer takes over — the same event that already
overrides it today (Finding 045 §5).

### 5. `max_ceiling` still means what ADR-0052's amendment says

The renderer's value reaches the DAC through the same map, which carries the
ceiling shift. So the renderer's 100, the panel's 100 and a phone's 100 all
remain the ceiling. The two records compose without either changing.

### 6. Mute stays local

ADR-0034's mute writes silence to the DAC and puts the level back. It is not
sent to the renderer: muting the device should not reset a phone's slider to
zero, and unmuting should not be a volume change anyone else sees.

## What it costs, measured

Per step, against today's ~15–30 ms (Finding 046 §7):

| renderer | added |
| --- | --- |
| Bluetooth | **+6 ms** |
| Spotify | **+10 ms** |
| LMS | **+22–33 ms** |

Plus up to the mirror's 40 ms rate limit in the worst case.

**LMS roughly doubles the per-step cost**: ~20 positions a second instead of
~33. The panel already delivers only a *sample* of a drag — 6 of 12 finger
positions on a fast one (Finding 045 §2) — and this halves the sample again.
**ADR-0052 §4's ramp becomes load-bearing**, not a nicety: what the ear hears
between the samples is the ramp, measured at 46 ms for a 4 dB gap.

## The risk, stated before it is built

**This makes a second two-way volume sync, and the first one ratcheted.**
Finding 045 §12: AVRCP's 128 values against the dummy's 151 meant a value
went out and came back different, every drift was a fresh change, and the
loop only settled by luck — until bluealsa died of it.

The same shape is possible here: panel percent → renderer value → dummy →
DAC raw → published percent. If that chain is not idempotent, a drag feeds a
ratchet. §3's scales are chosen so that it is (0–100 and 0–127 both
round-trip exactly), and the echo machinery already exists
(`_expected_adapter_value`, `_written`), but **an idempotence test across all
three chains is a precondition of building this, not a thing to verify
afterwards.**

## What this does not do

- It does not touch fixed output (ADR-0046), which still does not exist and
  under which the slider disappears everywhere.
- It does not give the panel any level a renderer cannot reach. If LMS is at
  100 there is no more; today the panel could still be pushed under a
  renderer sitting at 50. **That is a real loss**, and it is the reason the
  device has two controls at all. It is traded for one honest number.
- It does not change the boot level, the restore floor, or the ramp.

## Open, for George

1. **The seam in §4** — the number meaning "the device" at idle and "the
   renderer" while playing. The alternative is no slider at all when nothing
   is active, which is worse.
2. **Whether §6 is right**: mute local, not sent onward.
3. **Bluetooth's outbound leg is inference until a phone shows it.** If it
   turns out a phone will not follow our push, Bluetooth keeps two numbers
   and the other two renderers do not — the one case where this record
   cannot deliver what it promises.
