# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0168: the plugin catalogue on the player. Signatures are real (a key
made here, checked with gpgv as on the device); the network is faked."""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import shutil
import subprocess
import tarfile

import aiohttp
import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core import plugin_catalogue as pc
from gexis_core import plugins, settings_registry, uploads
from gexis_core.settings import SettingsStore
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

pytestmark = pytest.mark.skipif(not (shutil.which("gpg") and shutil.which("gpgv")), reason="needs gpg and gpgv")

URL = "https://example.test/catalogue.json"


@pytest.fixture(scope="session")
def key(tmp_path_factory):
    home = tmp_path_factory.mktemp("gnupg")
    home.chmod(0o700)
    run = lambda *a: subprocess.run(["gpg", "--homedir", str(home), "--batch", *a],  # noqa: E731
                                    check=True, capture_output=True)
    run("--passphrase", "", "--quick-gen-key", "Catalogue test key", "ed25519", "sign", "never")
    public = run("--export").stdout
    keyring = home / "catalogue.gpg"
    keyring.write_bytes(public)

    def sign(data: bytes) -> bytes:
        return subprocess.run(["gpg", "--homedir", str(home), "--batch", "--detach-sign", "--output", "-"],
                              input=data, check=True, capture_output=True).stdout
    return keyring, sign


def archive(plugin_id="hello", version="0.1.0", **extra) -> bytes:
    manifest = {"id": plugin_id, "name": "Hello", "kind": "service", "version": version, "run": "hello.py", **extra}
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in (("plugin.json", json.dumps(manifest).encode()), ("hello.py", b"#!/bin/sh\necho hi\n")):
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o755
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def listed(data: bytes, version="0.1.0", player="1.9.0", **extra) -> dict:
    return {"version": version, "url": f"https://github.com/someone/hello/releases/download/v{version}/h.tar.gz",
            "sha256": hashlib.sha256(data).hexdigest(), "size": len(data), "contract": 1, "player": player, **extra}


def entry(*versions, plugin_id="hello", **extra) -> dict:
    return {"id": plugin_id, "name": "Hello", "summary": "Says hello.", "kind": "service", "author": "someone",
            "source": "https://github.com/someone/hello", "licence": "MIT", "versions": list(versions), **extra}


def index(*entries, serial=1) -> bytes:
    return json.dumps({"format": 1, "serial": serial, "date": "2026-10-29T00:00:00Z",
                       "plugins": list(entries)}).encode()


def published(cat: bytes, sign) -> dict[str, bytes]:
    """As the release serves it: the catalogue, and its signature named by its serial."""
    return {URL: cat, pc.signature_url(URL, json.loads(cat)["serial"]): sign(cat)}


class Response:
    """A body as aiohttp hands it out: a read gives what has arrived, a piece
    at a time, never more of a longer body (the review of 1.16.1)."""
    PIECE = 1000

    def __init__(self, status: int, body: bytes):
        self.status, self._body, self.content, self._at = status, body, self, 0

    async def read(self, n: int = -1) -> bytes:
        end = len(self._body) if n < 0 else self._at + min(n, self.PIECE)
        piece = self._body[self._at:end]
        self._at += len(piece)
        return piece

    async def iter_chunked(self, size: int):
        while piece := await self.read(size):
            yield piece

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class Session:
    def __init__(self, served: dict[str, bytes]):
        self.served = served

    def get(self, url, **kw):
        return Response(200, self.served[url]) if url in self.served else Response(404, b"")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


# Reading the catalogue

def test_a_signed_catalogue_is_accepted_and_kept(key, tmp_path):
    keyring, sign = key
    data = index(entry(listed(archive())), serial=3)
    cat = pc.accept(data, sign(data), keyring=keyring, state=tmp_path)
    assert cat.serial == 3 and cat.entry("hello")
    assert pc.last(keyring=keyring, state=tmp_path).serial == 3


def test_a_catalogue_not_signed_by_the_catalogue_key_is_refused_and_nothing_kept(key, tmp_path):
    keyring, sign = key
    data = index(entry(listed(archive())))
    with pytest.raises(pc.Unavailable, match="signature"):
        pc.accept(data + b" ", sign(data), keyring=keyring, state=tmp_path)
    assert pc.last(keyring=keyring, state=tmp_path) is None


def test_an_older_serial_is_refused_and_the_same_one_is_not(key, tmp_path):
    keyring, sign = key
    newer, older = index(serial=5), index(serial=4)
    pc.accept(newer, sign(newer), keyring=keyring, state=tmp_path)
    with pytest.raises(pc.Unavailable, match="older"):
        pc.accept(older, sign(older), keyring=keyring, state=tmp_path)
    assert pc.accept(newer, sign(newer), keyring=keyring, state=tmp_path).serial == 5


def test_without_the_key_there_is_no_catalogue(key, tmp_path):
    _, sign = key
    data = index()
    with pytest.raises(pc.Unavailable, match="no catalogue key"):
        pc.accept(data, sign(data), keyring=tmp_path / "missing.gpg", state=tmp_path)


def test_one_unusable_entry_does_not_hide_the_others():
    bad = {**entry(listed(archive())), "id": "Bad Id"}
    cat = pc.parse(index(bad, entry(listed(archive()))))
    assert [e["id"] for e in cat.plugins] == ["hello"]
    with pytest.raises(pc.Unavailable):
        pc.parse(json.dumps({"format": 2, "serial": 1}).encode())


# What is offered

def test_the_newest_version_this_player_may_install_is_offered():
    a, b, c = archive(), archive(version="0.2.0"), archive(version="0.3.0")
    e = entry(listed(a), listed(b, "0.2.0", withdrawn="breaks"), listed(c, "0.3.0", player="2.0.0"))
    assert pc.offer(e, "1.9.1")["version"] == "0.1.0"
    assert pc.offer(e, "2.0.0")["version"] == "0.3.0"
    assert pc.offer({**e, "withdrawn": "gone"}, "2.0.0") is None
    assert pc.offer(entry({**listed(a), "contract": 2}), "1.9.1") is None
    assert pc.release_tuple("1.9.0+git9.484bd6d") == (1, 9, 0)


def test_each_plugins_state_on_more_plugins():
    a, b = archive(), archive(version="0.2.0")
    cat = pc.parse(index(
        entry(listed(a), listed(b, "0.2.0")),
        entry(listed(a), plugin_id="kept"),
        entry(listed(a), plugin_id="old", withdrawn="no longer kept up"),
        entry(listed(a, blocked="sends what it hears"), plugin_id="bad"),
        entry(listed(a), plugin_id="hidden", withdrawn="gone"),
        entry(listed(a), plugin_id="mine"),
        entry(listed(a), plugin_id="spotify"),
    ))
    installed = {"hello": "0.1.0", "kept": "0.1.0", "old": "0.1.0", "bad": "0.1.0", "mine": "0.1.0"}
    found = {r["id"]: (r["state"], r["reason"]) for r in pc.rows(
        cat, release="1.9.1", installed=installed,
        from_catalogue={"hello", "kept", "old", "bad"}, ours={"spotify"})}
    assert found == {
        "hello": ("update", None), "kept": ("installed", None),
        "old": ("withdrawn", "no longer kept up"), "bad": ("blocked", "sends what it hears"),
        "mine": ("uploaded", None),
    }


def test_blocked_by_the_plugin_or_by_the_version_installed():
    a = archive()
    cat = pc.parse(index(entry(listed(a, blocked="harm")), entry(listed(a), plugin_id="all", blocked="harm too"),
                         entry(listed(a), plugin_id="fine")))
    assert pc.blocked(cat, {"hello": "0.1.0", "all": "0.1.0", "fine": "0.1.0"}) == {
        "hello": "harm", "all": "harm too"}
    assert pc.pulled_for(cat, "fine", "0.1.0") is None


# Installing

async def test_only_the_listed_archive_is_taken():
    data = archive()
    v = listed(data)
    assert await pc.fetch_archive(Session({v["url"]: data}), v) == data
    for served in (data + b"x", data[:-1], archive(version="0.9.9")):
        with pytest.raises(pc.Unavailable):
            await pc.fetch_archive(Session({v["url"]: served}), {**v, "size": max(len(served), v["size"])})


def service(key, tmp_path, served, *, installed=None, from_catalogue=None, granted=None):
    keyring, sign = key
    calls = {"installed": [], "off": [], "restarted": 0, "restart_with": [], "permissions": []}

    async def install_archive(archive_bytes, plugin_id, restart, permissions):
        calls["installed"].append((plugin_id, hashlib.sha256(archive_bytes).hexdigest()))
        calls["restart_with"].append(restart)
        calls["permissions"].append(permissions)
        return {"installed": plugin_id}

    async def switch_off(plugin_id, why):
        calls["off"].append((plugin_id, why))

    async def restart_core():
        calls["restarted"] += 1

    svc = pc.Service(release=lambda: "1.9.1", installed=lambda: dict(installed or {}),
                     from_catalogue=lambda: set(from_catalogue or ()), ours={"spotify"},
                     install_archive=install_archive, switch_off=switch_off, restart_core=restart_core,
                     granted=lambda: dict(granted or {}),
                     keyring=keyring, state=tmp_path, url=URL, session=lambda: Session(served))
    return svc, calls


async def test_install_downloads_checks_and_hands_the_archive_on(key, tmp_path):
    keyring, sign = key
    data = archive()
    cat = index(entry(listed(data)))
    svc, calls = service(key, tmp_path, {**published(cat, sign), listed(data)["url"]: data})
    await svc.refresh()
    job = svc.start_install("hello")
    for _ in range(50):
        if job.phase in ("installed", "failed"):
            break
        await asyncio.sleep(0.01)
    assert job.phase == "installed" and calls["installed"] == [("hello", hashlib.sha256(data).hexdigest())]
    # The core restarted once it is in (ADR-0106).
    assert calls["restart_with"] == [False] and calls["restarted"] == 1


class Held(Session):
    """One download held until `release` is set."""

    def __init__(self, served: dict[str, bytes], url: str, release: asyncio.Event):
        super().__init__(served)
        self.url, self.release = url, release

    def get(self, url, **kw):
        response = super().get(url, **kw)
        if url == self.url:
            pieces = response.iter_chunked

            async def held(size):
                await self.release.wait()
                async for piece in pieces(size):
                    yield piece
            response.iter_chunked = held
        return response


async def _until(check) -> None:
    for _ in range(200):
        if check():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("not reached")


def _two(sign, *, hub_served: bytes | None = None):
    found = {pid: archive(plugin_id=pid) for pid in ("agent", "hub")}
    versions = {pid: listed(data, url=f"https://github.com/someone/b/releases/download/v1/{pid}.tar.gz")
                for pid, data in found.items()}
    cat = index(*(entry(v, plugin_id=pid) for pid, v in versions.items()))
    served = {**published(cat, sign), versions["agent"]["url"]: found["agent"],
              versions["hub"]["url"]: found["hub"] if hub_served is None else hub_served}
    return served, versions["hub"]["url"]


@pytest.mark.parametrize("hub_fails", [False, True])
async def test_installs_that_overlap_restart_the_core_once_none_is_under_way(key, tmp_path, hub_fails):
    """The review of 1.16.1: Beszel's hub, then its agent, added one after the
    other - the agent, in first, restarted the core under the hub's
    download, which was lost. The core restarts once, when the last ends,
    whether it went in or not."""
    keyring, sign = key
    served, held_url = _two(sign, hub_served=b"not the listed archive" if hub_fails else None)
    release = asyncio.Event()
    svc, calls = service(key, tmp_path, served)
    svc.session = lambda: Held(served, held_url, release)
    await svc.refresh()
    hub, agent = svc.start_install("hub"), svc.start_install("agent")
    await _until(lambda: agent.phase == "installed")
    await asyncio.sleep(0.05)
    assert hub.phase == "downloading" and calls["restarted"] == 0 and calls["restart_with"] == [False]
    release.set()
    await _until(lambda: hub.phase in ("installed", "failed"))
    await asyncio.sleep(0.05)
    assert hub.phase == ("failed" if hub_fails else "installed")
    assert calls["restarted"] == 1


async def test_a_restart_owed_elsewhere_waits_for_an_install_under_way(key, tmp_path):
    """The review of 1.16.1: a plugin blocked by a read of the catalogue
    restarted the core at once, under another plugin's download, which was
    lost. Owed with an install under way, the restart comes when it ends;
    with none, at once."""
    keyring, sign = key
    served, held_url = _two(sign)
    release = asyncio.Event()
    svc, calls = service(key, tmp_path, served)
    svc.session = lambda: Held(served, held_url, release)
    await svc.refresh()
    hub = svc.start_install("hub")
    await svc.restart_once_idle()
    assert hub.phase == "downloading" and calls["restarted"] == 0
    release.set()
    await _until(lambda: hub.phase == "installed")
    await asyncio.sleep(0.05)
    assert calls["restarted"] == 1
    await svc.restart_once_idle()
    assert calls["restarted"] == 2, "nothing under way: at once"


def test_a_blocked_plugin_restarts_the_core_once_no_install_is_under_way():
    from test_main_wiring import _closure
    body = _closure("_switch_off_blocked")
    assert "catalogue.restart_once_idle()" in body and "_restart_core_soon()" not in body


async def test_a_restore_during_an_install_leaves_the_restart_to_the_last(key, tmp_path):
    keyring, sign = key
    served, held_url = _two(sign)
    release = asyncio.Event()
    svc, calls = service(key, tmp_path, served)
    svc.session = lambda: Held(served, held_url, release)
    await svc.refresh()
    hub = svc.start_install("hub")
    assert await svc.restore([{"id": "agent", "version": "0.1.0"}]) == ["agent"]
    assert hub.phase == "downloading" and calls["restarted"] == 0
    release.set()
    await _until(lambda: hub.phase == "installed")
    await asyncio.sleep(0.05)
    assert calls["restarted"] == 1


async def test_an_archive_that_is_not_the_listed_one_fails_and_installs_nothing(key, tmp_path):
    keyring, sign = key
    data = archive()
    cat = index(entry(listed(data)))
    svc, calls = service(key, tmp_path, {**published(cat, sign), listed(data)["url"]: data[:-3] + b"abc"})
    await svc.refresh()
    job = svc.start_install("hello")
    for _ in range(50):
        if job.phase in ("installed", "failed"):
            break
        await asyncio.sleep(0.01)
    assert job.phase == "failed" and "not the listed archive" in job.error and calls["installed"] == []


async def test_what_cannot_be_installed_says_why(key, tmp_path):
    keyring, sign = key
    data = archive()
    cat = index(entry(listed(data)), entry(listed(data), plugin_id="spotify"))
    served = published(cat, sign)
    svc, _ = service(key, tmp_path, served, installed={"hello": "0.1.0"}, from_catalogue={"hello"})
    await svc.refresh()
    for plugin_id, why in (("hello", "already installed"), ("spotify", "not in the catalogue"),
                           ("nothing", "not in the catalogue")):
        with pytest.raises(pc.Unavailable, match=why):
            svc.start_install(plugin_id)
    uploaded, _ = service(key, tmp_path, served, installed={"hello": "0.0.9"})
    await uploaded.refresh()
    with pytest.raises(pc.Unavailable, match="uploaded here"):
        uploaded.start_install("hello")


async def test_a_read_that_blocks_a_plugin_switches_it_off(key, tmp_path):
    keyring, sign = key
    cat = index(entry(listed(archive(), blocked="it sends what it hears")))
    svc, calls = service(key, tmp_path, published(cat, sign),
                         installed={"hello": "0.1.0"}, from_catalogue={"hello"})
    await svc.refresh()
    assert calls["off"] == [("hello", "it sends what it hears")]


async def test_a_failed_read_keeps_the_last_good_catalogue(key, tmp_path):
    keyring, sign = key
    cat = index(entry(listed(archive())), serial=2)
    pc.accept(cat, sign(cat), keyring=keyring, state=tmp_path)
    svc, _ = service(key, tmp_path, {})
    await svc.refresh()
    view = svc.view()
    assert view["available"] and view["serial"] == 2 and "404" in view["error"]


async def test_a_catalogue_that_arrives_in_pieces_is_read_whole(key, tmp_path):
    """The review of 1.16.1: one read took what had arrived - on a real
    network one TLS record, about 16 KB - and a longer catalogue was refused
    as not readable, every read after it."""
    keyring, sign = key
    data = archive()
    cat = index(*(entry(listed(data), plugin_id=f"plugin-{n}") for n in range(60)))
    assert len(cat) > 16 * 1024
    svc, _ = service(key, tmp_path, published(cat, sign))
    await svc.refresh()
    assert svc.error is None and len(svc.catalogue.plugins) == 60


async def test_a_catalogue_larger_than_one_can_be_is_refused():
    with pytest.raises(pc.Unavailable, match="larger than a catalogue"):
        await pc._get(Session({URL: b" " * 5001}), URL, 5000)
    assert len(await pc._get(Session({URL: b" " * 5000}), URL, 5000)) == 5000


async def test_a_body_sent_in_two_parts_is_read_to_its_end():
    """aiohttp itself, over a local socket: the server sends part of the
    body, waits, then the rest."""
    from aiohttp import web
    body = b"[" + b" " * 40000 + b"]"

    async def handler(request):
        response = web.StreamResponse(headers={"Content-Length": str(len(body))})
        await response.prepare(request)
        await response.write(body[:16384])
        await asyncio.sleep(0.2)
        await response.write(body[16384:])
        await response.write_eof()
        return response

    app = web.Application()
    app.router.add_get("/catalogue.json", handler)
    async with TestClient(TestServer(app)) as client:
        got = await pc._get(client.session, str(client.make_url("/catalogue.json")), pc.MAX_INDEX)
    assert got == body


async def test_a_release_without_the_key_reads_nothing_and_says_so(key, tmp_path):
    keyring, sign = key
    cat = index(entry(listed(archive())))
    served = published(cat, sign)
    svc, _ = service(key, tmp_path, served)
    svc.keyring = tmp_path / "none.gpg"
    asked = []
    svc.session = lambda: (asked.append(1), Session(served))[1]
    await svc.refresh()
    view = svc.view()
    assert asked == [] and view["keyed"] is False and not view["available"]


async def test_a_blocked_plugins_switch_refuses_on_with_the_reason(key, tmp_path):
    keyring, sign = key
    cat = index(entry(listed(archive(), blocked="It sends what it hears.")))
    svc, _ = service(key, tmp_path, published(cat, sign),
                     installed={"hello": "0.1.0"}, from_catalogue={"hello"})
    assert svc.switch_unavailable("hello") == {}
    await svc.refresh()
    assert svc.switch_unavailable("hello") == {
        True: "Blocked in the plugin catalogue, and switched off: It sends what it hears"}
    base = plugins.parse({"id": "hello", "name": "Hello", "kind": "service",
                          "unit": "gexis-uploaded-service@hello.service"})
    from dataclasses import replace
    registry = settings_registry.Settings.with_plugins(
        settings_registry.load_registry(), [replace(base, uploaded=True, catalogue=True)])
    settings = settings_registry.Settings(
        SettingsStore(tmp_path / "s.db"), registry=registry, wired={"hello.enabled": None},
        restrictions={"hello.enabled": lambda: svc.switch_unavailable("hello")})
    with pytest.raises(settings_registry.Locked, match="It sends what it hears"):
        settings.set("hello.enabled", True)
    assert settings.set("hello.enabled", False) is False


async def test_a_restore_installs_the_version_it_had_while_it_is_offered(key, tmp_path):
    keyring, sign = key
    a, b = archive(), archive(version="0.2.0")
    cat = index(entry(listed(a), listed(b, "0.2.0")))
    served = {**published(cat, sign), listed(a)["url"]: a, listed(b, "0.2.0")["url"]: b}
    svc, _ = service(key, tmp_path, served)
    await svc.refresh()
    assert await svc.restore([{"id": "hello", "version": "0.1.0"}]) == ["hello"]
    assert svc.jobs["hello"].version == "0.1.0"
    withdrawn = index(entry(listed(a, withdrawn="broken"), listed(b, "0.2.0")), serial=2)
    served.update(published(withdrawn, sign))
    other, _ = service(key, tmp_path, served)
    await other.refresh()
    await other.restore([{"id": "hello", "version": "0.1.0"}])
    assert other.jobs["hello"].version == "0.2.0"


async def test_a_restore_installs_them_all_then_restarts_once(key, tmp_path):
    keyring, sign = key
    found = {pid: archive(plugin_id=pid) for pid in ("hello", "tone", "gone")}
    versions = {pid: listed(data, url=f"https://github.com/someone/hello/releases/download/v1/{pid}.tar.gz")
                for pid, data in found.items()}
    cat = index(*(entry(v, plugin_id=pid) for pid, v in versions.items()))
    served = {**published(cat, sign), versions["hello"]["url"]: found["hello"],
              versions["tone"]["url"]: found["tone"]}
    svc, calls = service(key, tmp_path, served)
    await svc.refresh()
    missing = [{"id": pid, "version": "0.1.0"} for pid in ("hello", "gone", "tone")]
    # "gone" cannot be downloaded: the others are installed all the same.
    assert await svc.restore(missing) == ["hello", "tone"]
    assert [pid for pid, _ in calls["installed"]] == ["hello", "tone"]
    assert calls["restart_with"] == [False, False] and calls["restarted"] == 1
    assert svc.jobs["gone"].phase == "failed"
    # Nothing installed, nothing restarted.
    again, calls = service(key, tmp_path, published(cat, sign))
    await again.refresh()
    assert await again.restore(missing) == [] and calls["restarted"] == 0


class Offline(Session):
    """No network until `net["up"]`."""

    def __init__(self, served: dict[str, bytes], net: dict):
        super().__init__(served)
        self.net = net

    def get(self, url, **kw):
        if not self.net["up"]:
            raise aiohttp.ClientConnectionError("no route to host")
        return super().get(url, **kw)


REAL_SLEEP = asyncio.sleep


async def _run(svc, restore, monkeypatch, *, until, on_wait=lambda seconds: None) -> list[float]:
    """`Service.run` with each wait recorded and skipped, until `until(waits)`."""
    waits = []

    async def skip(seconds):
        waits.append(seconds)
        on_wait(seconds)
        await REAL_SLEEP(0)
    monkeypatch.setattr(pc.asyncio, "sleep", skip)
    task = asyncio.ensure_future(svc.run(restore=restore))
    for _ in range(300):
        if until(waits):
            break
        await REAL_SLEEP(0.01)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    return waits


OWED = [{"id": "hello", "version": None, "origin": "catalogue"}]


async def test_what_is_owed_is_installed_once_the_network_is_there(key, tmp_path, monkeypatch):
    """The review of 1.16.1: a plugin a restore or the carry-over owes was
    tried once per start; with no network 20 s after it, not again until the
    next start, while its row said it would be installed once the player
    reaches the catalogue. A new card keeps no catalogue."""
    keyring, sign = key
    data = archive()
    served = {**published(index(entry(listed(data))), sign), listed(data)["url"]: data}
    net = {"up": False}
    svc, calls = service(key, tmp_path, served)
    svc.session = lambda: Offline(served, net)
    waits = await _run(svc, OWED, monkeypatch, until=lambda waits: calls["installed"] and calls["restarted"],
                       on_wait=lambda seconds: seconds != 20 and net.update(up=True))
    assert [pid for pid, _ in calls["installed"]] == ["hello"] and calls["restarted"] == 1
    assert waits[:2] == [20, pc.RETRY_S]


async def test_a_download_that_failed_is_tried_again(key, tmp_path, monkeypatch):
    keyring, sign = key
    data = archive()
    cat = index(entry(listed(data)))
    pc.accept(cat, sign(cat), keyring=keyring, state=tmp_path)
    served = {**published(cat, sign), listed(data)["url"]: data}
    net = {"up": False}
    svc, calls = service(key, tmp_path, served)
    svc.session = lambda: Offline(served, net)
    await _run(svc, OWED, monkeypatch, until=lambda waits: calls["installed"],
               on_wait=lambda seconds: seconds != 20 and net.update(up=True))
    assert [pid for pid, _ in calls["installed"]] == ["hello"] and svc.jobs["hello"].phase == "installed"


async def test_owed_is_tried_sooner_then_less_often_and_daily_once_in(key, tmp_path, monkeypatch):
    keyring, sign = key
    monkeypatch.setattr(pc, "EVERY_S", 300)
    cat = index(entry(listed(archive())))
    svc, calls = service(key, tmp_path, published(cat, sign))   # its archive cannot be had
    waits = await _run(svc, OWED, monkeypatch, until=lambda waits: len(waits) >= 6)
    assert waits[:6] == [20, pc.RETRY_S, 2 * pc.RETRY_S, 4 * pc.RETRY_S, 300, 300]
    assert calls["installed"] == []
    nothing, _ = service(key, tmp_path, published(cat, sign))
    waits = await _run(nothing, [], monkeypatch, until=lambda waits: len(waits) >= 3)
    assert waits[:3] == [60, 300, 300], "nothing owed: the daily read"


async def test_a_withdrawal_read_during_a_run_reaches_the_row(key, tmp_path):
    """Found on sofapi, 2026-10-30: the row's mark was fixed at the start."""
    keyring, sign = key
    a = archive()
    cat = index(entry(listed(a)))
    served = published(cat, sign)
    svc, _ = service(key, tmp_path, served, installed={"hello": "0.1.0"}, from_catalogue={"hello"})
    told = []
    svc.on_change = lambda: told.append(svc.catalogue.serial)
    await svc.refresh()
    await svc.refresh()
    assert told == [1] and svc.pulled("hello") is None
    withdrawn = index(entry(listed(a), withdrawn="no longer kept up"), serial=2)
    served.update(published(withdrawn, sign))
    await svc.refresh()
    assert told == [1, 2]
    assert settings_registry.catalogue_note(svc.pulled("hello")) == \
        "Withdrawn from the plugin catalogue: no longer kept up"


