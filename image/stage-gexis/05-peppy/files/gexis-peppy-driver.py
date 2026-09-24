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
import json
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

#: How many bands peppyalsa puts in the spectrum pipe
#: ([ADR-0011](../../../../docs/decisions/0011-meter-data-three-transports.md),
#: `spectrum_size` in `/etc/alsa/conf.d/output.conf`). The cap on how many
#: bars a skin may draw: more bars than measurements would invent data, and
#: fewer is only ever the skin's own artwork running out of room.
SPECTRUM_BANDS = 30


def meter_sections(path: Path) -> dict[str, dict[str, str]]:
    """The skin file, read with the same tolerance the engines use: unknown
    keys are data, not errors. `make skins` is where a bad pack is rejected."""
    parser = configparser.ConfigParser(strict=False)
    parser.optionxform = str
    parser.read(path)
    return {name: dict(parser[name]) for name in parser.sections()}


#: What the daemon publishes and this reads (ADR-0051 §1). Polled on the
#: same hook as the metadata: a stat, and a read only when it has moved.
SELECTION_PATH = Path("/run/gexis/visualisation.json")

METERS, SPECTRUM, BOTH = "meters", "spectrum", "both"

#: The `skin_corpus` words and the kinds each one draws from. The same table
#: as `gexis_core.skins.CORPUS`; the two processes share no code, so they
#: share the words instead.
ALL = "All"
CORPUS = {
    "VU meters": (METERS,),
    "Spectrum": (SPECTRUM,),
    "VU meters + spectrum": (BOTH,),
    ALL: (METERS, SPECTRUM, BOTH),
    # Understood, for a selection written before the 2026-09-22 rename.
    "Random": (METERS, SPECTRUM, BOTH),
}


def kind_of(skin: dict[str, str]) -> str:
    """What a skin shows, from what it declares - never from which directory
    it lives in (ADR-0019 as amended). An absent `spectrum.visible` means no
    spectrum; an absent `meter.visible` means a meter."""
    spectrum = skin.get("spectrum.visible", "False").strip().lower() == "true"
    if not spectrum:
        return METERS
    return BOTH if skin.get("meter.visible", "True").strip().lower() != "false" else SPECTRUM


class Selection:
    """The three settings, as the daemon last published them.

    A missing or unreadable file leaves what we have: the settings database
    is the record and this is a projection of it, so a screen drawing the
    previous skin is the right answer to a file that is not there yet.
    """

    def __init__(self, path: Path = SELECTION_PATH) -> None:
        self.path = path
        self.corpus = ALL
        self.skin: str | None = None
        self.rotate = True
        self._stamp: int | None = None

    def reload(self) -> bool:
        """True when something changed, so the caller can act on it."""
        try:
            stamp = self.path.stat().st_mtime_ns
        except OSError:
            return False
        if stamp == self._stamp:
            return False
        self._stamp = stamp
        try:
            data = json.loads(self.path.read_text())
        except (OSError, ValueError) as exc:
            print(f"peppy: {self.path} unreadable: {exc}", file=sys.stderr)
            return False
        was = (self.corpus, self.skin, self.rotate)
        self.corpus = str(data.get("corpus") or ALL)
        skin = data.get("skin")
        self.skin = str(skin) if skin else None
        self.rotate = data.get("rotate") is not False
        return was != (self.corpus, self.skin, self.rotate)

    def pool(self, skins: dict[str, dict[str, str]]) -> list[str]:
        """The names this corpus offers. An empty pool is not a corpus: a
        word we do not know, or one that selects nothing on this pack, falls
        back to everything rather than to a blank screen."""
        wanted = CORPUS.get(self.corpus) or CORPUS[ALL]
        chosen = [name for name, skin in skins.items() if kind_of(skin) in wanted]
        return chosen or list(skins)


