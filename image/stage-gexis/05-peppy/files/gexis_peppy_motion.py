# SPDX-License-Identifier: GPL-3.0-or-later
"""What moves on a turntable or a tape deck (ADR-0096).

A spinning vinyl with the album art on it, a tonearm that drops, tracks the
song and lifts, and the reels of a cassette or a tape recorder. Drawn after the
meter each frame, into the regions that changed, and presented by the caller.

**The design is upstream's, the code is not.** The mechanics - pre-rendered
rotation frames at a fixed step, a frame-rate gate on the spin, art composited
onto the disc so the two turn as one, the tonearm's REST/DROP/TRACKING/LIFT
states with an eased drop and lift and an early lift before the end of a track,
and the rotation about a pivot inside the arm's own picture - come from
`volumio_turntable.py` and `volumio_cassette.py` in foonerd/peppy_screensaver
(MIT; 2aCD's original ISC). This module drives them from `nowplaying.json`
instead of a Volumio state dict, keeps our own text and badge layer, and
rotates the tonearm when it moves instead of pre-rendering it at every half
degree - which is where most of upstream's ~350 MB per skin went.
"""
from __future__ import annotations

import logging
import math
import time
from pathlib import Path

import pygame

logger = logging.getLogger("gexis.peppy.motion")

#: Degrees between pre-rendered frames, and how often the spin is redrawn.
#: Upstream's "medium" preset: 60 frames, 8 redraws a second.
SPIN_STEP_DEG = 6
SPIN_FPS = 8
#: Pre-rendered frames built per tick, so a new track's disc is built while
#: the old one keeps turning rather than in one long stall.
BUILD_PER_TICK = 4
#: The tonearm lifts this long before the end of a track, as upstream's does.
EARLY_LIFT_S = 1.5
#: How often a tracking arm is redrawn: it moves a fraction of a degree.
TRACKING_REDRAW_S = 0.5


