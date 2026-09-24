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


def test_the_shipped_core_toml_only_names_fields_config_has():
    """`Config.load` rejects an unknown key, which is right - a typo in a
    deployment file should not be silently ignored. But it only ever fired
    on the device: on 2026-09-23 `boot_volume_steps` was removed from the
    dataclass and left in the shipped `core.toml`, and the daemon would not
    start while 867 tests passed.

    The second time in one afternoon that a removal left a dangling
    reference nothing tested (see the registry check above), which is what
    earned this file."""
    import dataclasses
    import tomllib

    from gexis_core.config import Config

    shipped = (
        Path(__file__).resolve().parents[2]
        / "image" / "stage-gexis" / "03-core" / "files" / "core.toml"
    )
    keys = set(tomllib.loads(shipped.read_text()))
    fields = {f.name for f in dataclasses.fields(Config)}

    assert not keys - fields, f"core.toml names fields Config does not have: {sorted(keys - fields)}"