def load_corpus(base_folder: Path, meter_folder: str) -> tuple[dict, dict]:
    """**Every skin the device has**, and where each one lives.

    Four directories on this image, two per pack: the engine is configured
    with one of them - `gelo5/templates`, which is 71 skins and not one
    spectrum - so reading only what the engine reads would leave a corpus
    word naming a spectrum with nothing to offer (ADR-0051 §2).

    The configured pack comes first, so the skin a fresh device starts on is
    the one it has always started on; the rest follow in name order. A name
    two packs share resolves to the first, which is the one that would be
    selected.
    """
    pack = base_folder.parent
    root = pack.parent
    others = sorted(p for p in root.iterdir() if p.is_dir() and p != pack) if root.is_dir() else []
    skins: dict[str, dict[str, str]] = {}
    homes: dict[str, Path] = {}
    for where in [pack, *others]:
        for templates in ("templates", "templates_spectrum"):
            directory = where / templates / meter_folder
            path = directory / "meters.txt"
            if not path.is_file():
                continue
            for name, options in meter_sections(path).items():
                if name in skins:
                    continue
                skins[name] = options
                homes[name] = directory
    return skins, homes


def adopt_sections(meter_config, directory: Path) -> list[str]:
    """Put a directory's sections into the engine's parsed config, in the
    engine's own shapes, and answer which names were added.

    The engine parses exactly one `meters.txt` at start. Its two section
    builders take a `ConfigParser` and return a dictionary, and reach for
    `self` only for helpers - so the second directory is parsed by the code
    that parsed the first, rather than by a second implementation of it that
    would drift the first time upstream added a key.

    A section that will not parse is skipped with a line in the log: one
    unbuildable skin is not a reason to lose the other eighty-three.
    """
    from configfileparser import ConfigFileParser, METER_TYPE, TYPE_LINEAR

    parser = configparser.ConfigParser(strict=False)
    parser.read(directory / "meters.txt")
    builder = ConfigFileParser()
    added: list[str] = []
    for name in parser.sections():
        if name in meter_config:
            continue
        try:
            meter_type = parser.get(name, METER_TYPE)
            meter_config[name] = (
                builder.get_linear_section(parser, name, meter_type)
                if meter_type == TYPE_LINEAR
                else builder.get_circular_section(parser, name, meter_type)
            )
        except Exception as exc:  # noqa: BLE001 - one skin, not the corpus
            print(f"peppy: {name} in {directory} will not parse: {exc}", file=sys.stderr)
            continue
        added.append(name)
    return added


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


#: The bar count, once the corpus has been looked at: see `spectrum_bars`.
_BARS: int | None = None


