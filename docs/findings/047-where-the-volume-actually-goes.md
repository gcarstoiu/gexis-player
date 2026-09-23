# Finding 047 — Where the volume actually goes: the renderer's floor, bluealsa's curve, and what the other device really does

**Date:** 2026-09-23
**Question:** George's four findings after a night on the built device — a
Bluetooth session that connected quiet, a slider that ran to 0 and jumped
back to 100, audible sound at a renderer's zero, and *"below 40 the sound is
really dim already. Feels almost like nothing is changing."* Plus two
questions: is any of this software attenuation, and **why does a DietPi box
with the same DAC "basically work out of the box as it should"?**

**Scope, stated up front:**

- **Measured on `gexis`** on 2026-09-23, against the code deployed
  2026-09-22 (ADR-0052 amended, ADR-0053 built). The Bluetooth numbers are
  **read out of the logs of George's own session**, not reproduced — his
  phone was gone by the time this was written.
- **`ShelvesPi`**, the comparison device, was read by George running four
  commands and pasting the output. Its configuration is therefore evidence;
  nothing about how it *sounds* was measured.
- **Not measured:** what happens at connection time (needs his phone), and
  anything about how a wider window would sound.
- **One instrument error, caught:** the first run of §3's table was labelled
  "nothing active" while LMS was in fact still powered on from the previous
  step. The table below is the re-run, with the active renderer read from
  the daemon rather than assumed. This is [LESSONS](../LESSONS.md) case 15's
  shape again and the fifth fault in Finding 034.

## 1. The DAC's volume is the converter's own, and it is digital

```
numid=1,iface=MIXER,name='DAC Playback Volume'
  ; type=INTEGER,access=rw---R--,values=2,min=0,max=240
  | dBscale-min=-120.00dB,step=0.50dB,mute=1
```

`snd_rpi_hifiberry_dacplushd`, alongside `DAC Invert Output Switch` and
`DAC Rolloff Filter Switch` — the PCM179x family's own controls. **So the
answer to "is it software?" is no**: the CPU never scales a sample on this
device, and the stream reaches the converter at full scale.

**It is still a *digital* attenuator, not an analogue one.** Digital
attenuation costs resolution wherever it is done; doing it inside the
converter avoids a second stage and is done at the converter's internal
precision, which is why the project chose it. That is a difference of
degree, not of kind, and it matters for §5.

## 2. Bluetooth: the ratchet is not fixed, and 2026-09-22's claim was wrong

**What was claimed on 2026-09-22:** AVRCP's 128 values against the dummy's
151 made the round trip lossy, and 128 against 128 would make it exact
(Finding 045 §12).

**It did not.** From George's session, 09:30–09:36, both sides at 0–127:

| phone → bluealsa → back | count |
| --- | --- |
| **exact** | 120 |
| drifted by ±1 | 32 |
| drifted by +4 to +6 | 15 |
| **jumped to 127** | **5** |

**179 round trips, 59 of them wrong — one in three.**

**Why the range change could not have fixed it:** the two scales are not the
same *shape*. Fitted from bluealsa's own log lines, its AVRCP curve is

    dB = 33.2 · log10(value) − 69.9

— about **10 dB per doubling**, so 5 is −46.66 dB and 107 is −2.47 dB. Our
dummy control is **linear in dB**, 0.30 dB a step. Converting between a log
curve and a linear one quantises differently in each direction, and matching
the number of steps does nothing about that. The 2026-09-22 conclusion
mistook a symptom for the mechanism.

**The wrap, in bluealsa's words:**

```
bluez.c:1502:        Updating A2DP volume: 0 [-96.00 dB]      <- the phone
bluealsa-dbus.c:1002: Setting volume: 127 [0.00 dB] <> 127    <- bluealsa-aplay
bluez.c:1502:        Updating A2DP volume: 127 [0.00 dB]      <- pushed back out
```

The phone asks for silence and gets full scale back. Five times in six
minutes. **Where inside bluealsa this happens was not established** — the
source was not read, and the conversion could not be reproduced from the
logged values alone.

