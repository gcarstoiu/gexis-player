# Finding 045 — The volume path, measured

**Date:** 2026-09-22
**Question:** Phase 9 subphase 9i opens with this, on three symptoms George
found on the built panel: *"the volume is not increased or decreased
smoothly, there is this delay we introduce a while back"*; *"there are the
occasional hops in volume (especially after a first boot)"*; and *"sometimes
it feels like the max volume is different between renderers (song quality
independent)."* What is actually happening?
**Status:** LMS and Spotify measured. Bluetooth is the one renderer left,
and it needs a phone connected and nothing else. **§7 is the answer to the
third symptom, and it is a defect, not a scale difference.**

**Scope, stated up front:**

- **Measured on `gexis`**, the image-built device, on 2026-09-22, against the
  deployed build (`v0.2.1-386-gfbfa3dc`). Not on any other hardware, and not
  against any other DAC.
- **What was measured:** the cost of one volume write three ways; what a
  drag on the panel delivers to the hardware at three speeds; the HTTP round
  trip behind each step; LMS's and Spotify's scales end to end; whether the
  meter tap is before or after the hardware volume; and the level through
  two cold boots.
- **Not measured:** Bluetooth's delivered level (needs a phone paired and
  connected), anything about how a ramp *sounds*, and any renderer's
  behaviour under fixed output, which does not exist yet.
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

## 7. Spotify attenuates the stream *and* we attenuate the hardware

George connected Spotify and started playing. Two things were true before
anything was measured: go-librespot reported **volume 100 of 100**, and the
DAC was at **0.00 dB** — the daemon had put it there on acquisition
(`volume: restoring spotify to 240/240`), up from the −37 dB LMS had left.

Stepping go-librespot's own volume through its API, watching the DAC and the
meter — the meter being pre-attenuation, so it reports what the *stream*
carries:

| go-librespot volume | DAC | stream (median / p90 / max) |
|---|---|---|
| 100 | **0.00 dB** | 35 / 64 / 68 |
| 25 | **−34.00 dB** | **2 / 5 / 6** |

**Both are applied.** At 25 the stream itself is down by a factor of about
eleven — **−21 dB** — *and* the DAC is at −34 dB. Together that is roughly
**−55 dB where the user asked for a quarter**. The same quarter on LMS is
−37 dB and nothing else, because squeezelite delivers full scale (§4).

**That is the third symptom.** It is not that the renderers' maxima differ —
at 100% both deliver full scale into a 0 dB DAC. It is that **everything
below maximum is attenuated twice on Spotify and once on LMS**, so the two
diverge by up to 21 dB as you come down, and the same panel percentage means
two different loudnesses.

**The fix is a config key, and it has a physical consequence.** This build of
go-librespot supports `external_volume`, `disable_volume`, `mixer_device`,
`mixer_control`, `volume_steps` and `initial_volume`; our config sets **none
of them**, so it runs its default software volume. `external_volume: true`
keeps the phone's slider working and the events flowing — which is what the
daemon mirrors to the DAC — while stopping go-librespot touching the stream.
`mixer_device` would make it write the hardware itself, which would give the
DAC two writers; `disable_volume` would take the phone's slider away.

**It will make Spotify louder at the same setting**, by up to 21 dB.
Changing it belongs at 9i's gate, with the amplifier turned down first.

## 8. Bluetooth: the meter sees nothing, and nothing mirrors its volume

George connected a phone over Bluetooth and started playing. What is
certain, measured while it ran:

- **Audio is flowing.** `/proc/asound/card5/pcm0p/sub0/status` reads
  `state: RUNNING` with `hw_ptr` advancing, and BlueZ's
  `MediaTransport1.State` is `active`, codec SBC.
- **The phone is at AVRCP 16 of 127** (≈12%), and bluealsa reports
  `SoftVolume: false` — so bluealsa is not attenuating; it delegates to the
  mixer it was given, which is the dummy `hw:gexisbtvol`.
- **Nothing mirrored that to the DAC.** The daemon logged no `restoring
  bluetooth`, the DAC sat at **0.00 dB** where Spotify had left it, and the
  dummy reads **0** — which our own mapping calls −30 dB. The mirror is
  change-driven (§4) and the dummy has not changed all session, so this may
  be "no event yet" rather than "not wired"; moving the phone's volume would
  tell them apart.
- **The meter produced nothing at all.** Not "low" — *nothing*: zeros on the
  service's WebSocket for 15 s, and **zero bytes** read directly from
  `/tmp/peppymeter` for 3 s with the service stopped. Unchanged after
  restarting `bluealsa-aplay` cleanly with the reader running. Yet
  `libpeppyalsa.so` **is** mapped into its process (4 entries in
  `/proc/<pid>/maps`), so the scope is loaded and in the chain.

**If that holds, the visualiser is blind on Bluetooth** — flat needles and
no bars while music plays — which nothing in Phase 5 would have caught,
because the meter was proved against LMS.

**What it cannot be concluded from here** is whether the stream carries
audible content at all: a phone that sends near-silence and a meter that
cannot see the stream look identical from this side. That takes one ear and
one phone: is it audible, and does moving the phone's volume move the DAC?

## 9. Bluetooth's volume oscillates when the phone's slider is dragged

George, minutes after §8: *"when trying to put the Audio up or down on my
phone the volume bar on my phone goes up and down continuously and I can't
control it anymore... Maybe you left some measuring tools on?"*

