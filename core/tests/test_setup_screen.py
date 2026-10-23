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
    assert len(models) == len(screens.all_screens()) == 166
    assert set(models[0]) == {"id", "label", "maker", "model", "width", "height", "family", "tested", "problem", "skins", "skin_count"}
    # Four Waveshares and two HMTECHs (2026-10-20), the Hosyond 7" DSI and its
    # class (ADR-0158, 2026-10-23).
    assert sum(m["tested"] for m in models) == 8


class FakeSetup:
    def __init__(self, network="open", needed=True):
        self.state = {"network": network, "needed": needed}

    def status(self):
        return dict(self.state)

    def public_status(self):
        return dict(self.state)

    def page_opened(self):
        pass

    def page_used(self):
        self.used = getattr(self, "used", 0) + 1


@pytest.mark.asyncio
async def test_the_screen_route_answers_only_while_setup_is_open(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    fake = FakeSetup()
    server = StateServer(StateStore({}), setup=fake, setup_flow=flow, screen_seen=screen_detect.Seen)
    async with TestClient(TestServer(server.make_app())) as client:
        r = await client.get("/setup/screen")
        assert r.status == 200
        body = await r.json()
        assert body["suggested"] is None and not body["seen"]["connected"] and len(body["models"]) == 166
        fake.state = {"network": "online", "needed": False}
        assert (await client.get("/setup/screen")).status == 409


@pytest.mark.asyncio
async def test_the_screen_route_without_detection_says_so(tmp_path):
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    server = StateServer(StateStore({}), setup=FakeSetup(), setup_flow=flow)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.get("/setup/screen")).status == 503


@pytest.mark.asyncio
async def test_a_phone_asking_the_setup_page_anything_is_noted(tmp_path):
    """George, 2026-10-12: a phone on the setup network holds the player
    off its Wi-Fi only while the page is in use - the page itself or any
    `/setup/...` route, from a phone, not the panel."""
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    (tmp_path / "ui" / "assets").mkdir(parents=True)
    (tmp_path / "ui" / "index.html").write_text("<html></html>")
    fake = FakeSetup()
    server = StateServer(StateStore({}), setup=fake, setup_flow=flow, ui_dir=tmp_path / "ui")
    phone = {"on": True}
    server._from_panel = lambda request: not phone["on"]
    async with TestClient(TestServer(server.make_app())) as client:
        for path in ("/", "/setup/status", "/setup/answers"):
            assert (await client.get(path)).status == 200
        assert fake.used == 3
        await client.get("/state")
        await client.get("/players")
        assert fake.used == 3, "only the setup page"
        phone["on"] = False
        await client.get("/")
        await client.get("/setup/status")
        assert fake.used == 3, "the panel is not somebody setting up"


def test_each_screen_names_its_skin_pack():
    """ADR-0111: the Visualiser step names the pack the screen gets."""
    by_label = {m["label"]: m for m in screen_choices(screen_detect.Seen())["models"]}
    assert by_label[PANEL]["skins"] == "1280x800" and by_label[PANEL]["skin_count"] == 286
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


def _finish_told(flow, net):
    import asyncio

    async def go():
        net._state = "open"
        net._needed = True
        told = flow.finish()
        await flow._task
        return told
    return asyncio.run(go())


def test_finishing_tells_the_phone_whether_keep_will_be_asked(tmp_path, monkeypatch):
    """ADR-0109 as amended 2026-10-02: the phone says the question is coming."""
    from gexis_core import screen_apply

    asked = []
    monkeypatch.setattr(screen_apply, "would_ask", lambda applied, **kw: asked.append(applied) or True)
    flow, net, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    flow.save({"ssid": "Home", "password": "hunter22", "screen": PANEL})
    assert _finish_told(flow, net) == {"keep_question": True}
    assert asked[0].screen_id == "waveshare-10.1-hdmi-b"


def test_headless_is_never_asked(tmp_path):
    flow, net, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    flow.save({"ssid": "Home", "password": "hunter22", "headless": True})
    assert _finish_told(flow, net) == {"keep_question": False}


