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

#: **Where a plugin's mark lives** (ADR-0086). `BADGES` above is the three
#: built-ins, whose artwork is three different techniques the design owns - a
#: tinted figure and two images. Anything else brought its own glyph with its
#: manifest, and this is the path it was installed at.
#:
#: **The third place this had to be learned.** The panel's `SourceMark` and its
#: handoff screen each drew a plugin renderer as an empty space for the same
#: reason: a map of the three, and no fallback to the thing the plugin shipped.
#: Here it was a guard rather than a crash - `source not in BADGES` returned
#: None - so the visualiser simply had no badge and said nothing about it.
PLUGIN_MARKS = Path("/usr/share/gexis/plugins")

#: **Where a skin's badge slot really is**, for the skins whose declared
#: `playinfo.type` box sits off-centre in the slot they draw (George,
#: 2026-09-26: *"sometimes the logo is not centered on the allocated space"*).
#: Those boxes held a format icon with the sample rate beside it, and the
#: sample rate is never drawn here, so the badge sat at one end of an empty
#: slot. Measured from each skin's own artwork and reviewed tile by tile; a
#: skin absent from the file keeps its declared box, which is what every
#: other skin already centres correctly.
BADGE_SLOTS = Path(__file__).with_name("badge-slots.json")

#: **The badge fills 80% of its field**, leaving a tenth of it clear on every
#: side (George, 2026-09-26: *"it fits too snuggly vertically so it needs to be
#: slightly smaller ... Some small border should be left to the edges of the
#: field"* - for every renderer's mark, not only Plex's). The field is the
#: slot where one is measured, otherwise the box the skin declares.
BADGE_FILL = 0.8


def load_badge_slots(path: Path = BADGE_SLOTS) -> dict[str, tuple[int, int, int, int]]:
    try:
        raw = json.loads(path.read_text()).get("slots", {})
        return {name: tuple(int(v) for v in rect[:4]) for name, rect in raw.items()}
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        logger.warning("render: no badge slots from %s: %s", path, exc)
        return {}
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


def _float(value, default: float) -> float:
    try:
        return float(str(value).strip()) if value not in (None, "") else default
    except ValueError:
        return default


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


#: The edge's colour and how far it reaches, as a share of the mark's height.
EDGE_RGBA = (0, 0, 0, 170)
EDGE_SHARE = 0.05


def _with_edge(image: pygame.Surface) -> pygame.Surface:
    """`image` on a dark silhouette of itself grown by a few pixels."""
    reach = max(1, round(image.get_height() * EDGE_SHARE))
    w, h = image.get_size()
    silhouette = image.copy()
    # Black, and the mark's own alpha scaled by the edge's: transparent stays
    # transparent. (Raising alpha with BLEND_RGBA_MAX would paint the whole
    # square.)
    silhouette.fill(EDGE_RGBA, special_flags=pygame.BLEND_RGBA_MULT)
    out = pygame.Surface((w + 2 * reach, h + 2 * reach), pygame.SRCALPHA)
    for dx in range(-reach, reach + 1):
        for dy in range(-reach, reach + 1):
            if dx * dx + dy * dy <= reach * reach:
                out.blit(silhouette, (reach + dx, reach + dy))
    out.blit(image, (reach, reach))
    return out


#: **Below this height LMS's mark is the panel's four-bar reduction**, not the
#: ten-bar picture: the panel's `SourceMark` does the same below 40 px because
#: the ten thin bars antialias to a smear, and with the dark edge added they
#: became a dark smudge on the smaller skins (checked 2026-09-27 on
#: 101G5_Free S+M, gold, black-blue and emerald). **72, not 48**: rendered
#: side by side on a cream skin at 40-72 px, the ten bars only read as bars from
#: 72 px up; below that the edge swallows them.
LYRION_REDUCTION_BELOW = 72
#: The panel's own proportions (`SourceMark.svelte`): bar heights, width and gap.
LYRION_BARS = (0.5, 1.0, 0.72, 0.88)