def spectrum_bars(base_folder: Path | None, folder: str, bands: int) -> int | None:
    """**How many bars every spectrum skin draws.**

    The engine draws `config[SIZE]` bars from the global `config.txt`. It was
    30 and no skin has room for 30: measured across both installed packs,
    their artwork holds 19 or 20 (Finding 049). What fits is arithmetic on
    the skin's own numbers - the width of its background picture, where the
    first bar starts, and how wide a bar and a gap are:

        room = (background width - 2*origin.x + bar.gap) // (bar.width + bar.gap)

    **`origin.x` twice, because the picture has a frame.** Filling to the
    picture's own right-hand edge puts the last bar on the bezel: `Free`'s
    panel is 933px wide and its drawn interior ends 25px short of that, so
    the 22nd bar overhung by most of its width (George, 2026-09-23: *"the
    bars for spectrum are also out of the bounds of the space they should
    sit in, by half a bar in general for all skins"*). The inset is not in
    the config; `origin.x` is the author's own left-hand margin, and ending
    as far from the right edge as the bars begin from the left cannot
    overhang.

    **One number for the whole corpus, not one per skin**, and that is the
    part worth explaining. The engine reads `size` **once**, when the driver
    constructs it - a skin change re-points the section, the base folder and
    the screen size, but `config[SIZE]` keeps the value it started with. The
    meter relay, meanwhile, reads this same file and follows it
    ([ADR-0056](../../../../docs/decisions/0056-the-spectrum-frame-follows-its-reader.md)).
    So a per-skin count made the two disagree from the second skin onwards,
    and a FIFO has no message boundaries: the reader then takes its frames
    across record boundaries and every bar shows a different band each
    refresh. George saw it as flashing in the low bars, and the device's own
    log had it - *"drawing 20"* while the engine was still on 19.

    **The spread is one bar**, 19 against 20, so the minimum over the whole
    installed corpus costs nothing and removes the disagreement entirely:
    the number is written once and never changes while the engine runs.

    **The pipe is not touched.** peppyalsa keeps sending `bands` bands
    (ADR-0011); the count is capped at that, never the other way round.

    **The count comes down, never the bar width.** The bar is a picture the
    skin's author drew at a fixed size; narrowing it would scale their
    artwork.
    """
    global _BARS
    if _BARS is not None:
        return _BARS
    if base_folder is None or not folder:
        return None
    rooms = []
    # `base_folder` is `<root>/<pack>/templates_spectrum`, so two levels up is
    # the root every installed pack sits under. Every pack, not just the one
    # in use: the number has to hold for whatever the corpus rotates onto.
    root = base_folder.parent.parent
    for spectrum_txt in sorted(root.glob(f"*/templates*/{folder}/spectrum.txt")):
        parser = configparser.ConfigParser(strict=False)
        try:
            parser.read(spectrum_txt)
        except configparser.Error:
            continue
        for name in parser.sections():
            section = parser[name]
            try:
                width = int(section["bar.width"])
                gap = int(section["bar.gap"])
                origin = int(section["origin.x"])
                area = png_width(spectrum_txt.parent / section["bgr.filename"])
            except (KeyError, ValueError, OSError):
                continue
            if not area:
                continue
            room = (area - 2 * origin + gap) // (width + gap)
            if room > 0:
                rooms.append(room)
    if not rooms:
        return None
    _BARS = min(min(rooms), bands)
    print(
        f"peppy: {len(rooms)} spectrum sections hold {min(rooms)}-{max(rooms)} bars, "
        f"drawing {_BARS} everywhere",
        flush=True,
    )
    return _BARS


def png_width(path: Path) -> int | None:
    """A PNG's width, without pulling in an image library. The spectrum
    backgrounds are all PNG; anything else answers None and the skin keeps
    its own count."""
    try:
        header = path.read_bytes()[:24]
    except OSError:
        return None
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(header[16:20], "big")


def select_spectrum_section(name: str, base_folder: Path | None = None) -> None:
    """Point the spectrum engine's own config at one section. Rewritten in
    place: configparser fails hard on a duplicate key, and an appended one
    would stop the process starting.

    **`base_folder` is the pack's, not the build's** (ADR-0051 §2, amended
    2026-09-22). Each pack keeps its own `spectrum.txt`, and a section name
    only means something inside one of them - the stock pack's skins name
    `s.1`…`s.9`, which Gelo5 has never heard of. Leaving this pinned to one
    pack is what made the other pack's spectrum skins unusable, and that is
    what the corpus was narrowed for.
    """
    path = SPECTRUM_DIR / "config.txt"
    parser = configparser.ConfigParser()
    parser.read(path)
    parser["current"]["spectrum"] = name
    if base_folder is not None:
        parser["current"]["base.folder"] = str(base_folder)
    # The engine resolves its sections under `base.folder/spectrum.folder`,
    # so the bar count is read from the same place it will read the rest.
    # The cap is what the *pipe* carries, which is the band count peppyalsa
    # was configured with - never more bars than there are measurements.
    bars = spectrum_bars(
        base_folder, parser["current"].get("spectrum.folder", ""), SPECTRUM_BANDS
    )
    if bars:
        parser["current"]["size"] = str(bars)
    # The engine reads this file; the daemon never does. It is rewritten on
    # every skin change, which is why the image installs it writable by the
    # user the unit runs as.
    with path.open("w") as handle:
        parser.write(handle)


