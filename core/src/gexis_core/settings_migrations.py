# SPDX-License-Identifier: GPL-3.0-or-later
"""**Settings move forward with the code** (ADR-0105 §5, Phase 13c step 4).

An update replaces the code and keeps `settings.db`. A release that renames a
setting, removes one, or changes what its values mean must also carry what
moves the value a device has stored - or the device keeps a value nothing
reads, and the user's choice silently goes back to the default.

**How:** `MIGRATIONS` is an ordered list; the store records how many have
run (`SCHEMA_KEY`), and `migrate` runs the rest at the core's start, before
anything reads a setting. A device restoring an older backup is migrated on
the reboot that follows every restore.

**What makes it hold** (LESSONS 19-20: the checks that only ran in
production): `SHIPPED_KEYS` is every setting key a release has shipped. The
registry tests fail when a key leaves the registry without a migration that
renames or drops it here, and when the registry gains a key not added to
`settings_shipped_keys.json`. Plugins' keys (`<id>.<key>`) come and go with
the plugin and are not tracked.

**A migration is never removed or edited once shipped**: a device may be
several releases behind, and runs every one it has not run, in order.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("gexis_core.settings_migrations")

#: Where the store records how many migrations have run. Not a setting: no
#: row names it, and the settings API never lists it.
SCHEMA_KEY = "_settings_schema"

SHIPPED_KEYS_PATH = Path(__file__).with_name("settings_shipped_keys.json")


@dataclass(frozen=True)
class Migration:
    """One step. `renames` and `drops` are what it does to keys, declared so
    the tests can see that every key that left the registry was handled;
    `run` does it."""

    note: str
    run: Callable[[Any], None]
    renames: dict[str, str] = field(default_factory=dict)
    drops: frozenset[str] = frozenset()


def rename(old: str, new: str, note: str,
           convert: Callable[[Any], Any] | None = None) -> Migration:
    """`old`'s stored value moves to `new` (converted if a function is given);
    a value already stored under `new` wins and `old` is dropped."""
    def run(store) -> None:
        value = store.get(old)
        if value is None:
            return
        if store.get(new) is None:
            store.set(new, convert(value) if convert else value)
        store.delete(old)
    return Migration(note=note, run=run, renames={old: new})


def drop(key: str, note: str) -> Migration:
    """A setting no release reads any more: its stored value goes."""
    return Migration(note=note, run=lambda store: store.delete(key), drops=frozenset({key}))


def convert(key: str, change: Callable[[Any], Any], note: str) -> Migration:
    """The same key, its stored value in a new form."""
    def run(store) -> None:
        value = store.get(key)
        if value is not None:
            store.set(key, change(value))
    return Migration(note=note, run=run)


#: In the order they shipped. Append only.
MIGRATIONS: tuple[Migration, ...] = (
    # George, on the Settings copy review (2026-10-05): the forecast's
    # second layout still shows today's weather, so it is not "None".
    convert("idle_forecast", lambda v: "Today only" if v == "None" else v,
            "idle_forecast: None is called Today only"),
    # George, trying the touchpad (2026-10-05): "50 is way too slow" - the
    # range is 150 to 400 now. A slower speed kept from a preview is raised.
    convert("pointer_speed", lambda v: max(150, v) if isinstance(v, (int, float)) else v,
            "pointer_speed: at least 150 %"),
)


def migrate(store, migrations: tuple[Migration, ...] = MIGRATIONS) -> int:
    """Run what this store has not run. Returns how many ran."""
    done = store.get(SCHEMA_KEY, 0)
    if not isinstance(done, int) or done < 0:
        logger.warning("settings: %s is %r, not a count; treating it as 0", SCHEMA_KEY, done)
        done = 0
    if done > len(migrations):
        # A store written by a newer release, under an older one - an older
        # image with a newer backup restored. Nothing here knows those steps;
        # the keys this release does not read are left for when it is newer.
        logger.warning("settings: the store is at %d migrations, this release knows %d; leaving it as it is",
                       done, len(migrations))
        return 0
    for number, step in enumerate(migrations[done:], start=done + 1):
        step.run(store)
        store.set(SCHEMA_KEY, number)
        logger.info("settings: migration %d - %s", number, step.note)
    return len(migrations) - done


def shipped_keys(path: Path = SHIPPED_KEYS_PATH) -> set[str]:
    return set(json.loads(path.read_text()))
