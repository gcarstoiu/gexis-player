# SPDX-License-Identifier: GPL-3.0-or-later
"""The settings registry and its API behaviour (ADR-0035).

`settings_registry.json` is the executable form of ADR-0022's inventory,
keyed by the design's own keys. A row is *wired* when some feature reads its
value; only wired rows accept writes. Adding a setting is one row here plus
the code that reads it, in the same change as its feature.
"""
from __future__ import annotations

import json
import logging
import math
from functools import lru_cache
from pathlib import Path
from collections.abc import Hashable
from typing import Any, Callable

from gexis_core.settings import SettingsStore

REGISTRY_PATH = Path(__file__).with_name("settings_registry.json")
SEED_PATH = Path("/etc/gexis/settings-seed.json")

#: `list` is settable in the sense that tapping an item chooses one, but it
#: never takes a scalar through the API: its items come from discovery, not
#: from the store (ADR-0044 §1). It is therefore in TYPES and not in SETTABLE
#: - except for `kind: "server"`, which `validate` admits on its own; see
#: there for why one shape of list stores a value and the others do not.
SETTABLE = {"toggle", "choice", "number", "text", "multi"}
TYPES = SETTABLE | {"readonly", "action", "group", "list"}
TEXT_MAX = 500

#: `onlyWhen: [key, value]` hides a row unless that key holds that value.
#: ANY means "holds anything non-empty" - the sentinel the design writes as
#: `{ any: true }` and the API carries as this string, because JSON has no
#: symbol and a bare `true` would be indistinguishable from a toggle's value.
ONLY_WHEN_ANY = "*any*"

#: `onlyWhen: [key, {"not": value}]` - shown unless the key holds *that*
#: value (ADR-0044 §3, amended 2026-09-21 for `background_brightness`, which
#: George asked to apply to *"all background types except black"*).
#:
#: **A negation rather than a list of the three that do apply.** The list
#: would be right today and wrong the day a fifth background is added, and
#: wrong silently - the new background would simply have no brightness
#: control and nothing would say why. An object rather than another string
#: sentinel because a setting's value is always a scalar, so this cannot be
#: mistaken for one.
ONLY_WHEN_NOT = "not"

#: Sources a `choice` may draw its options from instead of a literal list
#: (ADR-0044 §4). Adding one is a code change, not a registry edit, which is
#: the point: an unknown name is a typo and must fail the load.
OPTION_SOURCES = {"skin_corpus", "timezones", "output_device"}


@lru_cache(maxsize=1)
def _timezones() -> tuple[str, ...]:
    """Every zone this system knows, which is the honest list. The design
    curates about thirty-five and a user outside them cannot set their
    clock; `grouped` is what makes the full set navigable instead.

    Cached: it is a scan of the tzdata directory and it is read on every
    `GET /settings`, where nothing on the request path should be doing
    filesystem work it could have done once."""
    try:
        from zoneinfo import available_timezones
    except ImportError:  # pragma: no cover - stdlib since 3.9
        return ()
    return tuple(sorted(available_timezones()))


#: What each source resolves to, called when the payload is built. A source
#: with nothing behind it yet resolves to an empty list: the row is drawn,
#: has nothing to offer, and says so - the same shape as a `list` with no
#: items (ADR-0044 §4).
#:
#: **`skin_corpus` has no default resolver on purpose.** The skins it offers
#: depend on where the corpus is installed *and* on another row's current
#: value, neither of which this module knows; the daemon injects it
#: (`Settings(options=...)`, ADR-0051 §4) and a Settings built without one
#: offers nothing, which is what a device with no skins has.
#: `tuple` is "nothing, until the daemon injects a real resolver" - a
#: device that cannot read its corpus or its sound cards gets an empty
#: picker rather than a crash (ADR-0044 §4).
OPTION_RESOLVERS = {"timezones": _timezones, "skin_corpus": tuple, "output_device": tuple}

logger = logging.getLogger("gexis_core.settings_registry")


class UnknownSetting(KeyError):
    pass


class NotWired(Exception):
    pass


class InvalidValue(ValueError):
    pass


class NotSettable(Exception):
    pass


def load_registry(path: Path = REGISTRY_PATH) -> list[dict]:
    return check(json.loads(path.read_text()))


