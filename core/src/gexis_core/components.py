# SPDX-License-Identifier: GPL-3.0-or-later
"""Software a plugin downloads when it is switched on (ADR-0100), and what the
user is told about it while it happens.

**George, 2026-09-27:** *"Even if it's extremely fast, feedback is a must. Also
retry in case of failure and a general status. This goes for all plugins which
require a download."*

`gexis-fetch-component` writes `/run/gexis/components/<name>.json` at every
step: preparing, downloading (bytes of total, attempt n of N), retrying,
verifying, installing, installed, failed. This module reads those files and
the pins beside them (`/usr/share/gexis/components/<name>.env`, which name the
plugin a download belongs to), and turns them into what the panel draws
under that plugin's switch.
"""
from __future__ import annotations

import json
import logging
import shlex
import time
from pathlib import Path

logger = logging.getLogger("gexis_core.components")

PINS = Path("/usr/share/gexis/components")
STATUS = Path("/run/gexis/components")
INSTALLED = Path("/var/lib/gexis/components")

#: States in which something is still happening; the watcher polls quickly
#: while any component is in one.
BUSY = frozenset({"preparing", "downloading", "retrying", "verifying", "installing"})


def read_pin(path: Path) -> dict[str, str]:
    """A pin's variables. Shell syntax, but only `KEY=value` lines: nothing is
    executed to read it."""
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, raw = line.partition("=")
        try:
            parts = shlex.split(raw, comments=True)
        except ValueError:
            continue
        values[key.strip()] = parts[0] if parts else ""
    return values


def pins(directory: Path = PINS) -> dict[str, dict[str, str]]:
    """Every component the image knows how to fetch, by name."""
    if not directory.is_dir():
        return {}
    return {p.stem: read_pin(p) for p in sorted(directory.glob("*.env"))}


def for_plugin(plugin_id: str, directory: Path = PINS) -> str | None:
    """The component a plugin's switch downloads, if it downloads one."""
    for name, pin in pins(directory).items():
        if pin.get("PLUGIN") == plugin_id:
            return name
    return None


def status(name: str, pin: dict[str, str] | None = None, *, status_dir: Path = STATUS,
           installed_dir: Path = INSTALLED) -> dict:
    """What the panel says about one component.

    The helper's own file when there is one. Before it has ever run, the
    answer comes from what is on disk: installed (a stamp matching the pin)
    or not installed yet."""
    pin = pin or {}
    base = {"name": name, "label": pin.get("LABEL", name), "from": pin.get("FROM", "its maker"),
            "state": "absent", "received": None, "total": None, "attempt": None,
            "attempts": None, "error": None, "updated": None}
    try:
        live = json.loads((status_dir / f"{name}.json").read_text())
        if isinstance(live, dict):
            return {**base, **live}
    except (OSError, ValueError):
        pass
    try:
        stamp = (installed_dir / f"{name}.sha256").read_text().strip()
    except OSError:
        stamp = None
    if stamp and stamp == pin.get("SHA256"):
        base["state"] = "installed"
    return base


def preparing(name: str, pin: dict[str, str] | None = None, *, status_dir: Path = STATUS) -> None:
    """Said the moment the switch goes on, before systemd has started the
    download - so there is never a gap in which nothing is shown."""
    pin = pin or {}
    current = status(name, pin, status_dir=status_dir)
    if current["state"] == "installed" or current["state"] in BUSY:
        return
    payload = {"name": name, "label": pin.get("LABEL", name), "from": pin.get("FROM", "its maker"),
               "state": "preparing", "received": None, "total": None, "attempt": None,
               "attempts": None, "error": None, "updated": int(time.time())}
    try:
        status_dir.mkdir(parents=True, exist_ok=True)
        tmp = status_dir / f"{name}.json.tmp"
        tmp.write_text(json.dumps(payload))
        tmp.replace(status_dir / f"{name}.json")
    except OSError as exc:
        logger.warning("components: cannot write %s's status: %s", name, exc)


def all_status(directory: Path = PINS, *, status_dir: Path = STATUS,
               installed_dir: Path = INSTALLED) -> dict[str, dict]:
    return {name: status(name, pin, status_dir=status_dir, installed_dir=installed_dir)
            for name, pin in pins(directory).items()}