def _point(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    try:
        x, y = (int(v.strip()) for v in value.split(",")[:2])
    except ValueError:
        return None
    return x, y


def _number(value: str | None, default: float) -> float:
    try:
        return float(value) if value not in (None, "") else default
    except ValueError:
        return default


def _true(value: str | None) -> bool:
    return str(value or "").strip().lower() in ("true", "1", "yes")


def _load(directory: Path, name: str | None) -> pygame.Surface | None:
    if not name:
        return None
    try:
        return pygame.image.load(str(directory / name.strip())).convert_alpha()
    except (pygame.error, OSError) as exc:
        logger.warning("motion: cannot load %s: %s", name, exc)
        return None


def _theme(value: str | None) -> str | None:
    """The record's own picture from upstream's `album,theme` form.

    `cdart.png,Vertere DG1_vinyl.png` means: the album's disc art, from the
    music folder, when it has one - otherwise this picture. We never see the
    music folder, so it is always the second. Loaded as one name, it drew no
    record at all on 18 turntables."""
    if not value or "," not in value:
        return value
    parts = [part.strip() for part in value.split(",")]
    return parts[1] or parts[0] or None


def _disc(surface: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
    """`surface` scaled to `size` and cut to a circle - a record label."""
    scaled = pygame.transform.smoothscale(surface.convert_alpha(), size)
    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.ellipse(mask, (255, 255, 255, 255), mask.get_rect())
    scaled.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return scaled


class Spinner:
    """A vinyl or a reel: a picture turning about `center` at `rpm` while
    playing, still while not."""

    def __init__(self, picture: pygame.Surface, center: tuple[int, int], rpm: float, clockwise: bool):
        self.base = picture
        self.picture = picture
        self.center = center
        self.rpm = abs(rpm)
        self.sign = 1 if clockwise else -1
        self.angle = 0.0
        self._frames: list[pygame.Surface | None] = []
        self._queue: list[int] = []
        self._rebuild()
        diagonal = int(math.hypot(*picture.get_size())) + 4
        self.region = pygame.Rect(0, 0, diagonal, diagonal)
        self.region.center = center

    def with_label(self, label: pygame.Surface | None) -> None:
        """The album art composited onto the disc, so art and record turn as
        one (upstream's COMPOSITE MODE)."""
        self.picture = self.base.copy()
        if label is not None:
            spot = label.get_rect(center=self.picture.get_rect().center)
            self.picture.blit(label, spot)
        self._rebuild()

    def _rebuild(self) -> None:
        count = 360 // SPIN_STEP_DEG
        self._frames = [None] * count
        self._queue = list(range(count))

    def build_some(self) -> None:
        for _ in range(min(BUILD_PER_TICK, len(self._queue))):
            index = self._queue.pop(0)
            self._frames[index] = pygame.transform.rotate(self.picture, -index * SPIN_STEP_DEG)

    def advance(self, seconds: float) -> None:
        self.angle = (self.angle + self.rpm * 6.0 * seconds * self.sign) % 360.0

    def draw(self, screen: pygame.Surface) -> None:
        index = int(self.angle // SPIN_STEP_DEG) % len(self._frames)
        frame = self._frames[index]
        if frame is None:
            frame = pygame.transform.rotate(self.picture, -self.angle)
        screen.blit(frame, frame.get_rect(center=self.center))


class Tonearm:
    REST, DROP, TRACKING, LIFT = "rest", "drop", "tracking", "lift"

    def __init__(self, picture, pivot_screen, pivot_image, rest, start, end, drop_s, lift_s):
        self.picture = picture
        self.pivot_screen = pivot_screen
        self.pivot_image = pivot_image
        self.rest, self.start, self.end = rest, start, end
        self.drop_s, self.lift_s = max(0.05, drop_s), max(0.05, lift_s)
        self.state = self.REST
        self.angle = rest
        self._from = self._to = rest
        self._began = 0.0
        self._length = 1.0
        self._early = False
        self.drawn_angle: float | None = None
        self.drawn_rect: pygame.Rect | None = None

    def _groove(self, progress: float) -> float:
        return self.start + (self.end - self.start) * max(0.0, min(1.0, progress))

    def _move(self, target: float, seconds: float, now: float) -> None:
        self._from, self._to, self._began, self._length = self.angle, target, now, seconds

    def _eased(self, now: float) -> bool:
        t = min(1.0, (now - self._began) / self._length)
        self.angle = self._from + (self._to - self._from) * (1 - (1 - t) ** 3)
        return t >= 1.0

    def update(self, playing: bool, progress: float | None, remaining: float | None, now: float) -> None:
        progress = 0.0 if progress is None else progress
        if self.state == self.REST:
            # Not straight back down on a track that has barely moved since an
            # early lift - the next track's own start drops it.
            if playing and not (self._early and progress > 0.1):
                self._early = False
                self.state = self.DROP
                self._move(self._groove(progress), self.drop_s, now)
        elif self.state == self.DROP:
            if not playing:
                self.state = self.LIFT
                self._move(self.rest, self.lift_s, now)
            elif self._eased(now):
                self.state = self.TRACKING
        elif self.state == self.TRACKING:
            if not playing or (remaining is not None and 0 < remaining < EARLY_LIFT_S):
                self._early = playing
                self.state = self.LIFT
                self._move(self.rest, self.lift_s, now)
            else:
                self.angle = self._groove(progress)
        elif self.state == self.LIFT:
            if self._eased(now):
                self.state = self.REST
                self.angle = self.rest

    def needs_drawing(self) -> bool:
        if self.drawn_angle is None:
            return True
        if self.state in (self.DROP, self.LIFT):
            return True
        return abs(self.angle - self.drawn_angle) >= 0.1

    def placed(self, angle: float | None = None) -> tuple[pygame.Surface, pygame.Rect]:
        """The arm rotated by `angle` (its current one unless given) and
        placed so `pivot_image` lands on `pivot_screen` (pygame rotates
        counter-clockwise, y down)."""
        angle = self.angle if angle is None else angle
        rotated = pygame.transform.rotate(self.picture, angle)
        w, h = self.picture.get_size()
        dx, dy = self.pivot_image[0] - w / 2, self.pivot_image[1] - h / 2
        a = math.radians(-angle)
        rx, ry = dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
        rw, rh = rotated.get_size()
        left = int(self.pivot_screen[0] - (rw / 2 + rx))
        top = int(self.pivot_screen[1] - (rh / 2 + ry))
        return rotated, pygame.Rect(left, top, rw, rh)


def merged(rects: list[pygame.Rect], bounds: pygame.Rect) -> list[pygame.Rect]:
    """`rects` inside `bounds`, those that touch joined into one. Only those:
    one rectangle round both reels of a cassette covered the title between
    them, and repainted it eight times a second."""
    out: list[pygame.Rect] = []
    for rect in rects:
        rect = rect.clip(bounds)
        if not rect.width or not rect.height:
            continue
        joined = True
        while joined:
            joined = False
            for other in out:
                if other.colliderect(rect):
                    out.remove(other)
                    rect = rect.union(other)
                    joined = True
                    break
        out.append(rect)
    return out


class MotionLayer:
    """Everything that moves on the current skin, or nothing.

    **Whatever it repaints, it repaints whole** (ADR-0096), in upstream's
    z-order: the static picture, what turns, the artwork, the needles, the
    title and its fields, the tonearm, the time and the badge, the
    foreground. Repainting only the background and what moves wiped
    whatever else was there until it next changed - the title flashed, the
    art was half painted, the arm seemed to carry a mask (George, on the
    panel, 2026-09-27).
    """

    def __init__(self, screen: pygame.Surface, layer=None, needles=None) -> None:
        self._screen = screen
        #: The text layer (`MetadataLayer.paint`), and a callable that redraws
        #: the meter's needles inside a rectangle; either may be absent.
        self.layer = layer
        self.needles = needles
        self.spinners: list[Spinner] = []
        self.arm: Tonearm | None = None
        self._background: pygame.Surface | None = None
        self._foreground: pygame.Surface | None = None
        self._label_size: tuple[int, int] | None = None
        self._label_spinner: Spinner | None = None
        self._label_source: pygame.Surface | None = None
        self._last_spin = 0.0
        self._last_tick = 0.0
        self._last_arm = 0.0

    @property
    def active(self) -> bool:
        return bool(self.spinners or self.arm)

    def set_skin(self, skin: dict[str, str], directory: Path,
                 background: pygame.Surface | None) -> None:
        self.spinners, self.arm = [], None
        self._label_spinner = self._label_source = None
        self._label_size = None
        self._background = self._foreground = None
        if background is None:
            return
        # The static picture under everything that moves: the layer's own
        # background with the meter's drawn over it, which is what the engine
        # paints (screen.bgr first, then bgr.filename at the meter's origin).
        self._background = background.copy()
        origin = (int(_number(skin.get("meter.x"), 0)), int(_number(skin.get("meter.y"), 0)))
        meter = _load(directory, skin.get("bgr.filename"))
        if meter is not None:
            self._background.blit(meter, origin)
        foreground = _load(directory, skin.get("fgr.filename"))
        if foreground is not None:
            self._foreground = pygame.Surface(self._screen.get_size(), pygame.SRCALPHA)
            self._foreground.blit(foreground, origin)

        rpm = _number(skin.get("albumart.rotation.speed"), 0.0)
        spins = _true(skin.get("albumart.rotation")) and rpm > 0
        clockwise = (skin.get("vinyl.direction") or skin.get("reel.direction") or "cw").strip().lower() != "ccw"
        art_pos, art_dim = _point(skin.get("albumart.pos")), _point(skin.get("albumart.dimension"))

        vinyl = _load(directory, _theme(skin.get("vinyl.filename")))
        center = _point(skin.get("vinyl.center"))
        if vinyl is not None and center is not None:
            size = _point(skin.get("vinyl.dimension"))
            if size:
                vinyl = pygame.transform.smoothscale(vinyl, size)
            # The record turns at the skin's speed whether or not the art is
            # on it: `albumart.rotation` says only where the art goes, as in
            # upstream. Read as "still", it left 27 turntables' records
            # standing - every `_03` variant among them.
            self._label_spinner = Spinner(vinyl, center, rpm, clockwise)
            self.spinners.append(self._label_spinner)
        elif spins and art_pos and art_dim:
            # No vinyl picture: the album art itself is the record (ten of the
            # turntables), turning where the layer would have drawn it still.
            blank = pygame.Surface(art_dim, pygame.SRCALPHA)
            spot = (art_pos[0] + art_dim[0] // 2, art_pos[1] + art_dim[1] // 2)
            self._label_spinner = Spinner(blank, spot, rpm, clockwise)
            self.spinners.append(self._label_spinner)
        if self._label_spinner is not None and spins and art_dim:
            self._label_size = art_dim

        reel_rpm = _number(skin.get("reel.rotation.speed"), 0.0)
        reel_cw = (skin.get("reel.direction") or "ccw").strip().lower() == "cw"
        for side in ("left", "right"):
            picture = _load(directory, skin.get(f"reel.{side}.filename"))
            spot = _point(skin.get(f"reel.{side}.center"))
            if picture is not None and spot is not None:
                self.spinners.append(Spinner(picture, spot, reel_rpm, reel_cw))

        arm = _load(directory, skin.get("tonearm.filename"))
        pivot_screen, pivot_image = _point(skin.get("tonearm.pivot.screen")), _point(skin.get("tonearm.pivot.image"))
        if arm is not None and pivot_screen and pivot_image:
            self.arm = Tonearm(
                arm, pivot_screen, pivot_image,
                _number(skin.get("tonearm.angle.rest"), -30.0),
                _number(skin.get("tonearm.angle.start"), 0.0),
                _number(skin.get("tonearm.angle.end"), 25.0),
                _number(skin.get("tonearm.drop.duration"), 1.5),
                _number(skin.get("tonearm.lift.duration"), 1.0),
            )
        self._last_spin = self._last_tick = 0.0
        if self.active:
            logger.info("motion: %d spinning, tonearm %s", len(self.spinners), "yes" if self.arm else "no")

    def _set_label(self, artwork: pygame.Surface | None) -> None:
        if self._label_spinner is None or self._label_size is None or artwork is self._label_source:
            return
        self._label_source = artwork
        self._label_spinner.with_label(_disc(artwork, self._label_size) if artwork is not None else None)

    def tick(self, metadata: dict, artwork: pygame.Surface | None, now: float | None = None) -> list[pygame.Rect]:
        """Advance and draw what moved; the rectangles to present."""
        if not self.active or self._background is None:
            return []
        now = time.monotonic() if now is None else now
        playing = metadata.get("transport") == "playing"
        self._set_label(artwork)
        for spinner in self.spinners:
            spinner.build_some()

        regions: list[pygame.Rect] = []
        spin_due = now - self._last_spin >= 1.0 / SPIN_FPS
        if spin_due and (playing or self._last_spin == 0.0):
            elapsed = min(0.5, now - self._last_spin) if self._last_spin else 0.0
            for spinner in self.spinners:
                if playing:
                    spinner.advance(elapsed)
                regions.append(spinner.region)
            self._last_spin = now

        if self.arm is not None:
            position, duration = metadata.get("position"), metadata.get("duration")
            progress = remaining = None
            if position is not None and duration:
                if playing:
                    position += max(0.0, time.time() - metadata.get("written_at", time.time()))
                progress, remaining = position / duration, duration - position
            self.arm.update(playing, progress, remaining, now)
            moving = self.arm.state in (Tonearm.DROP, Tonearm.LIFT)
            if self.arm.needs_drawing() and (moving or now - self._last_arm >= TRACKING_REDRAW_S):
                _, rect = self.arm.placed()
                if self.arm.drawn_rect is not None:
                    regions.append(self.arm.drawn_rect)
                regions.append(rect)
                self.arm.drawn_angle, self.arm.drawn_rect = self.arm.angle, rect
                self._last_arm = now

        if not regions:
            return []
        return self.compose(regions)

    def compose(self, rects: list[pygame.Rect]) -> list[pygame.Rect]:
        """Repaint `rects` from the bottom up; the rectangles to present."""
        if self._background is None:
            return []
        areas = merged(rects, self._screen.get_rect())
        clip = self._screen.get_clip()
        for area in areas:
            self._screen.set_clip(area)
            self._screen.blit(self._background, area, area)
            for spinner in self.spinners:
                spinner.draw(self._screen)
            if self.layer is not None:
                self.layer.paint(("art",), area)
            if self.needles is not None:
                self.needles(area)
            if self.layer is not None:
                self.layer.paint(("text",), area)
            if self.arm is not None and self.arm.drawn_angle is not None:
                # At the angle it was last drawn at in full: a spin repainting
                # a corner of the arm must not draw that corner somewhere new.
                arm, rect = self.arm.placed(self.arm.drawn_angle)
                self._screen.blit(arm, rect)
            if self.layer is not None:
                self.layer.paint(("meta",), area)
            if self._foreground is not None:
                self._screen.blit(self._foreground, area, area)
        self._screen.set_clip(clip)
        return areas
