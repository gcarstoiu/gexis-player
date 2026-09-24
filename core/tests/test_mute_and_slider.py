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


def test_travel_is_the_shared_cubic_curve_and_zero_is_silence():
    """**ADR-0054 §3/§4.** The panel's own window was -45..0 dB with its
    floor a level rather than silence; it is now the same curve every
    renderer gets - cubic over 60 dB - and 0% is silence.

    George, 2026-09-23: *"Even with volume at 0 on any renderer there is
    still sound coming. Faint but still there"*, then *"the bottom half of
    the volume range is quite quiet."*"""
    assert raw_to_db(slider_percent_to_raw(100)) == 0.0
    assert raw_to_db(slider_percent_to_raw(50)) == -15.5
    assert raw_to_db(slider_percent_to_raw(1)) == pytest.approx(-58.0, abs=0.5)
    assert slider_percent_to_raw(0) == 0


@pytest.mark.parametrize("percent", range(0, 101))
def test_every_slider_position_round_trips_within_one(percent):
    """The cubic taper is finer than the DAC's 0.5 dB steps above about
    44%, so some neighbouring positions share a level (volume.py's note on
    the taper). Below that every position has one of its own."""
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