**What the range change *did* fix is the storm.** 7 "Couldn't set BT device
volume" retries since 09:30 and 929 log lines in total, against **104,780
lines in 2 min 19 s** when it melted down (Finding 045 §10). No flood, no
SIGBUS, no restart. That symptom is gone and the ratchet under it is not.

**`gexis-core` is not in this loop:** zero `remote_volume` lines in the
daemon's log for the whole episode. ADR-0053 sends only what the panel
originates, and the panel was untouched.

## 3. A renderer's zero is −38 dB, and the bottom fifth of travel is one dB

Panel percentage → DAC, read from the hardware, with the active renderer
read from the daemon rather than assumed:

| panel | nothing active | **LMS active** |
| --- | --- | --- |
| 40% | −27.0 dB | **−23.0 dB** |
| 20% | — | **−37.0 dB** |
| 10% | −40.5 dB | **−38.0 dB** |
| 5% | — | **−38.0 dB** |
| 0% | **raw 0 — silence** | **−38.0 dB** |

**Two defects, and they are not the same age.**

**(a) A renderer's own zero was never silence.** `dummy_raw_to_hardware_raw`
puts the dummy's floor at the bottom of the renderer window: −45 dB until
2026-09-22 and **−38.1 dB since**, because the AVRCP range change spent
6.9 dB at the quiet end. So this is old, and it was made 7 dB worse. It was
a *recorded, accepted* trade — `dummy_raw_to_hardware_raw`'s own docstring
says "dead silence is what pause/mute are for, not the bottom of a
renderer's own volume slider". George has now found that wrong in use.

**(b) The panel's 0% used to be silence and no longer is.** With nothing
playing it still writes raw 0. With a renderer active, ADR-0053 routes it to
the renderer instead, whose zero is −38.1 dB. **That is a regression
introduced on 2026-09-22.**

**And the bottom of LMS's travel does almost nothing:** 0%, 5% and 10% are
one value, and 0–20% spans one decibel. That is squeezelite's own curve,
which it derives from the dummy control's declared range, collapsing its
bottom onto the control's floor — measured independently on 2026-09-22 as
LMS 10 and LMS 0 both landing on dummy 0 (Finding 046 §1).

## 4. The two dummy cards cannot have different ranges

From `/sys/module/snd_dummy/parameters`:

```
enable=Y,Y,N,...          <- per card
id=gexislmsvol,gexisbtvol <- per card
index=-1,-1,...           <- per card
mixer_volume_level_max=127   <- ONE value, both cards
mixer_volume_level_min=0     <- ONE value, both cards
```

`enable`, `id`, `index` and `pcm_devs` are arrays; **the mixer range is a
scalar shared by every card the module creates.** So while Bluetooth's
control must be 0–127 for AVRCP, LMS is held to the same 38.1 dB window.
The two constraints are wired together by the module, not by us.

## 5. `ShelvesPi`: same DAC, and **both renderers use software volume**

George's own device, read by him and pasted 2026-09-23.

**squeezelite:**

```
/usr/bin/squeezelite -W -C 2 -n ShelvesPi -o plughw:CARD=sndrpihifiberry,DEV=0
```

**There is no `-V`.** squeezelite's own help: *"-V <control> Use ALSA
control for volume adjustment, **otherwise use software volume
adjustment**."* So LMS's volume there is applied to the samples, not to the
converter.

**raspotify:**

```
#LIBRESPOT_MIXER_TYPE=softvol     <- commented: the default applies
LIBRESPOT_VOLUME_CTRL=log
#LIBRESPOT_VOLUME_RANGE=60        <- commented: 60 dB applies
```

Every ALSA-mixer line is commented out. librespot's `softvol`, **log curve,
60 dB**, in software.

**And the hardware control is parked and never touched:**

```
'DAC Playback Volume' : values=233,233     (-3.50 dB)
```

**So the thing that "works out of the box" is software attenuation.** It
reaches true silence because a software gain can multiply by zero; it is
smooth all the way down because it has 60 dB and its own curve; and the
converter sits at a fixed −3.5 dB with nothing arbitrating between the two
renderers, because on that device nothing has to.

**This does not overturn the 2026-09-08 finding, and it is important not to
read it that way.** That finding measured what happens when squeezelite
derives its curve from a *wide hardware TLV* — 75% at −30 dB, 50% at −60 —
and it stands. `ShelvesPi` does not hit it because it points squeezelite at
no hardware control at all. It is a third configuration, not a
counter-example.

