# Finding 048 — Two skins that render wrong, and what arbitration watches

> **Superseded in part, 2026-09-23, by
> [Finding 050](050-two-skins-name-the-wrong-background.md).** §2's
> arithmetic holds but names the wrong cause; §3 is wrong outright — that
> skin renders correctly; §4's exclusions are withdrawn, both skins are
> offered again and `skins.BROKEN` is empty. §1 and §5 stand.

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

## 2. Teletronix: what it looks like, and why

> **The cause given below is not the cause.** Both pins are indeed outside
> the 672×302 rectangle, and the restore is indeed bounded by it — but the
> reason that rectangle is 672×302 is that `bgr.filename` names the
> *spectrum's* panel rather than the dial artwork. With the right picture
> the pins are inside it and the skin draws correctly.
> [Finding 050](050-two-skins-name-the-wrong-background.md) has the
> measurement and the fix.

**George described it from the panel** and his description is the better
one, because it is what a person sees:

> *"the arrows of the vu meters were trailing some shadows behind and in
> the left, there was an overlay on top of the actual meter."*

**Both symptoms come from one cause, and the first version of this finding
gave the cause without connecting it to either symptom.**

```
bgr.filename  ->  672 x 302      meter.x = 0, meter.y = 0
left.origin   ->  (317, 350)
right.origin  ->  (963, 350)
```

The dial face is drawn as a 672×302 picture at the top-left corner, so it
occupies `(0,0)–(672,302)`. **Both needle pins are outside it** — one below
it, one below *and* to the right of it.

- **The overlay on the left** is that 672×302 picture. It lands over the
  left dial rather than on it, so the printed scale is covered by a blank
  face.
- **The trailing shadows** are the same rectangle seen from the other side.
  `meter.py`'s `reset_bgr_fgr` sets the restore area to
  `comp.content[1].get_rect()` — **the background image's own rectangle**.
  Every frame repaints only inside it. A needle sweeping outside it moves
  across pixels nobody ever repaints, so each position it leaves behind
  stays on the screen. That is the smear.

Read from the engine, not inferred: the restore is bounded by the image,
and the needles are outside the image.

**Sub-screen artwork is not itself the fault.** The stock pack is full of
it — `gold` is 1280×290, `galaxy` is 480×170 — and those skins place it
with `meter.x`/`meter.y`. This one places it at the origin and then puts
the pins elsewhere.

## 3. Kenwood Rev: the needles sweep a quadrant the scale does not occupy

> **Wrong. This skin renders correctly.** −227° is a *reverse* dial: the
> needles hang from a pin at the top of each face and swing down, which is
> what the artwork draws. The capture this section rests on was taken with
> nothing playing, so it was a held last frame. Photographed again with
> music playing, the needles sit on the scale.
> [Finding 050](050-two-skins-name-the-wrong-background.md).

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

> **Withdrawn 2026-09-23.** Neither skin is excluded now; `skins.BROKEN` is
> empty and the corpus is 99 again. Teletronix is corrected in the image,
> and so is `107G5_Marantz S+M`, which had the same defect and was not
> noticed here. The "not a validator" paragraph is also wrong: one of the
> two faults *was* checkable, mechanically and over the whole corpus, once
> it was understood. [Finding 050](050-two-skins-name-the-wrong-background.md).

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

**Fixed the same day**, on George's *"Any output holding the device follows
the same arbitration as the DAC. Needs to be fixed."*

`alsa` gains a current card — `set_card()` / `card()` — and every function
defaults to it instead of to `CARD_ID`, which stays as the card the device
ships with. `__main__` points it at the chosen output at startup and on
every switch, and the `alsactl monitor` is moved with it by ending it: its
own loop already restarts it, and that path was written for the monitor
dying on its own.

**Verified from the daemon's own log**, not from a probe — a separate
process imports a fresh module and would have reported the default
whatever the daemon believed:

```
gexis_core.alsa   INFO alsa: arbitration now watches Headphones
gexis_core.volume INFO volume: moving the mixer monitor to Headphones
```

## What is left, and what it needs

- ~~**Seven `S+M` skins unexamined**~~ **Closed 2026-09-23:** all 99 were
  checked for the file-level defect and four photographed
  ([Finding 050](050-two-skins-name-the-wrong-background.md)).
- **Arbitration's card**, above — needs a decision on whether the card
  follows the output or arbitration is scoped to the DAC by definition.
- **Nothing here was heard.** Every judgement is from pixels and from
  `fuser`; no skin was assessed for whether it *looks good*, only for
  whether its needles are on its dials.
