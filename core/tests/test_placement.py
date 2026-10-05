"""ADR-0120: where a background picture sits, by what it shows."""
from __future__ import annotations

from pathlib import Path

import pytest

from gexis_core import placement as pl

BAR = (1280, 400)
NOTHING = lambda band: 0.0  # noqa: E731 - "what stands out" is at the top


def test_a_face_is_placed_by_its_eyes_a_third_down_the_band():
    # 1920x1080 on a bar: the band is 600 picture pixels tall.
    p = pl.decide(1920, 1080, BAR, faces=[(500, 200, 580)], subject=None, salient=NOTHING)
    band = 400 / (1280 / 1920)  # 600: the screen's height in picture pixels
    top = 580 - pl.EYES_AT * 600
    assert p.how == "faces" and p.width == 1.0 and not p.skip
    assert p.y == pytest.approx(top / (1080 - band))


def test_a_face_too_big_for_the_band_is_shrunk_while_it_fills_three_quarters():
    # A 450-pixel face needs 675 with room; the band is 600: shrink to fit.
    p = pl.decide(1920, 1080, BAR, faces=[(200, 450, 380)], subject=None, salient=NOTHING)
    assert p.how == "faces, shrunk" and pl.MIN_WIDTH <= p.width < 1.0 and not p.skip


def test_a_face_far_too_big_is_skipped_rather_than_half_the_screen_blurred():
    p = pl.decide(1920, 1080, BAR, faces=[(50, 900, 400)], subject=None, salient=NOTHING)
    assert p.skip and p.how == "faces, too big"


def test_an_animal_taller_than_the_band_keeps_its_top():
    # A goose from 100 to 1000: the band starts just above its head.
    p = pl.decide(1920, 1080, BAR, faces=[], subject=(100, 1000, 0.2), salient=NOTHING)
    assert p.how == "subject" and p.y == pytest.approx((100 - 0.06 * 600) / 480)


def test_a_close_up_animal_is_shrunk_or_skipped_by_its_top_half():
    fits = pl.decide(1920, 1080, BAR, faces=[], subject=(0, 1300, 0.7), salient=NOTHING)
    assert fits.how in ("subject, shrunk", "subject, too big")
    shrunk = pl.decide(1920, 1080, BAR, faces=[], subject=(0, 1000, 0.7), salient=NOTHING)
    assert shrunk.how == "subject, shrunk" and shrunk.width >= pl.MIN_WIDTH


def test_nothing_found_follows_what_stands_out_and_a_square_picture_too():
    p = pl.decide(1920, 1080, BAR, faces=[], subject=None, salient=lambda band: 480.0)
    assert p.how == "stands out" and p.y == pytest.approx(1.0)
    square = pl.decide(1000, 1000, BAR, faces=[(100, 150, 160)], subject=None, salient=NOTHING)
    assert square.y < 0.2, "a face near the top of a square photo keeps the band at the top"


def test_without_the_models_pictures_sit_where_they_always_did(tmp_path):
    p = pl.Placer(models=tmp_path).place(b"not a picture", BAR)
    assert p == pl.Placement() and p.y == pl.DEFAULT_Y


SCRATCH = Path("/tmp/claude-1000/-home-george-projects-gexis-player/0e15ccba-1aa7-41e5-9e7f-eeee6edec5db/scratchpad/crop")


@pytest.mark.skipif(not (SCRATCH / "yolox.onnx").exists(), reason="the models are on the player, not here")
def test_the_real_models_place_a_real_picture(tmp_path):
    pytest.importorskip("cv2")
    models = tmp_path
    (models / pl.FACE_MODEL).symlink_to(SCRATCH / "yunet.onnx")
    (models / pl.SUBJECT_MODEL).symlink_to(SCRATCH / "yolox.onnx")
    placer = pl.Placer(models=models)
    artist = next((SCRATCH / "artists").glob("*.jpg"))
    assert placer.place(artist.read_bytes(), BAR).how.startswith("faces")