def spectrum_base(home: Path) -> Path:
    """Where the pack that owns `home` keeps its spectrum sections.

    `<root>/<pack>/<templates…>/<resolution>` -> `<root>/<pack>/templates_spectrum`,
    which is what the spectrum engine wants as its `base.folder`: it joins
    that with its own `spectrum.folder`.
    """
    return home.parent.parent / "templates_spectrum"


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


DAEMON_TOUCH_URL = os.environ.get("GEXIS_TOUCH_URL", "http://127.0.0.1:8090/touch")
TOUCH_EVENTS = {pygame.MOUSEBUTTONUP, getattr(pygame, "FINGERUP", pygame.MOUSEBUTTONUP)}


def report_touches_to_the_daemon() -> None:
    """A touch on the Peppy screen lands in this window, not in the UI, so
    the daemon never hears of it (George, 2026-09-16: "touching the peppy
    screen doesn't hide it").

    PeppyMeter's own loop reads the events and discards touches unless told
    to exit or stop drawing, and we want neither. So the event read itself is
    wrapped: every touch it returns is reported, and the loop sees the same
    events as before. The report runs on its own thread, because a slow or
    absent daemon must never stall a frame.
    """
    import threading
    import urllib.request

    original_get = pygame.event.get
    last = [0.0]

    def post() -> None:
        try:
            urllib.request.urlopen(
                urllib.request.Request(DAEMON_TOUCH_URL, method="POST"), timeout=2
            ).close()
        except Exception as exc:  # never fatal: the screen keeps drawing
            print(f"peppy: touch report failed: {exc}", file=sys.stderr)

    def get(*args, **kwargs):
        events = original_get(*args, **kwargs)
        if any(event.type in TOUCH_EVENTS for event in events):
            import time

            now = time.monotonic()
            if now - last[0] > 0.5:  # one report per tap, not per event
                last[0] = now
                threading.Thread(target=post, daemon=True).start()
        return events

    pygame.event.get = get


