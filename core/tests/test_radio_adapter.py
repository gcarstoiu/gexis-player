# SPDX-License-Identifier: GPL-3.0-or-later
"""The internet radio's renderer (ADR-0180 items 3-5) against a fake mpv.

The fake speaks mpv's JSON protocol on a real socket and behaves as mpv did
in Finding 146 (Lesson 83): `loadfile` is answered *success* whatever then
happens to the stream; a cut and a station gone arrive as an ordinary
`end-file` with `core-idle` going true; a freeze is `core-idle` true and
nothing else; a refused station ends at once, every time; and observing a
property reports its value straight away.
"""
from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from gexis_core.adapters import radio as radio_mod
from gexis_core.adapters.radio import RadioAdapter
from gexis_core.model import TrackMetadata
from gexis_core.radio_directory import Station


class FakeMpv:
    """One mpv process: a socket, and streams that behave by their address."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.server: asyncio.base_events.Server | None = None
        self.writers: list[asyncio.StreamWriter] = []
        self.commands: list[list] = []
        self.observed: dict[int, str] = {}
        self.props = {"core-idle": True, "metadata": None, "audio-params": None,
                      "audio-codec-name": None}
        self.loaded: list[str] = []

    async def start(self) -> None:
        self.server = await asyncio.start_unix_server(self._client, self.path)

    async def stop(self) -> None:
        """The process ends; the next one starts idle, observing nothing."""
        if self.server is not None:
            self.server.close()
            self.server = None
        for writer in self.writers:
            writer.close()
        self.writers.clear()
        self.observed.clear()
        self.props = {"core-idle": True, "metadata": None, "audio-params": None,
                      "audio-codec-name": None}
        Path(self.path).unlink(missing_ok=True)

    async def _client(self, reader, writer) -> None:
        self.writers.append(writer)
        try:
            while line := await reader.readline():
                message = json.loads(line)
                await self._command(message["command"], message.get("request_id"), writer)
        except (ConnectionError, asyncio.CancelledError):
            pass

    def _send(self, message: dict) -> None:
        for writer in list(self.writers):
            if not writer.is_closing():
                writer.write((json.dumps(message) + "\n").encode())

    def set(self, name: str, value) -> None:
        self.props[name] = value
        for number, observed in self.observed.items():
            if observed == name:
                self._send({"event": "property-change", "id": number, "name": name, "data": value})

    async def _command(self, command: list, request_id, writer) -> None:
        self.commands.append(command)
        reply = {"request_id": request_id, "error": "success", "data": None}
        writer.write((json.dumps(reply) + "\n").encode())
        name = command[0]
        if name == "observe_property":
            self.observed[command[1]] = command[2]
            self.set(command[2], self.props.get(command[2]))
        elif name == "loadfile":
            self.loaded.append(command[1])
            asyncio.get_running_loop().call_soon(self._play, command[1])

    def _play(self, url: str) -> None:
        self._send({"event": "start-file"})
        if "refused" in url:
            self.set("core-idle", True)
            self._send({"event": "end-file", "reason": "error", "file_error": "loading failed"})
            return
        rate = 22050 if "lowrate" in url else 44100
        self.set("audio-params", {"samplerate": rate, "channels": "stereo", "format": "floatp"})
        self.set("core-idle", False)
        if "titled" in url:
            self.set("metadata", {"icy-name": "Example FM", "icy-title": "Band - Song"})

    def cut(self) -> None:
        """The connection closed: the buffer ran out, then an ordinary end."""
        self.set("core-idle", True)
        self._send({"event": "end-file", "reason": "eof"})

    def freeze(self) -> None:
        self.set("core-idle", True)


class FakeUnits:
    def __init__(self, mpv: FakeMpv) -> None:
        self.mpv = mpv
        self.calls: list[str] = []
        self.fail_start = False

    async def start(self) -> None:
        self.calls.append("start")
        if not self.fail_start and self.mpv.server is None:
            await self.mpv.start()

    async def stop(self) -> None:
        self.calls.append("stop")
        await self.mpv.stop()

    async def kill(self) -> None:
        self.calls.append("kill")
        await self.mpv.stop()


def station(n: int = 1, url: str | None = None, **changes) -> Station:
    return Station(id=f"id-{n}", name=f"Station {n}", url=url or f"http://example.org/{n}",
                   logo=f"https://example.org/{n}.png", codec="AAC", bitrate=128, **changes)


@pytest.fixture
def fast(monkeypatch):
    monkeypatch.setattr(radio_mod, "WATCHDOG_S", 0.2)
    monkeypatch.setattr(radio_mod, "SETTLED_S", 0.3)
    monkeypatch.setattr(radio_mod, "SOCKET_WAIT_S", 1.0)


@pytest.fixture
async def rig(fast):
    folder = tempfile.mkdtemp(prefix="mpv")
    path = f"{folder}/s"
    mpv = FakeMpv(path)
    units = FakeUnits(mpv)
    favourites: list[Station] = []
    resolved: list[str] = []

    async def resolve(s: Station) -> str:
        resolved.append(s.id)
        return s.url

    def step(station_id: str, by: int):
        ids = [f.id for f in favourites]
        if station_id not in ids:
            return None
        return favourites[(ids.index(station_id) + by) % len(favourites)]

    adapter = RadioAdapter(user_agent="GexisPlayer/test", resolve=resolve, step=step,
                           is_favourite=lambda sid: any(f.id == sid for f in favourites),
                           units=units, socket_path=path)
    metadata: list[TrackMetadata] = []
    states = []
    adapter.on_metadata_change(metadata.append)
    adapter.on_state_change(states.append)

    class Rig:
        pass
    r = Rig()
    r.adapter, r.mpv, r.units, r.favourites = adapter, mpv, units, favourites
    r.metadata, r.states, r.resolved = metadata, states, resolved
    yield r
    await adapter.release()
    await mpv.stop()


async def until(predicate, timeout: float = 3.0) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not predicate():
        if loop.time() > deadline:
            raise AssertionError("never happened")
        await asyncio.sleep(0.01)


async def test_a_station_plays_with_the_options_and_lines_it_needs(rig):
    assert await rig.adapter.play_station(station(1, url="http://example.org/titled"))
    await until(lambda: rig.adapter.state.state == radio_mod.PLAYING)
    assert rig.units.calls == ["start"]
    assert ["set_property", "user-agent", "GexisPlayer/test"] in rig.mpv.commands
    assert rig.mpv.loaded == ["http://example.org/titled"]
    await until(lambda: rig.metadata[-1].title == "Song")
    last = rig.metadata[-1]
    assert (last.artist, last.title, last.album) == ("Band", "Song", "Station 1")
    assert last.source_type == "radio" and last.transport == "playing"
    assert last.artwork is None and last.fallback_artwork == "https://example.org/1.png"
    assert last.sample_rate == 44100 and last.codec == "AAC"
    # Not a favourite: Next and Previous are not available.
    assert last.unavailable == frozenset({"next", "previous"})


async def test_a_low_rate_stream_is_converted_to_48_khz(rig):
    await rig.adapter.play_station(station(1, url="http://example.org/lowrate"))
    await until(lambda: any(c[:2] == ["af", "add"] for c in rig.mpv.commands))
    assert ["af", "add", "@gexisrate:format=srate=48000"] in rig.mpv.commands
    # A station at the usual rate after it: the filter goes.
    await rig.adapter.play_station(station(2))
    assert ["af", "remove", "@gexisrate"] in rig.mpv.commands


async def test_a_cut_is_reloaded_after_the_watchdog_and_the_count_settles(rig):
    await rig.adapter.play_station(station(1))
    await until(lambda: rig.adapter.state.state == radio_mod.PLAYING)
    rig.mpv.cut()
    await until(lambda: len(rig.mpv.loaded) == 2)
    await until(lambda: rig.adapter.state.state == radio_mod.PLAYING)
    assert [(s.state, s.attempt) for s in rig.states if s.state == radio_mod.RECONNECTING] \
        == [(radio_mod.RECONNECTING, 1)]
    assert rig.mpv.loaded == ["http://example.org/1", "http://example.org/1"]
    # Playing long enough starts the count again.
    await until(lambda: rig.adapter.state.attempt == 0)


async def test_a_freeze_counts_from_the_audio_stopping(rig):
    await rig.adapter.play_station(station(1))
    await until(lambda: rig.adapter.state.state == radio_mod.PLAYING)
    rig.mpv.freeze()
    await asyncio.sleep(radio_mod.WATCHDOG_S * 0.5)
    assert len(rig.mpv.loaded) == 1, "not before the watchdog's time"
    await until(lambda: len(rig.mpv.loaded) == 2)


async def test_a_station_that_stays_down_stops_with_a_message_after_three_tries(rig):
    await rig.adapter.play_station(station(1, url="http://example.org/refused"))
    await until(lambda: rig.adapter.state.state == radio_mod.NOT_ANSWERING, timeout=5)
    assert len(rig.mpv.loaded) == 1 + radio_mod.TRIES
    assert rig.units.calls[-1] == "stop"
    assert rig.metadata[-1].transport == "stopped"
    attempts = [s.attempt for s in rig.states if s.state == radio_mod.RECONNECTING]
    assert attempts == [1, 2, 3]


async def test_mpv_going_away_mid_play_is_a_drop(rig):
    await rig.adapter.play_station(station(1))
    await until(lambda: rig.adapter.state.state == radio_mod.PLAYING)
    await rig.mpv.stop()  # the process died
    await until(lambda: len(rig.mpv.loaded) == 2)
    await until(lambda: rig.adapter.state.state == radio_mod.PLAYING)
    assert rig.units.calls.count("start") >= 2


async def test_stop_is_a_stop_and_play_starts_it_afresh(rig):
    await rig.adapter.play_station(station(1))
    await until(lambda: rig.adapter.state.state == radio_mod.PLAYING)
    assert await rig.adapter.pause()
    assert rig.adapter.state.state == radio_mod.STOPPED
    assert rig.metadata[-1].transport == "stopped"
    assert rig.units.calls[-1] == "stop"
    await asyncio.sleep(radio_mod.WATCHDOG_S * 2)
    assert len(rig.mpv.loaded) == 1, "a stop is not a drop"
    assert await rig.adapter.play()
    await until(lambda: rig.adapter.state.state == radio_mod.PLAYING)
    assert rig.resolved == ["id-1", "id-1"]


async def test_next_and_previous_step_through_the_favourites(rig):
    rig.favourites[:] = [station(1), station(2), station(3)]
    await rig.adapter.play_station(station(1))
    assert rig.metadata[-1].unavailable == frozenset()
    assert await rig.adapter.next()
    assert rig.adapter.state.station.id == "id-2"
    assert await rig.adapter.previous()
    assert await rig.adapter.previous()
    assert rig.adapter.state.station.id == "id-3"
    # Another station: nowhere to step.
    await rig.adapter.play_station(station(9))
    assert not await rig.adapter.next()


async def test_a_release_during_the_lookup_stops_the_play(rig):
    gate = asyncio.Event()

    async def slow(s):
        await gate.wait()
        return s.url
    rig.adapter._resolve = slow
    playing = asyncio.ensure_future(rig.adapter.play_station(station(1)))
    await asyncio.sleep(0.05)
    released = asyncio.ensure_future(rig.adapter.release())
    await asyncio.sleep(0.05)
    gate.set()
    assert await playing is False
    await released
    assert rig.mpv.loaded == [], "mpv never started behind the new source's back"
    assert "start" not in rig.units.calls


async def test_reopen_loads_a_playing_station_again(rig):
    await rig.adapter.play_station(station(1))
    await until(lambda: rig.adapter.state.state == radio_mod.PLAYING)
    await rig.mpv.stop()   # the chain's rewrite stopped every renderer
    await rig.adapter.reopen()
    assert rig.mpv.loaded[-1] == "http://example.org/1"
    await until(lambda: rig.adapter.state.state == radio_mod.PLAYING)


async def test_reopen_does_nothing_when_nothing_plays(rig):
    await rig.adapter.reopen()
    assert rig.units.calls == []


async def test_a_unit_that_does_not_start_is_not_answering(rig):
    rig.units.fail_start = True
    assert not await rig.adapter.play_station(station(1))
    assert rig.adapter.state.state == radio_mod.NOT_ANSWERING


def test_capabilities_declare_no_level_of_its_own():
    caps = RadioAdapter.capabilities
    assert caps.volume_mechanism.value == "output"
    assert not caps.volume_managed
    assert caps.controls == frozenset({"play", "pause", "next", "previous"})
    assert RadioAdapter.unit_name == "gexis-radio.service"