async def test_a_cached_catalogue_reads_its_own_signature(key, tmp_path):
    """Found on sofapi, 2026-10-30: GitHub's cache paired serial 3 with serial
    2's signature, and the read was refused. Each serial's has its own name."""
    keyring, sign = key
    old, new = index(entry(listed(archive())), serial=2), index(serial=3)
    # Both signatures on the release; the cache still serves the old catalogue.
    served = {**published(new, sign), **published(old, sign)}
    svc, _ = service(key, tmp_path, served)
    await svc.refresh()
    assert svc.error is None and svc.catalogue.serial == 2
    served[URL] = new
    await svc.refresh()
    assert svc.error is None and svc.catalogue.serial == 3
    # A catalogue whose own signature is not there: refused, the last good kept.
    served[URL] = index(serial=4)
    await svc.refresh()
    assert svc.catalogue.serial == 3 and svc.error == "GitHub answered 404"


# Where it came from

def test_an_uploads_origin_survives_the_record_and_goes_with_remove(tmp_path):
    root, known = tmp_path / "plugins", tmp_path / "known.json"
    uploads.install(archive(), ours=set(), root=root)
    uploads.remember(root=root, path=known)
    uploads.set_origin("hello", uploads.CATALOGUE, path=known)
    uploads.remember(root=root, path=known)
    assert uploads.origins(path=known) == {"hello": "catalogue"}
    assert uploads.versions(root=root) == {"hello": "0.1.0"}
    assert uploads.installed(root=root, known=known)[0].catalogue is True
    uploads.set_origin("hello", None, path=known)
    assert uploads.installed(root=root, known=known)[0].catalogue is False
    uploads.forget("hello", path=known)
    assert uploads.origins(path=known) == {}


