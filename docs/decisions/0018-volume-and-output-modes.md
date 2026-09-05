# ADR-0018 — Volume and output modes

**Status:** Accepted
**Date:** 2026-09-04
**Amends:** ADR-0010 (the silence rule was restated to accommodate mute)
**Amended:** 2026-09-05 — confirmed from source that the startup assertion
below has to be ours. See "squeezelite must be told".

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
