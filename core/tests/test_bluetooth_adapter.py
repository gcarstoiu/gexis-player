"""Unit tests for the parts of BluetoothAdapter that don't need D-Bus
(Phase 3 criterion 1's metadata reporting). The live D-Bus watch itself is
covered by hardware sessions - see adapters/bluetooth.py's module and
`_attach_media_player`'s own docstrings for what is and isn't confirmed.
"""
from __future__ import annotations

import asyncio

import pytest
from dbus_next import Variant

from gexis_core.adapters.bluetooth import (
    MEDIA_PLAYER_IFACE,
    MEDIA_TRANSPORT_IFACE,
    PROPERTIES_IFACE,
    BluetoothAdapter,
    _unwrap,
)
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


# --- _attach_media_player: regression test for the interface bug ----------


class _FakeInterface:
    def __init__(self):
        self.callback = None

    def on_properties_changed(self, callback):
        self.callback = callback


class _FakeProxyObject:
    def __init__(self):
        self.interfaces: dict[str, _FakeInterface] = {}

    def get_interface(self, name):
        return self.interfaces.setdefault(name, _FakeInterface())


class _FakeBus:
    def __init__(self):
        self.proxy = _FakeProxyObject()

    async def introspect(self, service, path):
        return None  # unused - _FakeProxyObject ignores it

    def get_proxy_object(self, service, path, introspection):
        return self.proxy


@pytest.mark.asyncio
async def test_attach_media_player_subscribes_via_the_properties_interface():
    """Regression test - found broken on hardware, 2026-09-12 (George,
    testing against a real phone: Bluetooth reported no metadata at all).
    `MediaPlayer1`'s own proxy interface has no `on_properties_changed` -
    confirmed by introspection, it defines no signals of its own.
    `PropertiesChanged` belongs to `org.freedesktop.DBus.Properties`."""
    adapter = BluetoothAdapter()
    adapter._bus = _FakeBus()

    await adapter._attach_media_player("/org/bluez/hci0/dev_XX/player0")

    assert adapter._bus.proxy.interfaces[PROPERTIES_IFACE].callback is not None
    assert MEDIA_PLAYER_IFACE not in adapter._bus.proxy.interfaces


@pytest.mark.asyncio
async def test_attach_media_player_reports_metadata_on_a_real_signal_shape():
    """End-to-end through the fixed subscription: a PropertiesChanged
    signal for the right interface, with the two-level Variant nesting a
    dict-valued property actually has, must reach `on_metadata_change`."""
    adapter = BluetoothAdapter()
    adapter._bus = _FakeBus()
    received = []
    adapter.on_metadata_change(received.append)

    await adapter._attach_media_player("/org/bluez/hci0/dev_XX/player0")
    callback = adapter._bus.proxy.interfaces[PROPERTIES_IFACE].callback

    callback(
        MEDIA_PLAYER_IFACE,
        {
            "Track": Variant(
                "a{sv}",
                {"Title": Variant("s", "Song"), "Artist": Variant("s", "Band")},
            )
        },
        [],
    )

    assert received[-1].title == "Song"
    assert received[-1].artist == "Band"


# --- _handle_interfaces_added / _handle_interfaces_removed -----------------


@pytest.mark.asyncio
async def test_interfaces_added_media_player_seeds_metadata_and_acquires():
    adapter = BluetoothAdapter()
    received = []
    adapter.on_metadata_change(received.append)
    acquired = []

    adapter._handle_interfaces_added(
        "/org/bluez/hci0/dev_XX/player0",
        {MEDIA_PLAYER_IFACE: {"Track": Variant("a{sv}", {"Title": Variant("s", "Song")})}},
        lambda: acquired.append(None),
    )
    # `_handle_interfaces_added` fires off `_attach_media_player` as a
    # background task (real usage has a live `self._bus` to introspect;
    # this test doesn't) - let it run to its own caught exception so
    # nothing is left pending when the test ends.
    await asyncio.sleep(0)

    assert acquired == [None]
    assert received[-1].title == "Song"
    assert adapter._connected_device_path == "/org/bluez/hci0/dev_XX"


@pytest.mark.asyncio
async def test_interfaces_added_media_transport_only_acquires_no_metadata():
    """MediaTransport1 appears before MediaPlayer1 negotiates (Finding 010
    §3) - it's an acquisition signal, not a metadata source."""
    adapter = BluetoothAdapter()
    received = []
    adapter.on_metadata_change(received.append)
    acquired = []

    adapter._handle_interfaces_added(
        "/org/bluez/hci0/dev_XX/fd2", {MEDIA_TRANSPORT_IFACE: {}}, lambda: acquired.append(None)
    )

    assert acquired == [None]
    assert received == []


def test_interfaces_removed_relinquishes_and_blanks_metadata():
    """Regression test: George found this live, 2026-09-12 - disconnecting
    Spotify/Bluetooth left `active` pointed at the disconnected renderer
    indefinitely instead of returning to "nobody" (ADR-0027), an oversight
    in the original work, not a deliberate deferral."""
    adapter = BluetoothAdapter()
    adapter._connected_device_path = "/org/bluez/hci0/dev_XX"
    adapter._last_track = {"Title": "Song"}
    adapter._last_position_ms = 5000
    received = []
    adapter.on_metadata_change(received.append)
    released = []

    adapter._handle_interfaces_removed(
        "/org/bluez/hci0/dev_XX/player0", {MEDIA_PLAYER_IFACE: {}}, lambda: released.append(None)
    )

    assert released == [None]
    assert received[-1] == TrackMetadata(source_type="bluetooth")
    assert adapter._connected_device_path is None


def test_interfaces_removed_ignores_a_path_for_a_different_device():
    """Two devices could in principle both have MediaPlayer1 objects
    momentarily (a reconnect race) - only the one this adapter is actually
    tracking should trigger a release."""
    adapter = BluetoothAdapter()
    adapter._connected_device_path = "/org/bluez/hci0/dev_XX"
    released = []

    adapter._handle_interfaces_removed(
        "/org/bluez/hci0/dev_YY/player0", {MEDIA_PLAYER_IFACE: {}}, lambda: released.append(None)
    )

    assert released == []
    assert adapter._connected_device_path == "/org/bluez/hci0/dev_XX"


def test_interfaces_removed_ignores_an_unrelated_interface():
    adapter = BluetoothAdapter()
    adapter._connected_device_path = "/org/bluez/hci0/dev_XX"
    released = []

    adapter._handle_interfaces_removed(
        "/org/bluez/hci0/dev_XX/player0", {"org.bluez.Battery1": {}}, lambda: released.append(None)
    )

    assert released == []
    assert adapter._connected_device_path == "/org/bluez/hci0/dev_XX"


@pytest.mark.asyncio
async def test_attach_media_player_ignores_a_signal_for_another_interface():
    adapter = BluetoothAdapter()
    adapter._bus = _FakeBus()
    received = []
    adapter.on_metadata_change(received.append)

    await adapter._attach_media_player("/org/bluez/hci0/dev_XX/player0")
    callback = adapter._bus.proxy.interfaces[PROPERTIES_IFACE].callback

    callback("org.bluez.Device1", {"Connected": Variant("b", False)}, [])

    assert received == []