def _rows(plugins_=(), missing=()):
    groups = settings_registry.Settings.with_plugins(settings_registry.load_registry(), list(plugins_),
                                                     missing=list(missing))
    return {r.get("key"): r for g in groups for r in g.get("rows", []) if r.get("key")}


def _switch(plugin):
    return _rows([plugin])[f"{plugin.id}.enabled"]


def test_a_catalogue_plugins_row_says_where_it_came_from_and_why_it_is_off():
    base = plugins.parse({"id": "hello", "name": "Hello", "kind": "service",
                          "unit": "gexis-uploaded-service@hello.service"})
    from dataclasses import replace
    row = _switch(replace(base, uploaded=True, catalogue=True))
    assert row["catalogue"] and row["note"] == "A service from the plugin catalogue."
    row = _switch(replace(base, uploaded=True, catalogue=True, summary="Says hello."))
    assert row["note"] == "Says hello."
    row = _switch(replace(base, uploaded=True))
    assert row["note"] == "A service, installed from a file."
    row = _switch(replace(base, uploaded=True, catalogue=True, pulled=("blocked", "it sends what it hears")))
    assert row["blocked"] and "it sends what it hears" in row["note"]
    row = _switch(replace(base, uploaded=True, catalogue=True, pulled=("withdrawn", "no longer kept up")))
    assert "Withdrawn" in row["note"] and not row.get("blocked")


