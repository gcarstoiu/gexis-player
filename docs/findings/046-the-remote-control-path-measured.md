# Finding 046 — The remote-control path, measured

**Date:** 2026-09-22
**Question:** George, on the panel showing 33 where LMS shows 25: *"For sure
the remote way. That's how it should be. Does this apply to the other
renderers?"* — and then, before approving it: *"you can give me some numbers
before implementation is approved."* So: what does it cost, per renderer,
to make the panel a remote for the thing that is playing rather than a
second volume in series with it?

**Scope, stated up front:**

- **Measured on `gexis`**, the image-built device, on 2026-09-22, against
  the build deployed that afternoon. LMS is the one on the house network at
  `192.168.178.188:9000`; the player is `gexis`.
- **Nothing was playing.** Every number here is a *transport* cost —
  how long a value takes to travel a path — and none of them is a
  measurement of the sound. The daemon's mirror only writes the DAC while
  the renderer that changed is the active one, so with nothing playing the
  DAC stayed at 164 throughout, on purpose.
- **What was measured:** the outbound leg for LMS and Spotify, whether
  squeezelite carries a mixer change back to LMS, the `alsactl monitor`
  transport every inbound leg shares, and each renderer's scale.
- **Not measured:** the full loop under playback; anything about how it
  *sounds*; and **Bluetooth's outbound leg**, which needs George's phone —
  the one renderer whose outbound channel is inferred rather than seen.
- The DAC's control is `DAC` on `hw:sndrpihifiberry`, not `Digital`; the
  first run of the instrument read `None` for every DAC value and was fixed
  before any of it was written down.

## 1. What the two numbers are today

The panel's slider and the renderer's slider are two controls in series, so
they show different numbers for one sound. Measured end to end — LMS set by
its own RPC, the dummy and the DAC read back:

| LMS says | dummy | DAC | panel would say |
| --- | --- | --- | --- |
| 100 | 127 | 0.00 dB | 100 |
| 75 | 109 | −5.50 dB | 88 |
| 50 | 68 | −17.50 dB | 61 |
| 25 | 27 | −30.00 dB | **33** |
| 10 | 0 | −38.00 dB | 16 |
| 0 | 0 | −38.00 dB | 16 |

The LMS, dummy and DAC columns are read from the device. **The panel column
is computed**, by `raw_to_slider_percent` — the same function the daemon
publishes with — not read off the screen, because the screen needs the DAC
to be moving and nothing was playing.

Neither number is wrong. They measure different things, and there is no
reading of "the volume" under which both are true. Note also that LMS 10 and
LMS 0 are the same sound: LMS's bottom 10% lands on the dummy's floor.

## 2. Panel → LMS: 16–26 ms, and it has to go through the server

`mixer volume N` over LMS's JSON-RPC, timing the call and then watching the
dummy control that squeezelite drives:

| target | the RPC call | dummy follows after | lands on |
| --- | --- | --- | --- |
| 40 | 15.9 ms | 7.4 ms | 50 |
| 70 | 11.6 ms | 4.3 ms | 101 |
| 25 | 13.1 ms | 10.6 ms | 27 |

**16–26 ms for the whole outbound leg**, over the house network to another
machine and back.

## 3. squeezelite does not carry a mixer change back to LMS

The cheaper design would have been to write squeezelite's own control and
let it tell the server. It does not:

| dummy set to | LMS was | LMS after | dummy after |
| --- | --- | --- | --- |
| 60 | 25 | 25 (4 s) | 60 |
| 30 | 25 | 25 (4 s) | 30 |
| 55 | 0 | 0 (**10 s**) | 55 |

squeezelite runs `-V Master`, which means LMS's volume commands *reach* the
control; the reverse is not implemented. The control keeps whatever is
written to it and the server never hears about it — so a write to the dummy
**silently desynchronises LMS from the device**, which is today's complaint
in a new place.

The ten-second run is deliberate: four seconds finding nothing is not proof
that nothing happens (`docs/LESSONS.md`). Ten seconds finding nothing, with
the control demonstrably still holding the written value, is as far as this
can be taken from here.

