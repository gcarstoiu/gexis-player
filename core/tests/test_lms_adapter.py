"""Unit tests for the parts of LmsAdapter that don't need a network.

signal_stop went through a full revert-then-restore-then-revert,
2026-09-06 through 2026-09-11 - see adapters/lms.py's class-level comment
for the reasoning behind each. As of 2026-09-11 (second time) it always
sends SIGKILL regardless of the ladder rung that called it, relying on
systemd's own Restart=on-failure to bring squeezelite back - a same-day
attempt at an adapter-driven explicit restart (stop_unit/
restart_after_release) was reverted after live use reproduced the exact
residual risk that attempt's own docs had already named. release_ladder
has no override (the supervisor's default grace periods are used, made to
work by -C 1 on squeezelite.service, not by adapter-specific timing).
These tests guard the two independently - a future attempt to "simplify"
by reverting signal_stop again should fail loudly, not silently reproduce
a defect this project already paid for twice.

The CometD/JSON-RPC parts need a real LMS server and are covered by live
hardware sessions instead (see adapters/lms.py's own module docstring).
"""
from __future__ import annotations

import pytest

from gexis_core.adapters.lms import LmsAdapter
from gexis_core.model import TrackMetadata


@pytest.mark.asyncio
async def test_signal_stop_always_sends_sigkill_regardless_of_force(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "gexis_core.adapters.lms.kill_unit",
        lambda unit, force: calls.append((unit, force)),
    )

    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")

    await adapter.signal_stop(force=False)  # the ladder's "SIGTERM" rung
    await adapter.signal_stop(force=True)  # the ladder's "SIGKILL" rung

    assert calls == [
        ("squeezelite.service", True),
        ("squeezelite.service", True),
    ]


def test_no_release_ladder_override():
    # -C 1 (squeezelite.service) makes the supervisor's default grace
    # periods work fine for LMS - no per-adapter timing override needed.
    # Escalation frequency and escalation signal are independent
    # decisions; this test is only about the former.
    assert LmsAdapter.release_ladder is None


@pytest.mark.asyncio
async def test_restart_after_release_is_the_inherited_noop():
    # Reverted 2026-09-11 (same day as introduced) - squeezelite's own
    # restart is systemd's job again (Restart=on-failure), not this
    # adapter's. Guards against silently reintroducing the override
    # without also reconsidering signal_stop's mechanism alongside it -
    # the two were designed and reverted as a pair, not independently.
    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")
    assert await adapter.restart_after_release() is None


# --- ADR-0027: pause-then-power-off, and replaying what the user left ------


class FakeRpc:
    """Records the commands `release()`/`device_freed()` send, and answers
    the status queries they make. Stands in for the whole aiohttp session so
    these stay tier-1 tests with no network.

    `mode`/`position` are what the *next* status query reports, so a test can
    change them between `release()` and `device_freed()` to model what LMS
    did in between - restarting the track from zero, say."""

    def __init__(self, mode="play", position=60.0):
        self.mode = mode
        self.position = position
        self.commands = []

    async def __call__(self, session, player, command):
        self.commands.append(list(command))
        if command[0] == "status":
            return {"result": {"mode": self.mode, "power": 1, "time": self.position}}
        return {"result": {}}


def _adapter(monkeypatch, mode, position=60.0):
    rpc = FakeRpc(mode, position)
    monkeypatch.setattr(LmsAdapter, "_rpc", rpc)
    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")
    adapter._player_id = "aa:bb:cc:dd:ee:ff"
    return adapter, rpc


@pytest.mark.asyncio
async def test_release_pauses_before_powering_off(monkeypatch):
    """Order is the whole point (ADR-0027, Finding 018). Powering off a
    *playing* player makes LMS restore it as playing, which fires
    squeezelite's ALSA open 58ms later against a device the incoming
    renderer hasn't released - it fails and then waits out an untunable 5s
    retry tick. Pausing first means it is restored paused and makes no
    attempt at all."""
    adapter, rpc = _adapter(monkeypatch, mode="play")

    assert await adapter.release() is True

    assert rpc.commands == [["status", "-", 1], ["pause", 1], ["power", 0]]


@pytest.mark.asyncio
async def test_release_records_that_it_was_playing_and_device_freed_resumes(monkeypatch):
    adapter, rpc = _adapter(monkeypatch, mode="play")
    await adapter.release()
    rpc.mode = "pause"  # LMS restored it paused, as powering on a paused player does
    rpc.commands.clear()

    await adapter.device_freed()

    # A status probe first - device_freed has to see what LMS actually did
    # before deciding what to put back - then the resume itself.
    assert ["play"] in rpc.commands


