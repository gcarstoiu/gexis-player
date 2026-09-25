# SPDX-License-Identifier: GPL-3.0-or-later
"""**A plugin's settings reach its unit as environment** (ADR-0088).

ADR-0084 gives a plugin a socket and a line protocol, and that is the right
channel for a plugin written against this contract. **A third-party binary will
never speak it** - the Beszel agent is one, Plexamp is another, and so is
anything else worth plugging in that already exists. A contract that can only
configure programs written for it is a renderer API wearing a plugin's name.

So: a manifest row may name an environment variable, and every such row is
exported to one file the plugin's unit reads with `EnvironmentFile=`. The core
learns nothing about the program it is configuring - a name and a string, no
format - and the image already does exactly this for one value, ADR-0048's
`GEXIS_DEVICE_NAME`.

`/run` and not `/etc`: the file is derived from the settings store, it holds
secrets, and a reboot should rebuild it rather than leave a stale credential on
disk.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("gexis_core.plugin_env")

#: tmpfs, so nothing here outlives a reboot. The daemon runs as root and this
#: directory is its own; a plugin's unit reads the file, it does not write one.
RUN_DIR = Path("/run/gexis/plugins")

#: What `EnvironmentFile=` can carry as a name. Not uppercase-only: the
#: convention is not universal and a manifest naming a variable this core
#: refuses would be a plugin nobody could configure.
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def path(plugin_id: str, *, directory: Path = RUN_DIR) -> Path:
    return directory / f"{plugin_id}.env"


def quote(value: str) -> str:
    r"""One `EnvironmentFile` value, double-quoted.

    **The values are not safe.** A hub's public key is
    `ssh-ed25519 AAAA... comment` - spaces, and systemd would read everything
    after the first one as a second assignment. Double quotes with `\` and `"`
    escaped is systemd's own documented form for this.
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def as_text(value: Any) -> str | None:
    """The string a program should see, or None to write no line at all.

    **An absent value is an absent variable**, not an empty one: to most
    programs those differ, and *not configured* is the honest statement.
    `False` is a written `false` rather than nothing, because a toggle that is
    off is a decision and a program that reads it should see it.
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def render(plugin, values: dict[str, Any]) -> str:
    """The file's contents for one plugin, given the registry's current values.

    `values` is keyed as the registry stores them - `<id>.<key>` - because that
    is what the caller has; the variable name comes from the row.
    """
    lines = []
    for row in plugin.settings:
        name = row.get("env")
        key = row.get("key")
        if not name or not key:
            continue
        text = as_text(values.get(f"{plugin.id}.{key}"))
        if text is None:
            continue
        if "\n" in text or "\r" in text:
            # No `EnvironmentFile` line can carry a newline, and silently
            # truncating a credential is worse than not writing it: the plugin
            # fails to authenticate and nothing says why.
            logger.warning(
                "plugins: %s's %s contains a newline and cannot be exported", plugin.id, key,
            )
            continue
        lines.append(f"{name}={quote(text)}\n")
    return "".join(lines)


def write(plugin, values: dict[str, Any], *, directory: Path = RUN_DIR) -> bool:
    """Write the file. True if its contents changed.

    The answer is what decides whether the unit is restarted: environment is
    read once at exec, so a changed value means a restart, and an unchanged one
    must not - a settings screen that bounces a running service on every
    unrelated write is worse than one that does nothing.

    Written and renamed rather than truncated in place: a unit starting while
    this runs gets the old file or the new one, never half of one.
    """
    wanted = render(plugin, values)
    target = path(plugin.id, directory=directory)
    try:
        current = target.read_text()
    except OSError:
        current = None
    if current == wanted:
        return False
    directory.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(".env.new")
    # 0600 before anything is in it, not after: the window between a
    # world-readable create and a chmod is the whole of what mode is for here.
    handle = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(handle, "w") as out:
            out.write(wanted)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    os.replace(temp, target)
    logger.info("plugins: %s environment written (%d variable(s))",
                plugin.id, len(wanted.splitlines()))
    return True


def has_env(plugin) -> bool:
    """Whether this plugin exports anything at all. A plugin with no `env` row
    never gets a file, so its unit's `EnvironmentFile=-` finds nothing and that
    is correct rather than missing."""
    return any(row.get("env") and row.get("key") for row in plugin.settings)
