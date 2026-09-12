"""Unit tests for the parts of BluetoothAdapter that don't need D-Bus
(Phase 3 criterion 1's metadata reporting). The live D-Bus watch itself is
covered by hardware sessions - see adapters/bluetooth.py's module and
`_attach_media_player`'s own docstrings for what is and isn't confirmed.
"""
from __future__ import annotations

from dbus_next import Variant

from gexis_core.adapters.bluetooth import BluetoothAdapter, _unwrap
from gexis_core.model import TrackMetadata


def test_unwrap_extracts_variant_values():
    props = {"Title": Variant("s", "Song"), "Duration": Variant("u", 200000)}
    assert _unwrap(props) == {"Title": "Song", "Duration": 200000}


def test_seed_metadata_reports_title_artist_album_and_position():
    adapter = BluetoothAdapter()
    received = []
    adapter.on_metadata_change(received.append)

    adapter._seed_metadata(
        {
            "Track": Variant(
                "a{sv}",
                {
                    "Title": Variant("s", "Song"),
                    "Artist": Variant("s", "Band"),
                    "Album": Variant("s", "Album"),
                    "Duration": Variant("u", 200000),
                },
            ),
            "Position": Variant("u", 5000),
        }
    )

    assert received == [
        TrackMetadata(
            title="Song",
            artist="Band",
            album="Album",
            position=5.0,
            duration=200.0,
            source_type="bluetooth",
        )
    ]


def test_seed_metadata_never_reports_artwork_or_sample_rate():
    """ADR-0014: Bluetooth supplies no artwork - MediaPlayer1's Track dict
    has no such field at all, not merely omitted here."""
    adapter = BluetoothAdapter()
    received = []
    adapter.on_metadata_change(received.append)

    adapter._seed_metadata(
        {"Track": Variant("a{sv}", {"Title": Variant("s", "Song")})}
    )

    assert received[0].artwork is None
    assert received[0].sample_rate is None


def test_seed_metadata_without_track_or_position_reports_blank():
    """No MediaPlayer1 connected yet, or a device with no Track property at
    all - must not crash on the missing keys."""
    adapter = BluetoothAdapter()
    received = []
    adapter.on_metadata_change(received.append)

    adapter._seed_metadata({})

    assert received == [TrackMetadata(source_type="bluetooth")]


def test_seed_metadata_is_a_noop_without_a_registered_callback():
    adapter = BluetoothAdapter()
    adapter._seed_metadata({"Track": Variant("a{sv}", {})})  # must not raise


def test_position_only_update_keeps_the_last_known_track():
    """The `on_properties_changed` shape this models: a Position-only
    change must not blank out the track that's still playing."""
    adapter = BluetoothAdapter()
    adapter._last_track = {"Title": "Song", "Artist": "Band"}
    received = []
    adapter.on_metadata_change(received.append)

    adapter._last_position_ms = 9000
    adapter._report_metadata()

    assert received[0].title == "Song"
    assert received[0].position == 9.0
