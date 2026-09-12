"""Unit tests for the moOde-compatible metadata file writer (Phase 3
criterion 4). Field values and the exact key=value shape are checked
against moode-player/moode's own worker.php (updExtMetaFile()), not
assumed.
"""
from __future__ import annotations

from pathlib import Path

from gexis_core.metadata_file import MetadataFileWriter
from gexis_core.model import PlaybackState, TrackMetadata


def test_writes_key_value_lines_for_an_active_renderer(tmp_path: Path):
    path = tmp_path / "currentsong.txt"
    writer = MetadataFileWriter(path)
    state = PlaybackState(
        active="lms",
        available={"lms": True},
        metadata=TrackMetadata(
            title="Song Title",
            artist="The Artist",
            album="The Album",
            artwork="http://192.168.178.188:9000/music/abc/cover.jpg",
            source_type="lms",
        ),
    )

    writer.write(state)

    assert path.read_text() == (
        "file=Squeezelite Active\n"
        "artist=The Artist\n"
        "album=The Album\n"
        "title=Song Title\n"
        "coverurl=http://192.168.178.188:9000/music/abc/cover.jpg\n"
    )


def test_renderer_labels_match_moode_vocabulary_exactly(tmp_path: Path):
    # worker.php literally sets $renderer to these three strings for the
    # renderer categories that overlap ours - reusing them means an
    # existing reader's own renderer-name handling, if it has any, sees a
    # string it may already recognise.
    for renderer_id, label in (
        ("lms", "Squeezelite Active"),
        ("spotify", "Spotify Active"),
        ("bluetooth", "Bluetooth Active"),
    ):
        path = tmp_path / f"{renderer_id}.txt"
        writer = MetadataFileWriter(path)
        state = PlaybackState(
            active=renderer_id,
            available={renderer_id: True},
            metadata=TrackMetadata(source_type=renderer_id),
        )

        writer.write(state)

        assert path.read_text().splitlines()[0] == f"file={label}"


def test_missing_fields_are_written_blank_not_omitted(tmp_path: Path):
    """Bluetooth supplies no artwork (ADR-0014) - the key must still be
    present, just empty, so a reader doing a fixed key=value parse (as
    moOde's own PHP does) doesn't choke on a missing line."""
    path = tmp_path / "currentsong.txt"
    writer = MetadataFileWriter(path)
    state = PlaybackState(
        active="bluetooth",
        available={"bluetooth": True},
        metadata=TrackMetadata(title="Song", artist="Artist", source_type="bluetooth"),
    )

    writer.write(state)

    assert "album=\n" in path.read_text()
    assert "coverurl=\n" in path.read_text()


def test_nobody_holding_the_device_blanks_every_field(tmp_path: Path):
    path = tmp_path / "currentsong.txt"
    writer = MetadataFileWriter(path)
    # Seed with a real track first, so the test proves the blank actually
    # overwrites something rather than starting blank by coincidence.
    writer.write(
        PlaybackState(
            active="lms",
            available={"lms": True},
            metadata=TrackMetadata(title="Song", source_type="lms"),
        )
    )

    writer.write(PlaybackState(active=None, available={"lms": True}))

    assert path.read_text() == "file=\nartist=\nalbum=\ntitle=\ncoverurl=\n"


def test_identical_state_is_not_rewritten(tmp_path: Path):
    """moOde's own updExtMetaFile() reads the file back and compares
    before writing, to avoid needless SD card wear - same reasoning."""
    path = tmp_path / "currentsong.txt"
    writer = MetadataFileWriter(path)
    state = PlaybackState(
        active="lms",
        available={"lms": True},
        metadata=TrackMetadata(title="Song", source_type="lms"),
    )
    writer.write(state)
    written_at = path.stat().st_mtime_ns

    writer.write(
        PlaybackState(
            active="lms",
            available={"lms": True},
            metadata=TrackMetadata(title="Song", source_type="lms"),
        )
    )

    assert path.stat().st_mtime_ns == written_at


def test_write_is_atomic_no_tmp_file_left_behind(tmp_path: Path):
    path = tmp_path / "currentsong.txt"
    writer = MetadataFileWriter(path)

    writer.write(
        PlaybackState(
            active="lms",
            available={"lms": True},
            metadata=TrackMetadata(title="Song", source_type="lms"),
        )
    )

    assert path.exists()
    assert not (tmp_path / "currentsong.txt.tmp").exists()


def test_creates_missing_parent_directories(tmp_path: Path):
    path = tmp_path / "nested" / "dir" / "currentsong.txt"
    writer = MetadataFileWriter(path)

    writer.write(
        PlaybackState(active=None, available={})
    )

    assert path.exists()


def test_write_failure_does_not_raise(tmp_path: Path):
    """A read-only or missing filesystem must not crash the whole daemon
    over a compatibility nicety for external displays."""
    path = tmp_path / "does" / "not" / "exist" / "currentsong.txt"
    writer = MetadataFileWriter(path)
    # Block directory creation by putting a file where a directory needs
    # to go.
    (tmp_path / "does").write_text("not a directory")

    writer.write(PlaybackState(active=None, available={}))  # must not raise
