"""ADR-0109: a chosen screen becomes screen.env and, when needed, video=."""
from __future__ import annotations

from gexis_core import screen_apply, screen_detect, screens
from gexis_core.screen_apply import Applied

CMDLINE = "console=serial0,115200 console=tty3 root=PARTUUID=758b8ca3-02 rootwait quiet splash\n"


def files(tmp_path):
    cmd = tmp_path / "cmdline.txt"
    cmd.write_text(CMDLINE)
    return dict(state=tmp_path / "screen.json", env=tmp_path / "screen.env", cmdline=cmd)


def env_of(path):
    return dict(l.split("=", 1) for l in path.read_text().splitlines() if l and not l.startswith("#"))


def test_the_13_3_inch_screen_is_standard_at_one_and_a_half():
    env = dict(l.split("=", 1) for l in screen_apply.env_for(screens.by_id("waveshare-13.3-hdmi-h"), 0).splitlines() if "=" in l and not l.startswith("#"))
    assert env["GEXIS_SCREEN_FAMILY"] == "standard" and env["GEXIS_SCREEN_SCALE"] == "1.5"
    assert env["GEXIS_SCREEN_TRANSFORM"] == "normal"


def test_a_bar_is_turned_and_scaled_to_400_tall():
    """Finding 100: both bars are portrait panels used sideways."""
    seven = dict(l.split("=", 1) for l in screen_apply.env_for(screens.by_id("waveshare-7.9-hdmi"), 0).splitlines() if "=" in l and not l.startswith("#"))
    assert seven["GEXIS_SCREEN_FAMILY"] == "bar" and seven["GEXIS_SCREEN_SCALE"] == "1"
    assert seven["GEXIS_SCREEN_TRANSFORM"] == "90"
    eleven = dict(l.split("=", 1) for l in screen_apply.env_for(screens.by_id("waveshare-11.9-hdmi"), 180).splitlines() if "=" in l and not l.startswith("#"))
    assert eleven["GEXIS_SCREEN_SCALE"] == "0.8" and eleven["GEXIS_SCREEN_TRANSFORM"] == "270"


def test_a_bar_s_mode_goes_on_the_kernel_s_command_line_and_comes_off_again(tmp_path):
    f = files(tmp_path)
    screen_apply.choose(Applied("waveshare-7.9-hdmi", 0), **f, now=1)
    # With the panel's orientation (George, 2026-10-04, "A"): a bar is a
    # portrait panel used turned, and the boot screens draw it so.
    assert f["cmdline"].read_text().split()[-1] == "video=HDMI-A-1:400x1280,panel_orientation=left_side_up"
    assert env_of(f["env"])["GEXIS_SCREEN_ID"] == "waveshare-7.9-hdmi"
    # Turned the other way up, the orientation follows.
    screen_apply.choose(Applied("waveshare-7.9-hdmi", 180), **f, now=1.5)
    assert f["cmdline"].read_text().split()[-1].endswith(",panel_orientation=right_side_up")
    screen_apply.choose(Applied("waveshare-13.3-hdmi-h", 0), **f, now=2)
    assert "video=" not in f["cmdline"].read_text()
    assert f["cmdline"].read_text().count("\n") == 1


def test_a_choice_waits_for_keep_and_the_password_stays_fixed_until_then(tmp_path):
    """Decision 5: the 13.3" is drawn at 1.5, which changes the picture."""
    f = files(tmp_path)
    assert not screen_apply.confirmed(f["state"])
    assert screen_apply.choose(Applied("waveshare-13.3-hdmi-h", 0), **f, now=1) is True
    assert not screen_apply.confirmed(f["state"])
    screen_apply.keep(state=f["state"])
    assert screen_apply.confirmed(f["state"])


def test_no_keep_goes_back_to_the_screen_before(tmp_path):
    f = files(tmp_path)
    screen_apply.choose(Applied("waveshare-10.1-hdmi-b", 0), **f, now=1)
    screen_apply.keep(state=f["state"])
    screen_apply.choose(Applied("waveshare-7.9-hdmi", 0), **f, now=2)
    screen_apply.revert(**f)
    assert env_of(f["env"])["GEXIS_SCREEN_ID"] == "waveshare-10.1-hdmi-b"
    assert "video=" not in f["cmdline"].read_text()
    assert screen_apply.confirmed(f["state"])


