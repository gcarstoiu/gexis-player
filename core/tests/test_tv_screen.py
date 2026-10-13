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


# --- D3: Keep from the phone on a screen without touch ----------------------

def test_only_a_screen_without_known_touch_is_answered_from_the_phone():
    assert screen_detect.has_touch("waveshare-10.1-hdmi-b")
    assert not screen_detect.has_touch("other-1920x1080-capped")


def test_the_question_says_the_phone_answers_for_a_tv(tmp_path):
    from gexis_core.__main__ import screen_question
    state = {"pending": True, "current": {"screen": "other-1920x1080-capped", "rotation": 0,
                                          "connector": "HDMI-A-2", "chosen": True},
             "previous": {"screen": "waveshare-10.1-hdmi-b", "rotation": 0, "connector": "HDMI-A-1"}}
    assert screen_question(state)["phone"] is True
    state["current"] = state["previous"]
    assert screen_question(state)["phone"] is False


def _answer(confirm, remote):
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
    request = make_mocked_request("POST", "/screen/keep", match_info={"action": "keep"}, transport=transport)
    response = asyncio.run(server._handle_screen_answer(request))
    return response.status, answered


def test_a_phone_answers_keep_for_a_tv_and_not_for_a_panel():
    assert _answer({"model": "LG TV", "phone": True}, "192.168.1.20") == (200, ["keep"])
    assert _answer({"model": "Waveshare 10.1", "phone": False}, "192.168.1.20")[0] == 403
    assert _answer({"model": "Waveshare 10.1", "phone": False}, "127.0.0.1") == (200, ["keep"])


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
