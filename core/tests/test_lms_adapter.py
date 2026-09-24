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

import asyncio

import aiohttp
import pytest

from gexis_core.adapters.lms import QUEUE_CEILING, QUEUE_LIMIT, LmsAdapter
from gexis_core.model import TrackMetadata


async def _done(value):
    """A coroutine that just answers, for stubbing an awaited method."""
    return value


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
    did in between - restarting the track from zero, say. `timestamp` is
    the queue's `playlist_timestamp`; a test changes it to model a load or
    an edit, and sets it to None for an LMS that does not report one."""

    def __init__(self, mode="play", position=60.0):
        self.mode = mode
        self.position = position
        self.timestamp = 1789663581.32885
        self.commands = []

    async def __call__(self, session, player, command):
        self.commands.append(list(command))
        if command[0] == "status":
            result = {"mode": self.mode, "power": 1, "time": self.position}
            if self.timestamp is not None:
                result["playlist_timestamp"] = self.timestamp
            return {"result": result}
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


# --- Finding 029 defect A: never put the old queue's state onto a new one --


@pytest.mark.asyncio
async def test_a_load_while_away_is_not_seeked_to_the_old_position(monkeypatch):
    """Measured 2026-09-17: a radio station released at 192.6s, then an album
    loaded from an LMS app while Spotify played. Loading powers LMS on and
    starts track 1 at zero - and the core seeked it to 192.6s. A load changes
    `playlist_timestamp`, so nothing is restored."""
    adapter, rpc = _adapter(monkeypatch, mode="play", position=192.6)
    await adapter.release()
    rpc.timestamp = 1789664147.20098  # a new load
    rpc.position = 0.0
    rpc.commands.clear()

    await adapter.device_freed()

    assert not any(c[0] == "time" for c in rpc.commands)
    assert ["play"] not in rpc.commands


@pytest.mark.asyncio
async def test_reloading_the_same_content_is_still_a_new_load(monkeypatch):
    """Loading the album that was already playing changes the timestamp too
    (measured). The user asked for it from the start, so no seek."""
    adapter, rpc = _adapter(monkeypatch, mode="play", position=80.0)
    await adapter.release()
    rpc.timestamp += 12.5
    rpc.position = 2.4
    rpc.commands.clear()

    await adapter.device_freed()

    assert not any(c[0] == "time" for c in rpc.commands)


@pytest.mark.asyncio
async def test_a_paused_player_given_new_content_gets_no_play(monkeypatch):
    """Released while playing, then the queue replaced but left stopped:
    playing it would start music the user did not ask for."""
    adapter, rpc = _adapter(monkeypatch, mode="play", position=30.0)
    await adapter.release()
    rpc.mode = "stop"
    rpc.timestamp += 40.0
    rpc.commands.clear()

    await adapter.device_freed()

    assert ["play"] not in rpc.commands


@pytest.mark.asyncio
async def test_an_edit_while_away_loses_the_position(monkeypatch):
    """George's rule A, 2026-09-17: an add or a shuffle also changes the
    timestamp, and the position is then not restored. Accepted, because it
    can never seek into content the user just chose."""
    adapter, rpc = _adapter(monkeypatch, mode="play", position=60.0)
    await adapter.release()
    rpc.timestamp += 7.5  # cmd:add while another renderer held the device
    rpc.position = 1.2
    rpc.commands.clear()

    await adapter.device_freed()

    assert not any(c[0] == "time" for c in rpc.commands)


@pytest.mark.asyncio
async def test_a_skipped_restore_does_not_linger_for_a_later_acquisition(monkeypatch):
    adapter, rpc = _adapter(monkeypatch, mode="play", position=60.0)
    await adapter.release()
    rpc.timestamp += 1.0
    await adapter.device_freed()
    rpc.timestamp -= 1.0  # even if the old value came back
    rpc.position = 1.0
    rpc.commands.clear()

    await adapter.device_freed()

    assert rpc.commands == []


@pytest.mark.asyncio
async def test_same_queue_still_resumes_after_a_takeover(monkeypatch):
    """The ADR-0027 behaviour that must survive: pause, skip and the power
    cycle leave the timestamp alone (measured), so returning to the same
    queue is still put back."""
    adapter, rpc = _adapter(monkeypatch, mode="play", position=60.0)
    await adapter.release()
    rpc.mode = "pause"
    rpc.position = 1.2
    rpc.commands.clear()

    await adapter.device_freed()

    assert ["time", "60.00"] in rpc.commands
    assert ["play"] in rpc.commands


@pytest.mark.asyncio
async def test_an_lms_reporting_no_timestamp_behaves_as_before(monkeypatch):
    """Nothing to compare means nothing to learn from it; the ADR-0027
    restore stands rather than silently switching itself off."""
    adapter, rpc = _adapter(monkeypatch, mode="play", position=60.0)
    rpc.timestamp = None
    await adapter.release()
    rpc.position = 1.2
    rpc.commands.clear()

    await adapter.device_freed()

    assert ["time", "60.00"] in rpc.commands


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
            artwork="http://127.0.0.1:9000/music/abc123/cover_500x500_o.jpg",
            sample_rate=44100,
            position=30.5,
            duration=200.0,
            source_type="lms",
            transport="playing",
        )
    ]


def _radio(song, **top):
    """A stream's status result: only what LMS sends for one (no album,
    duration or samplerate unless a test adds them)."""
    adapter = LmsAdapter("192.168.178.188", 9000, "gexis")
    received = []
    adapter.on_metadata_change(received.append)
    result = {"power": 1, "mode": "play", "time": 6.6, "remote": 1, "playlist_loop": [song]}
    result.update(top)
    adapter._report_metadata(result)
    return received[0]


def test_a_station_shows_the_song_as_title_and_the_station_as_album():
    """Finding 029, measured 2026-09-17 on TuneIn "100% Deutsch": the core
    published the station as the title and dropped the song. ADR-0038 §8a,
    George's option A."""
    meta = _radio(
        {
            "title": "Hand in Hand",
            "artist": "Julian le Play",
            "coverid": "-94298681189064",
            "artwork_url": "/imageproxy/https%3A%2F%2Flastfm.freetls.fastly.net%2Fi%2Fu%2Fb97d5d1f.jpg/image.jpg",
            "remote": 1,
        },
        current_title="SCHLAGERPLANET RADIO Deutsch",
    )

    assert meta.title == "Hand in Hand"
    assert meta.artist == "Julian le Play"
    assert meta.album == "SCHLAGERPLANET RADIO Deutsch"
    assert meta.artwork == (
        "http://192.168.178.188:9000/imageproxy/"
        "https%3A%2F%2Flastfm.freetls.fastly.net%2Fi%2Fu%2Fb97d5d1f.jpg/image.jpg"
    )


