"""ADR-0165: mute with Fixed volume - the output's own control silenced, and
full scale given back; no mute where the output has no control."""
from __future__ import annotations

import ast
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer

from gexis_core import volume as vol
from gexis_core.state import StateStore
from gexis_core.volume import VolumeBridge
from gexis_core.wsserver import StateServer

MAIN = Path(__file__).resolve().parents[1] / "src" / "gexis_core" / "__main__.py"


class FakeSpotify:
    renderer_id = "spotify"

    def __init__(self):
        self.told = []

    def on_volume_change(self, callback):
        pass

    async def get_volume_steps(self):
        return 100

    async def set_volume(self, value):
        self.told.append(value)


def _closure(name: str) -> str:
    tree = ast.parse(MAIN.read_text())
    [main] = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "main"]
    for node in ast.walk(main):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.unparse(node)
    raise AssertionError(name)


def test_published_as_null_until_there_is_such_a_mute():
    store = StateStore({})
    assert store.state.to_json()["fixed_mute"] is None
    store.set_fixed_output(True)
    store.set_fixed_mute(False)
    assert store.state.to_json()["fixed_mute"] is False
    store.set_fixed_mute(True)
    assert store.state.to_json()["fixed_mute"] is True
    assert store.state.to_json()["volume"] is None, "ADR-0046: no level in Fixed"


async def test_the_route_refuses_where_the_output_has_no_control():
    got = []

    async def set_mute(muted):
        got.append(muted)
        return True

    store = StateStore({})
    store.set_fixed_output(True)
    server = StateServer(store, set_mute=set_mute)
    async with TestClient(TestServer(server.make_app())) as client:
        refused = await client.post("/volume/mute", json={"muted": True})
        assert refused.status == 409
        assert "no volume control of its own" in (await refused.json())["error"]
        store.set_fixed_mute(False)
        assert (await client.post("/volume/mute", json={"muted": True})).status == 200
    assert got == [True]


async def test_the_write_goes_straight_to_the_control_and_is_known_as_ours(monkeypatch):
    """`write_hardware` refuses in Fixed; this one does not, and its echo is
    not handed to the renderer - Spotify's own slider stays where it was."""
    writes, cuts = [], []

    async def fake_set_raw(mixer_name, value, *args, **kwargs):
        writes.append((mixer_name, value))

    monkeypatch.setattr(vol, "set_raw", fake_set_raw)
    monkeypatch.setattr(vol, "publish_attenuation", cuts.append)
    monkeypatch.setattr(vol, "fixed_output", lambda: True)
    spotify = FakeSpotify()
    bridge = VolumeBridge("DAC", spotify, get_active_renderer=lambda: "spotify")

    await bridge.write_fixed(vol.hardware_silence())
    assert writes == [("DAC", vol.hardware_silence())]
    assert bridge._was_ours(vol.hardware_silence())
    assert bridge._last_written is None, "the next ramp starts at its target"
    assert cuts == [vol.hardware_silence()], "the meters see silence"
    await bridge.write_fixed(vol.hardware_max())
    assert writes[-1] == ("DAC", vol.hardware_max()) and cuts[-1] == vol.hardware_max()
    assert spotify.told == []


def test_with_fixed_volume_mute_takes_the_fixed_path():
    assert "if fixed_now['value']:\n        return await _set_fixed_mute(muted)" in _closure("set_mute")
    fixed = _closure("_set_fixed_mute")
    assert "if not _fixed_mute_offered():\n        return False" in fixed
    assert "volume_bridge.write_fixed(hardware_silence() if muted else hardware_max())" in fixed


def test_offered_only_where_the_output_has_a_control():
    offered = _closure("_fixed_mute_offered")
    assert "if not fixed_now['value']:\n        return False" in offered
    assert "output.control is not None" in offered
    publish = _closure("publish_fixed_mute")
    assert "state_store.set_fixed_mute(None)" in publish


def test_a_change_of_volume_type_or_output_ends_it():
    """§5: Variable's mute and Fixed's both end with a change of type, and a
    change of output takes the new card to full scale."""
    apply = _closure("_apply_output_mode")
    assert "mute.observe(hardware_max())" in apply
    assert apply.index("fixed_muted['value'] = False") < apply.index("publish_fixed_mute()")
    switch = _closure("_switch_output")
    assert switch.index("set_raw(volume_bridge.mixer_name, hardware_max())") < switch.index(
        "publish_fixed_mute()")
