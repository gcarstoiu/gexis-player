"""ADR-0096: what moves on a turntable or a tape deck.

Runs headless via SDL's dummy driver; like `test_peppy_render`, it has to pass
on the device, where pygame is the one the renderer runs on."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

pygame = pytest.importorskip("pygame")

STAGE = Path(__file__).parents[2] / "image" / "stage-gexis" / "05-peppy" / "files"
sys.path.insert(0, str(STAGE))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from gexis_peppy_motion import MotionLayer, Spinner, Tonearm  # noqa: E402


@pytest.fixture(scope="module")
def screen():
    try:
        pygame.display.init()
    except (NotImplementedError, pygame.error) as exc:
        pytest.skip(f"pygame display unavailable: {exc}")
    yield pygame.display.set_mode((1280, 800))
    pygame.display.quit()


def arm(**kw):
    picture = pygame.Surface((100, 20), pygame.SRCALPHA)
    options = dict(pivot_screen=(600, 200), pivot_image=(90, 10), rest=0.0, start=-27.0,
                   end=-47.0, drop_s=1.0, lift_s=1.0)
    options.update(kw)
    return Tonearm(picture, **options)


def test_the_arm_drops_tracks_and_lifts(screen):
    a = arm()
    a.update(True, 0.5, 100.0, now=0.0)
    assert a.state == Tonearm.DROP
    a.update(True, 0.5, 100.0, now=0.5)
    assert a.start > a.angle > -37.0 - 0.01 or a.angle < 0, "on its way down"
    a.update(True, 0.5, 100.0, now=1.1)
    assert a.state == Tonearm.TRACKING
    a.update(True, 0.5, 100.0, now=1.2)
    assert a.angle == pytest.approx(-37.0), "halfway through the track, halfway across the grooves"
    a.update(False, 0.5, 100.0, now=2.0)
    assert a.state == Tonearm.LIFT
    a.update(False, 0.5, 100.0, now=3.1)
    assert a.state == Tonearm.REST and a.angle == 0.0


def test_the_arm_lifts_before_the_end_and_waits_for_the_next_track(screen):
    """Upstream's early lift: 1.5 s before the end, and not straight back down
    on the same track - the next one's start drops it."""
    a = arm(drop_s=0.1, lift_s=0.1)
    a.update(True, 0.0, 200.0, now=0.0)
    a.update(True, 0.0, 200.0, now=0.2)
    a.update(True, 0.99, 1.0, now=0.3)
    assert a.state == Tonearm.LIFT
    a.update(True, 0.995, 0.5, now=0.5)
    assert a.state == Tonearm.REST
    a.update(True, 0.998, 0.3, now=0.6)
    assert a.state == Tonearm.REST, "still the old track"
    a.update(True, 0.0, 200.0, now=1.0)
    assert a.state == Tonearm.DROP, "the next track"


@pytest.mark.parametrize("angle", [0.0, -27.0, -47.0, 15.0])
def test_the_pivot_stays_on_its_screen_point(screen, angle):
    """Rotated about the pivot inside the arm's picture, the pivot pixel must
    land on `tonearm.pivot.screen` whatever the angle."""
    picture = pygame.Surface((100, 20), pygame.SRCALPHA)
    picture.set_at((90, 10), (255, 0, 0, 255))
    a = Tonearm(picture, (600, 200), (90, 10), 0.0, 0.0, 0.0, 1.0, 1.0)
    a.angle = angle
    rotated, rect = a.placed()
    reds = [(x, y) for x in range(rotated.get_width()) for y in range(rotated.get_height())
            if rotated.get_at((x, y))[0] > 100 and rotated.get_at((x, y))[3] > 100]
    assert reds, "the marked pixel survives the rotation"
    x = sum(p[0] for p in reds) / len(reds) + rect.left
    y = sum(p[1] for p in reds) / len(reds) + rect.top
    assert abs(x - 600) <= 1.5 and abs(y - 200) <= 1.5


def test_a_spinner_turns_at_its_speed_and_direction(screen):
    s = Spinner(pygame.Surface((50, 50), pygame.SRCALPHA), (100, 100), rpm=33, clockwise=True)
    s.advance(1.0)
    assert s.angle == pytest.approx(198.0), "33 rpm is 198 degrees a second"
    ccw = Spinner(pygame.Surface((50, 50), pygame.SRCALPHA), (100, 100), rpm=33, clockwise=False)
    ccw.advance(1.0)
    assert ccw.angle == pytest.approx(162.0)


def test_the_disc_turns_only_while_playing(screen, tmp_path):
    # The dev box's pygame wheel cannot write PNGs (as it has no font module);
    # the device's can, and that is where this has to pass.
    if not pygame.image.get_extended():
        pytest.skip("this pygame cannot save PNG files")
    vinyl = pygame.Surface((200, 200), pygame.SRCALPHA)
    pygame.draw.circle(vinyl, (20, 20, 20, 255), (100, 100), 100)
    pygame.image.save(vinyl, str(tmp_path / "v.png"))
    background = pygame.Surface((1280, 800))
    skin = {"vinyl.filename": "v.png", "vinyl.center": "300,300", "albumart.rotation": "True",
            "albumart.rotation.speed": "33", "albumart.dimension": "80,80"}
    motion = MotionLayer(screen)
    motion.set_skin(skin, tmp_path, background)
    assert motion.active
    playing = {"transport": "playing"}
    assert motion.tick(playing, None, now=1.0), "the first frame is drawn"
    angle = motion.spinners[0].angle
    motion.tick(playing, None, now=1.2)
    assert motion.spinners[0].angle != angle, "it turned"
    angle = motion.spinners[0].angle
    assert motion.tick({"transport": "paused"}, None, now=1.5) == []
    assert motion.spinners[0].angle == angle, "and stands still when paused"


def test_a_static_skin_has_no_motion(screen, tmp_path):
    motion = MotionLayer(screen)
    motion.set_skin({"meter.type": "circular"}, tmp_path, pygame.Surface((1280, 800)))
    assert not motion.active
    assert motion.tick({"transport": "playing"}, None) == []
