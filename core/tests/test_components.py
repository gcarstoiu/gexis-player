"""ADR-0100 as amended: what a plugin's download tells the user."""
from __future__ import annotations

import json

from gexis_core import components
from gexis_core.settings_registry import Settings, load_registry

PIN = """# a comment
URL=https://example.invalid/player.tar.bz2
SHA256=abc123
FORMAT=tar.bz2
DEST=/home/pi/player
OWNER=pi:pi
LABEL="Player 1.2"
FROM=Maker
PLUGIN=player
"""


def setup(tmp_path):
    pins, status, installed = tmp_path / "pins", tmp_path / "run", tmp_path / "lib"
    pins.mkdir()
    (pins / "player.env").write_text(PIN)
    return pins, status, installed


def test_a_pin_is_read_without_running_it(tmp_path):
    pins, _, _ = setup(tmp_path)
    pin = components.pins(pins)["player"]
    assert pin["LABEL"] == "Player 1.2" and pin["FROM"] == "Maker" and pin["PLUGIN"] == "player"
    assert components.for_plugin("player", pins) == "player"
    assert components.for_plugin("other", pins) is None


def test_before_anything_ran_it_is_absent_or_installed(tmp_path):
    pins, status, installed = setup(tmp_path)
    pin = components.pins(pins)["player"]
    assert components.status("player", pin, status_dir=status, installed_dir=installed)["state"] == "absent"
    installed.mkdir()
    (installed / "player.sha256").write_text("abc123\n")
    assert components.status("player", pin, status_dir=status, installed_dir=installed)["state"] == "installed"
    (installed / "player.sha256").write_text("stale\n")
    assert components.status("player", pin, status_dir=status, installed_dir=installed)["state"] == "absent", \
        "a stamp for another version is not this one installed"


def test_the_helpers_own_file_wins_and_a_broken_one_does_not(tmp_path):
    pins, status, installed = setup(tmp_path)
    pin = components.pins(pins)["player"]
    status.mkdir()
    (status / "player.json").write_text(json.dumps(
        {"state": "downloading", "received": 5, "total": 10, "attempt": 2, "attempts": 3}))
    s = components.status("player", pin, status_dir=status, installed_dir=installed)
    assert (s["state"], s["received"], s["total"], s["attempt"], s["label"]) == ("downloading", 5, 10, 2, "Player 1.2")
    (status / "player.json").write_text("{half")
    assert components.status("player", pin, status_dir=status, installed_dir=installed)["state"] == "absent"


def test_the_switch_says_preparing_at_once_unless_there_is_nothing_to_do(tmp_path):
    pins, status, installed = setup(tmp_path)
    pin = components.pins(pins)["player"]
    components.preparing("player", pin, status_dir=status)
    assert components.status("player", pin, status_dir=status, installed_dir=installed)["state"] == "preparing"
    (status / "player.json").write_text(json.dumps({"state": "installed"}))
    components.preparing("player", pin, status_dir=status)
    assert components.status("player", pin, status_dir=status, installed_dir=installed)["state"] == "installed"


def test_a_plugin_that_downloads_gets_a_row_under_its_switch():
    class P:
        id, name, kind, accent, settings, enabled_row, unit = "player", "Player", "renderer", "#fff", [], None, "p.service"

    groups = Settings.with_plugins(load_registry(), [P()], {"player": "player"})
    rows = next(g for g in groups if g["id"] == "plugins")["rows"]
    keys = [r["key"] for r in rows]
    assert keys.index("player.download") == keys.index("player.enabled") + 1
    row = next(r for r in rows if r["key"] == "player.download")
    assert row["type"] == "action" and row["component"] == "player"
    none = Settings.with_plugins(load_registry(), [P()])
    assert "player.download" not in [r["key"] for r in next(g for g in none if g["id"] == "plugins")["rows"]]
