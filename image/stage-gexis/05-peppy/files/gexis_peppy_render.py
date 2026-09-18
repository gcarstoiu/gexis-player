# SPDX-License-Identifier: GPL-3.0-or-later
"""Draws the track's metadata onto the Peppy screen (Phase 5 criterion 7).

Neither vendored engine draws any of this: every `playinfo.*`, `albumart.*`
and `time.remaining.*` key belongs to the Volumio wrapper we deliberately did
not vendor (ADR-0026). This is our own layer over the skins' own geometry.

**Criterion 7 is the rule here, not a test of it**: a field we have nothing
for is not drawn, and its area is left as the skin's background. Phase 8's
enrichment will fill some gaps later; where it finds nothing, blank is right
(George, 2026-09-16).

Fonts are the image's DejaVu, not the wrapper's PeppyFont and seven-segment
faces: those are third-party files with their own terms, and vendoring them
is a decision of its own rather than a side effect of this.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.request
from pathlib import Path

import pygame

logger = logging.getLogger("peppy.render")

METADATA_PATH = Path("/run/gexis/nowplaying.json")
FONT_DIR = Path(__file__).with_name("fonts")
FONTS = {
    "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "light": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    # The skins place remaining time for a seven-segment face: DSEG7 Classic
    # Italic, the wrapper's own "digi" font. Ours is upstream's OFL-1.1 release,
    # measured identical to the wrapper's copy at the skins' sizes.
    "digi": str(FONT_DIR / "DSEG7Classic-Italic.ttf"),
}
#: The wrapper's layout constants, which the skins were authored against
#: (volumio_basic.py): a box left without a width runs to this margin, or to
#: 60 % of the screen when the skin centres its text.
RIGHT_MARGIN = 20
CENTRED_BOX_SHARE = 0.6
#: The wrapper turns remaining time red for the last ten seconds.
FINAL_SECONDS = 10
FINAL_SECONDS_COLOUR = (242, 0, 0)
#: The renderer's mark, from the UI's own assets (copied into the stage;
#: test_peppy_render checks they have not drifted from ui/src/assets).
ICON_DIR = Path(__file__).with_name("icons")
#: The mark alone, no name beside it (George, 2026-09-18, reversing his own
#: 2026-09-16 call). The name was the only thing drawn outside the square the
#: skin reserves, with no bounds check: on 7 of the 71 Gelo5 skins "Bluetooth"
#: ran off the 1280px screen - by 291px on Kenwood Rev - and on others it
#: crossed the skin's own controls and text. Fitting the mark inside
#: `playinfo.type.*` keeps every pixel inside space the skin author reserved.
BADGES = {
    "spotify": ("icon-spotify.png", None),
    "bluetooth": ("icon-bluetooth.png", None),
    # Lyrion's mark is a single-colour figure the UI tints with its LMS accent
    # (--accent-lms); it is drawn the same way here.
    "lms": ("icon-lyrion.svg", (126, 214, 188)),
}
ARTWORK_TIMEOUT_S = 5


def read_metadata(path: Path = METADATA_PATH) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def parse_point(value: str | None) -> tuple[int, int, str] | None:
    """`x,y` or `x,y,weight` — the skins use both spellings."""
    if not value:
        return None
    parts = [part.strip() for part in value.split(",")]
    try:
        return int(parts[0]), int(parts[1]), (parts[2] if len(parts) > 2 else "regular")
    except (IndexError, ValueError):
        return None


def parse_colour(value: str | None, fallback=(255, 255, 255)) -> tuple[int, int, int]:
    if not value:
        return fallback
    try:
        red, green, blue = (int(part) for part in value.split(",")[:3])
    except ValueError:
        return fallback
    return red, green, blue


def parse_size(value: str | None) -> tuple[int, int] | None:
    point = parse_point(value)
    return (point[0], point[1]) if point else None


class MetadataLayer:
    def __init__(self, screen: pygame.Surface, corpus: Path, icon_dir: Path = ICON_DIR) -> None:
        self._screen = screen
        self._corpus = corpus
        self._icon_dir = icon_dir
        self._badges: dict[tuple, pygame.Surface | None] = {}
        self._skin: dict[str, str] = {}
        self._background: pygame.Surface | None = None
        self._painted: list[pygame.Rect] = []
        self._fonts: dict[tuple[str, int], pygame.font.Font] = {}
        # Keyed on the skin's dimension as well as the URL: the same track
        # across a skin change needs the art rescaled, and reusing the old
        # surface drew it at the previous skin's size (found on the panel).
        self._artwork_key: tuple | None = None
        self._artwork: pygame.Surface | None = None
        self._artwork_source: pygame.Surface | None = None
        self._artwork_url: str | None = None
        self._last_drawn: tuple | None = None

    # ---- skin ----------------------------------------------------------

    def set_skin(self, skin: dict[str, str]) -> None:
        """A clean copy of the skin's own background, so a field that
        disappears can be erased back to it rather than smeared."""
        self._skin = skin
        self._painted = []
        self._last_drawn = None
        self._background = None
        name = skin.get("screen.bgr")
        if not name:
            return
        path = self._corpus / name
        try:
            image = pygame.image.load(str(path)).convert()
        except (pygame.error, OSError) as exc:
            logger.warning("render: no background %s: %s", path, exc)
            return
        if image.get_size() != self._screen.get_size():
            image = pygame.transform.smoothscale(image, self._screen.get_size())
        self._background = image

    def font(self, weight: str, size: int) -> pygame.font.Font:
        key = (weight, size)
        if key not in self._fonts:
            try:
                self._fonts[key] = pygame.font.Font(FONTS.get(weight, FONTS["regular"]), size)
            except (OSError, FileNotFoundError, pygame.error) as exc:
                logger.warning("render: font %s unavailable (%s), using regular", weight, exc)
                self._fonts[key] = pygame.font.Font(FONTS["regular"], size)
        return self._fonts[key]

    # ---- drawing -------------------------------------------------------

    def draw(self, metadata: dict) -> list[pygame.Rect]:
        """Returns the rectangles that changed, for the caller to present."""
        if self._background is None:
            return []
        fields = self._fields(metadata)
        fingerprint = (fields, metadata.get("source"), metadata.get("artwork"))
        if fingerprint == self._last_drawn:
            return []
        self._last_drawn = fingerprint

        dirty = list(self._painted)
        for rect in self._painted:
            self._screen.blit(self._background, rect, rect)
        self._painted = []

        # Artwork first, text last: some skins deliberately place the text
        # over the artwork (dash-spectrum puts title, artist and album inside
        # its 770x770 well), and drawing the art second hid it.
        for rect in (
            self._artwork_rect(metadata.get("artwork")),
            self._badge_rect(metadata.get("source")),
        ):
            if rect is not None:
                self._painted.append(rect)
                dirty.append(rect)

        for text, point, colour, size, maxwidth in fields:
            if not text:
                continue  # criterion 7: nothing for this field, nothing drawn
            rect = self._text(text, point, colour, size, maxwidth)
            if rect is not None:
                self._painted.append(rect)
                dirty.append(rect)

        return dirty

    def _fields(self, metadata: dict) -> tuple:
        skin = self._skin
        colour = parse_colour(skin.get("font.color"))
        maxwidth = int(skin.get("playinfo.maxwidth", 0) or 0)
        sizes = {
            weight: int(skin.get(f"font.size.{weight}", 20) or 20)
            for weight in ("regular", "bold", "light", "digi")
        }

        centred = skin.get("playinfo.center", skin.get("playinfo.text.center", "")).strip().lower() == "true"
        screen_width = self._screen.get_width()

        def box_width(point, own_width: int) -> int:
            # get_box_width() in the wrapper: the field's own width, then the
            # skin's global one, then an automatic box.
            if own_width:
                return own_width
            if maxwidth:
                return maxwidth
            if centred:
                return int(screen_width * CENTRED_BOX_SHARE)
            return max(0, screen_width - point[0] - RIGHT_MARGIN)

        def field(key: str, text: str | None, colour_key: str | None = None, width_key: str | None = None,
                  weight: str | None = None, override_colour=None):
            point = parse_point(skin.get(key))
            if point is None:
                return None
            if weight is not None:
                point = (point[0], point[1], weight)
            own_width = int(skin.get(width_key, 0) or 0) if width_key else 0
            return (
                text,
                point,
                override_colour or (parse_colour(skin.get(colour_key), colour) if colour_key else colour),
                sizes.get(point[2], sizes["regular"]),
                box_width(point, own_width) if width_key else 0,
            )

        entries = [
            field("playinfo.title.pos", metadata.get("title"), "playinfo.title.color", "playinfo.title.maxwidth"),
            field("playinfo.artist.pos", metadata.get("artist"), "playinfo.artist.color", "playinfo.artist.maxwidth"),
            field("playinfo.album.pos", metadata.get("album"), "playinfo.album.color", "playinfo.album.maxwidth"),
            # Not a text box: drawn top-left at the position in the digi face,
            # like the wrapper, so it lines up with the label the skin paints.
            field(
                "time.remaining.pos",
                remaining_time(metadata),
                "time.remaining.color",
                weight="digi",
                override_colour=FINAL_SECONDS_COLOUR if 0 < remaining_seconds(metadata, -1) <= FINAL_SECONDS else None,
            ),
            # The source is a badge, not text: see _badge_rect.
            # playinfo.samplerate.pos is never filled: no sample rate and no
            # codec renders anywhere (ADR-0036). The skins keep the position;
            # we keep it empty, which is this criterion's own rule.
        ]
        return tuple(entry for entry in entries if entry is not None)

    def _text(self, text, point, colour, size, maxwidth) -> pygame.Rect | None:
        font = self.font(point[2], size)
        surface = font.render(str(text), True, colour)
        if maxwidth and surface.get_width() > maxwidth:
            trimmed = str(text)
            while trimmed and font.size(trimmed + "…")[0] > maxwidth:
                trimmed = trimmed[:-1]
            surface = font.render(trimmed + "…", True, colour)
        x, y = point[0], point[1]
        centred = self._skin.get("playinfo.center", self._skin.get("playinfo.text.center", "")).strip().lower() == "true"
        if centred and maxwidth:
            # Centred *inside the box that starts at the position*, as the
            # wrapper does - not around the position, which slid text left by
            # half its width and onto the artwork (George, 2026-09-16).
            x += (maxwidth - surface.get_width()) // 2
        self._screen.blit(surface, (x, y))
        return pygame.Rect(x, y, surface.get_width(), surface.get_height())

    def _badge_rect(self, source: str | None) -> pygame.Rect | None:
        """The renderer's mark, fitted inside the square the skin reserves for
        it (`playinfo.type.pos`, `playinfo.type.dimension`)."""
        position = parse_size(self._skin.get("playinfo.type.pos"))
        if position is None or source not in BADGES:
            return None
        box = parse_size(self._skin.get("playinfo.type.dimension")) or (50, 50)
        badge = self._badge(source, box)
        if badge is None:
            return None
        x = position[0] + (box[0] - badge.get_width()) // 2
        y = position[1] + (box[1] - badge.get_height()) // 2
        self._screen.blit(badge, (x, y))
        return pygame.Rect(x, y, badge.get_width(), badge.get_height())

    def _badge(self, source: str, box: tuple[int, int]) -> pygame.Surface | None:
        key = (source, box)
        if key not in self._badges:
            filename, tint = BADGES[source]
            try:
                image = pygame.image.load(str(self._icon_dir / filename)).convert_alpha()
            except (pygame.error, OSError) as exc:
                logger.warning("render: no badge for %s: %s", source, exc)
                self._badges[key] = None
                return None
            scale = min(box[0] / image.get_width(), box[1] / image.get_height())
            size = (max(1, round(image.get_width() * scale)), max(1, round(image.get_height() * scale)))
            image = pygame.transform.smoothscale(image, size)
            if tint is not None:
                # Keep the shape, replace the colour: raise every pixel to
                # white, then multiply by the accent.
                image.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_MAX)
                image.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self._badges[key] = image
        return self._badges[key]

    def _artwork_rect(self, url: str | None) -> pygame.Rect | None:
        position = parse_size(self._skin.get("albumart.pos"))
        dimension = parse_size(self._skin.get("albumart.dimension"))
        if position is None or dimension is None or not url:
            return None  # Bluetooth never has artwork; the well stays as the skin drew it
        if url != self._artwork_url:
            # One network read per track, however many skins it is shown on.
            self._artwork_url = url
            self._artwork_source = self._fetch(url)
            self._artwork_key = None
        if self._artwork_source is None:
            return None
        if self._artwork_key != (url, dimension):
            self._artwork = pygame.transform.smoothscale(self._artwork_source, dimension)
            self._artwork_key = (url, dimension)
        self._screen.blit(self._artwork, position)
        return pygame.Rect(position, self._artwork.get_size())

    @staticmethod
    def _fetch(url: str) -> pygame.Surface | None:
        """Artwork comes from the renderer's own server (LMS, Spotify's CDN),
        so this is a network read on a screen that must not stall: one short
        timeout, and failure means no artwork rather than no screen."""
        try:
            with urllib.request.urlopen(url, timeout=ARTWORK_TIMEOUT_S) as response:
                data = response.read()
            import io

            return pygame.image.load(io.BytesIO(data)).convert()
        except Exception as exc:  # urllib raises a wide family; none is fatal here
            logger.info("render: no artwork from %s: %s", url, exc)
            return None


def remaining_seconds(metadata: dict, default: int | None = None) -> int | None:
    """Advanced from the last write, because position only arrives when the
    renderer reports one - the same interpolation the UI does."""
    position, duration = metadata.get("position"), metadata.get("duration")
    if position is None or duration is None:
        return default  # a renderer that publishes neither
    if metadata.get("transport") == "playing":
        position += max(0.0, time.time() - metadata.get("written_at", time.time()))
    return max(0, int(duration - position))


def remaining_time(metadata: dict) -> str | None:
    """`MM:SS`, zero-padded and without a minus sign: the wrapper's format,
    which the skins' "Remaining time" labels were laid out beside."""
    remaining = remaining_seconds(metadata)
    if remaining is None:
        return None
    return f"{remaining // 60:02d}:{remaining % 60:02d}"
