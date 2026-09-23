# Finding 048 — Two skins that render wrong, and what arbitration watches

**Date:** 2026-09-23
**Question:** George photographed the panel: *"a visualisation with broken
vu meters. Please check and fix."* And separately: *"Measure it"*, on the
arbitration gap flagged when ADR-0055 landed.

**Scope:** `gexis`, 2026-09-23, 1280×800, against the deployed build. **The
skins were judged as pixels** — captured off the panel with `grim` and
compared against one that works — not inferred from their configuration.
**Seven of the pack's nine `S+M` skins were not looked at**, and nothing
here claims anything about them.

## 1. It is two skins, not a class

Captured, all three at the same moment in the same track:

| skin | pack | result |
| --- | --- | --- |
| `01G5_Accuphase` | `gelo5/templates` | **correct** — needles on the scale |
| `111G5_Teletronix S+M` | `gelo5/templates_spectrum` | **wrong** — one dial blank, both needles off the face |
| `108G5_Kenwood Rev S+M` | `gelo5/templates_spectrum` | **wrong** — needles cross the face diagonally |

**The first guess was wrong and is recorded because it cost time.** "The
spectrum pack is broken" is contradicted by `103/105/106G5_*Spectrum`,
which have no needles at all, and by the other `S+M` skins not being
examined. "Two packs name a skin the same thing and one overwrites the
other" is contradicted by the count: 99 sections, 99 unique names.

## 2. Teletronix: the needle pins are not on the dial

```
bgr.filename  ->  672 x 302      meter.x = 0, meter.y = 0
left.origin   ->  (317, 350)
right.origin  ->  (963, 350)
```

The dial face is drawn as a 672×302 picture at the top-left corner, so it
occupies `(0,0)–(672,302)`. **Both needle pins are outside it** — one below
it, one below *and* to the right of it. The needles are drawn correctly
around pins that are not on any dial, which is why one meter shows a face
with a needle hanging off it and the other shows a needle with no face.

**Sub-screen artwork is not itself the fault.** The stock pack is full of
it — `gold` is 1280×290, `galaxy` is 480×170 — and those skins place it
with `meter.x`/`meter.y`. This one places it at the origin and then puts
the pins elsewhere.

## 3. Kenwood Rev: the needles sweep a quadrant the scale does not occupy

```
start.angle = -227      stop.angle = -133      distance = 190
left.origin = (319, 435)
```

**It is the only skin of all 99 whose `start.angle` is not between 0 and
65.** Checked across every section of all three `meters.txt` files.

The needle obeys the configuration exactly — from the pin at (319, 435) a
339-pixel needle at −227° lands within a pixel or two of where the capture
shows it. **The configuration is what does not match the artwork**, whose
dials are in the lower half of the screen with their pins near y ≈ 490.

## 4. What was done

Both are excluded from the corpus (`skins.BROKEN`), each with the
measurement as its reason. **Not a validator**: the two faults have
different shapes — one is "the pin is off the dial", which is checkable,
and the other is "the angles do not match a picture", which is not
checkable without knowing where the printed scale is inside the image. A
rule general enough to catch both would exclude working skins.

**The corpus is 97, not 99.** ADR-0051's count changes with it.

**Open:** the other seven `S+M` skins in that pack. Each needs a capture
and a look, which is ten minutes and a decision per skin, not a rule.

## 5. Arbitration watches one card, whatever the output is

Flagged when ADR-0055 landed and measured here on George's *"Measure it"*.

`alsa.CARD_ID` is a module constant, `"sndrpihifiberry"`. `device_busy()`
and `device_held_by()` default to it, and the release ladder
(`arbitration.py`) calls them that way.

**With the output switched to the headphone jack and something holding it:**

```
  something IS holding the chosen output (hw:Headphones):
    Headphones         busy=True   holder=10531
    sndrpihifiberry    busy=False  holder=-

  what arbitration actually asks:
    alsa.device_busy() -> False
    i.e. it is looking at /dev/snd/pcmC5D0p - the HiFiBerry
```

**So on any output but the DAC, the release ladder cannot see who holds the
device.** It would read "already released" the instant a polite stop was
sent, and hand the device over while the outgoing renderer still had it.

**It predates ADR-0055** — the constant has been there since Phase 2 — but
ADR-0055 is what made a second output reachable, so it is now possible to
get into this state from the settings screen.

**Not fixed here.** The fix is to thread the chosen output's card through
`alsa`'s three functions and the supervisor, which is a change to
arbitration's contract and wants its own record.

## What is left, and what it needs

- **Seven `S+M` skins unexamined**, above.
- **Arbitration's card**, above — needs a decision on whether the card
  follows the output or arbitration is scoped to the DAC by definition.
- **Nothing here was heard.** Every judgement is from pixels and from
  `fuser`; no skin was assessed for whether it *looks good*, only for
  whether its needles are on its dials.
