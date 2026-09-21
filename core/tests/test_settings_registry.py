"""ADR-0035: the settings registry and API."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core.settings import SettingsStore
from gexis_core.settings_registry import (
    ONLY_WHEN_ANY,
    SETTABLE,
    InvalidValue,
    NotSettable,
    NotWired,
    Settings,
    UnknownSetting,
    load_registry,
    validate,
    visible,
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


#: Thirteen design keys the registry does not have yet, **each owed to a
#: named subphase**: nine to 9g (the idle screen's backgrounds and the
#: weather stack) and four to 9h (the home strip, the skin picker and
#: `viz_stop`). A key not owed to one of them is a key nobody planned for,
#: which is what this assertion catches.
#:
#: `handoff_duration` and `reboot` were on this list until 2026-09-20 and
#: were owed to nobody - George found both missing on the panel. Neither has
#: a feature behind it, so both belonged in 9d and landed there. **Checking
#: the list against the plan is the step that was skipped**; it is written
#: out here so the next omission is a test failure rather than a discovery.
#:
#: **This list only shrinks.**
DESIGN_KEYS_NOT_YET_IN_THE_REGISTRY = {
    # 9g - the idle screen
    "idle_background", "idle_days", "idle_icons", "idle_minmax",
    "idle_screen", "idle_weather", "wallpaper_key", "weather_key",
    "weather_location",
    # 9h - home strip, skin picker, viz_stop
    "home_strip", "home_strip_count", "skin", "viz_stop",
}


#: Not a row. The Wi-Fi password sheet builds its key at runtime from the
#: network name - `k: 'wifi_pass_' + it[0]` - and the literal prefix is all
#: the regex below can see. It will never be a registry key.
DESIGN_KEYS_THAT_ARE_NOT_ROWS = {"wifi_pass_"}


def test_registry_keys_are_the_designs_keys_apart_from_recorded_deviations():
    design_keys = set(
        re.findall(r"\bk:\s*'([a-z_0-9]+)'", DESIGN.read_text())
    ) - DESIGN_KEYS_THAT_ARE_NOT_ROWS
    ours = {r["key"] for r in _rows()}
    # `idle_grace` was merged into `idle_timeout` (ADR-0033) and is gone
    # from the drop, so every outstanding gap belongs to 9g or 9h.
    assert design_keys - ours == DESIGN_KEYS_NOT_YET_IN_THE_REGISTRY
    # Every row below is one the 2026-09-20 drop stopped surfacing.
    # ADR-0022's amendment keeps them inventoried - George: "decisions. They
    # should still be kept on a list, but not used at this point in the
    # settings screen" - so they stay in the registry and gain
    # `surfaced: false` in 9d rather than being deleted.
    #
    # The four rows that used to be listed here as ours-only -
    # drawer_on_external, drawer_autohide, listenbrainz_token and fanart_key -
    # are in the design now; the drop adopted them.
    assert ours - design_keys == {
        "api_loopback", "backup", "boot_default_scope", "brightness",
        "confidence", "factory_reset", "idle_close", "image_build",
        "lms_player", "log_level", "plugins", "power", "release_ladder",
        "restore_floor", "seek_reanchor", "spotify_name", "theme",
        "time_display", "updates", "volume_managed",
    }


def test_navigation_is_gone_and_lists_replaced_it():
    """ADR-0044 §1: `action` + `navigation: true` was a row that could never
    be wired - `run()` raised NotWired for it unconditionally - so a
    sub-screen behind one could never be finished. `list` means what it
    does, and nothing carries `navigation` any more."""
    assert not [r for r in _rows() if r.get("navigation")]
    lists = {r["key"] for r in _rows() if r["type"] == "list"}
    assert lists == {"bt_trusted", "wifi", "lms_server"}
    # A list is navigation, not a value: it never takes a scalar write.
    assert all(r["type"] not in SETTABLE for r in _rows() if r["type"] == "list")


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
            {"key": "bt_trusted", "type": "list", "empty": "Nothing paired."},
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


def test_readonly_and_action_take_no_value_and_a_list_is_neither(store):
    settings = Settings(store, registry=REGISTRY, wired={"power": None})
    with pytest.raises(NotSettable):
        settings.set("version", "x")
    with pytest.raises(NotSettable):
        settings.run("idle_timeout")
    with pytest.raises(UnknownSetting):
        settings.value("nope")
    # A list is navigation with items: it is not an action, so it cannot be
    # run, and it is not settable, so it takes no scalar. Before ADR-0044
    # these rows were `action` + `navigation: true`, which `run()` rejected
    # with NotWired - a row that could never be wired, behind which a
    # sub-screen could never be finished.
    with pytest.raises(NotSettable):
        settings.run("bt_trusted")
    with pytest.raises(NotSettable):
        settings.set("bt_trusted", "anything")


def test_wiring_an_unknown_key_fails_at_startup(store):
    with pytest.raises(ValueError):
        Settings(store, registry=REGISTRY, wired={"nope": None})


async def test_settings_routes(store, monkeypatch):
    # `/settings` counts `bt_trusted`'s devices on the way out. Nothing here
    # is about BlueZ, and a test that reaches the system bus to find that
    # out is a test about the machine it runs on.
    async def no_bluetooth(call, *args):
        return []

    monkeypatch.setattr(StateServer, "_bluetooth", staticmethod(no_bluetooth))
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
        # A list is not an action: POSTing it is 405 (NotSettable), where an
        # action nobody has wired is 409 (NotWired). Before ADR-0044 this row
        # was `action` + `navigation: true` and gave 409 - a row that looked
        # runnable and never could be.
        assert (await client.post("/settings/bt_trusted")).status == 405
        assert (await client.post("/settings/power")).status == 409


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


# ── ADR-0044's six mechanics ──────────────────────────────────────────────

def _vis(rows, values):
    by = {r["key"]: r for r in rows if r.get("key")}
    return {r["key"] for r in rows if r.get("key") and visible(r, by, values)}


def test_surfaced_false_hides_a_row_the_api_still_publishes():
    """ADR-0022's amendment: the inventory keeps every row it ever decided on
    and the screen shows the design's. George: "decisions. They should still
    be kept on a list, but not used at this point in the settings screen."
    """
    rows = [
        {"key": "shown", "type": "toggle"},
        {"key": "kept", "type": "toggle", "surfaced": False},
    ]
    assert _vis(rows, {}) == {"shown"}


def test_only_when_matches_a_value_and_ANY_matches_anything_present():
    rows = [
        {"key": "on", "type": "toggle"},
        {"key": "key", "type": "text"},
        {"key": "exact", "type": "toggle", "onlyWhen": ["on", True]},
        {"key": "any", "type": "text", "onlyWhen": ["key", ONLY_WHEN_ANY]},
    ]
    assert _vis(rows, {"on": False, "key": None}) == {"on", "key"}
    assert _vis(rows, {"on": True, "key": ""}) == {"on", "key", "exact"}
    assert _vis(rows, {"on": False, "key": "abc"}) == {"on", "key", "any"}
    # False is "not present" for ANY, the same as None and "" - a toggle that
    # is off has not been given a value in the sense the sentinel means.
    assert "any" not in _vis(rows, {"key": False})


def test_only_when_is_transitive():
    """The weather stack: Location depends on the key, which depends on the
    toggle. Turning the toggle off has to take all of them, not just the row
    naming it."""
    rows = [
        {"key": "weather", "type": "toggle"},
        {"key": "weather_key", "type": "text", "onlyWhen": ["weather", True]},
        {"key": "location", "type": "text", "onlyWhen": ["weather_key", ONLY_WHEN_ANY]},
    ]
    assert _vis(rows, {"weather": True, "weather_key": "k"}) == {"weather", "weather_key", "location"}
    # The key is hidden, so Location goes with it even though its own
    # condition is satisfied.
    assert _vis(rows, {"weather": False, "weather_key": "k"}) == {"weather"}


def test_only_when_cycle_hides_rather_than_recursing():
    rows = [
        {"key": "a", "type": "toggle", "onlyWhen": ["b", True]},
        {"key": "b", "type": "toggle", "onlyWhen": ["a", True]},
    ]
    assert _vis(rows, {"a": True, "b": True}) == set()


def test_the_loader_rejects_a_vocabulary_that_cannot_work(tmp_path):
    def write(groups):
        path = tmp_path / "r.json"
        path.write_text(json.dumps(groups))
        return path

    def rows(*r):
        return [{"id": "g", "label": "G", "rows": list(r)}]

    # onlyWhen naming a key that does not exist
    with pytest.raises(ValueError, match="unknown setting"):
        load_registry(write(rows({"key": "a", "type": "toggle", "onlyWhen": ["nope", True]})))
    # warn naming an option that does not exist
    with pytest.raises(ValueError, match="warn names options"):
        load_registry(write(rows(
            {"key": "a", "type": "choice", "options": ["x"], "warn": {"y": "boom"}}
        )))
    # warn on something that is not a choice
    with pytest.raises(ValueError, match="only for a choice"):
        load_registry(write(rows({"key": "a", "type": "toggle", "warn": {"x": "boom"}})))
    # optionsFrom naming a source nothing provides
    with pytest.raises(ValueError, match="unknown optionsFrom"):
        load_registry(write(rows({"key": "a", "type": "choice", "optionsFrom": "nope"})))
    # a choice with neither options nor optionsFrom
    with pytest.raises(ValueError, match="options or optionsFrom"):
        load_registry(write(rows({"key": "a", "type": "choice"})))
    # and the shapes that are fine
    load_registry(write(rows(
        {"key": "a", "type": "choice", "options": ["x"], "warn": {"x": "careful"}},
        {"key": "b", "type": "choice", "optionsFrom": "skin_corpus"},
        {"key": "c", "type": "list", "empty": "Nothing found."},
        {"key": "d", "type": "toggle", "onlyWhen": ["a", "x"]},
    )))


def test_the_shipped_registry_hides_twenty_rows_and_shows_the_rest():
    rows = _rows()
    kept = [r for r in rows if r.get("surfaced") is False]
    assert len(kept) == 20, "ADR-0022's amendment: inventoried, not surfaced"
    # Every one of them is still served by the API.
    assert all(r.get("key") for r in kept)
    # 54 at the start of 9d, plus the two rows the design has and the plan
    # had given to nobody.
    assert len(rows) == 56
    assert len(rows) - len(kept) == 36


def test_a_server_list_stores_an_address_and_every_other_list_does_not():
    """ADR-0044 §1 draws the line inside the type: tapping a discovered
    server *sets the value*; a Wi-Fi or Bluetooth list is navigation and its
    readout is derived."""
    server = {"key": "lms_server", "type": "list", "kind": "server"}
    plain = {"key": "bt_trusted", "type": "list"}
    assert validate(server, " 192.168.1.10:9000 ") == "192.168.1.10:9000"
    with pytest.raises(InvalidValue):
        validate(server, "  ")
    with pytest.raises(InvalidValue):
        validate(server, 9000)
    with pytest.raises(NotSettable):
        validate(plain, "George's iPhone")


def test_set_refuses_a_navigation_list_before_it_asks_whether_it_is_wired(store):
    settings = Settings(store, registry=REGISTRY, wired={"bt_trusted": None})
    with pytest.raises(NotSettable):
        settings.set("bt_trusted", "anything")


def test_the_payload_carries_visibility_per_row(store):
    settings = Settings(store)
    rows = [r for g in settings.to_json() for r in g["rows"] if r.get("key")]
    assert all("visible" in r for r in rows)
    by = {r["key"]: r for r in rows}
    # Inventoried but not surfaced, and still published.
    assert by["log_level"]["visible"] is False
    assert by["log_level"]["type"] == "choice"
    # Conditional: show_transition defaults on, so its dependant is drawn.
    assert by["show_transition"]["value"] is True
    assert by["handoff_threshold"]["visible"] is True
