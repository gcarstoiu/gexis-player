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


def test_rectangles_that_do_not_touch_are_repainted_apart(screen):
    """One rectangle round both reels of a cassette covered the title
    between them."""
    from gexis_peppy_motion import merged
    bounds = pygame.Rect(0, 0, 1280, 800)
    left, right = pygame.Rect(100, 300, 200, 200), pygame.Rect(900, 300, 200, 200)
    assert merged([left, right], bounds) == [left, right]
    touching = pygame.Rect(250, 450, 100, 100)
    assert merged([left, right, touching], bounds) == [right, left.union(touching)]
    assert merged([pygame.Rect(1200, 700, 200, 200)], bounds) == [pygame.Rect(1200, 700, 80, 100)]


class Recorder:
    """A stand-in for the text layer and the needles, noting the order."""

    def __init__(self):
        self.calls = []

    def paint(self, strata, area):
        self.calls.append(strata[0])

    def needles(self, area):
        self.calls.append("needles")


def test_a_repaint_puts_everything_back_in_upstreams_order(screen, tmp_path):
    record = Recorder()
    motion = MotionLayer(screen, record, record.needles)
    arm_picture = pygame.Surface((100, 20), pygame.SRCALPHA)
    pygame.image.save(arm_picture, str(tmp_path / "arm.bmp"))
    skin = {"reel.left.filename": "arm.bmp", "reel.left.center": "300,300",
            "reel.rotation.speed": "10", "tonearm.filename": "arm.bmp",
            "tonearm.pivot.screen": "320,300", "tonearm.pivot.image": "90,10"}
    motion.set_skin(skin, tmp_path, pygame.Surface((1280, 800)))
    assert motion.tick({"transport": "playing"}, None, now=1.0)
    assert record.calls[:4] == ["art", "needles", "text", "meta"]


def test_a_title_under_a_turning_reel_survives_the_spin(screen, tmp_path):
    """The flashing title: the spin repainted the background over it and
    nothing put it back until the next second's redraw."""
    class Title:
        def paint(self, strata, area):
            if "text" in strata:
                clip = screen.get_clip()
                screen.set_clip(area)
                screen.fill((255, 0, 0), pygame.Rect(280, 290, 40, 20))
                screen.set_clip(clip)

    reel = pygame.Surface((100, 100), pygame.SRCALPHA)
    pygame.draw.circle(reel, (0, 0, 255, 255), (50, 50), 50)
    pygame.image.save(reel, str(tmp_path / "reel.bmp"))
    motion = MotionLayer(screen, Title())
    motion.set_skin({"reel.left.filename": "reel.bmp", "reel.left.center": "300,300",
                     "reel.rotation.speed": "10"}, tmp_path, pygame.Surface((1280, 800)))
    for now in (1.0, 1.2, 1.4):
        motion.tick({"transport": "playing"}, None, now=now)
        assert screen.get_at((300, 300))[:3] == (255, 0, 0)


def test_the_record_turns_when_the_art_stays_off_it(screen, tmp_path):
    """`albumart.rotation = false` puts the art beside the record, as
    upstream reads it; it does not stop the record."""
    vinyl = pygame.Surface((200, 200), pygame.SRCALPHA)
    pygame.image.save(vinyl, str(tmp_path / "v.bmp"))
    skin = {"vinyl.filename": "v.bmp", "vinyl.center": "300,300", "albumart.rotation": "false",
            "albumart.rotation.speed": "33", "albumart.dimension": "80,80"}
    motion = MotionLayer(screen)
    motion.set_skin(skin, tmp_path, pygame.Surface((1280, 800)))
    motion.tick({"transport": "playing"}, None, now=1.0)
    angle = motion.spinners[0].angle
    motion.tick({"transport": "playing"}, None, now=1.2)
    assert motion.spinners[0].angle != angle
    assert motion._label_size is None, "and the art is not put on it"


def test_a_record_named_album_comma_theme_is_the_theme(screen, tmp_path):
    """18 turntables name their record `cdart.png,<theme>.png`: the album's
    disc art when the music folder has one, which we never see."""
    from gexis_peppy_motion import _theme
    assert _theme("cdart.png,Vertere DG1_vinyl.png") == "Vertere DG1_vinyl.png"
    assert _theme(",theme.png") == "theme.png"
    assert _theme("plain.png") == "plain.png"
    vinyl = pygame.Surface((200, 200), pygame.SRCALPHA)
    pygame.image.save(vinyl, str(tmp_path / "theme.bmp"))
    motion = MotionLayer(screen)
    motion.set_skin({"vinyl.filename": "cdart.png,theme.bmp", "vinyl.center": "300,300",
                     "albumart.rotation.speed": "33"}, tmp_path, pygame.Surface((1280, 800)))
    assert motion.spinners, "the record is there"


def _record_and_reel(tmp_path):
    picture = pygame.Surface((100, 100), pygame.SRCALPHA)
    pygame.image.save(picture, str(tmp_path / "p.bmp"))
    return {"vinyl.filename": "p.bmp", "vinyl.center": "300,300", "albumart.rotation.speed": "33",
            "reel.left.filename": "p.bmp", "reel.left.center": "800,300", "reel.rotation.speed": "25"}


def test_motion_off_stands_everything_still(screen, tmp_path):
    motion = MotionLayer(screen)
    motion.configure(False, None)
    motion.set_skin(_record_and_reel(tmp_path), tmp_path, pygame.Surface((1280, 800)))
    assert motion.tick({"transport": "playing"}, None, now=1.0), "drawn once, still"
    angles = [s.angle for s in motion.spinners]
    motion.tick({"transport": "playing"}, None, now=1.5)
    assert [s.angle for s in motion.spinners] == angles
    motion.configure(True, None)
    motion.tick({"transport": "playing"}, None, now=2.0)
    assert [s.angle for s in motion.spinners] != angles, "and turns again when it is on"


