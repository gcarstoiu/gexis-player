"""ADR-0035: the settings registry and API."""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core.settings import SettingsStore
from gexis_core.settings_registry import (
    Locked,
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


#: Design keys the registry does not have yet, **each owed to a named
#: subphase**. A key not owed to one is a key nobody planned for, which is
#: what this assertion catches.
#:
#: `handoff_duration` and `reboot` were on this list until 2026-09-20 and
#: were owed to nobody - George found both missing on the panel. Neither has
#: a feature behind it, so both belonged in 9d and landed there. **Checking
#: the list against the plan is the step that was skipped**; it is written
#: out here so the next omission is a test failure rather than a discovery.
#:
#: **It is empty now, and it can only shrink.** `skin` was the last entry:
#: the picker arrived in the 2026-09-22 drop and the row with it
#: (ADR-0051 §4).
DESIGN_KEYS_NOT_YET_IN_THE_REGISTRY: set[str] = set()

#: A design key the registry **deliberately** does not have, which is a
#: different statement from "not yet" and has to be said out loud: ADR-0022's
#: amendment makes the drop the point of truth, so a row we decline is a
#: decision, not a gap.
#:
#: `weather_key` gates four rows in the drop on the assumption that a weather
#: provider needs a key. **Open-Meteo does not** (ADR-0047 §2a, Finding 043),
#: so the row would store nothing and gate on nothing. The three rows left
#: hang off `idle_weather` instead.
#:
#: `idle_minmax` hid the day's high and low. George, 2026-09-22: *"the min
#: and max option in settings you can remove as it is not needed"* - the
#: design draws both numbers in both forecast layouts, so the row existed to
#: turn off something nobody would.
#:
#: **This set only grows with George's agreement**, and both of these are
#: his.
#: `per_renderer_volume` joined them on 2026-09-23, with the machinery
#: behind it: since ADR-0054 §5 a renderer is *asked* where it is when it
#: takes the device, so a second copy of what the renderer already
#: remembers decides nothing. Measured before deleting: 12 acquisitions,
#: 12 answers, 0 fallbacks. George: "delete them".
#: `boot_volume` joined them the same day, with the unit behind it.
#: Measured over two boots: the converter comes up at -20 dB of its own
#: accord, nothing carries a level across a boot, and nothing plays before
#: a renderer acquires - at which point ADR-0054 §5 sets the level from the
#: renderer itself (Finding 047 §10). ADR-0018's boot level is amended out.
DESIGN_KEYS_WE_DECLINED = {
    "weather_key", "idle_minmax", "per_renderer_volume", "boot_volume",
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
    assert design_keys - ours == DESIGN_KEYS_NOT_YET_IN_THE_REGISTRY | DESIGN_KEYS_WE_DECLINED
    # Every row below is one the 2026-09-20 drop stopped surfacing.
    # ADR-0022's amendment keeps them inventoried - George: "decisions. They
    # should still be kept on a list, but not used at this point in the
    # settings screen" - so they stay in the registry and gain
    # `surfaced: false` in 9d rather than being deleted.
    #
    # The four rows that used to be listed here as ours-only -
    # drawer_on_external, drawer_autohide, listenbrainz_token and fanart_key -
    # are in the design now; the drop adopted them.
    #
    # `wallpaper_topics`, `background_interval` and `background_brightness`
    # are 9g's, appended to ADR-0022's inventory on George's confirmation
    # (2026-09-21): Pixabay takes one category per request and the drop has
    # no row for which ones, for how often the picture changes, or for how
    # bright it is.
    assert ours - design_keys == {
        "api_loopback", "backup", "brightness",
        "confidence", "factory_reset", "idle_close", "image_build",
        "lms_player", "log_level", "plugins", "power", "release_ladder",
        "seek_reanchor", "spotify_name", "theme",
        # ADR-0055, 2026-09-23: the design has no output picker, because
        # the design did not know the device has four playback outputs and
        # that two of them cannot be turned down.
        "output_device",
        "background_brightness", "background_interval", "idle_clock",
        "time_display", "updates", "volume_managed", "wallpaper_topics",
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
    # a per-option warn on something that is not a choice
    with pytest.raises(ValueError, match="only for a choice"):
        load_registry(write(rows({"key": "a", "type": "toggle", "warn": {"x": "boom"}})))
    # a row-level warn on a row that takes no value: there is no sheet to
    # show it in (ADR-0044 §2, amended 2026-09-22)
    with pytest.raises(ValueError, match="takes a value"):
        load_registry(write(rows({"key": "a", "type": "readonly", "warn": "boom"})))
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
        # the string form: about the row, not about one of its values
        {"key": "e", "type": "text", "warn": "This one bites."},
    )))