def test_a_station_without_artwork_url_gets_no_artwork_not_the_placeholder():
    """The stream's coverid URL is LMS's grey radio tower (George saw it on the
    panel). None lets the panel show its own pending glyph."""
    meta = _radio({"title": "Hand in Hand", "artist": "Julian le Play", "coverid": "-1"},
                  current_title="SCHLAGERPLANET RADIO Deutsch")

    assert meta.artwork is None


def test_an_absolute_artwork_url_is_used_as_is():
    meta = _radio({"title": "T", "artwork_url": "https://cdn.example/logo.png"},
                  current_title="Station")

    assert meta.artwork == "https://cdn.example/logo.png"


def test_a_blank_current_title_keeps_the_song_fields():
    """Phase 6's KissFM case: `current_title` a single space, the names only
    in the song fields."""
    meta = _radio({"title": "#1 Hit Radio", "artist": "KissFM  Live!"}, current_title=" ")

    assert meta.title == "#1 Hit Radio"
    assert meta.artist == "KissFM  Live!"
    assert meta.album is None


def test_a_station_with_no_song_shows_the_station_as_title():
    meta = _radio({"title": "", "artist": None}, current_title="Talk Radio One")

    assert meta.title == "Talk Radio One"
    assert meta.album is None


def test_a_current_title_that_repeats_the_song_is_not_the_album():
    """2026-09-08: `current_title` was "Backstreet Boys - Anywhere for You"."""
    meta = _radio({"title": "Anywhere for You", "artist": "Backstreet Boys"},
                  current_title="Backstreet Boys - Anywhere for You")

    assert meta.title == "Anywhere for You"
    assert meta.album is None


def test_a_remote_track_with_a_real_album_keeps_it():
    """A Qobuz track through LMS is `remote` too, and has an album."""
    meta = _radio({"title": "Bad Guy", "artist": "Billie Eilish", "album": "WHEN WE ALL FALL ASLEEP"},
                  current_title="Bad Guy")

    assert meta.album == "WHEN WE ALL FALL ASLEEP"