@pytest.mark.asyncio
async def test_a_player_left_paused_comes_back_paused(monkeypatch):
    """George, 2026-09-12: the transport state on return is whatever the
    user left, never something we impose. A paused player gets no play."""
    adapter, rpc = _adapter(monkeypatch, mode="pause")
    await adapter.release()
    rpc.commands.clear()

    await adapter.device_freed()

    assert ["play"] not in rpc.commands


@pytest.mark.asyncio
async def test_the_resume_fires_once_not_on_every_later_acquisition(monkeypatch):
    """Otherwise a user who activates the player themselves, long after an
    unrelated takeover, would have playback start under them."""
    adapter, rpc = _adapter(monkeypatch, mode="play")
    await adapter.release()
    await adapter.device_freed()
    rpc.commands.clear()

    await adapter.device_freed()

    assert rpc.commands == []


@pytest.mark.asyncio
async def test_device_freed_sends_nothing_without_a_preceding_release(monkeypatch):
    """Activating the player with no takeover involved - first boot, or the
    user turning it on after turning it off themselves. LMS restores its own
    transport state natively there; we must not add a play on top."""
    adapter, rpc = _adapter(monkeypatch, mode="play")

    await adapter.device_freed()

    assert rpc.commands == []


# --- ADR-0027: the position re-anchor -------------------------------------


@pytest.mark.asyncio
async def test_position_is_restored_when_lms_restarted_the_track(monkeypatch):
    """The press-play route. Pressing play on a deactivated player makes LMS
    power it on and restart from zero - its own documented auto-power-on,
    which happens before our acquisition even reaches us. Measured on
    hardware 2026-09-12: deactivated at 24.4s, back at 2.3s."""
    adapter, rpc = _adapter(monkeypatch, mode="play", position=60.0)
    await adapter.release()          # records playing at 60s
    rpc.position = 1.2               # LMS restarted the track
    rpc.commands.clear()

    await adapter.device_freed()

    assert ["time", "60.00"] in rpc.commands


@pytest.mark.asyncio
async def test_no_seek_when_the_position_survived(monkeypatch):
    """The activate route, which restores the player at exactly the stored
    position. A seek makes LMS re-request the stream, so it is not worth
    spending when there is nothing to correct."""
    adapter, rpc = _adapter(monkeypatch, mode="play", position=60.0)
    await adapter.release()
    rpc.position = 60.1              # came back where it left off
    rpc.commands.clear()

    await adapter.device_freed()

    assert not any(c[0] == "time" for c in rpc.commands)


@pytest.mark.asyncio
async def test_position_restored_even_for_a_player_left_paused(monkeypatch):
    """LMS restarts from zero whichever transport state the player was in, so
    the correction cannot be conditional on the play/pause flag. The user
    pressed play, so it stays playing - only the position was wrong."""
    adapter, rpc = _adapter(monkeypatch, mode="pause", position=45.0)
    await adapter.release()          # records paused at 45s
    rpc.mode = "play"                # LMS auto-powered-on and started
    rpc.position = 0.8
    rpc.commands.clear()

    await adapter.device_freed()

    assert ["time", "45.00"] in rpc.commands
    assert ["play"] not in rpc.commands  # it is already playing; don't impose


@pytest.mark.asyncio
async def test_the_seek_fires_once_not_on_every_later_acquisition(monkeypatch):
    adapter, rpc = _adapter(monkeypatch, mode="play", position=60.0)
    await adapter.release()
    rpc.position = 1.0
    await adapter.device_freed()
    rpc.commands.clear()

    await adapter.device_freed()

    assert rpc.commands == []


# --- the user's own deactivation, not a takeover ---------------------------


@pytest.mark.asyncio
async def test_position_noted_when_the_user_deactivates_the_player(monkeypatch):
    """George, 2026-09-12: "after a deactivation the player starts from 0".
    `release()` only runs for a takeover, so a user powering the player off
    themselves recorded nothing and there was nothing to seek back to.
    ADR-0027 makes deactivation an ordinary user action, so it has to be
    covered too."""
    adapter, rpc = _adapter(monkeypatch, mode="play", position=72.0)

    await adapter._note_position_if_unset(session=None)

    assert adapter._resume_position == 72.0
    # The transport state is deliberately untouched: LMS restores that
    # natively on power-on for a deactivation it owns.
    assert adapter._resume_playing is False


