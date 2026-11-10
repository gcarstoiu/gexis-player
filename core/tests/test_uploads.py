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
    assert checked.previous is None, "a first install"
    assert (tmp_path / "radiofoo" / "current").resolve() == tmp_path / "radiofoo" / "1.0.0"
    assert (tmp_path / "radiofoo" / "current" / "bin" / "radiofoo").stat().st_mode & 0o111
    [plugin] = uploads.installed(tmp_path)
    assert plugin.unit == "gexis-uploaded-renderer@radiofoo.service", "the player's unit, never its own"


def test_a_newer_version_updates_and_keeps_one_step_back(tmp_path):
    for v in ("1.0.0", "1.1.0", "1.2.0"):
        m = {"id": "radiofoo", "name": "Radio Foo", "kind": "renderer", "version": v, "run": "bin/radiofoo"}
        checked = uploads.install(package(m), ours=set(), root=tmp_path)
    assert checked.previous == "1.1.0", "the page says what it updated from"
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


def _shaped(*members) -> bytes:
    """An archive member by member: (name, data) for a file, (name, None,
    type, target) for a link."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data, *link in members:
            info = tarfile.TarInfo(name)
            if data is None:
                info.type, info.linkname = link
                tar.addfile(info)
            else:
                info.size, info.mode = len(data), 0o755
                tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _manifest(kind: str, version: str) -> bytes:
    return json.dumps({"id": "quiet", "name": "Quiet", "kind": kind, "version": version, "run": "run"}).encode()


RUN = ("run", b"#!/bin/sh\nexec sleep 1\n")


@pytest.mark.parametrize("members, reason", [
    # A second manifest after the first, read by the check in its place.
    ([("plugin.json", _manifest("renderer", "9.9")), (".plugin.json", _manifest("service", "1.0"))], None),
    ([("plugin.json", _manifest("renderer", "9.9")), ("./plugin.json", _manifest("service", "1.0"))], "twice"),
    # The manifest a hard link to a file the archive writes again later.
    ([("x.json", _manifest("service", "1.0")), ("plugin.json", None, tarfile.LNKTYPE, "x.json"),
      ("x.json", _manifest("renderer", "9.9"))], "twice"),
    # The manifest written again through a link to the package's own folder.
    ([("plugin.json", _manifest("service", "1.0")), ("sub", None, tarfile.SYMTYPE, "."),
      ("sub/plugin.json", _manifest("renderer", "9.9"))], "inside a link"),
])
def test_the_manifest_checked_is_the_one_installed(tmp_path, members, reason):
    """The review of 1.16.1: each of these was checked as a service at 1.0
    and installed as a renderer at 9.9, with the sound card."""
    archive = _shaped(*members, RUN)
    try:
        checked = uploads.check(archive, ours=set(), installed={})
    except uploads.Refused as exc:
        assert reason and reason in str(exc)
    else:
        assert reason is None and (checked.kind, checked.version) == ("renderer", "9.9")
        return
    with pytest.raises(uploads.Refused):
        uploads.install(archive, ours=set(), root=tmp_path)
    assert uploads.installed(tmp_path) == []


def test_a_package_made_from_its_folder_still_installs(tmp_path):
    """`tar -C folder .` names every member from `./`."""
    archive = _shaped(("./", None, tarfile.DIRTYPE, ""), ("./plugin.json", _manifest("service", "1.0")),
                      ("./run", RUN[1]))
    assert uploads.install(archive, ours=set(), root=tmp_path).kind == "service"
    assert [p.id for p in uploads.installed(tmp_path)] == ["quiet"]


def test_a_file_listed_twice_the_same_still_installs(tmp_path):
    """`tar -czf p.tar.gz plugin.json run .` lists each file twice, the same."""
    manifest = _manifest("service", "1.0")
    archive = _shaped(("plugin.json", manifest), RUN, ("./", None, tarfile.DIRTYPE, ""),
                      ("./plugin.json", manifest), ("./run", RUN[1]))
    assert uploads.install(archive, ours=set(), root=tmp_path).kind == "service"


def test_a_manifest_that_unpacks_other_than_checked_is_not_installed(tmp_path, monkeypatch):
    """Whatever the archive's trick: what is unpacked is read again, and
    installed only if it is what the check read."""
    real = uploads.check

    def checked_as_a_service(archive, **kw):
        found = real(archive, **kw)
        return uploads.replace(found, manifest={**found.manifest, "kind": "service"})
    monkeypatch.setattr(uploads, "check", checked_as_a_service)
    with pytest.raises(uploads.Refused, match="other than the one checked"):
        uploads.install(_shaped(("plugin.json", _manifest("renderer", "1.0")), RUN), ours=set(), root=tmp_path)
    assert uploads.installed(tmp_path) == []
    assert not any((tmp_path / "quiet").iterdir()), "nothing left unpacked"


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


def test_an_uploaded_plugins_switch_starts_off_and_says_it_was_uploaded(tmp_path):
    from gexis_core.settings_registry import Settings, load_registry
    uploads.install(package(), ours=set(), root=tmp_path)
    [plugin] = uploads.installed(tmp_path)
    registry = Settings.with_plugins(load_registry(), [plugin], {})
    rows = [r for g in registry for r in g.get("rows", []) if r.get("key") == "radiofoo.enabled"]
    assert rows and rows[0]["default"] is False and rows[0]["uploaded"] is True
    # ADR-0169: its tag says it was uploaded; its note what it does.
    assert rows[0]["note"].endswith("installed from a file.")


def test_a_restore_without_the_package_is_listed_as_needing_it_again(tmp_path):
    """ADR-0106 / 13a criterion 4: a backup keeps settings and data, not the
    package, and the restored device says what to upload again."""
    root, known = tmp_path / "plugins", tmp_path / "known.json"
    uploads.install(package(), ours=set(), root=root)
    uploads.remember(root, known)
    assert uploads.missing(root, known) == []
    uploads.remove("radiofoo", root)            # a new card: the package is gone
    gone = uploads.missing(root, known)
    assert gone == [{"id": "radiofoo", "name": "Radio Foo", "kind": "renderer", "area": "sources", "version": "1.0.0"}]
    uploads.remember(root, known)                # a start does not forget it
    assert uploads.missing(root, known) == gone
    uploads.forget("radiofoo", known)
    assert uploads.missing(root, known) == []


def test_the_missing_plugin_is_a_row_not_a_plugin(tmp_path):
    from gexis_core.settings_registry import Settings, load_registry
    registry = Settings.with_plugins(load_registry(), [], {}, missing=[
        {"id": "radiofoo", "name": "Radio Foo", "kind": "renderer", "version": "1.0.0"}])
    rows = [r for g in registry for r in g.get("rows", []) if r.get("key", "").startswith("radiofoo.")]
    assert [r["key"] for r in rows] == ["radiofoo.missing"]
    assert rows[0]["type"] == "readonly" and "Upload version 1.0.0 again" in rows[0]["note"]


def test_backups_hold_uploaded_plugins_data_and_list_not_packages():
    from gexis_core import backups
    assert "var/lib/private/gexis-uploaded" in backups.MEMBERS
    assert "var/lib/gexis/plugins-known.json" in backups.MEMBERS
    assert not any(m.startswith("var/lib/gexis/plugins") and m != "var/lib/gexis/plugins-known.json"
                   for m in backups.MEMBERS), "never the packages"


def test_a_manifest_can_say_which_settings_page_it_belongs_on(tmp_path):
    """George, 2026-09-30: an optional `area`; absent, the kind decides."""
    from gexis_core.settings_registry import Settings, load_registry
    m = {"id": "lyrics", "name": "Lyrics", "kind": "service", "version": "1.0.0",
         "run": "bin/radiofoo", "area": "enrichment",
         "settings": [{"key": "lang", "type": "text", "label": "Language", "default": None}]}
    uploads.install(package(m), ours=set(), root=tmp_path)
    [plugin] = uploads.installed(tmp_path)
    assert plugin.area == "enrich"
    registry = Settings.with_plugins(load_registry(), [plugin], {})
    where = {g["id"]: [r.get("key") or r["label"] for r in g["rows"]] for g in registry}
    assert "lyrics.lang" in where["enrich"] and "lyrics.lang" not in where["system"]
    plugins_page = where["plugins"]
    assert plugins_page.index("Enrichment") < plugins_page.index("lyrics.enabled"), "its switch under Enrichment"


def test_an_area_that_is_not_a_settings_page_is_refused(tmp_path):
    m = {"id": "radiofoo", "name": "Radio Foo", "kind": "renderer", "version": "1.0.0",
         "run": "bin/radiofoo", "area": "plugins"}
    with pytest.raises(uploads.Refused, match="is not one of"):
        uploads.install(package(m), ours=set(), root=tmp_path)


def test_an_uploaded_plugin_switched_on_and_not_running_is_started():
    """2026-10-12, sofapi: an upload restarted the plugin before the core knew
    it; refused, it ended cleanly and nothing started it after the core's
    restart. Started at the core's start - only uploaded, switched-on, idle."""
    from types import SimpleNamespace
    from gexis_core.__main__ import _start_uploaded
    p = lambda pid, uploaded=True: SimpleNamespace(id=pid, uploaded=uploaded, unit=f"u@{pid}")
    plugins = [p("qobuz"), p("running"), p("off"), p("shipped", uploaded=False)]
    started = []
    out = _start_uploaded(plugins, enabled=lambda u: u != "u@off",
                          state=lambda u: "active" if u == "u@running" else "inactive",
                          start=started.append)
    assert out == started == ["u@qobuz"]


