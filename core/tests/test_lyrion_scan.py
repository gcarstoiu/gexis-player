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
    """George's Ark refuses a guest list; his Nuc does not."""
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
