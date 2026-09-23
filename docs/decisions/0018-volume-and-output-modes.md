# ADR-0018 — Volume and output modes

**Status:** Accepted
**Date:** 2026-09-04
**Amends:** ADR-0010 (the silence rule was restated to accommodate mute)
**Amended:** 2026-09-05 — confirmed from source that the startup assertion
below has to be ours. See "squeezelite must be told".
**Amended:** 2026-09-08 — squeezelite and bluealsa-aplay no longer engage
the real hardware mixer directly (B2, George's decision). See "Dummy
mixer controls" below.
**Amended:** 2026-09-23 — **"Boot volume is a fixed safe level" is
withdrawn**, on measurement and George's decision. The unit, the setting
and `boot_volume_steps` are deleted. See the section, which is kept with
its reasoning so the amendment has something to argue with.

## Context

The requirement list originally read "hardware or software volume control
(compromises bit perfect)". Measurement on the rig showed that framing is wrong
for this hardware.

From Finding 002:

```
numid=1  'DAC Playback Volume'
  INTEGER, 2 values (stereo), min=0 max=240, step=0
  dBscale-min=-120.00dB, step=0.50dB, mute=1
```

240 steps of 0.5 dB, giving a 120 dB range. 0 is mute, 240 is 0 dB. The
simple-mixer control name is `DAC`.

The codec is a PCM179x with an **internal digital attenuator**. Attenuation
happens inside the DAC chip, after the I²S data path. The samples we send are
therefore unmodified in either mode — but in one mode nothing at all is touched.

## Decision — three modes

| Mode | Volume controlled by | Claim | Availability |
|---|---|---|---|
| **Fixed output** | external amplifier | Nothing in the signal path is touched, on the Pi or in the DAC | DAC2 HD |
| **Variable output** | DAC hardware attenuator | Samples we send are unmodified; attenuation is inside the chip | DAC2 HD |
| **Software volume** | ALSA `softvol` | Samples are modified. Not bit-perfect. | fallback only, for HATs with no mixer |

Software volume is **never** used on the DAC2 HD. It exists so the architecture
does not assume a hardware mixer, since a future HAT may not have one.

Fixed output sets the mixer to 240 and locks it.

These are not quality gradations. Fixed and variable are different **provability
modes**, and the honest wording differs between them.

## Settled consequences

### Controls disappear, not grey out

In fixed output mode, volume controls are removed from the UI. Not disabled, not
greyed. A slider that does nothing is worse than no slider — the same rule
ADR-0014 applies to inapplicable transport controls.

### Phone-app sliders will still exist

Spotify and Bluetooth send volume commands regardless of our mode. In fixed
output we accept and ignore them. The phone's slider moves and nothing happens.
This is unavoidable and needs a line in the user documentation.

### Mode switching is not instantaneous

Full-scale output into a powered amplifier is loud. Switching from variable to
fixed while playing must not jump to 0 dB unannounced.

- Confirmation dialogue on the switch, stating what will happen.
- The change takes effect on the next track or after a stop, not mid-playback.

### squeezelite must be told

`squeezelite -V DAC` is required to engage the hardware mixer. **Omitting it
silently falls back to software volume** — no error, no warning, and a
bit-perfect claim that is quietly false. This is a startup assertion, not a
configuration preference: if the flag is missing or the control name is wrong,
the daemon should refuse to start rather than play.

**Confirmed by reading squeezelite's source (`output_alsa.c`), Phase 2:**
squeezelite will not enforce this itself. A missing or misnamed mixer
control doesn't stop it — `mixer_init_alsa()` failing is caught, logged as
an error, and squeezelite carries on with software volume, process still
running, unit still "active" to systemd. The refusal-to-start this record
already calls for has to be built by us: `squeezelite.service` runs
`amixer -D output sget DAC` as `ExecStartPre`, so systemd refuses to start
the unit at all if the control isn't there, rather than starting it and
quietly losing the bit-perfect claim. Not a workaround for a squeezelite
defect — squeezelite was never going to do this, and the assertion was
always ours to build.

### Dummy mixer controls — squeezelite and bluealsa-aplay no longer touch the real mixer directly

**Amended, 2026-09-08 (B2, George's decision).** `squeezelite -V DAC` and
`bluealsa-aplay --mixer-name=DAC` (as configured above) both write
straight to the shared hardware mixer whenever their own upstream (the
LMS app, the phone's AVRCP slider) tells them to - **regardless of
which renderer is actually allowed to be heard.** Confirmed on hardware:
raising LMS's volume from its own app audibly changed an actively
playing Bluetooth stream's loudness, because both were writing to the
identical `DAC` control unconditionally. Only Spotify's volume path was
ever isolated from this - go-librespot keeps its own software volume
state, and only `VolumeBridge` (gexis-core) decides when that reaches
hardware.

**Fix: give each of them a private control with no audio path behind
it at all**, rather than the real one. `snd-dummy` (already present on
this kernel, no build needed) creates a virtual sound card whose
`Master` control is a genuine ALSA simple-mixer element - readable and
writable through the exact same API `amixer`, squeezelite and
bluealsa-aplay already use - with nothing wired to it. Writing to it
changes nothing anyone can hear, by construction.

```
squeezelite -o output -O hw:gexislmsvol -V Master ...   (-o unchanged: still the real playback path)
bluealsa-aplay --pcm=output --mixer-device=hw:gexisbtvol --mixer-name=Master
```

`gexis-core`'s `DummyMixerBridge` (`core/src/gexis_core/volume.py`) is
the only thing that ever copies a dummy control's value onto the real
`DAC`, and only while that control's renderer is the currently active
one - the same "mirror when active, remember otherwise" shape
`_on_spotify_volume` already used for Spotify, generalised to the two
renderers that didn't have an equivalent private state of their own.

> **Amended 2026-09-17 (George): a dummy control's change is mirrored only
> once it has settled, and only while its renderer is playing.**
> [Finding 031](../findings/031-lms-pause-fade-and-push-latency.md): LMS
> fades the player out on pause by moving that control (dummy raw 22 to -50
> in 150 ms), which the bridge was copying onto the DAC and publishing as
> the user's volume - 0% for as long as the pause lasted, and remembered as
> LMS's own level, so a takeover during a pause would bring LMS back at
> -45 dB. LMS's own `mixer volume` never moves during the fade, and the
> pause itself only reaches the core 0.51 s later, so the decision waits
> `SETTLE_S` (0.8 s) for the control to stop moving and then reads the
> transport. **Cost:** an LMS-app volume change reaches the DAC about a
> second after the tap. **Bluetooth is unchanged** - its volume does not
> fade, so its control is still mirrored as it moves.

No software attenuation is introduced anywhere by this - the real DAC's
hardware attenuator is still the only thing that ever changes what's
audible, matching this record's "variable output" mode exactly as
before. This does not change squeezelite's own startup assertion
(`squeezelite-mixer-check.sh` now checks `hw:gexislmsvol`'s `Master`
control instead of `output`'s `DAC`) - the underlying concern (a
missing/misnamed mixer control silently falling back to software
volume) is unchanged, just checked against the new target.

**Amended again, 2026-09-08 (later the same day) - two bugs found on the
first real hardware test of this, both fixed, full detail in Finding
009:**

1. **Scale translation was wrong.** Originally by fractional position
   within each control's own dB range (dummy: -45..0dB over 150 raw
   steps; DAC: -120..0dB over 240) - reasoned at the time as "a 1:1 dB
   copy would mean the dummy's quietest setting could never reach the
   DAC's true mute." George reported LMS silent below ~75%. Measured on
   hardware: squeezelite derives its own percent-to-dB curve from
   *whatever control it's pointed at*'s declared TLV range, so against
   the dummy (-45dB span) it already computes a gentler curve than it
   ever would against the DAC directly (-120dB span) - fractional-
   position rescaling threw that gentleness away by re-stretching the
   curve back across the DAC's full range, recreating the exact "most of
   the slider does nothing" compression a wide-range hardware mixer
   already has a well-known reputation for. **Fixed: a direct dB copy**,
   no rescaling - `dummy_raw_to_hardware_raw()`'s own docstring has the
   full reasoning and the measured before/after curve.
2. **The value-parsing regex silently dropped minus signs.** The dummy
   controls' own range is -50..100 (unlike the DAC's 0..240), and
   `_VALUE_RE`'s `\d+` doesn't match a leading `-` - every negative
   reading parsed as its own absolute value ("-50" as 50), which is a
   *wrong* value, not a failure, so nothing short of comparing against a
   live reading would have caught it. Affected roughly the bottom third
   of LMS/Bluetooth's own volume range with wrong mirrored values and
   erratic missed updates (a mis-parsed reading could coincidentally
   equal an unrelated earlier or later real reading and get deduped
   against it). Fixed: `-?\d+`.

**Amended a third time, 2026-09-08 (George's next hardware round) - two
more bugs, full detail in Finding 010:**

3. **`DummyMixerBridge` carried an echo window copied from
   `VolumeBridge` without re-deriving whether it applied - it didn't.**
   `VolumeBridge` both watches and writes the same real-DAC `alsactl`
   stream, so its own writes genuinely echo back on it and the window
   exists to recognise "that was us." `DummyMixerBridge` watches the
   *dummy* card but writes to the *real DAC* - different cards, so a
   write here can never echo back on the dummy's own monitor stream.
   The window could only ever swallow *genuine* updates arriving within
   0.75s of the previous mirror - and Bluetooth's AVRCP updates during a
   phone slider drag land as little as ~35ms apart, so a chain of them
   could silence itself indefinitely (each mirror re-arming the window
   before the next real update got through). Explains both a Bluetooth
   session with zero mirrored volume changes despite a full slider drag,
   and Bluetooth's usable maximum reading quieter than Spotify/LMS's (a
   drag toward maximum getting silenced partway). **Fixed: removed
   entirely** - `raw == last_raw` already dedupes the one case an echo
   window would legitimately have covered (multiple monitor lines from
   one underlying change). Verified live: five writes 150ms apart, and
   two negative-value writes 200ms apart, all mirrored correctly
   afterward - previously this exact cadence would have silenced itself
   after the first write or two.
4. **Spotify's own volume mapping had the identical raw-linear bug as
   LMS's original one, just never touched by that fix.**
   `_on_spotify_volume` mapped Spotify's `value/max_` fraction linearly
   in *raw steps* onto the DAC's full 0..240 - raw steps are dB-linear,
   not perceptually linear (this record's own `raw_to_db` finding), so
   this compressed nearly all perceived loudness change into the last
   quarter of the slider, same shape as LMS's bug, just never
   discovered because the echo-window bug (this section, first
   amendment) made Spotify's volume too unreliable to properly assess
   until that was fixed. George: "60% volume there is no sound."
   **Fixed the same way LMS was**: `spotify_fraction_to_hardware_raw()`
   maps dB-linearly across -45..0dB (matching LMS's own effective span,
   for consistency across renderers - Spotify has no hardware control
   of its own to derive a span from, unlike LMS/Bluetooth). 60% now
   lands at -18dB (raw 204) instead of -108dB (raw 144, inaudible).
   Applied to both directions - `_on_spotify_volume` and `run()`'s
   hardware-changed-so-tell-Spotify path both go through it now.

### The mixer is subscribed, not polled

ALSA ctl events are subscribed to, so the UI slider stays in sync when the
control is changed by anything else — `amixer` over SSH, a renderer, or a script.
Polling would show visible lag and would waste cycles.

---

## Resolved decisions

### Renderers do not set volume on acquisition

Spotify Connect carries an initial volume when a device is selected. **It is
ignored.** Volume is a property of the room and the amplifier, not of the
renderer.

*Rationale:* volume stays constant across renderer switches, and a takeover
cannot produce a sudden jump in loudness as a side effect. Consistency here is
also a safety property, not only a convenience.

### Boot volume is a fixed safe level

> **Withdrawn 2026-09-23.** `gexis-boot-volume.service`, the `boot_volume`
> row and `config.boot_volume_steps` are deleted. **The second sentence
> below survives and is now the whole of it:** `alsactl` state is not used
> to restore volume across boots, which the image enforces by masking
> `alsa-restore.service`. That mask is the load-bearing half and stays.
>
> **Why the level itself went** ([Finding 047](../findings/047-where-the-volume-actually-goes.md) §10,
> two boots):
> - **The converter comes up at −20 dB of its own accord** — measured
>   twice, the second time with the stored level deliberately different so
>   the reading could not be a leftover. The device does not boot loud.
> - **Nothing carries a level across a boot**: `alsa-restore` masked, no
>   `asound.state`, and the udev rule's own attempt in the boot log failing
>   with exit code 99. **The hazard named below cannot happen on this
>   image.**
> - **Nothing plays before a renderer acquires**, and acquisition sets the
>   level from the renderer itself
>   ([ADR-0054](0054-one-curve-and-the-renderers-own-number.md) §5). The
>   unit was writing a number into a window in which the device is silent.
> - And since the per-renderer memory was deleted the same day, a renderer
>   that fails to answer is left at whatever the level already is — so the
>   unit had become **the thing that could turn a missed answer into a
>   silent device** rather than a quiet one.
>
> [ADR-0052](0052-the-volume-path.md) §1 had already found that the boot
> number is not the hazard and that whatever it wrote was overridden
> seconds later; it kept the unit anyway. This finishes that thought.

Not restored from the previous session. `alsactl` state is not used to restore
volume across boots.

*Rationale:* a device that was left loud and boots into playback is a real
hazard, and the cost is one adjustment for a user who habitually listens loud.

Fixed output mode has no question here: it is always 240.

The specific safe level is a configuration value, not a decision for this
record.

### The slider is logarithmic, at full hardware resolution

The scale is linear in dB, so 0-100 on the displayed control is meaningful
across its whole travel rather than bunching the useful range into the top
fifth.

**The control exposes all 240 hardware steps.** It does not quantise to 100. A
100-point scale would give roughly 1.2 dB per point, which is coarse near the
top where fine adjustment happens. Gesture sensitivity is a UI concern, decided
in the UI, and the underlying resolution stays available to it.

### Phone-app volume moves the hardware mixer — in variable mode only

| Mode | Phone sliders |
|---|---|
| Variable output | move the DAC attenuator |
| Fixed output | do nothing |

*Rationale:* every Bluetooth speaker and Connect device the user owns responds
to the phone's volume control. Violating that expectation reads as a fault. In
fixed output there is no attenuator to move, and the phone slider doing nothing
is consistent with our own controls being absent.

**This makes bidirectional sync a requirement, not a nicety.** Our screen and
the phone are two views of one value. The ALSA ctl subscription covers changes
made anywhere on our side; the open part is the other direction — see Unverified.

### Mute is hardware mute

The mixer supports mute at value 0. The mute control uses it.

**Mute differs from dragging the slider to zero by state, not by effect.** Both
produce silence. Mute remembers the level and restores it in one action;
dragging to zero destroys it. At -25 dB with a phone ringing, mute-talk-unmute
returns to -25 dB, where slider-to-zero leaves the user hunting for where it was
— an imprecise operation on a touchscreen at arm's length.

It is also mechanically cheaper: one write to 0 and one write back, rather than
traversing the attenuator down and up.

Requirements:

- The muted state is displayed prominently enough that it cannot be read as a
  fault.
- The volume readout shows **the level it will return to**, not zero.
- **Mute does not exist in fixed output mode.** The mixer is locked at 240, so
  the control disappears along with the slider. In fixed output the device has
  no volume affordances at all.

#### Relationship to ADR-0010

Mute is a silent-while-playing state, which appeared to collide with ADR-0010's
original wording, "never show playing while silent".

That wording was too narrow and has been **restated in ADR-0010** as: *never
show a state the user cannot account for.* Mute passes — user-initiated,
displayed, reversible by the same action. So does fixed output into a
powered-down amplifier. The rule is about accountability, not about silence.

Carving out an exception for mute would have been the first of several.

## To be recorded once resolved

- Whether the fixed/variable setting is per-device or per-renderer (assumed
  per-device).
- Whether a maximum-volume ceiling is offered as a safety setting.
- Behaviour when a HAT without a mixer is fitted — detection and fallback to
  software volume, including how the UI communicates the loss of bit-perfect.
- **Fixed output mode itself is not implemented — deferred, George's
  decision, 2026-09-10.** Phase 2b's criterion 5 ("phone-app volume
  moves the hardware mixer in variable mode and does nothing in fixed
  mode") only has variable mode built and hardware-verified
  (`gexis_core` has no config toggle or code path that locks the mixer
  at 240 and stops the volume bridges — checked, not assumed, via the
  three bullets above this one already flagging the mode-selection
  mechanism as unresolved). Criterion 4's Bluetooth SIGKILL item (see
  ADR-0010's "Open" section) is deferred the same way, same decision.
  Phase 2b ships on variable mode only; fixed output mode is real,
  design-complete work (the table and "Settled consequences" above), not
  a placeholder — it needs its own implementation pass, most naturally
  once mode *selection* has a UI to live in (Phase 4+), not invented
  ad hoc here.
- **Two floor/fallback values, found too conservative on hardware,
  2026-09-08/10 (Finding 011), need George's call on the actual number -
  not fixed here, the mechanisms already do the right thing:**
  - `boot_volume_steps` (raw 60, -90dB) is written by two different
    callers with different intent, and only one of them matches this
    record's own rationale above ("a device that was left loud and boots
    into playback is a real hazard"). The boot script's one-time write is
    that case. But `RendererVolumeMemory.resolve_restore()` *also* falls
    back to the same value for any managed renderer's (LMS/Spotify)
    first-ever acquisition, including mid-session, long after boot's own
    safety concern has passed - confirmed directly in `gexis`'s log:
    Spotify's first acquisition of a session that had already had LMS
    playing loud for over 20 minutes still restored to 60/240 (-90dB),
    quiet enough to read as "no sound from Spotify until the volume
    button on the phone is pressed" (George's report). `resolve_restore`'s
    own docstring already documents this as deliberate ("boot_default...
    is deliberately NOT subject to floor_db - that's a separate,
    already-confirmed-quiet value... not a degenerate remembered one"),
    so this isn't a bug to silently fix - it's this record's own boot-time
    rationale not covering the case it's actually being used for. Options:
    keep as-is (accept the UX cost as the price of the boot-safety
    guarantee), or give "never remembered, mid-session" its own fallback
    (e.g. the same floor-bump `unmanaged_floor_raw` already gives
    Bluetooth) distinct from the true boot-time default.
  - `restore_volume_floor_db` (-40.0dB) is the floor Bluetooth's
    unmanaged-renderer bump already targets (see "Dummy mixer controls"
    below), and the mechanism fired correctly and reached hardware
    (confirmed in the log: `"bluetooth is not volume-managed, but the
    mixer was left at -45.0dB - bumping to the -40.0dB floor"`) - but
    George's live report on that same connection was "no sound came
    until I first played something over lms and then reconnected",
    meaning -40dB itself wasn't loud enough to register as sound on his
    hardware. The mechanism isn't in question; the number is - and
    that's a hardware/room-dependent judgement call, not something to
    pick unilaterally.

## Unverified

These bear on the bidirectional sync requirement above, and one of them could
force a different answer than the one recorded.

- **Whether go-librespot's volume bridging to an ALSA control is bidirectional
  or one-way.** If it only reports outward, a change made on our screen will not
  propagate to the phone and the two displays drift apart.
- **Whether bluez-alsa exposes AVRCP absolute volume in a form we can both read
  and write.** Same failure mode.
- Whether the MPD-era stereo-channel bug reported against similar DAC controls
  affects `DAC Playback Volume` here. The control reports two values and should
  be tested with `amixer` for independent channel behaviour.

The first two are Phase 2 tests. If either is one-way, the choice is to accept
drift, to poll, or to reconsider bridging for that renderer.
