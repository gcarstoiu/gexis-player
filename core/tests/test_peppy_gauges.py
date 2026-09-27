"""ADR-0097: progress and volume as upstream draws them - shown, never
acted on. Runs where pygame has a display (the device, or SDL's dummy)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

pygame = pytest.importorskip("pygame")

STAGE = Path(__file__).parents[2] / "image" / "stage-gexis" / "05-peppy" / "files"
sys.path.insert(0, str(STAGE))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from gexis_peppy_gauges import Gauge, arc  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def screen():
    try:
        pygame.display.init()
    except (NotImplementedError, pygame.error) as exc:
        pytest.skip(f"pygame display unavailable: {exc}")
    yield pygame.display.set_mode((1280, 800))
    pygame.display.quit()


def gauge(prefix="progress", tmp_path=Path("/nonexistent"), **keys):
    skin = {f"{prefix}.{k.replace('_', '.')}": v for k, v in keys.items()}
    return Gauge(prefix, skin, tmp_path, "", 20)


def test_a_horizontal_bar_fills_left_to_right():
    g = gauge(pos="100,50", dim="200,10", color="255,0,0", bg_color="0,0,255")
    (bar, where), = g.pieces(25)
    assert where == (100, 50)
    assert bar.get_at((10, 5))[:3] == (255, 0, 0) and bar.get_at((60, 5))[:3] == (0, 0, 255)


def test_a_tall_bar_with_no_orientation_fills_bottom_up():
    """Upstream: anything not 'horizontal' that is taller than wide."""
    g = gauge(pos="0,0", dim="10,100", color="255,0,0", bg_color="0,0,255", slider_orientation="hotizontal")
    (bar, _), = g.pieces(30)
    assert bar.get_at((5, 95))[:3] == (255, 0, 0) and bar.get_at((5, 10))[:3] == (0, 0, 255)


def test_a_tip_slides_along_its_travel_from_the_bottom(tmp_path):
    tip = pygame.Surface((10, 10), pygame.SRCALPHA)
    pygame.image.save(tip, str(tmp_path / "tip.bmp"))
    g = gauge("volume", tmp_path, pos="100,100", dim="20,200", style="slider", slider_orientation="vertical",
              slider_tip="tip.bmp", slider_travel="0,150", slider_tip_offset="-7,0")
    (_, low), = g.pieces(0)
    (_, high), = g.pieces(100)
    assert low == (100 - 7 + 5, 250) and high == (98, 100), "0 % at the travel's end, 100 % at its start"


def test_nothing_is_drawn_without_a_value_or_a_place():
    assert gauge(pos="0,0", dim="10,10").pieces(None) == []
    assert not gauge(pos="0,0").ok


def test_an_arc_fills_clockwise_from_twelve_oclock():
    """The skins' 90 / -270: a full ring behind, the fill growing clockwise."""
    g = gauge(pos="0,0", dim="100,100", style="arc", arc_angle_start="90", arc_angle_end="-270",
              arc_width="10", color="255,0,0", bg_color="0,0,255")
    back, fill = [p for p, _ in g.pieces(25)]
    assert back.get_at((50, 4))[3] > 200 and back.get_at((50, 96))[3] > 200, "the ring is whole"
    assert fill.get_at((82, 18))[3] > 200, "a quarter covers twelve to three"
    assert fill.get_at((18, 18))[3] < 50 and fill.get_at((82, 82))[3] < 50, "and nothing either side"


def test_markers_sit_on_the_bar(tmp_path):
    mark = pygame.Surface((4, 4), pygame.SRCALPHA)
    pygame.image.save(mark, str(tmp_path / "m.bmp"))
    g = gauge(tmp_path=tmp_path, pos="100,50", dim="200,10", marker_1_pos="0", marker_1_image="m.bmp",
              marker_2_pos="50", marker_2_image="m.bmp")
    places = [where for _, where in g.pieces(10)[1:]]
    assert places == [(98, 53), (198, 53)]


def test_the_arc_helper_draws_a_half_ring():
    half = arc((100, 100), (255, 255, 255), 0, 180, 10)
    assert half.get_at((50, 4))[3] > 200 and half.get_at((50, 96))[3] < 50
