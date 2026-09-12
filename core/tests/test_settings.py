"""Unit tests for the SQLite settings store (Phase 3 criterion 5)."""
from __future__ import annotations

from pathlib import Path

from gexis_core.settings import SettingsStore


def test_unknown_key_returns_default(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.db")
    assert store.get("nope") is None
    assert store.get("nope", "fallback") == "fallback"


def test_set_then_get_roundtrips(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.db")
    store.set("device_name", "gexis")
    assert store.get("device_name") == "gexis"


def test_set_overwrites_an_existing_value(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.db")
    store.set("boot_volume_steps", 60)
    store.set("boot_volume_steps", 90)
    assert store.get("boot_volume_steps") == 90


def test_values_of_different_json_types_roundtrip(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.db")
    store.set("a_bool", True)
    store.set("an_int", 60)
    store.set("a_float", -40.0)
    store.set("a_string", "meter+spectrum")
    store.set("a_list", ["aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66"])

    assert store.get("a_bool") is True
    assert store.get("an_int") == 60
    assert store.get("a_float") == -40.0
    assert store.get("a_string") == "meter+spectrum"
    assert store.get("a_list") == ["aa:bb:cc:dd:ee:ff", "11:22:33:44:55:66"]


def test_delete_removes_a_key(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.db")
    store.set("theme", "dark")
    store.delete("theme")
    assert store.get("theme") is None


def test_delete_of_an_unknown_key_is_a_noop(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.db")
    store.delete("never_set")  # must not raise


def test_settings_survive_a_restart(tmp_path: Path):
    """The acceptance bar, literally: a fresh SettingsStore instance
    pointed at the same file (standing in for the daemon restarting)
    must see what an earlier instance wrote."""
    path = tmp_path / "settings.db"
    SettingsStore(path).set("idle_timeout_s", 300)

    reopened = SettingsStore(path)

    assert reopened.get("idle_timeout_s") == 300


def test_creates_missing_parent_directories(tmp_path: Path):
    path = tmp_path / "nested" / "dir" / "settings.db"
    store = SettingsStore(path)
    store.set("x", 1)
    assert path.exists()
