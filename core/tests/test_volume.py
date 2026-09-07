"""Unit tests for the volume bridge's echo suppression and per-renderer
memory attribution (criterion 5).

Regression coverage for a real ratchet-to-zero measured on hardware,
2026-09-06, and for the per-renderer-volume decision, 2026-09-07 (see
volume.py's module docstring for both). Only `_on_spotify_volume` is
exercised directly here - `run()`'s `alsactl monitor` side needs a real
subprocess and isn't covered by these tests; the shared
`_within_echo_window` and remember/apply logic is the same code path
either way.
"""
from __future__ import annotations

import asyncio
import time as time_module

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


class FakeVolumeMemory:
    def __init__(self):
        self.remembered: list[tuple[str, int]] = []

    def remember(self, renderer_id, raw):
        self.remembered.append((renderer_id, raw))

    def get(self, renderer_id):
        for rid, raw in reversed(self.remembered):
            if rid == renderer_id:
                return raw
        return None


@pytest.fixture(autouse=True)
def fake_set_raw(monkeypatch):
    calls = []

    async def fake(mixer_name, value):
        calls.append((mixer_name, value))

    monkeypatch.setattr(volume_module, "set_raw", fake)
    return calls


def make_bridge(active="spotify"):
    memory = FakeVolumeMemory()
    bridge = VolumeBridge(
        "DAC", FakeSpotify(), volume_memory=memory, get_active_renderer=lambda: active
    )
    return bridge, memory


@pytest.mark.asyncio
async def test_spotify_echo_within_window_is_ignored(fake_set_raw):
    bridge, _ = make_bridge()
    bridge._last_own_write = time_module.monotonic()  # "we just wrote"

    bridge._on_spotify_volume(71, 100)
    await asyncio.sleep(0)  # let any scheduled task run

    assert fake_set_raw == []


@pytest.mark.asyncio
async def test_genuine_spotify_change_outside_window_is_applied(fake_set_raw):
    bridge, memory = make_bridge()
    bridge._last_own_write = 0.0  # long ago

    bridge._on_spotify_volume(50, 100)
    await asyncio.sleep(0)

    assert fake_set_raw == [("DAC", 120)]  # 50/100 * 240
    assert memory.remembered == [("spotify", 120)]


@pytest.mark.asyncio
async def test_spotify_volume_arms_the_window_so_a_second_echo_is_also_dropped(fake_set_raw):
    bridge, _ = make_bridge()
    bridge._last_own_write = 0.0

    bridge._on_spotify_volume(50, 100)
    await asyncio.sleep(0)
    assert fake_set_raw == [("DAC", 120)]

    # A second event arriving immediately after (e.g. a duplicate WS
    # frame) is inside the window this write just armed.
    bridge._on_spotify_volume(51, 100)
    await asyncio.sleep(0)
    assert fake_set_raw == [("DAC", 120)]  # unchanged - second call ignored


@pytest.mark.asyncio
async def test_spotify_volume_while_inactive_is_remembered_not_applied(fake_set_raw):
    """Spotify isn't the active renderer - its own volume report must not
    move the mixer someone else currently owns, but should still be
    remembered for when it next becomes active."""
    bridge, memory = make_bridge(active="lms")
    bridge._last_own_write = 0.0

    bridge._on_spotify_volume(50, 100)
    await asyncio.sleep(0)

    assert fake_set_raw == []  # not applied to the live mixer
    assert memory.remembered == [("spotify", 120)]  # but remembered


def test_echo_window_is_positive_and_not_absurdly_long():
    # Sanity bound, not a precise spec - see module docstring on why this
    # is a mitigation rather than a proven-convergent design.
    assert 0 < ECHO_WINDOW_S < 5
