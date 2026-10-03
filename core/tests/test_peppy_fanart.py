"""ADR-0112: the artist's photos in a skin's fanart frame.

`gexis_peppy_fanart` lives in the image stage beside the renderer and is
imported from there, as test_peppy_render does."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

pygame = pytest.importorskip("pygame")

STAGE = Path(__file__).parents[2] / "image" / "stage-gexis" / "05-peppy" / "files"
sys.path.insert(0, str(STAGE))

from gexis_peppy_fanart import (  # noqa: E402
    FADE_S,
    FADE_STEPS,
    INTERVAL_S,
    FanartFrame,
    frame_of,
    moment,
    placed,
)

SKIN = {"fanart.pos": "100,50", "fanart.dimension": "400,200", "fanart.scale": "fit",
        "fanart.zorder": "background"}
PHOTOS = {"wide": ((800, 200), (200, 30, 30)), "tall": ((100, 400), (30, 200, 30))}


class Component:
    def __init__(self, picture):
        self.content = ("file.png", picture)


class Meter:
    def __init__(self, bgr=None, fgr=None):
        self.bgr = Component(bgr) if bgr is not None else None
        self.fgr = Component(fgr) if fgr is not None else None


class Holds:
    """What MetadataLayer and MotionLayer give: a background surface."""

    def __init__(self, surface):
        self.background = surface
        self._background = surface


def loader(path, bound):
    size, colour = PHOTOS[path]
    picture = pygame.Surface(size)
    picture.fill(colour)
    return picture


def made(skin=SKIN, meter=None, holds=None):
    clock = [0.0]
    frame = FanartFrame(load=loader, clock=lambda: clock[0])
    frame.attach(skin, meter, holds, holds, (800, 480))
    return frame, clock


# ---- timing ---------------------------------------------------------------

def test_the_first_photo_shows_at_once_and_each_next_fades_in_over_twenty_seconds():
    assert moment(0.0, 3) == (0, None, 1.0)
    assert moment(INTERVAL_S - 0.01, 3) == (0, None, 1.0)
    shown, old, p = moment(INTERVAL_S + FADE_S / 2, 3)
    assert (shown, old) == (1, 0) and p == pytest.approx(0.5)
    assert moment(INTERVAL_S + FADE_S, 3) == (1, None, 1.0)
    # In list order, looping: the fourth step is the first photo again,
    # fading in over the last.
    shown, old, _ = moment(3 * INTERVAL_S + 0.1, 3)
    assert (shown, old) == (0, 2)


def test_one_photo_never_fades_and_none_shows_the_skin():
    assert moment(5 * INTERVAL_S + 0.2, 1) == (0, None, 1.0)
    assert moment(10.0, 0) == (-1, None, 1.0)


# ---- geometry -------------------------------------------------------------

def test_fit_keeps_the_aspect_centred_and_stretch_fills():
    frame = pygame.Rect(100, 50, 400, 200)
    assert placed((800, 200), frame, "fit") == pygame.Rect(100, 100, 400, 100)
    assert placed((100, 400), frame, "fit") == pygame.Rect(275, 50, 50, 200)
    assert placed((100, 400), frame, "stretch") == frame


def test_the_skins_keys_and_their_defaults():
    assert frame_of(SKIN) == (pygame.Rect(100, 50, 400, 200), "fit", "background")
    assert frame_of({**SKIN, "fanart.scale": "stretch", "fanart.zorder": "overlay"})[1:] == ("stretch", "overlay")
    assert frame_of({"fanart.pos": "1,1"}) is None
    assert frame_of({}) is None


# ---- where the photo goes -------------------------------------------------

def test_background_goes_into_every_picture_repainted_from_and_never_the_engines_cached_one():
    bgr = pygame.Surface((800, 480))
    bgr.fill((9, 9, 9))
    screen_bgr = pygame.Surface((800, 480))
    screen_bgr.fill((9, 9, 9))
    meter = Meter(bgr)
    frame, clock = made(meter=meter, holds=Holds(screen_bgr))
    frame.set_paths(["wide"])
    clock[0] = 1.0
    assert frame.tick() == pygame.Rect(100, 50, 400, 200)
    engine = meter.bgr.content[1]
    assert engine is not bgr, "the engine's cached surface is not drawn on"
    assert tuple(bgr.get_at((300, 150)))[:3] == (9, 9, 9)
    # fit: the wide photo is 400x100, centred: rows 100..199.
    for picture in (engine, screen_bgr):
        assert tuple(picture.get_at((300, 150)))[:3] == (200, 30, 30)
        assert tuple(picture.get_at((300, 60)))[:3] == (9, 9, 9), "the skin shows around a fitted photo"


def test_an_overlay_goes_under_the_glass():
    fgr = pygame.Surface((800, 480), pygame.SRCALPHA)
    fgr.fill((0, 0, 0, 0))
    fgr.fill((255, 255, 255, 255), (290, 140, 20, 20))     # a bit of glass
    meter = Meter(pygame.Surface((800, 480)), fgr)
    frame, clock = made({**SKIN, "fanart.zorder": "overlay"}, meter=meter)
    frame.set_paths(["wide"])
    clock[0] = 1.0
    frame.tick()
    glass = meter.fgr.content[1]
    assert tuple(glass.get_at((300, 150))) == (255, 255, 255, 255), "the glass stays over the photo"
    assert tuple(glass.get_at((200, 150))) == (200, 30, 30, 255)
    assert glass.get_at((200, 60)).a == 0, "outside the photo the meter shows through"


def test_an_empty_list_puts_the_skin_back():
    bgr = pygame.Surface((800, 480))
    bgr.fill((9, 9, 9))
    meter = Meter(bgr)
    frame, clock = made(meter=meter)
    frame.set_paths(["wide"])
    clock[0] = 1.0
    frame.tick()
    assert frame.set_paths([]) is True
    assert frame.tick() is not None
    assert tuple(meter.bgr.content[1].get_at((300, 150)))[:3] == (9, 9, 9)


def test_nothing_is_drawn_between_fades_and_a_fade_is_a_few_area_repaints():
    meter = Meter(pygame.Surface((800, 480)))
    frame, clock = made(meter=meter)
    frame.set_paths(["wide", "tall"])
    repaints = []
    t = 0.0
    while t < 2 * INTERVAL_S:
        clock[0] = t
        changed = frame.tick()
        if changed is not None:
            assert changed == pygame.Rect(100, 50, 400, 200)
            repaints.append(t)
        t += 1 / 30
    # The first photo once, then one fade of FADE_STEPS steps (and its end).
    assert len(repaints) <= FADE_STEPS + 2
    assert all(t < 0.1 or INTERVAL_S <= t <= INTERVAL_S + FADE_S + 0.05 for t in repaints)


def test_a_new_list_replaces_the_old_at_once():
    meter = Meter(pygame.Surface((800, 480)))
    frame, clock = made(meter=meter)
    frame.set_paths(["wide", "tall"])
    clock[0] = INTERVAL_S + 0.5        # mid-fade
    frame.tick()
    assert frame.set_paths(["tall"]) is True
    assert frame.set_paths(["tall"]) is False
    frame.tick()
    assert tuple(meter.bgr.content[1].get_at((300, 150)))[:3] == (30, 200, 30)


def test_a_skin_without_a_frame_draws_nothing_and_the_list_survives_a_switch():
    meter = Meter(pygame.Surface((800, 480)))
    frame, clock = made({}, meter=meter)
    frame.set_paths(["wide"])
    assert not frame.active and frame.tick() is None
    frame.attach(SKIN, meter, None, None, (800, 480))
    clock[0] = 1.0
    assert frame.tick() is not None, "the photos are shown on the next fanart skin"


def test_a_photo_is_read_once_per_list():
    reads = []

    def counting(path, bound):
        reads.append(path)
        return loader(path, bound)
    clock = [0.0]
    frame = FanartFrame(load=counting, clock=lambda: clock[0])
    meter = Meter(pygame.Surface((800, 480)))
    frame.attach(SKIN, meter, None, None, (800, 480))
    frame.set_paths(["wide", "tall"])
    for t in range(0, 90):
        clock[0] = t
        frame.tick()
    frame.attach(SKIN, Meter(pygame.Surface((800, 480))), None, None, (800, 480))   # another skin
    clock[0] = 95
    frame.tick()
    assert sorted(reads) == ["tall", "wide"]


def test_motion_layer_draws_an_overlay_after_the_needles_and_before_the_text():
    from gexis_peppy_motion import MotionLayer
    order = []

    class Layer:
        def paint(self, strata, area):
            order.append(strata[0])
    screen = pygame.Surface((100, 100))
    motion = MotionLayer(screen, Layer(), lambda area: order.append("needles"))
    motion.fanart = lambda surface, area: order.append("fanart")
    motion._background = pygame.Surface((100, 100))
    motion.compose([pygame.Rect(0, 0, 10, 10)])
    assert order == ["art", "needles", "fanart", "text", "meta"]
