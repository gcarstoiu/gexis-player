# SPDX-License-Identifier: GPL-3.0-or-later
"""What an animated skin shows beyond the title (ADR-0097): the track's
progress, the volume, and the mute, play state, shuffle and repeat icons.

**Display only.** Every one of these draws a state and does nothing when
touched - a tap dismisses the visualiser, as it always has (George,
2026-09-27: *"it is not its purpose to be actionable"*).

**The geometry is upstream's, the code is not.** Read from foonerd's
`volumio_indicators.py` (MIT): `SliderIndicator` for progress and volume -
a procedural bar, a picture sliding along a travel, a rotated knob or an
anti-aliased arc - and `IconIndicator` for the icons, with its glow. Each
piece is returned as a picture and a place, for `MetadataLayer` to draw in
its "meta" stratum, above the tonearm, as upstream orders them.
"""
from __future__ import annotations

import logging
import math
from pathlib import Path

import pygame

logger = logging.getLogger("gexis.peppy.gauges")

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:  # the image ships python3-pil; without it, no arc AA and no glow
    Image = ImageDraw = ImageFilter = None

#: Upstream draws arcs at four times the size and scales them down.
ARC_SCALE = 4


def _pair(value: str | None, default=None):
    if not value or not str(value).strip():
        return default
    try:
        a, b = (int(float(v.strip())) for v in str(value).split(",")[:2])
    except ValueError:
        return default
    return a, b


def _number(value, default: float) -> float:
    try:
        return float(str(value).strip()) if value not in (None, "") else default
    except ValueError:
        return default


def _colour(value: str | None, default):
    if not value or not str(value).strip():
        return default
    try:
        parts = [int(v.strip()) for v in str(value).split(",")]
    except ValueError:
        return default
    return tuple(parts[:4]) if len(parts) >= 3 else default


def _load(directory: Path, name: str | None) -> pygame.Surface | None:
    if not name or not name.strip():
        return None
    try:
        return pygame.image.load(str(directory / name.strip())).convert_alpha()
    except (pygame.error, OSError) as exc:
        logger.warning("gauges: cannot load %s: %s", name, exc)
        return None


def arc(size: tuple[int, int], colour, start_deg: float, stop_deg: float, width: int) -> pygame.Surface:
    """An annular sector inside `size`, counter-clockwise from `start_deg` to
    `stop_deg` (0 = east, y up, as upstream's `_draw_solid_arc`), `width`
    thick inset from the edge. A full turn is drawn as two halves."""
    surface = pygame.Surface(size, pygame.SRCALPHA)
    span = math.radians(stop_deg - start_deg)
    while span <= 0:
        span += 2 * math.pi
    while span > 2 * math.pi:
        span -= 2 * math.pi
    s = ARC_SCALE if Image is not None else 1
    w, h = size[0] * s, size[1] * s
    stroke = max(1, int(width) * s)

    def sector(a0: float, a1: float) -> list[tuple[float, float]]:
        cx, cy, rx, ry = w / 2, h / 2, w / 2, h / 2
        rxi, ryi = max(0.0, rx - stroke), max(0.0, ry - stroke)
        steps = max(24, int((a1 - a0) / (2 * math.pi) * 192))
        outer = [(cx + rx * math.cos(a0 + (a1 - a0) * i / steps), cy - ry * math.sin(a0 + (a1 - a0) * i / steps))
                 for i in range(steps + 1)]
        inner = [(cx + rxi * math.cos(a1 - (a1 - a0) * i / steps), cy - ryi * math.sin(a1 - (a1 - a0) * i / steps))
                 for i in range(steps + 1)]
        return outer + inner

    a0 = math.radians(start_deg)
    polygons = ([sector(a0, a0 + math.pi), sector(a0 + math.pi, a0 + 2 * math.pi)]
                if span >= 2 * math.pi - 1e-4 else [sector(a0, a0 + span)])
    fill = tuple(int(c) for c in colour[:3]) + ((int(colour[3]),) if len(colour) > 3 else (255,))
    if Image is not None:
        big = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(big)
        for points in polygons:
            draw.polygon(points, fill=fill)
        small = big.resize(size, Image.LANCZOS)
        return pygame.image.fromstring(small.tobytes(), small.size, "RGBA").convert_alpha()
    for points in polygons:
        pygame.draw.polygon(surface, fill, points)
    return surface


