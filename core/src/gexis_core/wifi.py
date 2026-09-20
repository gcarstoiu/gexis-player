# SPDX-License-Identifier: GPL-3.0-or-later
"""Wi-Fi through NetworkManager, for ADR-0044 §1's `list` row.

**`nmcli`, not D-Bus.** NetworkManager's D-Bus API would avoid a subprocess,
but it also means reimplementing the secret-agent dance that `nmcli` already
does for a WPA passphrase. The daemon runs as root on this image
(`gexis-core.service`, `User=root`, as `bluealsa-aplay.service` does), so
there is no polkit prompt to answer and nothing is gained by the longer road.

**`-t` output is escaped, not split-able.** `nmcli --terse` separates fields
with `:` and escapes a literal `:` or `\\` inside a value as `\\:` and `\\\\`.
An SSID may contain either. `_fields` walks the escapes rather than calling
`split(":")`, which would quietly cut a network called `2:1` in half.

**What is never done here:** nothing changes the connection the daemon is
reachable over without being asked. A scan is read-only; joining and
forgetting are explicit per-item actions from the settings sheet.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)

NMCLI = "nmcli"
#: How long the connected network's name is trusted without asking again.
#: `/settings` is built synchronously and is fetched on load and after every
#: write, so reading it per request would put a subprocess in the way of the
#: settings screen; it changes when someone joins a network, and that path
#: clears this itself.
CONNECTED_TTL_S = 10.0
#: A rescan takes seconds and the sheet waits on it. Longer than the scan
#: itself so a slow adapter is not reported as an empty network.
SCAN_TIMEOUT_S = 20.0
#: Association, DHCP and a route. NetworkManager gives up on its own well
#: inside this; the timeout is the backstop for a command that never returns.
JOIN_TIMEOUT_S = 45.0
SHORT_TIMEOUT_S = 10.0


def available() -> bool:
    return shutil.which(NMCLI) is not None


_connected: tuple[float, str | None] = (0.0, None)


def forget_connected() -> None:
    """Drop the cached name. Called where the connection itself changes."""
    global _connected
    _connected = (0.0, None)


def connected_ssid(now: Callable[[], float] = time.monotonic) -> str | None:
    """The network this device is on, or None.

    **Synchronous on purpose.** It is the `wifi` row's value, and the
    settings payload is built without a running loop to await in. The TTL is
    what keeps that honest: one short `nmcli` call every ten seconds at
    worst, and the join path clears it so a change is never stale.
    """
    global _connected
    when, cached = _connected
    moment = now()
    if cached is not None and moment - when < CONNECTED_TTL_S:
        return cached
    if not available():
        return None
    try:
        result = subprocess.run(
            [NMCLI, "-t", "-f", "ACTIVE,SSID", "device", "wifi"],
            capture_output=True,
            timeout=SHORT_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.info("wifi: cannot read the connection: %s", exc)
        return cached
    ssid = None
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        parts = _fields(line)
        if len(parts) >= 2 and parts[0] == "yes" and parts[1]:
            ssid = parts[1]
            break
    _connected = (moment, ssid)
    return ssid


async def _run(*args: str, timeout: float = SHORT_TIMEOUT_S) -> tuple[int, str, str]:
    """`nmcli` with its arguments, never a shell. Returns rc, stdout, stderr;
    a timeout is rc 124, matching the shell's own convention, so a caller
    reports "took too long" rather than "failed for no reason"."""
    try:
        process = await asyncio.create_subprocess_exec(
            NMCLI,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        logger.info("wifi: cannot run %s: %s", NMCLI, exc)
        return 127, "", str(exc)
    try:
        out, err = await asyncio.wait_for(process.communicate(), timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return 124, "", "timed out"
    return (
        process.returncode or 0,
        out.decode("utf-8", "replace"),
        err.decode("utf-8", "replace").strip(),
    )


def _fields(line: str) -> list[str]:
    """One `nmcli -t` row, unescaped. `\\:` is a colon in a value and `\\\\`
    a backslash; every other `:` separates two fields."""
    out: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            out.append("".join(current))
            current = []
        else:
            current.append(char)
    out.append("".join(current))
    return out


def _bars(signal: str) -> int:
    """NetworkManager's 0-100 as the four bars the sheet draws."""
    try:
        value = int(signal)
    except (TypeError, ValueError):
        return 0
    if value >= 75:
        return 4
    if value >= 55:
        return 3
    if value >= 35:
        return 2
    return 1


