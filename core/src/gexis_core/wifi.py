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
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

NMCLI = "nmcli"
#: How often the connected network's name is re-read, in the background.
#: **Not a lazy TTL.** It was one, and the accessor read `nmcli` itself when
#: the window expired - which measured **3.2 s inside the request handler**
#: on the device, blocking the whole daemon and leaving the settings sheet
#: sitting there with nothing to show for it (George, 2026-09-21). Bounding
#: how *often* that happened was never the point; it had to not happen at
#: all on the request path.
CONNECTED_EVERY_S = 20.0
#: A rescan takes seconds and the sheet waits on it. Longer than the scan
#: itself so a slow adapter is not reported as an empty network.
SCAN_TIMEOUT_S = 20.0
#: Association, DHCP and a route. NetworkManager gives up on its own well
#: inside this; the timeout is the backstop for a command that never returns.
JOIN_TIMEOUT_S = 45.0
SHORT_TIMEOUT_S = 10.0


def available() -> bool:
    return shutil.which(NMCLI) is not None


_connected: str | None = None


def connected_ssid() -> str | None:
    """The network this device is on, or None.

    **A pure read of what was last seen.** It is the `wifi` row's value and
    the settings payload is built synchronously, so this may not do any
    work: `watch_connected` keeps it current from its own task, where being
    slow costs nobody a response.

    None before the first read has finished, which is a second at boot. The
    row shows no network for that second rather than the wrong one.
    """
    return _connected


async def refresh_connected() -> str | None:
    """Re-read the connected network. Async, so the subprocess is awaited
    rather than blocking whatever is running."""
    global _connected
    if not available():
        return None
    rc, out, _ = await _run("-t", "-f", "ACTIVE,SSID", "device", "wifi")
    if rc != 0:
        return _connected
    for line in out.splitlines():
        parts = _fields(line)
        if len(parts) >= 2 and parts[0] == "yes" and parts[1]:
            _connected = parts[1]
            return _connected
    _connected = None
    return None


async def watch_connected(every: float = CONNECTED_EVERY_S) -> None:
    """Keep `connected_ssid` current for as long as the daemon runs."""
    while True:
        try:
            await refresh_connected()
        except Exception:  # pragma: no cover - a watcher must not die
            logger.exception("wifi: connection read failed")
        await asyncio.sleep(every)


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


