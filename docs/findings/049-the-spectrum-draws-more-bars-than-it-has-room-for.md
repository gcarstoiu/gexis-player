# Finding 049 — The spectrum draws more bars than the skin has room for

> **Corrected 2026-09-23, the same day.** The fix below used each section's
> `steps` as its bar count, on ADR-0015's word. **`steps` is not the bar
> count** — `spectrum.py` sets `step = bar area height / steps`, the height
> of one vertical segment of a bar. The right number is `room` alone, and
> using it gives ten skins back resolution the first version threw away.
> The two sections from "The fix" on are rewritten; the overflow
> measurement that opens the finding is unchanged and still correct.

**Date:** 2026-09-23
**Raised by:** George, on the device: *"the spectrum bars are actually
falling slightly outside their designated area in the right"*
**Scope:** all 22 spectrum sections in the two installed packs (`gelo5`,
13 sections, and `stock`, 9), at 1280x800, measured from their own
`spectrum.txt` and the pixel width of their own background PNG. One
section (`Kenwood Big`, reached through the skin `105G5_Kenwood Spectrum`)
was also photographed on the panel with music playing. **Not tested:**
other resolutions, packs not installed, and whether the peak-hold
`topping` sprite overhangs the last bar.

## What the engine does

`spectrum.py` draws `config[SIZE]` bars. `SIZE` is one number, `size`, in
the global `/opt/gexis-peppy/spectrum/config.txt`, and it applies to every
skin alike. It was 30.

**No section's artwork has room for 30.** They hold 20 to 22, and the
surplus ran off the right-hand end. That is what George saw.

Each section also carries `steps`, which
[ADR-0015](../decisions/0015-skin-renderer-peppymeter-format.md) recorded
as *"bar count — 15, 20, 25 or 30"*. **It is not the bar count** — see
"The first version used the wrong number" below — and the engine reads it
for something else entirely.

## What was measured

For each section, the room its own background holds:

```
room = (background width − origin.x + bar.gap) // (bar.width + bar.gap)
```

- **All 22 sections overflow at 30 bars.** The worst, `s.7`, holds 20 in
  250px; thirty bars would need 355px of that 250px background.
- **The most any section holds is 22**, the least 20. The 30 in the config
  was never right for any skin in either pack.

## The fix, and what it does not do

`gexis-peppy-driver.py` writes, as the global `size` before the engine
starts, **the number of bars the selected section's own artwork has room
for**:

```
room = (background width − origin.x + bar.gap) // (bar.width + bar.gap)
```

capped at the 30 bands peppyalsa puts in the pipe — never more bars than
there are measurements.

**Measured over all 22 sections: every one holds 20, 21 or 22.** None holds
30, which is why every one of them overflowed.

| room | sections |
| --- | --- |
| 20 | `Marschal`, `Lyng`, `Kenwood Big`, `Kenwoo`, `475A`, `KeyS`, `s.1`, `s.5`, `s.7` |
| 21 | `OPipe`, `Marantz`, `Peppy`, `Teletronix`, `s.4`, `s.8` |
| 22 | `Free`, `Naim`, `Old`, `s.2`, `s.3`, `s.6`, `s.9` |

### The first version used the wrong number

It took the section's `steps` and clamped *that* to `room`.
[ADR-0015](../decisions/0015-skin-renderer-peppymeter-format.md) recorded
`steps` as *"bar count — 15, 20, 25 or 30"*, and it is not. `spectrum.py`
computes

```python
self.step = int(self.height / self.spectrum_configs[self.index][STEPS])
```

— the height of one **vertical** segment of a bar. `steps` says how finely
a bar's height is quantised and nothing about how many bars there are. The
bar count is `config[SIZE]`, the global number, which is what both versions
write.

It produced numbers that fit, because they were clamped to `room` anyway,
so nothing overflowed and the screen looked right. **What it cost was
resolution**, on ten of the twenty-two: `s.1` drew 12 bars in a frame that
holds 20; `Naim` 15 in a frame that holds 22; `s.6`–`s.9` 16 in frames
holding 20 to 22; `Marantz`, `Peppy`, `Teletronix` and `KeyS` 20 where 21
fit. That is the opposite of what the fix was for — George asked for a
solution that did not cut the bar count and lose resolution.

**ADR-0015's line is corrected.** [LESSONS](../LESSONS.md) case 23: the
repository's own record was the wrong answer, and searching it first — the
right instinct, and this project's own rule — is not the same as checking
it.

**The pipe is not narrowed.** peppyalsa keeps sending 30 bands
([ADR-0011](../decisions/0011-meter-data-three-transports.md)). Cutting the
pipe would cost every skin resolution; `room` only ever limits what is
*drawn*. **The bar width is not changed either** — the bar is a sprite the
skin's author drew at a fixed size, and narrowing it would scale their
artwork.

**Nothing in the skin packs is edited.** The count is computed at load, so
a pack nobody has seen yet gets the same treatment, and the stock pack's
files stay as shipped.

## After

Re-measured across all 22: **none overflows**, and each draws the most its
own artwork allows. The log says so at selection:

```
Free: 933px holds 22 bars, drawing 22
```

Photographed on the panel with LMS playing: the bars sit inside the frame,
clear of the right-hand screw.

## What is left

- **Nothing was heard.** Every judgement here is pixels and arithmetic.
- **1280x800 only.** The packs ship other resolutions; none was measured.
- **`steps` is left alone.** It is the vertical quantisation and it is the
  skin author's choice; with 12 to 30 segments over a bar's height, a bar
  moves in visible jumps however smooth the number feeding it is. That is
  a separate question from this one.