def test_a_catalogue_plugin_with_a_page_says_where_it_is(monkeypatch):
    """ADR-0174: the Beszel hub from the catalogue still says where its page
    is, as it did shipped with the player - unless the catalogue pulled it."""
    from dataclasses import replace
    from gexis_core import device_name
    monkeypatch.setattr(device_name, "hostname", lambda: "living")
    hub = replace(plugins.parse({"id": "beszel-hub", "name": "Beszel hub", "kind": "service", "port": 8095,
                                 "unit": "gexis-uploaded-service@beszel-hub.service"}),
                  uploaded=True, catalogue=True, summary="A hub.")
    assert _switch(hub)["note"] == "Open http://living.local:8095"
    assert "Withdrawn" in _switch(replace(hub, pulled=("withdrawn", "gone")))["note"]


# The routes

async def test_the_routes_show_the_catalogue_and_start_an_install(key, tmp_path):
    keyring, sign = key
    data = archive()
    cat = index(entry(listed(data)))
    svc, _ = service(key, tmp_path, {**published(cat, sign), listed(data)["url"]: data})
    server = StateServer(StateStore({}), catalogue=svc)
    async with TestClient(TestServer(server.make_app())) as client:
        view = await (await client.get("/plugins/catalogue?refresh=1")).json()
        assert view["serial"] == 1 and view["plugins"][0]["state"] == "available"
        started = await client.post("/plugins/catalogue/install", json={"id": "hello"})
        assert started.status == 200 and (await started.json())["started"] == "hello"
        refused = await client.post("/plugins/catalogue/install", json={"id": "nothing"})
        assert refused.status == 409 and "not in the catalogue" in (await refused.json())["error"]
        assert (await client.post("/plugins/catalogue/install", json={})).status == 400


