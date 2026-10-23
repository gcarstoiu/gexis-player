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


def test_nothing_is_switched_headless_or_for_the_same_screen(tmp_path):
    path, files = tmp_path / "seen.json", _files(tmp_path)
    sw.kept(TEN, path)
    assert sw.at_start(MONITOR, headless=True, setup_needed=False, path=path, files=files) == "same"
    assert sw.at_start(TEN, headless=False, setup_needed=False, path=path, files=files) == "same"
    assert not files["env"].exists()


# ADR-0109 amended 2026-10-07 (George, the 13.3" on a fresh card: "The QR codes
# on the screen were skewed to the left"): during setup too, provisionally.

def test_during_setup_the_screen_is_laid_out_for_setup_without_keep(tmp_path):
    from gexis_core import screen_apply
    path, files = tmp_path / "seen.json", _files(tmp_path)
    assert sw.at_start(THIRTEEN, headless=False, setup_needed=True, path=path, files=files) == "switched"
    env = files["env"].read_text()
    assert "GEXIS_SCREEN_ID=waveshare-13.3-hdmi-h" in env and "GEXIS_SCREEN_SCALE=1.5" in env
    state = screen_apply.read_state(files["state"])
    assert state["provisional"] and not state["pending"], "no Keep: setup's Screen step asks"
    assert not screen_apply.confirmed(files["state"]), "the setup network keeps its fixed password"


def test_during_setup_it_is_applied_once(tmp_path):
    path, files = tmp_path / "seen.json", _files(tmp_path)
    assert sw.at_start(STRANGER, headless=False, setup_needed=True, path=path, files=files) == "switched"
    assert "GEXIS_SCREEN_ID=other-1920x1080" in files["env"].read_text(), "its own mode, scale only"
    assert sw.at_start(STRANGER, headless=False, setup_needed=True, path=path, files=files) == "same"


def test_during_setup_a_bar_is_turned_and_restarts_first(tmp_path):
    path, files = tmp_path / "seen.json", _files(tmp_path)
    assert sw.at_start(BAR, headless=False, setup_needed=True, path=path, files=files) == "restart"
    assert "video=HDMI-A-1:320x1480,panel_orientation=left_side_up" in files["cmdline"].read_text()


def test_during_setup_no_screen_attached_changes_nothing(tmp_path):
    path, files = tmp_path / "seen.json", _files(tmp_path)
    nothing = screen_detect.Seen(connected=False)
    assert sw.at_start(nothing, headless=False, setup_needed=True, path=path, files=files) == "same"
    assert not files["env"].exists()


def test_setups_screen_step_confirms_the_provisional_screen(tmp_path):
    from gexis_core import screen_apply
    path, files = tmp_path / "seen.json", _files(tmp_path)
    sw.at_start(THIRTEEN, headless=False, setup_needed=True, path=path, files=files)
    asks = screen_apply.choose(screen_apply.Applied("waveshare-13.3-hdmi-h", 0), after_setup=True, **files)
    assert asks is False, "the same picture: kept without asking"
    assert screen_apply.confirmed(files["state"])


def test_a_switch_waiting_for_keep_after_its_restart_is_left_to_the_core(tmp_path):
    # The 7.9" bar, 2026-10-04: switched, restarted for its mode, and the
    # next start found it waiting for Keep - not a screen to ask about.
    path, files = tmp_path / "seen.json", _files(tmp_path)
    sw.kept(TEN, path)
    assert sw.at_start(BAR, headless=False, setup_needed=False, path=path, files=files) == "restart"
    assert sw.at_start(BAR, headless=False, setup_needed=False, path=path, files=files) == "pending"


# ADR-0109 (George, 2026-10-12: "The two bugs we need to fix now"): the screen
# was taken to be on HDMI-A-1 whichever port it was plugged into - its mode,
# touch and standby all went to the first port.

from dataclasses import replace as _on  # noqa: E402


def _env(path):
    return dict(l.split("=", 1) for l in path.read_text().splitlines() if l and not l.startswith("#"))


def test_a_new_screen_on_the_second_port_is_applied_there(tmp_path):
    path, files = tmp_path / "seen.json", _files(tmp_path)
    sw.kept(TEN, path)
    assert sw.at_start(_on(BAR, connector="HDMI-A-2"), headless=False, setup_needed=False,
                       path=path, files=files) == "restart"
    words = files["cmdline"].read_text().split()
    assert "video=HDMI-A-2:320x1480,panel_orientation=left_side_up" in words
    assert not any(w.startswith("video=HDMI-A-1") for w in words)
    assert _env(files["env"])["GEXIS_SCREEN_CONNECTOR"] == "HDMI-A-2"


def test_during_setup_the_screen_on_the_second_port_is_laid_out_there(tmp_path):
    path, files = tmp_path / "seen.json", _files(tmp_path)
    assert sw.at_start(_on(BAR, connector="HDMI-A-2"), headless=False, setup_needed=True,
                       path=path, files=files) == "restart"
    assert "video=HDMI-A-2:320x1480,panel_orientation=left_side_up" in files["cmdline"].read_text().split()
    assert _env(files["env"])["GEXIS_SCREEN_CONNECTOR"] == "HDMI-A-2"


