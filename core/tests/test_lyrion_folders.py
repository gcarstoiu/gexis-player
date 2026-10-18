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
    walked all tens of thousands of files of George's share a second time (2026-10-03)."""
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
    assert asyncio.run(lf.sync(rpc, is_mount=lambda p: True, usb_seen=tmp_path / "seen.json")) is True
    assert prefs["mediadirs"] == ["/var/lib/gexis-music", str(usb / "DISK")]
    assert ["rescan"] not in calls
    calls.clear()
    assert asyncio.run(lf.sync(rpc, is_mount=lambda p: True, usb_seen=tmp_path / "seen.json")) is False
    assert ["rescan"] not in calls


def test_a_saved_share_stays_while_its_nas_is_off():
    """ADR-0115 decision 16: taking a folder out makes Lyrion wipe the whole
    library and scan everything - two hours for George's share."""
    nas = "/mnt/gexis-shares/Tower-local-Music-912e8d"
    current = ["/var/lib/gexis-music", nas, "/mnt/gexis-shares/forgotten-123456"]
    assert lf.wanted(current, [], saved=[nas]) == ["/var/lib/gexis-music", nas], \
        "not mounted, still saved: kept; forgotten: gone"


def test_a_usb_disk_stays_seven_days_after_it_is_unplugged(tmp_path, monkeypatch):
    """ADR-0115 decision 17 (George: "decision A, but 7 days not more")."""
    seen = tmp_path / "usb-seen.json"
    disk = "/media/gexis-usb/1234-ABCD"
    day = 24 * 3600
    assert lf.usb_recent([disk], seen, now=0) == [disk]
    assert lf.usb_recent([], seen, now=6 * day) == [disk], "unplugged six days: kept"
    assert lf.usb_recent([], seen, now=8 * day) == [], "eight days: gone"
    current = ["/var/lib/gexis-music", disk]
    lf.usb_recent([disk], seen, now=0)
    assert lf.wanted(current, [], saved=lf.usb_recent([], seen, now=day)) == current


def test_the_usb_record_is_written_whole_and_only_when_it_changes(tmp_path, monkeypatch):
    """Review, 2026-10-12: rewritten in place on every 20 s pass, so a power
    cut could leave it empty - every unplugged disk forgotten, and Lyrion
    wiping the library for it."""
    import os

    disk = str(lf.USB / "disk-a")
    seen = tmp_path / "seen.json"
    writes = []
    real = os.replace
    monkeypatch.setattr(os, "replace", lambda a, b: (writes.append(b), real(a, b)))
    lf.usb_recent([disk], seen, now=1000)
    assert writes == [seen] and not (tmp_path / "seen.json.tmp").exists()
    for n in range(1, 100):                         # half an hour of passes, still mounted
        lf.usb_recent([disk], seen, now=1000 + 20 * n)
    lf.usb_recent([], seen, now=3000)               # unplugged
    assert writes == [seen], "nothing changed, nothing written"
    lf.usb_recent([disk], seen, now=1000 + 3600)    # plugged in again an hour on
    assert len(writes) == 2
    assert lf.usb_recent([], seen, now=1000 + 3600 + 6 * 86400) == [disk]


def test_the_music_folder_switched_off_leaves_and_the_users_own_inside_it_stays():
    """ADR-0115 decision 20: the Music folder is a switch; a folder the user
    added on Lyrion's page, even inside it, is theirs."""
    mine = "/var/lib/gexis-music/Jazz"
    assert lf.wanted(["/var/lib/gexis-music", mine], [], music_on=False) == [mine]
    assert lf.wanted([mine], [], music_on=True) == [mine, "/var/lib/gexis-music"]


def test_the_music_folder_switched_on_keeps_its_place():
    """No write every 20 s: an unchanged list is the same list, in order."""
    current = ["/srv/elsewhere", "/var/lib/gexis-music"]
    assert lf.wanted(current, [], music_on=True) == current


def _rpc(prefs):
    async def rpc(command):
        if command[:3] == ["pref", "mediadirs", "?"]:
            return {"_p2": prefs["mediadirs"]}
        if command[:2] == ["pref", "mediadirs"]:
            prefs["mediadirs"] = command[2]
        return {}
    return rpc


def test_only_the_chosen_usb_folders_are_offered(monkeypatch, tmp_path):
    """ADR-0115 decision 23: a folder chosen on a drive, not the drive; a
    drive with nothing chosen is not added (George: "1b")."""
    usb = tmp_path / "usb"
    (usb / "AAAA" / "Music" / "Jazz").mkdir(parents=True)
    (usb / "BBBB").mkdir(parents=True)
    monkeypatch.setattr(lf, "MANAGED", (usb, tmp_path / "shares"))
    monkeypatch.setattr(lf, "USB", usb)
    prefs = {"mediadirs": []}
    chosen = [str(usb / "AAAA" / "Music")]
    assert asyncio.run(lf.sync(_rpc(prefs), is_mount=lambda p: p.endswith(("AAAA", "BBBB")),
                               usb_seen=tmp_path / "seen.json", music_on=False, usb_chosen=chosen)) is True
    assert prefs["mediadirs"] == [str(usb / "AAAA" / "Music")]


def test_a_chosen_folder_stays_for_7_days_after_its_drive_is_unplugged(monkeypatch, tmp_path):
    """Decision 17 holds for a chosen folder as for a whole drive."""
    usb = tmp_path / "usb"
    (usb / "AAAA" / "Music").mkdir(parents=True)
    monkeypatch.setattr(lf, "MANAGED", (usb, tmp_path / "shares"))
    monkeypatch.setattr(lf, "USB", usb)
    seen = tmp_path / "seen.json"
    chosen = [str(usb / "AAAA" / "Music")]
    prefs = {"mediadirs": []}
    asyncio.run(lf.sync(_rpc(prefs), is_mount=lambda p: True, usb_seen=seen, music_on=False, usb_chosen=chosen))
    assert prefs["mediadirs"] == chosen
    # Unplugged: no longer mounted, seen moments ago.
    asyncio.run(lf.sync(_rpc(prefs), is_mount=lambda p: False, usb_seen=seen, music_on=False, usb_chosen=chosen))
    assert prefs["mediadirs"] == chosen
    # Removed from the choice: out.
    asyncio.run(lf.sync(_rpc(prefs), is_mount=lambda p: False, usb_seen=seen, music_on=False, usb_chosen=[]))
    assert prefs["mediadirs"] == []


def test_the_music_folders_space_reads_as_a_phone_shows_it(tmp_path):
    """George, 2026-10-18: "For music folder display total available and
    free space"."""
    assert lf.size_text(51_234_000_000) == "51.2 GB"
    assert lf.size_text(256_000_000_000) == "256 GB"
    assert lf.size_text(1_500_000_000_000) == "1.5 TB"
    space = lf.music_space(tmp_path / "Music")
    assert space["free"] <= space["total"] and space["text"].count(" free of ") == 1
