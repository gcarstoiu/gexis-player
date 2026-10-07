# SPDX-License-Identifier: GPL-3.0-or-later
"""The connected Wi-Fi network in detail (ADR-0123)."""
from __future__ import annotations

import pytest

from gexis_core import wifi

# --- ADR-0123: the connected network in detail ------------------------------

def test_the_signal_speed_and_band_are_read_from_their_sources():
    proc = ("Inter-| sta-|   Quality        |   Discarded packets\n"
            " face | tus | link level noise |  nwid  crypt\n"
            " wlan0: 0000   53.  -57.  -256        0      0      0    543      0        0\n")
    assert wifi._level_dbm(proc, "wlan0") == -57
    assert wifi._level_dbm(proc, "eth0") is None
    assert wifi._bitrate("wlan0  IEEE 802.11  ESSID:x\n  Bit Rate=390 Mb/s   Tx-Power=31 dBm") == "390 Mb/s"
    assert wifi._bitrate("no rate here") is None
    assert wifi._band("5580 MHz") == "5 GHz" and wifi._band("2437 MHz") == "2.4 GHz"


@pytest.mark.asyncio
async def test_the_connected_network_comes_with_its_details(monkeypatch):
    async def fake_run(*args, timeout=None):
        if "list" in args:
            return 0, "*:Home:65:116:5580 MHz\n :Other:40:6:2437 MHz\n", ""
        if "show" in args:
            return 0, "IP4.ADDRESS[1]:192.168.1.20/24\n", ""
        return 1, "", ""

    async def fake_quiet(*cmd, timeout=None):
        return "  Bit Rate=390 Mb/s"

    monkeypatch.setattr(wifi, "available", lambda: True)
    monkeypatch.setattr(wifi, "_run", fake_run)
    monkeypatch.setattr(wifi, "_quiet", fake_quiet)
    found = await wifi.connected_details()
    lines = dict(found["details"])
    assert found["name"] == "Home" and found["speed"] == "390 Mb/s"
    assert lines["Speed"] == "390 Mb/s" and lines["Band"] == "5 GHz · channel 116"
    assert lines["Address"] == "192.168.1.20" and lines["Signal"].endswith("65 %")
