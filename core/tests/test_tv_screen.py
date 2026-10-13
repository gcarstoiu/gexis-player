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


# --- D5: the panel's touch off while it is not the screen -------------------

def test_screen_env_names_the_screen_s_touch_and_every_known_panel_s():
    env = screen_apply.env_for(screens.by_id("other-1920x1080-capped"), 0, "HDMI-A-2")
    assert "GEXIS_SCREEN_TOUCH_USB=\n" in env
    assert "0712:0010" in env.split("GEXIS_PANEL_TOUCH_USB=", 1)[1]
    env = screen_apply.env_for(screens.by_id("waveshare-10.1-hdmi-b"), 0, "HDMI-A-1")
    assert "GEXIS_SCREEN_TOUCH_USB=0712:0010\n" in env


DEVICES = ('I: Bus=0003 Vendor=0712 Product=0010 Version=0200\nN: Name="WaveShare  WaveShare "\n\n'
           'I: Bus=0003 Vendor=046d Product=c52b Version=0111\nN: Name="Logitech USB Receiver"\n')


def _kiosk(tmp_path, screen_touch):
    if shutil.which("bash") is None:
        pytest.skip("needs bash")
    source = tmp_path / "xdg"
    source.mkdir()
    shutil.copy(FILES / "labwc-rc.xml", source / "rc.xml")
    drm = tmp_path / "drm"
    for name in ("card1-HDMI-A-1", "card1-HDMI-A-2"):
        (drm / name).mkdir(parents=True)
        (drm / name / "status").write_text("connected\n")
    (tmp_path / "devices").write_text(DEVICES)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GEXIS_")}
    env.update(GEXIS_LABWC_SOURCE=str(source), GEXIS_DRM=str(drm), GEXIS_INPUT_DEVICES=str(tmp_path / "devices"),
               GEXIS_SCREEN_CONNECTOR="HDMI-A-2" if not screen_touch else "HDMI-A-1",
               GEXIS_SCREEN_TOUCH_USB=screen_touch, GEXIS_PANEL_TOUCH_USB="0712:000a 0712:0010 222a:0001")
    subprocess.run(["bash", str(FILES / "gexis-kiosk-start"), "labwc-config", str(tmp_path / "out")],
                   env=env, check=True, capture_output=True, timeout=30)
    return (tmp_path / "out" / "rc.xml").read_text()


def test_with_a_tv_as_the_screen_the_panel_s_touch_is_off(tmp_path):
    rc = _kiosk(tmp_path, screen_touch="")
    assert '<device category="WaveShare  WaveShare "><sendEventsMode>no</sendEventsMode></device>' in rc
    assert "Logitech" not in rc, "only a known panel's touch"


def test_with_the_panel_as_the_screen_its_touch_stays(tmp_path):
    rc = _kiosk(tmp_path, screen_touch="0712:0010")
    assert "sendEventsMode" not in rc