def test_record_speed_turns_the_record_and_not_the_reels(screen, tmp_path):
    motion = MotionLayer(screen)
    motion.configure(True, 45.0)
    motion.set_skin(_record_and_reel(tmp_path), tmp_path, pygame.Surface((1280, 800)))
    record, reel = motion.spinners
    assert (record.rpm, reel.rpm) == (45.0, 25.0)
    motion.configure(True, 33.0)
    assert (record.rpm, reel.rpm) == (33.0, 25.0), "changed in place, no new skin needed"


def test_smooth_redraws_whenever_the_picture_changes_and_not_otherwise(screen, tmp_path):
    """ADR-0097 decision 2: every frame the step changes, rather than 8 a
    second; a part whose picture has not moved is not redrawn."""
    picture = pygame.Surface((50, 50), pygame.SRCALPHA)
    pygame.image.save(picture, str(tmp_path / "r.bmp"))
    skin = {"reel.left.filename": "r.bmp", "reel.left.center": "300,300", "reel.rotation.speed": "33"}
    motion = MotionLayer(screen)
    motion.configure(True, None, smooth=True)
    motion.set_skin(skin, tmp_path, pygame.Surface((1280, 800)))
    playing = {"transport": "playing"}
    assert motion.tick(playing, None, now=1.0)
    # 33 rpm is 198 deg/s: 1/30 s is 6.6 deg, past a 6 deg step.
    assert motion.tick(playing, None, now=1.0 + 1 / 30), "a new step at frame rate, not held to 8 a second"
    assert motion.tick(playing, None, now=1.0 + 1 / 30 + 0.001) == [], "the same step is not redrawn"


def _picture(kind):
    """Pictures a record or a reel can be: a disc with a soft edge, of odd
    and even size, an opaque square, and a reel with spokes and holes."""
    if kind == "opaque":
        pic = pygame.Surface((180, 120))
        for x in range(0, 180, 6):
            pygame.draw.line(pic, (x, 255 - x, 90), (x, 0), (179 - x, 119))
        return pic
    size = {"soft-odd": 201, "soft-even": 200, "reel": 240}[kind]
    pic = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    if kind == "reel":
        pygame.draw.circle(pic, (90, 90, 90, 255), (c, c), c - 3)
        for a in range(0, 360, 60):
            pygame.draw.circle(pic, (0, 0, 0, 0), (int(c + 60 * __import__("math").cos(a)), int(c + 60 * __import__("math").sin(a))), 25)
        return pic
    for r in range(c, 0, -1):
        alpha = 255 if r < c - 6 else max(1, 255 - (r - (c - 6)) * 40)
        pygame.draw.circle(pic, ((r * 7) % 256, (r * 3) % 256, 200, alpha), (c, c), r)
    return pic


@pytest.mark.parametrize("kind", ["soft-odd", "soft-even", "opaque", "reel"])
def test_a_turned_frame_is_the_whole_turn_cut_to_its_reach(screen, kind):
    """Finding 134: the frames are kept cut to the picture's reach, and the
    box repainted is that reach, not the diagonal. Every step and some angles
    between must put exactly the pixels the whole turned picture did."""
    picture = _picture(kind)
    spinner = Spinner(picture, (403, 297), 33, True)
    while spinner._queue:
        spinner.build_some()
    background = pygame.Surface((800, 600))
    background.fill((30, 60, 90))
    for angle in [i * 6.0 for i in range(60)] + [1.5, 44.9, 133.3, 271.0]:
        spinner.angle = angle
        old = background.copy()
        whole = pygame.transform.rotate(picture, -(int(angle // 6) % 60) * 6)
        old.blit(whole, whole.get_rect(center=spinner.center))
        new = background.copy()
        spinner.draw(new)
        assert pygame.image.tobytes(old, "RGB") == pygame.image.tobytes(new, "RGB"), (kind, angle)
        # Every pixel the turn changed is inside the box repainted.
        changed = pygame.mask.from_threshold(old, (30, 60, 90), (1, 1, 1, 255))
        changed.invert()
        for box in changed.get_bounding_rects():
            assert spinner.region.contains(box), (kind, angle, box, spinner.region)


def test_the_box_of_a_round_record_is_its_reach_not_its_diagonal(screen):
    spinner = Spinner(_picture("soft-even"), (300, 300), 33, True)
    assert spinner.region.width <= 200 + 8, "its reach and a margin, not the diagonal (288)"
    opaque = Spinner(_picture("opaque"), (300, 300), 33, True)
    assert opaque.region.width >= 216, "an opaque picture reaches its corners"


def test_the_arm_is_turned_once_for_each_angle(screen, monkeypatch):
    """Finding 134: every repaint of every box the arm crosses turned it
    again - a tenth of the driver's time on a turntable."""
    tonearm = arm()
    turns = []
    real = pygame.transform.rotate
    monkeypatch.setattr(pygame.transform, "rotate", lambda s, a: turns.append(a) or real(s, a))
    first = tonearm.placed(-30.0)
    second = tonearm.placed(-30.0)
    assert turns == [-30.0]
    assert first[0] is second[0] and first[1] == second[1]
    second[1].move_ip(5, 5)
    assert tonearm.placed(-30.0)[1] == first[1], "the cached place is not the caller's to move"
    tonearm.placed(-31.0)
    assert turns == [-30.0, -31.0]
