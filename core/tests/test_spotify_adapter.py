"""Unit tests for the parts of SpotifyAdapter that don't need a network
(Phase 3 criterion 1's metadata reporting). The WS event loop itself is
covered by live hardware sessions - see adapters/spotify.py's own module
docstring for why (go-librespot's exact event shapes were confirmed
against its source, not assumed).
"""
from __future__ import annotations

import pytest

from gexis_core.adapters.spotify import SpotifyAdapter
from gexis_core.model import TrackMetadata


def _metadata_event(**overrides) -> dict:
    """Shaped per API.md's "metadata" event fields."""
    data = {
        "name": "Song Title",
        "artist_names": ["Artist One", "Artist Two"],
        "album_name": "The Album",
        "album_cover_url": "https://example.com/cover.jpg",
        "position": 5000,
        "duration": 200000,
        "sample_rate": 44100,
    }
    data.update(overrides)
    return data


def test_metadata_event_maps_to_track_metadata():
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    received = []
    adapter.on_metadata_change(received.append)

    adapter._handle_metadata_event(_metadata_event())

    assert received == [
        TrackMetadata(
            title="Song Title",
            artist="Artist One, Artist Two",
            album="The Album",
            artwork="https://example.com/cover.jpg",
            sample_rate=44100,
            position=5.0,
            duration=200.0,
            source_type="spotify",
        )
    ]


def test_metadata_event_is_a_noop_without_a_registered_callback():
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    adapter._handle_metadata_event(_metadata_event())  # must not raise


def test_seek_event_updates_timing_but_keeps_the_rest_of_the_last_metadata():
    """API.md: "seek" carries only context_uri/uri/position/duration/
    play_origin - not name/artist/album."""
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    received = []
    adapter.on_metadata_change(received.append)
    adapter._handle_metadata_event(_metadata_event())

    adapter._handle_seek_event({"position": 90000, "duration": 200000})

    assert received[-1].title == "Song Title"  # unchanged
    assert received[-1].position == 90.0
    assert received[-1].duration == 200.0


def test_seek_event_before_any_metadata_is_a_noop():
    """A "seek" arriving with nothing to merge onto (should not happen per
    API.md's ordering, but must not crash if it did)."""
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    received = []
    adapter.on_metadata_change(received.append)

    adapter._handle_seek_event({"position": 1000, "duration": 200000})

    assert received == []


# --- Phase 4: transport state ---------------------------------------------


def test_transport_events_map_onto_the_normalised_vocabulary():
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    received = []
    adapter.on_metadata_change(received.append)
    adapter._handle_metadata_event(_metadata_event())

    for event, expected in (
        ("playing", "playing"),
        ("paused", "paused"),
        ("not_playing", "stopped"),
        ("stopped", "stopped"),
    ):
        adapter._handle_transport_event(event)
        assert received[-1].transport == expected


def test_a_transport_event_keeps_the_track_it_belongs_to():
    """go-librespot's transport events carry no track fields, so reporting
    one on its own would blank the title."""
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    received = []
    adapter.on_metadata_change(received.append)
    adapter._handle_metadata_event(_metadata_event())

    adapter._handle_transport_event("paused")

    assert received[-1].title == "Song Title"
    assert received[-1].transport == "paused"


def test_a_transport_event_before_any_metadata_is_a_noop():
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    received = []
    adapter.on_metadata_change(received.append)

    adapter._handle_transport_event("playing")

    assert received == []


def test_a_track_change_does_not_blank_the_transport_state():
    """API.md's "metadata" event means a new track was *loaded* - it says
    nothing about whether playback is running, and the transport edges are
    separate events. Constructing metadata fresh without carrying this
    forward left it blank on every track change until the next edge."""
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    received = []
    adapter.on_metadata_change(received.append)
    adapter._handle_metadata_event(_metadata_event())
    adapter._handle_transport_event("playing")

    adapter._handle_metadata_event(_metadata_event(name="Next Song"))

    assert received[-1].title == "Next Song"
    assert received[-1].transport == "playing"


def test_a_transport_event_takes_the_position_from_status_when_given():
    """Finding 028: transport events carry no position, and without one the
    published position stayed at the track's start through every pause, so
    the panel's progress bar went back to 0:00."""
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    received = []
    adapter.on_metadata_change(received.append)
    adapter._handle_metadata_event(_metadata_event(position=0))

    adapter._handle_transport_event("paused", 41092)

    assert received[-1].transport == "paused"
    assert received[-1].position == 41.092
    assert received[-1].title == "Song Title"


