# ADR-0052 — The volume path: what moves the level, how fast, and how loud it may get on its own

**Status:** Accepted — George, 2026-09-22, on the five proposals below:
*"Go for it including the visualiser fix inside 9i."*
**Amended:** 2026-09-22, same day, on his objection to §1 as built:
*"I tend not to like introducing differences between the panel and the phone
or controlling device. We are taking away the decision from the user and
creating what looks like an error because the sound jumps up or down with
the first move of the volume."* **§1 is withdrawn and §3 is redefined** —
see "Amendment" below. Nothing else in this record changes.
**Date:** 2026-09-22
**Raised by:** Phase 9 subphase 9i and
[Finding 045](../findings/045-the-volume-path-measured.md), which measured
the three symptoms he found on the built panel.
**Implements / amends:** [ADR-0018](0018-volume-and-output-modes.md) (the
boot level is no longer the last word), [ADR-0034](0034-panel-volume-travel-and-mute.md)
(what the travel curve is called), [ADR-0035](0035-settings-registry.md)
(two rows)

## Context

Everything here rests on measurement, not on reading the code:

- A drag delivers a *sample* of the gesture to the hardware — 6 of 12 finger
  positions on a fast one, in **4 dB steps** (Finding 045 §2).
- A volume write costs **16.4 ms**, of which 10.7 is our `amixer`
  subprocess; the DAC's own I²C floor is 5.7 ms (§1).
- **The level rises 53 dB thirteen seconds after boot**, untouched, because
  the first renderer to connect restores its remembered level over the boot
  service's (§5). Connecting Spotify put the DAC at **0.00 dB** the same way
  (§7).
- **Spotify attenuates the stream and we attenuate the hardware** — about
  −55 dB where a quarter was asked for, against −37 on LMS (§7).
- A bluealsa meltdown wrote the Bluetooth dummy ~750 times a second, and our
  mirror turned each one into a hardware write (§10).

## Decision

### 1. The boot level stays at silence; the *restore* is what gets a ceiling

`gexis-boot-volume` keeps writing the safe level (ADR-0018). **The design's
60% default is not adopted**, because the measurement shows it would buy
nothing: whatever the boot service writes, the first renderer to connect
overrides it seconds later.

**What gets bounded is the restore.** `resolve_restore` already has a floor —
a remembered level too quiet to look like anything but a fault. It gains a
**ceiling**, `restore_ceiling`, default **−20 dB**: a renderer may not put
the device louder than that on its own. Above it, the user has to ask.

**Why a ceiling rather than a better boot number:** the boot number is not
the hazard. An unattended jump is, and it arrives from a renderer, at boot
and on every acquisition.

> **Withdrawn the same day — see the Amendment.** The paragraph above is
> kept as written because the amendment is an argument against it, and an
> argument against something deleted is unreadable.

### 2. `travel_curve` is renamed to describe what it does

The row offers `dB-linear` and `Perceptual`, defaults to `dB-linear`, and is
unwired — and what the code *does* is ADR-0034's −45…0 dB window, which is
not the design's definition of dB-linear (travel straight to dB across the
hardware's −120…0). Implementing the design's reading would make every
renderer 34 dB quieter at mid-travel.

**So the window is called `Perceptual`, which is what it is**, and
`dB-linear` keeps its meaning for a curve nobody has asked to hear. One
word, no behaviour change, and the row stops describing something untrue.

### 3. `max_ceiling` is enforced where every level passes

In `VolumeBridge.write_hardware`, the one place a level reaches the DAC.
`None` stays the default — no ceiling — and any value clamps every source:
the panel, a renderer's mirror, and a restore alike.

> **Redefined the same day — see the Amendment.** It is still enforced
> there, but as a backstop; the ceiling proper is now a shift on every
> scale rather than a clamp on top of one.

### 4. The write is direct, and a change of more than a step is a ramp

**libasound through `ctypes`, not `amixer`**: 5.7 ms against 16.4, and the
subprocess stays as the fallback if the mixer cannot be opened.

**A new target is walked to, not jumped to.** The panel can only deliver
~33 positions a second (§2), so the hardware is told to fill in the rest:
0.5 dB steps at the DAC's own pace, capped at **120 ms** for the whole move,
and cancelled if another target arrives. A 4 dB gap becomes eight steps and
46 ms — a slide instead of a staircase — and a 53 dB restore stops being an
instantaneous event.

### 5. The mirror is rate-limited

`DummyMixerBridge` writes the DAC for every change of a renderer's dummy
control. When bluealsa melted down that was 750 changes a second (§10).
**At most one hardware write every 40 ms**, latest value wins — below what a
finger produces and far below what a fault does.

### 6. Spotify stops attenuating the stream

`external_volume: true` in go-librespot's config. It keeps reporting volume —
which is what the daemon mirrors to the DAC — and stops touching the audio,
so Spotify matches LMS: full-scale digital, all of the level in hardware.

**This makes Spotify louder at the same setting, by up to 21 dB.** It ships
with the rest of 9i and is tested with the amplifier turned down.

### 7. Two questions answered as asked

