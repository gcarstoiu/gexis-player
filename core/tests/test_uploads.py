"""ADR-0106: a plugin a user uploads is checked before anything is written,
installed where nothing of ours lives, and run under a unit the player writes."""
from __future__ import annotations

import io
import json
import tarfile

import pytest

from gexis_core import uploads

ELF_AARCH64 = b"\x7fELF\x02\x01\x01" + b"\x00" * 11 + (0xB7).to_bytes(2, "little") + b"\x00" * 40
ELF_X86 = b"\x7fELF\x02\x01\x01" + b"\x00" * 11 + (0x3E).to_bytes(2, "little") + b"\x00" * 40


def package(manifest=None, files=None, extra=None) -> bytes:
    manifest = manifest if manifest is not None else {
        "id": "radiofoo", "name": "Radio Foo", "kind": "renderer",
        "version": "1.0.0", "run": "bin/radiofoo",
    }
    files = files if files is not None else {"bin/radiofoo": b"#!/bin/sh\nexec sleep 1\n"}
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        def add(name, data, **kw):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            for k, v in kw.items():
                setattr(info, k, v)
            tar.addfile(info, io.BytesIO(data))
        add("plugin.json", json.dumps(manifest).encode())
        for name, data in files.items():
            add(name, data, mode=0o644)
        for info in extra or []:
            tar.addfile(info, io.BytesIO(b""))
    return buf.getvalue()


def test_a_good_package_installs_under_var_lib_with_current_pointing_at_it(tmp_path):
    checked = uploads.install(package(), ours={"lms"}, root=tmp_path)
    assert (checked.id, checked.version, checked.kind) == ("radiofoo", "1.0.0", "renderer")
    assert (tmp_path / "radiofoo" / "current").resolve() == tmp_path / "radiofoo" / "1.0.0"
    assert (tmp_path / "radiofoo" / "current" / "bin" / "radiofoo").stat().st_mode & 0o111
    [plugin] = uploads.installed(tmp_path)
    assert plugin.unit == "gexis-uploaded-renderer@radiofoo.service", "the player's unit, never its own"


def test_a_newer_version_updates_and_keeps_one_step_back(tmp_path):
    for v in ("1.0.0", "1.1.0", "1.2.0"):
        m = {"id": "radiofoo", "name": "Radio Foo", "kind": "renderer", "version": v, "run": "bin/radiofoo"}
        uploads.install(package(m), ours=set(), root=tmp_path)
    kept = sorted(p.name for p in (tmp_path / "radiofoo").iterdir() if not p.name.startswith("."))
    assert kept == ["1.1.0", "1.2.0", "current"]
    assert (tmp_path / "radiofoo" / "current").resolve().name == "1.2.0"


@pytest.mark.parametrize("change, reason", [
    (lambda m: m.pop("run"), "no 'run'"),
    (lambda m: m.pop("version"), "no 'version'"),
    (lambda m: m.update(unit="evil.service"), "may not bring its own unit"),
    (lambda m: m.update(id="lms"), "belongs to the player"),
    (lambda m: m.update(kind="daemon"), "plugin.json:"),
    (lambda m: m.update(run="bin/missing"), "is not in the package"),
    (lambda m: m.update(version="1.0 beta"), "not a usable version"),
])
def test_a_bad_manifest_is_refused_with_a_reason(tmp_path, change, reason):
    m = {"id": "radiofoo", "name": "Radio Foo", "kind": "renderer", "version": "1.0.0", "run": "bin/radiofoo"}
    change(m)
    with pytest.raises(uploads.Refused, match=reason):
        uploads.install(package(m), ours={"lms"}, root=tmp_path)
    assert not (tmp_path / "radiofoo").exists(), "nothing written"


def test_paths_that_escape_the_package_are_refused(tmp_path):
    for name in ("../etc/passwd", "/etc/passwd"):
        with pytest.raises(uploads.Refused, match="outside"):
            uploads.install(package(files={"bin/radiofoo": b"#!/bin/sh\n", name: b"x"}), ours=set(), root=tmp_path)
    link = tarfile.TarInfo("bin/escape")
    link.type = tarfile.SYMTYPE
    link.linkname = "/etc/shadow"
    with pytest.raises(uploads.Refused, match="links outside"):
        uploads.install(package(extra=[link]), ours=set(), root=tmp_path)


def test_a_program_for_another_machine_is_refused(tmp_path):
    with pytest.raises(uploads.Refused, match="aarch64"):
        uploads.install(package(files={"bin/radiofoo": ELF_X86}), ours=set(), root=tmp_path)
    assert uploads.install(package(files={"bin/radiofoo": ELF_AARCH64}), ours=set(), root=tmp_path)


def test_the_same_version_again_is_refused(tmp_path):
    uploads.install(package(), ours=set(), root=tmp_path)
    with pytest.raises(uploads.Refused, match="already installed"):
        uploads.install(package(), ours=set(), root=tmp_path)


def test_not_a_tarball_is_refused(tmp_path):
    with pytest.raises(uploads.Refused, match="not a .tar.gz"):
        uploads.install(b"PK\x03\x04 a zip", ours=set(), root=tmp_path)


def test_remove_deletes_every_version(tmp_path):
    uploads.install(package(), ours=set(), root=tmp_path)
    assert uploads.remove("radiofoo", tmp_path)
    assert not (tmp_path / "radiofoo").exists() and uploads.installed(tmp_path) == []
    assert not uploads.remove("radiofoo", tmp_path)