def test_at_first_setup_going_back_is_no_screen_chosen(tmp_path):
    """Decision 3: the screen's own preferred mode, and setup carries on."""
    f = files(tmp_path)
    screen_apply.choose(Applied("waveshare-7.9-hdmi", 0), **f, now=1)
    screen_apply.revert(**f)
    assert not f["env"].exists() and "video=" not in f["cmdline"].read_text()
    assert not screen_apply.confirmed(f["state"])


def test_two_choices_without_a_keep_go_back_to_the_last_kept_one(tmp_path):
    f = files(tmp_path)
    screen_apply.choose(Applied("waveshare-10.1-hdmi-b", 0), **f, now=1)
    screen_apply.keep(state=f["state"])
    screen_apply.choose(Applied("waveshare-7.9-hdmi", 0), **f, now=2)
    screen_apply.choose(Applied("waveshare-11.9-hdmi", 0), **f, now=3)
    screen_apply.revert(**f)
    assert env_of(f["env"])["GEXIS_SCREEN_ID"] == "waveshare-10.1-hdmi-b"


def test_the_question_names_the_model_and_the_one_it_goes_back_to(tmp_path):
    from gexis_core.__main__ import screen_question
    f = files(tmp_path)
    screen_apply.choose(Applied("waveshare-10.1-hdmi-b", 0), **f, now=1)
    screen_apply.keep(state=f["state"])
    screen_apply.choose(Applied("waveshare-7.9-hdmi", 0), **f, now=2)
    q = screen_question(screen_apply.read_state(f["state"]))
    assert q["model"].startswith("Waveshare 7.9") and q["previous"].startswith("Waveshare 10.1")
    assert not q["untested"] and not q["rotation_only"] and q["deadline"] is None


def test_a_rotation_only_change_asks_about_the_rotation(tmp_path):
    from gexis_core.__main__ import screen_question
    f = files(tmp_path)
    screen_apply.choose(Applied("waveshare-10.1-hdmi-b", 0), **f, now=1)
    screen_apply.keep(state=f["state"])
    screen_apply.choose(Applied("waveshare-10.1-hdmi-b", 180), **f, now=2)
    q = screen_question(screen_apply.read_state(f["state"]))
    assert q["rotation_only"] and q["previous_rotation"] == "0°"
    # George, 2026-10-04: a rotation waits two minutes, as after setup.
    assert q["total"] == 120.0


def test_a_kept_screen_asks_nothing(tmp_path):
    from gexis_core.__main__ import screen_question
    f = files(tmp_path)
    screen_apply.choose(Applied("waveshare-10.1-hdmi-b", 0), **f, now=1)
    screen_apply.keep(state=f["state"])
    assert screen_question(screen_apply.read_state(f["state"])) is None


def test_settings_name_the_screen_gone_back_to(tmp_path):
    """ADR-0109 as amended 2026-10-02: Settings no longer names a screen undone."""
    f = files(tmp_path)
    screen_apply.choose(Applied("waveshare-10.1-hdmi-b", 180), **f, now=1)
    screen_apply.keep(state=f["state"])
    screen_apply.choose(Applied("waveshare-7.9-hdmi", 0), **f, now=2)
    screen_apply.revert(**f)
    assert screen_apply.settings_of(f["state"]) == {
        "screen": screens.by_id("waveshare-10.1-hdmi-b").label, "rotation": "180°"}


def test_at_first_setup_settings_go_back_to_no_screen(tmp_path):
    f = files(tmp_path)
    assert screen_apply.settings_of(f["state"]) == {"screen": None, "rotation": None}
    screen_apply.choose(Applied("waveshare-7.9-hdmi", 0), **f, now=1)
    screen_apply.revert(**f)
    assert screen_apply.settings_of(f["state"]) == {"screen": None, "rotation": None}


