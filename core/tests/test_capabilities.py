"""Unit tests for the declared capabilities contract (Phase 3 criterion 2,
ADR-0013). Each adapter's declaration is checked against its own actual,
already-tested behaviour - not just that a Capabilities object exists.
"""
from __future__ import annotations

from gexis_core.adapters.base import Capabilities
from gexis_core.adapters.bluetooth import BluetoothAdapter
from gexis_core.adapters.lms import LmsAdapter
from gexis_core.adapters.spotify import SpotifyAdapter


def test_to_json_sorts_the_set_fields_for_stable_output():
    caps = Capabilities(
        audio_connection="output",
        acquisition_events=frozenset({"b", "a"}),
        supports_artwork=True,
        supports_sample_rate=False,
        controls=frozenset({"pause", "next"}),
    )
    assert caps.to_json() == {
        "audio_connection": "output",
        "acquisition_events": ["a", "b"],
        "supports_artwork": True,
        "supports_sample_rate": False,
        "controls": ["next", "pause"],
    }


def test_all_three_adapters_declare_output_as_the_audio_connection():
    # ADR-0009: every renderer writes to the same logical device today.
    for cls in (LmsAdapter, SpotifyAdapter, BluetoothAdapter):
        assert cls.capabilities.audio_connection == "output"


def test_no_adapter_declares_transport_controls_yet():
    # Phase 4 has no transport controls beyond LMS activation; Phase 6
    # ("capability-driven controls") is where this becomes real. Declared
    # honestly empty rather than invented ahead of that work.
    for cls in (LmsAdapter, SpotifyAdapter, BluetoothAdapter):
        assert cls.capabilities.controls == frozenset()


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
