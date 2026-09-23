"""Every key `__main__` declares must exist in the registry.

`Settings.__init__` already checks this and raises `not in the registry:
[...]` — but nothing exercised it with the daemon's *real* dictionaries, so
the check only ran on the device. On 2026-09-23 a row was removed from the
registry and its `defaults` entry left behind; the tests passed and the
daemon would not start.

Read out of the source rather than by importing, because both dictionaries
are built inside `main()` from objects that need a device.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src" / "gexis_core"


def _registry_keys() -> set[str]:
    return {
        row["key"]
        for group in json.loads((SOURCE / "settings_registry.json").read_text())
        for row in group.get("rows", [])
        if "key" in row
    }


def _declared_keys() -> dict[str, set[str]]:
    """The literal string keys of `defaults={...}` and `wired={...}` in the
    `Settings(...)` call."""
    tree = ast.parse((SOURCE / "__main__.py").read_text())
    found: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == "Settings"):
            continue
        for keyword in node.keywords:
            if keyword.arg in {"defaults", "wired", "options"} and isinstance(
                keyword.value, ast.Dict
            ):
                found[keyword.arg] = {
                    k.value
                    for k in keyword.value.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)
                }
    return found


def test_the_settings_call_was_found_at_all():
    """Otherwise the tests below pass by finding nothing."""
    declared = _declared_keys()
    assert set(declared) == {"defaults", "options", "wired"}
    assert len(declared["wired"]) > 20


def test_every_declared_key_exists_in_the_registry():
    registry = _registry_keys()
    for where, keys in _declared_keys().items():
        missing = sorted(keys - registry)
        assert not missing, f"{where} names rows the registry does not have: {missing}"