class Rotation:
    """Phase 5 criterion 5: a new skin per track, with the next one built
    before it is needed.

    Random without repeats until the pool is exhausted, which is what
    PeppyMeter's own random mode does — but driven by track changes rather
    than a timer, so the skin belongs to the track.

    **The pool is the selection's, not the corpus's** (ADR-0051): which
    skins it draws from is `skin_corpus`, and whether it draws a new one at
    all is `skin_rotate`.
    """

    def __init__(
        self,
        peppy,
        skins: dict[str, dict[str, str]],
        spectrum_state,
        layer=None,
        homes: dict[str, Path] | None = None,
        selection: Selection | None = None,
    ) -> None:
        self.peppy = peppy
        self.vumeter = peppy.meter
        self.skins = skins
        self.homes = homes or {}
        self.selection = selection or Selection()
        self.spectrum = spectrum_state
        self.layer = layer
        self.unseen: list[str] = []
        self.current: str | None = None
        self.prepared: tuple[str, object] | None = None
        #: False when the spectrum engine could not be built. A spectrum-only
        #: skin then draws **nothing at all** - `meter.visible = False` is
        #: honoured and there is no spectrum to take its place - which is a
        #: black screen the panel cannot be got back from (George, on the
        #: panel, 2026-09-22). Such a skin is not a choice, so it leaves the
        #: pool rather than reaching the glass.
        self.spectrum_ready = True

    def pool(self) -> list[str]:
        chosen = self.selection.pool(self.skins)
        if self.spectrum_ready:
            return chosen
        drawable = [n for n in chosen if kind_of(self.skins[n]) != SPECTRUM]
        if drawable:
            return drawable
        # The whole corpus word is unusable without a spectrum: anything that
        # draws beats a black screen.
        return [n for n, skin in self.skins.items() if kind_of(skin) != SPECTRUM] or chosen

    def pick(self) -> str:
        pool = self.pool()
        if not self.rotating:
            # Not rotating: the next skin is the chosen one, and preparing it
            # costs nothing because it is the one already on screen.
            return self.chosen() or self.current or pool[0]
        self.unseen = [name for name in self.unseen if name in pool]
        if not self.unseen:
            self.unseen = [name for name in pool if name != self.current] or list(pool)
        return self.unseen.pop(random.randrange(len(self.unseen)))

    @property
    def rotating(self) -> bool:
        return self.selection.rotate

    def chosen(self) -> str | None:
        """The skin the selection names, if this pack has it and the corpus
        still offers it. A name we do not have is not an error: the daemon
        and the driver can disagree for as long as it takes a settings write
        to reach the file."""
        name = self.selection.skin
        return name if name in self.pool() else None

    def follow_selection(self) -> None:
        """Apply a change the daemon published. Rotation off moves to the
        named skin; rotation on leaves the screen alone until the track
        changes, unless what is on it has fallen out of the corpus."""
        pool = self.pool()
        wanted = self.chosen() if not self.rotating else None
        if wanted is None and self.current in pool:
            self.prepared = None
            return
        if wanted is None:
            wanted = pool[0]
        if wanted == self.current:
            self.prepared = None
            return
        self.prepared = None
        self.switch(wanted)

    def prepare_next(self, name: str | None = None) -> None:
        """Build the next skin's meter now, so a track change costs no image
        loading. Done right after a switch, while the new skin is already on
        screen — the moment with the most slack, not the least."""
        name = name or self.pick()
        from configfileparser import BASE_PATH, METER
        from meterfactory import MeterFactory

        # Built through the factory, not `vumeter.get_meter()`: that returns
        # the *existing* meter unless the engine is in its own random mode, so
        # asking it for the next skin hands back the current one - which drew
        # each new skin with the previous skin's needles, and then no needles
        # at all (George saw it on the panel, 2026-09-16).
        vumeter = self.vumeter
        config = self.peppy.util.meter_config
        was, config[METER] = config[METER], name
        # Every image this skin names is loaded here, from `base.path` +
        # `meter.folder` - so a skin that lives in the pack's other template
        # directory is built by pointing `base.path` at it and putting it
        # back afterwards, exactly as `meter` is swapped (ADR-0051 §2).
        was_base = config.get(BASE_PATH)
        home = self.homes.get(name)
        if home is not None:
            # `base.path` is the directory *above* the resolution folder:
            # the engine joins it with `meter.folder` and the file name.
            config[BASE_PATH] = str(home.parent)
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
            if was_base is not None:
                config[BASE_PATH] = was_base
        self.prepared = (name, meter)

    def switch(self, to: str | None = None) -> None:
        if to is not None and (self.prepared is None or self.prepared[0] != to):
            self.prepare_next(to)
        if self.prepared is None:
            self.prepare_next()
        name, meter = self.prepared
        self.prepared = None

        from configfileparser import BASE_PATH, METER

        if self.vumeter.meter is not None:
            self.vumeter.meter.stop()
        self.peppy.util.meter_config[METER] = name
        # Left pointing at the skin on screen, so anything the engine loads
        # later finds the right directory.
        home = self.homes.get(name)
        if home is not None:
            self.peppy.util.meter_config[BASE_PATH] = str(home.parent)
        self.vumeter.meter = meter
        meter.set_volume(self.vumeter.current_volume)
        meter.start()
        self.current = name
        print(f"peppy: skin -> {name}")
        skin = self.skins.get(name, {})
        self.spectrum.follow(skin, self.homes.get(name))
        if self.layer is not None:
            self.layer.set_skin(skin, self.homes.get(name))
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

    def follow(self, skin: dict[str, str], home: Path | None = None) -> None:
        wanted = spectrum_for(skin)
        if wanted is None or self.spectrum is None:
            self.active = False
            return
        name, width, height = wanted
        from spectrumconfigparser import (
            AVAILABLE_SPECTRUM_NAMES,
            BASE_FOLDER,
            SCREEN_HEIGHT,
            SCREEN_WIDTH,
            SPECTRUM_X,
            SPECTRUM_Y,
        )

        here = Path.cwd()
        os.chdir(SPECTRUM_DIR)
        try:
            select_spectrum_section(name, spectrum_base(home) if home else None)
            spectrum = self.spectrum
            spectrum.config[SCREEN_WIDTH] = width
            spectrum.config[SCREEN_HEIGHT] = height
            spectrum.config[AVAILABLE_SPECTRUM_NAMES] = [name]
            # **In memory as well as in the file.** The parser read
            # `base.folder` once, at startup, and `get_spectrum_configs`
            # answers from what it holds - so rewriting only the file left
            # the stock pack's `s.3` "missing from the corpus" while the
            # engine looked for it in Gelo5's.
            if home is not None:
                spectrum.config[BASE_FOLDER] = str(spectrum_base(home))
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
        except Exception as exc:  # noqa: BLE001 - one skin, not the screen
            print(f"peppy: spectrum {name!r} would not load: {exc}", file=sys.stderr)
            self.active = False
        finally:
            os.chdir(here)