def test_a_bar_moved_to_the_other_port_takes_its_mode_there_and_asks_keep(tmp_path):
    """A change of picture - the `video=` moves - so the existing Keep flow:
    the restart for the kernel's mode first, then the question."""
    from gexis_core import screen_apply
    from gexis_core.__main__ import screen_question
    path, files = tmp_path / "seen.json", _files(tmp_path)
    sw.kept(BAR, path)
    screen_apply.choose(screen_apply.Applied("waveshare-11.9-hdmi", 0), **files, now=1)
    screen_apply.keep(state=files["state"])
    assert sw.at_start(_on(BAR, connector="HDMI-A-2"), headless=False, setup_needed=False,
                       path=path, files=files) == "restart"
    words = files["cmdline"].read_text().split()
    assert [w for w in words if w.startswith("video=")] == ["video=HDMI-A-2:320x1480,panel_orientation=left_side_up"]
    state = screen_apply.read_state(files["state"])
    assert state["pending"] and state["current"]["connector"] == "HDMI-A-2"
    q = screen_question(state)
    assert not q["rotation_only"], "the same screen on another port is not a rotation"
    # Not kept: back to the port before, and the next start tries again.
    screen_apply.revert(**files)
    assert "video=HDMI-A-1:320x1480,panel_orientation=left_side_up" in files["cmdline"].read_text().split()
    assert sw.at_start(_on(BAR, connector="HDMI-A-2"), headless=False, setup_needed=False,
                       path=path, files=files) == "restart"


def test_a_screen_without_its_own_mode_moves_port_without_asking(tmp_path):
    """Nothing the screen shows changes - only which output touch and standby
    go to - so it is kept, and the panel starts on it without a restart."""
    from gexis_core import screen_apply
    path, files = tmp_path / "seen.json", _files(tmp_path)
    sw.kept(THIRTEEN, path)
    screen_apply.choose(screen_apply.Applied("waveshare-13.3-hdmi-h", 0), **files, now=1)
    screen_apply.keep(state=files["state"])
    assert sw.at_start(_on(THIRTEEN, connector="HDMI-A-2"), headless=False, setup_needed=False,
                       path=path, files=files) == "switched"
    assert _env(files["env"])["GEXIS_SCREEN_CONNECTOR"] == "HDMI-A-2"
    assert screen_apply.confirmed(files["state"])
    assert sw.at_start(_on(THIRTEEN, connector="HDMI-A-2"), headless=False, setup_needed=False,
                       path=path, files=files) == "same", "once"


def test_a_screen_off_at_the_start_keeps_the_port_applied_last(tmp_path):
    from gexis_core import screen_apply
    path, files = tmp_path / "seen.json", _files(tmp_path)
    sw.kept(THIRTEEN, path)
    screen_apply.choose(screen_apply.Applied("waveshare-13.3-hdmi-h", 0, "HDMI-A-2"), **files, now=1)
    screen_apply.keep(state=files["state"])
    nothing = screen_detect.Seen(connected=False)
    assert sw.at_start(nothing, headless=False, setup_needed=False, path=path, files=files) == "same"
    assert _env(files["env"])["GEXIS_SCREEN_CONNECTOR"] == "HDMI-A-2"
    assert screen_apply.connector_now(nothing, files["state"]) == "HDMI-A-2"
    assert sw.at_start(_on(THIRTEEN, connector="HDMI-A-2"), headless=True, setup_needed=False,
                       path=path, files=files) == "same"


# ADR-0158: a DSI panel has no EDID; it is told apart by its port and its
# controller, and recognised as the Touch Display class.
DSI_PANEL = screen_detect.Seen(connected=True, connector="DSI-1", preferred=(800, 480),
                               panel=("edt_ft5x06", "rpi_touchscreen_attiny"))
HOSYOND_5 = screen_detect.Seen(connected=True, connector="HDMI-A-1", edid_maker="HSD", edid_name="HDMI",
                               preferred=(800, 480), usb=())


def test_a_dsi_panel_has_a_key_without_an_edid():
    assert sw.key(DSI_PANEL) == ["DSI", "rpi_touchscreen_attiny", "800x480"]
    other = screen_detect.Seen(connected=True, connector="DSI-1", preferred=(1280, 800), panel=("goodix",))
    assert sw.key(other) == ["DSI", None, "1280x800"], "another kind of DSI panel is a different screen"


def test_bedroompi_s_next_start_switches_to_the_dsi_panel_and_asks_keep(tmp_path):
    """bedroompi, 2026-10-23: a Hosyond 5" HDMI kept long ago, the HMTECH 7"
    HDMI chosen in Settings while the DSI panel was on the ribbon. The next
    start sees the DSI panel, switches to the class on DSI-1 - no overlay to
    write, so no restart - and asks Keep on the panel."""
    import json
    from gexis_core import screen_apply, screens
    path = tmp_path / "seen.json"
    files = _files(tmp_path)
    files["config"] = tmp_path / "config.txt"
    files["config"].write_text("display_auto_detect=1\n")
    sw.kept(HOSYOND_5, path)
    screen_apply.write_state({"current": {"screen": "hmtech-7-hdmi", "rotation": 180, "connector": "HDMI-A-1"},
                              "previous": None, "pending": False}, files["state"])
    outcome = sw.at_start(DSI_PANEL, headless=False, setup_needed=False, path=path, files=files)
    assert outcome == "switched"
    state = json.loads(files["state"].read_text())
    assert state["current"]["screen"] == screens.TOUCH_DISPLAY_CLASS and state["current"]["connector"] == "DSI-1"
    assert state["pending"] is True, "Keep this screen? on the panel"
    assert files["config"].read_text() == "display_auto_detect=1\n"
    env = dict(l.split("=", 1) for l in files["env"].read_text().splitlines() if l and not l.startswith("#"))
    assert env["GEXIS_SCREEN_CONNECTOR"] == "DSI-1" and env["GEXIS_SCREEN_SCALE"] == "0.625"


def test_a_dsi_panel_kept_is_the_same_screen_at_the_next_start(tmp_path):
    path = tmp_path / "seen.json"
    sw.kept(DSI_PANEL, path)
    assert sw.question(DSI_PANEL, headless=False, path=path) is None
