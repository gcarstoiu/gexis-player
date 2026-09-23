"""ADR-0022's `boot_volume` row, wired 2026-09-23.

ADR-0018: a fixed safe level at every cold boot, never the previous
session's. The level is now the user's, in dB; `core.toml`'s
`boot_volume_steps` remains the fallback.

**The unit exists so that nothing plays into whatever `alsactl` left**, so
every failure here has to end with the safe level written anyway - a
settings file that cannot be read must not be able to skip it.
"""
from __future__ import annotations

import pytest

from gexis_core import boot_volume
from gexis_core.config import Config
from gexis_core.settings import SettingsStore
from gexis_core.volume import db_to_raw


@pytest.fixture
def store(tmp_path, monkeypatch):
    path = tmp_path / "settings.db"
    monkeypatch.setattr(
        boot_volume, "SettingsStore", lambda *a, **k: SettingsStore(path)
    )
    return SettingsStore(path)


def test_the_row_decides_the_level(store):
    store.set("boot_volume", -60)

    level, source = boot_volume._chosen_level(Config())

    assert level == db_to_raw(-60)
    assert "settings" in source


def test_nothing_stored_falls_back_to_the_configured_steps(store):
    config = Config()

    level, source = boot_volume._chosen_level(config)

    assert level == config.boot_volume_steps
    assert "core.toml" in source


def test_a_value_that_is_not_a_number_does_not_skip_the_safe_level(store):
    store.set("boot_volume", "quite loud")
    config = Config()

    level, source = boot_volume._chosen_level(config)

    assert level == config.boot_volume_steps


def test_a_settings_store_that_will_not_open_does_not_skip_it_either(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("read-only filesystem")

    monkeypatch.setattr(boot_volume, "SettingsStore", boom)
    config = Config()

    level, source = boot_volume._chosen_level(config)

    assert level == config.boot_volume_steps
    assert "core.toml" in source


def test_the_shipped_default_is_the_row_and_the_config_agreeing(store):
    """-90 dB is raw 60, which is what `core.toml` carries and what the
    registry offers as the row's default. They are two statements of one
    number and they must not drift."""
    assert db_to_raw(-90) == Config().boot_volume_steps
