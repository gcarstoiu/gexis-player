# ADR-0055 — Which output the device plays to

**Status:** **Accepted and built, 2026-09-23** — George answered the three
Open questions below (*"Offer all, but maybe it clears that the one that is
not connected looks disabled or has a note saying that nothing is
connected"*; a switch may interrupt playback; and the fallback as proposed)
and then *"Go ahead."* Phase 9 subphase **9j**, split from 9i on
George's agreement 2026-09-22: *"Let's add to this output audio selection
as it is directly related to volume as well. The card holds now 3 outputs
but only one we've dealt with. We need to give the user the choice of
output."*
**Date:** 2026-09-23
**Relates to:** [ADR-0009](0009-alsa-device-indirection.md) (`pcm.output`,
the indirection this rests on), [ADR-0046](0046-fixed-output-hides-the-slider.md)
(fixed output, built today and load-bearing here),
[ADR-0011](0011-meter-data-three-transports.md) (the meter tap rides the
same PCM), [ADR-0054](0054-one-curve-and-the-renderers-own-number.md)
(what writes the level)

## Context

**Measured on `gexis`, 2026-09-23.** Scope: one device, one HAT, one boot.
Nothing here was tested by listening — no output but the HiFiBerry has ever
had audio through it on this device.

`aplay -l` and `amixer` over every playback card:

| card | what it is | playback volume control |
| --- | --- | --- |
| 0 `vc4hdmi0` | HDMI-A-1 — **the panel's own connector**, `connected` | **none** |
| 1 `vc4hdmi1` | HDMI-A-2, `disconnected` | **none** |
| 4 `Headphones` | the Pi's own 3.5 mm jack, `bcm2835` | `PCM` |
| 5 `sndrpihifiberry` | HiFiBerry DAC+ HD, `pcm179x` | `DAC` |

(`gexislmsvol` and `gexisbtvol` are ours and have no audio path.)

**Three facts make this cheap, and one makes it interesting.**

- **Everything already goes through one name.** All three renderers play to
  `pcm.output` and the daemon opens its mixer through `ctl.output`
  (`volume.py`'s `MIXER_DEVICE = "output"`), so the switch is the two lines
  of `/etc/alsa/conf.d/output.conf` that say `slave.pcm` and `card`. ADR-0009
  bought this years of work ago.
- **The visualiser follows for free.** `pcm.output` is a `type meter` with
  the peppyalsa scope wrapped *around* the slave, so whatever the slave
  becomes, the meter taps it (ADR-0011).
- **The card is discovered, not configured.** There is no
  `dtoverlay=hifiberry-…` in `config.txt`: the HAT's EEPROM is read at boot.
  So a different HAT gives a different card name **and a different control
  name**, and anything that hardcodes `DAC` is hardcoding this one device.
- **Two of the four outputs have no volume control at all.** Choosing one
  *is* fixed output — the decision ADR-0046 made and built today, arrived at
  from the other direction.

## Decision (proposed)

### 1. The list of outputs is discovered, not written down

Enumerated from ALSA at startup: every playback card that is not one of our
own dummies. Each carries a name for a person, its ALSA card id, and
**whether it has a playback volume control** — which is the fact everything
else here turns on.

`output_device` is a `choice` row fed by `optionsFrom`, the mechanism
ADR-0044 already has and `skin` already uses.

### 2. Selecting an output rewrites `output.conf` and restarts the renderers

ALSA reads its configuration when a PCM is *opened*, so a change reaches a
renderer that is playing only when it next opens one. Rather than leave that
to chance, the renderers are restarted — which is why **the change applies
after playback stops**, the same rule ADR-0018 gives output mode.

### 3. `mixer_name` follows the card instead of being `"DAC"`

`config.mixer_name` is the HiFiBerry's control. On the headphone jack the
control is `PCM`; on either HDMI there is none. It becomes a property of the
chosen output, discovered with it.

### 4. An output with no volume control forces fixed output

Not as a silent side effect but as the stated consequence: the device cannot
attenuate, so ADR-0046's behaviour is exactly right — the slider disappears,
both triggers carry the padlock, and the drawer explains. `output_mode` is
then not a choice, and the row says so rather than offering one that cannot
be honoured.

**This is why 9j and fixed output were one conversation.**

## How it was built, and what it cost

**Measured on the device**, switching between all three kinds:

| chosen | `output.conf` | control | `fixed_output` |
| --- | --- | --- | --- |
| HiFiBerry DAC+ HD | `hw:sndrpihifiberry` | `DAC` | false |
| Headphones (3.5 mm) | `hw:Headphones` | `PCM` | false |
| **HDMI 1** | `hw:vc4hdmi0` | **none** | **true** |

The picker offers all four, and the one with nothing plugged into it says
so: **`HDMI 2 — nothing connected`**. The suffix is display only — a stored
choice is matched on what comes before it, so plugging a cable in does not
orphan it.

### The bug this found in itself, within seconds of deploying

The first version resolved "nothing stored" straight through to *the first
output with a volume control*. On this device that is **the Pi's own
headphone jack** — `aplay -l` lists card 4 before the HiFiBerry's card 5 —
so a daemon restart silently moved the device off the HAT and wrote a log
line about it afterwards.

**A rule for recovering from missing hardware must not fire when no
hardware is missing.** The order is now stored, then *what `output.conf`
already says*, then the audible fallback. Nothing stored means change
nothing.

The same deploy also put `snd_rpi_hifiberry_dacplushd` in the picker:
`aplay -l` gives a card description and a device description, and the
card's is the driver's module name. The device's is what the board calls
itself.

## Open — answered 2026-09-23

1. **Which outputs should be offered at all?** All four is honest but two of
   them are traps:
   - **HDMI-A-1 is the panel's own connector.** Sending audio there sends it
     to a touchscreen, which on this device means silence with no
     explanation.
   - **HDMI-A-2 is not connected to anything** today.
   - **The 3.5 mm jack is the Pi's own converter**, which is the thing this
     device exists to avoid — but it is a real, working output and somebody
     debugging without the HAT would want it.

   **My recommendation was to hide what is not usable. George's answer was
   better:** *"Offer all, but maybe it clears that the one that is not
   connected looks disabled or has a note saying that nothing is
   connected."* An absent option explains nothing; a present one that says
   *nothing connected* tells the user what to do about it.

2. ~~**Should a switch be allowed to interrupt playback?**~~ **Yes**
   (George: *"Yes, it should"*). The renderers are restarted, and so is the
   daemon — which is how the new card's control name is picked up, one path
   instead of three mutable ones threaded through the bridges.

3. ~~**What happens to a remembered choice when the hardware changes?**~~
   **As proposed** (George: *"Agreed"*) — the first output that has a
   volume control, never a silent one, with a log line. See the bug above
   for the half of this that was wrong.

## Consequences

- **`output.conf` stops being a static image file** and becomes something
  the daemon writes. The image ships the default; the daemon owns it after
  first boot.
- **A wrong choice here is silent, where ADR-0046's is loud.** Both are worth
  a `warn`, for opposite reasons.
- **Nothing about the curve, the ceiling or the remote model changes.** They
  are all expressed against `pcm.output`/`ctl.output`, which is the point of
  ADR-0009.
- **Not measured: audio out of any output but the HiFiBerry.** Selecting one
  is untested end to end until somebody plugs something in.