def test_local_tracks_still_use_the_coverid():
    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")
    received = []
    adapter.on_metadata_change(received.append)

    adapter._report_metadata(_status_result(song={"artwork_url": "/ignored.png"}))

    assert received[0].artwork == "http://127.0.0.1:9000/music/abc123/cover_500x500_o.jpg"


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


@pytest.mark.asyncio
async def test_deactivate_then_load_something_else_does_not_seek(monkeypatch):
    """The user's own deactivation records a position too; loading new content
    afterwards must not be seeked to it either."""
    adapter, rpc = _adapter(monkeypatch, mode="play", position=72.0)
    await adapter._note_position_if_unset(session=None)

    rpc.timestamp += 30.0
    rpc.position = 0.4
    rpc.commands.clear()

    await adapter.device_freed()

    assert not any(c[0] == "time" for c in rpc.commands)


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


@pytest.mark.asyncio
async def test_next_and_previous_use_the_buttons_lms_apps_use(monkeypatch):
    """Finding 028: `playlist index -1` always goes back a whole track;
    `jump_rew` restarts the track unless it is near its start."""
    adapter, rpc = _adapter(monkeypatch, mode="play")

    assert await adapter.next() is True
    assert await adapter.previous() is True

    assert rpc.commands == [["button", "jump_fwd"], ["button", "jump_rew"]]


@pytest.mark.parametrize(
    ("result", "unavailable"),
    [
        # a radio station: one live item - nothing to skip, shuffle or repeat
        ({"playlist_tracks": 1, "remote": 1}, {"next", "previous", "shuffle", "repeat"}),
        ({"playlist_tracks": "1", "remote": "1"}, {"next", "previous", "shuffle", "repeat"}),
        # one song: repeat-one loops it, so repeat stays
        ({"playlist_tracks": 1, "duration": 227.6}, {"next", "previous", "shuffle"}),
        # a playlist wraps, even with repeat off
        ({"playlist_tracks": 12, "duration": 227.6}, set()),
        # several stations: skipping and shuffling work, a live stream has no end
        ({"playlist_tracks": 3, "remote": 1}, {"repeat"}),
        # nothing reported: disable nothing
        ({}, set()),
    ],
)
def test_what_cannot_work_on_lms_right_now(result, unavailable):
    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")
    received = []
    adapter.on_metadata_change(received.append)

    adapter._report_metadata({"mode": "play", "playlist_loop": [{"title": "x"}], **result})

    assert received[-1].unavailable == frozenset(unavailable)


@pytest.mark.parametrize(
    ("lms_shuffle", "lms_repeat", "shuffle", "repeat"),
    [
        (0, 0, False, "off"),
        (1, 2, True, "all"),
        ("2", "1", True, "one"),   # by album shows as on; 1 is one song in LMS
        (None, None, None, None),  # not reported
    ],
)
def test_shuffle_and_repeat_map_from_lms_numbers(lms_shuffle, lms_repeat, shuffle, repeat):
    """Finding 028: shuffle 0 off / 1 songs / 2 albums; repeat 0 off / 1 one
    song / 2 all - not the design's off/all/one order."""
    adapter = LmsAdapter("127.0.0.1", 9000, "gexis")
    received = []
    adapter.on_metadata_change(received.append)
    result = {"mode": "play"}
    if lms_shuffle is not None:
        result["playlist shuffle"] = lms_shuffle
    if lms_repeat is not None:
        result["playlist repeat"] = lms_repeat

    adapter._report_metadata(result)

    assert (received[-1].shuffle, received[-1].repeat) == (shuffle, repeat)


@pytest.mark.asyncio
async def test_shuffle_and_repeat_commands_use_lms_numbers(monkeypatch):
    adapter, rpc = _adapter(monkeypatch, mode="play")

    await adapter.shuffle(True)
    await adapter.shuffle(False)
    for mode in ("off", "all", "one"):
        await adapter.repeat(mode)

    assert rpc.commands == [
        ["playlist", "shuffle", 1],
        ["playlist", "shuffle", 0],
        ["playlist", "repeat", 0],
        ["playlist", "repeat", 2],
        ["playlist", "repeat", 1],
    ]


# --- ADR-0038 §1: the queue rail's contents --------------------------------


