"""ADR-0115's scan: servers that announce themselves, then a server's shares."""
from __future__ import annotations

import subprocess

import pytest

from gexis_core import lyrion_scan as sc

BROWSE = "\n".join([
    "+;wlan0;IPv4;Box;_smb._tcp;local",
    "=;wlan0;IPv4;Box;_smb._tcp;local;Box.local;10.0.0.20;445;",
    "=;wlan0;IPv6;Box;_smb._tcp;local;Box.local;fe80::1;445;",
    "=;wlan0;IPv4;player;_smb._tcp;local;player.local;10.0.0.5;445;",
    "=;wlan0;IPv4;Store;_nfs._tcp;local;Store.local;10.0.0.30;2049;",
])


def test_servers_are_found_once_by_name_and_this_device_is_not_one():
    found = sc.parse_browse(BROWSE, own={"player", "player.local", "10.0.0.5"})
    assert found == [sc.Server("Box", "Box.local", "smb"), sc.Server("Store", "Store.local", "nfs")]


def test_a_server_s_disk_shares_and_not_its_hidden_or_printer_ones():
    out = "Disk|Music|\nDisk|Video|films\nDisk|backup$|\nIPC|IPC$|IPC Service\nPrinter|hp|\n"
    assert sc.parse_smb_shares(out, "Box.local") == [
        {"address": "//Box.local/Music", "comment": ""}, {"address": "//Box.local/Video", "comment": "films"}]
    assert sc.parse_nfs_exports("Export list for Store.local:\n/volume1/music *\n", "Store.local") == [
        {"address": "Store.local:/volume1/music", "comment": ""}]


def test_a_nas_that_refuses_a_guest_asks_for_a_login_and_the_password_stays_off_the_command_line():
    """A NAS (Storebox) refuses a guest list; a mini PC (Minibox) does not."""
    calls = []

    def run(command, **kw):
        calls.append(command)
        if "-N" in command:
            return subprocess.CompletedProcess(command, 1, "", "session setup failed: NT_STATUS_LOGON_FAILURE")
        return subprocess.CompletedProcess(command, 0, "Disk|Music|\n", "")

    box = sc.Server("Box", "Box.local", "smb")
    with pytest.raises(sc.NeedsLogin):
        sc.shares(box, run=run)
    assert sc.shares(box, "me", "s3cret", run=run) == [{"address": "//Box.local/Music", "comment": ""}]
    assert not any("s3cret" in part for c in calls for part in c)
    assert "-A" in calls[-1]


def test_a_host_from_the_request_is_never_read_as_an_option():
    """Review, 2026-10-12: the browsed host comes from the request."""
    calls = []

    def run(command, **kw):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "Export list:\n", "")

    sc.shares(sc.Server("x", "-d", "nfs"), run=run)
    assert calls[-1] == ["showmount", "-e", "--", "-d"]


def test_a_server_that_does_not_answer_is_said_so_not_an_error_page():
    """Review, 2026-10-12: smbclient or showmount past its timeout escaped
    as an HTTP 500."""
    def slow(command, **kw):
        raise subprocess.TimeoutExpired(command, kw.get("timeout"))

    for kind in ("smb", "nfs"):
        with pytest.raises(sc.NoAnswer) as refused:
            sc.shares(sc.Server("Box", "Box.local", kind), run=slow)
        assert isinstance(refused.value, ValueError) and str(refused.value) == "Box to answer"
    assert sc.servers(set(), run=slow) == []


def test_one_machine_announced_under_two_names_is_one_row_named_by_its_host():
    """Found 2026-10-16: a player announced its share as `BEDROOMPI` and as
    `bedroompi-2`, both on `bedroompi-2.local`, and the scan listed it twice."""
    browse = "\n".join([
        "=;wlan0;IPv4;bedroompi-2;_smb._tcp;local;bedroompi-2.local;10.0.0.7;445;",
        "=;wlan0;IPv4;BEDROOMPI;_smb._tcp;local;bedroompi-2.local;10.0.0.7;445;",
        "=;wlan0;IPv6;BEDROOMPI;_smb._tcp;local;bedroompi-2.local;fe80::7;445;",
    ])
    assert sc.parse_browse(browse) == [sc.Server("bedroompi-2", "bedroompi-2.local", "smb")]


def test_a_server_with_no_host_name_keeps_its_announced_name():
    browse = "=;wlan0;IPv4;Shelf;_smb._tcp;local;;10.0.0.9;445;"
    assert sc.parse_browse(browse) == [sc.Server("Shelf", "10.0.0.9", "smb")]


def test_a_share_folder_is_listed_with_smbclient_and_never_as_commands():
    """George, 2026-10-18: deeper than a share's top. The path goes inside
    smbclient's quotes; a `;` or `"` in it is refused, not run."""
    calls = []

    def run(args, **kw):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout=(
            "  .                                   D        0  Tue Sep  8 15:19:30 2026\n"
            "  Blues                               D        0  Thu Jan  2 20:50:14 2025\n"
            "  cover.jpg                           A    12345  Thu Jan  2 20:50:14 2025\n"), stderr="")

    assert sc.folders("//nas.local/Music/Jazz", run=run) == ["Blues"]
    assert calls[-1][:3] == ["smbclient", "//nas.local/Music", "-N"]
    assert calls[-1][-1] == 'cd "Jazz"; ls'
    for bad in ('//nas.local/Music/a"; rm x', "//nas.local/Music/a;ls", "//nas.local/Music/../x", "nas:/music"):
        with pytest.raises(ValueError):
            sc.folders(bad, run=run)
