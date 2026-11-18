# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0183: Spotify keeps playing on the lead through a group change."""
from __future__ import annotations

import pytest

from gexis_core import rechain


class FakeSpotify:
    def __init__(self, playing, *, pause_ok=True, play_ok=True, log=None):
        self.playing = playing
        self.pause_ok = pause_ok
        self.play_ok = play_ok
        self.log = log if log is not None else []

    async def playing_now(self):
        self.log.append("status")
        return self.playing

    async def pause(self):
        self.log.append("pause")
        return self.pause_ok

    async def play(self):
        self.log.append("resume")
        return self.play_ok


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    async def sleep(self, seconds):
        self.now += seconds


def _run(spotify, *, held_for=0, clock=None, rewrite_takes=0.0):
    """`held_for`: how many polls the device stays held after the pause."""
    clock = clock or Clock()
    polls = {"n": 0}

    def holds():
        polls["n"] += 1
        return polls["n"] <= held_for

    async def rewrite():
        spotify.log.append("rewrite")
        clock.now += rewrite_takes

    return rechain.keep_spotify_playing(spotify, holds=holds, rewrite=rewrite, sleep=clock.sleep, clock=clock)


@pytest.mark.asyncio
async def test_playing_spotify_is_paused_the_chain_rewritten_and_it_resumes():
    spotify = FakeSpotify(True)
    assert await _run(spotify, held_for=2, rewrite_takes=1.5) is True
    assert spotify.log == ["status", "pause", "rewrite", "resume"]


@pytest.mark.asyncio
async def test_a_paused_session_is_rewritten_under_and_left_paused():
    spotify = FakeSpotify(False)
    assert await _run(spotify) is True
    assert spotify.log == ["status", "rewrite"]


@pytest.mark.asyncio
@pytest.mark.parametrize("playing, pause_ok, held_for", [
    (None, True, 0),       # the state could not be read
    (True, False, 0),      # the pause refused
    (True, True, 10_000),  # the device never let go
])
async def test_nothing_is_written_when_spotify_cannot_be_kept(playing, pause_ok, held_for):
    spotify = FakeSpotify(playing, pause_ok=pause_ok)
    assert await _run(spotify, held_for=held_for) is False
    assert "rewrite" not in spotify.log and "resume" not in spotify.log


@pytest.mark.asyncio
async def test_the_device_is_waited_for_no_longer_than_its_limit():
    clock = Clock()
    spotify = FakeSpotify(True)
    assert await _run(spotify, held_for=10_000, clock=clock) is False
    assert clock.now - 100.0 == pytest.approx(rechain.LET_GO_S)


@pytest.mark.asyncio
async def test_a_quick_rewrite_still_resumes_after_go_librespots_state_interval():
    """A resume within 200 ms of the pause would leave the paused state
    unsent to the phone (go-librespot's `statePutMinInterval`)."""
    clock = Clock()
    spotify = FakeSpotify(True)
    paused_at = {}

    async def pause():
        spotify.log.append("pause")
        paused_at["t"] = clock.now
        return True

    async def play():
        spotify.log.append("resume")
        paused_at["resumed"] = clock.now
        return True

    spotify.pause, spotify.play = pause, play
    assert await _run(spotify, clock=clock, rewrite_takes=0.05) is True
    assert paused_at["resumed"] - paused_at["t"] >= rechain.SETTLE_S


@pytest.mark.asyncio
async def test_a_refused_resume_is_still_a_rewrite_done():
    spotify = FakeSpotify(True, play_ok=False)
    assert await _run(spotify) is True
    assert spotify.log[-1] == "resume"
