# Finding 045 — The volume path, measured

**Date:** 2026-09-22
**Question:** Phase 9 subphase 9i opens with this, on three symptoms George
found on the built panel: *"the volume is not increased or decreased
smoothly, there is this delay we introduce a while back"*; *"there are the
occasional hops in volume (especially after a first boot)"*; and *"sometimes
it feels like the max volume is different between renderers (song quality
independent)."* What is actually happening?
**Status:** first half. The tests that need nobody at the speakers are done;
three that need a phone connected are listed at the end and are **also
silent**.

**Scope, stated up front:**

- **Measured on `gexis`**, the image-built device, on 2026-09-22, against the
  deployed build (`v0.2.1-386-gfbfa3dc`). Not on any other hardware, and not
  against any other DAC.
- **What was measured:** the cost of one volume write three ways; what a
  drag on the panel delivers to the hardware at three speeds; the HTTP round
  trip behind each step; LMS's own scale end to end; whether the meter tap
  is before or after the hardware volume; and the level through two cold
  boots.
- **Not measured:** Spotify's and Bluetooth's delivered levels (both need a
  phone), anything about how a ramp *sounds*, and any renderer's behaviour
  under fixed output, which does not exist yet.
- **One instrument was wrong and was caught**: see §6.

## 1. A volume write costs 5.7 ms, and 10.7 ms of the present 16.4 are ours

Three ways of writing the same control, 50 writes each:

| how | per write | a 20-step ramp |
|---|---|---|
| `amixer` subprocess — **what the daemon does today** | **16.4 ms** | 351 ms |
| libasound directly, both channels | **5.7 ms** | 121 ms |
| libasound, one channel | 3.4 ms | |

**The floor is the DAC, not us.** The same libasound call against the two
dummy controls — pure software — takes **0.021 ms**. The 5.7 ms is the I²C
transaction to the PCM1792 on the HiFiBerry, about 2.8 ms per channel. So
the hardware caps volume changes at roughly **175 a second**, and about
two thirds of today's cost is the process spawn.

## 2. The faster you move, the coarser the steps

A drag on the panel's slider, dispatched at three speeds across half the
travel, counting what reached the DAC:

| drag | finger positions | writes that landed | step size |
|---|---|---|---|
| slow, 2 s | 60 | **60** | 1% — 0.45 dB, smooth |
| normal, 600 ms | 30 | **17** | 3–4% — **1.4–1.8 dB** |
| fast, 200 ms | 12 | **6** | 8–9% — **3.6–4.0 dB** |

The level never passes through the values in between. The drawer sends one
request at a time and keeps only the latest while one is in flight
(`VolumeDrawer.svelte`), so the hardware receives a *sample* of the gesture
and the ear hears a staircase. **This is the "small jumps".**

The round trip behind each step, timed in the page: **p50 26–41 ms, p95 up
to 58 ms** — HTTP, the daemon, the 16.4 ms `amixer`, and the state echo. At
30 ms a step the panel cannot deliver more than ~33 a second whatever the
finger does, which is why a 200 ms drag fits six.

**What the numbers say the fix is.** Dropping the subprocess takes a step
from ~30 ms to ~20. That alone is not the answer: the answer is to stop
requiring the panel to deliver every intermediate value. With writes at
5.7 ms the daemon can **ramp** to a target — a 4 dB gap is 8 steps and
46 ms, heard as a slide. The decision is George's, in 9i.

## 3. A second quantisation underneath: 100 positions onto 90 steps

The slider spans −45…0 dB (ADR-0034), so 1% is **0.45 dB**, while the DAC
moves in **0.5 dB** steps. One hundred slider positions therefore land on
ninety distinct hardware values: some 1% moves do nothing at all and the
rest move 0.5 dB. Too small to be the symptom on its own, and it is why a
*slow* drag is not perfectly even either.

## 4. LMS: its own curve, all of it hardware

Setting LMS's own volume by RPC and reading both controls:

