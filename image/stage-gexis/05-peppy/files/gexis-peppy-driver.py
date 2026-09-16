#!/usr/bin/python3 -u
# SPDX-License-Identifier: GPL-3.0-or-later
"""Runs PeppyMeter and PeppySpectrum in one process (ADR-0026, Phase 5).

Both engines draw into the same pygame surface: PeppyMeter owns the loop and
calls `dependent` once per frame, which is where the spectrum is drawn. That
hook is upstream's own composition point, not a patch — foonerd's Volumio
wrapper uses the same one.

Why this exists at all: a skin with `meter.visible = False` draws no meter,
so its whole motion is the spectrum. Running PeppyMeter alone leaves those
skins as still images (Finding 026).

**The cwd trap** (docs/reference/peppymeter-fork-on-moode.md): each engine
reads `config.txt` from the *working directory*, and the spectrum engine
calls `os._exit(0)` when it cannot find one — a silent exit 0 with an empty
log unless Python runs unbuffered. Hence `-u` above, the absolute paths in
both configs, and the deliberate chdir below.
"""
from __future__ import annotations

import configparser
import os
import sys
from pathlib import Path

# Overridable so the driver can be exercised from a scratch copy on a device
# whose image predates this stage; the unit never sets it.
PEPPY = Path(os.environ.get("GEXIS_PEPPY_DIR", "/opt/gexis-peppy"))
METER_DIR = PEPPY / "peppymeter"
SPECTRUM_DIR = PEPPY / "spectrum"


def meter_sections(path: Path) -> dict[str, dict[str, str]]:
    """The skin file, read with the same tolerance the engines use: unknown
    keys are data, not errors. `make skins` is where a bad pack is rejected."""
    parser = configparser.ConfigParser(strict=False)
    parser.optionxform = str
    parser.read(path)
    return {name: dict(parser[name]) for name in parser.sections()}


def spectrum_for(skin: dict[str, str]) -> tuple[str, int, int] | None:
    """`spectrum.name` links a skin to a spectrum section **by name, never by
    index** (ADR-0015). A skin without the key simply has no spectrum."""
    name = skin.get("spectrum.name")
    if not name:
        return None
    size = skin.get("spectrum.size", "")
    try:
        width, height = (int(part) for part in size.split(",", 1))
    except ValueError:
        print(f"WARNING: {name}: spectrum.size {size!r} unusable, skipping spectrum", file=sys.stderr)
        return None
    return name, width, height


def select_spectrum_section(name: str) -> None:
    """Point the spectrum engine's own config at one section. Rewritten in
    place: configparser fails hard on a duplicate key, and an appended one
    would stop the process starting."""
    path = SPECTRUM_DIR / "config.txt"
    parser = configparser.ConfigParser()
    parser.read(path)
    parser["current"]["spectrum"] = name
    with path.open("w") as handle:
        parser.write(handle)


def install_screensaver_shim(name: str, width: int, height: int) -> None:
    """PeppySpectrum's base class expects Peppy player's own config object,
    which PeppyMeter's utility does not have. Upstream's plug-in model assumes
    the whole player; shadowing that one class is how the Volumio wrapper
    solves it too, and it is the smallest change that keeps both engines
    unmodified.

    It also fixes where the spectrum goes: the position belongs to the
    spectrum section (`spectrum.x`/`spectrum.y`), not to the meter skin.
    """
    import types

    import pygame
    from spectrumconfigparser import (
        AVAILABLE_SPECTRUM_NAMES,
        SPECTRUM_X,
        SPECTRUM_Y,
        SpectrumConfigParser,
    )

    class ScreensaverSpectrum:
        def __init__(self, spectrum_name, util, plugin_folder):
            self.util = util
            self.name = spectrum_name
            self.plugin_folder = plugin_folder
            self.update_period = 1
            self.ready = True
            # No background of its own: it draws over the skin's.
            self.bg = (None, None, None, None)
            self.w, self.h, self.s = util.spectrum_size

            parser = SpectrumConfigParser(standalone=False)
            parser.config[AVAILABLE_SPECTRUM_NAMES] = [self.s]
            sections = parser.get_spectrum_configs()
            if not sections:
                raise RuntimeError(f"spectrum section {self.s!r} is not in the installed corpus")
            util.screen_rect = pygame.Rect(
                sections[0][SPECTRUM_X], sections[0][SPECTRUM_Y], self.w, self.h
            )

        def get_update_period(self):
            return self.update_period

        def set_image(self, image):
            pass

        def set_image_folder(self, state):
            pass

        def set_volume(self, volume):
            pass

    module = types.ModuleType("screensaverspectrum")
    module.ScreensaverSpectrum = ScreensaverSpectrum
    sys.modules["screensaverspectrum"] = module


