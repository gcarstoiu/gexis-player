"""ADR-0105 §6, Phase 13c step 5: the core's side of updates."""
from __future__ import annotations

import json
import time

from gexis_core import updates


def write(tmp_path, **doc):
    path = tmp_path / "status.json"
    path.write_text(json.dumps(doc))
    return path


def test_release_says_only_what_runs_here_and_the_channel():
    """George, 2026-10-01: Release is read-only - the number and the channel."""
    assert updates.release_line("Testing", installed="0.3.1") == "0.3.1 · Testing"
    assert updates.release_line("Stable", installed="0.2.1+git871.c73ea29") == "0.2.1 · Stable"


def test_the_software_update_tile_says_what_was_found_and_when(tmp_path):
    here = "0.3.1"
    noon = time.mktime((2026, 10, 1, 12, 0, 0, 0, 0, -1))
    line = lambda **doc: updates.sentence(write(tmp_path, **doc), installed=here, now=noon)
    stamp = lambda t_: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t_))
    assert updates.sentence(tmp_path / "none.json", installed=here) == "Not checked yet"
    assert line(state="current", at=stamp(noon - 3600)) == "Up to date · checked today 11:00"
    assert line(state="current", at=stamp(noon - 86400)) == "Up to date · checked yesterday 12:00"
    assert line(state="current", at=stamp(noon - 4 * 86400)) == "Up to date · checked 27 Sep"
    assert line(state="checking") == "Checking…"
    assert line(state="available", release="0.3.2") == "0.3.2 available"
    assert line(state="installing", release="0.3.2") == "Updating to 0.3.2…"
    assert line(state="done", release="0.3.2") == "Updated to 0.3.1"
    assert line(state="failed", message="x") == "Did not update"


def test_the_published_update_locks_the_panel_only_while_the_install_runs(tmp_path):
    """ADR-0110 §6, and a stale file never locks it: `active` needs the unit."""
    path = write(tmp_path, state="installing", release="0.2.5+git1.a", previous="0.2.4",
                 steps={"download": "done", "install": "active"}, progress=1.0)
    v = updates.view(path, installed="0.2.4", running=True)
    assert v["active"] and v["release"] == "0.2.5" and v["steps"]["install"] == "active"
    assert not updates.view(path, installed="0.2.4", running=False)["active"]
    done = write(tmp_path, state="done", release="0.2.5")
    assert not updates.view(done, installed="0.2.5", running=True)["active"]


def test_the_updates_rows_are_in_system_and_the_channel_warns_on_testing():
    from gexis_core.settings_registry import load_registry
    system = next(g for g in load_registry() if g["id"] == "system")
    rows = {r.get("key"): r for r in system["rows"] if r.get("key")}
    assert {"update_status", "update_check", "update_install", "updates", "update_channel"} <= set(rows)
    assert rows["updates"]["default"] == "Manual" and not rows["updates"].get("surfaced") is False
    assert rows["update_channel"]["options"] == ["Stable", "Testing"]
    assert rows["update_channel"]["default"] == "Stable"
    assert "does not downgrade" in rows["update_channel"]["warn"]["Testing"]
    assert rows["update_install"].get("confirm")


def test_the_release_row_s_note_says_what_is_new_only_while_waiting(tmp_path):
    """2026-10-01, George: the release's own notes under the Release row."""
    text = "Release notes on the device."
    assert updates.whats_new(write(tmp_path, state="available", release="0.2.2", whats_new=text)) \
        == "What's new in 0.2.2: Release notes on the device."
    assert updates.whats_new(write(tmp_path, state="done", release="0.2.2", whats_new=text)) is None, \
        "installed: its notes are under Change logs (ADR-0116)"
    assert updates.whats_new(write(tmp_path, state="current", release="0.2.2", whats_new=text)) is None
    assert updates.whats_new(write(tmp_path, state="available", release="0.2.2")) is None


def test_a_row_s_note_can_follow_the_device(tmp_path):
    from gexis_core.settings import SettingsStore
    from gexis_core.settings_registry import Settings
    note = {"text": None}
    s = Settings(SettingsStore(tmp_path / "s.json"), notes={"update_status": lambda: note["text"]})
    row = lambda: next(r for g in s.to_json() for r in g["rows"] if r.get("key") == "update_status")
    assert row().get("note") is None
    note["text"] = "What's new in 0.2.2: something"
    assert row()["note"] == "What's new in 0.2.2: something"


def test_the_installed_release_is_asked_of_dpkg_once_per_change(tmp_path, monkeypatch):
    """2026-10-05: four Settings rows read it on every GET /settings, at
    31 ms a dpkg-query - most of a slow save. Asked again only when dpkg's
    status file changes."""
    import os
    import subprocess as sp

    from gexis_core import updates

    calls = []
    answers = iter(["0.8.9+git1.aaa", "0.9.0"])

    def run(*args, **kwargs):
        calls.append(args)
        return sp.CompletedProcess(args, 0, next(answers), "")

    monkeypatch.setattr(updates.subprocess, "run", run)
    monkeypatch.setattr(updates, "_installed", (None, None))
    status = tmp_path / "status"
    status.write_text("x")
    os.utime(status, (1000, 1000))
    assert updates.installed_release(status) == "0.8.9+git1.aaa"
    assert updates.installed_release(status) == "0.8.9+git1.aaa"
    assert len(calls) == 1
    os.utime(status, (2000, 2000))  # an install
    assert updates.installed_release(status) == "0.9.0"
    assert len(calls) == 2
