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
import random
import sys
from pathlib import Path

import pygame

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


class Rotation:
    """Phase 5 criterion 5: a new skin per track, with the next one built
    before it is needed.

    Random without repeats until the corpus is exhausted, which is what
    PeppyMeter's own random mode does — but driven by track changes rather
    than a timer, so the skin belongs to the track.
    """

    def __init__(self, peppy, skins: dict[str, dict[str, str]], spectrum_state) -> None:
        self.peppy = peppy
        self.vumeter = peppy.meter
        self.skins = skins
        self.spectrum = spectrum_state
        self.unseen: list[str] = []
        self.current: str | None = None
        self.prepared: tuple[str, object] | None = None

    def pick(self) -> str:
        if not self.unseen:
            self.unseen = [name for name in self.skins if name != self.current] or list(self.skins)
        return self.unseen.pop(random.randrange(len(self.unseen)))

    def prepare_next(self) -> None:
        """Build the next skin's meter now, so a track change costs no image
        loading. Done right after a switch, while the new skin is already on
        screen — the moment with the most slack, not the least."""
        name = self.pick()
        from configfileparser import METER
        from meterfactory import MeterFactory

        # Built through the factory, not `vumeter.get_meter()`: that returns
        # the *existing* meter unless the engine is in its own random mode, so
        # asking it for the next skin hands back the current one - which drew
        # each new skin with the previous skin's needles, and then no needles
        # at all (George saw it on the panel, 2026-09-16).
        vumeter = self.vumeter
        config = self.peppy.util.meter_config
        was, config[METER] = config[METER], name
        try:
            factory = MeterFactory(
                self.peppy.util,
                config,
                vumeter.data_source,
                vumeter.mono_needle_cache,
                vumeter.mono_rect_cache,
                vumeter.left_needle_cache,
                vumeter.left_rect_cache,
                vumeter.right_needle_cache,
                vumeter.right_rect_cache,
            )
            meter = factory.create_meter()
        finally:
            config[METER] = was
        self.prepared = (name, meter)

    def switch(self) -> None:
        if self.prepared is None:
            self.prepare_next()
        name, meter = self.prepared
        self.prepared = None

        from configfileparser import METER

        if self.vumeter.meter is not None:
            self.vumeter.meter.stop()
        self.peppy.util.meter_config[METER] = name
        self.vumeter.meter = meter
        meter.set_volume(self.vumeter.current_volume)
        meter.start()
        self.current = name
        print(f"peppy: skin -> {name}")
        self.spectrum.follow(self.skins.get(name, {}))
        pygame.display.update()
        self.prepare_next()


class SpectrumState:
    """One PeppySpectrum instance for the whole run, re-pointed at whichever
    section the current skin links to.

    Rebuilding it per skin would be simpler and wrong: `stop()` leaves its
    pipe open (spectrum.py:506), so every rebuild would leave another reader
    on the passthrough FIFO, splitting the bytes between them.
    """

    def __init__(self) -> None:
        self.spectrum = None
        self.util = None
        self.active = False

    def follow(self, skin: dict[str, str]) -> None:
        wanted = spectrum_for(skin)
        if wanted is None or self.spectrum is None:
            self.active = False
            return
        name, width, height = wanted
        from spectrumconfigparser import (
            AVAILABLE_SPECTRUM_NAMES,
            SCREEN_HEIGHT,
            SCREEN_WIDTH,
            SPECTRUM_X,
            SPECTRUM_Y,
        )

        here = Path.cwd()
        os.chdir(SPECTRUM_DIR)
        try:
            select_spectrum_section(name)
            spectrum = self.spectrum
            spectrum.config[SCREEN_WIDTH] = width
            spectrum.config[SCREEN_HEIGHT] = height
            spectrum.config[AVAILABLE_SPECTRUM_NAMES] = [name]
            spectrum.spectrum_configs = spectrum.config_parser.get_spectrum_configs()
            if not spectrum.spectrum_configs:
                print(f"peppy: spectrum {name!r} missing from the corpus; meters only", file=sys.stderr)
                self.active = False
                return
            spectrum.index = 0
            self.util.spectrum_size = (width, height, name)
            self.util.screen_rect = pygame.Rect(
                spectrum.spectrum_configs[0][SPECTRUM_X],
                spectrum.spectrum_configs[0][SPECTRUM_Y],
                width,
                height,
            )
            # Rebuild the images and geometry, but not the data source: that
            # would open a second reader on the pipe.
            spectrum.init_spectrums()
            spectrum.set_background()
            spectrum.set_bars()
            spectrum.set_reflections()
            spectrum.set_toppings()
            spectrum.set_foreground()
            spectrum.init_variables()
            spectrum._dirty_rects = []
            self.active = True
        finally:
            os.chdir(here)