def main() -> int:
    sys.path.insert(0, str(METER_DIR))
    sys.path.insert(0, str(SPECTRUM_DIR))

    os.chdir(METER_DIR)  # PeppyMeter reads ./config.txt

    # Read the same file PeppyMeter is about to read: its parsed config keeps
    # base.folder only as a local, so there is nothing to ask it for.
    meter_config = configparser.ConfigParser()
    meter_config.read(METER_DIR / "config.txt")
    current = meter_config["current"]
    skin_name = current.get("meter", "").strip()
    corpus = Path(current.get("base.folder", "")) / current.get("meter.folder", "")

    from peppymeter import Peppymeter

    peppy = Peppymeter(standalone=True, timer_controlled_random_meter=False, quit_pygame_on_stop=False)
    # The constructor does not create the display: upstream's own entry point
    # calls this afterwards (peppymeter.py:289), and until it runs there is no
    # surface for either engine to draw on.
    peppy.init_display()
    util = peppy.util

    skins = meter_sections(corpus / "meters.txt")
    if skin_name not in skins:
        # `random`, or a comma-separated list: which skin is showing is
        # PeppyMeter's choice, and pairing a spectrum with it is criterion 5's
        # rotation work, not this driver's.
        print(f"peppy: meter = {skin_name!r} is not a single skin; meters only for now")
        skin = {}
    else:
        skin = skins[skin_name]
    wanted = spectrum_for(skin)

    if wanted is None:
        print(f"peppy: {skin_name} has no spectrum; meters only")
    else:
        name, width, height = wanted
        print(f"peppy: {skin_name} + spectrum {name} at {width}x{height}")
        from spectrumutil import SpectrumUtil

        # What PeppySpectrum expects of a util object, which PeppyMeter's does
        # not carry: the shared surface, an image helper, and its own extent.
        util.spectrum_size = (width, height, name)
        util.pygame_screen = util.PYGAME_SCREEN
        util.image_util = SpectrumUtil()

        select_spectrum_section(name)
        os.chdir(SPECTRUM_DIR)  # its config parser reads ./config.txt too
        install_screensaver_shim(name, width, height)
        # `spectrum`, not `spectrum.spectrum`: the engine's own directory is on
        # sys.path, so its modules are top-level. The Volumio wrapper's spelling
        # reflects its own nesting, not ours.
        from spectrum import Spectrum
        from spectrumconfigparser import AVAILABLE_SPECTRUM_NAMES, SCREEN_HEIGHT, SCREEN_WIDTH

        spectrum = Spectrum(util, standalone=False)
        spectrum.config[SCREEN_WIDTH] = width
        spectrum.config[SCREEN_HEIGHT] = height
        spectrum.config[AVAILABLE_SPECTRUM_NAMES] = [name]
        spectrum.spectrum_configs = spectrum.config_parser.get_spectrum_configs()
        spectrum.init_spectrums()
        # Setting callback_start takes the place of the engine's own refresh
        # thread (spectrum.py:371): that thread calls pygame.display.update()
        # itself, and a second thread touching the surface fails outright
        # under Wayland - "Unable to make EGL context current", because the
        # GL context belongs to the thread that made it. PeppyMeter's loop
        # does the drawing instead, through `dependent` below.
        spectrum.callback_start = lambda _spectrum: None
        spectrum.start()
        os.chdir(METER_DIR)

        import pygame

        def draw_spectrum() -> None:
            # draw(), not dirty_draw_update(): that one updates the display
            # from whatever thread calls it, which is what broke under
            # Wayland. Drawing here is on PeppyMeter's own loop thread.
            if not (spectrum.components and spectrum.components[0].content is not None):
                return
            clip = util.pygame_screen.get_clip()
            util.pygame_screen.set_clip(util.screen_rect)
            # Erase where the bars were, then draw where they are now.
            for rect in [r.copy() for r in getattr(spectrum, "_dirty_rects", []) if r]:
                spectrum.draw_area(rect)
            spectrum._dirty_rects = []
            spectrum.draw()
            util.pygame_screen.set_clip(clip)
            # PeppyMeter updates only the meter's own dirty areas, and this
            # hook runs after that update - so the spectrum has to present its
            # own region or it is drawn and never shown.
            rects = [r for r in getattr(spectrum, "_dirty_rects", []) if r]
            pygame.display.update(rects or [util.screen_rect])

        peppy.dependent = draw_spectrum

    peppy.start_display_output()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
