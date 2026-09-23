# Finding 049 — The spectrum draws more bars than the skin has room for

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

Each section in `spectrum.txt` also carries `steps`
— [ADR-0015](../decisions/0015-skin-renderer-peppymeter-format.md) records
it as *"bar count — 15, 20, 25 or 30"* — and **the engine never reads it.**
The skins' own counts are 12, 15, 16, 20, 25 and 30.

So a section drawn for twelve bars was given thirty, and the surplus ran
off the right-hand end of its artwork. That is what George saw.

## What was measured

For each section, the room its own background holds:

```
room = (background width − origin.x + bar.gap) // (bar.width + bar.gap)
```

- **All 22 sections overflow at 30 bars.** The worst, `s.7`, holds 16 and
  needs 250px for them; thirty would need 480px of a 250px background.
- **12 of the 22 overflow at their own declared `steps` as well.**
  `Kenwood Big` declares 30 and holds 20: thirty bars need 1262px of an
  850px background. `Marschal`, `Lyng`, `Kenwoo`, `475A`, `OPipe`, `Free`,
  `Old`, `s.2`, `s.3`, `s.4` and `s.5` are the others.
- **10 fit as declared** and are left alone: `Naim` 15, `Marantz` 20,
  `Peppy` 20, `Teletronix` 20, `KeyS` 20, `s.1` 12, `s.6`, `s.7`, `s.8`,
  `s.9` 16.

## The fix, and what it does not do

`gexis-peppy-driver.py` now reads the selected section's `steps` and
clamps it to the room measured above, then writes that number as `size`
before the engine starts — so `size` is per-skin, not global.

**The pipe is not narrowed.** peppyalsa keeps sending 30 bands
([ADR-0011](../decisions/0011-meter-data-three-transports.md)). Cutting the
pipe to 20 would cost resolution on every skin, including the ten drawn
for enough bars to use it; only what is *drawn* changes. **The bar width
is not changed either** — the bar is a sprite the skin's author drew at a
fixed size, and narrowing it would scale their artwork.

**Nothing in the skin packs is edited.** The clamp happens at load, so a
pack nobody has seen yet gets the same treatment, and the stock pack's
files stay as shipped.

## After

Re-measured across all 22: **none overflows.** `Kenwood Big` now draws 20
bars needing 842px of its 850, and the log says so at selection:

```
Kenwood Big: drawn for 30 bars, 850px holds 20
```

Photographed on the panel with LMS playing: the bars sit inside the
frame, clear of the right-hand screw.
