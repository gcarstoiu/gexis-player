"""ADR-0035: the settings registry and API."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core.settings import SettingsStore
from gexis_core.settings_registry import (
    InvalidValue,
    NotSettable,
    NotWired,
    Settings,
    UnknownSetting,
    load_registry,
    validate,
)
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

DESIGN = Path(__file__).parents[2] / "design" / "source" / "Settings.dc.html"


def _rows():
    return [r for g in load_registry() for r in g["rows"] if r["type"] != "group"]


def test_the_shipped_registry_loads_and_every_number_is_bounded():
    rows = _rows()
    assert len({r["key"] for r in rows}) == len(rows)
    assert all("min" in r and "max" in r for r in rows if r["type"] == "number")


def test_registry_keys_are_the_designs_keys_apart_from_recorded_deviations():
    design_keys = set(re.findall(r"\bk:\s*'([a-z_0-9]+)'", DESIGN.read_text()))
    ours = {r["key"] for r in _rows()}
    assert design_keys - ours == {"idle_grace"}  # merged into idle_timeout, ADR-0033
    # Rows the design has no key for, each with a reason:
    #   drawer_on_external / drawer_autohide - ADR-0034's volume drawer
    #   listenbrainz_token - ListenBrainz began requiring a token for the
    #     artist page's Popular list on 2026-09-18 (George chose a per-user
    #     token over dropping the section; ADR-0022, ADR-0040 §2)
    #   fanart_key - artist pictures (George, 2026-09-18)
    assert ours - design_keys == {
        "drawer_on_external", "drawer_autohide", "listenbrainz_token", "fanart_key",
    }


def test_trusted_devices_and_plugins_are_navigation():
    nav = {r["key"] for r in _rows() if r.get("navigation")}
    assert nav == {"bt_trusted", "plugins"}


@pytest.mark.parametrize(
    ("row", "value", "ok"),
    [
        ({"key": "t", "type": "toggle"}, True, True),
        ({"key": "t", "type": "toggle"}, 1, False),
        ({"key": "c", "type": "choice", "options": ["A", "B"]}, "B", True),
        ({"key": "c", "type": "choice", "options": ["A", "B"]}, "C", False),
        ({"key": "n", "type": "number", "min": 1, "max": 60}, 5, True),
        ({"key": "n", "type": "number", "min": 1, "max": 60}, 61, False),
        ({"key": "n", "type": "number", "min": 1, "max": 60}, True, False),
        ({"key": "n", "type": "number", "min": 1, "max": 60}, float("nan"), False),
        ({"key": "x", "type": "text"}, "  http://a/  ", True),
        ({"key": "x", "type": "text"}, 42, False),
        ({"key": "x", "type": "text"}, "a" * 501, False),
    ],
)
def test_validate_by_row_type(row, value, ok):
    if ok:
        validate(row, value)
    else:
        with pytest.raises(InvalidValue):
            validate(row, value)


def test_text_is_trimmed():
    assert validate({"key": "x", "type": "text"}, "  http://a/  ") == "http://a/"


def test_a_number_row_without_bounds_is_rejected(tmp_path):
    path = tmp_path / "r.json"
    path.write_text(json.dumps([{"id": "g", "rows": [{"key": "n", "type": "number"}]}]))
    with pytest.raises(ValueError):
        load_registry(path)


REGISTRY = [
    {
        "id": "g",
        "label": "G",
        "rows": [
            {"type": "group", "label": "Sub"},
            {"key": "idle_timeout", "type": "number", "min": 1, "max": 60, "default": 5},
            {"key": "idle_url", "type": "text", "default": None},
            {"key": "version", "type": "readonly", "default": None},
            {"key": "power", "type": "action"},
            {"key": "bt_trusted", "type": "action", "navigation": True},
        ],
    }
]


@pytest.fixture
def store(tmp_path):
    s = SettingsStore(tmp_path / "settings.db")
    yield s
    s.close()


def test_stored_beats_config_beats_registry_default(store):
    settings = Settings(store, registry=REGISTRY, defaults={"idle_url": lambda: "http://from-config/"})
    assert settings.value("idle_timeout") == 5
    assert settings.value("idle_url") == "http://from-config/"
    store.set("idle_url", "http://from-user/")
    assert settings.value("idle_url") == "http://from-user/"


def test_unwired_rows_render_but_refuse_writes(store):
    settings = Settings(store, registry=REGISTRY)
    rows = {r.get("key"): r for r in settings.to_json()[0]["rows"]}
    assert rows["idle_timeout"]["value"] == 5 and rows["idle_timeout"]["wired"] is False
    assert "default" not in rows["idle_timeout"]
    with pytest.raises(NotWired):
        settings.set("idle_timeout", 10)
    assert store.get("idle_timeout") is None


def test_a_wired_write_stores_calls_back_and_bumps_revision(store):
    seen, bumps = [], []
    settings = Settings(store, registry=REGISTRY, wired={"idle_timeout": seen.append}, on_change=lambda: bumps.append(1))
    assert settings.set("idle_timeout", 10) == 10
    assert store.get("idle_timeout") == 10 and seen == [10] and bumps == [1]
    with pytest.raises(InvalidValue):
        settings.set("idle_timeout", 0)


def test_readonly_and_action_take_no_value_and_navigation_does_not_run(store):
    settings = Settings(store, registry=REGISTRY, wired={"bt_trusted": None})
    with pytest.raises(NotSettable):
        settings.set("version", "x")
    with pytest.raises(NotSettable):
        settings.run("idle_timeout")
    with pytest.raises(NotWired):
        settings.run("bt_trusted")
    with pytest.raises(UnknownSetting):
        settings.value("nope")


def test_wiring_an_unknown_key_fails_at_startup(store):
    with pytest.raises(ValueError):
        Settings(store, registry=REGISTRY, wired={"nope": None})


async def test_settings_routes(store):
    state = StateStore({})
    settings = Settings(
        store, registry=REGISTRY, wired={"idle_timeout": None}, on_change=state.bump_settings_revision
    )
    server = StateServer(state, settings=settings)
    async with TestClient(TestServer(server.make_app())) as client:
        body = await (await client.get("/settings")).json()
        assert body["groups"][0]["rows"][1]["key"] == "idle_timeout"
        assert (await client.put("/settings/idle_timeout", json={"value": 7})).status == 200
        assert state.state.to_json()["settings_revision"] == 1
        assert (await client.put("/settings/idle_timeout", json={"value": 99})).status == 400
        assert (await client.put("/settings/idle_url", json={"value": "x"})).status == 409
        assert (await client.put("/settings/version", json={"value": "x"})).status == 405
        assert (await client.put("/settings/nope", json={"value": 1})).status == 404
        assert (await client.put("/settings/idle_timeout", json={})).status == 400
        assert (await client.post("/settings/bt_trusted")).status == 409


async def test_surface_is_panel_from_loopback():
    server = StateServer(StateStore({}))
    async with TestClient(TestServer(server.make_app())) as client:
        assert await (await client.get("/surface")).json() == {"surface": "panel"}


def test_timezone_is_read_from_the_localtime_link(tmp_path):
    from gexis_core.__main__ import read_timezone

    zone = tmp_path / "usr/share/zoneinfo/Europe/Berlin"
    zone.parent.mkdir(parents=True)
    zone.write_bytes(b"TZif")
    link = tmp_path / "localtime"
    link.symlink_to(zone)
    assert read_timezone(link) == "Europe/Berlin"
    assert read_timezone(tmp_path / "missing") is None


def test_clearing_a_text_value_falls_back_to_config(store):
    settings = Settings(
        store, registry=REGISTRY, defaults={"idle_url": lambda: "http://from-config/"}, wired={"idle_url": None}
    )
    assert settings.set("idle_url", "http://from-user/") == "http://from-user/"
    assert settings.set("idle_url", "   ") == "http://from-config/"
    assert store.get("idle_url") is None


def _seed(tmp_path, text):
    path = tmp_path / "seed.json"
    path.write_text(text)
    return path


def test_a_flash_time_seed_beats_config_and_loses_to_a_stored_value(store, tmp_path):
    settings = Settings(
        store,
        registry=REGISTRY,
        defaults={"idle_url": lambda: "http://from-config/"},
        wired={"idle_timeout": None},
        seed_path=_seed(tmp_path, '{"idle_timeout": 12, "idle_url": "http://from-seed/"}'),
    )
    assert settings.value("idle_timeout") == 12
    assert settings.value("idle_url") == "http://from-seed/"
    settings.set("idle_timeout", 30)
    assert settings.value("idle_timeout") == 30


def test_a_missing_seed_is_normal(store, tmp_path):
    settings = Settings(store, registry=REGISTRY, seed_path=tmp_path / "absent.json")
    assert settings.value("idle_timeout") == 5


@pytest.mark.parametrize(
    "text",
    ['{"idle_timeout": 999}', '{"nope": 1}', "[1, 2]", "not json", '{"version": "x"}'],
)
def test_a_bad_seed_entry_is_dropped_not_fatal(store, tmp_path, text):
    settings = Settings(store, registry=REGISTRY, seed_path=_seed(tmp_path, text))
    assert settings.value("idle_timeout") == 5