def test_a_transport_event_keeps_the_last_position_when_status_gave_none():
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    received = []
    adapter.on_metadata_change(received.append)
    adapter._handle_metadata_event(_metadata_event(position=5000))

    adapter._handle_transport_event("paused", None)

    assert received[-1].position == 5.0


def test_shuffle_and_repeat_events_update_the_published_metadata():
    """go-librespot's shuffle_context / repeat_context / repeat_track events,
    each {"value": bool}; Spotify's two repeat flags become three states."""
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    received = []
    adapter.on_metadata_change(received.append)
    adapter._handle_metadata_event(_metadata_event())

    adapter._handle_flag_event("shuffle_context", {"value": True})
    assert received[-1].shuffle is True

    adapter._handle_flag_event("repeat_context", {"value": True})
    assert received[-1].repeat == "all"
    adapter._handle_flag_event("repeat_track", {"value": True})
    assert received[-1].repeat == "one"
    adapter._handle_flag_event("repeat_track", {"value": False})
    adapter._handle_flag_event("repeat_context", {"value": False})
    assert received[-1].repeat == "off"
    assert received[-1].title == "Song Title"


def test_flags_known_before_a_track_are_carried_onto_it():
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    received = []
    adapter.on_metadata_change(received.append)
    adapter._handle_flag_event("shuffle_context", {"value": True})  # nothing to report yet
    assert received == []

    adapter._handle_metadata_event(_metadata_event())
    assert received[-1].shuffle is True
    assert received[-1].repeat is None  # never reported


def test_a_malformed_flag_event_changes_nothing():
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    received = []
    adapter.on_metadata_change(received.append)
    adapter._handle_metadata_event(_metadata_event())
    adapter._handle_flag_event("shuffle_context", {"value": "yes"})
    assert len(received) == 1


# --- already playing when the daemon starts --------------------------------


class FakeStatus:
    """Stands in for go-librespot's `/status`, which is the only thing that
    can say a stream was *already* running."""

    def __init__(self, body, status=200):
        self._body = body
        self._status = status
        self.asked = 0

    def get(self, url, timeout=None):
        self.asked += 1
        outer = self

        class Response:
            status = outer._status

            async def json(self, content_type=None):
                return outer._body

            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc):
                return False

        return Response()


PLAYING = {"paused": False, "stopped": False, "track": _metadata_event()}


@pytest.mark.asyncio
async def test_a_stream_already_running_at_startup_is_an_acquisition():
    """**The defect this test exists for.** go-librespot announces
    acquisition with events, and events are edges: nothing is emitted for a
    stream that was already playing. After a daemon restart the core
    believed nobody held the device while sound was coming out of it, and
    the panel showed its "waiting for a service" block over a playing
    Spotify track until the next track change - 66 s in the case George
    saw (2026-09-18)."""
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    seen = []
    adapter.on_metadata_change(seen.append)
    acquired = []

    await adapter._acquire_if_already_playing(FakeStatus(PLAYING), lambda: acquired.append(True))

    assert acquired == [True]
    assert seen and seen[0].title == "Song Title"


@pytest.mark.asyncio
async def test_a_paused_session_at_startup_does_not_acquire():
    """Holding the device is the acquisition (ADR-0027), but a session left
    paused before the daemon started is indistinguishable from one somebody
    abandoned - and claiming it would take the device from whoever has it."""
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    acquired = []

    await adapter._acquire_if_already_playing(
        FakeStatus({**PLAYING, "paused": True}), lambda: acquired.append(True))

    assert acquired == []


@pytest.mark.asyncio
async def test_nothing_playing_at_startup_acquires_nothing():
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    acquired = []

    await adapter._acquire_if_already_playing(
        FakeStatus({"stopped": True, "paused": False}), lambda: acquired.append(True))

    assert acquired == []


@pytest.mark.asyncio
async def test_a_status_that_cannot_be_read_acquires_nothing():
    adapter = SpotifyAdapter("127.0.0.1", 3678)
    acquired = []

    await adapter._acquire_if_already_playing(
        FakeStatus({}, status=500), lambda: acquired.append(True))

    assert acquired == []
