# SPDX-License-Identifier: GPL-3.0-or-later
"""**The plugin catalogue** (ADR-0168, Phase 24): other authors' plugins,
listed in `gcarstoiu/gexis-plugins` once its checks pass and a person has
read them.

- **Trusted by its signature and serial, not by GitHub**, as the channel
  files are (ADR-0108): `catalogue.json` is verified with gpgv against the
  catalogue key the core package carries, and a serial lower than one already
  accepted is refused. The last good one is kept for a player offline.
- **Installed through the upload's own path** (`uploads.install`): the same
  checks, folder and sandbox. The catalogue adds where the archive comes from
  and that its bytes are the listed ones (size and sha256).
- **Withdrawn and blocked** (decision 5): a withdrawn version or plugin is
  not offered and is marked where it is installed; a blocked one is also
  switched off, and stays off.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable

import aiohttp

from gexis_core import plugins, uploads

logger = logging.getLogger("gexis_core.plugin_catalogue")

URL = "https://github.com/gcarstoiu/gexis-plugins/releases/download/index/catalogue.json"
KEYRING = Path("/usr/share/gexis/keys/gexis-catalogue.gpg")
STATE = Path("/var/lib/gexis/catalogue")
#: What the index may weigh; twenty entries are a few kilobytes.
MAX_INDEX = 2 * 1024 * 1024
FORMAT = 1
CONTRACTS = (1,)
#: Read by itself once a day, and when *More plugins* opens if older than this.
EVERY_S = 24 * 3600
FRESH_S = 15 * 60
SHA256 = re.compile(r"^[0-9a-f]{64}$")
TIMEOUT = aiohttp.ClientTimeout(total=30)
ARCHIVE_TIMEOUT = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=60)
HEADERS = {"User-Agent": "gexis-player"}


class Unavailable(Exception):
    """Why something from the catalogue cannot be had, in words for the page."""


@dataclass(frozen=True)
class Catalogue:
    serial: int
    date: str
    plugins: tuple[dict, ...]

    def entry(self, plugin_id: str) -> dict | None:
        return next((e for e in self.plugins if e["id"] == plugin_id), None)


def verify(data: bytes, signature: bytes, keyring: Path = KEYRING) -> None:
    if not keyring.is_file():
        raise Unavailable("this player has no catalogue key")
    with tempfile.TemporaryDirectory() as tmp:
        index, sig = Path(tmp) / "catalogue.json", Path(tmp) / "catalogue.json.sig"
        index.write_bytes(data)
        sig.write_bytes(signature)
        try:
            out = subprocess.run(["gpgv", "--keyring", str(keyring), str(sig), str(index)],
                                 capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Unavailable(f"its signature could not be checked ({exc})") from None
    if out.returncode != 0:
        raise Unavailable("its signature is not the catalogue key's")


def _usable(entry: object) -> bool:
    """Enough of an entry to show and install it. The catalogue's own check
    is the strict one; this keeps one bad entry from hiding the rest."""
    if not isinstance(entry, dict) or not plugins.ID.match(str(entry.get("id", ""))):
        return False
    if entry.get("kind") not in plugins.KINDS or not isinstance(entry.get("name"), str):
        return False
    versions = entry.get("versions")
    if not isinstance(versions, list) or not versions:
        return False
    for v in versions:
        if not isinstance(v, dict) or not isinstance(v.get("version"), str):
            return False
        if not str(v.get("url", "")).startswith("https://") or not SHA256.match(str(v.get("sha256", ""))):
            return False
        if not isinstance(v.get("size"), int) or not 0 < v["size"] <= uploads.MAX_BYTES:
            return False
    return True


def parse(data: bytes) -> Catalogue:
    try:
        raw = json.loads(data)
    except ValueError:
        raise Unavailable("it is not readable") from None
    if not isinstance(raw, dict) or raw.get("format") != FORMAT:
        raise Unavailable("it is in a form this player does not read")
    serial = raw.get("serial")
    if not isinstance(serial, int) or isinstance(serial, bool) or serial < 1:
        raise Unavailable("it has no serial")
    entries = []
    for entry in raw.get("plugins") or []:
        if _usable(entry):
            entries.append(entry)
        else:
            logger.warning("catalogue: an entry is not usable and is left out: %r",
                           entry.get("id") if isinstance(entry, dict) else entry)
    return Catalogue(serial=serial, date=str(raw.get("date", "")), plugins=tuple(entries))


def accepted_serial(state: Path = STATE) -> int:
    try:
        return int((state / "serial").read_text())
    except (OSError, ValueError):
        return 0


def _write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def accept(data: bytes, signature: bytes, *, keyring: Path = KEYRING, state: Path = STATE) -> Catalogue:
    """Verify, parse, refuse a lower serial, and keep it as the last good one."""
    verify(data, signature, keyring)
    catalogue = parse(data)
    seen = accepted_serial(state)
    if catalogue.serial < seen:
        raise Unavailable(f"it is older than the one already read (serial {catalogue.serial}, not {seen})")
    state.mkdir(parents=True, exist_ok=True)
    _write(state / "catalogue.json.sig", signature)
    _write(state / "catalogue.json", data)
    _write(state / "serial", str(catalogue.serial).encode())
    return catalogue


def last(*, keyring: Path = KEYRING, state: Path = STATE) -> Catalogue | None:
    """The last good catalogue on this player, verified again."""
    try:
        data = (state / "catalogue.json").read_bytes()
        signature = (state / "catalogue.json.sig").read_bytes()
        verify(data, signature, keyring)
        return parse(data)
    except (OSError, Unavailable):
        return None


async def _get(session: aiohttp.ClientSession, url: str, limit: int) -> bytes:
    async with session.get(url, timeout=TIMEOUT, headers=HEADERS) as response:
        if response.status != 200:
            raise Unavailable(f"GitHub answered {response.status}")
        data = await response.content.read(limit + 1)
    if len(data) > limit:
        raise Unavailable("it is larger than a catalogue can be")
    return data


async def download(session: aiohttp.ClientSession, url: str = URL) -> tuple[bytes, bytes]:
    try:
        return await _get(session, url, MAX_INDEX), await _get(session, url + ".sig", 64 * 1024)
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        raise Unavailable(f"it could not be reached ({exc.__class__.__name__})") from None


def release_tuple(release: str | None) -> tuple[int, ...]:
    """`1.9.1` -> (1, 9, 1); a build's `1.9.0+git9.484bd6d` reads as 1.9.0."""
    head = (release or "").split("+", 1)[0].split("~", 1)[0].split("-", 1)[0]
    try:
        return tuple(int(part) for part in head.split("."))
    except ValueError:
        return (0,)


