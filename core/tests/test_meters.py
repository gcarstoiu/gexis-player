"""The visualisation service (Phase 5 criterion 1, ADR-0011, Finding 024)."""
from __future__ import annotations

import asyncio
import os
import struct

import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core.meter_service import MeterServer
from gexis_core.meters import (
    FifoPassthrough,
    FifoSource,
    Levels,
    METER_FRAME,
    parse_meter,
    parse_spectrum,
    read_latest_frame,
)


def meter_frame(left, right):
    return struct.pack("<HH", left, right)


def spectrum_frame(bands):
    return struct.pack(f"<{len(bands)}I", *bands)


def test_frame_formats_match_finding_024():
    assert parse_meter(meter_frame(60, 63)) == (60, 63)
    bands = tuple(range(30))
    assert parse_spectrum(spectrum_frame(bands)) == bands


def test_mono_is_the_average():
    assert Levels(60, 63, ()).mono == 62
    assert Levels(0, 0, ()).to_json()["mono"] == 0


@pytest.fixture
def fifos(tmp_path):
    meter, spectrum = str(tmp_path / "m"), str(tmp_path / "s")
    os.mkfifo(meter)
    os.mkfifo(spectrum)
    writers = [os.open(p, os.O_RDWR | os.O_NONBLOCK) for p in (meter, spectrum)]
    yield meter, spectrum, writers
    for fd in writers:
        os.close(fd)


def test_the_newest_frame_wins_and_a_backlog_is_discarded(fifos):
    meter, spectrum, (mw, sw) = fifos
    source = FifoSource(meter, spectrum)
    os.write(mw, meter_frame(1, 2) + meter_frame(3, 4) + meter_frame(60, 63))
    os.write(sw, spectrum_frame((1,) * 30) + spectrum_frame(tuple(range(30))))

    levels = source.read()

    assert (levels.left, levels.right) == (60, 63)
    assert levels.bands == tuple(range(30))
    source.close()


def test_nothing_new_holds_the_last_frame(fifos):
    meter, spectrum, (mw, _) = fifos
    source = FifoSource(meter, spectrum)
    os.write(mw, meter_frame(60, 63))
    source.read()

    again = source.read()

    assert (again.left, again.right) == (60, 63)
    source.close()


def test_a_partial_frame_is_not_read_as_levels(fifos):
    meter, spectrum, (mw, _) = fifos
    source = FifoSource(meter, spectrum)
    os.write(mw, b"\x01\x02")

    assert (source.read().left, source.read().right) == (0, 0)
    source.close()


def test_an_absent_pipe_is_not_fatal(tmp_path):
    source = FifoSource(str(tmp_path / "absent"), str(tmp_path / "gone"))
    assert source.read() == Levels(0, 0, (0,) * 30)
    source.close()


def test_read_latest_frame_returns_none_when_empty(fifos):
    meter, _, _ = fifos
    fd = os.open(meter, os.O_RDONLY | os.O_NONBLOCK)
    assert read_latest_frame(fd, METER_FRAME) is None
    os.close(fd)


def test_passthrough_writes_frames_a_reader_can_parse(tmp_path):
    meter, spectrum = str(tmp_path / "pm"), str(tmp_path / "ps")
    passthrough = FifoPassthrough(meter, spectrum)
    readers = [os.open(p, os.O_RDONLY | os.O_NONBLOCK) for p in (meter, spectrum)]

    passthrough.publish(Levels(60, 63, tuple(range(30))))

    assert parse_meter(os.read(readers[0], 4)) == (60, 63)
    assert parse_spectrum(os.read(readers[1], 120)) == tuple(range(30))
    for fd in readers:
        os.close(fd)
    passthrough.close()


def test_passthrough_with_no_reader_is_silent(tmp_path):
    passthrough = FifoPassthrough(str(tmp_path / "pm"), str(tmp_path / "ps"))
    passthrough.publish(Levels(1, 2, (3,) * 30))  # must not raise
    passthrough.close()


async def test_the_websocket_publishes_levels(tmp_path):
    source = FifoSource(str(tmp_path / "absent"), str(tmp_path / "gone"))
    server = MeterServer(source)
    async with TestClient(TestServer(server.make_app())) as client:
        async with client.ws_connect("/meter") as ws:
            await server.publish(Levels(60, 63, tuple(range(30))))
            message = await asyncio.wait_for(ws.receive_json(), timeout=2)

    assert message == {"left": 60, "right": 63, "mono": 62, "bands": list(range(30))}
    source.close()