def test_a_screen_that_leaves_the_picture_as_it_is_is_kept_without_asking(tmp_path):
    """ADR-0109 as amended 2026-10-02 (George: "A"): the 10.1" at its own
    mode, scale 1, unrotated - what an unchosen screen shows already."""
    f = files(tmp_path)
    assert screen_apply.choose(Applied("waveshare-10.1-hdmi-b", 0), **f, now=1) is False
    assert screen_apply.confirmed(f["state"])
    # turned over, it is a change, and it asks
    assert screen_apply.choose(Applied("waveshare-10.1-hdmi-b", 180), **f, now=2) is True
    screen_apply.revert(**f)
    assert env_of(f["env"])["GEXIS_SCREEN_TRANSFORM"] == "normal"


def test_a_forced_mode_or_a_scale_asks(tmp_path):
    f = files(tmp_path)
    assert screen_apply.choose(Applied("waveshare-7.9-hdmi", 0), **f, now=1) is True, "video= and a turn"
    screen_apply.keep(state=f["state"])
    assert screen_apply.choose(Applied("waveshare-7.9-hdmi", 0), **f, now=2) is False, "the same again"


def test_after_setup_the_question_waits_two_minutes(tmp_path):
    """ADR-0109 as amended 2026-10-02 (George: "C"): setup ends on the phone."""
    from gexis_core.__main__ import KEEP_S, SETUP_KEEP_S, screen_question

    f = files(tmp_path)
    screen_apply.choose(Applied("waveshare-13.3-hdmi-h", 0), **f, now=1, after_setup=True)
    assert screen_question(screen_apply.read_state(f["state"]))["total"] == SETUP_KEEP_S == 120
    screen_apply.choose(Applied("waveshare-7.9-hdmi", 0), **f, now=2)
    assert screen_question(screen_apply.read_state(f["state"]))["total"] == KEEP_S == 120, "every Keep waits two minutes (George, 2026-10-04)"


def test_would_ask_writes_nothing(tmp_path):
    f = files(tmp_path)
    assert screen_apply.would_ask(Applied("waveshare-13.3-hdmi-h", 0), env=f["env"], cmdline=f["cmdline"])
    assert not screen_apply.would_ask(Applied("waveshare-10.1-hdmi-b", 0), env=f["env"], cmdline=f["cmdline"])
    assert not f["env"].exists() and f["cmdline"].read_text() == CMDLINE


def test_a_bar_kept_before_gets_its_orientation_at_the_next_start(tmp_path):
    f = files(tmp_path)
    screen_apply.choose(Applied("waveshare-11.9-hdmi", 0), **f, now=1)
    screen_apply.keep(state=f["state"])
    # As a version before 2026-10-04 wrote it: the calculated mode alone.
    words = f["cmdline"].read_text().split()
    f["cmdline"].write_text(" ".join(words[:-1] + ["video=HDMI-A-1:320x1480M@60"]) + "\n")
    assert screen_apply.refresh(**f) is True
    assert f["cmdline"].read_text().split()[-1] == "video=HDMI-A-1:320x1480,panel_orientation=left_side_up"
    assert screen_apply.refresh(**f) is False, "nothing to do the second time"


def test_cmdline_txt_is_never_rewritten_in_place(tmp_path, monkeypatch):
    """Review, 2026-10-12: `write_text` truncates first, on the FAT boot
    partition, and these players are switched off at the wall (ADR-0019). A
    power cut there left a cmdline.txt with no `root=` - a Pi that does not
    boot until someone edits the card by hand. Written beside it, flushed to
    the card, then renamed over it."""
    import os
    f = files(tmp_path)
    inode = f["cmdline"].stat().st_ino
    synced, real_fsync = [], os.fsync

    def fsync(fd):
        synced.append(os.readlink(f"/proc/self/fd/{fd}"))
        real_fsync(fd)

    monkeypatch.setattr(os, "fsync", fsync)
    screen_apply.choose(Applied("waveshare-7.9-hdmi", 0), **f, now=1)
    assert f["cmdline"].stat().st_ino != inode, "a new file renamed into place"
    assert "video=HDMI-A-1:400x1280" in f["cmdline"].read_text()
    assert f["cmdline"].read_text().startswith("console=serial0")
    assert str(f["cmdline"]) + ".tmp" in synced, "the new text is on the card before the rename"
    assert str(tmp_path) in synced, "and so is the rename"
    assert not (tmp_path / "cmdline.txt.tmp").exists()