def test_the_device_name_warning_says_what_this_device_does():
    """The 2026-09-22 drop gives `device_name` a warning that says saving
    *restarts the services*. **It does not**: ADR-0048 writes all four and
    applies none of them until the next restart, on purpose, so the drop's
    sentence would describe a device that does not exist. The mechanic is
    the design's; the wording is this device's."""
    row = next(r for r in _rows() if r["key"] == "device_name")
    assert isinstance(row["warn"], str)
    assert row["restart"] is True
    # George's own sentence, 2026-09-22.
    assert row["warn"] == "Change only takes place after a restart of the device."


def test_the_shipped_registry_hides_twenty_rows_and_shows_the_rest():
    rows = _rows()
    kept = [r for r in rows if r.get("surfaced") is False]
    assert len(kept) == 18, "ADR-0022's amendment: inventoried, not surfaced"
    # Every one of them is still served by the API.
    assert all(r.get("key") for r in kept)
    # 54 at the start of 9d, plus the two rows the design has and the plan
    # had given to nobody (56), plus 9g's eleven: the design's nine
    # idle-screen keys minus `weather_key`, which a key-free provider leaves
    # gating nothing (ADR-0047 §2a), plus `wallpaper_topics`,
    # `background_interval` and `background_brightness`, all asked for by
    # George on 2026-09-21. Then 9h's three: `viz_stop`, `home_strip` and
    # `home_strip_count`. Then `idle_clock`, asked for on 2026-09-22, and
    # `skin`, the picker's own row, which the same day's drop drew
    # (ADR-0051 §4). Less `idle_minmax`, which George removed the same day.
    # `restore_ceiling` was added and withdrawn the same day without ever
    # being surfaced (ADR-0052's amendment), so it leaves no trace here.
    # Less `restore_floor` and `boot_default_scope`, which George ruled out
    # of scope on 2026-09-23 ("The other 2 you flagged - not needed"):
    # both were [?] rows, decisions owed rather than behaviour missing, and
    # the behaviour behind them stays hardcoded. Less `per_renderer_volume`
    # too, deleted with the memory it switched on and off, and
    # `boot_volume`, deleted with the unit that read it. Plus
    # `output_device`, ADR-0055's own.
    assert len(rows) == 68
    assert len(rows) - len(kept) == 50


def test_the_clock_can_be_turned_off_without_taking_the_screen_with_it():
    """George, 2026-09-22: *"another entry for disabling the clock (with
    current day) on the idle screen. this way a user can actually use the
    panel as a photo frame only."*

    So it hangs off the built-in screen like the background and the weather,
    and off nothing else: a picture frame is this screen with one thing
    turned off, not a fourth kind of screen.
    """
    rows = {r["key"]: r for r in _rows()}
    clock = rows["idle_clock"]
    assert (clock["type"], clock["default"]) == ("toggle", True)
    assert clock["onlyWhen"] == ["idle_screen", "Built in"]
    values = {k: rows[k].get("default") for k in rows}
    assert visible(clock, rows, values)
    values["idle_screen"] = "External URL"
    assert not visible(clock, rows, values), "an external page replaces all of it"


def test_every_picture_background_carries_the_same_two_rows():
    """George, 2026-09-21: *"The picture rotation is not available for music
    library option. It should be common for all types that have a
    background: artists, online, or local media."*

    Brightness and rotation belong to *a picture*, and three of the four
    backgrounds are one. The Pixabay rows stay Pixabay's.
    """
    rows = {r["key"]: r for r in _rows()}
    values = {k: rows[k].get("default") for k in rows}
    for key in ("background_brightness", "background_interval"):
        assert rows[key]["onlyWhen"] == ["idle_background", {"not": "Black"}], key
        for background in ("Artist pictures", "Wallpapers online", "Wallpapers on device"):
            values["idle_background"] = background
            assert visible(rows[key], rows, values), f"{key} under {background}"
        values["idle_background"] = "Black"
        assert not visible(rows[key], rows, values), key
    # A key and a topic list are about the service, not about the picture.
    for key in ("wallpaper_key", "wallpaper_topics"):
        assert rows[key]["onlyWhen"] == ["idle_background", "Wallpapers online"], key


