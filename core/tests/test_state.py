"""Unit tests for StateStore (Phase 3 criterion 1's aggregator)."""
from __future__ import annotations

from gexis_core.model import BLANK_METADATA, TrackMetadata
from gexis_core.state import StateStore


def test_starts_with_nobody_active_and_all_unavailable():
    store = StateStore(["lms", "spotify", "bluetooth"])
    state = store.state
    assert state.active is None
    assert state.available == {"lms": False, "spotify": False, "bluetooth": False}
    assert state.metadata == BLANK_METADATA


def test_set_active_updates_state_and_notifies():
    store = StateStore(["lms", "spotify"])
    seen = []
    store.subscribe(seen.append)

    store.set_active("lms")

    assert store.state.active == "lms"
    assert len(seen) == 1
    assert seen[0].active == "lms"


def test_set_active_to_same_value_does_not_notify():
    store = StateStore(["lms"])
    store.set_active("lms")
    seen = []
    store.subscribe(seen.append)

    store.set_active("lms")

    assert seen == []


def test_set_available_updates_and_notifies():
    store = StateStore(["lms", "spotify"])
    seen = []
    store.subscribe(seen.append)

    store.set_available("spotify", True)

    assert store.state.available == {"lms": False, "spotify": True}
    assert len(seen) == 1


def test_set_available_to_same_value_does_not_notify():
    store = StateStore(["lms"])
    seen = []
    store.subscribe(seen.append)

    store.set_available("lms", False)  # already False by default

    assert seen == []


def test_set_available_rejects_unknown_renderer():
    store = StateStore(["lms"])
    try:
        store.set_available("qobuz", True)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_metadata_from_the_active_renderer_is_published():
    store = StateStore(["lms", "spotify"])
    store.set_active("lms")
    metadata = TrackMetadata(title="Song", source_type="lms")

    store.set_metadata("lms", metadata)

    assert store.state.metadata == metadata


def test_metadata_from_an_inactive_renderer_is_not_published_but_is_remembered():
    """Recorded so becoming active shows metadata immediately rather than a
    blank screen for however long the first push after activation takes."""
    store = StateStore(["lms", "spotify"])
    store.set_active("lms")
    seen = []
    store.subscribe(seen.append)

    store.set_metadata("spotify", TrackMetadata(title="Not shown yet", source_type="spotify"))

    assert store.state.metadata == BLANK_METADATA
    assert seen == []  # inactive renderer's metadata must not broadcast

    store.set_active("spotify")

    assert store.state.metadata.title == "Not shown yet"


def test_metadata_blanked_when_nobody_is_active():
    store = StateStore(["lms"])
    store.set_active("lms")
    store.set_metadata("lms", TrackMetadata(title="Song", source_type="lms"))

    store.set_active(None)

    assert store.state.metadata == BLANK_METADATA


def test_subscribers_see_the_final_combined_state_not_a_partial_one():
    store = StateStore(["lms"])
    store.set_active("lms")
    seen = []
    store.subscribe(seen.append)

    store.set_metadata("lms", TrackMetadata(title="Song", source_type="lms"))

    assert seen[-1].active == "lms"
    assert seen[-1].metadata.title == "Song"