async def saved_ssids(run=None) -> dict[str, str]:
    """SSID -> the name of the saved connection that carries it.

    **A saved connection is not named after its network.** This image ships
    one called `preconfigured`, so matching by connection name would report
    every known network as unknown and offer to forget nothing.
    """
    run = run or _run
    rc, out, _ = await run(
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
        rc2, ssid_out, _ = await run(
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
    details = await connected_details()
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
            if details and details.get("speed"):
                meta = f"Connected · {details['speed']}"
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
        if connected and details:
            item["details"] = details["details"]
        # The same network is seen once per band and per access point; the
        # strongest sighting is the one worth showing.
        if ssid not in best or item["bars"] > best[ssid]["bars"] or connected:
            best[ssid] = item
    order = {"connected": 0, "saved": 1, "open": 2, "locked": 2}
    return sorted(best.values(), key=lambda i: (order[i["state"]], -i["bars"], i["name"].lower()))


async def _quiet(*cmd: str, timeout: float = SHORT_TIMEOUT_S) -> str:
    """Another tool's output, or "" - details are a nicety, never an error."""
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(process.communicate(), timeout)
        return out.decode("utf-8", "replace")
    except (OSError, asyncio.TimeoutError):
        return ""


def _level_dbm(proc_wireless: str, device: str) -> int | None:
    """`/proc/net/wireless`'s signal level for one interface, in dBm."""
    for line in proc_wireless.splitlines():
        if line.strip().startswith(f"{device}:"):
            parts = line.split()
            try:
                return int(float(parts[3].rstrip(".")))
            except (IndexError, ValueError):
                return None
    return None


def _bitrate(iwconfig: str) -> str | None:
    """The link's current speed from `iwconfig` - what the radio is using
    now, not the access point's best (nmcli's RATE)."""
    m = re.search(r"Bit Rate[=:]\s*([\d.]+)\s*([GMk]b/s)", iwconfig)
    if not m:
        return None
    value = float(m.group(1))
    # Whole megabits: "292.5 Mb/s" broke the connected line in two on a
    # phone, and the half adds nothing a listener can use.
    if m.group(2) == "Mb/s":
        return f"{int(value + 0.5)} Mb/s"
    return f"{value:g} {m.group(2)}"


def _band(freq_mhz: str) -> str | None:
    try:
        mhz = int(freq_mhz.split()[0])
    except (ValueError, IndexError):
        return None
    return "2.4 GHz" if mhz < 3000 else "6 GHz" if mhz >= 5925 else "5 GHz"


async def connected_details(device: str = "wlan0") -> dict | None:
    """**The connected network, in detail** (ADR-0123): signal, speed, band,
    channel and address. Cheap - no rescan - so the open sheet can ask
    every few seconds. None when not connected."""
    if not available():
        return None
    rc, out, _ = await _run("-t", "-f", "IN-USE,SSID,SIGNAL,CHAN,FREQ", "device", "wifi", "list", "--rescan", "no")
    if rc != 0:
        return None
    row = next((_fields(l) for l in out.splitlines() if l.startswith("*")), None)
    if not row or len(row) < 5:
        return None
    _, ssid, signal, chan, freq = row[:5]
    rc, show, _ = await _run("-t", "-f", "IP4.ADDRESS", "device", "show", device)
    address = None
    for line in show.splitlines() if rc == 0 else ():
        value = _fields(line)[-1]
        if value:
            address = value.split("/")[0]
            break
    try:
        level = _level_dbm(Path("/proc/net/wireless").read_text(), device)
    except OSError:
        level = None
    speed = _bitrate(await _quiet("iwconfig", device))
    band = _band(freq)
    try:
        percent = int(signal)
    except ValueError:
        percent = None
    lines = []
    if percent is not None or level is not None:
        lines.append(["Signal", " · ".join(x for x in (f"{level} dBm" if level is not None else None,
                                                       f"{percent} %" if percent is not None else None) if x)])
    if speed:
        lines.append(["Speed", speed])
    if band or chan:
        lines.append(["Band", " · ".join(x for x in (band, f"channel {chan}" if chan else None) if x)])
    if address:
        lines.append(["Address", address])
    return {"name": ssid, "speed": speed, "details": lines}


def join_reason(rc: int, err: str) -> str:
    """NetworkManager's refusal, as the page and the panel say it - in
    Setup and in Settings alike."""
    text = (err or "").lower()
    if rc == 124:
        return "It took too long. The network may be out of range."
    if "secrets were required" in text or "no secrets" in text:
        return "The password was not accepted."
    if "no network with ssid" in text or "not found" in text or "could not be found" in text:
        return "No network with that name is in range."
    # The `Error:` line, not the last one: NetworkManager follows it with a
    # `Hint: use 'journalctl -xe ...'` line, which reached the panel as the
    # reason on the first scripted trial.
    for line in (err or "").splitlines():
        if line.startswith("Error:"):
            said = line.removeprefix("Error:").strip().removeprefix("Connection activation failed:").strip()
            if said:
                return said[0].upper() + said[1:].rstrip(".") + "."
    return "The network refused the connection."


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
    await refresh_connected()
    if rc == 0:
        return True, None
    logger.info("wifi: could not join %s: rc %s, %s", ssid, rc, (err or "").strip()[:200])
    return False, join_reason(rc, err)


async def forget(ssid: str) -> tuple[bool, str | None]:
    """Delete the saved connection for a network, so it stops reconnecting."""
    saved = await saved_ssids()
    name = saved.get(ssid)
    if name is None:
        return False, "That network is not saved."
    rc, _, err = await _run("connection", "delete", name)
    await refresh_connected()
    if rc == 0:
        return True, None
    logger.info("wifi: could not forget %s: %s", ssid, (err or "").strip()[:200])
    return False, "Could not forget that network."
