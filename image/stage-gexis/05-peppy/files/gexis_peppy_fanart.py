# SPDX-License-Identifier: GPL-3.0-or-later
"""The artist's photos in a skin's fanart frame (ADR-0112).

A skin names a frame - `fanart.pos`, `fanart.dimension` - how a photo sits in
it - `fanart.scale`: `fit` keeps the aspect, centred, with the skin showing
around it; `stretch` fills the frame - and where it goes - `fanart.zorder`:
`background` under the meters, `overlay` over them and under our text. The
core puts the photos' local paths in `nowplaying.json` (`fanart`, up to ten);
this shows them one after another, **20 s each, in list order, looping, with a
1 s crossfade** (George: *"20 seconds is fine"*). A new list replaces the old
at once; an empty one leaves the skin's own picture (*"Agree"*).

**Where the photo is put, not just drawn.** Every fanart frame in the packs
lies on the meter's full-screen `bgr`, opaque there (all 70 checked). The
engine repaints a needle's old place from that picture, and the motion layer
and the text layer erase from their own copies of it, so a photo drawn once
on the screen would be wiped by the first needle that moved over it.
"background" therefore goes *into* each of those pictures - the engine's `bgr`
component (a private copy: the engine's image cache hands the same surface to
the next build of the skin), MetadataLayer's background and MotionLayer's -
and every repaint of any kind redraws it under the needles, the glass (`fgr`)
and the text. "overlay" goes into the engine's foreground, under the
foreground's own pixels, so a needle's repaint keeps it over the needle; and
MotionLayer draws it after the needles, before the text.

**Cheap.** A file is read only after the list changes, when its photo is
first needed (the next one at half-time, not at the fade), never larger than
the screen, and scaled to the frame once per skin. Between fades nothing is
drawn. A fade has FADE_STEPS steps, each repainting the frame's area only.

The design is upstream's (foonerd/peppy_screensaver, `volumio_artistfanart.py`:
`fit`/`stretch`, the zorder, a crossfade); the code is ours.
"""
from __future__ import annotations

import logging
import time

import pygame

logger = logging.getLogger("gexis.peppy.fanart")

#: George, 2026-10-02: one photo every 20 seconds, with a crossfade.
INTERVAL_S = 20.0
FADE_S = 1.0
#: Repaints per fade. A fade every 20 s at 30 fps would be 30 full-frame
#: blends; 12 reads as smooth at a second and costs less than half.
FADE_STEPS = 12
#: The core's own bound (ADR-0112: at most 10 photos per artist).
MAX_PHOTOS = 10


def _pair(value: str | None) -> tuple[int, int] | None:
    try:
        x, y = (int(v.strip()) for v in (value or "").split(",")[:2])
    except ValueError:
        return None
    return x, y


def _number(value: str | None) -> float:
    try:
        return float(value) if value not in (None, "") else 0.0
    except ValueError:
        return 0.0


def frame_of(skin: dict[str, str]) -> tuple[pygame.Rect, str, str] | None:
    """The skin's frame, scale and zorder, or None when it has no frame."""
    pos, dim = _pair(skin.get("fanart.pos")), _pair(skin.get("fanart.dimension"))
    if pos is None or dim is None or dim[0] <= 0 or dim[1] <= 0:
        return None
    scale = (skin.get("fanart.scale") or "fit").strip().lower()
    zorder = (skin.get("fanart.zorder") or "background").strip().lower()
    return (pygame.Rect(pos, dim), "stretch" if scale == "stretch" else "fit",
            "overlay" if zorder == "overlay" else "background")


