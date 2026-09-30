"""ADR-0105 §6, Phase 13c step 5: the core's side of updates."""
from __future__ import annotations

import json

from gexis_core import updates


def write(tmp_path, **doc):
    path = tmp_path / "status.json"
    path.write_text(json.dumps(doc))
    return path


def test_the_release_row_says_what_the_updater_last_said(tmp_path):
    assert updates.sentence(tmp_path / "none.json") == "Not checked yet"
    assert updates.sentence(write(tmp_path, state="current", channel="testing")) == "Up to date (testing)"
    assert updates.sentence(write(tmp_path, state="available", release="0.2.2")) == "0.2.2 is waiting"
    assert updates.sentence(write(tmp_path, state="installing", release="0.2.2")) == "Installing 0.2.2…"
    assert updates.sentence(write(tmp_path, state="done", release="0.2.2")) == "Updated to 0.2.2"
    failed = updates.sentence(write(tmp_path, state="failed", message="install failed. Back on 0.2.1."))
    assert failed.startswith("Did not update: ") and "Back on 0.2.1" in failed


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
