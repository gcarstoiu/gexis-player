# ADR-0054 — One volume curve, ours, applied to each renderer's own number

**Status:** Accepted, **§5 amended 2026-09-26** (Spotify is told the level, not
asked) **and 2026-09-28** (a renderer handed its level starts no louder than a setting) — George, 2026-09-23: *"All three at once. Let's try the
fix in order to still have hardware attenuation. If it doesn't work we might
need to reconsider the software volume path."*
**Date:** 2026-09-23
**Raised by:** his four findings on the built device, measured in
[Finding 047](../findings/047-where-the-volume-actually-goes.md)
**Amends:** [ADR-0018](0018-volume-and-output-modes.md) (what moves the DAC),
[ADR-0052](0052-the-volume-path.md) §5, [ADR-0053](0053-the-panel-is-a-remote-control.md)
(which gains the acquisition rule in §5), [ADR-0011](0011-meter-data-three-transports.md)
is untouched
**Supersedes in part:** the 2026-09-08 decision recorded in
`dummy_raw_to_hardware_raw`'s docstring — the dummy control's *declared
range* stops being anybody's volume curve

## Context

Four findings, all measured (Finding 047):

- **A renderer's zero is −38 dB, not silence**, and since ADR-0053 that is
  also what the *panel's* 0% does. The panel used to reach silence.
- **The bottom fifth of LMS's travel spans one decibel** — 0%, 5% and 10%
  are one value. That is squeezelite's curve, which it derives from the
  dummy control's declared range and which collapses onto that control's
  floor.
- **Bluetooth's level still ratchets** — 59 of 179 round trips wrong, five
  of them jumping to 127 — because bluealsa's AVRCP curve is ~10 dB per
  doubling and the dummy control is linear in dB. Matching the step counts
  on 2026-09-22 fixed the storm, not the drift.
- **A phone connects and the device is quiet though the phone says maximum.**
  `bluealsa-aplay(1)`, on `--volume=mixer`: *"When the audio stream starts
  then bluealsa-aplay will change the Bluetooth volume to match the current
  setting of the ALSA mixer control."* **The stale mixer value overwrites
  the phone**, by documented design.

And the comparison device, `ShelvesPi`: same DAC, and **both renderers use
software volume** — squeezelite with no `-V` at all, librespot's `softvol`
on a log curve over **60 dB** — with the hardware control parked at
−3.50 dB. What George likes there is 60 dB, a curve, and a true zero.

**The common cause of the first three is that we let other programs derive
our curve from a control's declared range.** Since ADR-0053 we do not need
them to: the daemon knows every renderer's own number.

## Decision

### 1. Bluetooth's level stops travelling through an ALSA mixer

`bluealsa-aplay --volume=none`, which the man page describes as exactly this
case: it *"will force the BlueALSA PCM volume mode setting to native
('pass-through')... It will not operate its configured ALSA mixer... it can
be used to allow some other application to apply remote volume change
requests."*

**"Native pass-through" is the important half**: bluealsa applies no
software attenuation, so the stream still reaches the DAC at full scale.

The level comes instead from bluealsa's own D-Bus API, `org.bluealsa.PCM1`'s
`Volume` property — documented on the device: *"channel 1 is stored in the
upper byte, channel 2 in the lower byte. The highest bit of both bytes
determines whether channel is muted. A2DP: 0-127."* We read it, and we write
it when the panel asks.

**This removes the loop rather than tuning it.** One writer in each
direction, no mixer in between, and the ratchet has nowhere to live. It also
removes the stale-value push at stream start, which is the fourth finding.

### 2. The dummy control stops being a scale and becomes a trigger

Nothing reads `dummy_raw_to_hardware_raw` any more. squeezelite still writes
`gexislmsvol`, and that write is still the fastest signal that LMS's volume
moved — **but the value is squeezelite's curve of LMS's number, not LMS's
number**, so it is used as an *event*, and the number is read from the
server (~13 ms, Finding 046 §2).

**`gexisbtvol` becomes unused** and is kept only so the module's two-card
configuration is unchanged.

### 3. One curve, ours: **cubic** over 60 dB, with zero as silence

```
value == 0          ->  DAC raw 0, silence
value in 1..steps   ->  ceiling + 20*log10((x*(1-f) + f)^3),  x = value/steps
                        f = 10^(-60/60) = 0.1
```

**The taper was linear in dB until George heard it** (2026-09-23): *"60db
might not be enough. The bottom half of the volume range is quite quiet."*
The symptom was right; the remedy he reached for goes the wrong way, and
the arithmetic is the argument — a *wider* span moves the bottom **down**:

| position | linear, 60 dB | linear, 80 dB | **cubic, 60 dB** |
| --- | --- | --- | --- |
| 75% | −15.0 dB | −20.0 dB | **−6.5 dB** |
| 50% | −30.0 dB | −40.0 dB | **−15.5 dB** |
| 25% | −45.0 dB | −60.0 dB | **−29.5 dB** |
| 1% | −59.4 dB | −79.2 dB | −58.0 dB |

