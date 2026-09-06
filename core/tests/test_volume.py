"""Unit tests for the volume bridge's echo suppression (criterion 5).

Regression coverage for a real ratchet-to-zero measured on hardware,
2026-09-06 (see volume.py's module docstring). Only `_on_spotify_volume`
is exercised directly here - `run()`'s `alsactl monitor` side needs a
real subprocess and isn't covered by these tests; the shared
`_within_echo_window` check is the same code path either way.
"""
from __future__ import annotations

import asyncio

import pytest

from gexis_core import volume as volume_module
from gexis_core.volume import ECHO_WINDOW_S, VolumeBridge


class FakeSpotify:
    def __init__(self):
        self._callback = None

    def on_volume_change(self, callback):
        self._callback = callback

    async def get_volume_steps(self):
        return 100

    async def set_volume(self, value):
        pass


@pytest.fixture(autouse=True)
def fake_set_raw(monkeypatch):
    calls = []

    async def fake(mixer_name, value):
        calls.append((mixer_name, value))

    monkeypatch.setattr(volume_module, "set_raw", fake)
    return calls


@pytest.mark.asyncio
async def test_spotify_echo_within_window_is_ignored(fake_set_raw):
    import time as time_module

    bridge = VolumeBridge("DAC", FakeSpotify())
    bridge._last_own_write = time_module.monotonic()  # "we just wrote"

    bridge._on_spotify_volume(71, 100)
    await asyncio.sleep(0)  # let any scheduled task run

    assert fake_set_raw == []


@pytest.mark.asyncio
async def test_genuine_spotify_change_outside_window_is_applied(fake_set_raw):
    bridge = VolumeBridge("DAC", FakeSpotify())
    bridge._last_own_write = 0.0  # long ago

    bridge._on_spotify_volume(50, 100)
    await asyncio.sleep(0)

    assert fake_set_raw == [("DAC", 120)]  # 50/100 * 240


@pytest.mark.asyncio
async def test_spotify_volume_arms_the_window_so_a_second_echo_is_also_dropped(fake_set_raw):
    bridge = VolumeBridge("DAC", FakeSpotify())
    bridge._last_own_write = 0.0

    bridge._on_spotify_volume(50, 100)
    await asyncio.sleep(0)
    assert fake_set_raw == [("DAC", 120)]

    # A second event arriving immediately after (e.g. a duplicate WS
    # frame) is inside the window this write just armed.
    bridge._on_spotify_volume(51, 100)
    await asyncio.sleep(0)
    assert fake_set_raw == [("DAC", 120)]  # unchanged - second call ignored


def test_echo_window_is_positive_and_not_absurdly_long():
    # Sanity bound, not a precise spec - see module docstring on why this
    # is a mitigation rather than a proven-convergent design.
    assert 0 < ECHO_WINDOW_S < 5
