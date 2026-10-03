"""ADR-0115: the Lyrion server's music folders."""
from __future__ import annotations

import asyncio
from pathlib import Path

from gexis_core import lyrion_folders as lf


def test_the_music_folder_and_mounted_disks_are_added_and_the_user_s_kept():
    current = ["/home/user/Music", "/media/gexis-usb/OLD-DISK"]
    want = lf.wanted(current, ["/media/gexis-usb/1234-ABCD", "/mnt/gexis-shares/nas-music"])
    assert want == ["/home/user/Music", "/var/lib/gexis-music",
                    "/media/gexis-usb/1234-ABCD", "/mnt/gexis-shares/nas-music"], \
        "the user's own stays; an unplugged disk goes; the Music folder is always there"


def test_nothing_changes_when_nothing_did():
    current = ["/var/lib/gexis-music", "/media/gexis-usb/1234-ABCD"]
    assert lf.wanted(current, ["/media/gexis-usb/1234-ABCD"]) == current


def test_only_mounted_folders_count(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    assert lf.mounted(tmp_path, lambda p: p.endswith("/b")) == [str(tmp_path / "b")]
    assert lf.mounted(tmp_path / "absent") == []


def test_sync_sets_the_list_and_leaves_the_scan_to_lyrion(monkeypatch, tmp_path):
    """Lyrion scans a folder added to `mediadirs` by itself; a rescan on top
    walked all 61,362 files of George's share a second time (2026-10-03)."""
    calls = []
    prefs = {"mediadirs": ["/var/lib/gexis-music"]}

    async def rpc(command):
        calls.append(command)
        if command[:3] == ["pref", "mediadirs", "?"]:
            return {"_p2": prefs["mediadirs"]}
        if command[:2] == ["pref", "mediadirs"]:
            prefs["mediadirs"] = command[2]
        return {}

    usb = tmp_path / "usb"
    (usb / "DISK").mkdir(parents=True)
    monkeypatch.setattr(lf, "MANAGED", (usb, tmp_path / "shares"))
    assert asyncio.run(lf.sync(rpc, is_mount=lambda p: True)) is True
    assert prefs["mediadirs"] == ["/var/lib/gexis-music", str(usb / "DISK")]
    assert ["rescan"] not in calls
    calls.clear()
    assert asyncio.run(lf.sync(rpc, is_mount=lambda p: True)) is False
    assert ["rescan"] not in calls


def test_a_saved_share_stays_while_its_nas_is_off():
    """ADR-0115 decision 16: taking a folder out makes Lyrion wipe the whole
    library and scan everything - two hours for George's share."""
    nas = "/mnt/gexis-shares/Tower-local-Music-912e8d"
    current = ["/var/lib/gexis-music", nas, "/mnt/gexis-shares/forgotten-123456"]
    assert lf.wanted(current, [], saved=[nas]) == ["/var/lib/gexis-music", nas], \
        "not mounted, still saved: kept; forgotten: gone"
