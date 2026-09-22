# ADR-0052 — The volume path: what moves the level, how fast, and how loud it may get on its own

**Status:** Accepted — George, 2026-09-22, on the five proposals below:
*"Go for it including the visualiser fix inside 9i."*
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

## Consequences

- **Two new rows**: `restore_ceiling` and nothing else — `travel_curve` is
  reworded rather than added. `restore_ceiling` goes to ADR-0022's inventory
  as `[N]`, pending George.
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