**So LMS's remote channel is the server's RPC, and nothing else.**

## 4. Panel → Spotify: 2–5 ms

`POST /player/volume` on go-librespot's local API, then `/status`:

| target | the POST | `/status` reflects it after |
| --- | --- | --- |
| 40 | 4.1 ms | 4.6 ms |
| 70 | 3.1 ms | 1.9 ms |
| 25 | 2.2 ms | 1.5 ms |
| 98 | 3.1 ms | 2.7 ms |

Loopback to a process on the same machine, and it shows. **This half is
already built**: `SpotifyAdapter.set_volume` exists and the bridge already
calls it, because Spotify is the one renderer the daemon has always had to
talk back to.

## 5. The leg every inbound path shares is free

A change on a renderer's control reaching a listener through
`alsactl monitor hw:gexisbtvol`:

| written | `amixer` returned at | event at | lag |
| --- | --- | --- | --- |
| 100 | 6.4 ms | 6.5 ms | +0.2 ms |
| 90 | 5.1 ms | 5.2 ms | +0.1 ms |
| 110 | 12.1 ms | 12.2 ms | +0.1 ms |
| 80 | 10.0 ms | 10.0 ms | +0.0 ms |
| 127 | 8.2 ms | 8.2 ms | +0.1 ms |

**Median 0.1 ms.** The subscription costs nothing; what costs is the write
in front of it (`amixer` here, 5.7 ms through libasound in the daemon) and
the mirror's own 40 ms rate limit behind it (ADR-0052 §5).

## 6. The scales

| control | positions | note |
| --- | --- | --- |
| LMS | 0–100 | 101, and its bottom ten land on one dummy value |
| Spotify | 0–100 | 101; `volume_steps` reads 100 today, not the 65535 the adapter falls back to |
| Bluetooth | 0–127 | 128, AVRCP's own, and the dummy's since this morning |
| panel | 0–100 | 101 over 45 dB |
| DAC | 0–240 | 241, 0.5 dB each |

LMS and Spotify are the panel's own resolution exactly. Bluetooth is finer,
and 0–100 → 0–127 → 0–100 round-trips to the same integer at every point.

## 7. What a step would cost, added up

Panel → sound, per step, against today's ~15–30 ms (Finding 045 §2's
measured p50 of 26–41 ms, less the 10.7 ms `amixer` subprocess ADR-0052 §4
removed):

| renderer | added by going through it | why |
| --- | --- | --- |
| **Bluetooth** | **+6 ms** | the panel writes the same control it writes today; only the monitor hop and the DAC write are new |
| **Spotify** | **+10 ms** | 2–5 ms to the API, its event back, the DAC write |
| **LMS** | **+22–33 ms** | 16–26 ms to the server and back to the dummy, then the monitor hop and the DAC write |

Plus, for any of them, up to the mirror's **40 ms** rate limit in the worst
case.

**LMS is the expensive one: roughly double the per-step cost, ~20 positions
a second instead of ~33.** That makes ADR-0052 §4's ramp load-bearing rather
than a nicety — the panel was already delivering a *sample* of a drag
(6 of 12 positions on a fast one), and this halves the sample again. What
the ear hears depends on the ramp filling it in, which is measured to take
46 ms for a 4 dB gap.

## What is left, and what it needs

**Needs George's phone:**

1. **Bluetooth's outbound leg.** Writing `gexisbtvol` should push AVRCP to
   the phone — `bluealsa-aplay --volume=mixer` is running, and Finding 045
   §12's ratchet is proof that the outbound push exists. But *a phone's
   slider has never been seen to move because the panel moved.* Until it
   is, Bluetooth's half of this is inference.
2. **Whether go-librespot still publishes volume to the Connect session**
   now that `external_volume: true` stops it attenuating. `/status` reflects
   our writes; whether the Spotify app on a phone does is a different claim.

**Needs playback**, which needs him at the amplifier: every number here is a
transport cost with the DAC deliberately out of the loop. The full
panel-to-sound latency has not been measured end to end in the remote model,
because the model does not exist yet.