**Nothing of mine was running** — checked for every script, loop and reader
this session had used, on the device and on the build host, before looking
any further.

**What it is.** 1280 volume events in three minutes, about **40 a second**,
with the dummy control thrashing: `48 → 20 → 9 → 13 → 37 → 35 → 70 → 56 →
68 → 61 → 32 → 3`. It is **not self-sustaining** — zero events in the thirty
seconds after he stopped touching the phone — so it runs only while the
slider is moved.

**Our daemon is downstream of it.** `volume.py` only ever *reads* the dummy
controls (`get_raw` on `hw:<dummy>`) and only ever *writes* the real DAC.
Nothing of ours writes `gexisbtvol`, so those values are bluealsa-aplay's,
carrying the phone's AVRCP updates. The mirror faithfully copies each one to
the hardware, which is what it is for.

**Where the loop closes, most likely.** `--volume=mixer` was added on
2026-09-10 (Finding 012) to fix a frozen Bluetooth ceiling, and it makes
bluealsa-aplay sync the ALSA mixer **both ways**: AVRCP in, and mixer
changes back out to the phone. The two scales do not round-trip — **AVRCP is
0–127 and the dummy is −50…100**, 128 steps against 150 — so a value that
goes out and comes back need not land where it started. That is the same
shape as the Spotify ratchet this module's own docstring describes ("two
scales ... cannot round-trip exactly"), which was solved there with an echo
window.

**Why it has not been seen before:** it needs a *drag*. Single steps settle;
rapid updates cross with the outgoing ones.

**What would prove it** is an A/B that needs the phone: stop `gexis-core`,
so our mirror is out of the picture entirely, and drag the slider. Still
oscillating means the loop is bluealsa↔phone and ours only inherits it.

**A candidate fix we already have the lever for:** `snd-dummy` exposes
`mixer_volume_level_min` / `mixer_volume_level_max` as module parameters
(currently the defaults, −50 and 100). Setting the Bluetooth dummy's range
to **0…127** makes the AVRCP round trip exact. Both dummy cards come from
one module instance, so LMS's range moves with it and `volume.py`'s
`DUMMY_MIN_RAW`, `DUMMY_MAX_RAW` and `DUMMY_DB_STEP` have to move with that
— which is 9i work, not a change to make while a phone is connected.

## 10. What the oscillation actually was: bluealsa melting down, and crashing

§9's A/B ran and **came back clean** — both phases tracked the finger
smoothly, 125 changes in twelve seconds with the mirror running and 89 with
`gexis-core` stopped, all of them monotone sweeps. It proved nothing about
the fault, because **the fault was already over**: the logs say why.

From bluealsa's side, starting **18:05:39**:

```
ba-transport-pcm.c:679: Couldn't set BT device volume:
  GDBus.Error:org.bluez.Error.Failed: Internal error No such file or directory (-2)
```

and from BlueZ's, the other end of the same call:

```
profiles/audio/transport.c:set_volume() Unable to set volume: No such file or directory (-2)
```

**bluealsa retried it without backoff: 104,780 log lines between 18:05:39
and 18:07:58** — about **750 a second** — burning 1 min 28 s of CPU, until
the process died:

```
bluealsa.service: Main process exited, code=killed, status=7/BUS
bluealsa.service: Scheduled restart job, restart counter is at 1
```

systemd restarted it, the A2DP endpoints re-registered, and the phone's
volume behaved normally again — which is exactly why the A/B twenty minutes
later saw nothing wrong.

**So the phone's dancing bar was bluealsa hammering a volume push that BlueZ
could not deliver.** The AVRCP control channel was unusable (ENOENT from
BlueZ) while A2DP audio kept playing — the two are separate, and a phone
dropping the control channel mid-stream is ordinary.

**Our part in it is real but secondary.** The daemon's `DummyMixerBridge`
faithfully mirrored every one of those thrashing dummy values onto the DAC,
about forty a second — it did not cause the storm and did not sustain it,
but it did convert it into hardware writes at 16 ms each. A rate limit there
is cheap and belongs in 9i whatever else is decided.

**And the mixer→AVRCP direction is there because we asked for it.**
`--volume=mixer` forces `SoftVolume=false` (Finding 012, and it fixed a real
frozen ceiling), and the same flag is what makes bluealsa push the mixer's
value back out to the phone. That outbound push is the path that melts down.

**What this does not yet say** is what made the control channel fail at
18:05:39. Nothing of ours writes AVRCP; the candidates are the phone itself
and the `bluealsa-aplay` restart I ran at 17:50 to test §8's meter, fifteen
minutes earlier. A reproduction would need the control channel to fail
again, which is not something this side can arrange.

## What is left, and what it needs

**Silent, but needs a phone connected** — no listening, just a stream:

1. **Whether §8's silence is the phone or the meter** — one ear, one phone.
   George has since confirmed the audio *is* audible, so the meter being
   blind (§8) stands as the likelier of the two readings and wants the same
   A/B as §9.
2. **Whether Spotify's or Bluetooth's remembered level overrides the boot
   level** the way LMS's does. Spotify's restore is already known to be
   240/240 on acquisition, which is the loudest the device can be.

**Needs the amplifier, and George at it:** how a ramp sounds, and the boot
level itself.