def current_track(path: Path = Path("/var/local/www/currentsong.txt")) -> str | None:
    """Which track is playing, from the file the core daemon already writes
    (Phase 3 criterion 4). Cheaper than a second WebSocket client, and it
    needs no dependency this image does not have."""
    try:
        fields = dict(
            line.split("=", 1) for line in path.read_text().splitlines() if "=" in line
        )
    except OSError:
        return None
    key = "\t".join(fields.get(name, "") for name in ("title", "artist", "album"))
    return key if key.strip() else None


def main() -> int:
    sys.path.insert(0, str(METER_DIR))
    sys.path.insert(0, str(SPECTRUM_DIR))

    os.chdir(METER_DIR)  # PeppyMeter reads ./config.txt

    # Read the same file PeppyMeter is about to read: its parsed config keeps
    # base.folder only as a local, so there is nothing to ask it for.
    meter_config = configparser.ConfigParser()
    meter_config.read(METER_DIR / "config.txt")
    current = meter_config["current"]
    corpus = Path(current.get("base.folder", "")) / current.get("meter.folder", "")
    skins = meter_sections(corpus / "meters.txt")
    if not skins:
        print(f"ERROR: no skins in {corpus}/meters.txt", file=sys.stderr)
        return 1

    from configfileparser import FRAME_RATE, METER
    from peppymeter import Peppymeter

    peppy = Peppymeter(standalone=True, timer_controlled_random_meter=False, quit_pygame_on_stop=False)
    # The constructor does not create the display: upstream's own entry point
    # calls this afterwards (peppymeter.py:289), and until it runs there is no
    # surface for either engine to draw on.
    peppy.init_display()
    util = peppy.util

    spectrum_state = SpectrumState()
    spectrum_state.util = util

    # One spectrum for the whole run, built against whichever skin starts.
    first = peppy.util.meter_config[METER]
    if first not in skins:
        first = next(iter(skins))
    wanted = spectrum_for(skins[first])
    if wanted is not None:
        name, width, height = wanted
        from spectrumutil import SpectrumUtil

        # What PeppySpectrum expects of a util object, which PeppyMeter's does
        # not carry: the shared surface and an image helper.
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
        spectrum_state.spectrum = spectrum
        spectrum_state.active = True

    rotation = Rotation(peppy, skins, spectrum_state)
    rotation.current = first
    peppy.util.meter_config[METER] = first
    rotation.prepare_next()
    print(f"peppy: {len(skins)} skins, starting on {first}")

    track = current_track()
    # Polled rather than watched: at a tenth of a second the check is a stat
    # and a small read, and it costs nothing to be a little late to a skin.
    poll_every = max(1, int(peppy.util.meter_config[FRAME_RATE] / 10))
    frames = 0

    def per_frame() -> None:
        nonlocal track, frames
        frames += 1
        if frames % poll_every == 0:
            playing = current_track()
            if playing is not None and playing != track:
                track = playing
                rotation.switch()

        if not spectrum_state.active:
            return
        spectrum = spectrum_state.spectrum
        # draw(), not dirty_draw_update(): that one updates the display from
        # whatever thread calls it, which is what broke under Wayland.
        if not (spectrum.components and spectrum.components[0].content is not None):
            return
        clip = util.pygame_screen.get_clip()
        util.pygame_screen.set_clip(util.screen_rect)
        for rect in [r.copy() for r in getattr(spectrum, "_dirty_rects", []) if r]:
            spectrum.draw_area(rect)
        spectrum._dirty_rects = []
        spectrum.draw()
        util.pygame_screen.set_clip(clip)
        # PeppyMeter updates only the meter's own dirty areas, and this hook
        # runs after that update - so the spectrum has to present its own
        # region or it is drawn and never shown.
        rects = [r for r in getattr(spectrum, "_dirty_rects", []) if r]
        pygame.display.update(rects or [util.screen_rect])

    peppy.dependent = per_frame
    peppy.start_display_output()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
