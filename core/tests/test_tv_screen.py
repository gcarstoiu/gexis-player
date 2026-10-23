"""ADR-0147: a TV as the screen, by choosing its port (George, 2026-10-13).

On sofapi, the LG TV chosen under Screen port on HDMI 2 went back to the panel
on HDMI 1 at every start. Decided: the choice wins (D1), Keep is answered from
the phone on a screen without touch (D3), a TV runs at 1920x1080 at most
(D4), and the panel left on the other port has its touch switched off (D5)."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from unittest import mock

import pytest

from gexis_core import screen_apply, screen_detect, screens
from gexis_core.screen_apply import Applied

from test_screen_detect import EDID, _receiver_edid, two_ports

FILES = Path(__file__).resolve().parents[2] / "image" / "stage-gexis" / "04-ui" / "files"


# --- D4: 1920 x 1080 at most ------------------------------------------------

@pytest.mark.parametrize("native", [(3840, 2160), (2560, 1440)])
def test_a_larger_16_9_screen_is_run_at_1080p_by_a_kernel_mode(native):
    s = screens.fitted(*native)
    assert s.id == "other-1920x1080-capped" and (s.width, s.height) == (1920, 1080)
    assert screen_apply.video_for(s, "HDMI-A-2") == "video=HDMI-A-2:1920x1080"
    assert screens.by_id(s.id) == s, "the name gives the same screen back"


@pytest.mark.parametrize("native", [(1920, 1080), (1280, 800), (3440, 1440), (800, 1280)])
def test_anything_else_keeps_its_own_mode(native):
    s = screens.fitted(*native)
    assert not s.id.endswith("-capped") and s.video_mode is None


# --- D1: the choice wins ----------------------------------------------------

def test_a_port_chosen_holds_over_a_known_panel_on_the_other(tmp_path, monkeypatch):
    """The panel on HDMI 1, the TV chosen on HDMI 2."""
    drm, usb = two_ports(tmp_path, EDID, _receiver_edid())
    monkeypatch.setattr(screen_detect, "_applied_connector", lambda: "HDMI-A-2")
    monkeypatch.setattr(screen_detect, "_chosen_connector", lambda: None)
    assert screen_detect.seen(drm, usb).connector == "HDMI-A-1", "found, not chosen: the panel"
    monkeypatch.setattr(screen_detect, "_chosen_connector", lambda: "HDMI-A-2")
    assert screen_detect.seen(drm, usb).connector == "HDMI-A-2"


def test_a_port_chosen_with_nothing_on_it_lets_the_panel_be_found(tmp_path, monkeypatch):
    drm, usb = two_ports(tmp_path, EDID, None)
    monkeypatch.setattr(screen_detect, "_chosen_connector", lambda: "HDMI-A-2")
    assert screen_detect.seen(drm, usb).connector == "HDMI-A-1"


def test_the_choice_is_kept_in_screen_json_and_read_back(tmp_path):
    a = Applied("other-1920x1080-capped", 0, "HDMI-A-2", chosen=True)
    assert Applied.of(a.to_json()) == a
    plain = Applied("waveshare-10.1-hdmi-b", 0, "HDMI-A-1")
    assert "chosen" not in plain.to_json() and Applied.of(plain.to_json()) == plain


def test_choosing_the_tv_asks_keep_and_going_back_forgets_the_choice(tmp_path):
    f = {"state": tmp_path / "screen.json", "env": tmp_path / "screen.env", "cmdline": tmp_path / "cmdline.txt"}
    f["cmdline"].write_text("console=tty1\n")
    screen_apply.choose(Applied("waveshare-10.1-hdmi-b", 0, "HDMI-A-1"), **f, now=1)
    screen_apply.keep(state=f["state"])
    asks = screen_apply.choose(Applied("other-1920x1080-capped", 0, "HDMI-A-2", chosen=True), **f, now=2)
    assert asks, "a new mode and scale: Keep is asked"
    assert "video=HDMI-A-2:1920x1080" in f["cmdline"].read_text()
    screen_apply.revert(state=f["state"], env=f["env"], cmdline=f["cmdline"])
    current = screen_apply.read_state(f["state"])["current"]
    assert current["connector"] == "HDMI-A-1" and not current.get("chosen")


def test_a_rotation_or_model_change_on_a_chosen_tv_keeps_it_chosen(tmp_path):
    """Finding 125 #7 (2026-10-14): the LG TV chosen on HDMI 2, the panel on
    HDMI 1. A rotation, or another model under Attached screen, rebuilt the
    screen without the chosen mark; at the next start the panel's port won
    and the TV's settings were moved onto it."""
    f = {"state": tmp_path / "screen.json", "env": tmp_path / "screen.env", "cmdline": tmp_path / "cmdline.txt"}
    f["cmdline"].write_text("console=tty1\n")
    screen_apply.choose(Applied("other-1920x1080-capped", 0, "HDMI-A-2", chosen=True), **f, now=1)
    screen_apply.keep(state=f["state"])
    applied = screen_apply.applied_on("other-1920x1080-capped", 180, "HDMI-A-2", state=f["state"])
    assert applied == Applied("other-1920x1080-capped", 180, "HDMI-A-2", chosen=True)
    screen_apply.choose(applied, **f, now=2)
    assert screen_apply.read_state(f["state"])["current"]["chosen"] is True
    # Another model on the chosen port is still the choice of that port.
    assert screen_apply.applied_on("other-1280x720", 0, "HDMI-A-2", state=f["state"]).chosen
    # On another port it is not: the choice was of HDMI 2.
    assert not screen_apply.applied_on("waveshare-10.1-hdmi-b", 0, "HDMI-A-1", state=f["state"]).chosen
    # Nothing chosen before, nothing chosen now.
    screen_apply.write_state({"current": Applied("waveshare-10.1-hdmi-b", 0, "HDMI-A-1").to_json()}, f["state"])
    assert not screen_apply.applied_on("waveshare-10.1-hdmi-b", 90, "HDMI-A-1", state=f["state"]).chosen


