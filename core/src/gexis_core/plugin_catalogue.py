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

from gexis_core import plugin_permissions, plugins, uploads

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


class NeedsConsent(Exception):
    """ADR-0170: the version asks for permissions its person has not agreed
    to; nothing is downloaded until the page has listed them."""

    def __init__(self, plugin_id: str, permissions: tuple[str, ...], missing: tuple[str, ...]):
        super().__init__(f"{plugin_id} asks for {', '.join(missing)}")
        self.plugin_id, self.permissions, self.missing = plugin_id, permissions, missing


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
        perms = v.get("permissions", [])
        if not isinstance(perms, list) or not all(isinstance(n, str) for n in perms):
            return False
    return True


def version_permissions(v: dict) -> tuple[str, ...] | None:
    """What a version asks for beyond the sandbox (ADR-0170); None when it
    names one this player does not grant - not a version for this player."""
    try:
        return plugin_permissions.parse(v.get("permissions"))
    except plugin_permissions.Unknown:
        return None


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


def signature_url(url: str, serial: int) -> str:
    """A catalogue's signature, named by its serial: GitHub's cache once gave
    a new catalogue.json with the previous signature, which a name per
    serial cannot pair (George, 2026-10-30)."""
    return f"{url.rsplit('/', 1)[0]}/catalogue-{serial}.json.sig"