| LMS | dummy (`hw:gexislmsvol`, −50…100) | DAC | predicted by `dummy_raw_to_db` |
|---|---|---|---|
| 100% | 100 | — | 0 dB |
| 75% | 59 | — | −12.3 dB |
| 50% | 18 | −24.5 dB | −24.6 dB |
| 25% | −23 | −37.0 dB | −36.9 dB |
| 10% | −50 (floor) | — | −45 dB |

The mirror is exact to the 0.5 dB grid, so `volume.py`'s mapping is right.
Two things to know about it:

- **Nothing moves unless a renderer is active.** With playback stopped, LMS's
  slider moves the dummy and the DAC does not follow at all — the mirror is
  change-driven and bound to the active renderer.
- **squeezelite does not attenuate in software.** Same eight seconds of the
  same track at LMS 100% and at 25%, with the DAC at −∞ so the room stayed
  silent: median meter level **49.5 both times**, p90 71 and 70. All of
  LMS's volume is the hardware, and its digital stream is full-scale
  whatever its slider says.

## 5. The hop after a boot is 53 dB, and `boot_volume` does not survive it

Two cold boots, sampling the DAC and both dummies at 5 Hz from the moment
SSH answered, with the journal for the parts that happen before that:

```
17:29:03.0   boot volume service:  DAC -> 60/240   (-90 dB, "fixed safe level")
17:29:13.0   squeezelite starts
17:29:15.98  LMS dummy jumps 0 -> -23              (LMS pushes its remembered 25%)
17:29:16.20  daemon: "volume: restoring lms to 166/240"
17:29:16.45  DAC reads 166                          (-37 dB)
```

**Thirteen seconds after boot, untouched, the level rises 53 dB.** The size
of that jump is whatever the renderer remembers: at LMS 100% it would be
0 dB, **+90 dB from the boot level**, into an amplifier at whatever gain it
was left at.

So ADR-0018's "fixed safe level" holds for thirteen seconds. **`boot_volume`
as a setting is partly fiction** — whatever it sets, the first renderer to
connect overrides it — and that changes the boot-level question from "what
number" to "what number, and does it survive the renderer".

**One thing this does not separate:** whether the restore came from our own
per-renderer memory (`renderer_volume.py`) or from mirroring the dummy LMS
had just written. Both held the same value here. A run with them deliberately
disagreeing would tell them apart.

## 6. The meter is a pre-attenuation tap, which makes the third question silent

`peppyalsa` is a scope on `pcm.output`, above the hardware slave. With the
DAC at **raw 0 (−120 dB, nothing audible)** a 1 kHz sine still read a
rock-steady **80** on the meter's WebSocket.

So **what each renderer delivers can be compared with the room silent** —
play the same material on each with the DAC at zero and read the meter. That
is how the "max differs between renderers" question gets answered without
anyone listening to anything.

**And the instrument that was wrong.** The first boot trace reported the DAC
stuck at 0 through both services' writes — a striking result, and false.
`amixer sget` prints `Limits: Playback 0 - 240` above the value lines, and
the sampler's `grep -oE "Playback [0-9]+"` matched the limit. The DAC was
never at 0. Caught by checking the claim against a direct read before
reporting it; `docs/LESSONS.md`'s shape exactly, and the reason the boot
numbers above come from a second run.

## What is left, and what it needs

**Silent, but needs a phone connected** — no listening, just a stream:

1. **Spotify's delivered level.** Same measurement as §4's second half: with
   the DAC at zero, does go-librespot's stream sit below LMS's, and does its
   own volume change the digital level? If it does, "100%" means two
   different things and that is the answer to the third symptom.
2. **Bluetooth's delivered level**, the same way — and the phone's own volume
   is in series with ours, which LMS has no equivalent of.
3. **Whether either renderer's remembered level overrides the boot level**
   the way LMS's does.

**Needs the amplifier, and George at it:** how a ramp sounds, and the boot
level itself.
