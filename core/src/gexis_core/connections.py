# SPDX-License-Identifier: GPL-3.0-or-later
"""**Is a service connected to what it reports to?** (ADR-0129)

Read from the kernel's own table of TCP connections, by the user the unit runs
as - not from the service's log, whose wording is upstream's to change with
any version (Beszel went from 0.20 to 0.21 the day this was written). A
service that holds an established connection to somewhere off this device is
connected; one that is running without one is connecting for a while, then
not connected.

Coarse on purpose: a connection the far end has not yet accepted for good -
the Beszel hub checking the agent's key - counts for as long as it stays open,
which with a key it refuses is a second or two, shorter than one look.
"""
from __future__ import annotations

import pwd
import subprocess
from pathlib import Path

TABLES = (Path("/proc/net/tcp"), Path("/proc/net/tcp6"))
ESTABLISHED = "01"
#: What a running service without a connection is called *Connecting* for,
#: since it started or last had one: the Beszel agent retries every few
#: seconds, and a hub restarting takes about this long to come back.
GRACE_S = 60.0

_LOOPBACK_V6 = ("00000000000000000000000001000000",)


def unit_uid(unit: str) -> int | None:
    """The uid `User=` names, or None for a unit run as root or not asked."""
    try:
        result = subprocess.run(["systemctl", "show", "-p", "User", "--value", unit],
                                check=False, capture_output=True, text=True, timeout=5)
        name = (result.stdout or "").strip()
        return pwd.getpwnam(name).pw_uid if name else None
    except (OSError, subprocess.SubprocessError, KeyError):
        return None


def _off_device(remote: str) -> bool:
    address = remote.split(":")[0]
    if len(address) == 8:  # IPv4, little-endian: 127.x.x.x ends in 7F
        return not address.upper().endswith("7F") and address != "00000000"
    address = address.upper()
    if address in _LOOPBACK_V6 or address.strip("0") == "":
        return False
    if address.startswith("0000000000000000FFFF0000"):  # IPv4 mapped
        return not address.endswith("7F")
    return True


def established(uid: int, tables: tuple[Path, ...] = TABLES) -> bool:
    """Whether a process of this uid holds a TCP connection off this device."""
    for table in tables:
        try:
            lines = table.read_text().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            if len(fields) < 8 or fields[3] != ESTABLISHED:
                continue
            if fields[7] == str(uid) and _off_device(fields[2]):
                return True
    return False


def reading(active: str, connected: bool, quiet_s: float) -> tuple[str, str]:
    """The indicator for a switched-on service: its unit's state, whether it
    holds a connection, and how long it has been without one - since it was
    switched on, started, or last connected."""
    if active == "failed":
        return ("bad", "Not connected")
    if active == "active" and connected:
        return ("ok", "Connected")
    return ("wait", "Connecting") if quiet_s < GRACE_S else ("bad", "Not connected")
