"""ADR-0109, amended 2026-10-03: a new screen noticed at start."""
from __future__ import annotations

from gexis_core import screen_detect
from gexis_core import screen_watch as sw

TEN = screen_detect.Seen(connected=True, connector="HDMI-A-1", edid_maker="WAV", edid_name="WaveShare",
                         preferred=(1280, 800), usb=("0712:0010",))
THIRTEEN = screen_detect.Seen(connected=True, connector="HDMI-A-1", edid_maker="RTK", edid_name="RTK FHD",
                              preferred=(1920, 1080), usb=("2109:3431", "222a:0001"))
STRANGER = screen_detect.Seen(connected=True, connector="HDMI-A-1", edid_maker="SAM", edid_name="LS24",
                              preferred=(1920, 1080), usb=())


def test_a_player_updating_to_this_asks_nothing_and_remembers_what_is_attached(tmp_path):
    path = tmp_path / "seen.json"
    assert sw.question(TEN, headless=False, path=path) is None
    assert sw.question(TEN, headless=False, path=path) is None


def test_a_recognised_new_screen_is_asked_about_by_name(tmp_path):
    path = tmp_path / "seen.json"
    sw.kept(TEN, path)
    q = sw.question(THIRTEEN, headless=False, path=path)
    assert q["name"] == 'Waveshare 13.3" HDMI LCD (H) (1920x1080)'
    assert q["label"].startswith("Waveshare/") and q["size"] == "1920x1080"


def test_an_unknown_new_screen_is_asked_about_by_its_size(tmp_path):
    path = tmp_path / "seen.json"
    sw.kept(TEN, path)
    q = sw.question(STRANGER, headless=False, path=path)
    assert q["name"] is None and q["label"] is None and q["size"] == "1920x1080"


def test_not_now_is_remembered_for_that_screen_only(tmp_path):
    path = tmp_path / "seen.json"
    sw.kept(TEN, path)
    sw.not_now(sw.key(THIRTEEN), path)
    assert sw.question(THIRTEEN, headless=False, path=path) is None
    assert sw.question(STRANGER, headless=False, path=path) is not None


def test_a_usb_stick_is_not_a_new_screen(tmp_path):
    path = tmp_path / "seen.json"
    sw.kept(TEN, path)
    with_stick = screen_detect.Seen(**{**TEN.__dict__, "usb": ("0712:0010", "0781:5581")})
    assert sw.question(with_stick, headless=False, path=path) is None


def test_headless_and_nothing_readable_ask_nothing(tmp_path):
    path = tmp_path / "seen.json"
    sw.kept(TEN, path)
    assert sw.question(THIRTEEN, headless=True, path=path) is None
    assert sw.question(screen_detect.Seen(), headless=False, path=path) is None


def test_a_recognised_screen_is_switched_to_once_then_asked_about(tmp_path):
    # Amended 2026-10-04: switched to, not asked about - unless that switch
    # went back, when the next start asks instead of switching again.
    path = tmp_path / "seen.json"
    sw.kept(TEN, path)
    assert sw.question(THIRTEEN, headless=False, path=path)["tried"] is False
    sw.tried(sw.key(THIRTEEN), path)
    assert sw.question(THIRTEEN, headless=False, path=path)["tried"] is True


def test_keeping_a_screen_clears_what_was_tried(tmp_path):
    path = tmp_path / "seen.json"
    sw.kept(TEN, path)
    sw.tried(sw.key(THIRTEEN), path)
    sw.kept(THIRTEEN, path)
    sw.kept(TEN, path)
    assert sw.question(THIRTEEN, headless=False, path=path)["tried"] is False
