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


class TestTheSpectrumFrameMatchesTheReader:
    """**A FIFO carries bytes, not messages** (Finding 051).

    PeppySpectrum reads `4 * size` bytes at a time, where `size` is the bar
    count the driver writes per skin. peppyalsa measures 30 bands. When the
    two differ, the reader takes 88 bytes out of a stream of 120-byte
    records and every bar shows a different band from one refresh to the
    next - which on the panel is a flashing spectrum, and is immune to any
    amount of smoothing upstream.
    """

    def test_a_matching_count_is_passed_through_untouched(self):
        from gexis_core.meters import resample

        bands = tuple(range(30))
        assert resample(bands, 30) is bands

    def test_no_declared_count_changes_nothing(self):
        from gexis_core.meters import resample

        bands = tuple(range(30))
        assert resample(bands, None) is bands
        assert resample(bands, 0) is bands

    def test_thirty_bands_fold_into_the_bars_a_skin_draws(self):
        from gexis_core.meters import resample

        bands = tuple(range(30))
        for want in (20, 21, 22):
            out = resample(bands, want)
            assert len(out) == want, want
            # every measurement is accounted for, and none is invented
            assert max(out) == max(bands)
            assert min(out) <= min(bands) + 1

    def test_a_group_reports_its_peak_not_its_mean(self):
        from gexis_core.meters import resample

        # 30 -> 15 is two bands per bar; the loud one must survive
        bands = tuple(100 if i % 2 else 0 for i in range(30))
        assert set(resample(bands, 15)) == {100}

    def test_it_never_invents_bands(self):
        from gexis_core.meters import resample

        bands = tuple(range(10))
        assert resample(bands, 30) is bands

    def test_the_declared_size_is_read_from_the_engines_own_config(self, tmp_path):
        from gexis_core.meters import read_declared_size

        conf = tmp_path / "config.txt"
        conf.write_text("[current]\nspectrum = Free\nsize = 22\nframe.rate = 30\n")
        assert read_declared_size(str(conf)) == 22
        assert read_declared_size(str(tmp_path / "nope.txt")) is None


class TestTheMetersFollowTheVolume:
    """**The meter tap is upstream of the DAC's attenuator** (ADR-0057).

    `pcm.output` is a `type meter` over the card and the hardware volume is
    applied afterwards, so nothing the volume control does reaches the
    needles or the bars unless it is applied here. George, 2026-09-23:
    *"Shouldn't the vu meters and spectrum amplitude be based on volume?
    And only on fixed volume be like it is now?"*
    """

    def test_no_attenuation_changes_nothing(self):
        from gexis_core.meters import Levels, attenuate

        levels = Levels(80, 70, (50,) * 30)
        assert attenuate(levels, 0) is levels
        assert attenuate(levels, -3) is levels

    def test_the_vu_level_is_linear_so_it_is_scaled(self):
        from gexis_core.meters import Levels, attenuate

        # tracking=1 is the physically exact case: -6 dB is half the
        # amplitude, -20 dB is a tenth
        assert attenuate(Levels(100, 50, ()), 6.02, tracking=1).left == 50
        assert attenuate(Levels(100, 50, ()), 20, tracking=1).left == 10
        assert attenuate(Levels(100, 50, ()), 20, tracking=1).right == 5

    def test_the_spectrum_is_logarithmic_so_it_is_shifted(self):
        from gexis_core.meters import SPECTRUM_DB_FULL_SCALE, Levels, attenuate

        # one unit is 96.3/100 dB, so 20 dB is about 21 units off every bar
        out = attenuate(Levels(0, 0, (90, 60, 30)), 20, tracking=1).bands
        shift = round(20 * 100 / SPECTRUM_DB_FULL_SCALE)
        assert out == (90 - shift, 60 - shift, 30 - shift)

    def test_nothing_goes_below_silence(self):
        from gexis_core.meters import Levels, attenuate

        out = attenuate(Levels(5, 5, (10, 2)), 60, tracking=1)
        assert out.left == 0 and out.right == 0
        assert out.bands == (0, 0)

    def test_the_needle_stays_alive_across_the_whole_slider(self):
        """**60 dB of volume onto a dial drawn for 20** puts the needle at
        the bottom stop from about 40% down, which George saw as *"a bit
        quiet on the bottom part"*. The volume curve is not up for changing
        (his call, 2026-09-23), so the meters follow a third of it.
        """
        from gexis_core.meters import Levels, attenuate

        full = Levels(100, 100, (60,) * 22)
        # the dB the 60 dB cubic curve cuts at each slider position
        reads = {percent: attenuate(full, db).left
                 for percent, db in ((100, 0.0), (60, 11.6), (40, 20.2), (20, 33.2), (10, 43.3))}
        assert reads[100] == 100
        # every position below full is lower than the one above it
        assert list(reads.values()) == sorted(reads.values(), reverse=True)
        # and none of them is at the stop - the needle still moves at 10%
        assert reads[10] > 15, reads
        assert reads[40] > 40, reads

    def test_the_bars_stay_visible_too(self):
        from gexis_core.meters import Levels, attenuate

        full = Levels(0, 0, (60,) * 22)
        assert min(attenuate(full, 54.0).bands) > 30

    def test_fixed_output_needs_no_special_case(self):
        """In fixed output the DAC sits at full scale, so the attenuation
        the daemon publishes is 0 and the meters show the source - which is
        what George asked for there, without a branch to get wrong."""
        from gexis_core.meters import Levels, attenuate

        levels = Levels(80, 70, (50,) * 22)
        assert attenuate(levels, 0.0) is levels

    def test_the_writer_and_the_reader_name_the_same_file(self):
        """A meter reading a path nobody writes would show the source level
        and say nothing about it (LESSONS case 20)."""
        from gexis_core.config import Config
        from gexis_core.volume import ATTENUATION_PATH

        assert Config().attenuation_path == str(ATTENUATION_PATH)

    def test_an_unreadable_file_means_no_attenuation(self, tmp_path):
        from gexis_core.meters import read_attenuation

        assert read_attenuation(tmp_path / "nope") == 0.0
        bad = tmp_path / "bad"
        bad.write_text("not a number")
        assert read_attenuation(bad) == 0.0
        good = tmp_path / "good"
        good.write_text("18.50\n")
        assert read_attenuation(good) == 18.5

    def test_the_daemon_publishes_the_dB_it_is_cutting(self, tmp_path):
        from gexis_core.meters import read_attenuation
        from gexis_core.volume import publish_attenuation

        path = tmp_path / "attenuation"
        publish_attenuation(240, path)          # full scale
        assert read_attenuation(path) == 0.0
        assert path.read_text().strip() == "0.00", "full scale must not read -0.00"
        publish_attenuation(200, path)          # 40 steps of 0.5 dB
        assert read_attenuation(path) == 20.0
        publish_attenuation(0, path)            # silence
        assert read_attenuation(path) == 120.0


