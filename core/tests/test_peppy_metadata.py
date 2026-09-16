"""What the Peppy screen reads (Phase 5 criterion 7)."""
from __future__ import annotations

import json

from gexis_core.model import BLANK_METADATA, PlaybackState, TrackMetadata
from gexis_core.peppy_metadata import PeppyMetadataWriter


def state(**kw):
    return PlaybackState(active=kw.pop("active", "lms"), metadata=TrackMetadata(**kw))


def read(path):
    return json.loads(path.read_text())


def test_it_writes_what_the_screen_draws(tmp_path):
    path = tmp_path / "nowplaying.json"
    PeppyMetadataWriter(path).write(
        state(title="T", artist="A", album="B", artwork="http://art/", position=12.0, duration=200.0, transport="playing")
    )

    written = read(path)
    assert written["title"] == "T" and written["artist"] == "A" and written["album"] == "B"
    assert written["artwork"] == "http://art/" and written["source"] == "lms"
    assert written["position"] == 12.0 and written["duration"] == 200.0
    assert written["written_at"] > 0


def test_absent_fields_are_null_not_guessed(tmp_path):
    """Bluetooth supplies no artwork and no position (criterion 7): the
    renderer must be able to tell 'nothing' from 'zero'."""
    path = tmp_path / "nowplaying.json"
    PeppyMetadataWriter(path).write(state(active="bluetooth", title="T", transport="playing"))

    written = read(path)
    assert written["artwork"] is None
    assert written["position"] is None and written["duration"] is None


def test_nothing_playing_is_written_too(tmp_path):
    path = tmp_path / "nowplaying.json"
    PeppyMetadataWriter(path).write(PlaybackState(active=None, metadata=BLANK_METADATA))

    written = read(path)
    assert written["source"] is None and written["title"] is None


def test_an_unchanged_state_is_not_rewritten(tmp_path):
    path = tmp_path / "nowplaying.json"
    writer = PeppyMetadataWriter(path)
    writer.write(state(title="T", position=1.0, duration=2.0))
    first = path.stat().st_mtime_ns

    writer.write(state(title="T", position=1.0, duration=2.0))

    assert path.stat().st_mtime_ns == first


def test_a_reader_never_sees_half_a_file(tmp_path):
    path = tmp_path / "nowplaying.json"
    writer = PeppyMetadataWriter(path)
    writer.write(state(title="first"))
    writer.write(state(title="second"))

    assert read(path)["title"] == "second"
    assert not list(tmp_path.glob("*.tmp"))


def test_a_directory_that_cannot_be_written_is_not_fatal(tmp_path):
    unwritable = tmp_path / "ro"
    unwritable.mkdir(mode=0o500)
    PeppyMetadataWriter(unwritable / "sub" / "nowplaying.json").write(state(title="T"))