def test_attached_screen_and_rotation_carry_the_port_choice():
    """Finding 125 #7: the Settings handler builds its screen through it -
    on the connector for the model (ADR-0158: a DSI model on DSI)."""
    from test_main_wiring import _closure
    choose = _closure("_choose_screen")
    assert "screen_apply.applied_on(model.id, turn, screen_apply.connector_for(model))" in choose


# --- D3: Keep from the phone on a screen without touch ----------------------

def test_only_a_screen_without_known_touch_is_answered_from_the_phone():
    assert screen_detect.has_touch("waveshare-10.1-hdmi-b")
    assert not screen_detect.has_touch("other-1920x1080-capped")


def test_a_panel_kept_under_its_old_cased_name_still_has_its_touch(tmp_path):
    """Finding 125 #8 (2026-10-14): a 10.1" (B) kept before the cased presets
    were merged into their panels has `waveshare-10.1-hdmi-b-case` in
    screen.json. Read raw, it had no fingerprint: its own touch was ignored
    by udev at every start and Keep went to the phone."""
    from gexis_core import screen_watch
    from gexis_core.__main__ import screen_question
    assert screen_detect.has_touch("waveshare-10.1-hdmi-b-case")
    state, rules = tmp_path / "screen.json", tmp_path / "rules" / "90.rules"
    screen_apply.write_state({"current": {"screen": "waveshare-10.1-hdmi-b-case", "rotation": 0,
                                          "connector": "HDMI-A-1"}}, state)
    assert screen_watch.touch_rules(state, rules, run=lambda args, check=False: None) == []
    assert not rules.exists()
    question = screen_question({"pending": True, "current": {"screen": "waveshare-10.1-hdmi-b-case",
                                                             "rotation": 180, "connector": "HDMI-A-1"}})
    assert question["phone"] is False and question["panel_buttons"] is True


@pytest.mark.parametrize("screen_id", ["waveshare-7.9-hdmi", "btt-hdmi7-v1.2", "geeekpi-7-hdmi"])
def test_a_listed_touch_panel_without_a_fingerprint_has_touch(tmp_path, screen_id):
    """Finding 125 #9 and #11 (2026-10-14): only the three fingerprinted
    models counted as touch, so the tested 7.9" bar and every other listed
    touch panel had Keep sent to the phone, its buttons hidden, and the
    known panels' touch ids ignored by udev while it was in use."""
    from gexis_core import screen_watch
    from gexis_core.__main__ import screen_question
    assert screen_detect.has_touch(screen_id)
    state, rules = tmp_path / "screen.json", tmp_path / "rules" / "90.rules"
    current = {"screen": screen_id, "rotation": 0, "connector": "HDMI-A-1"}
    screen_apply.write_state({"current": current}, state)
    assert screen_watch.touch_rules(state, rules, run=lambda args, check=False: None) == []
    assert screen_question({"pending": True, "current": current})["panel_buttons"] is True
    assert screen_apply.panels_off(screen_id, "HDMI-A-1", []) == []