def test_a_plugin_restored_from_the_catalogue_says_it_is_installed_again():
    row = _rows(missing=[{"id": "hello", "name": "Hello", "kind": "service", "version": "0.1.0",
                          "origin": "catalogue"}])["hello.missing"]
    assert row["default"] == "Installing again" and "plugin catalogue" in row["note"]
    row = _rows(missing=[{"id": "hello", "name": "Hello", "kind": "service", "version": "0.1.0"}])["hello.missing"]
    assert row["default"] == "Upload again"



# Plugins that ask for more (ADR-0170)

async def test_a_version_that_asks_for_more_waits_for_its_person(key, tmp_path):
    keyring, sign = key
    data = archive(plugin_id="tv")
    v = listed(data, permissions=["cec"])
    cat = index(entry(v, plugin_id="tv"))
    svc, calls = service(key, tmp_path, {**published(cat, sign), v["url"]: data})
    await svc.refresh()
    row = svc.view()["plugins"][0]
    assert row["permissions"][0]["name"] == "cec" and row["asks"] == ["cec"]
    with pytest.raises(pc.NeedsConsent) as asked:
        svc.start_install("tv")
    assert asked.value.missing == ("cec",) and "tv" not in svc.jobs
    job = svc.start_install("tv", grant=("cec",))
    for _ in range(50):
        if job.phase in ("installed", "failed"):
            break
        await asyncio.sleep(0.01)
    assert job.phase == "installed" and calls["permissions"] == [("cec",)]