class QueueRpc(FakeRpc):
    """Answers the metadata query and the queue query differently, the way
    LMS does: `start="-"` is the current song, `start=0` the whole queue."""

    def __init__(self, timestamp=1.0, index=1, max_playlist="2500"):
        super().__init__()
        self.timestamp = timestamp
        self.index = index
        self.queue_reads = 0
        #: What the server says `maxPlaylistLength` is; `None` refuses to
        #: answer, as an older server would.
        self.max_playlist = max_playlist

    async def __call__(self, session, player, command):
        self.commands.append(list(command))
        if command[0] == "pref" and command[1] == "maxPlaylistLength":
            if self.max_playlist is None:
                raise aiohttp.ClientError("no such preference")
            return {"result": {"_p2": self.max_playlist}}
        if command[0] == "status" and command[1] == 0:
            self.queue_reads += 1
            return {
                "result": {
                    "playlist_cur_index": self.index,
                    "playlist_name": "Sunday",
                    "playlist_id": 900,
                    "playlist_modified": 0,
                    "playlist_loop": [
                        {"id": 71, "title": "Opening", "artist": "Aria Nova",
                         "coverid": "abc", "duration": 201.5},
                        {"id": 72, "title": "Closing", "artist": "Aria Nova"},
                    ],
                }
            }
        return {"result": {"mode": "play", "power": 1, "time": 1.0,
                           "playlist_timestamp": self.timestamp,
                           "playlist_cur_index": self.index}}


@pytest.mark.asyncio
async def test_the_queue_is_read_and_reported(monkeypatch):
    adapter, _ = _adapter(monkeypatch, mode="play")
    rpc = QueueRpc()
    monkeypatch.setattr(LmsAdapter, "_rpc", rpc)
    seen = []
    adapter.on_queue_change(seen.append)

    await adapter._report_queue_if_changed(None, {"playlist_timestamp": 1.0, "playlist_cur_index": 1})

    assert rpc.queue_reads == 1
    queue = seen[0]
    assert [item.title for item in queue.items] == ["Opening", "Closing"]
    # **The rail needs to tell one row from another** (ADR-0064): keyed by
    # position, removing a track rewrites every row below it.
    assert [item.track_id for item in queue.items] == ["71", "72"]
    assert queue.index == 1
    assert (queue.name, queue.id, queue.modified) == ("Sunday", 900, False)
    # A queue row is 42px: it gets the row step, not now playing's 500
    # (Phase 7a step 1 - up to a hundred of them open at once).
    assert queue.items[0].artwork.endswith("/music/abc/cover_100x100_o.jpg")


@pytest.mark.asyncio
async def test_the_queue_is_read_as_long_as_lms_allows(monkeypatch):
    """ADR-0063: the length of the queue is the server owner's setting, and
    the rail follows it rather than keeping a window of its own."""
    adapter, _ = _adapter(monkeypatch, mode="play")
    rpc = QueueRpc(max_playlist="2500")
    monkeypatch.setattr(LmsAdapter, "_rpc", rpc)
    adapter.on_queue_change(lambda queue: None)

    await adapter._report_queue_if_changed(None, {"playlist_timestamp": 1.0, "playlist_cur_index": 1})

    status = [c for c in rpc.commands if c[0] == "status" and c[1] == 0]
    assert status[0][2] == 2500


@pytest.mark.asyncio
async def test_the_playlist_length_is_asked_for_once(monkeypatch):
    """It is a preference someone sets and forgets, and this runs on every
    queue change."""
    adapter, _ = _adapter(monkeypatch, mode="play")
    rpc = QueueRpc()
    monkeypatch.setattr(LmsAdapter, "_rpc", rpc)
    adapter.on_queue_change(lambda queue: None)

    for stamp in (1.0, 2.0, 3.0):
        await adapter._report_queue_if_changed(
            None, {"playlist_timestamp": stamp, "playlist_cur_index": 1}
        )

    assert len([c for c in rpc.commands if c[0] == "pref"]) == 1


@pytest.mark.asyncio
async def test_no_limit_in_lms_is_not_no_limit_here(monkeypatch):
    """`0` means unlimited to LMS. A request needs a number, and a rail that
    reads an unbounded queue on every change is its own problem."""
    adapter, _ = _adapter(monkeypatch, mode="play")
    rpc = QueueRpc(max_playlist="0")
    monkeypatch.setattr(LmsAdapter, "_rpc", rpc)
    adapter.on_queue_change(lambda queue: None)

    await adapter._report_queue_if_changed(None, {"playlist_timestamp": 1.0, "playlist_cur_index": 1})

    status = [c for c in rpc.commands if c[0] == "status" and c[1] == 0]
    assert status[0][2] == QUEUE_CEILING