def check(groups: list[dict]) -> list[dict]:
    """Every rule a row has to satisfy, whoever wrote it.

    **Split out of `load_registry` on 2026-09-25 so a plugin's rows go through
    the same door** (ADR-0086). A plugin is written elsewhere, by somebody who
    cannot test against this device, and the alternative to validating its
    rows is a Settings screen that draws something nobody checked.
    """
    seen: set[str] = set()
    for group in groups:
        for row in group["rows"]:
            kind = row["type"]
            if kind not in TYPES:
                raise ValueError(f"{row}: unknown row type {kind!r}")
            if kind == "group":
                continue
            key = row["key"]
            if key in seen:
                raise ValueError(f"duplicate setting key {key!r}")
            seen.add(key)
            if kind == "number" and ("min" not in row or "max" not in row):
                raise ValueError(f"{key}: a number row needs min and max (ADR-0035)")
            if kind == "choice" and not (row.get("options") or row.get("optionsFrom")):
                raise ValueError(f"{key}: a choice row needs options or optionsFrom")
            source = row.get("optionsFrom")
            if source is not None and source not in OPTION_SOURCES:
                raise ValueError(f"{key}: unknown optionsFrom {source!r}")
            warn = row.get("warn")
            if warn is not None:
                # ADR-0044 §2, amended 2026-09-22 for `device_name`: **two
                # forms**. A string warns about the row - it is shown
                # whenever the sheet is open, because what it describes
                # happens whatever is typed. An object warns about one
                # option and appears when that option is picked, which only
                # a choice has.
                if isinstance(warn, str):
                    if kind not in SETTABLE:
                        raise ValueError(f"{key}: warn is for a row that takes a value")
                elif kind != "choice":
                    raise ValueError(f"{key}: a per-option warn is only for a choice row")
                else:
                    unknown = set(warn) - set(row.get("options") or ())
                    if unknown:
                        raise ValueError(f"{key}: warn names options that do not exist: {sorted(unknown)}")
            only = row.get("onlyWhen")
            if only is not None and (not isinstance(only, list) or len(only) != 2):
                raise ValueError(f"{key}: onlyWhen is [key, value]")
            if only is not None and isinstance(only[1], dict) and set(only[1]) != {ONLY_WHEN_NOT}:
                # A typo in the one key this form has would otherwise read as
                # "not equal to nothing", which is every value, which is a row
                # that never hides and never says why.
                raise ValueError(f"{key}: onlyWhen's object form is {{\"not\": value}}")

    # Deferred to a second pass: a row may depend on one declared after it.
    keys = {r["key"] for g in groups for r in g["rows"] if r["type"] != "group"}
    for group in groups:
        for row in group["rows"]:
            only = row.get("onlyWhen")
            if only is not None and only[0] not in keys:
                raise ValueError(f"{row['key']}: onlyWhen names unknown setting {only[0]!r}")
    return groups


def visible(row: dict, rows: dict[str, dict], values: dict[str, Any]) -> bool:
    """Whether a row is shown, given every row and every current value.

    Two reasons a row can be absent from the screen and present in the API
    (ADR-0044 §3, §6): `surfaced: false` is permanent - the row is inventoried
    and not offered - and `onlyWhen` is conditional. **The API publishes both
    regardless; the panel filters**, so a phone and the panel agree without
    the daemon knowing which is asking.

    **The test is transitive.** A row whose dependency is itself hidden is
    hidden too: a condition on something nobody can see cannot be satisfied on
    purpose, and showing the dependant would offer a setting whose reason for
    existing is invisible. Every weather row depends on `idle_weather`, which
    depends on `idle_screen` being the built-in one - choosing an external URL
    has to take all five weather rows with it, not just the toggle.

    A cycle would otherwise recurse forever; `seen` makes one resolve to
    hidden rather than crashing the daemon, and the load-time check cannot
    catch it because each link is individually valid.
    """
    return _visible(row, rows, values, set())


def _visible(row: dict, rows: dict[str, dict], values: dict[str, Any], seen: set[str]) -> bool:
    if row.get("surfaced") is False:
        return False
    only = row.get("onlyWhen")
    if only is None:
        return True
    key, wanted = only
    if key in seen:
        logger.warning("settings: onlyWhen cycle at %r; hiding the row", key)
        return False
    parent = rows.get(key)
    if parent is not None and not _visible(parent, rows, values, seen | {row.get("key", "")}):
        return False
    held = values.get(key)
    if wanted == ONLY_WHEN_ANY:
        return held not in (None, "", False)
    if isinstance(wanted, dict):
        return held != wanted[ONLY_WHEN_NOT]
    return held == wanted


