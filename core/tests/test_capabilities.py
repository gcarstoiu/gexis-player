"""Unit tests for the declared capabilities contract (Phase 3 criterion 2,
ADR-0013). Each adapter's declaration is checked against its own actual,
already-tested behaviour - not just that a Capabilities object exists.
"""
from __future__ import annotations

from gexis_core.adapters.base import Capabilities, VolumeMechanism
from gexis_core.adapters.bluetooth import BluetoothAdapter
from gexis_core.adapters.lms import LmsAdapter
from gexis_core.adapters.spotify import SpotifyAdapter


def test_to_json_sorts_the_set_fields_for_stable_output():
    caps = Capabilities(
        audio_connection="output",
        acquisition_events=frozenset({"b", "a"}),
        supports_artwork=True,
        supports_sample_rate=False,
        volume_managed=True,
        volume_mechanism=VolumeMechanism.DUMMY_MIXER,
        dummy_mixer_card="somecard",
        controls=frozenset({"pause", "next"}),
    )
    assert caps.to_json() == {
        "audio_connection": "output",
        "acquisition_events": ["a", "b"],
        "supports_artwork": True,
        "supports_sample_rate": False,
        "volume_managed": True,
        "volume_mechanism": "dummy_mixer",
        "dummy_mixer_card": "somecard",
        "controls": ["next", "pause"],
    }


def test_all_three_adapters_declare_output_as_the_audio_connection():
    # ADR-0009: every renderer writes to the same logical device today.
    for cls in (LmsAdapter, SpotifyAdapter, BluetoothAdapter):
        assert cls.capabilities.audio_connection == "output"


def test_only_lms_declares_activate():
    """Phase 4 criterion 7. Spotify and Bluetooth are taken over by a phone
    connecting, never by us asking."""
    assert "activate" in LmsAdapter.capabilities.controls
    assert "activate" not in SpotifyAdapter.capabilities.controls
    assert "activate" not in BluetoothAdapter.capabilities.controls


def test_all_three_declare_play_and_pause():
    """ADR-0037, measured on all three in Finding 028."""
    for cls in (LmsAdapter, SpotifyAdapter, BluetoothAdapter):
        assert {"play", "pause"} <= cls.capabilities.controls, cls.__name__


def test_every_adapter_implements_what_it_declares():
    """A declaration nothing backs is worse than no declaration - the
    command surface answers 409 from the capability, so a missing method
    would be a 502 for a button the panel shows as working."""
    for cls in (LmsAdapter, SpotifyAdapter, BluetoothAdapter):
        for control in cls.capabilities.controls:
            assert callable(getattr(cls, control, None)), f"{cls.__name__}.{control}"


def test_declared_controls_are_known_commands():
    from gexis_core.adapters.base import TRANSPORT_COMMANDS

    for cls in (LmsAdapter, SpotifyAdapter, BluetoothAdapter):
        assert cls.capabilities.controls <= TRANSPORT_COMMANDS | {"activate"}, cls.__name__


def test_lms_declares_power_on_as_its_acquisition_event():
    # ADR-0027: powering on is the acquisition, not pressing play.
    assert LmsAdapter.capabilities.acquisition_events == frozenset({"power_on"})


def test_lms_declares_full_metadata_support():
    # Confirmed live, 2026-09-12: coverid and samplerate both resolved
    # correctly for a real library track (HANDOFF.md).
    assert LmsAdapter.capabilities.supports_artwork is True
    assert LmsAdapter.capabilities.supports_sample_rate is True


def test_spotify_declares_both_of_its_acquisition_events():
    # Finding 010/014: "will_play" is needed alongside "active" because
    # "active" can arrive too late (or never) when the ALSA open races
    # another renderer's release.
    assert SpotifyAdapter.capabilities.acquisition_events == frozenset({"active", "will_play"})


def test_spotify_declares_full_metadata_support():
    assert SpotifyAdapter.capabilities.supports_artwork is True
    assert SpotifyAdapter.capabilities.supports_sample_rate is True


def test_bluetooth_declares_both_of_its_acquisition_events():
    # Finding 010 §3: MediaTransport1 fires earlier than MediaPlayer1,
    # closing a ~1s race a MediaPlayer1-only trigger used to lose.
    assert BluetoothAdapter.capabilities.acquisition_events == frozenset(
        {"media_player_appeared", "media_transport_appeared"}
    )


def test_bluetooth_declares_no_artwork_or_sample_rate():
    # ADR-0014: Bluetooth supplies no artwork. MediaPlayer1's Track dict
    # has no such fields at all - confirmed against BlueZ's own doc and a
    # live phone connection, 2026-09-12.
    assert BluetoothAdapter.capabilities.supports_artwork is False
    assert BluetoothAdapter.capabilities.supports_sample_rate is False


# --- criterion 3: volume mechanism, replacing what used to be hardcoded --


def test_lms_and_spotify_are_volume_managed_bluetooth_is_not():
    # Finding 006: Bluetooth's own volume path isn't understood well
    # enough yet to restore a remembered level for it.
    assert LmsAdapter.capabilities.volume_managed is True
    assert SpotifyAdapter.capabilities.volume_managed is True
    assert BluetoothAdapter.capabilities.volume_managed is False


def test_lms_and_bluetooth_use_a_dummy_mixer_spotify_uses_the_software_api():
    assert LmsAdapter.capabilities.volume_mechanism is VolumeMechanism.DUMMY_MIXER
    assert BluetoothAdapter.capabilities.volume_mechanism is VolumeMechanism.DUMMY_MIXER
    assert SpotifyAdapter.capabilities.volume_mechanism is VolumeMechanism.SOFTWARE_API


def test_dummy_mixer_cards_are_distinct_and_match_volume_py():
    from gexis_core.volume import DUMMY_CARD_BLUETOOTH, DUMMY_CARD_LMS

    assert LmsAdapter.capabilities.dummy_mixer_card == DUMMY_CARD_LMS
    assert BluetoothAdapter.capabilities.dummy_mixer_card == DUMMY_CARD_BLUETOOTH
    assert LmsAdapter.capabilities.dummy_mixer_card != BluetoothAdapter.capabilities.dummy_mixer_card


def test_spotify_has_no_dummy_mixer_card():
    assert SpotifyAdapter.capabilities.dummy_mixer_card is None