async def test_an_update_asks_again_only_for_what_is_new(key, tmp_path):
    keyring, sign = key
    a, b = archive(plugin_id="tv"), archive(plugin_id="tv", version="0.2.0")
    cat = index(entry(listed(a, permissions=["cec"]), listed(b, "0.2.0", permissions=["cec", "usb"]), plugin_id="tv"))
    svc, _ = service(key, tmp_path, published(cat, sign), installed={"tv": "0.1.0"},
                     from_catalogue={"tv"}, granted={"tv": ("cec",)})
    await svc.refresh()
    row = svc.view()["plugins"][0]
    assert row["state"] == "update" and row["asks"] == ["usb"]
    with pytest.raises(pc.NeedsConsent) as asked:
        svc.start_install("tv")
    assert asked.value.missing == ("usb",)


async def test_a_version_asking_for_what_this_player_does_not_grant_is_not_offered(key, tmp_path):
    keyring, sign = key
    a, b = archive(), archive(version="0.2.0")
    cat = index(entry(listed(a), listed(b, "0.2.0", permissions=["root"])))
    svc, _ = service(key, tmp_path, published(cat, sign))
    await svc.refresh()
    assert svc.view()["plugins"][0]["version"] == "0.1.0"


async def test_a_restore_grants_nothing_new(key, tmp_path):
    keyring, sign = key
    data = archive(plugin_id="tv")
    v = listed(data, permissions=["cec"])
    cat = index(entry(v, plugin_id="tv"))
    served = {**published(cat, sign), v["url"]: data}
    svc, calls = service(key, tmp_path, served)
    await svc.refresh()
    assert await svc.restore([{"id": "tv", "version": "0.1.0"}]) == []
    agreed, calls = service(key, tmp_path, served, granted={"tv": ("cec",)})
    await agreed.refresh()
    assert await agreed.restore([{"id": "tv", "version": "0.1.0"}]) == ["tv"]
    assert calls["permissions"] == [("cec",)]