def validate(row: dict, value: Any, *, options: Any = None) -> Any:
    kind = row["type"]
    if kind == "list":
        # ADR-0044 §1 draws the line inside the type: a Wi-Fi or Bluetooth
        # list is navigation and its readout is derived ("4 paired"), while a
        # server list *"sets the value"* when an item is tapped - the address
        # is the setting. Same sheet, same items, one of them stores.
        if row.get("kind") != "server":
            raise NotSettable(f"{row['key']} is a list and takes no value")
        if not isinstance(value, str) or not value.strip():
            raise InvalidValue("expected an address")
        return value.strip()[:TEXT_MAX]
    if kind not in SETTABLE:
        raise NotSettable(f"{row['key']} is {kind} and takes no value")
    if kind == "toggle":
        if not isinstance(value, bool):
            raise InvalidValue("expected true or false")
    elif kind == "choice":
        # A derived choice is checked against what the source offers now,
        # not against the empty literal the registry carries (ADR-0044 §4).
        source = row.get("optionsFrom")
        if options is None:
            options = OPTION_RESOLVERS[source]() if source else row["options"]
        if value not in options:
            raise InvalidValue(
                f"expected one of {options}" if len(options) < 12 else "not an available option"
            )
    elif kind == "multi":
        # ADR-0044 §7. A set, with three rules the row would otherwise have
        # to trust the panel for: known options only, **never empty** -
        # no category means no picture, which is a broken screen rather
        # than a weaker selection - and stored in the registry's order so
        # the readout is stable whatever order they were tapped in.
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise InvalidValue("expected a list of options")
        options = row["options"]
        unknown = [v for v in value if v not in options]
        if unknown:
            raise InvalidValue(f"not an option: {unknown[0]}")
        chosen = [o for o in options if o in value]
        if not chosen:
            raise InvalidValue("at least one has to stay selected")
        return chosen
    elif kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise InvalidValue("expected a number")
        if not row["min"] <= value <= row["max"]:
            raise InvalidValue(f"expected {row['min']} to {row['max']}")
    elif kind == "text":
        if not isinstance(value, str):
            raise InvalidValue("expected text")
        value = value.strip()
        if len(value) > TEXT_MAX:
            raise InvalidValue(f"at most {TEXT_MAX} characters")
    return value


def load_seed(settings_rows: dict[str, dict], path: Path = SEED_PATH) -> dict[str, Any]:
    """Settings chosen at flash time (`make provision`). Treated as defaults,
    so a later change from a phone still wins. A seed is written by hand, so
    every entry is checked and a bad one is dropped with a log line rather
    than taking the daemon down."""
    try:
        seed = json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        logger.warning("settings: ignoring %s: %s", path, exc)
        return {}
    if not isinstance(seed, dict):
        logger.warning("settings: ignoring %s: expected an object", path)
        return {}
    checked = {}
    for key, value in seed.items():
        row = settings_rows.get(key)
        if row is None:
            logger.warning("settings: %s has unknown setting %r", path, key)
            continue
        try:
            checked[key] = validate(row, value)
        except (InvalidValue, NotSettable) as exc:
            logger.warning("settings: %s: %s is invalid: %s", path, key, exc)
    return checked


#: **ADR-0044 §8, added 2026-09-23.** Raised when an option exists but the
#: hardware cannot honour it right now.
#:
#: The first version locked the whole *row*, which George corrected:
#: *"while on outputs that do not support it, variable should be greyed
#: out. I wouldn't hide this time as settings is different than the now
#: playing screen when it comes to capabilities."* So the row opens, both
#: options are drawn, and the one that cannot be had is greyed with its
#: reason - **the opposite of the now-playing rule, on purpose**: a screen
#: for changing things should show what could be changed and why it
#: cannot, where a screen for listening should not carry dead controls.
class Locked(Exception):
    pass