Linear in dB spends half its decibels on the bottom half of the slider.
**Cubic is how a volume control is normally tapered**, and it is what
librespot offers beside its `log`; the dr-lex article librespot's own
source cites describes the same curve.

**And `log` is not an alternative.** Read from librespot's source,
`ratio = exp(ln(db_ratio)·x) / db_ratio`, which for 60 dB is `1000^(x−1)` —
**exactly linear in dB**. So Spotify on the comparison device has the same
curve this is replacing, and what George is comparing against for LMS is
squeezelite's software volume applying LMS's own server-side gain.

**What the taper costs, recorded because it is the same complaint moved:**
above about 44% the curve is finer than the DAC's 0.5 dB steps, so 101
slider positions land on 81 distinct levels and some neighbouring
percentages sound identical. Those pairs are **0.23 dB** apart, which is
inaudible; the bottom-end collapse they replace was ten positions on one
value across a usable range.

- **Zero is silence**, for every renderer and for the panel. This is the
  2026-09-08 note — *"dead silence is what pause/mute are for, not the
  bottom of a renderer's own volume slider"* — reversed on use.
- **60 dB**, because that is what librespot chose for `softvol`. It is a
  constant so that changing it is a one-line experiment.
- **`max_ceiling` still shifts the whole window** (ADR-0052 amended), so the
  top of every scale remains the user's.

The DAC has 0.5 dB steps and 120 dB of range, so 60 dB is 120 hardware
steps — more than any renderer's 101 or 128 positions needs.

### 4. The panel's slider is unchanged in meaning and regains its zero

ADR-0053 stands: with a renderer active the panel shows and sets the
renderer's own number. That number now reaches the DAC through §3, so
**panel 0% is silence again** whether or not something is playing.

**Finding 046 §9's seam closes on its own.** The panel's fallback window
becomes the same 60 dB with the same floor, so the number no longer moves
when a renderer lets go. ADR-0034's −45…0 dB window is replaced by this one.

### 5. A renderer is *asked* where it is on acquisition, not restored

`resolve_restore` writes a remembered DAC level when a renderer becomes
active. Under §3 the renderer's own number is authoritative and available:
LMS's from the server, Spotify's from `/status`, Bluetooth's from the
`Volume` property. **So acquisition reads it and applies §3's curve**, and
the remembered level is used only when the renderer has none to give.

> **Amended 2026-09-23: there is no remembered level any more.** George:
> *"Don't we ask each renderer the volume when they take over? If so what
> is the purpose of the remember level per renderer."* None, once this
> section shipped — **12 acquisitions, 12 answers, 0 fallbacks**, measured
> before deleting it. `RendererVolumeMemory`, `volume.json`,
> `restore_volume_floor_db` and the `per_renderer_volume` row are gone.
>
> **A renderer that does not answer is left alone**, deliberately. Every
> one has an inbound path that corrects the level within a second —
> bluealsa's PCM appearing, LMS's status push, Spotify's volume event — so
> it self-corrects, and guessing meanwhile can only be wrong in a way
> nobody asked for.

This is George's first finding in its general form, and it is what makes
every control agree at the moment of connection rather than a second later.

> **Amended 2026-09-26: Spotify is told, not asked.** George: *"the Spotify
> renderer always defaults to 100% volume which shouldn't be the case."* Every
> acquisition in his reproduction logged `spotify says it is at 100`, and
> **the answer was never a measurement.** With `external_volume: true` ([ADR-0052](0052-the-volume-path.md) §6,
> which keeps the attenuation in hardware) go-librespot
> v0.9.0 starts every session at 65535 and never reads `initial_volume` or its
> own `last_volume` (`daemon/player_state.go:185`, `daemon/player.go:166`); a
> transfer carries no volume from the phone (`connectstate/transfer.proto`). So
> "asking" Spotify returns a constant, and the constant is full scale.
>
> George chose, of two: **the level already playing carries across.** When
> Spotify takes the device, the DAC's current level - the one unmuting would
> restore, if muted - goes to go-librespot through
> `hardware_raw_to_renderer_value`, the inverse of this record's §3 curve, and
> the phone's slider follows it. A renderer declares this about itself
> (`reports_real_volume = False`); LMS and Bluetooth report real levels and
> are still asked. **Fixed output is unchanged**: the DAC is at full scale
> there by design and there is nothing to carry.
>
> **Rejected: remember Spotify's last level ourselves.** It is the
> per-renderer memory this section deleted three days earlier, for a renderer
> whose own memory we would be standing in for because it does not keep one.

### 6. The panel's own change does not wait for the round trip

**Added during implementation, on a measurement.** Routing a panel change
through the renderer and back took **560 ms** to reach the DAC, against
160 ms writing it directly — and *"the volume is not increased or decreased
smoothly, there is this delay we introduce a while back"* is the symptom
that opened 9i. The remote model may not reintroduce it.

