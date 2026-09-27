"""ADR-0096: the 1280x720 animated packs, letterboxed into the 1280x800 panel.

`letterbox.py` ships in the image stage and runs inside the target at build
time; this reaches into that directory to import it, as `test_peppy_render`
does for the renderer."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

STAGE = Path(__file__).parents[2] / "image" / "stage-gexis" / "05-peppy" / "files"
sys.path.insert(0, str(STAGE))

from letterbox import LetterboxError, letterbox_pack, letterbox_text  # noqa: E402

SECTION = """[T]
meter.type = linear
meter.x = 0
meter.y = 0
left.y = 67
right.origin.y = 300
bgr.filename = t_bgr.png
fgr.filename = t_fgr.png
screen.bgr =
albumart.pos = 195,235
playinfo.ticker.pos = 20,638,bold
playinfo.center = True
vinyl.center = 293,334
tonearm.pivot.screen = 629,166
tonearm.pivot.image = 57,129
progress.pos = 111,683
progress.marker.2.pos = 25
albumart.dimension = 198,198
"""


def moved(text):
    out, _ = letterbox_text(text, 40)
    return dict(line.split(" = ", 1) for line in out.splitlines() if " = " in line)


def test_positions_move_down_by_the_band():
    got = moved(SECTION)
    assert got["left.y"] == "107"
    assert got["right.origin.y"] == "340"
    assert got["albumart.pos"] == "195,275"
    assert got["vinyl.center"] == "293,374"
    assert got["tonearm.pivot.screen"] == "629,206"
    assert got["progress.pos"] == "111,723"


def test_what_is_not_a_screen_position_stays():
    """A marker's `pos` is a percentage along the bar, the pivot inside the
    tonearm picture is not on the screen, `playinfo.center` is a flag, and a
    dimension is a size."""
    got = moved(SECTION)
    assert got["progress.marker.2.pos"] == "25"
    assert got["tonearm.pivot.image"] == "57,129"
    assert got["playinfo.center"] == "True"
    assert got["albumart.dimension"] == "198,198"


def test_a_font_weight_after_the_point_is_kept():
    assert moved(SECTION)["playinfo.ticker.pos"] == "20,678,bold"


def test_line_endings_comments_and_order_are_kept():
    text = "# a comment\r\n[T]\r\nmeter.x = 0\r\nalbumart.pos = 1,2\r\n; another\r\n"
    out, _ = letterbox_text(text, 40)
    assert out == "# a comment\r\n[T]\r\nmeter.x = 0\r\nalbumart.pos = 1,42\r\n; another\r\n"


def test_a_meter_away_from_the_origin_is_refused():
    """PeppyMeter adds the meter origin to a bar's bounding box twice, so the
    letterbox cannot move the origin - and a pack that already has one is not
    one this script can shift correctly."""
    with pytest.raises(LetterboxError, match="origin must be 0,0"):
        letterbox_text("[T]\nmeter.y = 280\n", 40)


def test_the_full_frame_pictures_are_named_with_their_role():
    _, pictures = letterbox_text(SECTION, 40)
    assert pictures == {"t_bgr.png": {"bgr.filename"}, "t_fgr.png": {"fgr.filename"}}


def test_a_pack_is_padded_opaque_behind_and_clear_in_front(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    source = tmp_path / "pack"
    source.mkdir()
    (source / "meters.txt").write_text(SECTION)
    Image.new("RGBA", (1280, 720), (10, 20, 30, 255)).save(source / "t_bgr.png")
    Image.new("RGBA", (1280, 720), (0, 0, 0, 0)).save(source / "t_fgr.png")

    assert letterbox_pack(source, tmp_path / "out", (1280, 720), (1280, 800)) == 2

    bgr = Image.open(tmp_path / "out" / "t_bgr.png")
    fgr = Image.open(tmp_path / "out" / "t_fgr.png")
    assert bgr.size == fgr.size == (1280, 800)
    assert bgr.getpixel((5, 5)) == (0, 0, 0, 255), "a background's band is opaque"
    assert bgr.getpixel((5, 40)) == (10, 20, 30, 255), "the picture starts at the band"
    assert fgr.getpixel((5, 5))[3] == 0, "an overlay's band is clear"
    assert (source / "t_bgr.png").exists() and Image.open(source / "t_bgr.png").size == (1280, 720), \
        "the source pack is not touched"


def test_a_picture_that_is_not_a_full_frame_is_refused(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    source = tmp_path / "pack"
    source.mkdir()
    (source / "meters.txt").write_text("[T]\nmeter.x = 0\nbgr.filename = small.png\n")
    Image.new("RGB", (400, 300)).save(source / "small.png")
    with pytest.raises(LetterboxError, match="not a full 1280x720 frame"):
        letterbox_pack(source, tmp_path / "out", (1280, 720), (1280, 800))
