"""Unit tests for the normalised playback model (Phase 3 criterion 1)."""
from __future__ import annotations

from gexis_core.model import BLANK_METADATA, PlaybackState, TrackMetadata


def test_blank_metadata_is_all_none():
    assert TrackMetadata() == BLANK_METADATA
    assert BLANK_METADATA.to_json() == {
        "track_id": None,
        "title": None,
        "artist": None,
        "album": None,
        "year": None,
        "artwork": None,
        "sample_rate": None,
        "codec": None,
        "remaining_time": None,
        "source_type": None,
        "position": None,
        "duration": None,
        "transport": None,
    }


def test_remaining_time_is_duration_minus_position():
    metadata = TrackMetadata(position=30.0, duration=200.0)
    assert metadata.remaining_time == 170.0


def test_remaining_time_is_none_without_both_position_and_duration():
    assert TrackMetadata(position=30.0).remaining_time is None
    assert TrackMetadata(duration=200.0).remaining_time is None


def test_remaining_time_never_negative():
    # A stale duration paired with a position past it (e.g. a race between
    # two pushes) should read as "finished", not a negative countdown.
    metadata = TrackMetadata(position=205.0, duration=200.0)
    assert metadata.remaining_time == 0.0


def test_playback_state_defaults_to_blank_metadata():
    state = PlaybackState(active=None, available={"lms": True})
    assert state.metadata == BLANK_METADATA


def test_playback_state_to_json_shape():
    state = PlaybackState(
        active="lms",
        available={"lms": True, "spotify": True, "bluetooth": False},
        metadata=TrackMetadata(title="Song", source_type="lms"),
    )
    payload = state.to_json()
    assert payload["active"] == "lms"
    assert payload["available"] == {"lms": True, "spotify": True, "bluetooth": False}
    assert payload["metadata"]["title"] == "Song"


def test_playback_state_available_is_copied_not_aliased():
    """A caller mutating the dict it passed in must not silently mutate a
    published state after the fact."""
    available = {"lms": True}
    state = PlaybackState(active=None, available=available)
    available["lms"] = False
    assert state.available == {"lms": True}


def test_year_is_published_for_the_album_line():
    """The design puts the release year beside the album name, and LMS is the
    source it prefers - `_as_year` in the LMS adapter turns LMS's 0-for-absent
    into None so the panel blanks the slot rather than printing a zero."""
    assert TrackMetadata(year="1996").to_json()["year"] == "1996"
    assert TrackMetadata().to_json()["year"] is None
