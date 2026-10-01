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

from letterbox import LetterboxError, letterbox_pack, letterbox_spectrum_text, letterbox_text  # noqa: E402

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


OFF_CORNER = """[M]
meter.type = circular
meter.x = 147
meter.y = 280
left.origin.y = 100
bgr.filename = m_bgr.png
fgr.filename = m_fgr.png
screen.bgr = m.jpg
albumart.pos = 10,20
"""


def test_a_meter_away_from_the_corner_moves_by_its_origin():
    """ADR-0111 decision 15. Everything drawn relative to the meter goes
    with `meter.y`, so its own positions stay; the screen's positions move."""
    out, pictures = letterbox_text(OFF_CORNER, 40)
    got = dict(line.split(" = ", 1) for line in out.splitlines() if " = " in line)
    assert got["meter.y"] == "320" and got["meter.x"] == "147"
    assert got["left.origin.y"] == "100", "meter-relative: moves with the origin"
    assert got["albumart.pos"] == "10,60"
    assert pictures == {"m.jpg": {"screen.bgr"}}, "only the whole frame is padded"


def test_a_meter_at_the_corner_drawn_on_a_strip_moves_by_its_origin_too():
    """A `bgr` that is not a whole frame cannot be padded into one; the
    section is told to move by its origin instead."""
    text = "[S]\nmeter.x = 0\nmeter.y = 0\nleft.y = 67\nbgr.filename = strip.png\n"
    out, pictures = letterbox_text(text, 40, moved={"S"})
    assert "meter.y = 40" in out and "left.y = 67" in out
    assert pictures == {}


def test_a_moved_section_must_have_a_meter_y():
    with pytest.raises(LetterboxError, match="no meter.y"):
        letterbox_text("[T]\nmeter.x = 5\n", 40)


def test_a_spectrum_moves_by_its_position_only():
    text = "[Free]\r\norigin.x = 84\r\norigin.y = 140\r\nspectrum.x = 342\r\nspectrum.y = 384\r\nbgr.filename = F.png\r\n"
    assert letterbox_spectrum_text(text, 40) == text.replace("spectrum.y = 384", "spectrum.y = 424")
    with pytest.raises(LetterboxError, match="without spectrum.y"):
        letterbox_spectrum_text("[S]\nspectrum.x = 1\n", 40)


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


def test_a_strip_at_the_corner_is_left_as_it_is_and_its_meter_moved(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    source = tmp_path / "pack"
    source.mkdir()
    (source / "meters.txt").write_text("[T]\nmeter.x = 0\nmeter.y = 0\nleft.y = 67\nbgr.filename = small.png\n")
    Image.new("RGB", (400, 300)).save(source / "small.png")
    assert letterbox_pack(source, tmp_path / "out", (1280, 720), (1280, 800)) == 0
    assert Image.open(tmp_path / "out" / "small.png").size == (400, 300)
    text = (tmp_path / "out" / "meters.txt").read_text()
    assert "meter.y = 40" in text and "left.y = 67" in text


def test_a_screen_background_that_is_not_a_frame_is_still_refused(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    source = tmp_path / "pack"
    source.mkdir()
    (source / "meters.txt").write_text("[T]\nmeter.x = 3\nmeter.y = 3\nscreen.bgr = small.png\n")
    Image.new("RGB", (400, 300)).save(source / "small.png")
    with pytest.raises(LetterboxError, match="not a full 1280x720 frame"):
        letterbox_pack(source, tmp_path / "out", (1280, 720), (1280, 800))


def test_a_spectrum_folder_alone_is_letterboxed(tmp_path):
    source = tmp_path / "pack"
    source.mkdir()
    (source / "spectrum.txt").write_text("[S]\nspectrum.x = 1\nspectrum.y = 2\nbgr.filename = s.png\n")
    (source / "s.png").write_bytes(b"not opened")
    assert letterbox_pack(source, tmp_path / "out", (1280, 720), (1280, 800)) == 0
    assert "spectrum.y = 42" in (tmp_path / "out" / "spectrum.txt").read_text()
    assert (tmp_path / "out" / "s.png").read_bytes() == b"not opened"
    assert not (tmp_path / "out" / "meters.txt").exists()


def test_a_frame_taller_than_the_screen_is_cut_to_it_before_padding(tmp_path):
    """`1280x720_g5_701_meters` draws a 1280x743 background at 0,0: the 23
    rows below the screen were never seen, and must not fill the lower band."""
    Image = pytest.importorskip("PIL.Image")
    source = tmp_path / "pack"
    source.mkdir()
    (source / "meters.txt").write_text("[T]\nmeter.x = 5\nmeter.y = 5\nscreen.bgr = tall.png\n")
    tall = Image.new("RGB", (1280, 743), (200, 0, 0))
    tall.paste((0, 200, 0), (0, 720, 1280, 743))
    tall.save(source / "tall.png")
    assert letterbox_pack(source, tmp_path / "out", (1280, 720), (1280, 800)) == 1
    out = Image.open(tmp_path / "out" / "tall.png")
    assert out.size == (1280, 800)
    assert out.getpixel((5, 759)) == (200, 0, 0) and out.getpixel((5, 770)) == (0, 0, 0)
