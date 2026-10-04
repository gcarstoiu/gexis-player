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


# ADR-0109, amended again 2026-10-04: every new screen is switched to before
# the panel starts, in its own layout, with Keep.
BAR = screen_detect.Seen(connected=True, connector="HDMI-A-1", edid_maker="WSD", edid_name="WaveShare-119",
                         preferred=(320, 1480), usb=())
MONITOR = screen_detect.Seen(connected=True, connector="HDMI-A-1", edid_maker="DEL", edid_name="U2412M",
                             preferred=(1920, 1200), usb=())


def _files(tmp_path):
    cmd = tmp_path / "cmdline.txt"
    cmd.write_text("console=tty1 root=PARTUUID=x rootwait\n")
    return dict(state=tmp_path / "screen.json", env=tmp_path / "screen.env", cmdline=cmd)


def test_what_a_new_screen_is_switched_to():
    assert sw.target(THIRTEEN).id == "waveshare-13.3-hdmi-h", "recognised"
    assert sw.target(BAR).id == "waveshare-11.9-hdmi", "the one listed bar of its mode"
    small = screen_detect.Seen(connected=True, edid_maker="ABC", edid_name="M", preferred=(1024, 768), usb=())
    assert sw.target(small).id == "other-1024x768", "a standard size names no listed panel"
    other = sw.target(MONITOR)
    assert other.id == "other-1920x1200" and other.family == "standard", "its own mode"
    turned = sw.target(screen_detect.Seen(connected=True, edid_maker="XYZ", edid_name="Tall",
                                          preferred=(400, 1600), usb=()))
    assert turned.width == 1600 and turned.family == "bar" and turned.rotation == 90, "landscape, always"


def test_a_new_screen_is_switched_to_before_the_panel_and_tried_once(tmp_path):
    path, files = tmp_path / "seen.json", _files(tmp_path)
    sw.kept(TEN, path)
    assert sw.at_start(MONITOR, headless=False, setup_needed=False, path=path, files=files) == "switched"
    env = files["env"].read_text()
    assert "GEXIS_SCREEN_ID=other-1920x1200" in env and "GEXIS_SCREEN_SCALE=1.5" in env
    # Not kept, gone back: the next start asks rather than switching again.
    from gexis_core import screen_apply
    screen_apply.revert(**files)
    assert sw.at_start(MONITOR, headless=False, setup_needed=False, path=path, files=files) == "asks"


def test_a_bar_needing_its_own_mode_restarts_first(tmp_path):
    path, files = tmp_path / "seen.json", _files(tmp_path)
    sw.kept(TEN, path)
    assert sw.at_start(BAR, headless=False, setup_needed=False, path=path, files=files) == "restart"
    assert "video=HDMI-A-1:320x1480,panel_orientation=left_side_up" in files["cmdline"].read_text()


def test_nothing_is_switched_during_setup_headless_or_for_the_same_screen(tmp_path):
    path, files = tmp_path / "seen.json", _files(tmp_path)
    sw.kept(TEN, path)
    assert sw.at_start(MONITOR, headless=False, setup_needed=True, path=path, files=files) == "same"
    assert sw.at_start(MONITOR, headless=True, setup_needed=False, path=path, files=files) == "same"
    assert sw.at_start(TEN, headless=False, setup_needed=False, path=path, files=files) == "same"
    assert not files["env"].exists()


def test_a_switch_waiting_for_keep_after_its_restart_is_left_to_the_core(tmp_path):
    # The 7.9" bar, 2026-10-04: switched, restarted for its mode, and the
    # next start found it waiting for Keep - not a screen to ask about.
    path, files = tmp_path / "seen.json", _files(tmp_path)
    sw.kept(TEN, path)
    assert sw.at_start(BAR, headless=False, setup_needed=False, path=path, files=files) == "restart"
    assert sw.at_start(BAR, headless=False, setup_needed=False, path=path, files=files) == "pending"