def test_a_plugin_switched_on_without_its_package_is_not_retried():
    """A day of restarts every 3 s on sofapi: restored switched on, without
    its package. The run script says so and exits 78, which both units do
    not restart on."""
    import subprocess, sys
    from pathlib import Path
    files = Path(__file__).resolve().parents[2] / "image" / "stage-gexis" / "03-core" / "files"
    result = subprocess.run([sys.executable, str(files / "gexis-run-uploaded"), "no-such-plugin-here"],
                            capture_output=True, text=True)
    assert result.returncode == 78 and "not installed" in result.stderr
    for unit in ("gexis-uploaded-renderer@.service", "gexis-uploaded-service@.service"):
        assert "RestartPreventExitStatus=78" in (files / unit).read_text()


def test_what_a_plugin_downloads_into_its_folder_can_run():
    """ADR-0174, found on sofapi 2026-11-03: systemd mounts a DynamicUser
    state directory noexec, and Plexamp's native module, unpacked there by
    its plugin, failed to load. Both units give the folder exec back."""
    from pathlib import Path
    files = Path(__file__).resolve().parents[2] / "image" / "stage-gexis" / "03-core" / "files"
    for unit in ("gexis-uploaded-renderer@.service", "gexis-uploaded-service@.service"):
        lines = (files / unit).read_text().splitlines()
        assert "StateDirectory=gexis-uploaded/%i" in lines
        assert "ExecPaths=/var/lib/private/gexis-uploaded/%i" in lines, unit