- **A renderer that manages its own volume, under fixed output:** the slider
  disappears for everyone (ADR-0046), and Spotify and Bluetooth keep their
  own — a phone's slider is not ours to remove.
- **The mode is per-device**, as ADR-0018 assumed. Nothing measured argues
  otherwise.


## Amendment, 2026-09-22 — a ceiling that shifts the scale instead of clipping it

### What was wrong with §1

`restore_ceiling` clamped the **hardware** on a restore and told nobody.
LMS reconnects at 100, the DAC goes to −20 dB, and LMS still says 100, the
panel says 100, the phone says 100. Then the first nudge of any slider is
not a restore, so the clamp does not apply, and **20 dB arrives in one
move**. That is not a side effect of the design, it is the design; George
named it before it reached him on hardware.

Under a remote-control model (the next record) it is worse still, because
there the whole point is that there is one number and it is true.

### What replaces it

1. **`restore_ceiling` is withdrawn.** §1's hazard is real and measured — 53
   dB thirteen seconds after a boot, untouched (Finding 045 §5). It is
   answered instead by **§4's ramp**, which makes that restore a move rather
   than an event, and by the level being the user's own remembered one. A
   silent clamp that springs later is not a safety feature.

2. **`max_ceiling` becomes the top of every scale rather than a limit above
   one.** With it set to −10 dB, the panel's 100%, LMS's 100 and a phone's
   100 all mean −10 dB. No control anywhere displays a number louder than
   what comes out, and no first move can uncover held-back level.

   > **The row is a percentage from 2026-09-23**, not decibels — George:
   > *"everything must be in percentage. For example the maximum ceiling —
   > if we say 80% then the max output can only be 80% of the max volume."*
   > So the ceiling is a *position*, and its level is whatever the curve
   > makes of that position, which also means it follows the curve when the
   > curve changes. A negative value left over from the decibel row is
   > treated as unset rather than as 0%, because a migration must not be
   > able to mute the device.

3. **It is applied as a shift, not a compression.** Every position-to-dB map
   in `volume.py` — `slider_percent_to_raw`, `dummy_raw_to_db`,
   `spotify_fraction_to_hardware_raw`, and their inverses — adds
   `ceiling_db()`. The window slides down; its span does not change.

   **Why shift rather than compress.** Compressing the window to fit under
   the ceiling would change the size of a step with the setting: the dummy's
   128 values would stop landing on distinct DAC steps, the panel's travel
   would change feel, and the gentle renderer curve recovered on 2026-09-08
   would be re-stretched — the exact mistake that record names. Shifting
   costs only that the bottom of travel goes below −45 dB, which is
   inaudible either way.

4. **The clamp stays as a backstop**, for levels that are not positions: a
   raw value remembered before the ceiling was set, or somebody's `amixer`.
   There is no position to reinterpret in those, so clamping is right.

5. **Changing the row re-applies at once.** If the current level is now
   above the ceiling it comes down through the bridge, so it ramps; and the
   percentage is republished either way, because the scale moved even when
   the level did not.

### Verified on hardware, 2026-09-22

Panel percentage in, DAC dB out, on the device, with nothing playing:

| panel | ceiling unset | ceiling −10 dB | ceiling −20 dB |
| --- | --- | --- | --- |
| 100% | 0.00 dB | **−10.00 dB** | **−20.00 dB** |
| 75% | −11.00 dB | −21.00 dB | −31.00 dB |
| 50% | −22.50 dB | −32.50 dB | −42.50 dB |
| 0% | silence | silence | silence |

100% is the ceiling in every column, and 75%→50% is 11.5 dB in every
column — the window moved, its steps did not change size.

**One rough edge found doing it:** a number row with a `null` default cannot
be written back to `null` through the API (`{"value": null}` is rejected as
"expected a number"), so a ceiling cannot be *cleared* from the settings
screen once set. For this row it is cosmetic — `0` dB is the DAC's own
maximum and behaves identically to unset, and `ceiling_db()` treats any
value at or above 0 as no ceiling. It is noted here because the next
nullable number row may not be so lucky.

### What this does not do

It does not make the panel's number equal the renderer's. That is a
different defect — measured in Finding 045 §12's table, LMS at 25 shows 33
on the panel — and it needs the remote-control model, not a ceiling.

## Consequences

- **No new rows.** `restore_ceiling` was built, objected to and withdrawn
  within the day, before it was ever surfaced in the UI or appended to
  ADR-0022's inventory; `travel_curve` is reworded rather than added; and
  `max_ceiling` was already inventoried, now as `[R]` rather than `[R][?]`.
- **The daemon gains a ctypes dependency on libasound**, present on the
  image by construction (the renderers need it).
- **A ramp means a level change is no longer atomic.** Anything reading the
  hardware mid-ramp sees an intermediate value; the state published to the
  panel is the *target*, so the readout does not crawl.
- **Bluetooth's meter blindness is not this record's** — it is a 9h hole
  being fixed inside 9i, and it needs the DAC free to diagnose.
- **What this does not do:** fixed output (ADR-0046) is still unbuilt, and
  the eight Audio rows are still unwired. This is the path the level travels;
  the rows come next in 9i.
