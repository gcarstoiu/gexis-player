# Reference — every setting the visualisation has, in plain words

**Date:** 2026-09-23
**Asked for by George:** *"have a look at the peppy documentation and list
all possible settings the visualisation can have and what each does in
layman's terms."*

**What this is.** The visualisation is two programs: **PeppyMeter** (the VU
needles) and **PeppySpectrum** (the bars). Between them they read about
ninety settings. This lists them all, says what each one actually does, and
marks which are **already a setting on this device**, which are **fixed by
how the device is built**, and which are **candidates** — things that could
become settings if you want them.

**Nothing here is a proposal for ADR-0022's inventory.** Per the standing
rule, a candidate becomes an inventory row only when you say so.

**Key to the marks:**

| | |
| --- | --- |
| **[S]** | already a setting you can change today |
| **[B]** | fixed by the build — changing it would mean a new image |
| **[C]** | candidate: it would work as a setting, nobody has asked |
| **[X]** | not applicable to this device |

---

## 1. What you see — the things a person would actually want

| setting | **[ ]** | in plain words |
| --- | --- | --- |
| `meter` | **[S]** | **Which skin is on screen.** The `skin` row. |
| `meter.names` | **[S]** | The pool a random skin is drawn from — our `skin_corpus` row does this job instead. |
| `random` *(meter = random)* | **[S]** | **Whether the skin changes by itself.** The `skin_rotate` row. |
| `ui.refresh.period` | **[C]** | **How often the needles are redrawn**, in seconds. `0.033` is thirty times a second. Higher numbers mean a calmer, cheaper picture; lower means smoother. |
| `frame.rate` | **[C]** | The same idea for the whole screen — the ceiling on redraws per second. Lower costs the panel less. |
| `update.period` | **[C]** | **How long a random skin stays** before the next one. |
| `smooth.buffer.size` | **[C]** | **How much the needle is averaged before it moves.** Bigger is calmer and lags more; smaller twitches with every transient. |
| `position.regular` / `position.overload` | **[X]** | Where the bar segments sit on a *linear* meter — only for skins built from segments rather than a needle. |
| `step.width.regular` / `step.width.overload` | **[X]** | How wide those segments are. |

## 2. How loud the needle thinks the music is

These decide whether the needles sit near the bottom all evening or slam
into the red. They are the ones most worth having.

| setting | **[ ]** | in plain words |
| --- | --- | --- |
| `volume.gain.db` | **[C]** | **The single most useful knob here.** How much to lift the signal before drawing it. A quiet recording needs more; a loud one needs less. |
| `volume.gain.db.source` | **[C]** | Whether that lift is a fixed number or follows something else. |
| `volume.min` / `volume.max` | **[C]** | The bottom and top of the needle's travel, as numbers — what counts as "nothing" and what counts as "full". |
| `volume.constant` | **[C]** | Pin the needles at one level. Useful only for checking a skin looks right. |
| `volume.max.in.pipe` | **[B]** | The largest number the audio tap will ever send. Must match what our ALSA scope is configured to emit; changing one without the other mis-scales everything. |
| `mono.algorithm` | **[C]** | For a **one-needle** skin, how the two channels become one: the average of them, or whichever is louder. |
| `stereo.algorithm` | **[C]** | The same choice for a two-needle skin, applied per channel. |
| `max.value` *(spectrum)* | **[C]** | How tall a bar has to be to reach the top. The spectrum's own version of `volume.max`. |

## 3. Where the numbers come from

| setting | **[ ]** | in plain words |
| --- | --- | --- |
| `data.source` | **[B]** | Where the levels are read. Ours is a named pipe fed by the ALSA tap (ADR-0011). The alternatives are a test generator, HTTP, or a serial port. |
| `pipe.name` | **[B]** | Which pipe. Ours is `/run/gexis/meter.fifo` and `/run/gexis/spectrum.fifo` — moved there from `/tmp` because `PrivateTmp` hid them. |
| `polling.interval` | **[B]** | How often that pipe is read. |
| `use.test.data` | **[C]** | Draw invented levels instead of the music. Only useful for checking a skin with nothing playing. |
| `left.channel.address` / `right.channel.address` | **[X]** | For reading levels out of shared memory — not how ours arrive. |
| `frequency`, `baud.rate`, `port`, `target.url`, `http.port`, `http.interface`, `serial.interface`, `web.server` | **[X]** | Ways of sending levels to *other* hardware — an Arduino, a web page, a serial display. This device draws them itself. |

