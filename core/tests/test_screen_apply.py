"""ADR-0109: a chosen screen becomes screen.env and, when needed, video=."""
from __future__ import annotations

from gexis_core import screen_apply, screens
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
    assert f["cmdline"].read_text().split()[-1] == "video=HDMI-A-1:400x1280M@60"
    assert env_of(f["env"])["GEXIS_SCREEN_ID"] == "waveshare-7.9-hdmi"
    screen_apply.choose(Applied("waveshare-13.3-hdmi-h", 0), **f, now=2)
    assert "video=" not in f["cmdline"].read_text()
    assert f["cmdline"].read_text().count("\n") == 1


def test_a_choice_waits_for_keep_and_the_password_stays_fixed_until_then(tmp_path):
    """Decision 5."""
    f = files(tmp_path)
    assert not screen_apply.confirmed(f["state"])
    screen_apply.choose(Applied("waveshare-10.1-hdmi-b", 0), **f, now=1)
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