def pulled(obj: dict) -> tuple[str, str] | None:
    """("blocked", why) or ("withdrawn", why), blocked first."""
    for state in ("blocked", "withdrawn"):
        reason = obj.get(state)
        if isinstance(reason, str) and reason.strip():
            return state, reason.strip()
    return None


def offer(entry: dict, release: str | None) -> dict | None:
    """The newest version this player may install: listed last, not pulled,
    its contract spoken here, its release reached."""
    if pulled(entry):
        return None
    for v in reversed(entry["versions"]):
        if pulled(v) or v.get("contract") not in CONTRACTS:
            continue
        if release_tuple(str(v.get("player", ""))) > release_tuple(release):
            continue
        return v
    return None


def _listed(entry: dict, version: str | None) -> dict | None:
    return next((v for v in entry["versions"] if v["version"] == version), None) if version else None


def pulled_for(catalogue: Catalogue | None, plugin_id: str, version: str | None) -> tuple[str, str] | None:
    """Whether the catalogue withdrew or blocked this plugin, or the version
    installed here; blocked first."""
    entry = catalogue.entry(plugin_id) if catalogue else None
    if entry is None:
        return None
    found = [state for state in (pulled(entry), pulled(_listed(entry, version) or {})) if state]
    return next((st for st in found if st[0] == "blocked"), found[0] if found else None)


def blocked(catalogue: Catalogue | None, installed: dict[str, str]) -> dict[str, str]:
    """Plugins from the catalogue on this player that must be off: id -> why."""
    found: dict[str, str] = {}
    for plugin_id, version in installed.items():
        state = pulled_for(catalogue, plugin_id, version)
        if state and state[0] == "blocked":
            found[plugin_id] = state[1]
    return found


