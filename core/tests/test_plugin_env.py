# SPDX-License-Identifier: GPL-3.0-or-later
"""**ADR-0088: a plugin's settings reach its unit as environment.**

The case this exists for is a third-party binary that will never speak
ADR-0084's protocol. So the tests are about the file: is it a file systemd can
read, does it keep a secret at 0600, and does it say *nothing* rather than
something empty when a value has not been given.

**The quoting below was verified against real systemd, not against my reading of
its manual.** These tests assert the bytes this module chooses, which is only
half the claim. On the device, 2026-09-25, those bytes were handed to
`systemd-run --property=EnvironmentFile=` and the process's own `os.environ`
compared against the input: seven values - spaces, `"`, `\\`, `\\"`, `$$`, a
backtick and a single quote - all came back byte for byte
([Finding 079](../../docs/findings/079-what-the-plugin-contract-carries-to-a-unit.md)).
"""
from __future__ import annotations

import stat

import pytest

from gexis_core import plugin_env
from gexis_core.plugins import parse


def _plugin(rows, **over):
    return parse({"id": "beszel", "name": "Beszel", "kind": "service",
                  "unit": "beszel-agent.service", "settings": rows, **over})


def test_a_row_with_env_becomes_a_line(tmp_path):
    plugin = _plugin([{"key": "hub", "env": "HUB_URL"}])
    assert plugin_env.write(plugin, {"beszel.hub": "http://h:8090"}, directory=tmp_path)
    assert (tmp_path / "beszel.env").read_text() == 'HUB_URL="http://h:8090"\n'


def test_a_row_without_env_is_not_exported(tmp_path):
    """Most rows are the panel's business. Only the ones that name a variable
    are the unit's."""
    plugin = _plugin([{"key": "quiet", "type": "toggle"}, {"key": "hub", "env": "HUB_URL"}])
    plugin_env.write(plugin, {"beszel.quiet": True, "beszel.hub": "h"}, directory=tmp_path)
    assert (tmp_path / "beszel.env").read_text() == 'HUB_URL="h"\n'


@pytest.mark.parametrize("value", [None, ""])
def test_a_value_that_was_never_given_writes_no_line(tmp_path, value):
    """**An absent value is an absent variable**, not an empty one: to most
    programs those differ, and *not configured* is the honest statement."""
    plugin = _plugin([{"key": "token", "env": "TOKEN"}])
    plugin_env.write(plugin, {"beszel.token": value}, directory=tmp_path)
    assert (tmp_path / "beszel.env").read_text() == ""


def test_false_is_written_because_off_is_a_decision(tmp_path):
    plugin = _plugin([{"key": "x", "env": "X"}, {"key": "y", "env": "Y"}])
    plugin_env.write(plugin, {"beszel.x": False, "beszel.y": True}, directory=tmp_path)
    assert (tmp_path / "beszel.env").read_text() == 'X="false"\nY="true"\n'


def test_a_key_with_spaces_survives(tmp_path):
    """The case that forced quoting: a hub's public key is
    `ssh-ed25519 AAAA... comment`, and unquoted systemd reads everything after
    the first space as a second assignment."""
    plugin = _plugin([{"key": "key", "env": "KEY"}])
    plugin_env.write(plugin, {"beszel.key": "ssh-ed25519 AAAAC3 hub@host"}, directory=tmp_path)
    assert (tmp_path / "beszel.env").read_text() == 'KEY="ssh-ed25519 AAAAC3 hub@host"\n'


@pytest.mark.parametrize("raw, written", [
    ('a"b', 'A="a\\"b"'),
    ("a\\b", 'A="a\\\\b"'),
    ('\\"', 'A="\\\\\\""'),
])
def test_quotes_and_backslashes_are_escaped(tmp_path, raw, written):
    plugin = _plugin([{"key": "a", "env": "A"}])
    plugin_env.write(plugin, {"beszel.a": raw}, directory=tmp_path)
    assert (tmp_path / "beszel.env").read_text() == written + "\n"


def test_a_newline_is_refused_rather_than_truncated(tmp_path, caplog):
    """No `EnvironmentFile` line can carry one, and half a credential is worse
    than none: the plugin fails to authenticate and nothing says why."""
    plugin = _plugin([{"key": "key", "env": "KEY"}, {"key": "hub", "env": "HUB_URL"}])
    plugin_env.write(plugin, {"beszel.key": "line\nline", "beszel.hub": "h"},
                     directory=tmp_path)
    assert (tmp_path / "beszel.env").read_text() == 'HUB_URL="h"\n'
    assert "newline" in caplog.text


def test_the_file_is_not_readable_by_anyone_else(tmp_path):
    """It holds a token. 0600 from the moment it exists, not after a chmod."""
    plugin = _plugin([{"key": "token", "env": "TOKEN"}])
    plugin_env.write(plugin, {"beszel.token": "secret"}, directory=tmp_path)
    mode = stat.S_IMODE((tmp_path / "beszel.env").stat().st_mode)
    assert mode == 0o600


def test_nothing_is_left_behind(tmp_path):
    plugin = _plugin([{"key": "token", "env": "TOKEN"}])
    plugin_env.write(plugin, {"beszel.token": "secret"}, directory=tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["beszel.env"]


def test_an_unchanged_value_reports_no_change(tmp_path):
    """**What decides whether the unit is restarted.** A settings screen that
    bounces a running service on every unrelated write is worse than one that
    does nothing."""
    plugin = _plugin([{"key": "hub", "env": "HUB_URL"}])
    assert plugin_env.write(plugin, {"beszel.hub": "h"}, directory=tmp_path) is True
    assert plugin_env.write(plugin, {"beszel.hub": "h"}, directory=tmp_path) is False
    assert plugin_env.write(plugin, {"beszel.hub": "h2"}, directory=tmp_path) is True


def test_a_plugin_with_no_env_rows_gets_no_file(tmp_path):
    """Its unit's `EnvironmentFile=-` finds nothing, which is correct rather
    than missing."""
    plugin = _plugin([{"key": "quiet", "type": "toggle"}])
    assert plugin_env.has_env(plugin) is False
    assert plugin_env.has_env(_plugin([{"key": "hub", "env": "HUB_URL"}])) is True


def test_the_directory_is_made_if_it_is_not_there(tmp_path):
    """`/run` is tmpfs: on a fresh boot nothing under it exists yet."""
    plugin = _plugin([{"key": "hub", "env": "HUB_URL"}])
    nested = tmp_path / "run" / "gexis" / "plugins"
    plugin_env.write(plugin, {"beszel.hub": "h"}, directory=nested)
    assert (nested / "beszel.env").read_text() == 'HUB_URL="h"\n'


def test_the_path_is_named_after_the_plugin():
    assert plugin_env.path("beszel").name == "beszel.env"
    assert plugin_env.path("beszel").parent == plugin_env.RUN_DIR
    assert plugin_env.RUN_DIR.as_posix() == "/run/gexis/plugins"
