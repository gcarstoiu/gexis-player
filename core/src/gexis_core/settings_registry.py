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
#: value (ADR-0044 §3, amended 2026-09-21 for `idle_brightness`, which
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
OPTION_SOURCES = {"skin_corpus", "timezones"}


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
#: items (ADR-0044 §4). `skin_corpus` gets its corpus in 9h.
OPTION_RESOLVERS = {"timezones": _timezones, "skin_corpus": tuple}

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
    groups = json.loads(path.read_text())
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
            if row.get("warn") is not None:
                if kind != "choice":
                    raise ValueError(f"{key}: warn is only for a choice row")
                unknown = set(row["warn"]) - set(row.get("options") or ())
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


def validate(row: dict, value: Any) -> Any:
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


class Settings:
    """`defaults` maps a key to a callable giving its value from deployment
    config or the running system. Precedence, highest first (ADR-0035 §4): a
    stored value, the flash-time seed, a `defaults` callable, the registry's
    own default."""

    def __init__(
        self,
        store: SettingsStore,
        *,
        registry: list[dict] | None = None,
        defaults: dict[str, Callable[[], Any]] | None = None,
        wired: dict[str, Callable[[Any], None] | None] | None = None,
        on_change: Callable[[], None] | None = None,
        seed_path: Path = SEED_PATH,
    ) -> None:
        self._store = store
        self._groups = registry if registry is not None else load_registry()
        self._rows = {r["key"]: r for g in self._groups for r in g["rows"] if r["type"] != "group"}
        self._defaults = defaults or {}
        self._wired = wired or {}
        self._on_change = on_change
        self._seed = load_seed(self._rows, seed_path)
        unknown = (set(self._defaults) | set(self._wired)) - set(self._rows)
        if unknown:
            raise ValueError(f"not in the registry: {sorted(unknown)}")

    def row(self, key: str) -> dict:
        try:
            return self._rows[key]
        except KeyError:
            raise UnknownSetting(key) from None

    def value(self, key: str) -> Any:
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
                    public["options"] = list(OPTION_RESOLVERS[source]())
                public["value"] = self.value(row["key"])
                public["wired"] = row["key"] in self._wired
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
        value = validate(row, value)
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