## 4. Where the picture goes

| setting | **[ ]** | in plain words |
| --- | --- | --- |
| `output.display` | **[B]** | Draw on the screen. On for us. |
| `output.serial` / `output.http` / `output.pwm` | **[X]** | Drive a separate physical meter, a web page, or analogue needles wired to the Pi's pins. |
| `gpio.pin.left` / `gpio.pin.right` | **[X]** | Which pins those analogue needles are on. |
| `width`, `height`, `depth` | **[B]** | The screen: 1280×800. |
| `video.driver`, `video.display`, `framebuffer.device`, `sdl.env`, `double.buffer`, `no.frame` | **[B]** | How the picture reaches the panel. Settled by ADR-0026 and the image. |
| `output.size` | **[B]** | Which resolution folder of skins to use — `1280x800` here. |

## 5. Touch and exit

| setting | **[ ]** | in plain words |
| --- | --- | --- |
| `exit.on.touch` | **[B]** | Whether touching the screen closes the visualiser. Ours does not use this: the panel owns the touch and tells the daemon (ADR-0036), because a touch on a *phone* must not close the screen in another room. |
| `stop.display.on.touch` | **[B]** | As above. |
| `mouse.enabled`, `mouse.driver`, `mouse.device` | **[B]** | Pointer handling for the meter's own window. |

## 6. Skin geometry — how one skin is drawn

**These live in the skin, not in a settings screen.** They are here because
they are what goes wrong when a skin renders badly, and two of ours do
([Finding 048](../findings/048-two-skins-that-render-wrong.md)).

| setting | in plain words |
| --- | --- |
| `meter.type` | `circular` for a swinging needle, `linear` for a row of segments. |
| `channels` | One needle or two. |
| `bgr.filename` / `fgr.filename` | The picture behind the needle (the dial face) and the one in front of it (glass, bezel). |
| `indicator.filename` | The needle itself. |
| `screen.bgr` | The whole backdrop the meter sits on. |
| `meter.x` / `meter.y` | Where on screen the dial face is placed. |
| `left.origin.x/y`, `right.origin.x/y`, `mono.origin.x/y` | **The pin the needle swings around.** If this is not on the dial, the needle hangs in space — which is exactly the Teletronix fault. |
| `start.angle` / `stop.angle` | The angles for silence and for full scale. If these do not match the printed scale, the needle sweeps the wrong part of the dial — the Kenwood fault. |
| `left.start.angle` etc. | The same, per channel, when the two dials differ. |
| `distance` | How far the needle's tip reaches from its pin. |
| `steps.per.degree` | How finely the needle's rotation is pre-drawn. Higher is smoother and uses more memory. |
| `left.needle.flip`, `flip.left.x`, `flip.right.x` | Mirror the needle, for a dial that sweeps the other way. |
| `needle.width` / `needle.height` | The needle's size when it is drawn rather than loaded from a picture. |
| `left.center.x/y`, `left.x/y`, `mono.x/y` | Placement of a *linear* meter's segments. |
| `direction` | Which way a linear meter fills. |
| `step` | How many segments it has. |
| `include.time` | Whether the skin draws a clock. |
| `base.path`, `base.folder`, `meter.folder`, `spectrum.folder` | Where the skin's files are. **We change `base.path` per skin** so one engine can draw skins from four different folders (ADR-0051). |
| `use.cache`, `cache.size` | How many pre-rotated needles are kept in memory. |

## 7. Spectrum-only

| setting | **[ ]** | in plain words |
| --- | --- | --- |
| `spectrum` | **[S]** | Which spectrum skin — our `skin` row covers both kinds. |
| `size` | **[B]** | How many bars. |
| `update.ui.interval` | **[C]** | How often the bars are redrawn. |
| `use.logging` | **[B]** | Write a log. |