@pytest.mark.asyncio
async def test_a_server_that_will_not_say_still_gets_a_queue(monkeypatch):
    """An older server, or one that refuses the preference. The rail shows
    what it can rather than nothing."""
    adapter, _ = _adapter(monkeypatch, mode="play")
    rpc = QueueRpc(max_playlist=None)
    monkeypatch.setattr(LmsAdapter, "_rpc", rpc)
    seen = []
    adapter.on_queue_change(seen.append)

    await adapter._report_queue_if_changed(None, {"playlist_timestamp": 1.0, "playlist_cur_index": 1})

    status = [c for c in rpc.commands if c[0] == "status" and c[1] == 0]
    assert status[0][2] == QUEUE_LIMIT
    assert [item.title for item in seen[0].items] == ["Opening", "Closing"]


@pytest.mark.asyncio
async def test_the_queue_is_not_re_read_on_every_push(monkeypatch):
    """A status push arrives for every state change; the queue is only
    worth re-reading when LMS says it moved (Finding 029, step 1a)."""
    adapter, _ = _adapter(monkeypatch, mode="play")
    rpc = QueueRpc()
    monkeypatch.setattr(LmsAdapter, "_rpc", rpc)
    adapter.on_queue_change(lambda queue: None)
    same = {"playlist_timestamp": 1.0, "playlist_cur_index": 1}

    await adapter._report_queue_if_changed(None, same)
    await adapter._report_queue_if_changed(None, same)

    assert rpc.queue_reads == 1


@pytest.mark.asyncio
async def test_a_new_track_re_reads_the_queue(monkeypatch):
    """The rail shows what is coming up, so which track is playing moves it
    even when the queue itself has not changed."""
    adapter, _ = _adapter(monkeypatch, mode="play")
    rpc = QueueRpc()
    monkeypatch.setattr(LmsAdapter, "_rpc", rpc)
    adapter.on_queue_change(lambda queue: None)

    await adapter._report_queue_if_changed(None, {"playlist_timestamp": 1.0, "playlist_cur_index": 1})
    await adapter._report_queue_if_changed(None, {"playlist_timestamp": 1.0, "playlist_cur_index": 2})

    assert rpc.queue_reads == 2


@pytest.mark.asyncio
async def test_a_push_re_reads_the_queue(monkeypatch):
    """**The defect this test exists for.** The queue was read only by the
    seed status query at subscribe time, so a queue that changed afterwards
    never reached the panel: George added two albums on 2026-09-18, LMS held
    27 tracks, and the rail still showed the one it had at startup. The
    three tests above all passed, because they call
    `_report_queue_if_changed` themselves - nothing asserted that the push
    loop does (docs/LESSONS.md)."""
    adapter, _ = _adapter(monkeypatch, mode="play")
    rpc = QueueRpc()
    monkeypatch.setattr(LmsAdapter, "_rpc", rpc)
    adapter.on_queue_change(lambda queue: None)

    channel = "/cid/slim/playerstatus/aa:bb:cc:dd:ee:ff"
    frames = [
        # The queue changed while the player kept playing: no power edge,
        # only a new timestamp.
        [{"channel": channel, "data": {"power": 1, "playlist_timestamp": 2.0, "playlist_cur_index": 1}}],
    ]

    async def fake_post(self, session, message, timeout=None):
        if message["channel"] != "/meta/connect":
            return []
        if not frames:
            raise asyncio.CancelledError
        return frames.pop(0)

    monkeypatch.setattr(LmsAdapter, "_cometd_handshake", lambda self, session: _done("cid"))
    monkeypatch.setattr(LmsAdapter, "_cometd_post", fake_post)

    with pytest.raises(asyncio.CancelledError):
        await adapter._watch(lambda: None, lambda: None)

    # One for the seed query, one for the push.
    assert rpc.queue_reads == 2


@pytest.mark.asyncio
async def test_the_current_artist_id_is_a_value_not_a_method(monkeypatch):
    """**The defect this test exists for.** As a method it was truthy at the
    call site, so the enrichment service asked LMS's plugin about a bound
    method, got nothing, and quietly used Wikipedia instead for an artist the
    plugin knew (hardware, 2026-09-18). ADR-0040 §1 is "LMS first", and a
    fallback that silently wins looks exactly like one that was never
    needed."""
    adapter, _ = _adapter(monkeypatch, mode="play")

    assert adapter.current_artist_id is None

    adapter._report_metadata({
        "mode": "play",
        "playlist_loop": [{"title": "Maggie May", "artist": "Rod Stewart", "artist_id": 12316}],
    })

    assert adapter.current_artist_id == 12316