def rows(catalogue: Catalogue | None, *, release: str | None, installed: dict[str, str],
         from_catalogue: set[str], ours: set[str]) -> list[dict]:
    """What *More plugins* shows, by name. A plugin not installed shows only
    when there is a version this player may install."""
    out = []
    for entry in sorted(catalogue.plugins if catalogue else (), key=lambda e: e["name"].lower()):
        plugin_id = entry["id"]
        if plugin_id in ours:
            continue
        offered = offer(entry, release)
        here = installed.get(plugin_id)
        state, reason = "available", None
        if here is not None and plugin_id not in from_catalogue:
            state = "uploaded"
        elif here is not None:
            mine = _listed(entry, here)
            pulled_now = pulled(entry) or (pulled(mine) if mine else None)
            newer = offered is not None and offered["version"] != here and (
                mine is None or entry["versions"].index(offered) > entry["versions"].index(mine))
            if pulled_now and pulled_now[0] == "blocked":
                state, reason = pulled_now
            elif newer:
                state = "update"
                reason = pulled_now[1] if pulled_now else None
            elif pulled_now:
                state, reason = pulled_now
            else:
                state = "installed"
        elif offered is None:
            continue
        out.append({
            "id": plugin_id, "name": entry["name"], "summary": entry.get("summary"),
            "kind": entry["kind"], "author": entry.get("author"), "source": entry.get("source"),
            "licence": entry.get("licence"),
            "version": offered["version"] if offered else None,
            "size": offered["size"] if offered else None,
            "installed": here, "state": state, "reason": reason,
        })
    return out


async def fetch_archive(session: aiohttp.ClientSession, version: dict,
                        progress: Callable[[int, int], None] = lambda done, total: None) -> bytes:
    """The archive, refused unless it is the listed one: no longer than its
    size, and its sha256 the listed one."""
    size = version["size"]
    digest = hashlib.sha256()
    chunks, done = [], 0
    try:
        async with session.get(version["url"], timeout=ARCHIVE_TIMEOUT, headers=HEADERS) as response:
            if response.status != 200:
                raise Unavailable(f"the download answered {response.status}")
            async for chunk in response.content.iter_chunked(1 << 16):
                done += len(chunk)
                if done > size:
                    raise Unavailable("the download is larger than the listed archive")
                digest.update(chunk)
                chunks.append(chunk)
                progress(done, size)
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        raise Unavailable(f"the download stopped ({exc.__class__.__name__})") from None
    if done != size or digest.hexdigest() != version["sha256"]:
        raise Unavailable("the download is not the listed archive")
    return b"".join(chunks)


@dataclass
class Job:
    plugin_id: str
    version: str
    phase: str = "downloading"   # downloading, installing, installed, failed
    done: int = 0
    total: int = 0
    error: str | None = None

    def to_json(self) -> dict:
        return {"version": self.version, "phase": self.phase, "done": self.done,
                "total": self.total, "error": self.error}