**What it does establish** is that the behaviour George wants — silence at
zero, and something happening across the whole bottom half — needs about
**60 dB and a curve**, and that our 38.1 dB with squeezelite's derived curve
does not have it.

## 10. The DAC comes up at −20 dB, and nothing carries a level across a boot

**Added 2026-09-23** on George's *"reboot and check and then we decide"*,
about whether `gexis-boot-volume` still has a job.

**The instrument:** a oneshot unit ordered *before* `gexis-boot-volume`
(so the boot unit still ran and the device was never less safe for being
measured), reading the DAC and writing it to a log. Two boots.

| boot | probe read | what `gexis-boot-volume` then wrote |
| --- | --- | --- |
| 12:48 | **raw 200, −20.00 dB** | raw 200, −20 dB (from settings) |
| 12:51 | **raw 200, −20.00 dB** | raw 60, −90 dB (from settings) |

**The first run was ambiguous and was not reported as an answer**: the
probe's reading and the boot unit's write were the same number, so the
reading could have been a leftover rather than the hardware. The second
run changed the stored `boot_volume` to −90 first; the probe still read
200. **−20 dB is the converter's own power-on value.**

**And nothing restores a previous session's level.** `alsa-restore` is
masked, there is no `/var/lib/alsa/asound.state`, and the udev rule's own
attempt is in the boot log failing:

```
(udev-worker): controlC2: Process '/usr/sbin/alsactl ... restore 2'
  failed with exit code 99
```

**So ADR-0018's hazard — "a device that was left loud and boots into
playback" — cannot happen on this image**, and the device does not come up
loud either.

**What this leaves the boot unit doing**, and it is the decision George
asked for: it lowers −20 dB to −90 dB for the window between boot and the
first renderer acquiring — during which nothing plays, because acquisition
*is* a renderer taking the device, and acquisition sets the level from the
renderer itself (ADR-0054 §5).

**One argument against it that only appeared today.** Since the
per-renderer memory was deleted, a renderer that fails to answer on
acquisition is **left alone** — at whatever the level already is. If that
is the boot unit's −90 dB, the device is silent and looks broken; if it is
the converter's own −20 dB, it is quiet but plainly working. The boot unit
is now the thing that could turn a missed answer into a "no sound" report.

## What this says the answer is

Not software attenuation: the project's reason for refusing it is unchanged,
and §1 shows the converter is already doing the work.

**The range and the floor are wrong, and the curve is not ours.** Since
[ADR-0053](../decisions/0053-the-panel-is-a-remote-control.md) the daemon
knows every renderer's *own* number — LMS's 0–100 from the server, Spotify's
from its API, Bluetooth's 0–127 from AVRCP. It no longer needs any renderer
to derive a curve from a control's declared range, which is the mechanism
behind both §3's collapsed bottom and Finding 046 §9's seam.

Three changes fall out, and they want one record between them:

1. **Bluetooth's level stops going through the mixer** (`bluealsa-aplay
   --volume=none`, level from bluealsa's own D-Bus property). One writer in
   each direction, no automatic loop — §2's ratchet has nowhere to live.
2. **That frees the shared dummy range** of §4, which only has to be 0–127
   because AVRCP round-trips through it today.
3. **One curve, ours, applied to each renderer's own number**, with the
   floor at true silence and a span chosen by measurement. 60 dB is the
   first candidate, because that is what librespot chose and what George has
   found works.

**None of this is measured yet.** The candidate spans have to be heard, and
that needs George at the amplifier.

## What is left, and what it needs

- **Where inside bluealsa the 0 → 127 wrap happens.** The source was not
  read. It matters less if §1 of the proposal lands, since the loop
  disappears, but it is not *explained*.
- **Connection-time volume** (George's first finding): whether the phone
  announces its level first or bluealsa pushes a stale one. With
  `--volume=mixer` running both ways it is a race. **Needs his phone.**
  The general form — a renderer should be *asked* where it is on
  acquisition, rather than restored from memory — is an addition ADR-0053
  should make for all three.
- **How any candidate window sounds.** Needs the amplifier.
