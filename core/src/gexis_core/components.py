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
import shutil
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
            merged = {**base, **live}
            # **Never a "Starting…" over nothing.** The helper replaces
            # `preparing` within seconds; one still standing a minute on means
            # the download never began, and the row must say so.
            updated = merged.get("updated")
            if merged["state"] == "preparing" and updated and time.time() - updated > STALLED_S:
                merged.update(state="failed", error="The download did not start")
            return merged
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


#: A `preparing` older than this with nothing after it did not start.
STALLED_S = 60


def failed(name: str, pin: dict[str, str] | None, reason: str, *, status_dir: Path = STATUS) -> None:
    """Say it failed, and why - for a failure the helper itself never saw."""
    pin = pin or {}
    payload = {"name": name, "label": pin.get("LABEL", name), "from": pin.get("FROM", "its maker"),
               "state": "failed", "received": None, "total": None, "attempt": None,
               "attempts": None, "error": reason, "updated": int(time.time())}
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


#: Where a download may be removed from, and how deep below it at least:
#: a folder in /opt, or a folder in someone's home - never a home itself.
PLACES = ((Path("/opt"), 1), (Path("/home"), 2))
#: Where a pin's `DATA` may be: two levels inside /var/lib - a program's own
#: folder's subfolders (`/var/lib/squeezeboxserver/prefs`), never the folder.
DATA_PLACES = ((Path("/var/lib"), 2),)


def _inside(raw: str, places) -> Path | None:
    path = Path(raw)
    if not raw or not path.is_absolute() or ".." in path.parts:
        return None
    if not any(path.is_relative_to(top) and len(path.parts) - len(top.parts) >= depth
               for top, depth in places):
        return None
    return path


def _delete(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def remove(name: str, pin: dict[str, str], *, status_dir: Path = STATUS,
           installed_dir: Path = INSTALLED, places=PLACES, data_places=DATA_PLACES) -> Path:
    """**Remove** (ADR-0100, amended 2026-09-28): delete the downloaded software,
    its installed-version stamp and its status, so the row reads *Not
    installed* and switching on downloads it again.

    The caller refuses while the plugin is on. Here the only guard is the path:
    it must be the one the image's own pin names, absolute, and inside `/opt`
    (`/opt/lyrion`) or inside a home directory (`/home/pi/plexamp`) - never
    one of those itself - so an empty or mangled pin cannot become
    `rm -rf /opt`. (It asked for three parts below `/` until 2026-10-03, which
    refused `/opt/lyrion` and left the Lyrion server's Remove doing nothing.)
    Settings and whatever the software wrote outside `DEST` stay (Plexamp's
    sign-in among them) - unless the pin names it as `DATA`, colon-separated
    folders deleted with it (ADR-0115 decision 14: the Lyrion server's
    preferences and library). Every path is checked before anything is
    deleted, so a bad one deletes nothing."""
    raw = (pin or {}).get("DEST", "")
    dest = _inside(raw, places)
    if dest is None:
        raise ValueError(f"{name}: refusing to remove {raw!r}")
    data = []
    for part in filter(None, (pin.get("DATA") or "").split(":")):
        path = _inside(part, data_places)
        if path is None:
            raise ValueError(f"{name}: refusing to remove data {part!r}")
        data.append(path)
    for path in (dest, dest.with_name(dest.name + ".old"), *data):
        _delete(path)
    for stale in (installed_dir / f"{name}.sha256", status_dir / f"{name}.json"):
        stale.unlink(missing_ok=True)
    logger.info("components: %s removed from %s%s", name, dest,
                f" with {', '.join(map(str, data))}" if data else "")
    return dest