def test_a_row_can_be_shown_for_everything_but_one_value():
    """ADR-0044 §3, amended: `onlyWhen: [key, {"not": value}]`.

    George asked for background brightness *"that can apply to all background
    types except black"*. A list of the three that do apply would be right
    today and silently wrong the day a fifth background is added - the new
    one would have no brightness control and nothing would say why.
    """
    rows = {r["key"]: r for r in _rows()}
    brightness = rows["background_brightness"]
    assert brightness["onlyWhen"] == ["idle_background", {"not": "Black"}]
    values = {k: rows[k].get("default") for k in rows}
    for background in ("Artist pictures", "Wallpapers online", "Wallpapers on device"):
        values["idle_background"] = background
        assert visible(brightness, rows, values), background
    values["idle_background"] = "Black"
    assert not visible(brightness, rows, values)
    # And it is still transitive: an external screen hides the background
    # row, which hides this one whatever the background happens to hold.
    values["idle_background"] = "Wallpapers online"
    values["idle_screen"] = "External URL"
    assert not visible(brightness, rows, values)


def test_a_malformed_negation_fails_the_load():
    """A typo in the one key this form has would read as "not equal to
    nothing", which is every value - a row that never hides and never says
    why."""
    good = [{"id": "g", "label": "G", "rows": [
        {"key": "a", "type": "toggle", "default": True},
        {"key": "b", "type": "toggle", "default": True, "onlyWhen": ["a", {"not": False}]},
    ]}]
    bad = json.loads(json.dumps(good))
    bad[0]["rows"][1]["onlyWhen"] = ["a", {"nto": False}]
    with tempfile.TemporaryDirectory() as tmp:
        for registry, ok in ((good, True), (bad, False)):
            path = Path(tmp) / "r.json"
            path.write_text(json.dumps(registry))
            if ok:
                load_registry(path)
            else:
                with pytest.raises(ValueError):
                    load_registry(path)


def test_the_brightness_row_carries_the_designs_own_value():
    """0.62 is what the design dims a background to, and what its own
    comment does the contrast arithmetic for. The row starts there rather
    than at something rounder."""
    row = next(r for r in _rows() if r["key"] == "background_brightness")
    assert (row["type"], row["unit"], row["default"]) == ("number", "%", 62)
    assert (row["min"], row["max"]) == (20, 100)


def test_a_multi_holds_a_set_and_never_an_empty_one():
    """ADR-0044 §7. Three rules the panel must not be trusted with, because
    the phone reaches the same route: known options only, no duplicates, and
    **never empty** - no category means no picture, which is a broken screen
    rather than a weaker selection."""
    row = {"key": "m", "type": "multi", "options": ["Nature", "Animals", "Music"]}
    assert validate(row, ["Nature"]) == ["Nature"]
    # Stored in the registry's order, not the order they were tapped, so two
    # devices holding the same set read out the same words.
    assert validate(row, ["Music", "Nature"]) == ["Nature", "Music"]
    assert validate(row, ["Nature", "Nature"]) == ["Nature"]
    for bad in ([], ["Nope"], "Nature", [1], None, {}):
        with pytest.raises(InvalidValue):
            validate(row, bad)


def test_the_wallpaper_topics_row_offers_pixabays_own_categories():
    """ADR-0047 §2a: George chose categories over search terms - *"We start
    with categories and see later if we need to add queries too"* - so the
    options are Pixabay's twenty and nothing of ours. A word here that
    Pixabay does not have is a request that returns nothing, and the failure
    would look like an empty sky rather than like a typo."""
    pixabay = {
        "backgrounds", "fashion", "nature", "science", "education", "feelings",
        "health", "people", "religion", "places", "animals", "industry",
        "computer", "food", "sports", "transportation", "travel", "buildings",
        "business", "music",
    }
    row = next(r for r in _rows() if r["key"] == "wallpaper_topics")
    assert row["type"] == "multi"
    assert {o.lower() for o in row["options"]} == pixabay
    # A default that is empty would be a row the validator itself refuses.
    assert row["default"] == ["Nature"]


def test_every_weather_row_hangs_off_the_toggle_now_that_there_is_no_key():
    """ADR-0047 §2a: Open-Meteo needs no key, so `weather_key` is not in the
    registry and the four rows the design hung off it hang off `idle_weather`
    - which itself hangs off the built-in screen."""
    rows = {r["key"]: r for r in _rows()}
    assert "weather_key" not in rows
    for key in ("weather_location", "idle_forecast", "idle_icons"):
        assert rows[key]["onlyWhen"] == ["idle_weather", True], key
    assert rows["idle_weather"]["onlyWhen"] == ["idle_screen", "Built in"]
    # Transitively: an external URL hides all five, not just the toggle.
    values = {k: rows[k].get("default") for k in rows}
    values["idle_screen"] = "External URL"
    for key in ("idle_weather", "weather_location", "idle_forecast", "idle_icons"):
        assert not visible(rows[key], rows, values), key


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


