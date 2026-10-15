# SPDX-License-Identifier: GPL-3.0-or-later
"""**The player announces for its plugins** (ADR-0142).

An uploaded plugin may not answer mDNS itself - its units deny it port 5353 -
because one that did published a host named after the device, avahi saw a
second claim on the Pi's own name and renamed the Pi (`guestpi-2.local`,
2026-10-12). A plugin asks instead (`{"t": "announce", "services": [...]}`),
and this writes what it asked for as one avahi service file, under the Pi's
own host name. The file goes when the plugin does, and all of them when the
core starts.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)

SERVICES = Path("/etc/avahi/services")
PREFIX = "gexis-plugin-"

MAX_SERVICES = 4
MAX_TXT = 20
TYPE = re.compile(r"^_[a-z0-9][a-z0-9-]{0,14}\._(tcp|udp)$")
TXT_KEY = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
#: avahi's limit on a service's name: one DNS label, counted in UTF-8 bytes,
#: not characters (Finding 125 #20, 2026-10-14).
NAME_MAX = 63
#: What the player announces itself - never a plugin's to announce.
OURS = frozenset({"_gexis._tcp", "_smb._tcp", "_device-info._tcp", "_workstation._tcp",
                  "_ssh._tcp", "_sftp-ssh._tcp"})


class Refused(ValueError):
    """The whole message is refused; the reason is for the log."""


def checked(services, device_name: str) -> list[dict]:
    """The services as they will be written, or `Refused` with why."""
    if not isinstance(services, list):
        raise Refused("services is not a list")
    if len(services) > MAX_SERVICES:
        raise Refused(f"{len(services)} services; at most {MAX_SERVICES}")
    out = []
    for s in services:
        if not isinstance(s, dict):
            raise Refused("a service is not an object")
        kind = s.get("type")
        if not isinstance(kind, str) or not TYPE.match(kind):
            raise Refused(f"type {kind!r} is not _name._tcp or _name._udp")
        if kind in OURS:
            raise Refused(f"{kind} is the player's own")
        port = s.get("port")
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            raise Refused(f"port {port!r} is not 1-65535")
        # The device name is the default, and it has no length limit of its
        # own: cut it to fit rather than refuse every service that leaves the
        # name out. A plugin's own name is its to shorten (Finding 125 #20).
        name = s.get("name") or _fitted(device_name)
        if not isinstance(name, str) or _too_long(name) or not name.strip():
            raise Refused(f"name is not text of at most {NAME_MAX} bytes")
        txt = s.get("txt") or {}
        if not isinstance(txt, dict) or len(txt) > MAX_TXT:
            raise Refused(f"txt is not an object of at most {MAX_TXT} entries")
        for k, v in txt.items():
            if not TXT_KEY.match(k):
                raise Refused(f"txt key {k!r} is not letters, digits, '.', '_' or '-'")
            if not isinstance(v, str) or len(f"{k}={v}".encode()) > 255:
                raise Refused(f"txt {k!r} is not text, or longer than 255 bytes")
        out.append({"type": kind, "port": port, "name": name, "txt": dict(txt)})
    return out


def _too_long(name: str) -> bool:
    try:
        return len(name.encode()) > NAME_MAX
    except UnicodeEncodeError:  # a lone surrogate survives json.loads
        return True


def _fitted(name):
    """The name cut to NAME_MAX bytes at a character boundary; anything that
    is not text is left for the check to refuse."""
    if not isinstance(name, str) or not _too_long(name):
        return name
    try:
        cut = name.encode()[:NAME_MAX].decode(errors="ignore")
    except UnicodeEncodeError:
        return name
    return cut.rstrip() or name


def render(services: list[dict]) -> list[str]:
    """One avahi service group per service - avahi reads one per file -
    so each carries its own name."""
    groups = []
    for s in services:
        txt = "".join(f"\n    <txt-record>{escape(f'{k}={v}')}</txt-record>" for k, v in s["txt"].items())
        groups.append(
            "<service-group>\n"
            f"  <name>{escape(s['name'])}</name>\n"
            "  <service>\n"
            f"    <type>{s['type']}</type>\n"
            f"    <port>{s['port']}</port>{txt}\n"
            "  </service>\n"
            "</service-group>\n")
    return groups


def path_for(plugin_id: str, directory: Path = SERVICES) -> Path:
    return directory / f"{PREFIX}{plugin_id}.service"


def write(plugin_id: str, services: list[dict], directory: Path = SERVICES) -> None:
    """The plugin's announcements, replacing what it had; none removes the
    file. avahi notices the folder change by itself."""
    path = path_for(plugin_id, directory)
    if not services:
        # The numbered files go too: a plugin that announced three services
        # and then sent [] kept the second and third advertised until it
        # disconnected (Finding 125 #18, 2026-10-14).
        withdraw(plugin_id, directory)
        return
    # avahi reads one service-group per file, so several services go in
    # several files: the first keeps the plain name, the rest are numbered.
    groups = render(services)
    for i, group in enumerate(groups):
        target = path if i == 0 else directory / f"{PREFIX}{plugin_id}.{i}.service"
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text('<?xml version="1.0" standalone="no"?>\n'
                       '<!DOCTYPE service-group SYSTEM "avahi-service.dtd">\n'
                       f"<!-- Announced for the plugin {escape(plugin_id)} (ADR-0142). Written by gexis-core. -->\n"
                       + group)
        tmp.replace(target)
    for stale in directory.glob(f"{PREFIX}{plugin_id}.*.service"):
        number = stale.name.rsplit(".", 2)[1]
        if not number.isdigit() or int(number) >= len(groups):
            stale.unlink(missing_ok=True)


def withdraw(plugin_id: str, directory: Path = SERVICES) -> None:
    path_for(plugin_id, directory).unlink(missing_ok=True)
    for extra in directory.glob(f"{PREFIX}{plugin_id}.*.service"):
        extra.unlink(missing_ok=True)


def clear(directory: Path = SERVICES) -> None:
    """At the core's start: nothing announced for a plugin not connected."""
    for path in directory.glob(f"{PREFIX}*.service"):
        path.unlink(missing_ok=True)
