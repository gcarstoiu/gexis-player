"""ADR-0109: setup's Screen step - the answer it keeps and the route it reads."""
from __future__ import annotations

from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core import screen_detect, screens
from gexis_core.setup_flow import screen_choices
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

from test_setup_flow import FakeSettings, finish, make
from test_setup_network import NOTHING, FakeNM

PANEL = 'Waveshare/10.1" HDMI LCD (B) (1280x800)'
EDID = (Path(__file__).parent / "data" / "edid-waveshare-10.1-hdmi-b.bin").read_bytes()


def test_the_panel_s_label_is_one_the_list_knows():
    assert screens.by_label(PANEL).id == "waveshare-10.1-hdmi-b"


def test_choosing_a_screen_ends_headless_and_headless_drops_the_screen(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    flow.save({"headless": True})
    out = flow.save({"screen": PANEL})
    assert out["screen"] == PANEL and out["headless"] is False
    out = flow.save({"headless": True})
    assert out["headless"] is True and "screen" not in out


def test_an_unknown_screen_or_both_at_once_is_refused(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    with pytest.raises(ValueError):
        flow.save({"screen": "Acme/Nothing"})
    with pytest.raises(ValueError):
        flow.save({"screen": PANEL, "headless": True})
    assert "screen" not in flow.answers(), "a refused save writes nothing"


def test_finishing_sets_the_screen_after_headless(tmp_path):
    settings = FakeSettings(headless=True)
    flow, net, *_ = make(tmp_path, FakeNM(devices=NOTHING), settings)
    flow.save({"ssid": "Home", "password": "hunter22", "headless": False, "screen": PANEL})
    finish(flow, net)
    keys = [k for k, _ in settings.sets]
    assert ("screen", PANEL) in settings.sets and keys.index("headless") < keys.index("screen")


def test_a_screen_that_refuses_does_not_stop_setup(tmp_path):
    """Until applying a screen is wired, the setting raises NotWired."""
    class Refusing(FakeSettings):
        def set(self, key, value):
            if key == "screen":
                raise RuntimeError("screen is not wired yet")
            super().set(key, value)

    flow, net, *_ = make(tmp_path, FakeNM(devices=NOTHING), Refusing())
    flow.save({"ssid": "Home", "password": "hunter22", "screen": PANEL})
    finish(flow, net)
    assert (tmp_path / "setup-done").exists()


def test_the_screen_step_s_three_states():
    maker, name, preferred = screen_detect.parse_edid(EDID)
    recognised = screen_choices(screen_detect.Seen(True, "HDMI-A-1", maker, name, preferred, ("0712:0010",)))
    assert recognised["suggested"]["id"] == "waveshare-10.1-hdmi-b"
    assert recognised["suggested"]["label"] == PANEL and recognised["suggested"]["tested"] is True
    assert recognised["seen"]["preferred"] == "1280x800"
    uncertain = screen_choices(screen_detect.Seen(True, "HDMI-A-1", maker, name, preferred, ()))
    assert uncertain["suggested"] is None and uncertain["seen"]["connected"]
    none = screen_choices(screen_detect.Seen())
    assert none["suggested"] is None and not none["seen"]["connected"]
    models = none["models"]
    assert len(models) == len(screens.all_screens()) == 110
    assert set(models[0]) == {"id", "label", "maker", "model", "width", "height", "family", "tested", "skins", "skin_count"}
    assert sum(m["tested"] for m in models) == 4


class FakeSetup:
    def __init__(self, network="open", needed=True):
        self.state = {"network": network, "needed": needed}

    def status(self):
        return dict(self.state)

    def public_status(self):
        return dict(self.state)

    def page_opened(self):
        pass


@pytest.mark.asyncio
async def test_the_screen_route_answers_only_while_setup_is_open(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    fake = FakeSetup()
    server = StateServer(StateStore({}), setup=fake, setup_flow=flow, screen_seen=screen_detect.Seen)
    async with TestClient(TestServer(server.make_app())) as client:
        r = await client.get("/setup/screen")
        assert r.status == 200
        body = await r.json()
        assert body["suggested"] is None and not body["seen"]["connected"] and len(body["models"]) == 110
        fake.state = {"network": "online", "needed": False}
        assert (await client.get("/setup/screen")).status == 409


@pytest.mark.asyncio
async def test_the_screen_route_without_detection_says_so(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    server = StateServer(StateStore({}), setup=FakeSetup(), setup_flow=flow)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.get("/setup/screen")).status == 503


def test_each_screen_names_its_skin_pack():
    """ADR-0111: the Visualiser step names the pack the screen gets."""
    by_label = {m["label"]: m for m in screen_choices(screen_detect.Seen())["models"]}
    assert by_label[PANEL]["skins"] == "1280x800" and by_label[PANEL]["skin_count"] == 432
    for m in by_label.values():
        assert m["skins"] is None or m["skins"].count("x") == 1
        assert (m["skin_count"] is None) == (m["skins"] is None)


def test_the_visualiser_answer_becomes_the_setting(tmp_path):
    settings = FakeSettings()
    flow, net, *_ = make(tmp_path, FakeNM(devices=NOTHING), settings)
    flow.save({"ssid": "Home", "password": "hunter22", "screen": PANEL, "visualiser": True})
    finish(flow, net)
    assert ("visualiser_skins", True) in settings.sets


def test_headless_drops_the_visualiser_answer(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    flow.save({"screen": PANEL, "visualiser": True})
    assert flow.save({"headless": True}).get("visualiser") is None
    with pytest.raises(ValueError):
        flow.save({"visualiser": "yes"})