# --- Who answers Keep: the panel, the phone, or both (Finding 125, 2026-10-14) -

def _question(screen_id):
    from gexis_core.__main__ import screen_question
    return screen_question({"pending": True, "current": {"screen": screen_id, "rotation": 0,
                                                         "connector": "HDMI-A-1"}})


@pytest.mark.parametrize("screen_id", ["waveshare-10.1-hdmi-b", "waveshare-13.3-hdmi-h",
                                       "waveshare-11.9-hdmi", "waveshare-10.1-hdmi-b-case"])
def test_a_fingerprinted_panel_is_answered_on_itself_only(screen_id):
    """ADR-0109 decision 2: its USB touch is known, so a touch there proves
    the picture and the touch; the phone may not answer."""
    q = _question(screen_id)
    assert q["panel_buttons"] is True and q["phone"] is False
    assert _answer(q, "192.168.1.20")[0] == 403
    assert _answer(q, "127.0.0.1") == (200, ["keep"])


@pytest.mark.parametrize("screen_id", ["waveshare-7.9-hdmi", "btt-hdmi7-v1.2", "geeekpi-7-hdmi"])
def test_a_listed_panel_not_fingerprinted_is_answered_on_itself_or_the_phone(screen_id):
    """Finding 125 (2026-10-14): many listed panels need an SPI ads7846
    overlay or a goodtft driver the player never installs, so their touch
    may not work; with the buttons only on the panel, a panel whose touch is
    dead could only wait for the countdown. Its buttons are shown and the
    phone may answer too."""
    q = _question(screen_id)
    assert q["panel_buttons"] is True and q["phone"] is True
    assert _answer(q, "192.168.1.20") == (200, ["keep"])
    assert _answer(q, "127.0.0.1") == (200, ["keep"])


@pytest.mark.parametrize("screen_id", ["other-1920x1080-capped", "generic-1080p", "hmtech-7-hdmi",
                                       "no-such-screen"])
def test_a_screen_without_touch_is_answered_from_the_phone_only(screen_id):
    """A TV, a generic monitor mode, a model whose maker says it has no
    touch: no buttons on it (nothing can press them), the phone answers."""
    q = _question(screen_id)
    assert q["panel_buttons"] is False and q["phone"] is True
    assert _answer(q, "192.168.1.20") == (200, ["keep"])


@pytest.mark.parametrize("screen_id", ["other-1920x1080-capped", "other-1280x800", "generic-1080p",
                                       "hmtech-7-hdmi", "no-such-screen"])
def test_a_screen_known_to_have_no_touch_is_still_answered_from_the_phone(screen_id):
    """A TV or a screen in no list, a generic monitor mode, and a listed
    model its maker says has no touch."""
    assert not screen_detect.has_touch(screen_id)


def test_the_question_says_the_phone_answers_for_a_tv(tmp_path):
    from gexis_core.__main__ import screen_question
    state = {"pending": True, "current": {"screen": "other-1920x1080-capped", "rotation": 0,
                                          "connector": "HDMI-A-2", "chosen": True},
             "previous": {"screen": "waveshare-10.1-hdmi-b", "rotation": 0, "connector": "HDMI-A-1"}}
    assert screen_question(state)["phone"] is True
    state["current"] = state["previous"]
    assert screen_question(state)["phone"] is False


def _answer(confirm, remote, action="keep"):
    from aiohttp.test_utils import make_mocked_request
    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer
    import asyncio

    store = StateStore({})
    store.set_screen_confirm(confirm)
    answered = []

    async def screen_answer(action):
        answered.append(action)
        return {"ok": True}

    server = StateServer(store, screen_answer=screen_answer)
    transport = mock.Mock()
    transport.get_extra_info.side_effect = lambda name, default=None: (remote, 40000) if name == "peername" else default
    request = make_mocked_request("POST", f"/screen/{action}", match_info={"action": action}, transport=transport)
    response = asyncio.run(server._handle_screen_answer(request))
    return response.status, answered


