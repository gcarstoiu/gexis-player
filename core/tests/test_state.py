"""Unit tests for StateStore (Phase 3 criterion 1's aggregator)."""
from __future__ import annotations

from gexis_core.adapters.base import Capabilities, VolumeMechanism
from gexis_core.model import BLANK_METADATA, TrackMetadata
from gexis_core.state import StateStore


def _caps(*renderer_ids: str) -> dict[str, Capabilities]:
    """A minimal capabilities dict for tests that only care about which
    renderers exist, not what any of them declare (Phase 3 criterion 2)."""
    return {
        rid: Capabilities(
            audio_connection="output",
            acquisition_events=frozenset(),
            supports_artwork=False,
            supports_sample_rate=False,
            volume_managed=False,
            volume_mechanism=VolumeMechanism.DUMMY_MIXER,
        )
        for rid in renderer_ids
    }


def test_starts_with_nobody_active_and_all_unavailable():
    store = StateStore(_caps("lms", "spotify", "bluetooth"))
    state = store.state
    assert state.active is None
    assert state.available == {"lms": False, "spotify": False, "bluetooth": False}
    assert state.metadata == BLANK_METADATA


def test_set_active_updates_state_and_notifies():
    store = StateStore(_caps("lms", "spotify"))
    seen = []
    store.subscribe(seen.append)

    store.set_active("lms")

    assert store.state.active == "lms"
    assert len(seen) == 1
    assert seen[0].active == "lms"


def test_set_active_to_same_value_does_not_notify():
    store = StateStore(_caps("lms"))
    store.set_active("lms")
    seen = []
    store.subscribe(seen.append)

    store.set_active("lms")

    assert seen == []


def test_set_available_updates_and_notifies():
    store = StateStore(_caps("lms", "spotify"))
    seen = []
    store.subscribe(seen.append)

    store.set_available("spotify", True)

    assert store.state.available == {"lms": False, "spotify": True}
    assert len(seen) == 1


def test_set_available_to_same_value_does_not_notify():
    store = StateStore(_caps("lms"))
    seen = []
    store.subscribe(seen.append)

    store.set_available("lms", False)  # already False by default

    assert seen == []


def test_set_available_rejects_unknown_renderer():
    store = StateStore(_caps("lms"))
    try:
        store.set_available("qobuz", True)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_metadata_from_the_active_renderer_is_published():
    store = StateStore(_caps("lms", "spotify"))
    store.set_active("lms")
    metadata = TrackMetadata(title="Song", source_type="lms")

    store.set_metadata("lms", metadata)

    assert store.state.metadata == metadata


def test_metadata_from_an_inactive_renderer_is_not_published_but_is_remembered():
    """Recorded so becoming active shows metadata immediately rather than a
    blank screen for however long the first push after activation takes."""
    store = StateStore(_caps("lms", "spotify"))
    store.set_active("lms")
    seen = []
    store.subscribe(seen.append)

    store.set_metadata("spotify", TrackMetadata(title="Not shown yet", source_type="spotify"))

    assert store.state.metadata == BLANK_METADATA
    assert seen == []  # inactive renderer's metadata must not broadcast

    store.set_active("spotify")

    assert store.state.metadata.title == "Not shown yet"


def test_metadata_blanked_when_nobody_is_active():
    store = StateStore(_caps("lms"))
    store.set_active("lms")
    store.set_metadata("lms", TrackMetadata(title="Song", source_type="lms"))

    store.set_active(None)

    assert store.state.metadata == BLANK_METADATA


def test_identical_metadata_is_not_rebroadcast():
    """A renderer re-reporting the same data (e.g. a duplicate push) must
    not spam a broadcast - found live, 2026-09-12, from LMS's own
    change-driven CometD pushes still firing once a second while playing
    (the `time` field itself differs each time, so this alone doesn't
    silence that case - see adapters/lms.py's `subscribe:0` fix for that)."""
    store = StateStore(_caps("lms"))
    store.set_active("lms")
    metadata = TrackMetadata(title="Song", source_type="lms")
    store.set_metadata("lms", metadata)
    seen = []
    store.subscribe(seen.append)

    store.set_metadata("lms", TrackMetadata(title="Song", source_type="lms"))

    assert seen == []


def test_capabilities_are_published_and_static():
    caps = _caps("lms", "spotify")
    store = StateStore(caps)

    assert store.state.capabilities == caps
    # Unaffected by anything that changes active/available/metadata -
    # static for the process lifetime (Phase 3 criterion 2).
    store.set_active("lms")
    assert store.state.capabilities == caps