def test_a_cmdline_txt_that_cannot_be_written_is_left_as_it_was(tmp_path, monkeypatch):
    import os
    f = files(tmp_path)

    def refuse(fd):
        raise OSError(5, "Input/output error")

    monkeypatch.setattr(os, "fsync", refuse)
    try:
        screen_apply.write_files(Applied("waveshare-7.9-hdmi", 0), env=f["env"], cmdline=f["cmdline"])
    except OSError:
        pass
    assert f["cmdline"].read_text() == CMDLINE


# ADR-0109 (George, 2026-10-12: "The two bugs we need to fix now"): a screen
# laid out from its own mode is called "Other screen/W × H" in Settings, and
# that name was in no list - so *Screen rotation* on one logged "not a screen
# gexis knows" and turned nothing.

def test_a_screen_from_its_own_mode_is_found_by_the_name_settings_gives_it(tmp_path):
    f = files(tmp_path)
    screen_apply.choose(Applied("other-1920x1080", 0), **f, now=1)
    label = screen_apply.settings_of(f["state"])["screen"]
    assert label == "Other screen/1920 × 1080"
    assert screen_apply.named(label, f["state"]).id == "other-1920x1080"


def test_rotating_a_screen_from_its_own_mode_writes_the_turned_picture(tmp_path):
    f = files(tmp_path)
    screen_apply.choose(Applied("other-1920x1080", 0), **f, now=1)
    screen_apply.keep(state=f["state"])
    model = screen_apply.named(screen_apply.settings_of(f["state"])["screen"], f["state"])
    assert screen_apply.choose(Applied(model.id, 180), **f, now=2) is True
    assert env_of(f["env"])["GEXIS_SCREEN_TRANSFORM"] == "180"


def test_a_portrait_panel_used_sideways_keeps_its_turn_when_rotated(tmp_path):
    """`other-1920x1080-turned` and `other-1920x1080` share a name; the one
    in use is the one meant, so a turned panel is not straightened."""
    f = files(tmp_path)
    screen_apply.choose(Applied("other-1920x1080-turned", 0), **f, now=1)
    screen_apply.keep(state=f["state"])
    model = screen_apply.named("Other screen/1920 × 1080", f["state"])
    assert model.id == "other-1920x1080-turned"
    screen_apply.choose(Applied(model.id, 180), **f, now=2)
    assert env_of(f["env"])["GEXIS_SCREEN_TRANSFORM"] == "270"


def test_a_listed_screen_is_still_found_by_its_name(tmp_path):
    f = files(tmp_path)
    screen_apply.choose(Applied("other-1920x1080", 0), **f, now=1)
    ten = screens.by_id("waveshare-10.1-hdmi-b")
    assert screen_apply.named(ten.label, f["state"]) == ten
    assert screen_apply.named("Nobody/Nothing", f["state"]) is None
    assert screen_apply.named(None, f["state"]) is None


# ADR-0109 (George, 2026-10-12): the screen applied on the port it is on.

def test_a_state_written_before_the_connector_was_kept_reads_as_hdmi_1(tmp_path):
    """Every player before this ran its screen on HDMI-A-1: nothing to migrate."""
    f = files(tmp_path)
    screen_apply.choose(Applied("waveshare-11.9-hdmi", 0), **f, now=1)
    screen_apply.keep(state=f["state"])
    old = screen_apply.read_state(f["state"])
    for entry in ("current", "previous"):
        if old.get(entry):
            old[entry].pop("connector")
    screen_apply.write_state(old, f["state"])
    assert Applied.of(old["current"]) == Applied("waveshare-11.9-hdmi", 0, "HDMI-A-1")
    assert screen_apply.refresh(**f) is False, "the files it wrote are the files it writes"
    assert screen_apply.connector_now(screen_detect.Seen(), f["state"]) == "HDMI-A-1"
    assert screen_apply.connector_now(screen_detect.Seen(), tmp_path / "none.json") == "HDMI-A-1"