def test_a_phone_answers_keep_for_a_tv_and_not_for_a_panel():
    assert _answer({"model": "LG TV", "phone": True}, "192.168.1.20") == (200, ["keep"])
    assert _answer({"model": "Waveshare 10.1", "phone": False}, "192.168.1.20")[0] == 403
    assert _answer({"model": "Waveshare 10.1", "phone": False}, "127.0.0.1") == (200, ["keep"])


def test_only_the_panel_says_the_question_is_shown():
    """George, 2026-10-14: the countdown starts with the Keep screen
    displayed - which only the panel can say, a TV's question included."""
    assert _answer({"model": "Waveshare 11.9", "phone": False}, "127.0.0.1", "shown") == (200, ["shown"])
    assert _answer({"model": "LG TV", "phone": True}, "192.168.1.20", "shown")[0] == 403


# --- D4 as amended: the TV's mode from its own list --------------------------

def _modes(tmp_path, connector, lines):
    d = tmp_path / "drm" / f"card1-{connector}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "modes").write_text("\n".join(lines) + "\n")
    return tmp_path / "drm"


def test_a_tv_through_a_receiver_is_run_at_1080p_from_its_list(tmp_path):
    """sofapi's LG TV through the Sony receiver: the EDID's first timing was
    640 x 480 at the choice, 1280 x 720 later; the list holds 1920 x 1080."""
    drm = _modes(tmp_path, "HDMI-A-2", ["1280x720", "1280x720", "4096x2160", "3840x2160", "1920x1080",
                                        "1920x1080i", "720x576", "640x480"])
    assert screen_detect.tv_mode("HDMI-A-2", drm) == (1920, 1080)


def test_without_1080p_the_largest_16_9_below_it(tmp_path):
    drm = _modes(tmp_path, "HDMI-A-2", ["1024x768", "1280x720", "640x480"])
    assert screen_detect.tv_mode("HDMI-A-2", drm) == (1280, 720)
    drm = _modes(tmp_path / "b", "HDMI-A-2", ["1024x768", "800x600"])
    assert screen_detect.tv_mode("HDMI-A-2", drm) is None


def test_the_tv_s_mode_is_forced_by_the_kernel_whatever_a_receiver_says():
    s = screens.other(1920, 1080, capped=True)
    assert screen_apply.video_for(s, "HDMI-A-2") == "video=HDMI-A-2:1920x1080"
    assert screens.other(1280, 720, capped=True).video_mode == "1280x720"


def test_choosing_a_tv_takes_its_mode_from_the_list():
    from test_main_wiring import _closure
    body = _closure("_choose_screen_port")
    assert "screen_detect.tv_mode(connector)" in body and "screens.other(*size, capped=True)" in body


def test_a_chosen_port_is_not_asked_about_at_the_start(tmp_path):
    """The receiver names itself SONY AVSYSTEM or LG TV as it wakes: the chosen
    port is the screen whatever it says."""
    from gexis_core import screen_watch
    state = tmp_path / "screen.json"
    screen_apply.write_state({"current": Applied("other-1920x1080-capped", 0, "HDMI-A-2", chosen=True).to_json(),
                              "previous": None, "pending": False}, state)
    seen = screen_detect.Seen(True, "HDMI-A-2", "SNY", "SONY AVSYSTEM", (1280, 720), ())
    assert screen_watch.at_start(seen, headless=False, setup_needed=False, path=tmp_path / "seen.json",
                                 files={"state": state}) == "same"


# --- D5 as amended: the panel switched off, its touch ignored ---------------

def test_with_a_tv_as_the_screen_the_panels_touch_is_ignored_by_udev(tmp_path):
    from gexis_core import screen_watch
    state, rules, ran = tmp_path / "screen.json", tmp_path / "rules" / "90.rules", []
    screen_apply.write_state({"current": Applied("other-1920x1080-capped", 0, "HDMI-A-2", chosen=True).to_json()},
                             state)
    ids = screen_watch.touch_rules(state, rules, run=lambda args, check=False: ran.append(args))
    assert "0712:0010" in ids
    text = rules.read_text()
    assert 'ATTRS{idVendor}=="0712", ATTRS{idProduct}=="0010", ENV{LIBINPUT_IGNORE_DEVICE}="1"' in text
    assert ["udevadm", "trigger", "--action=change", "--subsystem-match=input"] in ran
    # The panel the screen again: the rule goes, and udev is told.
    screen_apply.write_state({"current": Applied("waveshare-10.1-hdmi-b", 0, "HDMI-A-1", chosen=True).to_json()},
                             state)
    ran.clear()
    assert screen_watch.touch_rules(state, rules, run=lambda args, check=False: ran.append(args)) == []
    assert not rules.exists() and ran


