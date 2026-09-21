# SPDX-License-Identifier: GPL-3.0-or-later
"""One name, written to the four places that advertise it (ADR-0048).

ADR-0022 §2 decided there is a single `device_name` and no per-service
override; §3 decided a rename is restart-gated. This is the mechanism, and
the part worth reading twice is that **nothing here takes effect now**.

The hostname and the Bluetooth alias *could* be set live. They are not: the
hostname is how the device is reached, so changing it from a phone is how
that phone loses its way back, and applying two of four immediately leaves
the device advertising one name over Bluetooth and another over LMS until
the next restart - a state nobody asked for and nobody can explain.

Every target is attempted and the result names the ones that failed. They
are four independent files and any one of them can refuse; a single boolean
would leave a device half-renamed with nothing on screen to say so.
"""
from __future__ import annotations

import logging
import re
import socket
import unicodedata
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

#: What the image ships and what a name that sanitises to nothing falls back
#: to. The design's own fallback.
FALLBACK = "gexis"
#: RFC 1123's limit on one label, which is what a `.local` name is.
HOSTNAME_MAX = 63

HOSTNAME_PATH = Path("/etc/hostname")
HOSTS_PATH = Path("/etc/hosts")
#: The image's interface to squeezelite's `-n`: the unit reads this rather
#: than carrying the name inside `ExecStart`, where only a drop-in restating
#: the whole command line could reach it (ADR-0048 §1).
ENV_PATH = Path("/etc/gexis/device-name.env")
ENV_KEY = "GEXIS_DEVICE_NAME"
LIBRESPOT_PATH = Path("/var/lib/go-librespot/config.yml")
BLUETOOTH_PATH = Path("/etc/bluetooth/main.conf")


def sanitise(name: str) -> str:
    """The hostname for a typed name. Accents fold, case drops, anything
    outside `[a-z0-9-]` becomes a hyphen, and what is left is trimmed and
    capped. A name with nothing usable in it gives `gexis`, which is visible
    in the header rather than silently substituted (ADR-0022)."""
    folded = unicodedata.normalize("NFKD", name or "")
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    folded = re.sub(r"[^a-zA-Z0-9-]+", "-", folded).lower()
    return folded.strip("-")[:HOSTNAME_MAX].strip("-") or FALLBACK


@dataclass(frozen=True)
class Written:
    """What a rename managed. `ok` is every target, not most of them."""

    hostname: str
    failed: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.failed

    def to_json(self) -> dict:
        return {"hostname": self.hostname, "ok": self.ok, "failed": list(self.failed)}


def _replace_line(path: Path, pattern: str, line: str) -> None:
    """Rewrite the one line a pattern matches, or append it. Read, edit,
    write - the files are small and a rename is rare, so nothing here is
    worth streaming."""
    text = path.read_text()
    new, count = re.subn(pattern, line, text, count=1, flags=re.MULTILINE)
    if count == 0:
        new = text if text.endswith("\n") or not text else text + "\n"
        new += line + "\n"
    if new != text:
        path.write_text(new)


def _write_hostname(host: str) -> None:
    HOSTNAME_PATH.write_text(host + "\n")
    if not HOSTS_PATH.exists():
        return
    # Debian's `127.0.1.1 <hostname>` line is what makes a machine able to
    # resolve its own name; without it sudo and anything else that tries
    # complains on every call.
    #
    # **Both names go on it while they differ.** A rename takes effect at the
    # restart (ADR-0048 §2), so between the two the system is still running
    # under the old name - and a hosts file naming only the new one would
    # leave the *current* hostname unresolvable for exactly that window. The
    # old alias is replaced outright by the next rename, so this never grows
    # past two.
    running = hostname()
    names = host if running in ("", host) else f"{host}\t{running}"
    _replace_line(HOSTS_PATH, r"^127\.0\.1\.1\s+.*$", f"127.0.1.1\t{names}")


def _write_env(name: str) -> None:
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.write_text(f"{ENV_KEY}={name}\n")


def _write_librespot(name: str) -> None:
    _replace_line(LIBRESPOT_PATH, r"^device_name:.*$", f"device_name: {name}")


def _write_bluetooth(name: str) -> None:
    # The commented-out `#Name = BlueZ` the package ships is matched too, so
    # a config that has never been touched still takes the name.
    _replace_line(BLUETOOTH_PATH, r"^#?\s*Name\s*=.*$", f"Name = {name}")


#: The four, by the name the user would recognise.
TARGETS = ("Spotify", "Bluetooth", "LMS", "mDNS")


def apply(name: str) -> Written:
    """Write the name to all four. Takes effect at the next restart.

    The dispatch list is built here rather than held as a module constant:
    a constant binds each function at import, which made the hostname a
    `None` special case inside the loop and made the failure path
    unreachable from a test.
    """
    host = sanitise(name)
    steps = (
        ("Spotify", lambda: _write_librespot(name)),
        ("Bluetooth", lambda: _write_bluetooth(name)),
        ("LMS", lambda: _write_env(name)),
        # The only one that takes the sanitised form.
        ("mDNS", lambda: _write_hostname(host)),
    )
    failed = []
    for label, write in steps:
        try:
            write()
        except OSError as exc:
            logger.warning("device name: %s not written: %s", label, exc)
            failed.append(label)
    return Written(hostname=host, failed=tuple(failed))


def hostname() -> str:
    return socket.gethostname()


def address() -> str | None:
    """The address this device is reached on, from the routing table.

    **Not `gethostbyname(gethostname())`**, which answers `127.0.1.1` on a
    Debian-derived image - true, and useless to someone trying to type it
    into a phone. A UDP socket "connected" to a documentation address
    (TEST-NET-1, RFC 5737) sends nothing and reports the interface that
    would carry it.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 9))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()