def test_a_screen_on_the_second_port_gets_its_mode_and_settings_there(tmp_path):
    f = files(tmp_path)
    screen_apply.choose(Applied("waveshare-11.9-hdmi", 0, "HDMI-A-2"), **f, now=1)
    assert f["cmdline"].read_text().split()[-1] == "video=HDMI-A-2:320x1480,panel_orientation=left_side_up"
    assert env_of(f["env"])["GEXIS_SCREEN_CONNECTOR"] == "HDMI-A-2"
    assert screen_apply.read_state(f["state"])["current"]["connector"] == "HDMI-A-2"
    seen = screen_detect.Seen(connected=True, connector="HDMI-A-2", preferred=(320, 1480))
    assert screen_apply.connector_now(seen, f["state"]) == "HDMI-A-2"
    # Back on the first port: its mode moves with it, none left behind.
    screen_apply.choose(Applied("waveshare-11.9-hdmi", 0, "HDMI-A-1"), **f, now=2)
    assert [w for w in f["cmdline"].read_text().split() if w.startswith("video=")] == [
        "video=HDMI-A-1:320x1480,panel_orientation=left_side_up"]


def test_setup_keeping_the_screen_it_applied_clears_provisional(tmp_path):
    """The bar, 2026-10-12: setup's own screen chosen again in the Screen step
    changed no setting, so it stayed provisional - and the setup network kept
    its fixed password."""
    from gexis_core import screen_apply, screens
    state = tmp_path / "screen.json"
    bar = screens.by_id("waveshare-11.9-hdmi")
    screen_apply.write_state({"current": {"screen": bar.id, "rotation": 0}, "previous": None,
                              "pending": False, "provisional": True}, state)
    assert screen_apply.confirmed(state) is False
    assert screen_apply.confirm_provisional("Some other screen", state=state) is False
    assert screen_apply.confirmed(state) is False
    assert screen_apply.confirm_provisional(bar.label, state=state) is True
    assert screen_apply.confirmed(state) is True
    assert screen_apply.confirm_provisional(bar.label, state=state) is False, "nothing left to clear"


#: Raspberry Pi OS's own config.txt, as on bedroompi (2026-10-23), the
#: comments left out: it ends in a section filter for the Pi 5, then [all].
CONFIG = """dtparam=audio=on
camera_auto_detect=1
display_auto_detect=1
auto_initramfs=1
dtoverlay=vc4-kms-v3d
max_framebuffers=2
disable_fw_kms_setup=1
arm_64bit=1
disable_overscan=1
arm_boost=1

[cm4]
otg_mode=1

[cm5]
dtoverlay=dwc2,dr_mode=host

[pi5]
dtoverlay=nospi10

[all]
disable_splash=1
"""


def dsi_files(tmp_path, config=CONFIG):
    f = files(tmp_path)
    f["config"] = tmp_path / "config.txt"
    f["config"].write_text(config)
    return f


def test_a_dsi_model_s_overlay_goes_in_our_block_and_comes_out_again(tmp_path):
    """ADR-0158 D1: the overlay the list gives, at the end under [all];
    every other line as it was; Keep asked; going back takes the block out
    and leaves the file as it was."""
    f = dsi_files(tmp_path)
    model = screens.by_id("rpi-touch2-7inch")
    assert screen_apply.choose(Applied(model.id, 0, "DSI-1"), **f, now=1), "a new picture asks Keep"
    text = f["config"].read_text()
    assert text.startswith(CONFIG.rstrip("\n")), "nothing above is touched"
    assert text.endswith(f"[all]\n{screen_apply.CONFIG_BEGIN}\ndtoverlay=vc4-kms-dsi-ili9881-7inch\n"
                         f"{screen_apply.CONFIG_END}\n")
    assert screen_apply.overlays_in(text) == ("vc4-kms-dsi-ili9881-7inch",)
    assert f["cmdline"].read_text() == CMDLINE, "a DSI panel needs no video="
    assert env_of(f["env"])["GEXIS_SCREEN_CONNECTOR"] == "DSI-1"
    screen_apply.revert(state=f["state"], env=f["env"], cmdline=f["cmdline"], config=f["config"])
    assert f["config"].read_text() == CONFIG