So when the panel originates a change, the target is known the moment it is
decided: **the hardware is told at once, then the renderer.** The renderer's
own report arrives later carrying the same value and moves nothing. Measured
after the change: **72–96 ms** with a renderer active, which is no slower
than writing the DAC directly.

**This does not weaken §1's invariant.** What is forbidden is sending a
*renderer's own reported value* back to it; this is the panel's value, going
outward, which is the direction the model is for.

## Consequences

- **Verified on the device, with the room silent** (LMS's acquisition is
  power-on, not play): panel 100/50/25/10/5/0% put the DAC at
  0.00/−30.00/−45.00/−54.00/−57.00 dB and **silence**, with LMS reading the
  same number as the panel at every point, and identical levels whether or
  not LMS held the device — **Finding 046 §9's seam is closed**, measured at
  release as 30% before and 30% after. What is *not* verified is Bluetooth's
  half and how any of it sounds.
- **One row changes meaning, on George's instruction 2026-09-23**
  (*"record the linear and cubic curves as settings for the next step"*):
  `travel_curve` becomes **Volume curve**, offering **Cubic** (shipping)
  and **Linear (dB)** (what §3 replaced). It described a *window* before —
  `Perceptual` / `dB-linear` — which was never a curve. **Recorded, not
  wired**: ADR-0022's inventory carries it as `[R][H]`, and wiring it is
  the next step. `max_ceiling` is unchanged.
- **`renderer_volume.py` is deleted** (2026-09-23). It became a fallback
  that never fired, and then it became nothing.
- **The image changes**: the `bluealsa-aplay` unit loses its mixer options.
  A device must be rebuilt or the unit hand-edited for §1.
- **Bluetooth's half cannot be verified without George's phone.** The D-Bus
  plumbing can be checked with nothing connected; the value path cannot.
- **If this does not deliver what `ShelvesPi` delivers, the fallback is
  named**: software volume, which is what that device actually does. George,
  2026-09-23: *"If it doesn't work we might need to reconsider the software
  volume path."* This record is the attempt to keep hardware attenuation.

## What is not decided here

- **Where inside bluealsa the 0 → 127 wrap happens** (Finding 047 §2). A
  candidate is that mute shares the byte with the level and our dummy
  control has no playback switch to express it — **not proven**, and §1
  makes it moot rather than answering it.
- **Whether 60 dB is right.** It is a measured starting point, not a
  measured answer, and it needs George at the amplifier.

## Amended 2026-09-28: Spotify starts no louder than *Starting volume*

**The problem.** §5 as amended hands Spotify the level already on the DAC. That
was safe while every source moved the DAC. Since Plexamp (Finding 095, revised)
keeps its own volume, the DAC stays wherever the panel left it, often high, with
the app turning the sound down inside the stream. The core's log of George's
test on 2026-09-28 shows the consequence: a source keeping its own volume had
left the DAC at 240/240, and Spotify took over at 100%.

**Decided (George, 2026-09-28).** He took Claude's proposal (a cap that only
ever lowers) and widened it: *"Spotify specific setting. Default is 60 applied
everywhere on all takeovers. 60 is the max. If the previous renderer had less
than 60 it stays to what the renderer had. If more than 60, then it comes down
to 60. I use 60 as example, it should follow the setting value."*

- **A setting in Spotify Connect's group:** `spotify_start_max`,
  *Starting volume*, 10-100 %, default 60.
- **On every takeover by Spotify, from any source**, the level handed to it is
  the lower of the DAC's level and the setting, both on the panel's percentage
  scale. It never raises a level.
- **When it lowers, the DAC is written first**, through `write_hardware` (a ramp
  of at most 0.12 s, ADR-0052 §4), then Spotify is told. The acquisition runs
  release → volume → `device_freed`, so the cap lands before Spotify's retry, and
  alongside its first open (0.26 s after it announces) at worst.
- **Spotify only.** It is the one renderer handed a level. The others report
  their own on acquisition (LMS, Bluetooth), or keep their own (Plexamp).
- Fixed output is untouched, as before: nothing is handed there.

### Amended again 2026-09-28: the cap covers every renderer that is handed its level

A plugin can have what Spotify has: a level at a takeover that is only its
app's leftover. George chose the cap for such a renderer too, the same day.

- **The row moves and is renamed:** `start_max`, *Starting volume*, under Audio
  beside *Maximum volume*. Same range, same default of 60 %. It left Spotify's
  group because it is no longer Spotify's alone. Nothing had shipped with the
  old key.
- **Which renderers:** every one the core hands a level on acquisition, not one
  named in code. Spotify is handed one (`reports_real_volume = False`), and so
  is any plugin that declares the new capability **`volume_handed`**
  (PLUGIN-CONTRACT.md).

