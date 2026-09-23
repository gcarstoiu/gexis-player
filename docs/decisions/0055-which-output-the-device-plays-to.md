# ADR-0055 — Which output the device plays to

**Status:** **Proposed** — Phase 9 subphase **9j**, split from 9i on
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

## Open — George's, and the reason this is Proposed

1. **Which outputs should be offered at all?** All four is honest but two of
   them are traps:
   - **HDMI-A-1 is the panel's own connector.** Sending audio there sends it
     to a touchscreen, which on this device means silence with no
     explanation.
   - **HDMI-A-2 is not connected to anything** today.
   - **The 3.5 mm jack is the Pi's own converter**, which is the thing this
     device exists to avoid — but it is a real, working output and somebody
     debugging without the HAT would want it.

   **My recommendation: offer what is usable and say why the rest is not** —
   the HiFiBerry, the headphone jack, and an HDMI entry only while something
   is plugged into it (`/sys/class/drm/…/status`). Offering a dead socket is
   how a user concludes the device is broken.

2. **Should a switch be allowed to interrupt playback**, or only offered
   while idle? §2 restarts the renderers. Stopping first is safer and
   slower.

3. **What happens to a remembered choice when the hardware changes?** Pull
   the HAT and `sndrpihifiberry` is gone; the stored value names a card that
   does not exist. **Proposed: fall back to the first output that has a
   volume control, and say so in the log** — never to a silent one.

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