@pytest.mark.parametrize("rows, reason", [
    ([{"key": "interval", "type": "number", "label": "Every (s)"}], "a number row needs min and max"),
    ([{"key": "mode", "type": "choice", "label": "Mode"}], "a choice row needs options"),
    ([{"key": "a", "type": "text", "label": "A"}, {"key": "a", "type": "text", "label": "A"}], "duplicate setting key"),
    ([{"key": "a", "type": "text", "label": "A", "onlyWhen": ["nowhere", True]}], "onlyWhen names unknown setting"),
])
def test_settings_the_registry_would_refuse_are_refused_at_upload(tmp_path, rows, reason):
    """ADR-0178 decision 4: a package whose rows Settings would leave out -
    and once stopped the core with - is refused before anything is written,
    with the registry's reason."""
    m = {"id": "radiofoo", "name": "Radio Foo", "kind": "renderer", "version": "1.0.0", "run": "bin/radiofoo",
         "settings": rows}
    with pytest.raises(uploads.Refused, match=f"plugin.json: .*{reason}"):
        uploads.install(package(m), ours={"lms"}, root=tmp_path)
    assert not (tmp_path / "radiofoo").exists(), "nothing written"


def test_usable_settings_still_install(tmp_path):
    m = {"id": "radiofoo", "name": "Radio Foo", "kind": "renderer", "version": "1.0.0", "run": "bin/radiofoo",
         "settings": [{"key": "interval", "type": "number", "label": "Every (s)", "min": 1, "max": 60},
                      {"key": "enabled", "type": "toggle", "label": "On"}]}
    assert uploads.install(package(m), ours={"lms"}, root=tmp_path).id == "radiofoo"