class Settings:
    """`defaults` maps a key to a callable giving its value from deployment
    config or the running system. Precedence, highest first (ADR-0035 §4): a
    stored value, the flash-time seed, a `defaults` callable, the registry's
    own default."""

    @staticmethod
    def with_plugins(registry: list[dict], plugins) -> list[dict]:
        """**A plugin's rows, merged into the registry** (ADR-0086).

        A renderer's rows land in `sources`, under a sub-heading carrying its
        own name - the same shape LMS, Spotify and Bluetooth already have, so
        a fourth renderer reads like the three rather than like an appendix.

        **Keys are prefixed with the plugin's id.** Two plugins both shipping
        an `enabled` row would otherwise collide, and the second would be
        refused at load with a duplicate-key error nobody could act on. A
        plugin writes `enabled` and the registry holds `plexamp.enabled`.

        Rows that fail the registry's own rules are dropped with the reason
        logged, not raised: one badly packaged plugin must not stop the
        others, nor the device.
        """
        merged = [dict(g, rows=list(g["rows"])) for g in registry]
        by_id = {g.get("id"): g for g in merged}
        for plugin in plugins:
            if not plugin.settings and plugin.enabled_row is not None:
                # Nothing to add: its rows are the registry's already.
                continue
            target = by_id.get("sources" if plugin.kind == "renderer" else "system")
            if target is None:
                continue
            rows = [{"type": "group", "label": plugin.name, "accent": plugin.accent}]
            if plugin.enabled_row is None:
                # **Every plugin can be switched off** (ADR-0086 as amended).
                # Not something a plugin declares, because a plugin that
                # forgot to would be one nobody could turn off - and
                # "installed, started, kept running and switched off again" is
                # the whole of what `docs/DEVELOPMENT.md` says a service
                # wants. A manifest naming an existing row opts out, which is
                # how the built-ins keep the keys they have always had.
                rows.append({"key": f"{plugin.id}.enabled", "type": "toggle",
                             "label": "Enabled", "default": True})
            reserved = {"enabled"} if plugin.enabled_row is None else set()
            for row in plugin.settings:
                row = dict(row)
                if not row.get("key"):
                    logger.warning("plugins: %s has a row with no key", plugin.id)
                    continue
                if row["key"] in reserved:
                    # **`enabled` is the core's.** A plugin shipping its own
                    # would collide with the switch it gets for free, and
                    # dropping the whole plugin over one row would cost it
                    # every other setting it has. The switch wins, because a
                    # plugin nobody can turn off is the thing this exists to
                    # prevent.
                    logger.warning(
                        "plugins: %s declares %r, which is the core's own switch - "
                        "ignoring the plugin's and keeping the switch",
                        plugin.id, row["key"],
                    )
                    continue
                row["key"] = f"{plugin.id}.{row['key']}"
                only = row.get("onlyWhen")
                if isinstance(only, list) and len(only) == 2 and isinstance(only[0], str):
                    # **A manifest's `onlyWhen` names the plugin's own rows**
                    # (ADR-0088), prefixed exactly as `key` is - `enabled`
                    # becomes `beszel.enabled`, which is the switch ADR-0086
                    # synthesised, and that is what makes George's *"when
                    # enabled fields appear"* work. Unconditional rather than
                    # "unless it looks like a core key": a plugin able to
                    # depend on a core row would be coupled to a registry it
                    # does not ship with, and the breakage would arrive the day
                    # that key was renamed.
                    row["onlyWhen"] = [f"{plugin.id}.{only[0]}", only[1]]
                rows.append(row)
            try:
                check([{"id": "check", "label": "check", "rows": rows}])
            except (ValueError, KeyError) as exc:
                logger.warning("plugins: %s's settings are not usable: %s", plugin.id, exc)
                continue
            target["rows"].extend(rows)
        return merged

    def __init__(
        self,
        store: SettingsStore,
        *,
        registry: list[dict] | None = None,
        defaults: dict[str, Callable[[], Any]] | None = None,
        wired: dict[str, Callable[[Any], None] | None] | None = None,
        lists: set[str] | None = None,
        on_change: Callable[[], None] | None = None,
        options: dict[str, Callable[[], Any]] | None = None,
        seed_path: Path = SEED_PATH,
    ) -> None:
        self._store = store
        self._groups = registry if registry is not None else load_registry()
        self._rows = {r["key"]: r for g in self._groups for r in g["rows"] if r["type"] != "group"}
        self._defaults = defaults or {}
        self._wired = wired or {}
        #: **`list` rows that act through their own route** rather than
        #: through `set` - `POST /settings/{key}/items` (ADR-0044 §1). They
        #: are wired in the only sense the word has here, "something acts on
        #: it", and until 2026-09-25 they reported `wired: false` and the
        #: panel marked them `data-unwired`. That is Phase 9 criterion 2's
        #: own mechanism lying about two rows that work: `wifi` joins a
        #: network and `bt_trusted` forgets a device.
        #:
        #: Declared rather than inferred from `type == "list"`, because a
        #: future list row with no handler behind it must still report
        #: itself unwired. `set` keeps refusing all of them - a list row is
        #: not written by writing a value.
        self._lists = set(lists or ())
        # An injected resolver wins over the module's, because only the
        # daemon knows where the corpus is and what the other row holds
        # (ADR-0051 §4).
        self._options = {**OPTION_RESOLVERS, **(options or {})}
        #: key -> {option: why}, for choices the hardware cannot honour.
        #: Injected by the daemon, because only it knows what the sound
        #: card can do.
        self._unavailable: dict[str, dict[Any, str]] = {}
        unknown_sources = set(options or ()) - OPTION_SOURCES
        if unknown_sources:
            raise ValueError(f"not an option source: {sorted(unknown_sources)}")
        self._on_change = on_change
        self._seed = load_seed(self._rows, seed_path)
        unknown = (set(self._defaults) | set(self._wired) | self._lists) - set(self._rows)
        if unknown:
            raise ValueError(f"not in the registry: {sorted(unknown)}")
        not_lists = {k for k in self._lists if self._rows[k]["type"] != "list"}
        if not_lists:
            raise ValueError(f"declared as list rows but are not: {sorted(not_lists)}")

    def row(self, key: str) -> dict:
        try:
            return self._rows[key]
        except KeyError:
            raise UnknownSetting(key) from None

    def restrict(self, key: str, unavailable: dict[Any, str]) -> None:
        """Grey out options the hardware cannot honour, or clear the set by
        passing an empty one.

        **The stored value is never touched**, which is what makes handing
        the choice back free. George: *"When changing back to dac set the
        previously selected option. If there is no previous selection
        default to variable."* - the first is the store, still there; the
        second is the row's own default.
        """
        self.row(key)
        if unavailable:
            self._unavailable[key] = dict(unavailable)
        else:
            self._unavailable.pop(key, None)

    def value(self, key: str) -> Any:
        row = self.row(key)
        blocked = self._unavailable.get(key)
        if blocked:
            # What is in force, which is not what is stored: the stored
            # choice is waiting for the hardware that can honour it.
            stored = self._value(key)
            if stored in blocked:
                for option in row.get("options") or ():
                    if option not in blocked:
                        return option
            return stored
        return self._value(key)

    def _value(self, key: str) -> Any:
        row = self.row(key)
        stored = self._store.get(key, _MISSING)
        if stored is not _MISSING:
            return stored
        if key in self._seed:
            return self._seed[key]
        if key in self._defaults:
            return self._defaults[key]()
        return row.get("default")

    def to_json(self) -> list[dict]:
        """Every row, including the ones the screen will not draw.

        ADR-0044 §6: **the API publishes the row, the panel filters.** The
        rule itself stays here - it is transitive and cycle-sensitive, and one
        tested implementation beats the same recursion written twice - so each
        row carries the answer as `visible` and the panel does nothing but
        obey it. A client that wants the whole inventory (ADR-0022's
        catalogue) still has it.
        """
        values = {key: self.value(key) for key in self._rows}
        groups = []
        for group in self._groups:
            rows = []
            for row in group["rows"]:
                if row["type"] == "group":
                    rows.append(row)
                    continue
                public = {k: v for k, v in row.items() if k != "default"}
                source = row.get("optionsFrom")
                if source is not None:
                    public["options"] = list(self._options.get(source, tuple)())
                public["value"] = self.value(row["key"])
                # A row is wired when something acts on it. For most that is
                # a `set` callback; for a `list` it is the items route.
                public["wired"] = row["key"] in self._wired or row["key"] in self._lists
                blocked = self._unavailable.get(row["key"])
                if blocked:
                    public["unavailable"] = dict(blocked)
                public["visible"] = visible(row, self._rows, values)
                rows.append(public)
            groups.append({**group, "rows": rows})
        return groups

    def set(self, key: str, value: Any) -> Any:
        row = self.row(key)
        # `validate` owns the question of what takes a value: a server list
        # does, every other list does not, and the rest follow SETTABLE.
        if row["type"] not in SETTABLE and row["type"] != "list":
            raise NotSettable(f"{key} is {row['type']} and takes no value")
        if row["type"] == "list" and row.get("kind") != "server":
            raise NotSettable(f"{key} is a list and takes no value")
        if key not in self._wired:
            raise NotWired(f"{key} is not wired yet")
        # `multi` rows take a list, which is not a dict key - and a list is
        # never an option anyway.
        blocked = self._unavailable.get(key) or {}
        if isinstance(value, Hashable) and value in blocked:
            raise Locked(blocked[value])
        source = row.get("optionsFrom")
        value = validate(row, value, options=list(self._options[source]()) if source else None)
        if value == "" and row["type"] == "text":
            # Clearing a text value falls back to deployment config (ADR-0035 §4).
            self._store.delete(key)
            value = self.value(key)
        else:
            self._store.set(key, value)
        callback = self._wired[key]
        if callback is not None:
            callback(value)
        if self._on_change is not None:
            self._on_change()
        return value

    def run(self, key: str) -> None:
        row = self.row(key)
        if row["type"] != "action":
            raise NotSettable(f"{key} is {row['type']}, not an action")
        if key not in self._wired:
            raise NotWired(f"{key} is not wired yet")
        callback = self._wired[key]
        if callback is not None:
            callback(None)


_MISSING = object()