## 8. What our ALSA tap adds

Set in `output.conf`, not in Peppy — they shape the numbers before Peppy
sees them, so they change the picture just as much.

| setting | **[ ]** | in plain words |
| --- | --- | --- |
| `decay_ms` | **[C]** | **How slowly a needle falls back** after a peak. This is the one that makes a meter feel like a real VU rather than a twitching bar. Ours is 400 ms. |
| `meter_max`, `spectrum_max` | **[B]** | The largest number sent — must agree with `volume.max.in.pipe`. |
| `spectrum_size` | **[B]** | How many frequency bands. Ours is 30. |
| `logarithmic_frequency` | **[C]** | Whether the bars are spaced by octaves (how hearing works) or evenly by frequency. On. |
| `logarithmic_amplitude` | **[C]** | Whether bar height follows decibels rather than raw amplitude. On. |
| `smoothing_factor` | **[C]** | How much neighbouring bars are averaged together — higher is a smoother, less jumpy shape. |
| `window` | **[C]** | The maths window used for the frequency analysis. Changes how sharp or smeared the bars look. |

---

## The ten with direct visual impact

**George, 2026-09-23:** *"surface the top 10 with direct visual impact for
the user and explain them."* In order of how much a listener would notice.

**1. `volume.gain.db` — how much of the dial the needles actually use.**
Everything else on this list is cosmetic next to it. Too low and the
needles hover near the left stop all evening and the meter looks dead; too
high and they sit pinned in the red and stop telling you anything. This is
the one knob that decides whether the visualiser *means* something.

**2. `decay_ms` (our ALSA tap) — how slowly a needle falls back.** The
single biggest difference between something that feels like a real VU
meter and something that feels like a twitching bar chart. A real meter has
weight: it rises fast and settles slowly. Ours is 400 ms. Shorter is
nervous; much longer and it stops following the music.

**3. `smooth.buffer.size` — how jumpy the needle is on the way up.**
Averages the last few readings before moving. Bigger is calmer and lags
behind the beat; smaller reacts to every transient and can look like it is
vibrating. Works with `decay_ms`: one shapes the rise, the other the fall.

**4. `update.period` — how long a skin stays before the next one.** Only
matters with rotation on. Short enough and the changing skin becomes the
thing you look at rather than the music; long enough and you forget it
rotates at all.

**5. `max.value` (spectrum) — how tall a bar has to be to reach the top.**
The spectrum's version of gain. Set wrong, the bars either barely leave the
floor or spend the whole track slammed against the ceiling.

**6. `smoothing_factor` (our ALSA tap) — how much neighbouring bars are
averaged.** Low gives a spiky, comb-like shape that moves a lot; high gives
a smooth rolling hill. Changes the character of the spectrum more than
anything else on it.

**7. `logarithmic_amplitude` (our ALSA tap) — whether bar height follows
decibels or raw amplitude.** On, the quiet parts of the music are visible.
Off, almost everything sits near the bottom and only the loudest moments
move, because hearing is logarithmic and raw amplitude is not.

**8. `logarithmic_frequency` (our ALSA tap) — whether the bars are spaced
by octaves or evenly by frequency.** On, bass and treble get comparable
space and the display looks like music. Off, nearly every bar is treble,
because the top octave is half the frequency range.

**9. `ui.refresh.period` / `frame.rate` — how smooth the movement is.**
Thirty times a second looks fluid; ten looks like a slideshow. **This is
also a cost**: it is the visualiser competing with the panel for the same
GPU, which is Phase 9 criterion 0's subject.

**10. `mono.algorithm` / `stereo.algorithm` — what a needle is showing.**
For a one-needle skin, whether it shows the average of both channels or
whichever is louder. Average is calmer and more honest about level; peak
catches things the average hides. On a two-needle skin, the same choice
applied per side.

**Not on the list, deliberately:** everything in §6. Those are the skin's
own drawing instructions, and getting one wrong is how a skin ends up on
[Finding 048](../findings/048-two-skins-that-render-wrong.md) rather than
how a user tunes anything.