@dataclass
class Service:
    """The catalogue as the core runs it: read it, show it, install from it,
    keep blocked plugins off."""
    #: The installed release (`updates.installed_release`).
    release: Callable[[], str | None]
    #: Uploaded plugins on this player: id -> version (`uploads.versions`).
    installed: Callable[[], dict[str, str]]
    #: Which of them came from the catalogue (`uploads.origins`).
    from_catalogue: Callable[[], set[str]]
    #: The player's own plugin ids: never shown, never shadowed.
    ours: set[str]
    #: Install a checked archive as `id`; restarts the core (ADR-0106).
    install_archive: Callable[[bytes, str], Awaitable[dict]]
    #: Switch a plugin off because it is blocked: (id, why).
    switch_off: Callable[[str, str], Awaitable[None]]
    keyring: Path = KEYRING
    state: Path = STATE
    url: str = URL
    session: Callable[[], aiohttp.ClientSession] | None = None
    catalogue: Catalogue | None = None
    checked: float | None = None
    error: str | None = None
    jobs: dict[str, Job] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.catalogue = last(keyring=self.keyring, state=self.state)
        try:
            self.checked = (self.state / "catalogue.json").stat().st_mtime if self.catalogue else None
        except OSError:
            self.checked = None
        self._lock = asyncio.Lock()

    def _session(self) -> aiohttp.ClientSession:
        return self.session() if self.session else aiohttp.ClientSession()

    async def refresh(self, *, older_than: float = 0) -> None:
        """Read the catalogue again, unless the last read is newer than
        `older_than` seconds. A failure keeps the last good one."""
        async with self._lock:
            if older_than and self.checked and time.time() - self.checked < older_than:
                return
            try:
                async with self._session() as session:
                    data, signature = await download(session, self.url)
                self.catalogue = await asyncio.to_thread(
                    accept, data, signature, keyring=self.keyring, state=self.state)
                self.checked, self.error = time.time(), None
                logger.info("catalogue: serial %s, %d plugins", self.catalogue.serial, len(self.catalogue.plugins))
            except Unavailable as exc:
                self.error = str(exc)
                logger.warning("catalogue: not read: %s", exc)
                return
        await self.enforce()

    def blocked(self) -> dict[str, str]:
        mine = {k: v for k, v in self.installed().items() if k in self.from_catalogue()}
        return blocked(self.catalogue, mine)

    async def enforce(self) -> list[str]:
        """Every blocked plugin from the catalogue, switched off."""
        found = self.blocked()
        for plugin_id, why in found.items():
            logger.warning("catalogue: %s is blocked: %s", plugin_id, why)
            await self.switch_off(plugin_id, why)
        return list(found)

    def view(self) -> dict:
        return {
            "available": self.catalogue is not None,
            "serial": self.catalogue.serial if self.catalogue else None,
            "date": self.catalogue.date if self.catalogue else None,
            "checked": self.checked,
            "error": self.error,
            "plugins": rows(self.catalogue, release=self.release(), installed=self.installed(),
                            from_catalogue=self.from_catalogue(), ours=self.ours),
            "jobs": {k: j.to_json() for k, j in self.jobs.items()},
        }

    def start_install(self, plugin_id: str, version: dict | None = None) -> Job:
        """Begin installing `version`, else the one offered for `plugin_id`,
        or say why not."""
        entry = self.catalogue.entry(plugin_id) if self.catalogue else None
        if entry is None or plugin_id in self.ours:
            raise Unavailable(f"{plugin_id} is not in the catalogue")
        here = self.installed().get(plugin_id)
        if here is not None and plugin_id not in self.from_catalogue():
            raise Unavailable(f"{plugin_id} was uploaded here; remove it first")
        version = version or offer(entry, self.release())
        if version is None:
            raise Unavailable(f"{plugin_id} has no version for this player")
        if version["version"] == here:
            raise Unavailable(f"{plugin_id} {here} is already installed")
        running = self.jobs.get(plugin_id)
        if running and running.phase in ("downloading", "installing"):
            return running
        job = Job(plugin_id, version["version"], total=version["size"])
        self.jobs[plugin_id] = job
        asyncio.ensure_future(self._install(job, version))
        return job

    async def _install(self, job: Job, version: dict) -> None:
        def progress(done: int, total: int) -> None:
            job.done, job.total = done, total
        try:
            async with self._session() as session:
                archive = await fetch_archive(session, version, progress)
            job.phase = "installing"
            await self.install_archive(archive, job.plugin_id)
            job.phase = "installed"
        except (Unavailable, uploads.Refused) as exc:
            job.phase, job.error = "failed", str(exc)
            logger.warning("catalogue: %s %s not installed: %s", job.plugin_id, job.version, exc)
        except Exception as exc:  # noqa: BLE001 - the row says it failed, whatever the cause
            job.phase, job.error = "failed", "it could not be installed"
            logger.exception("catalogue: %s %s not installed: %s", job.plugin_id, job.version, exc)

    def restore(self, missing: list[dict]) -> str | None:
        """After a restore, a plugin from the catalogue is installed from it
        again (ADR-0168): the version it had if still offered to this player,
        else the newest. One a start - each install restarts the core, and
        the next start goes on with the rest."""
        release = self.release()
        for gone in missing:
            entry = self.catalogue.entry(gone["id"]) if self.catalogue else None
            if entry is None or pulled(entry):
                continue
            had = _listed(entry, gone.get("version"))
            suits = had is not None and not pulled(had) and had.get("contract") in CONTRACTS and (
                release_tuple(str(had.get("player", ""))) <= release_tuple(release))
            version = had if suits else offer(entry, release)
            if version is None:
                continue
            try:
                self.start_install(gone["id"], version)
            except Unavailable as exc:
                logger.warning("catalogue: %s not installed again: %s", gone["id"], exc)
                continue
            logger.info("catalogue: %s %s installed again after a restore", gone["id"], version["version"])
            return gone["id"]
        return None

    async def run(self, *, first_delay: float = 60, restore: list[dict] | None = None) -> None:
        """Read it a minute after the start, then once a day; after a
        restore, sooner, and install from it what the restore needs."""
        await asyncio.sleep(20 if restore else first_delay)
        await self.refresh()
        if restore:
            self.restore(restore)
        while True:
            await asyncio.sleep(EVERY_S)
            await self.refresh()