def test_a_panel_on_the_other_port_is_switched_off_while_a_tv_is_the_screen(tmp_path):
    drm, usb = two_ports(tmp_path, EDID, _receiver_edid())
    ports = screen_detect.ports(drm, usb)
    assert screen_apply.panels_off("other-1920x1080-capped", "HDMI-A-2", ports) == ["HDMI-A-1"]
    assert screen_apply.panels_off("waveshare-10.1-hdmi-b", "HDMI-A-1", ports) == []
    env = screen_apply.env_for(screens.by_id("other-1920x1080-capped"), 0, "HDMI-A-2", ("HDMI-A-1",))
    assert "GEXIS_OUTPUTS_OFF=HDMI-A-1\n" in env
    script = (FILES / "gexis-kiosk-start").read_text()
    assert 'for off in ${GEXIS_OUTPUTS_OFF:-}; do' in script and 'wlr-randr --output "${off}" --off' in script


# --- Standby on a port that carries the sound ------------------------------

def test_standby_leaves_a_port_carrying_the_sound_on(monkeypatch):
    """The TV through the receiver went silent with standby: HDMI's sound rides
    on its picture. Black, and the sound goes on."""
    import asyncio
    from gexis_core import alsa, standby
    monkeypatch.setattr(standby, "screen_env", lambda: {"GEXIS_SCREEN_CONNECTOR": "HDMI-A-2"})
    monkeypatch.setattr(standby.pwd, "getpwnam", lambda name: mock.Mock(pw_uid=1000))
    ran = []

    async def no_exec(*args, **kw):
        ran.append(args)
        raise AssertionError("wlr-randr must not run")

    monkeypatch.setattr(standby.asyncio, "create_subprocess_exec", no_exec)
    monkeypatch.setattr(alsa, "card", lambda: "vc4hdmi1")
    assert asyncio.run(standby.switch_output(False)) is True and ran == []


# --- After the second try: the TV's mode held by the compositor too ---------

def test_a_tv_s_mode_is_named_for_the_kiosk_and_a_panel_s_is_not():
    """sofapi, 2026-10-13: the kernel held 1080p for the boot, then labwc took
    the receiver's preferred 1280 x 720 under a page scaled for 1080p."""
    tv = screen_apply.env_for(screens.by_id("other-1920x1080-capped"), 0, "HDMI-A-2")
    assert "GEXIS_SCREEN_MODE=1920x1080\n" in tv
    for panel in ("waveshare-10.1-hdmi-b", "waveshare-11.9-hdmi"):
        assert "GEXIS_SCREEN_MODE=\n" in screen_apply.env_for(screens.by_id(panel), 0, "HDMI-A-1")
    script = (FILES / "gexis-kiosk-start").read_text()
    assert 'wlr-randr --output "${connector}" --mode "${GEXIS_SCREEN_MODE}"' in script


def _splash():
    import importlib.machinery, importlib.util
    path = FILES.parents[1] / "06-splash" / "files" / "gexis-splash-fb"
    loader = importlib.machinery.SourceFileLoader("gexis_splash_fb", str(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader("gexis_splash_fb", loader))
    loader.exec_module(module)
    return module


def test_with_two_screens_the_boot_gap_is_black_on_both(tmp_path):
    """George's photo: the still drawn for the TV showed on the panel as a
    cut-off logo beside a block of another colour - one framebuffer, two
    sizes."""
    splash = _splash()
    drm = tmp_path / "drm"
    for name, status in (("card1-HDMI-A-1", "connected"), ("card1-HDMI-A-2", "connected")):
        (drm / name).mkdir(parents=True)
        (drm / name / "status").write_text(status + "\n")
    assert splash.connected_ports(str(drm)) == 2
    (drm / "card1-HDMI-A-2" / "status").write_text("disconnected\n")
    assert splash.connected_ports(str(drm)) == 1
    payload, geometry = splash.black((b"\x10\x20\x30\x40", (1, 1, 32, 4)))
    assert payload == bytes(4) and geometry == (1, 1, 32, 4)
    assert splash.black(None) is None
