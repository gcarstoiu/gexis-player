# SPDX-License-Identifier: GPL-3.0-or-later
"""**Finding network shares for the Lyrion server** (ADR-0115; George,
2026-10-03: *"for the network shares, can we have a Scan showing the
available shares in the network?"*, then *"A"*).

Two steps, as a person would take them: the servers that announce
themselves on the network (mDNS: `_smb._tcp`, `_nfs._tcp`), then one
server's shares - which a NAS often lists only after a login (George's Ark
refuses a guest; his Nuc does not), so that step can come back asking for
one. A server that does not announce itself (many Windows PCs) is still
added by typing its address.
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
from dataclasses import dataclass

logger = logging.getLogger(__name__)

TIMEOUT_S = 15


class NeedsLogin(Exception):
    """The server lists its shares only to a known user."""


@dataclass(frozen=True)
class Server:
    name: str
    host: str
    kind: str          # "smb" or "nfs"


def parse_browse(output: str, own: set[str] = frozenset()) -> list[Server]:
    """`avahi-browse -rtp` lines: `=;iface;proto;name;type;domain;host;address;port;txt`.
    One per server and kind, IPv4 first; this device's own left out."""
    seen: dict[tuple[str, str], Server] = {}
    for line in output.splitlines():
        parts = line.split(";")
        if len(parts) < 9 or parts[0] != "=":
            continue
        name, service, host, address = parts[3], parts[4], parts[6], parts[7]
        kind = "smb" if service == "_smb._tcp" else "nfs" if service == "_nfs._tcp" else None
        if kind is None or host in own or address in own or name in own:
            continue
        # By its announced name (Tower.local), which survives a new DHCP
        # address; the player resolves .local names through mDNS.
        seen[(name, kind)] = Server(name=name, host=host or address, kind=kind)
    return sorted(seen.values(), key=lambda s: (s.name.lower(), s.kind))


def servers(own: set[str], run=subprocess.run) -> list[Server]:
    found = []
    for service in ("_smb._tcp", "_nfs._tcp"):
        result = run(["avahi-browse", "-rtpk", service], capture_output=True, text=True,
                     timeout=TIMEOUT_S, check=False)
        found += parse_browse(result.stdout or "", own)
    return sorted(set(found), key=lambda s: (s.name.lower(), s.kind))


def parse_smb_shares(output: str, host: str) -> list[dict]:
    """`smbclient -L -g`: `Disk|name|comment` lines; printers and IPC$ and
    hidden ($) shares are not music folders."""
    out = []
    for line in output.splitlines():
        parts = line.split("|")
        if len(parts) >= 2 and parts[0] == "Disk" and not parts[1].endswith("$"):
            out.append({"address": f"//{host}/{parts[1]}", "comment": parts[2] if len(parts) > 2 else ""})
    return out


def parse_nfs_exports(output: str, host: str) -> list[dict]:
    """`showmount -e`: a header line, then `path  clients`."""
    out = []
    for line in output.splitlines()[1:]:
        path = line.split()[0] if line.split() else ""
        if path.startswith("/"):
            out.append({"address": f"{host}:{path}", "comment": ""})
    return out


def shares(server: Server, user: str | None = None, password: str | None = None,
           run=subprocess.run) -> list[dict]:
    """A server's shares. Raises NeedsLogin for an SMB server that refuses a
    guest (or the user given). The password reaches smbclient through a
    root-only file, never its command line."""
    if server.kind == "nfs":
        result = run(["showmount", "-e", server.host], capture_output=True, text=True,
                     timeout=TIMEOUT_S, check=False)
        return parse_nfs_exports(result.stdout or "", server.host)
    with tempfile.NamedTemporaryFile("w", prefix="gexis-smb-", delete=True) as auth:
        if user:
            auth.write(f"username={user}\npassword={password or ''}\n")
            auth.flush()
            login = ["-A", auth.name]
        else:
            login = ["-N"]
        result = run(["smbclient", "-L", f"//{server.host}", "-g", *login],
                     capture_output=True, text=True, timeout=TIMEOUT_S, check=False)
    text = (result.stdout or "") + (result.stderr or "")
    if "NT_STATUS_LOGON_FAILURE" in text or "NT_STATUS_ACCESS_DENIED" in text:
        raise NeedsLogin(server.name)
    return parse_smb_shares(result.stdout or "", server.host)