def _lyrion_reduction(box: tuple[int, int], colour) -> pygame.Surface:
    """The four-bar mark, `box[1]` tall, with the dark edge, fitted in `box`."""
    size = max(8, box[1])
    bar = max(3, round(size * 0.15))
    gap = max(2, round(size * 0.11))
    width = 4 * bar + 3 * gap
    mark = pygame.Surface((width, size), pygame.SRCALPHA)
    for i, share in enumerate(LYRION_BARS):
        h = max(bar, round(size * share))
        rect = pygame.Rect(i * (bar + gap), (size - h) // 2, bar, h)
        pygame.draw.rect(mark, (*colour, 255), rect, border_radius=max(1, bar // 2))
    mark = _with_edge(mark)
    shrink = min(box[0] / mark.get_width(), box[1] / mark.get_height(), 1.0)
    if shrink < 1.0:
        mark = pygame.transform.smoothscale(
            mark, (max(1, round(mark.get_width() * shrink)), max(1, round(mark.get_height() * shrink))))
    return mark


class Ticker:
    """**A ticker skin's line, scrolling** (ADR-0097; upstream's
    `ScrollingLabel` in ticker mode, volumio_turntable.py:448-659).

    The line is rendered once with the skin's `end_spaces` after it, twice
    side by side, and a box-wide window slides across that strip at `speed`
    pixels a second - leftward for `ltr`, every shipped skin's direction, and
    rightward for `rtl` - wrapping seamlessly. A line that fits its box stands
    still (upstream draws three copies of it there, which reads as a bug)."""

    def __init__(self, speed: float, rightward: bool, end_spaces: int) -> None:
        self.speed = speed
        self.rightward = rightward
        self.end_spaces = end_spaces
        self.box: pygame.Rect | None = None
        self._key: tuple | None = None
        self._strip: pygame.Surface | None = None
        self._segment = 1
        self.scrolls = False
        self.offset = 0.0
        self._last: float | None = None
        self._shown = -1

    def show(self, font: pygame.font.Font, text: str, point, colour, width: int) -> pygame.Rect:
        key = (text, tuple(point), tuple(colour), width, id(font))
        if key == self._key and self.box is not None:
            return self.box
        self._key = key
        line = font.render(text, True, colour)
        self.box = pygame.Rect(point[0], point[1], width, line.get_height())
        self.scrolls = line.get_width() > width
        if self.scrolls:
            segment = font.render(text + " " * self.end_spaces, True, colour)
            self._segment = max(1, segment.get_width())
            self._strip = pygame.Surface((self._segment * 2, line.get_height()), pygame.SRCALPHA)
            self._strip.blit(segment, (0, 0))
            self._strip.blit(segment, (self._segment, 0))
        else:
            self._strip = line
        # Offset 0 is what `picture` draws first, so it counts as shown.
        self.offset, self._last, self._shown = 0.0, None, 0
        return self.box

    def picture(self) -> pygame.Surface:
        window = pygame.Surface(self.box.size, pygame.SRCALPHA)
        window.blit(self._strip, (-int(self.offset), 0))
        return window

    def advance(self, now: float) -> bool:
        """True when the window has moved by a whole pixel."""
        if not self.scrolls or self.box is None:
            return False
        if self._last is not None:
            step = self.speed * min(0.5, max(0.0, now - self._last))
            self.offset = (self.offset + (-step if self.rightward else step)) % self._segment
        self._last = now
        if int(self.offset) == self._shown:
            return False
        self._shown = int(self.offset)
        return True


class MetadataLayer:
    def __init__(self, screen: pygame.Surface, corpus: Path, icon_dir: Path = ICON_DIR) -> None:
        self._screen = screen
        self._corpus = corpus
        self._icon_dir = icon_dir
        self._badges: dict[tuple, pygame.Surface | None] = {}
        self._skin: dict[str, str] = {}
        self._skin_name: str | None = None
        self._slots = load_badge_slots()
        self._background: pygame.Surface | None = None
        self._painted: list[pygame.Rect] = []
        # What `_painted` holds, as drawn: (stratum, picture, where), so an
        # animated skin can put it back over what moved (ADR-0096). The
        # strata are upstream's z-order - artwork under the needles, the
        # title and its fields over them, the time and the badge over the
        # tonearm too.
        self._items: list[tuple[str, pygame.Surface, tuple[int, int]]] = []
        self._painting = True
        self._fonts: dict[tuple[str, int], pygame.font.Font] = {}
        # Keyed on the skin's dimension as well as the URL: the same track
        # across a skin change needs the art rescaled, and reusing the old
        # surface drew it at the previous skin's size (found on the panel).
        self._artwork_key: tuple | None = None
        self._artwork: pygame.Surface | None = None
        self._artwork_source: pygame.Surface | None = None
        self._artwork_url: str | None = None
        self._last_drawn: tuple | None = None
        self._art_spins = False
        self._ticker: Ticker | None = None
        self._ticker_item: int | None = None

    # ---- skin ----------------------------------------------------------

    def set_skin(self, skin: dict[str, str], directory=None, name: str | None = None) -> None:
        """A clean copy of the skin's own background, so a field that
        disappears can be erased back to it rather than smeared.

        `directory` is the skin's own, for a corpus that spans more than one
        (ADR-0051 §2); without it the one this layer was built with stands.
        """
        if directory is not None:
            self._corpus = directory
        self._skin = skin
        self._skin_name = name
        # ADR-0096: art that turns with the record is the motion layer's to
        # draw; drawn here as well, a still copy would sit on the spinning one.
        speed = (skin.get("albumart.rotation.speed") or "0").strip()
        self._art_spins = (skin.get("albumart.rotation") or "").strip().lower() == "true" \
            and speed not in ("", "0", "0.0")
        self._painted = []
        self._items = []
        self._last_drawn = None
        self._background = None
        self._ticker = None
        self._ticker_item = None
        if (skin.get("playinfo.ticker") or "").strip().lower() == "true":
            self._ticker = Ticker(
                speed=_float(skin.get("playinfo.ticker.speed"), 40.0),
                rightward=(skin.get("playinfo.ticker.direction") or "ltr").strip().lower() == "rtl",
                end_spaces=int(_float(skin.get("playinfo.ticker.end_spaces"), 8)),
            )
        picture = (skin.get("screen.bgr") or "").strip()
        if not picture:
            self._background = self._meter_background(skin)
            return
        path = self._corpus / picture
        try:
            image = pygame.image.load(str(path)).convert()
        except (pygame.error, OSError) as exc:
            logger.warning("render: no background %s: %s", path, exc)
            return
        if image.get_size() != self._screen.get_size():
            image = pygame.transform.smoothscale(image, self._screen.get_size())
        self._background = image

    def _meter_background(self, skin: dict[str, str]) -> pygame.Surface | None:
        """**A skin with no `screen.bgr` is drawn by its meter's background
        alone** (ADR-0096) - 41 of the 48 turntables. Without this the layer had
        nothing to erase back to and drew no title, art or badge at all. The
        picture the engine paints is `bgr.filename` at the meter's origin, over
        whatever was there - black, here."""
        picture = (skin.get("bgr.filename") or "").strip()
        if not picture:
            return None
        path = self._corpus / picture
        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (pygame.error, OSError) as exc:
            logger.warning("render: no meter background %s: %s", path, exc)
            return None
        canvas = pygame.Surface(self._screen.get_size())
        canvas.fill((0, 0, 0))
        try:
            origin = (int(skin.get("meter.x") or 0), int(skin.get("meter.y") or 0))
        except ValueError:
            origin = (0, 0)
        canvas.blit(image, origin)
        return canvas

    @property
    def background(self) -> pygame.Surface | None:
        """The clean picture this layer erases back to (ADR-0096's motion
        layer paints over the same one)."""
        return self._background

    @property
    def artwork_source(self) -> pygame.Surface | None:
        """This track's artwork at full size, fetched once for both layers."""
        return self._artwork_source

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

    def draw(self, metadata: dict, paint: bool = True) -> list[pygame.Rect]:
        """Returns the rectangles that changed, for the caller to present.

        With `paint` false nothing reaches the screen: the fields are laid out
        and the rectangles returned, for ADR-0096's motion layer to compose -
        erasing to this layer's background there would wipe the record or
        the reels under a title."""
        if self._background is None:
            return []
        fields = self._fields(metadata)
        fingerprint = (fields, metadata.get("source"), metadata.get("artwork"), repr(metadata.get("next")))
        if fingerprint == self._last_drawn:
            return []
        self._last_drawn = fingerprint

        dirty = list(self._painted)
        if paint:
            for rect in self._painted:
                self._screen.blit(self._background, rect, rect)
        self._painted = []
        self._items = []
        self._ticker_item = None
        self._painting = paint

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

        for text, point, colour, size, maxwidth, stratum in fields:
            if not text:
                continue  # criterion 7: nothing for this field, nothing drawn
            if stratum == "ticker":
                rect = self._ticker_rect(text, point, colour, size, maxwidth)
            else:
                rect = self._text(text, point, colour, size, maxwidth, stratum)
            if rect is not None:
                self._painted.append(rect)
                dirty.append(rect)

        self._painting = True
        return dirty

    def paint(self, strata: tuple[str, ...], area: pygame.Rect) -> None:
        """Put back what this layer last drew in `strata`, inside `area`."""
        clip = self._screen.get_clip()
        self._screen.set_clip(area)
        for stratum, picture, where in self._items:
            if stratum in strata:
                self._screen.blit(picture, where)
        self._screen.set_clip(clip)

    def tick(self, now: float | None = None) -> list[pygame.Rect]:
        """Every frame: the ticker's box when it has moved, for the caller
        to compose (a moving skin) or `repaint` (a still one)."""
        if self._ticker is None or self._ticker_item is None:
            return []
        if not self._ticker.advance(time.monotonic() if now is None else now):
            return []
        box = self._ticker.box
        self._items[self._ticker_item] = ("text", self._ticker.picture(), box.topleft)
        return [box.copy()]

    def repaint(self, rects: list[pygame.Rect]) -> list[pygame.Rect]:
        """A still skin's own compose: the background, then what this layer
        drew, inside each rectangle."""
        if self._background is None:
            return []
        clip = self._screen.get_clip()
        for rect in rects:
            self._screen.set_clip(rect)
            self._screen.blit(self._background, rect, rect)
            self.paint(("art", "text", "meta"), rect)
        self._screen.set_clip(clip)
        return rects

    def _ticker_rect(self, text, point, colour, size, width) -> pygame.Rect | None:
        if self._ticker is None:
            return None
        room = self._screen.get_width() - point[0]
        width = min(width or room - RIGHT_MARGIN, room)
        box = self._ticker.show(self.font(point[2], size), str(text), point, colour, width)
        self._ticker_item = len(self._items)
        return self._put("text", self._ticker.picture(), box.topleft)

    def _put(self, stratum: str, picture: pygame.Surface, where: tuple[int, int]) -> pygame.Rect:
        self._items.append((stratum, picture, where))
        if self._painting:
            self._screen.blit(picture, where)
        return pygame.Rect(where, picture.get_size())

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

        def own_size(key: str | None) -> int:
            try:
                return int(skin.get(key) or 0) if key else 0
            except ValueError:
                return 0

        def field(key: str, text: str | None, colour_key: str | None = None, width_key: str | None = None,
                  weight: str | None = None, override_colour=None, stratum: str = "text",
                  size_key: str | None = None):
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
                own_size(size_key) or sizes.get(point[2], sizes["regular"]),
                box_width(point, own_width) if width_key else 0,
                stratum,
            )

        # A ticker that `replace`s the fields takes their place (upstream's
        # `playinfo.ticker.replace`; every shipped skin says False).
        replaced = self._ticker is not None and (skin.get("playinfo.ticker.replace") or "").strip().lower() == "true"
        shown = {} if replaced else metadata
        upcoming = {} if replaced else (metadata.get("next") or {})
        entries = [
            self._ticker_line(metadata, field),
            field("playinfo.title.pos", shown.get("title"), "playinfo.title.color", "playinfo.title.maxwidth"),
            field("playinfo.artist.pos", shown.get("artist"), "playinfo.artist.color", "playinfo.artist.maxwidth"),
            field("playinfo.album.pos", shown.get("album"), "playinfo.album.color", "playinfo.album.maxwidth"),
            # ADR-0097: the track after this one, where the source has a
            # queue (LMS); blank otherwise and at the end of it.
            *(field(f"playinfo.next.{key}.pos", upcoming.get(key), f"playinfo.next.{key}.color",
                    f"playinfo.next.{key}.maxwidth") for key in ("title", "artist", "album")),
            # Not a text box: drawn top-left at the position in the digi face,
            # like the wrapper, so it lines up with the label the skin paints.
            field(
                "time.remaining.pos",
                remaining_time(metadata),
                "time.remaining.color",
                weight="digi",
                override_colour=FINAL_SECONDS_COLOUR if 0 < remaining_seconds(metadata, -1) <= FINAL_SECONDS else None,
                stratum="meta",
                # The turntable and tape skins size their clock apart from
                # the digi face (66 of the 90; none of the 99 others): the
                # Sansui cassette's digits ran into its meter at 45 px.
                size_key="time.remaining.fontsize",
            ),
            # The source is a badge, not text: see _badge_rect.
            # playinfo.samplerate.pos is never filled: no sample rate and no
            # codec renders anywhere (ADR-0036). The skins keep the position;
            # we keep it empty, which is this criterion's own rule.
        ]
        return tuple(entry for entry in entries if entry is not None)

    def _ticker_line(self, metadata: dict, field):
        """**A ticker skin's title** (ADR-0096 as amended, ADR-0097): 27 of
        the animated skins place their title only as upstream's scrolling
        ticker. "Title • Artist • Album" - George's order - with the skin's
        separator and spacing, then the next track where LMS reports one;
        `Ticker` scrolls it. A skin with a title field of its own keeps that
        one: nine have both, and would show the title twice."""
        skin = self._skin
        if self._ticker is None or "playinfo.title.pos" in skin:
            return None
        separator = (skin.get("playinfo.ticker.separator") or "").strip() or "•"
        gap = " " * max(1, int(_float(skin.get("playinfo.ticker.space_between"), 1)))
        between = f"{gap}{separator}{gap}"
        parts = [metadata.get(key) for key in ("title", "artist", "album")]
        line = between.join(str(part) for part in parts if part)
        # ADR-0097: the next track where the source reports one - LMS's
        # queue - in upstream's words, "Next: artist - title".
        upcoming = metadata.get("next") or {}
        if line and (skin.get("playinfo.ticker.append_next") or "").strip().lower() == "true":
            coming = " - ".join(str(v) for v in (upcoming.get("artist"), upcoming.get("title")) if v)
            if coming:
                line += f"{between}Next: {coming}"
        return field("playinfo.ticker.pos", line or None, "playinfo.ticker.color", "playinfo.ticker.maxwidth",
                     stratum="ticker")

    def _text(self, text, point, colour, size, maxwidth, stratum="text") -> pygame.Rect | None:
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
        return self._put(stratum, surface, (x, y))

    def _badge_rect(self, source: str | None) -> pygame.Rect | None:
        """The renderer's mark, fitted inside the square the skin reserves for
        it (`playinfo.type.pos`, `playinfo.type.dimension`)."""
        position = parse_size(self._skin.get("playinfo.type.pos"))
        if position is None or source is None:
            return None
        box = parse_size(self._skin.get("playinfo.type.dimension")) or (50, 50)
        slot = self._slots.get(self._skin_name or "")
        if slot is not None:
            # Never larger than the slot: 59G5_Yamaha M85 declares a 95 px box
            # in a 94 px window.
            box = (min(box[0], slot[2] - slot[0]), min(box[1], slot[3] - slot[1]))
        # The size only: centring below still uses the whole field.
        fit = (max(1, round(box[0] * BADGE_FILL)), max(1, round(box[1] * BADGE_FILL)))
        badge = self._badge(source, fit)
        if badge is None:
            return None
        if slot is not None:
            # Same size as the declared box gives it; centred in the slot.
            x = (slot[0] + slot[2] - badge.get_width()) // 2
            y = (slot[1] + slot[3] - badge.get_height()) // 2
        else:
            x = position[0] + (box[0] - badge.get_width()) // 2
            y = position[1] + (box[1] - badge.get_height()) // 2
        return self._put("meta", badge, (x, y))

    def _badge(self, source: str, box: tuple[int, int]) -> pygame.Surface | None:
        key = (source, box)
        if key not in self._badges:
            if source in BADGES:
                filename, tint = BADGES[source]
                path = self._icon_dir / filename
            else:
                # A plugin renderer: its mark came with its manifest.
                tint = None
                path = PLUGIN_MARKS / source / "mark.png"
            if source == "lms" and box[1] < LYRION_REDUCTION_BELOW:
                self._badges[key] = _lyrion_reduction(box, tint)
                return self._badges[key]
            try:
                image = pygame.image.load(str(path)).convert_alpha()
            except (pygame.error, OSError) as exc:
                # A plugin that ships no mark is the ordinary case, not a fault -
                # LMS ships none either. Said at debug so a skin without a badge
                # does not fill the journal on every frame.
                logger.debug("render: no badge for %s: %s", source, exc)
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
                # **A dark edge, so thin mint bars hold on a light skin**
                # (George, 2026-09-27, of LMS's mark on 113G5_Old Spectrum:
                # "Change it up so it's more visible"). The same idea as the
                # Plex mark's contour: invisible on a dark panel, the edge
                # of the shape on a cream one.
                image = _with_edge(image)
                # The edge grows it; fit it back inside the box it was sized
                # for, so the margin to the field holds.
                shrink = min(box[0] / image.get_width(), box[1] / image.get_height(), 1.0)
                if shrink < 1.0:
                    image = pygame.transform.smoothscale(
                        image, (max(1, round(image.get_width() * shrink)),
                                max(1, round(image.get_height() * shrink))))
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
        if self._artwork_source is None or self._art_spins:
            return None
        if self._artwork_key != (url, dimension):
            self._artwork = pygame.transform.smoothscale(self._artwork_source, dimension)
            self._artwork_key = (url, dimension)
        return self._put("art", self._artwork, position)

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
