# ADR-0053 — The panel is a remote control for what is playing, not a second volume

**Status:** **Accepted** — George, 2026-09-22, on
[Finding 046](../findings/046-the-remote-control-path-measured.md)'s
numbers: *"Go"*. He agreed the model in principle the same day (*"For sure
the remote way. That's how it should be."*) and asked for the cost before
approving the build.
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

**Its size is measured** (Finding 046 §9). The panel's fallback window is
ADR-0034's −45…0 dB and the renderers span −38.1…0, so at mid-travel
Bluetooth's 50% reads as 58% the moment it lets go. **Almost all of that is
the panel's window, not the model**: at −38.1…0 the two numbers are
identical at every Bluetooth position, and LMS's seam shrinks from 10 points
to 1–6. Changing it would change what every percentage on the device means,
so it is left as a question for George rather than taken here.

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

The same shape is possible here. **The test was written first, and it found
the fault rather than clearing it:**

- **The direction the model uses is exact.** A panel position sent to a
  renderer and read back is the same integer, at all 101 positions, on all
  four scales in play — LMS's and Spotify's 0–100, Bluetooth's 0–127, and
  go-librespot's 0–65535 fallback. Drag to 37 and 37 comes back.
- **The opposite direction is not, and cannot be.** A value arriving *from*
  Bluetooth, shown as a percentage and pushed back out, lands somewhere else
  for **27 of AVRCP's 128 values**: 101 positions cannot name 128 without
  collisions. Raw 101 shows as 80%, and 80% sends 102. That is Finding 045
  §12's ratchet, one integer at a time.

**So the invariant is not "make the round trip exact", which is impossible
at these scales. It is that a renderer's own value is never sent back to
it.** The panel's percentage is a *view* of what the renderer reported;
only a change whose origin is the panel travels outward. `test_volume.py`'s
`TestTheRemoteRoundTripDoesNotRatchet` pins both halves, including the 27
drifting values, so that nobody later "fixes" the asymmetry by closing the
loop.

## What this does not do

- It does not touch fixed output (ADR-0046), which still does not exist and
  under which the slider disappears everywhere.
- It does not give the panel any level a renderer cannot reach. If LMS is at
  100 there is no more; today the panel could still be pushed under a
  renderer sitting at 50. **That is a real loss**, and it is the reason the
  device has two controls at all. It is traded for one honest number.
- It does not change the boot level, the restore floor, or the ramp.

## Open, for George

1. **The seam in §4, and the cheap way to almost close it.** Moving the
   panel's own window from −45…0 dB to −38.1…0 — the window the renderers
   actually span — makes Bluetooth's two numbers identical at every
   position and shrinks LMS's seam from 10 points to 1–6 (Finding 046 §9).
   It also changes what every existing percentage on the device means, and
   ADR-0034 chose −45 deliberately, so it is not taken here.
2. **Whether §6 is right**: mute local, not sent onward.
3. **Bluetooth's outbound leg is inference until a phone shows it.** If it
   turns out a phone will not follow our push, Bluetooth keeps two numbers
   and the other two renderers do not — the one case where this record
   cannot deliver what it promises.