def test_capabilities_dict_is_copied_not_aliased():
    caps = _caps("lms")
    store = StateStore(caps)

    caps["spotify"] = _caps("spotify")["spotify"]

    assert "spotify" not in store.state.capabilities


def test_subscribers_see_the_final_combined_state_not_a_partial_one():
    store = StateStore(_caps("lms"))
    store.set_active("lms")
    seen = []
    store.subscribe(seen.append)

    store.set_metadata("lms", TrackMetadata(title="Song", source_type="lms"))

    assert seen[-1].active == "lms"
    assert seen[-1].metadata.title == "Song"


# --- Phase 4: handoff and volume ------------------------------------------


def test_handoff_publishes_the_pair_and_clears():
    store = StateStore(_caps("lms", "spotify"))
    seen = []
    store.subscribe(seen.append)

    store.set_handoff("lms", "spotify")
    assert store.state.handoff.to_json() == {"from": "lms", "to": "spotify"}

    store.set_handoff(None, None)
    assert store.state.handoff is None
    assert len(seen) == 2


def test_handoff_with_no_outgoing_renderer_publishes_nothing():
    """A cold acquisition is not a takeover - there is no pair."""
    store = StateStore(_caps("lms"))
    store.set_handoff(None, "lms")
    assert store.state.handoff is None


def test_repeating_the_same_handoff_does_not_rebroadcast():
    store = StateStore(_caps("lms", "spotify"))
    store.set_handoff("lms", "spotify")
    seen = []
    store.subscribe(seen.append)

    store.set_handoff("lms", "spotify")

    assert seen == []


def test_volume_is_published_as_percent_raw_db_and_muted():
    store = StateStore(_caps("lms"))

    store.set_volume_raw(240)

    assert store.state.volume.to_json() == {"percent": 100, "raw": 240, "db": 0.0, "muted": False}


def test_volume_percent_is_the_slider_position_on_the_shared_curve():
    """ADR-0034 as amended by ADR-0054 §3: the number shown is slider
    position on the one curve - cubic over 60 dB - so half travel is
    -15.5 dB, not the hardware control's own travel, where half was -60."""
    store = StateStore(_caps("lms"))

    store.set_volume_raw(209)

    published = store.state.volume.to_json()
    assert published["percent"] == 50
    assert published["db"] == -15.5


def test_a_renderers_own_number_overrides_the_derivation():
    """ADR-0053: while a renderer holds the device the panel shows *its*
    number. `raw` and `db` stay the hardware's own."""
    store = StateStore(_caps("lms"))

    store.set_volume_raw(209, percent=25)

    published = store.state.volume.to_json()
    assert published["percent"] == 25
    assert published["db"] == -15.5


def test_muted_is_published():
    store = StateStore(_caps("lms"))

    store.set_volume_raw(0, muted=True)

    assert store.state.volume.muted is True


def test_setting_the_same_volume_does_not_rebroadcast():
    store = StateStore(_caps("lms"))
    store.set_volume_raw(120)
    seen = []
    store.subscribe(seen.append)

    store.set_volume_raw(120)

    assert seen == []


def test_handoff_exempt_pairs_are_published_not_applied():
    """Criterion 4 is explicit that the exempt list is data, not a
    constant - the store carries it and has no opinion about it."""
    store = StateStore(_caps("lms", "spotify"), handoff_exempt_pairs=(("lms", "spotify"),))

    assert store.state.to_json()["handoff_exempt_pairs"] == [["lms", "spotify"]]


def test_fixed_output_is_published_rather_than_inferred():
    """**ADR-0046, and the reason the old `disabled={!volume}` was wrong
    rather than merely ugly**: a renderer that has not reported its level
    yet looks exactly like fixed output from outside, and the panel drew a
    greyed control for both - "indistinguishable from a bug"."""
    store = StateStore(_caps("lms"))
    assert store.state.to_json()["fixed_output"] is False

    store.set_fixed_output(True)

    assert store.state.to_json()["fixed_output"] is True


def test_fixed_output_clears_the_level_and_keeps_it_clear():
    """There is nothing to show, and a stale number would have the panel
    hiding a slider while the mini strip still knew a percentage."""
    store = StateStore(_caps("lms"))
    store.set_volume_raw(180)
    assert store.state.volume is not None

    store.set_fixed_output(True)
    assert store.state.volume is None

    store.set_volume_raw(200)  # a mirror or the monitor, still running
    assert store.state.volume is None
