# Finding 050 — Two skins draw the spectrum's panel as their meter face

**Date:** 2026-09-23
**Question:** George, after [Finding 048](048-two-skins-that-render-wrong.md)
excluded two skins: *"Check all and don't just exclude, but try to fix
them."*
**Scope:** all 99 skins of both installed packs at 1280×800, on `gexis`,
against the deployed build. The file-level check is over every section;
the needle-sweep check is over the 60 circular ones; four skins were
photographed with LMS playing. **Not tested:** other resolutions, the 39
linear sections' own drawing, and whether any skin *looks good* — only
whether it draws where it means to.

## What George actually saw

> *"the arrows of the vu meters were trailing some shadows behind and the
> in the left, the was an overlay on top of the actual meter."*

## The cause: `bgr.filename` names the spectrum's panel

`111G5_Teletronix S+M` declares

```
bgr.filename = Teletronix_bgr.png      672 x 302     (meters.txt)
fgr.filename = Teletronix_fgr.png     1280 x 400
screen.bgr   = Teletronix.jpg         1280 x 800
```

and `spectrum.txt` declares, for its own section `Teletronix`:

```
bgr.filename = Teletronix_bgr.png      the same file
```

**That file is the spectrum's panel** — a plain blank frame the bars are
drawn into. Opened on its own it is exactly what the broken capture showed
sitting over the left dial, red border and all.

Two consequences, which are George's two symptoms:

- **The overlay.** `meter.py` draws the meter background once at
  `meter.x, meter.y` — here `(0, 0)`, on top of the dial artwork that
  `screen.bgr` had just painted. The left dial disappears under a blank
  panel.
- **The trails.** To move the needle, `meter.draw_bgr_fgr` repaints the
  area it last occupied *out of that same file*, blitting from
  `(rect.x − meter.x, rect.y − meter.y)`. pygame clips a source rectangle
  to its surface but leaves the destination where it was, so every part of
  the needle's travel outside 672×302 is repainted with the wrong pixels or
  not at all. What is not repainted stays on the screen — the smear.

**`107G5_Marantz S+M` has the identical defect** (`Marantz_bgr.png`,
406×134, is that skin's spectrum panel) and nobody had reported it,
because the skin has to be selected to be seen.

**These two are the only ones.** Checked mechanically: for every circular
section in both packs, is its `bgr.filename` also some spectrum section's
`bgr.filename`? Two hits, both above.

## The fix

**The meter background becomes the section's own `screen.bgr`** — the
picture that holds the dials — for those two sections only. It is applied
in the image build after the pack is compared against `skins/`, so the
comparison keeps seeing upstream exactly as it ships, and the correction
is one visible `sed` with an assertion behind it. `spectrum.txt` is not
touched: those panels are still the spectrum's own backgrounds.

**Photographed after, with LMS playing**: both dials draw, both needles sit
on their scales, nothing trails, nothing overlays. The spectrum below them
is unchanged.

A standing check goes with it (`meter-background-check.awk`, run in the
build over every `meters.txt` against every `spectrum.txt` of the same
pack): **a circular meter may not draw a spectrum section's background.**
awk rather than python3, which the build container does not have.

## `108G5_Kenwood Rev S+M` was never broken

Finding 048 excluded it for having *"needles [that] sweep a quadrant its
scale does not occupy"*, on the strength of its `start.angle = -227` being
the only one of 99 outside 0…65.

**Photographed with music playing, it renders correctly.** It is a reverse
dial: the needles hang from a pin at the top of each face and swing
downward, which is what −227° means and what the artwork draws. The
earlier capture that suggested otherwise was taken while nothing was
playing, so it was a held last frame, not a rendering.

That exclusion is withdrawn. `skins.BROKEN` is now empty.

## The needle-sweep model, and what it is worth

A second check computes, for each circular section, the screen rectangle
the needle's repaint touches over its whole sweep — reproducing
`needlefactory.rotate_image` and `circular.set_sprite`, including the 4px
`gap` — and compares it with the rectangle the background can supply.

**The first version of it flagged 50 of 60 skins.** It had
`image_bottom = (0, 0)` where the engine has `(w/2, h)`. Corrected, and
with the off-screen part clipped away (pygame trims source and destination
together at the screen edge, so an overshoot that leaves the screen stays
in register), it flags **ten**:

| skin | leaves its background by |
| --- | --- |
| `107G5_Marantz S+M` | right 524, bottom 444 |
| `111G5_Teletronix S+M` | right 526, bottom 53 |
| `56G5_Advence` | bottom 16 |
| `black-white`, `black-blue` | top 12, bottom 5–6 |
| `36G5_Klanghelm` | bottom 9 |
| `08G5_McIntosh Hybrid` | bottom 7 |
| `red`, `galaxy` | bottom 4–5 |
| `48G5_Vertical blue` | bottom 2 |

The two gross ones are the two above. **The other eight overshoot by 2 to
16 pixels** — the `gap` inflation and rotation rounding — into the black
below the dial. `56G5_Advence` (the worst) and `black-white` were
photographed with music playing: **both are clean.** No engine change is
made for them, because nothing was seen.

The model is recorded, not shipped: it needs the images, and the corpus
the repository validates is the config files alone.

## What is left

- **Nothing was heard.** Every judgement here is pixels.
- **39 linear sections** were checked for the file-level defect and have
  none; their own drawing was not modelled.
- **Four skins photographed**, not 99. The file-level check is exhaustive;
  the photographs are not.