async def saved_ssids() -> dict[str, str]:
    """SSID -> the name of the saved connection that carries it.

    **A saved connection is not named after its network.** This image ships
    one called `preconfigured`, so matching by connection name would report
    every known network as unknown and offer to forget nothing.
    """
    rc, out, _ = await _run(
        "-t", "-f", "NAME,UUID,TYPE", "connection", "show"
    )
    if rc != 0:
        return {}
    found: dict[str, str] = {}
    for line in out.splitlines():
        parts = _fields(line)
        if len(parts) < 3 or "wireless" not in parts[2]:
            continue
        name, uuid = parts[0], parts[1]
        rc2, ssid_out, _ = await _run(
            "-t", "-f", "802-11-wireless.ssid", "connection", "show", uuid
        )
        if rc2 != 0:
            continue
        ssid = _fields(ssid_out.strip())[-1] if ssid_out.strip() else ""
        if ssid:
            found.setdefault(ssid, name)
    return found


async def scan() -> list[dict]:
    """Every network in range, as the settings sheet draws an item.

    The connected network comes first and the rest follow by signal, because
    a list of neighbours is read from the top and the one in use is the one
    being looked for.
    """
    rc, out, err = await _run(
        "-t",
        "-f",
        "IN-USE,SSID,SIGNAL,SECURITY",
        "device",
        "wifi",
        "list",
        "--rescan",
        "yes",
        timeout=SCAN_TIMEOUT_S,
    )
    if rc != 0:
        logger.info("wifi: scan failed: %s", err or rc)
        return []
    saved = await saved_ssids()
    best: dict[str, dict] = {}
    for line in out.splitlines():
        parts = _fields(line)
        if len(parts) < 4:
            continue
        in_use, ssid, signal, security = parts[0], parts[1], parts[2], parts[3]
        # A hidden network reports no SSID. There is nothing to show and
        # nothing to tap, so it is not an item.
        if not ssid:
            continue
        secured = bool(security.strip()) and security.strip() != "--"
        connected = in_use.strip() == "*"
        if connected:
            state, meta = "connected", "Connected"
        elif ssid in saved:
            state, meta = "saved", "Saved"
        elif secured:
            state, meta = "locked", "Secured"
        else:
            state, meta = "open", "Open"
        item = {
            "name": ssid,
            "meta": meta,
            "bars": _bars(signal),
            "state": state,
            "secured": secured,
        }
        # The same network is seen once per band and per access point; the
        # strongest sighting is the one worth showing.
        if ssid not in best or item["bars"] > best[ssid]["bars"] or connected:
            best[ssid] = item
    order = {"connected": 0, "saved": 1, "open": 2, "locked": 2}
    return sorted(best.values(), key=lambda i: (order[i["state"]], -i["bars"], i["name"].lower()))


async def join(ssid: str, password: str | None = None) -> tuple[bool, str | None]:
    """Connect to one network. Returns (joined, message-if-not).

    A saved network needs no password and is brought up by name; a new
    secured one is joined with the passphrase, which `nmcli` stores. The
    error is NetworkManager's own last line, because "the password was not
    accepted" and "no network with that name" are different problems and
    only it knows which happened.
    """
    args = ["device", "wifi", "connect", ssid]
    if password:
        args += ["password", password]
    rc, _, err = await _run(*args, timeout=JOIN_TIMEOUT_S)
    forget_connected()
    if rc == 0:
        return True, None
    if rc == 124:
        return False, "Took too long. The network may be out of range."
    return False, (err.splitlines()[-1] if err else "Could not join that network.")


async def forget(ssid: str) -> tuple[bool, str | None]:
    """Delete the saved connection for a network, so it stops reconnecting."""
    saved = await saved_ssids()
    name = saved.get(ssid)
    if name is None:
        return False, "That network is not saved."
    rc, _, err = await _run("connection", "delete", name)
    forget_connected()
    if rc == 0:
        return True, None
    return False, (err.splitlines()[-1] if err else "Could not forget that network.")