class Gauge:
    """A value from 0 to 100 drawn as the skin says: `<prefix>.style` slider
    (a bar, or a tip picture moved along a travel), knob or arc; progress
    adds markers and a head picture. None of it is built when the skin has
    no `<prefix>.pos` and `.dim`."""

    SLIDER, KNOB, ARC = "slider", "knob", "arc"

    def __init__(self, prefix: str, skin: dict[str, str], directory: Path, font_path: str,
                 regular_size: int) -> None:
        get = lambda key, default=None: skin.get(f"{prefix}.{key}", default)  # noqa: E731
        self.pos = _pair(get("pos"))
        self.dim = _pair(get("dim"))
        self.ok = self.pos is not None and self.dim is not None and self.dim[0] > 0 and self.dim[1] > 0
        if not self.ok:
            return
        progress = prefix == "progress"
        self.colour = _colour(get("color"), (0, 200, 255) if progress else (255, 255, 255))
        self.bg = _colour(get("bg.color"), (40, 40, 40))
        style = (get("style") or ("slider" if progress else "numeric")).strip().lower()
        self.style = style if style in (self.SLIDER, self.KNOB, self.ARC) else None
        self.orientation = (get("slider.orientation") or ("horizontal" if progress else "vertical")).strip().lower()
        w, h = self.dim
        self.vertical = self.orientation == "vertical" or (self.orientation != "horizontal" and h > w)
        self.radius = int(_number(get("fill.radius"), 0))
        self.arc_start = _number(get("arc.angle.start"), 225.0)
        self.arc_end = _number(get("arc.angle.end"), -45.0)
        self.arc_width = int(_number(get("arc.width"), 6))
        self.knob_start = _number(get("knob.angle.start"), 225.0)
        self.knob_end = _number(get("knob.angle.end"), -45.0)
        self.knob = _load(directory, get("knob.image")) if self.style == self.KNOB else None
        self.tip = _load(directory, get("slider.tip")) if self.style == self.SLIDER else None
        self.tip_offset = _pair(get("slider.tip.offset"), (0, 0))
        if self.tip is not None:
            span = (h - self.tip.get_height()) if self.orientation == "vertical" else (w - self.tip.get_width())
            self.travel = _pair(get("slider.travel"), (0, span))
        self.head = _load(directory, get("head.image"))
        self.head_offset = _pair(get("head.offset"), (0, 0))
        self.markers: list[tuple[float, pygame.Surface]] = []
        if progress:
            for n in range(1, 11):
                where = get(f"marker.{n}.pos")
                if where in (None, ""):
                    break
                share = max(0.0, min(100.0, _number(where, 0.0))) / 100.0
                picture = _load(directory, get(f"marker.{n}.image"))
                label = get(f"marker.{n}.label") or ""
                if picture is None and label:
                    size = int(_number(get(f"marker.{n}.fontsize"), regular_size))
                    try:
                        picture = pygame.font.Font(font_path, size).render(label, True, self.colour[:3])
                    except (OSError, pygame.error):
                        picture = None
                if picture is not None:
                    self.markers.append((share, picture))
        self._arc_back: pygame.Surface | None = None
        self._arc_fill: dict[int, pygame.Surface] = {}
        self._knob_frames: dict[int, pygame.Surface] = {}

    def _point(self, share: float) -> tuple[int, int]:
        """Where a share of the way along sits: on the bar, or on the arc."""
        x, y = self.pos
        w, h = self.dim
        if self.style in (self.ARC, self.KNOB):
            angle = math.radians(self.arc_start - share * (self.arc_start - self.arc_end))
            radius = min(w, h) // 2 - self.arc_width
            return int(x + w / 2 + radius * math.cos(angle)), int(y + h / 2 - radius * math.sin(angle))
        if self.vertical:
            return x + w // 2, y + h - int(share * h)
        return x + int(share * w), y + h // 2

    def pieces(self, value: int | None) -> list[tuple[pygame.Surface, tuple[int, int]]]:
        """What to draw for `value` (0-100), bottom first."""
        if not self.ok or self.style is None or value is None:
            return []
        value = max(0, min(100, int(value)))
        x, y = self.pos
        w, h = self.dim
        out: list[tuple[pygame.Surface, tuple[int, int]]] = []
        if self.style == self.SLIDER and self.tip is not None:
            start, end = self.travel
            ox, oy = self.tip_offset
            tw, th = self.tip.get_size()
            if self.orientation == "vertical":
                where = (x + ox + (w - tw) // 2, y + end - int(value / 100 * (end - start)) + oy)
            else:
                where = (x + start + int(value / 100 * (end - start)) + ox, y + oy + (h - th) // 2)
            out.append((self.tip, where))
        elif self.style == self.SLIDER:
            bar = pygame.Surface((w, h), pygame.SRCALPHA)
            if self.bg:
                pygame.draw.rect(bar, self.bg, (0, 0, w, h), border_radius=self.radius)
            if self.vertical:
                fill = int(value / 100 * h)
                if fill > 0:
                    pygame.draw.rect(bar, self.colour, (0, h - fill, w, fill), border_radius=self.radius)
            else:
                fill = int(value / 100 * w)
                if fill > 0:
                    pygame.draw.rect(bar, self.colour, (0, 0, fill, h), border_radius=self.radius)
            out.append((bar, (x, y)))
        elif self.style == self.KNOB and self.knob is not None:
            frame = self._knob_frames.get(value)
            if frame is None:
                frame = pygame.transform.rotate(
                    self.knob, self.knob_start - value / 100 * (self.knob_start - self.knob_end))
                self._knob_frames[value] = frame
            out.append((frame, (x + (w - frame.get_width()) // 2, y + (h - frame.get_height()) // 2)))
        else:  # an arc, or a knob whose picture is missing, as upstream falls back
            if self._arc_back is None and self.bg:
                self._arc_back = arc((w, h), self.bg, self.arc_end, self.arc_start, self.arc_width)
            if self._arc_back is not None:
                out.append((self._arc_back, (x, y)))
            if value > 0:
                fill = self._arc_fill.get(value)
                if fill is None:
                    now = self.arc_start - value / 100 * (self.arc_start - self.arc_end)
                    fill = self._arc_fill[value] = arc((w, h), self.colour, now, self.arc_start, self.arc_width)
                out.append((fill, (x, y)))
        for share, picture in self.markers:
            px, py = self._point(share)
            out.append((picture, (px - picture.get_width() // 2, py - picture.get_height() // 2)))
        if self.head is not None:
            px, py = self._point(value / 100)
            ox, oy = self.head_offset
            out.append((self.head, (px - self.head.get_width() // 2 + ox, py - self.head.get_height() // 2 + oy)))
        return out