@pytest.mark.asyncio
async def test_a_takeover_recording_is_not_overwritten_by_the_power_off_echo(monkeypatch):
    """Our own release powers the player off, so the same edge fires ~0.5s
    later. `release()`'s value is the better one - read before the pause,
    and carrying the play/pause state a powered-off player no longer
    reports - so the echo must not clobber it."""
    adapter, rpc = _adapter(monkeypatch, mode="play", position=39.9)
    await adapter.release()
    assert adapter._resume_playing is True

    rpc.position = 0.0  # what a powered-off player might report
    await adapter._note_position_if_unset(session=None)

    assert adapter._resume_position == 39.9
    assert adapter._resume_playing is True


# --- Phase 3 criterion 1: metadata reporting -------------------------------


def _status_result(**overrides) -> dict:
    """A JSON-RPC "status" result shaped the way LMS actually nests it -
    per-song tags inside `playlist_loop[0]`, player-level fields (power,
    mode, time, duration, current_title, remote) at the top level. See
    `_report_metadata`'s own docstring for the sourcing."""
    song = {
        "title": "Song Title",
        "artist": "The Artist",
        "album": "The Album",
        "coverid": "abc123",
        "samplerate": 44100,
    }
    song.update(overrides.pop("song", {}))
    result = {
        "power": 1,
        "mode": "play",
        "time": 30.5,
        "duration": 200.0,
        "playlist_loop": [song],
    }
    result.update(overrides)
    return result


def test_report_metadata_maps_the_current_song():
    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")
    received = []
    adapter.on_metadata_change(received.append)

    adapter._report_metadata(_status_result())

    assert received == [
        TrackMetadata(
            title="Song Title",
            artist="The Artist",
            album="The Album",
            artwork="http://127.0.0.1:9000/music/abc123/cover.jpg",
            sample_rate=44100,
            position=30.5,
            duration=200.0,
            source_type="lms",
            transport="playing",
        )
    ]


def test_report_metadata_uses_current_title_for_remote_streams():
    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")
    received = []
    adapter.on_metadata_change(received.append)

    adapter._report_metadata(
        _status_result(remote=1, current_title="Radio Station: Now Playing")
    )

    assert received[0].title == "Radio Station: Now Playing"


def test_report_metadata_blanks_artwork_without_a_coverid():
    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")
    received = []
    adapter.on_metadata_change(received.append)

    adapter._report_metadata(_status_result(song={"coverid": None}))

    assert received[0].artwork is None


def test_report_metadata_is_a_noop_without_a_registered_callback():
    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")
    adapter._report_metadata(_status_result())  # must not raise


def test_report_metadata_handles_an_empty_playlist_loop():
    """A status result before anything has ever loaded (fresh boot, nothing
    queued) - must blank the fields, not raise on a missing index."""
    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")
    received = []
    adapter.on_metadata_change(received.append)

    adapter._report_metadata({"power": 0, "playlist_loop": []})

    assert received[0].title is None
    assert received[0].artwork is None


@pytest.mark.asyncio
async def test_deactivate_then_press_play_seeks_back(monkeypatch):
    """The exact sequence George reported: deactivate, then press play -
    LMS powers the player on and restarts from zero."""
    adapter, rpc = _adapter(monkeypatch, mode="play", position=72.0)
    await adapter._note_position_if_unset(session=None)  # user deactivated

    rpc.mode = "play"
    rpc.position = 1.1  # LMS auto-powered-on and restarted
    rpc.commands.clear()

    await adapter.device_freed()

    assert ["time", "72.00"] in rpc.commands


# --- ADR-0037: transport commands -----------------------------------------


@pytest.mark.asyncio
async def test_pause_sends_pause_1(monkeypatch):
    adapter, rpc = _adapter(monkeypatch, mode="play")

    assert await adapter.pause() is True

    assert rpc.commands == [["pause", 1]]


@pytest.mark.asyncio
async def test_play_resumes_a_paused_player_with_pause_0(monkeypatch):
    """`play` on some LMS versions restarts the track; `pause 0` resumes
    where it stopped (Finding 028)."""
    adapter, rpc = _adapter(monkeypatch, mode="pause")
    adapter._report_metadata({"mode": "pause", "time": 55.9})

    assert await adapter.play() is True

    assert rpc.commands == [["pause", 0]]


@pytest.mark.asyncio
async def test_play_starts_a_stopped_player_with_play(monkeypatch):
    adapter, rpc = _adapter(monkeypatch, mode="stop")
    adapter._report_metadata({"mode": "stop"})

    assert await adapter.play() is True

    assert rpc.commands == [["play"]]


@pytest.mark.asyncio
async def test_a_command_without_a_resolved_player_fails_rather_than_pretending(monkeypatch):
    adapter, rpc = _adapter(monkeypatch, mode="play")
    adapter._player_id = None

    assert await adapter.pause() is False
    assert rpc.commands == []