def test_a_screen_from_its_own_mode_is_one_setup_and_settings_can_name(tmp_path, monkeypatch):
    """ADR-0109 (George, 2026-10-12): a screen laid out from its own mode -
    applied for setup when nothing in the list matches it - is called
    `Other screen/W × H`, and that name has to stay one gexis can apply: the
    Settings row offers it, and finishing setup or a restore resolves it to
    the screen in use, turn and all."""
    from gexis_core import screen_apply, settings_registry

    state = tmp_path / "screen.json"
    screen_apply.write_state({"current": {"screen": "other-1920x1080-turned", "rotation": 0}}, state)
    monkeypatch.setattr(screen_apply, "STATE", state)
    label = "Other screen/1920 × 1080"
    assert label in settings_registry._screens()
    assert label not in settings_registry._screen_tags(), "nothing beside an untested model (2026-10-18)"
    asked = []
    monkeypatch.setattr(screen_apply, "would_ask", lambda applied, **kw: asked.append(applied) or True)
    flow, net, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    flow.save({"ssid": "Home", "password": "hunter22", "screen": label})
    assert _finish_told(flow, net) == {"keep_question": True}
    assert asked[0].screen_id == "other-1920x1080-turned"


def test_the_list_alone_is_offered_when_no_other_screen_is_in_use(tmp_path, monkeypatch):
    from gexis_core import screen_apply, settings_registry

    monkeypatch.setattr(screen_apply, "STATE", tmp_path / "screen.json")
    assert settings_registry._screens() == tuple(s.label for s in screens.all_screens())
    screen_apply.write_state({"current": {"screen": "waveshare-10.1-hdmi-b", "rotation": 0}}, tmp_path / "screen.json")
    assert settings_registry._screens() == tuple(s.label for s in screens.all_screens())


def test_setup_applies_and_compares_the_screen_on_the_port_it_is_on(tmp_path, monkeypatch):
    """ADR-0109 (George, 2026-10-12): the Screen step's choice is applied on
    the port the screen was seen on, and a bar already laid out there for
    setup is one that changes nothing."""
    from gexis_core import screen_apply

    seen = screen_detect.Seen(connected=True, connector="HDMI-A-2", edid_maker="WSD",
                              edid_name="WaveShare-119", preferred=(320, 1480), usb=("0712:000a",))
    monkeypatch.setattr(screen_detect, "seen", lambda *a, **k: seen)
    monkeypatch.setattr(screen_apply, "STATE", tmp_path / "screen.json")
    asked = []
    monkeypatch.setattr(screen_apply, "would_ask", lambda applied, **kw: asked.append(applied) or True)
    flow, net, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    flow.save({"ssid": "Home", "password": "hunter22", "screen": PANEL})
    _finish_told(flow, net)
    assert asked[0].connector == "HDMI-A-2"
    bar = screen_apply.Applied("waveshare-11.9-hdmi", 0, "HDMI-A-2")
    choices = screen_choices(seen, now=screen_apply.picture_of(bar))
    assert "waveshare-11.9-hdmi" in choices["unchanged"]


def test_setup_keeps_the_screen_it_confirms():
    """Setup's answers are written only when they differ, so confirming the
    screen already applied wrote nothing; it is kept explicitly."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "src" / "gexis_core" / "setup_flow.py").read_text()
    apply = src[src.index("    async def _apply(self, data: dict)"):src.index("    def _restore_values")]
    assert 'screen_apply.confirm_provisional(data["screen"])' in apply
    assert apply.index("confirm_provisional") < apply.index("self._network.finished(")


@pytest.mark.asyncio
async def test_the_outputs_route_says_which_have_a_volume_control(tmp_path, monkeypatch):
    """George, 2026-10-18: the Output step offers Hardware only where the
    output has a control of its own, as Settings does."""
    from gexis_core import outputs
    found = [outputs.Output("sndrpihifiberry", "HiFiBerry DAC+", "Digital"),
             outputs.Output("vc4hdmi0", "HDMI 1", None)]
    monkeypatch.setattr(outputs, "discover", lambda *a, **k: found)
    flow, *_ = make(tmp_path, FakeNM(devices=NOTHING))
    fake = FakeSetup()
    server = StateServer(StateStore({}), setup=fake, setup_flow=flow)
    async with TestClient(TestServer(server.make_app())) as client:
        r = await client.get("/setup/outputs")
        assert await r.json() == [{"option": "HiFiBerry DAC+", "hardware": True},
                                  {"option": "HDMI 1", "hardware": False}]
        fake.state = {"network": "online", "needed": False}
        assert (await client.get("/setup/outputs")).status == 409