def placed(size: tuple[int, int], frame: pygame.Rect, scale: str) -> pygame.Rect:
    """Where a photo of `size` goes: the whole frame for `stretch`; for `fit`
    the largest rectangle of its aspect inside the frame, centred."""
    if scale == "stretch" or size[0] <= 0 or size[1] <= 0:
        return frame.copy()
    ratio = min(frame.w / size[0], frame.h / size[1])
    w, h = max(1, round(size[0] * ratio)), max(1, round(size[1] * ratio))
    w, h = min(w, frame.w), min(h, frame.h)
    return pygame.Rect(frame.x + (frame.w - w) // 2, frame.y + (frame.h - h) // 2, w, h)


def moment(elapsed: float, count: int) -> tuple[int, int | None, float]:
    """(photo shown, photo fading out or None, how far the fade is, 0..1) at
    `elapsed` seconds into a list of `count` photos. The first photo shows at
    once; each later one fades in over the one before."""
    if count <= 0:
        return -1, None, 1.0
    step = int(max(0.0, elapsed) // INTERVAL_S)
    shown = step % count
    into = max(0.0, elapsed) - step * INTERVAL_S
    if step > 0 and count > 1 and into < FADE_S:
        return shown, (step - 1) % count, into / FADE_S
    return shown, None, 1.0


class Holder:
    """One picture the photo is put into, with its frame region as the skin
    drew it, so every update starts from the skin's own pixels."""

    def __init__(self, surface: pygame.Surface, offset: tuple[int, int], frame: pygame.Rect,
                 under: bool, during_fades: bool = True):
        self.surface = surface
        #: The frame on this surface (an engine picture sits at the meter's origin).
        self.area = frame.move(-offset[0], -offset[1]).clip(surface.get_rect())
        #: Where `area`'s top left is on the screen: a photo's screen place
        #: less this is its place in `area`.
        self.screen_origin = (self.area.x + offset[0], self.area.y + offset[1])
        self.pristine = surface.subsurface(self.area).copy()
        #: True: the picture's own pixels go *over* the photo (a foreground).
        self.under = under
        #: False: brought up to date at rest only - a picture nothing repaints
        #: from while the fade runs.
        self.during_fades = during_fades
        self._pair: tuple | None = None

    def show(self, photos: list[tuple[pygame.Surface, pygame.Rect]], old=None, p: float = 1.0) -> None:
        """`photos`: (picture, place inside the frame). `old`, when fading, is
        the outgoing photo; `p` how far the new one is in."""
        if old is None:
            self._put(self._with(photos))
            return
        if self.under:
            # A foreground: the outgoing photo fades out over what lies under
            # the glass, the incoming one in; the glass stays on top.
            canvas = pygame.Surface(self.area.size, pygame.SRCALPHA)
            for (picture, spot), alpha in ((old, 255 - int(255 * p)), (photos[0], int(255 * p))):
                picture.set_alpha(alpha)
                canvas.blit(picture, spot.move(-self.screen_origin[0], -self.screen_origin[1]))
                picture.set_alpha(None)
            canvas.blit(self.pristine, (0, 0))
            self._put(canvas)
            return
        # Opaque: the skin with the old photo, blended into the skin with the
        # new one - a true crossfade, letterbox edges included.
        key = (id(old[0]), id(photos[0][0]))
        if self._pair is None or self._pair[0] != key:
            self._pair = (key, self._with([old]), self._with(photos))
        _, before, after = self._pair
        canvas = before.copy()
        after.set_alpha(int(255 * p))
        canvas.blit(after, (0, 0))
        after.set_alpha(None)
        self._put(canvas)

    def restore(self) -> None:
        self._pair = None
        self._put(self.pristine)

    def _with(self, photos) -> pygame.Surface:
        if self.under:
            canvas = pygame.Surface(self.area.size, pygame.SRCALPHA)
            for picture, spot in photos:
                canvas.blit(picture, spot.move(-self.screen_origin[0], -self.screen_origin[1]))
            canvas.blit(self.pristine, (0, 0))
            return canvas
        canvas = self.pristine.copy()
        for picture, spot in photos:
            canvas.blit(picture, spot.move(-self.screen_origin[0], -self.screen_origin[1]))
        return canvas

    def _put(self, picture: pygame.Surface) -> None:
        if self.surface.get_flags() & pygame.SRCALPHA:
            # Replaced, not blended over: a foreground's transparency must stay
            # exactly what the picture says.
            self.surface.fill((0, 0, 0, 0), self.area)
            self.surface.blit(picture, self.area.topleft, special_flags=pygame.BLEND_RGBA_MAX)
        else:
            self.surface.blit(picture, self.area.topleft)


class FanartFrame:
    def __init__(self, load=None, clock=time.monotonic) -> None:
        self._load = load or self._read
        self._clock = clock
        self.paths: list[str] = []
        self._decoded: dict[str, pygame.Surface | None] = {}
        self._fitted: dict[str, tuple[pygame.Surface, pygame.Rect] | None] = {}
        self._started = 0.0
        self.frame: pygame.Rect | None = None
        self.scale = "fit"
        self.zorder = "background"
        self._holders: list[Holder] = []
        self._shown: tuple | None = None
        self._bound: tuple[int, int] | None = None

    # ---- the list ----------------------------------------------------

    def set_paths(self, paths) -> bool:
        """The metadata's list; True when it changed - the frame then shows
        the new first photo, or the skin's own picture, at once."""
        paths = [str(p) for p in (paths or []) if p][:MAX_PHOTOS]
        if paths == self.paths:
            return False
        self.paths = paths
        self._decoded = {p: v for p, v in self._decoded.items() if p in paths}
        self._fitted = {}
        self._started = self._clock()
        self._shown = None
        return True

    # ---- the skin ----------------------------------------------------

    @property
    def active(self) -> bool:
        return self.frame is not None and bool(self._holders)

    def attach(self, skin: dict[str, str], meter=None, layer=None, motion=None,
               bound: tuple[int, int] | None = None) -> pygame.Rect | None:
        """Take the skin's frame and the pictures it is put into; the frame's
        rectangle, or None for a skin without one. Nothing of the previous
        skin's needs restoring: each picture is that skin's own copy."""
        self._holders = []
        self._fitted = {}
        self._shown = None
        self._bound = bound
        found = frame_of(skin)
        if found is None:
            self.frame = None
            return None
        self.frame, self.scale, self.zorder = found
        origin = (int(_number(skin.get("meter.x"))), int(_number(skin.get("meter.y"))))
        if self.zorder == "background":
            if meter is not None and getattr(meter, "bgr", None) is not None:
                self._own(meter.bgr, origin, under=False)
            if motion is not None and motion._background is not None:
                self._holders.append(Holder(motion._background, (0, 0), self.frame, under=False))
            if layer is not None and layer.background is not None:
                # What the text layer erases to; nothing repaints the frame
                # from it while a fade runs.
                self._holders.append(Holder(layer.background, (0, 0), self.frame, under=False,
                                            during_fades=False))
        elif meter is not None and getattr(meter, "fgr", None) is not None:
            self._own(meter.fgr, origin, under=True)
        if self.zorder == "overlay" and not self._holders:
            # No glass to put it under: MotionLayer's hook still draws it.
            self._holders.append(None)
        return self.frame

    def _own(self, component, origin, under: bool) -> None:
        content = component.content
        if not isinstance(content, tuple) or not isinstance(content[1], pygame.Surface):
            return
        mine = content[1].copy()
        component.content = (content[0], mine)
        self._holders.append(Holder(mine, origin, self.frame, under=under))

    # ---- drawing -----------------------------------------------------

    def tick(self, now: float | None = None) -> pygame.Rect | None:
        """Bring the frame up to date; its rectangle when its picture changed
        (the caller repaints that area), None when nothing did."""
        if not self.active:
            return None
        now = self._clock() if now is None else now
        shown, fading, p = moment(now - self._started, len(self.paths))
        # Steps 1..FADE_STEPS of the blend: the first already shows the new
        # photo a little, the last is the photo alone (then the rest state).
        step = min(FADE_STEPS, int(p * FADE_STEPS) + 1) if fading is not None else None
        state = (shown, fading, step)
        if state == self._shown:
            self._prefetch(now)
            return None
        self._shown = state
        current, old = self._photo(shown), self._photo(fading) if fading is not None else None
        for holder in self._holders:
            if holder is None:
                continue
            if fading is not None and not holder.during_fades:
                continue
            if current is None:
                holder.restore()
            elif old is None:
                holder.show([current])
            else:
                holder.show([current], old, step / FADE_STEPS)
        return self.frame.copy()

    def overlay(self, screen: pygame.Surface, area: pygame.Rect) -> None:
        """MotionLayer's hook, after the needles and before the text: an
        overlay frame's photo, as it stands."""
        if not self.active or self.zorder != "overlay" or self._shown is None:
            return
        shown, fading, step = self._shown
        current = self._photo(shown)
        if current is None:
            return
        clip = screen.get_clip()
        screen.set_clip(area.clip(self.frame))
        if fading is not None and step is not None:
            old = self._photo(fading)
            p = step / FADE_STEPS
            for item, alpha in ((old, 255 - int(255 * p)), (current, int(255 * p))):
                if item is not None:
                    item[0].set_alpha(alpha)
                    screen.blit(item[0], item[1])
                    item[0].set_alpha(None)
        else:
            screen.blit(current[0], current[1])
        screen.set_clip(clip)

    def _photo(self, index: int | None) -> tuple[pygame.Surface, pygame.Rect] | None:
        """The photo at `index`, scaled to the frame, and where it goes."""
        if index is None or index < 0 or index >= len(self.paths) or self.frame is None:
            return None
        path = self.paths[index]
        if path not in self._fitted:
            if path not in self._decoded:
                self._decoded[path] = self._load(path, self._bound)
            raw = self._decoded[path]
            if raw is None:
                self._fitted[path] = None
            else:
                spot = placed(raw.get_size(), self.frame, self.scale)
                picture = raw if raw.get_size() == spot.size else pygame.transform.smoothscale(raw, spot.size)
                self._fitted[path] = (picture, spot)
        return self._fitted[path]

    def _prefetch(self, now: float) -> None:
        """The next photo, read at half-time rather than at its fade."""
        if len(self.paths) < 2:
            return
        elapsed = now - self._started
        if elapsed % INTERVAL_S < INTERVAL_S / 2:
            return
        self._photo((int(elapsed // INTERVAL_S) + 1) % len(self.paths))

    @staticmethod
    def _read(path: str, bound: tuple[int, int] | None) -> pygame.Surface | None:
        try:
            picture = pygame.image.load(path)
            if pygame.display.get_surface() is not None:
                picture = picture.convert()
        except (pygame.error, OSError) as exc:
            logger.warning("fanart: cannot read %s: %s", path, exc)
            return None
        if bound is not None and (picture.get_width() > bound[0] or picture.get_height() > bound[1]):
            ratio = min(bound[0] / picture.get_width(), bound[1] / picture.get_height())
            picture = pygame.transform.smoothscale(
                picture, (max(1, int(picture.get_width() * ratio)), max(1, int(picture.get_height() * ratio))))
        return picture
