"""The equaliser as the player keeps it and shows it, and its routes (ADR-0162 D9)."""
import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core import equaliser as eq
from gexis_core import outputs
from gexis_core.eq_control import KEY, EqualiserControl, kind_of
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

DAC = outputs.Output(card="sndrpihifiberry", label="HiFiBerry DAC+ HD", control="DAC")
HDMI = outputs.Output(card="vc4hdmi0", label="HDMI 1", control=None)


class Store(dict):
    def set(self, key, value):
        self[key] = value


class Engine:
    def __init__(self):
        self.calls = []
        self.dsd = False

    async def configure(self, card, gains, restart=False):
        self.calls.append((card, tuple(gains), restart))

    def status(self):
        return {"running": bool(self.calls and self.calls[-1][0]), "dsd": self.dsd}


class Rig:
    def __init__(self):
        self.store, self.engine = Store(), Engine()
        self.output = DAC
        self.fixed = False
        self.reopened, self.published, self.changes = [], [], []

        async def reopen(reason):
            self.reopened.append(reason)
            await self.control.sync(restart=True)

        self.control = EqualiserControl(self.store, self.engine, output=lambda: self.output,
                                        fixed=lambda: self.fixed, reopen=reopen,
                                        publish=self.published.append,
                                        changed=lambda: self.changes.append(1))


async def test_off_by_default_flat_and_bit_perfect():
    rig = Rig()
    snap = rig.control.snapshot()
    assert snap["on"] is False and snap["sel"] == "flat" and snap["gains"] == [0] * 10
    assert snap["output"] == {"card": "sndrpihifiberry", "name": "HiFiBerry DAC+ HD", "kind": "DAC"}
    assert [p["name"] for p in snap["presets"]][:2] == ["Flat", "Rock"] and snap["own_max"] == 10
    assert rig.control.summary() == "Off"


async def test_switching_on_reopens_the_output_and_starts_the_engine():
    rig = Rig()
    snap = await rig.control.update({"on": True})
    assert snap["on"] is True
    assert rig.reopened == ["the equaliser was switched on"]
    assert rig.engine.calls[-1] == ("sndrpihifiberry", eq.FLAT, True)
    assert rig.control.in_path("sndrpihifiberry") and not rig.control.in_path("vc4hdmi0")
    await rig.control.update({"on": False})
    assert rig.reopened[-1] == "the equaliser was switched off"
    assert rig.engine.calls[-1][0] is None


async def test_a_setting_or_a_band_does_not_reopen_it():
    rig = Rig()
    await rig.control.update({"on": True})
    rig.reopened.clear()
    snap = await rig.control.update({"sel": "rock"})
    assert snap["name"] == "Rock" and snap["headroom_db"] == 5
    snap = await rig.control.update({"band": 2, "gain": 5})
    assert snap["sel"] == "custom" and snap["from"] == "rock" and snap["from_name"] == "Rock"
    assert snap["name"] == "Custom"
    assert rig.reopened == []
    assert rig.engine.calls[-1] == ("sndrpihifiberry", (4, 3, 5, 0, -1, -1, 0, 2, 3, 4), False)
    assert rig.published[-1] == snap
    assert rig.control.summary() == "Custom"


async def test_each_output_keeps_its_own():
    rig = Rig()
    await rig.control.update({"on": True, "sel": "jazz"})
    rig.output = HDMI
    snap = rig.control.snapshot()
    assert snap["on"] is False and snap["sel"] == "flat" and snap["output"]["kind"] == "HDMI"


async def test_saved_renamed_deleted():
    rig = Rig()
    await rig.control.update({"sel": "pop"})
    saved = await rig.control.save_as("Kitchen radio")
    assert saved["saved"]["name"] == "Kitchen radio" and saved["equaliser"]["sel"] == saved["saved"]["key"]
    key = saved["saved"]["key"]
    snap = await rig.control.rename(key, "Kitchen")
    assert snap["own"][0]["name"] == "Kitchen" and snap["name"] == "Kitchen"
    snap = await rig.control.delete(key)
    assert snap["own"] == [] and snap["sel"] == "flat"
    assert rig.store[KEY]["own"] == []
    assert len(rig.changes) == 4, "the Settings row follows every change"


@pytest.mark.parametrize("body", [{}, {"loud": 1}, {"on": "yes"}, {"band": 3}, {"band": 12, "gain": 0},
                                  {"sel": "nope"}, {"gains": [1, 2]}])
async def test_refused(body):
    rig = Rig()
    with pytest.raises(eq.EqualiserError):
        await rig.control.update(body)


async def test_fixed_and_dsd_are_shown():
    rig = Rig()
    rig.fixed = True
    await rig.control.update({"on": True})
    rig.engine.dsd = True
    snap = rig.control.snapshot()
    assert snap["fixed"] is True and snap["dsd"] is True


def test_the_output_in_a_word():
    assert kind_of(DAC) == "DAC" and kind_of(HDMI) == "HDMI"
    assert kind_of(outputs.Output(card="Headphones", label="Headphones (3.5 mm)", control="PCM")) == "Headphones"


async def test_the_routes():
    rig = Rig()
    server = StateServer(StateStore({}), equaliser=rig.control)
    async with TestClient(TestServer(server.make_app())) as client:
        r = await client.get("/equaliser")
        assert r.status == 200 and (await r.json())["on"] is False
        r = await client.put("/equaliser", json={"sel": "vocal"})
        assert r.status == 200 and (await r.json())["name"] == "Vocal"
        r = await client.put("/equaliser", json={"band": 0, "gain": 40})
        assert r.status == 400 and "12" in (await r.json())["error"]
        r = await client.put("/equaliser", data="nope")
        assert r.status == 400
        r = await client.post("/equaliser/settings", json={"name": "Mine"})
        body = await r.json()
        assert r.status == 200 and body["saved"]["name"] == "Mine"
        key = body["saved"]["key"]
        r = await client.post("/equaliser/settings", json={"name": "mine"})
        assert r.status == 400 and "already" in (await r.json())["error"]
        r = await client.put(f"/equaliser/settings/{key}", json={"name": "Ours"})
        assert r.status == 200 and (await r.json())["own"][0]["name"] == "Ours"
        r = await client.delete(f"/equaliser/settings/{key}")
        assert r.status == 200 and (await r.json())["own"] == []
        r = await client.delete("/equaliser/settings/own-9")
        assert r.status == 400


async def test_not_wired_and_no_output():
    async with TestClient(TestServer(StateServer(StateStore({})).make_app())) as client:
        assert (await client.get("/equaliser")).status == 503
        assert (await client.put("/equaliser", json={"on": True})).status == 503
    rig = Rig()
    rig.output = None
    async with TestClient(TestServer(StateServer(StateStore({}), equaliser=rig.control).make_app())) as client:
        assert (await client.get("/equaliser")).status == 409
        r = await client.put("/equaliser", json={"on": True})
        assert r.status == 400 and "no output" in (await r.json())["error"]


async def test_the_state_carries_it():
    store = StateStore({})
    seen = []
    store.subscribe(lambda s: seen.append(s.to_json()["equaliser"]))
    store.set_equaliser({"on": True})
    store.set_equaliser({"on": True})
    assert seen == [{"on": True}], "published once per change"