# ── the derived options the picker lists (ADR-0051 §4) ───────────────────


def _skin_settings(store, offered, **kwargs):
    """The shipped registry, with the `skin` row's options coming from a
    stand-in for the installed corpus - which is what the daemon injects."""
    return Settings(store, options={"skin_corpus": lambda: list(offered)}, **kwargs)


def test_the_skin_row_offers_what_the_corpus_resolver_gives_it(store):
    settings = _skin_settings(store, ["01G5_Accuphase", "06G5_McIntosh"])
    row = next(
        r
        for g in settings.to_json()
        for r in g["rows"]
        if r.get("key") == "skin"
    )
    assert row["options"] == ["01G5_Accuphase", "06G5_McIntosh"]
    assert row["picker"] is True
    # The picker is for choosing *one* skin, so it is offered only when the
    # skin is not changing by itself.
    assert row["onlyWhen"] == ["skin_rotate", False]
    assert row["visible"] is False  # skin_rotate defaults to true


def test_a_skin_is_checked_against_the_corpus_and_not_against_the_registry(store):
    """The registry carries `"options": []` for this row - a literal check
    would refuse every skin there is."""
    settings = _skin_settings(store, ["01G5_Accuphase"], wired={"skin": None})
    assert settings.set("skin", "01G5_Accuphase") == "01G5_Accuphase"
    with pytest.raises(InvalidValue):
        settings.set("skin", "99G5_Not installed")


def test_a_settings_with_no_corpus_resolver_offers_no_skins(store):
    """A device whose corpus cannot be read has an empty picker, not a
    crash: the same shape as a `list` with no items (ADR-0044 §4)."""
    settings = Settings(store)
    row = next(r for g in settings.to_json() for r in g["rows"] if r.get("key") == "skin")
    assert row["options"] == []


def test_an_injected_resolver_has_to_name_a_source_that_exists(store):
    with pytest.raises(ValueError):
        Settings(store, options={"skin_korpus": list})


def _row(settings, key="output_mode"):
    return next(r for g in settings.to_json() for r in g["rows"] if r.get("key") == key)


def test_an_unavailable_option_is_greyed_not_hidden(store):
    """**ADR-0044's `unavailable`**, George 2026-09-23: *"while on outputs
    that do not support it, variable should be greyed out. I wouldn't hide
    this time as settings is different than the now playing screen when it
    comes to capabilities."*

    The opposite of the now-playing rule, on purpose: a screen for changing
    things should say what cannot be changed and why."""
    settings = Settings(store, wired={"output_mode": None})
    settings.set("output_mode", "Variable")

    settings.restrict("output_mode", {"Variable": "HDMI 1 has no volume control."})

    row = _row(settings)
    assert row["options"] == ["Variable", "Fixed"]  # both still offered
    assert row["unavailable"] == {"Variable": "HDMI 1 has no volume control."}
    assert row["value"] == "Fixed"  # what is in force
    with pytest.raises(Locked):
        settings.set("output_mode", "Variable")


def test_the_stored_choice_is_untouched_and_comes_back(store):
    """*"When changing back to dac set the previously selected option."*
    The restriction sits **over** the store and never replaces it."""
    settings = Settings(store, wired={"output_mode": None})
    settings.set("output_mode", "Variable")
    settings.restrict("output_mode", {"Variable": "no volume control here"})
    assert settings.value("output_mode") == "Fixed"

    settings.restrict("output_mode", {})

    assert settings.value("output_mode") == "Variable"


def test_with_no_previous_choice_the_rows_own_default_answers(store):
    """*"If there is no previous selection default to variable."*"""
    settings = Settings(store, wired={"output_mode": None})
    settings.restrict("output_mode", {"Variable": "no volume control here"})
    settings.restrict("output_mode", {})

    assert settings.value("output_mode") == "Variable"


def test_a_choice_a_user_had_already_made_is_still_settable(store):
    """Only the greyed option is refused, not the row."""
    settings = Settings(store, wired={"output_mode": None})
    settings.restrict("output_mode", {"Variable": "no volume control here"})

    assert settings.set("output_mode", "Fixed") == "Fixed"


def test_a_row_with_nothing_greyed_carries_no_field(store):
    settings = Settings(store, wired={"output_mode": None})
    assert "unavailable" not in _row(settings)
