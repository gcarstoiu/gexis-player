# Finding 027 — Both engines in one process: the composition point, and five traps on the way

**Date:** 2026-09-16
**Question:** ADR-0026's amendment puts the driver on us. What does composing
PeppyMeter and PeppySpectrum actually require, given neither is modified?
**System:** `gexis`, current image, LMS playing, engines and the stock
1280x800 skins in `/tmp/spike/gx`, fed by our visualisation service's
passthrough pipes. Skin `galaxy-spectrum` (`meter.visible = False`).

## Result

**It works.** Spectrum bars render over the skin's background and animate
with the music, in the same process as PeppyMeter, 28 % of one core. A
screenshot taken on the device shows the bars; frames 2 s apart differ.

**The composition point is upstream's own:** `Peppymeter.dependent` is called
once per frame by its display loop. Nothing is patched in either engine.

## Five things that had to be got right

Each failed first, and each failure looked like something else:

1. **`init_display()` is not called by the constructor.** Upstream's entry
   point calls it afterwards (`peppymeter.py:289`); until it runs there is no
   surface, and `util.PYGAME_SCREEN` does not exist.
2. **The folder name is validated.** `meter.folder` must start with a digit
   and parse as WIDTHxHEIGHT, else the engine prints one line and calls
   `os._exit(0)` — invisible without `python3 -u`. Same rule for
   `spectrum.folder`. Our install therefore nests a `1280x800` folder.
3. **Import spelling follows the layout.** With the engine's own directory on
   `sys.path` the module is `spectrum`, not the wrapper's `spectrum.spectrum`.
4. **PeppySpectrum's base class wants Peppy player's config object**, which
   PeppyMeter's utility has not got. Shadowing that one class is how the
   Volumio wrapper solves it; ours does the same, and also takes the
   spectrum's position from the spectrum section rather than the skin.
5. **Its refresh thread cannot draw under Wayland.** `Spectrum.start()`
   spawns a thread that calls `pygame.display.update()`, which fails with
   *"Unable to make EGL context current"* — the GL context belongs to the
   thread that made it. Setting `callback_start` suppresses that thread
   (upstream's own hook), and drawing happens on the meter's loop instead.

**And one that produced no error at all:** with the drawing moved onto the
meter's loop, the screen stayed static. PeppyMeter updates only the meter's
own dirty rectangles, and our hook runs *after* that update — so the spectrum
was drawn and never presented. The hook now presents its own region.

## Not established

- **Only one skin was exercised**, on the stock corpus. Gelo5's 13
  spectrum-linked skins are untested, as are their sizes and positions.
- **No rotation.** `meter = random` means PeppyMeter chooses the skin and the
  driver cannot pair a spectrum with it; the driver says so and runs
  meters-only. That is criterion 5's work.
- **Cost with both**: 28 % of one core, one sample, alongside Chromium.
- Not run from the systemd unit, and not from an installed image.
