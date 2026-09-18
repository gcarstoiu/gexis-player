# Finding 031 — LMS's pause fade moves the player's mixer, and the core hears about the pause 0.5 s late

**Date:** 2026-09-17
**Question:** George, from the Phase 7 step 4 panel check: *"when I pause the
volume goes to 0."* What moves the volume, and what can tell that apart from
a volume change?
**System:** `gexis` on the Phase 6 image with Phase 7 steps hand-installed,
LMS 9.1.1 at `192.168.178.188`, player `gexis`, `digitalVolumeControl` 1,
squeezelite `-o output -O hw:gexislmsvol -V Master -C 1`. Commands by
JSON-RPC from R2D2; levels read with `amixer` on the device and from the
core's own published state.

**Scope:** one player, one server, one album playing. Timings are single
measurements from a handful of repeats, not distributions. Nothing here was
measured with the speakers on; what George heard is his own report.

## Result

**LMS fades the player out on pause by moving the player's mixer control**,
and the core was mirroring that onto the DAC and publishing it as the user's
volume.

Measured on pause, from the core's log (dummy raw, then the DAC value it was
copied to):

| step | dummy raw | DAC |
|---|---|---|
| playing | 22 | 193/240 (−23.5 dB) |
| +0.00 s | 7 | 184 |
| +0.05 s | −6 | 176 |
| +0.10 s | −20 | 168 |
| +0.15 s | −50 | 150 (−45 dB, the floor) |

The panel therefore showed 0% for as long as the pause lasted, and the faded
level was remembered as LMS's own, so a takeover during a pause would have
brought LMS back at −45 dB. On resume the same ramp ran upwards.

**Three things the fade is not:**

- **Not a setting.** `pauseFade`, `volumeFade` and `fadeOnPause` are all
  unset on this player; `transitionType` is 0.
- **Not squeezelite's.** Its `-?` lists no fade option; it only applies what
  the server sends to the control named by `-V`.
- **Not visible in LMS's own volume.** `mixer volume` stayed **52**
  throughout, sampled every 0.15 s across the whole fade.

**What the core learns, and when.** Timed from sending the command to the
frame appearing on the core's `/state`:

| event | reaches the core |
|---|---|
| pause | **+0.51 s** |
| resume | +0.51 s |
| an LMS-app volume change | +0.51 s |

**The fade finishes (0.15 s) long before the pause is known (0.51 s).** That
is what makes a naive gate wrong: two implementations were tried on hardware
first and failed, both recorded here because the shape recurs.

1. **Gate on "is the renderer playing" at the moment each step arrives.**
   Every fade step was still mirrored: the transport reads "playing" for
   another 0.36 s after the fade has run.
2. **Ignore a step unless the renderer's own volume number moved.** The
   report arrives after the steps, so a real change was refused and a later
   fade step, arriving after the number had moved, was mirrored - leaving the
   DAC at levels nobody chose (measured: −45 dB while playing).

**What works (ADR-0018's amendment):** wait for the control to stop moving
for 0.8 s - which clears the 0.51 s report - and only then decide, by the
transport. Measured afterwards, with the speakers off:

| action | DAC |
|---|---|
| playing | 80% (−23.5 dB) |
| pause, twice | unchanged |
| resume, twice | unchanged |
| LMS set to 75% while playing | applied, −12.5 dB |
| LMS set to 30% while playing | applied, −34.5 dB |
| LMS set to 60% while paused | ignored, then applied on resume (−20 dB) |

The panel's published volume stayed at 48% across pause and resume.

**Accepted cost:** an LMS-app volume change reaches the DAC 0.8 s after the
control stops moving, so a single tap of volume-up is applied about a second
later. A drag now produces one write instead of one per step.

## Not covered

- **Bluetooth.** Its volume does not fade, so `bluealsa-aplay`'s control is
  mirrored as it moves, unchanged. Whether any phone fades on pause was not
  tested.
- **Whether 0.8 s is right.** It clears one measured 0.51 s report on one
  network. A slower report would let a fade through again; a faster one
  would allow a shorter, more responsive settle.
- **Audible behaviour.** Whether the pause itself still sounds clean with
  the fade no longer reaching the DAC is George's check, with the speakers
  on.
