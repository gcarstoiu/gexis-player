"""ADR-0105 §6, Phase 13c step 5: the core's side of updates."""
from __future__ import annotations

import json

from gexis_core import updates


def write(tmp_path, **doc):
    path = tmp_path / "status.json"
    path.write_text(json.dumps(doc))
    return path


def test_the_release_tile_says_the_number_and_its_state(tmp_path):
    """ADR-0110 §1-2: the number, not 0.2.1+git871.c73ea29, and its state."""
    here = "0.2.4+git3.abc1234"
    line = lambda **doc: updates.sentence(write(tmp_path, **doc), installed=here)
    assert updates.sentence(tmp_path / "none.json", installed="0.2.4") == "0.2.4 · Not checked yet"
    assert line(state="current", channel="testing") == "0.2.4 · Up to date"
    assert line(state="checking") == "0.2.4 · Checking…"
    assert line(state="available", release="0.2.5") == "0.2.5 available"
    assert line(state="installing", release="0.2.5") == "Updating to 0.2.5…"
    assert line(state="done", release="0.2.5") == "0.2.4 · Updated"
    assert line(state="failed", message="x") == "0.2.4 · Did not update"
    assert line(state="going-back", previous="0.2.3+git1.a") == "Going back to 0.2.3…"


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


def test_the_release_row_s_note_says_what_is_new_while_waiting_and_after(tmp_path):
    """2026-10-01, George: the release's own notes under the Release row."""
    text = "Release notes on the device."
    assert updates.whats_new(write(tmp_path, state="available", release="0.2.2", whats_new=text)) \
        == "What's new in 0.2.2: Release notes on the device."
    assert updates.whats_new(write(tmp_path, state="done", release="0.2.2", whats_new=text)).startswith("What's new in 0.2.2")
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