async def download(session: aiohttp.ClientSession, url: str = URL) -> tuple[bytes, bytes]:
    """The catalogue and the signature of the serial it says it is - read
    from it before it is verified, and verified with that signature."""
    try:
        data = await _get(session, url, MAX_INDEX)
        return data, await _get(session, signature_url(url, parse(data).serial), 64 * 1024)
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
        if pulled(v) or v.get("contract") not in CONTRACTS or version_permissions(v) is None:
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
         from_catalogue: set[str], ours: set[str], granted: dict[str, tuple[str, ...]] | None = None) -> list[dict]:
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
        # ADR-0170: what the version on offer asks for, and of that what its
        # person has not agreed to yet - all of it before a first install.
        asked = version_permissions(offered) if offered else ()
        agreed = set((granted or {}).get(plugin_id, ())) if here is not None else set()
        out.append({
            "id": plugin_id, "name": entry["name"], "summary": entry.get("summary"),
            "kind": entry["kind"], "author": entry.get("author"), "source": entry.get("source"),
            "licence": entry.get("licence"),
            # ADR-0169: its group under *Add plugins*, as its manifest's area.
            "area": entry["area"] if entry.get("area") in plugins.AREAS else plugins.default_area(entry["kind"]),
            "version": offered["version"] if offered else None,
            "size": offered["size"] if offered else None,
            "installed": here, "state": state, "reason": reason,
            "permissions": plugin_permissions.words(asked or ()),
            "asks": [n for n in (asked or ()) if n not in agreed],
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
    #: Install a checked archive as `id`, then restart the core unless told
    #: not to (ADR-0106): (archive, id, restart, the permissions its listing
    #: says it asks for, ADR-0170).
    install_archive: Callable[[bytes, str, bool, tuple[str, ...]], Awaitable[dict]]
    #: Switch a plugin off because it is blocked: (id, why).
    switch_off: Callable[[str, str], Awaitable[None]]
    keyring: Path = KEYRING
    state: Path = STATE
    url: str = URL
    session: Callable[[], aiohttp.ClientSession] | None = None
    #: Restart the core once after installs that did not.
    restart_core: Callable[[], Awaitable[None]] | None = None
    #: ADR-0170: what each plugin's person agreed to (`uploads.granted`).
    granted: Callable[[], dict[str, tuple[str, ...]]] | None = None
    #: A read brought a different catalogue: the screens read the settings
    #: again, for a row's withdrawn mark and an update offered.
    on_change: Callable[[], None] | None = None
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
            if not self.keyed:
                # A release built without the key has no catalogue to trust.
                self.error = "this player has no catalogue key"
                return
            before = self.catalogue.serial if self.catalogue else None
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
        if self.on_change and self.catalogue.serial != before:
            self.on_change()
        await self.enforce()

    @property
    def keyed(self) -> bool:
        return self.keyring.is_file()

    def blocked(self) -> dict[str, str]:
        mine = {k: v for k, v in self.installed().items() if k in self.from_catalogue()}
        return blocked(self.catalogue, mine)

    def summary(self, plugin_id: str) -> str | None:
        """Its entry's one line on what it does, for its row (ADR-0169)."""
        entry = self.catalogue.entry(plugin_id) if self.catalogue else None
        return entry.get("summary") if entry else None

    def pulled(self, plugin_id: str) -> tuple[str, str] | None:
        """Whether the catalogue read last withdrew or blocked this plugin,
        or the version installed here - for its row, read with the settings."""
        return pulled_for(self.catalogue, plugin_id, self.installed().get(plugin_id))

    def switch_unavailable(self, plugin_id: str) -> dict:
        """What the plugin's switch cannot be set to (the registry's
        `restrictions`): on, while it is blocked."""
        why = self.blocked().get(plugin_id)
        return {True: f"Blocked in the plugin catalogue, and switched off: {why.rstrip('.')}"} if why else {}

    async def enforce(self) -> list[str]:
        """Every blocked plugin from the catalogue, switched off."""
        found = self.blocked()
        for plugin_id, why in found.items():
            logger.warning("catalogue: %s is blocked: %s", plugin_id, why)
            await self.switch_off(plugin_id, why)
        return list(found)

    def view(self) -> dict:
        return {
            #: False on a release built without the key: *More plugins* is
            #: not offered there.
            "keyed": self.keyed,
            "available": self.catalogue is not None,
            "serial": self.catalogue.serial if self.catalogue else None,
            "date": self.catalogue.date if self.catalogue else None,
            "checked": self.checked,
            "error": self.error,
            "plugins": rows(self.catalogue, release=self.release(), installed=self.installed(),
                            from_catalogue=self.from_catalogue(), ours=self.ours, granted=self._granted()),
            "jobs": {k: j.to_json() for k, j in self.jobs.items()},
        }

    def _granted(self) -> dict[str, tuple[str, ...]]:
        return self.granted() if self.granted else {}

    def start_install(self, plugin_id: str, version: dict | None = None, grant=()) -> Job:
        """Begin installing `version`, else the one offered for `plugin_id`,
        or say why not. ADR-0170: what it asks for must be agreed to now
        (`grant`) or for the version before; else `NeedsConsent`."""
        job, version, running = self._job(plugin_id, version)
        if not running:
            asked = version_permissions(version) or ()
            agreed = set(grant) | set(self._granted().get(plugin_id, ()))
            missing = tuple(n for n in asked if n not in agreed)
            if missing:
                self.jobs.pop(plugin_id, None)
                raise NeedsConsent(plugin_id, asked, missing)
            asyncio.ensure_future(self._install(job, version))
        return job

    def _job(self, plugin_id: str, version: dict | None) -> tuple[Job, dict, bool]:
        """The job for an install, a new one unless one is under way; or
        `Unavailable` for why there is none."""
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
            return running, version, True
        job = Job(plugin_id, version["version"], total=version["size"])
        self.jobs[plugin_id] = job
        return job, version, False

    async def _install(self, job: Job, version: dict, *, restart: bool = True) -> bool:
        def progress(done: int, total: int) -> None:
            job.done, job.total = done, total
        try:
            async with self._session() as session:
                archive = await fetch_archive(session, version, progress)
            job.phase = "installing"
            await self.install_archive(archive, job.plugin_id, restart, version_permissions(version) or ())
            job.phase = "installed"
            return True
        except (Unavailable, uploads.Refused) as exc:
            job.phase, job.error = "failed", str(exc)
            logger.warning("catalogue: %s %s not installed: %s", job.plugin_id, job.version, exc)
        except Exception as exc:  # noqa: BLE001 - the row says it failed, whatever the cause
            job.phase, job.error = "failed", "it could not be installed"
            logger.exception("catalogue: %s %s not installed: %s", job.plugin_id, job.version, exc)
        return False

    async def restore(self, missing: list[dict]) -> list[str]:
        """After a restore, the plugins from the catalogue are installed from
        it again (ADR-0168): each the version it had if still offered to this
        player, else the newest. All in one go (George, 2026-10-29): each
        downloaded and installed in turn, then the core restarted once."""
        release = self.release()
        todo = []
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
            # ADR-0170: nothing granted that was not agreed to before.
            asked = version_permissions(version) or ()
            agreed = self._granted().get(gone["id"], ())
            if any(n not in agreed for n in asked):
                logger.warning("catalogue: %s not installed again: it asks for more than was agreed", gone["id"])
                continue
            try:
                job, version, running = self._job(gone["id"], version)
            except Unavailable as exc:
                logger.warning("catalogue: %s not installed again: %s", gone["id"], exc)
                continue
            if not running:
                todo.append((job, version))
        done = []
        for job, version in todo:
            if await self._install(job, version, restart=False):
                logger.info("catalogue: %s %s installed again after a restore", job.plugin_id, job.version)
                done.append(job.plugin_id)
        if done and self.restart_core:
            await self.restart_core()
        return done

    async def run(self, *, first_delay: float = 60, restore: list[dict] | None = None) -> None:
        """Read it a minute after the start, then once a day; after a
        restore, sooner, and install from it what the restore needs."""
        await asyncio.sleep(20 if restore else first_delay)
        await self.refresh()
        if restore:
            await self.restore(restore)
        while True:
            await asyncio.sleep(EVERY_S)
            await self.refresh()