def test_another_dsi_model_replaces_the_block_rather_than_adding_one(tmp_path):
    f = dsi_files(tmp_path)
    screen_apply.choose(Applied("rpi-touch2-7inch", 0, "DSI-1"), **f, now=1)
    screen_apply.keep(state=f["state"])
    screen_apply.choose(Applied("waveshare-dsi-v2-10.1a", 0, "DSI-1"), **f, now=2)
    text = f["config"].read_text()
    assert text.count(screen_apply.CONFIG_BEGIN) == 1 and text.count("[all]") == 2
    assert screen_apply.overlays_in(text) == screens.by_id("waveshare-dsi-v2-10.1a").overlays


def test_a_panel_the_firmware_finds_writes_nothing(tmp_path):
    """The Hosyond and the Touch Display class: brought up by
    display_auto_detect, so config.txt is not written at all."""
    for screen_id in ("hosyond-7-dsi", screens.TOUCH_DISPLAY_CLASS):
        (tmp_path / screen_id).mkdir()
        f = dsi_files(tmp_path / screen_id)
        before = f["config"].stat().st_mtime_ns
        screen_apply.choose(Applied(screen_id, 180, "DSI-1"), **f, now=1)
        assert f["config"].read_text() == CONFIG and f["config"].stat().st_mtime_ns == before
        assert env_of(f["env"])["GEXIS_SCREEN_TRANSFORM"] == "180"


def test_an_hdmi_screen_chosen_after_a_dsi_one_takes_the_block_out(tmp_path):
    f = dsi_files(tmp_path)
    screen_apply.choose(Applied("rpi-touch2-7inch", 0, "DSI-1"), **f, now=1)
    screen_apply.keep(state=f["state"])
    screen_apply.choose(Applied("waveshare-10.1-hdmi-b", 0), **f, now=2)
    assert f["config"].read_text() == CONFIG


def test_the_overlay_is_what_only_a_restart_changes(tmp_path):
    """The boot check restarts when the boot part of the picture changes: a
    DSI model's overlay is in it, as a bar's video= is."""
    f = dsi_files(tmp_path)
    where = {k: f[k] for k in ("env", "cmdline", "config")}
    now = screen_apply.picture(**where)[0]
    assert now == (None, ())
    assert screen_apply.picture_of(Applied("rpi-touch2-7inch", 0, "DSI-1"))[0] != now
    assert screen_apply.picture_of(Applied("hosyond-7-dsi", 0, "DSI-1"))[0] == now


def test_a_dsi_model_is_applied_on_the_dsi_connector(tmp_path):
    """ADR-0158: a panel whose overlay is not written has no connector yet -
    DSI-1; one seen on another DSI connector, that one. An HDMI model goes
    where the screen is found."""
    model = screens.by_id("rpi-touch2-7inch")
    assert screen_apply.connector_for(model, ports=[]) == "DSI-1"
    seen = [screen_detect.Seen(False, "DSI-1"), screen_detect.Seen(True, "DSI-2", preferred=(800, 480))]
    assert screen_apply.connector_for(model, ports=seen) == "DSI-2"
    hdmi = screen_detect.Seen(True, "HDMI-A-2", "WAV", "WaveShare", (1280, 800))
    assert screen_apply.connector_for(screens.by_id("waveshare-10.1-hdmi-b"), seen=hdmi) == "HDMI-A-2"


def test_our_block_survives_a_file_without_a_trailing_newline(tmp_path):
    out = screen_apply.with_overlays("dtparam=audio=on", ("vc4-kms-dsi-generic",))
    assert out == f"dtparam=audio=on\n\n[all]\n{screen_apply.CONFIG_BEGIN}\ndtoverlay=vc4-kms-dsi-generic\n{screen_apply.CONFIG_END}\n"
    assert screen_apply.with_overlays(out, ()) == "dtparam=audio=on\n"
    assert screen_apply.with_overlays(screen_apply.with_overlays(out, ("a",)), ("a",)).count(screen_apply.CONFIG_BEGIN) == 1
