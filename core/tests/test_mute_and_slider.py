"""ADR-0034: the panel slider's scale and mute."""
from __future__ import annotations

import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core.state import StateStore
from gexis_core.volume import Mute, raw_to_db, raw_to_slider_percent, slider_percent_to_raw
from gexis_core.wsserver import StateServer


def test_bottom_of_travel_is_silence():
    assert slider_percent_to_raw(0) == 0
    assert raw_to_slider_percent(0) == 0


def test_travel_is_linear_in_db_over_minus_45_to_0():
    assert raw_to_db(slider_percent_to_raw(100)) == 0.0
    assert raw_to_db(slider_percent_to_raw(50)) == -22.5
    assert raw_to_db(slider_percent_to_raw(1)) == pytest.approx(-44.55, abs=0.5)


@pytest.mark.parametrize("percent", range(0, 101))
def test_every_slider_position_round_trips_within_one_step(percent):
    # 45dB is 90 hardware steps for 101 positions, so some positions share a step.
    assert abs(raw_to_slider_percent(slider_percent_to_raw(percent)) - percent) <= 1


def test_audible_but_below_the_floor_reads_as_zero():
    assert raw_to_slider_percent(60) == 0  # -90dB, the boot volume


class _Hardware:
    def __init__(self, raw):
        self.raw = raw
        self.writes = []

    async def write(self, raw):
        self.writes.append(raw)
        self.raw = raw


async def test_mute_writes_silence_and_unmute_restores_the_prior_level():
    hw = _Hardware(180)
    mute = Mute(hw.write, lambda: hw.raw)

    assert await mute.set(True)
    assert mute.muted and hw.raw == 0
    assert await mute.set(False)
    assert not mute.muted and hw.raw == 180


async def test_muting_twice_does_not_lose_the_level():
    hw = _Hardware(180)
    mute = Mute(hw.write, lambda: hw.raw)

    await mute.set(True)
    await mute.set(True)
    await mute.set(False)

    assert hw.raw == 180
    assert hw.writes == [0, 180]


async def test_any_other_level_change_ends_mute():
    hw = _Hardware(180)
    mute = Mute(hw.write, lambda: hw.raw)
    await mute.set(True)

    mute.observe(0)
    assert mute.muted
    mute.observe(150)  # a phone turned it up
    assert not mute.muted

    await mute.set(False)
    assert hw.writes == [0]


async def test_mute_before_the_level_is_known_is_refused():
    mute = Mute(_Hardware(0).write, lambda: None)
    assert await mute.set(True) is False
    assert not mute.muted


async def test_mute_route():
    got = []

    async def set_mute(muted):
        got.append(muted)
        return True

    server = StateServer(StateStore({}), set_mute=set_mute)
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.post("/volume/mute", json={"muted": True})).status == 200
        assert (await client.post("/volume/mute", json={"muted": "yes"})).status == 400
        assert (await client.post("/volume/mute", json={})).status == 400
    assert got == [True]


async def test_mute_route_answers_503_when_not_wired():
    server = StateServer(StateStore({}))
    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.post("/volume/mute", json={"muted": True})).status == 503