class TestFoldingKeepsTheWholeSpectrum:
    """**George, 2026-09-23:** *"Does that mean that for certain skins the
    upper frequencies represented by the outer right bars will not be
    shown?"*

    No: the fold merges, it does not truncate. Pinned here because the
    obvious wrong implementation - draw the first N bands and drop the rest
    - looks identical on a still screen and silently loses the top of the
    spectrum.
    """

    def test_every_band_lands_in_exactly_one_bar(self):
        """One band at a time, so the answer cannot come from repeating the
        implementation's own arithmetic."""
        from gexis_core.meters import resample

        for want in range(15, 30):
            for band in range(30):
                one_hot = tuple(100 if i == band else 0 for i in range(30))
                out = resample(one_hot, want)
                assert len(out) == want, want
                lit = [i for i, v in enumerate(out) if v]
                assert lit == [min(want - 1, band * want // 30)] or len(lit) == 1, (
                    f"band {band} of 30 into {want} bars lit {lit}"
                )
                assert sum(out) == 100, f"band {band} of 30 into {want} bars was dropped"

    def test_the_top_of_the_spectrum_is_the_rightmost_bar(self):
        from gexis_core.meters import resample

        for want in range(15, 30):
            top = tuple(0 for _ in range(29)) + (100,)
            assert resample(top, want)[-1] == 100, want
            bottom = (100,) + tuple(0 for _ in range(29))
            assert resample(bottom, want)[0] == 100, want

    def test_the_doubling_is_spread_rather_than_bunched(self):
        from gexis_core.meters import resample

        bands = tuple(range(30))
        out = resample(bands, 19)
        widths = [b - a for a, b in zip((-1,) + out[:-1], out)]
        assert set(widths) == {1, 2}
        # no run of three consecutive doubled groups
        assert "2, 2, 2" not in ", ".join(str(w) for w in widths)


def test_the_read_is_a_whole_number_of_frames(monkeypatch):
    """**A pipe carries bytes.** Reading a chunk that is not a multiple of the
    frame would truncate the last record and splice it onto the next read -
    the fault Finding 052 is about, reintroduced on this side."""
    import os as real_os
    from gexis_core import meters

    asked = []

    def fake_read(fd, n):
        asked.append(n)
        return b""

    monkeypatch.setattr(meters.os, "read", fake_read)
    meters.read_latest_frame(3, 120)
    meters.read_latest_frame(3, 4)
    assert asked, "the read was never attempted"
    for n, frame in zip(asked, (120, 4)):
        assert n % frame == 0, (n, frame)
        assert n > 0