def hold_the_last_frame(data_source) -> None:
    """**"No frame this tick" is not "silence".**

    The engine's `get_latest_pipe_data` starts each call with `[0, 0, 0, 0]`
    and overwrites it only if a read returns bytes - so a poll that finds the
    pipe empty reports *zero level*. It polls every 43 ms while the daemon
    writes every 33, and measured on the device **40% of its reads find
    nothing**: 47 of 117 over five seconds, with music playing. Each of those
    zeros then goes into a four-deep smoothing buffer, so the needle spends
    its life averaging real levels with invented silence - it was reading
    21, 20, 12, 12, 19, 13, 12, 19 for a steady passage. That is the shake
    George saw, on meters and spectrum alike.

    This replaces the drain with one that holds the last frame when the pipe
    has nothing new, which is what `gexis_core.meters.FifoSource` already
    does on our side of the same pipes and for the same reason. A *real*
    silent frame still reads as silence: it arrives as bytes.

    Patched on the instance, not in the engine: the same composition point as
    the touch reporter below, and ADR-0026 keeps the vendored engines
    unmodified.
    """
    last = [0, 0, 0, 0]

    def latest():
        nonlocal last
        frame = None
        while True:
            try:
                data = os.read(data_source.pipe, 4)
            except (BlockingIOError, OSError):
                break
            if len(data) != 4:
                break
            frame = data
        if frame is not None:
            last = [frame[0], frame[1], frame[2], frame[3]]
        return last

    if getattr(data_source, "pipe", None) is not None:
        data_source.get_latest_pipe_data = latest


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
    sys.path.insert(0, str(PEPPY))  # our own render module lives beside the engines
    sys.path.insert(0, str(METER_DIR))
    sys.path.insert(0, str(SPECTRUM_DIR))

    os.chdir(METER_DIR)  # PeppyMeter reads ./config.txt

    # Read the same file PeppyMeter is about to read: its parsed config keeps
    # base.folder only as a local, so there is nothing to ask it for.
    meter_config = configparser.ConfigParser()
    meter_config.read(METER_DIR / "config.txt")
    current = meter_config["current"]
    base_folder = Path(current.get("base.folder", ""))
    meter_folder = current.get("meter.folder", "")
    corpus = base_folder / meter_folder
    # Every pack, not the one directory the engine is configured with
    # (ADR-0051 §2).
    skins, homes = load_corpus(base_folder, meter_folder)
    if not skins:
        print(f"ERROR: no skins in {corpus}/meters.txt", file=sys.stderr)
        return 1

    from configfileparser import BASE_PATH, FRAME_RATE, METER
    from peppymeter import Peppymeter

    peppy = Peppymeter(standalone=True, timer_controlled_random_meter=False, quit_pygame_on_stop=False)
    # The constructor does not create the display: upstream's own entry point
    # calls this afterwards (peppymeter.py:289), and until it runs there is no
    # surface for either engine to draw on.
    peppy.init_display()
    util = peppy.util

    # The engine parsed its own directory; the other one is adopted into the
    # same config so the factory can build from either.
    for directory in {home for home in homes.values()} - {corpus}:
        adopted = adopt_sections(util.meter_config, directory)
        print(f"peppy: {len(adopted)} more skins from {directory}")

    spectrum_state = SpectrumState()
    spectrum_state.util = util

    selection = Selection()
    selection.reload()

    # Which skin is on screen first: the chosen one when the skin is not
    # rotating, otherwise anything the corpus offers.
    pool = selection.pool(skins)
    first = selection.skin if (not selection.rotate and selection.skin in pool) else None
    if first is None:
        first = peppy.util.meter_config[METER]
    if first not in pool:
        first = pool[0]

    # **One spectrum for the whole run, whatever the first skin is**
    # (ADR-0051 §3). It used to be built only when the starting skin had one,
    # which was safe while the corpus was a single spectrum directory and is
    # not once meters and spectra share a pool: the skin chosen an hour later
    # would have had no engine to draw with. Bootstrapped against the first
    # section the corpus offers and re-pointed by `follow`.
    #
    # **And it must not be able to take the screen with it.** This is the
    # only place that writes to the spectrum engine's config, and when that
    # file was not writable by the user the unit runs as, the exception
    # killed `main()` *after* the display existed - leaving a black pygame
    # window with no loop behind it, swallowing every touch (George, on the
    # panel, 2026-09-22). A device with no spectrum is a device with meters.
    bootstrap = spectrum_for(skins[first]) or next(
        (found for name in pool if (found := spectrum_for(skins[name])) is not None), None
    )
    spectrum_home = homes.get(first)
    if bootstrap is not None and spectrum_for(skins[first]) is None:
        # Bootstrapping against another skin's section: point the config at
        # *that* skin's pack, not at the one we happen to start on.
        spectrum_home = next(
            (homes.get(n) for n in pool if spectrum_for(skins[n]) == bootstrap), spectrum_home
        )
    wanted = None
    try:
        wanted = bootstrap
        if wanted is not None:
            name, width, height = wanted
            from spectrumutil import SpectrumUtil

            # What PeppySpectrum expects of a util object, which PeppyMeter's
            # does not carry: the shared surface and an image helper.
            util.spectrum_size = (width, height, name)
            util.pygame_screen = util.PYGAME_SCREEN
            util.image_util = SpectrumUtil()

            select_spectrum_section(name, spectrum_base(spectrum_home) if spectrum_home else None)
            os.chdir(SPECTRUM_DIR)  # its config parser reads ./config.txt too
            install_screensaver_shim(name, width, height)
            # `spectrum`, not `spectrum.spectrum`: the engine's own directory
            # is on sys.path, so its modules are top-level. The Volumio
            # wrapper's spelling reflects its own nesting, not ours.
            from spectrum import Spectrum
            from spectrumconfigparser import (
                AVAILABLE_SPECTRUM_NAMES,
                SCREEN_HEIGHT,
                SCREEN_WIDTH,
            )

            spectrum = Spectrum(util, standalone=False)
            spectrum.config[SCREEN_WIDTH] = width
            spectrum.config[SCREEN_HEIGHT] = height
            spectrum.config[AVAILABLE_SPECTRUM_NAMES] = [name]
            spectrum.spectrum_configs = spectrum.config_parser.get_spectrum_configs()
            spectrum.init_spectrums()
            # Setting callback_start takes the place of the engine's own
            # refresh thread (spectrum.py:371): that thread calls
            # pygame.display.update() itself, and a second thread touching the
            # surface fails outright under Wayland - "Unable to make EGL
            # context current", because the GL context belongs to the thread
            # that made it. PeppyMeter's loop does the drawing instead,
            # through `dependent` below.
            spectrum.callback_start = lambda _spectrum: None
            spectrum.start()
            spectrum_state.spectrum = spectrum
            # Only if the skin on screen is the one it was built against;
            # otherwise it waits, built, for the first skin that wants it.
            spectrum_state.active = spectrum_for(skins[first]) is not None
    except Exception as exc:  # noqa: BLE001 - the meter is the screen
        print(f"peppy: no spectrum engine ({exc!r}); meters only", file=sys.stderr)
        spectrum_state.spectrum = None
        spectrum_state.active = False
        wanted = None
    finally:
        os.chdir(METER_DIR)

    from gexis_peppy_render import MetadataLayer, read_metadata

    rotation = Rotation(peppy, skins, spectrum_state, None, homes, selection)
    rotation.spectrum_ready = spectrum_state.spectrum is not None
    # Settled *after* the spectrum engine is known: without one, a
    # spectrum-only skin draws nothing at all, so it is not in the pool and
    # cannot be the skin this starts on.
    startable = rotation.pool()
    if first not in startable:
        first = startable[0]

    layer = MetadataLayer(util.PYGAME_SCREEN, homes.get(first, corpus))
    rotation.layer = layer
    rotation.current = first
    peppy.util.meter_config[METER] = first
    if first in homes:
        peppy.util.meter_config[BASE_PATH] = str(homes[first].parent)
    # **The engine's own random mode is off, because the driver owns the
    # choice** (ADR-0051). `config.txt` says `meter = random`, which makes
    # `VUMeter.get_meter()` pick a skin of its own at `start()` and overwrite
    # `meter_config[METER]` on the way past - so the first frame drew
    # something nobody had asked for and the picker's answer only took effect
    # at the next track change. George, 2026-09-22, having chosen McIntosh
    # and been given an Electrocompaniet.
    peppy.meter.random_meter = False
    peppy.meter.list_meter = False
    layer.set_skin(skins[first], homes.get(first))
    rotation.prepare_next()
    print(
        f"peppy: {len(skins)} skins, {len(pool)} in {selection.corpus!r}, "
        f"starting on {first}, rotation {'on' if selection.rotate else 'off'}"
    )

    track = current_track()
    # Polled rather than watched: at a tenth of a second the check is a stat
    # and a small read, and it costs nothing to be a little late to a skin.
    poll_every = max(1, int(peppy.util.meter_config[FRAME_RATE] / 10))
    frames = 0

    def per_frame() -> None:
        nonlocal track, frames
        frames += 1
        if frames % poll_every == 0:
            # The same poll carries both files: which track is playing, and
            # what the panel last asked for (ADR-0051 §1).
            if selection.reload():
                print(
                    f"peppy: selection -> {selection.corpus!r}, "
                    f"{selection.skin!r}, rotation {'on' if selection.rotate else 'off'}"
                )
                rotation.follow_selection()
            playing = current_track()
            if playing is not None and playing != track:
                track = playing
                if rotation.rotating:
                    rotation.switch()
            dirty = layer.draw(read_metadata())
            if dirty:
                pygame.display.update(dirty)

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

    hold_the_last_frame(peppy.meter.data_source)
    report_touches_to_the_daemon()
    peppy.dependent = per_frame
    peppy.start_display_output()
    return 0


def run() -> int:
    """**A window with no loop behind it is worse than no window.**

    pygame's display outlives `main()` - its threads keep the process up, so
    an exception after `init_display()` left a black surface on the panel
    that owned every touch and could not be dismissed (George, 2026-09-22).
    Anything that gets out of `main()` now takes the window with it, and
    systemd restarts a process that exited rather than nursing one that is
    only half alive.
    """
    try:
        return main()
    except Exception:
        import traceback

        traceback.print_exc()
        return 1
    finally:
        try:
            pygame.quit()
        except Exception:  # noqa: BLE001 - we are already on the way out
            pass


if __name__ == "__main__":
    raise SystemExit(run())
