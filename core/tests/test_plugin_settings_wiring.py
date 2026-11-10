# SPDX-License-Identifier: GPL-3.0-or-later
"""**A plugin whose rows the registry refuses stops nothing** (the review of
1.16.1, critical). `Settings.with_plugins` dropped it with the reason logged,
and `main()` wired its keys all the same: `Settings` refused to start, the
core with it at every boot, and no screen was left to remove the plugin
from."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from gexis_core import plugins
from gexis_core.__main__ import _row_keys, _settled
from gexis_core.settings import SettingsStore
from gexis_core.settings_registry import Settings, load_registry

SOURCE = Path(__file__).resolve().parents[1] / "src" / "gexis_core" / "__main__.py"


def _plugin(plugin_id, rows):
    return plugins.parse({"id": plugin_id, "name": plugin_id.title(), "kind": "service",
                          "unit": f"{plugin_id}.service", "settings": rows})


REFUSED = [
    [{"key": "interval", "type": "number", "label": "Every (s)"}],
    [{"key": "mode", "type": "choice", "label": "Mode"}],
    [{"key": "a", "type": "text", "label": "A"}, {"key": "a", "type": "text", "label": "A again"}],
    [{"key": "a", "type": "text", "label": "A", "onlyWhen": ["nowhere", True]}],
]


@pytest.mark.parametrize("rows", REFUSED)
def test_settings_start_with_a_plugin_the_registry_refused(tmp_path, rows):
    good = _plugin("radio", [{"key": "station", "type": "text", "label": "Station"}])
    bad = _plugin("weather", rows)
    registry = Settings.with_plugins(load_registry(), [good, bad])

    settled = _settled([good, bad], registry)
    assert [p.id for p in settled] == ["radio"]
    wired = {key: (lambda value: None) for p in settled
             for key in (p.enabled_row or f"{p.id}.enabled", *_row_keys(p))}
    settings = Settings(SettingsStore(tmp_path / "s.db"), registry=registry, wired=wired,
                        seed_path=tmp_path / "none.json")
    assert settings.value("radio.station") is None


def test_a_row_named_enabled_never_takes_the_switch_s_place():
    """The registry keeps the core's switch over a manifest's own `enabled`
    row; wired after the switch, the row's callback replaced the switch's,
    and switching the plugin never started or stopped its unit."""
    radio = _plugin("radio", [{"key": "enabled", "type": "toggle", "label": "On"},
                              {"key": "station", "type": "text", "label": "Station"}])
    assert _row_keys(radio) == ["radio.station"]


def test_main_wires_only_the_plugins_the_registry_took():
    """Every plugin-derived key `main()` hands `Settings` comes from
    `settled`, not from every plugin installed."""
    tree = ast.parse(SOURCE.read_text())
    main = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "main")
    names = {"plugin_switches", "plugin_switch_defaults", "plugin_rows"}
    checked = [n.value for n in ast.walk(main) if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id in names for t in n.targets)]
    checked += [k.value for n in ast.walk(main) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name) and n.func.id == "Settings"
                for k in n.keywords if k.arg != "shown"]
    assert len(checked) >= 4
    over = {g.iter.id for value in checked for c in ast.walk(value)
            if isinstance(c, (ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp))
            for g in c.generators if isinstance(g.iter, ast.Name)}
    assert "installed_plugins" not in over and "settled" in over
