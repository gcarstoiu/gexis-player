"""ADR-0115 decision 27: the Music share stops at 4 GB free (George,
2026-10-18), opens again above 4.5 GB."""

from gexis_core import music_floor as mf


def test_closes_below_4_gb_and_opens_only_above_4_5():
    assert mf.closed(3_999_000_000, was_closed=False) is True
    assert mf.closed(4_100_000_000, was_closed=False) is False
    # Closed, it stays closed in the gap - no flapping at the line.
    assert mf.closed(4_100_000_000, was_closed=True) is True
    assert mf.closed(4_600_000_000, was_closed=True) is False


def test_the_include_is_written_and_samba_reloaded_only_on_a_change(tmp_path):
    path, calls = tmp_path / "gexis" / "music-share.conf", []
    run = lambda args, **kw: calls.append(args)
    assert mf.is_closed(path) is False, "no file is an open share"
    assert mf.apply(True, path, run) is True
    assert path.read_text() == "   read only = yes\n" and mf.is_closed(path)
    assert calls == [["smbcontrol", "smbd", "reload-config"]]
    assert mf.apply(True, path, run) is False and len(calls) == 1
    assert mf.apply(False, path, run) is True and path.read_text() == "" and not mf.is_closed(path)


def test_the_share_includes_the_file_last():
    from pathlib import Path

    conf = (Path(__file__).resolve().parents[2] / "image/stage-gexis/10-lyrion/files/gexis-music.conf").read_text()
    lines = [line.strip() for line in conf.splitlines() if line.strip() and not line.strip().startswith("#")]
    assert lines[-1] == f"include = {mf.PATH}"
