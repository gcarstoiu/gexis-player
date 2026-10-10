"""ADR-0105 §5: settings move forward with the code (Phase 13c step 4)."""
from __future__ import annotations

import json

from gexis_core import settings_migrations as sm
from gexis_core.settings import SettingsStore

REGISTRY = sm.SHIPPED_KEYS_PATH.with_name("settings_registry.json")


def registry_keys() -> set[str]:
    return {r["key"] for g in json.loads(REGISTRY.read_text()) for r in g["rows"] if r.get("key")}


def test_every_key_that_left_the_registry_has_a_migration():
    """LESSONS 19-20: a key renamed or removed without a migration leaves a
    device's stored value behind, read by nothing, and the user's choice
    back at its default - found only on a device."""
    handled = set()
    for step in sm.MIGRATIONS:
        handled |= set(step.renames) | set(step.drops)
    gone = sm.shipped_keys() - registry_keys()
    assert gone <= handled, f"keys left the registry with no migration: {sorted(gone - handled)}"


def test_every_registry_key_is_recorded_as_shipped():
    """The other half of the check above: a new key must be recorded, or a
    later rename of it would slip through."""
    new = registry_keys() - sm.shipped_keys()
    assert not new, f"add to settings_shipped_keys.json: {sorted(new)}"


def test_a_rename_keeps_the_value_and_runs_once(tmp_path):
    store = SettingsStore(tmp_path / "s.db")
    store.set("old_name", "Automatic")
    steps = (sm.rename("old_name", "new_name", "renamed for a test"),)
    assert sm.migrate(store, steps) == 1
    assert store.get("new_name") == "Automatic" and store.get("old_name") is None
    assert store.get(sm.SCHEMA_KEY) == 1
    store.set("new_name", "Manual")
    assert sm.migrate(store, steps) == 0, "already run"
    assert store.get("new_name") == "Manual"


def test_a_device_several_releases_behind_runs_them_in_order(tmp_path):
    store = SettingsStore(tmp_path / "s.db")
    store.set("a", 5)
    steps = (sm.rename("a", "b", "one"), sm.convert("b", lambda v: v * 10, "two"), sm.drop("gone", "three"))
    store.set("gone", True)
    assert sm.migrate(store, steps) == 3
    assert store.get("b") == 50 and store.get("gone") is None and store.get(sm.SCHEMA_KEY) == 3


def test_a_rename_does_not_overwrite_a_value_already_under_the_new_name(tmp_path):
    store = SettingsStore(tmp_path / "s.db")
    store.set("old", 1)
    store.set("new", 2)
    sm.migrate(store, (sm.rename("old", "new", "t"),))
    assert store.get("new") == 2 and store.get("old") is None


def test_a_store_from_a_newer_release_is_left_alone(tmp_path):
    """An older image with a newer backup restored: nothing here knows the
    newer steps, so nothing is touched."""
    store = SettingsStore(tmp_path / "s.db")
    store.set(sm.SCHEMA_KEY, 7)
    store.set("x", 1)
    assert sm.migrate(store, (sm.drop("x", "t"),)) == 0
    assert store.get("x") == 1 and store.get(sm.SCHEMA_KEY) == 7


def test_the_schema_key_is_not_a_setting():
    assert sm.SCHEMA_KEY not in registry_keys()


def test_a_stored_none_forecast_becomes_today_only(tmp_path):
    """George, 2026-10-05: the forecast's second layout is "Today only". A
    device that chose "None" keeps that layout under its new name, and the
    new name is one the registry offers."""
    store = SettingsStore(tmp_path / "s.db")
    store.set("idle_forecast", "None")
    sm.migrate(store)
    assert store.get("idle_forecast") == "Today only"
    options = next(r["options"] for g in json.loads(REGISTRY.read_text()) for r in g["rows"]
                   if r.get("key") == "idle_forecast")
    assert store.get("idle_forecast") in options and "None" not in options
    other = SettingsStore(tmp_path / "t.db")
    other.set("idle_forecast", "3 days")
    sm.migrate(other)
    assert other.get("idle_forecast") == "3 days"


def test_a_slow_pointer_speed_is_raised_to_the_new_least(tmp_path):
    """George, 2026-10-05: the range moved from 50-300 to 150-400. A stored
    speed below 150 is raised to it; one inside the range is kept."""
    store = SettingsStore(tmp_path / "s.db")
    store.set("pointer_speed", 75)
    sm.migrate(store)
    assert store.get("pointer_speed") == 150
    row = next(r for g in json.loads(REGISTRY.read_text()) for r in g["rows"] if r.get("key") == "pointer_speed")
    assert row["min"] == 150 and row["default"] == 150
    other = SettingsStore(tmp_path / "t.db")
    other.set("pointer_speed", 225)
    sm.migrate(other)
    assert other.get("pointer_speed") == 225


def test_an_existing_player_keeps_artist_pictures_and_a_new_one_starts_on_gexis_wallpapers(tmp_path):
    """ADR-0133: Gexis wallpapers is the default on a new player, and an
    existing choice is kept - including the old default nobody stored."""
    keep = sm.MIGRATIONS.index(next(m for m in sm.MIGRATIONS if m.note.startswith("idle_background")))
    used = SettingsStore(tmp_path / "used.db")          # ran the earlier releases' migrations
    used.set(sm.SCHEMA_KEY, keep)
    sm.migrate(used)
    assert used.get("idle_background") == "Artist pictures"
    chosen = SettingsStore(tmp_path / "chosen.db")      # a choice already stored stays
    chosen.set(sm.SCHEMA_KEY, keep)
    chosen.set("idle_background", "Black")
    sm.migrate(chosen)
    assert chosen.get("idle_background") == "Black"
    new = SettingsStore(tmp_path / "new.db")            # a freshly flashed card
    sm.migrate(new)
    assert new.get("idle_background") is None and new.get(sm.SCHEMA_KEY) == len(sm.MIGRATIONS)
    default = next(r["default"] for g in json.loads(REGISTRY.read_text()) for r in g["rows"]
                   if r.get("key") == "idle_background")
    assert default == "Gexis wallpapers"