def test_a_row_s_group_is_its_area_else_its_kind_s():
    e = entry(listed(archive()))
    rows = pc.rows(pc.Catalogue(serial=1, date="", plugins=(e, {**e, "id": "lib", "area": "library"})),
                   release="1.10.0", installed={}, from_catalogue=set(), ours=set())
    assert {r["id"]: r["area"] for r in rows} == {"hello": "system", "lib": "library"}


def test_a_catalogue_plugin_that_downloads_its_software_shows_it_on_its_switch():
    """ADR-0174: Plexamp from the catalogue downloads Plexamp itself; its
    switch shows that download, with Retry, as ours do - but not Remove the
    software, which goes with the plugin."""
    from dataclasses import replace
    from gexis_core import plugin_server
    raw = {"id": "plexamp", "name": "Plexamp", "kind": "renderer", "software": "Plexamp",
           "unit": "gexis-uploaded-renderer@plexamp.service"}
    plugin = replace(plugins.parse(raw), uploaded=True, catalogue=True)
    assert plugin.downloads == "Plexamp"
    assert plugins.parse({**raw, "software": "x" * 41}).downloads is None
    rows = settings_registry.Settings.with_plugins(settings_registry.load_registry(), [plugin],
                                                   downloads={"plexamp": "plexamp"})
    keys = {r.get("key"): r for g in rows for r in g.get("rows", []) if r.get("key")}
    assert keys["plexamp.enabled"]["component"] == "plexamp"
    assert "plexamp.download" in keys and "plexamp.remove" not in keys
    assert "software" in plugin_server.EVENTS


async def test_what_part_two_may_install_without_a_question(key, tmp_path):
    """ADR-0174 decision 3: offered to this player, and asking for nothing
    beyond the sandbox - part 2 has no page to agree on."""
    keyring, sign = key
    data = archive()
    cat = index(entry(listed(data)), entry(listed(data, permissions=["cec"]), plugin_id="tv"),
                entry(listed(data, player="9.0.0"), plugin_id="later"), entry(listed(data), plugin_id="spotify"))
    svc, _ = service(key, tmp_path, published(cat, sign))
    assert svc.offered("hello") is None, "nothing read yet"
    await svc.refresh()
    assert svc.offered("hello")["id"] == "hello"
    assert [svc.offered(i) for i in ("tv", "later", "spotify", "absent")] == [None] * 4


async def test_the_installs_under_way_are_named(key, tmp_path):
    keyring, sign = key
    served, held_url = _two(sign)
    release = asyncio.Event()
    svc, calls = service(key, tmp_path, served)
    svc.session = lambda: Held(served, held_url, release)
    await svc.refresh()
    assert svc.under_way() == []
    svc.start_install("hub")
    assert svc.under_way() == [svc.catalogue.entry("hub")["name"]]
    release.set()
    await _until(lambda: not svc.under_way())
