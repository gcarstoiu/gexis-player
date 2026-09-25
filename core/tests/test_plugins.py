# SPDX-License-Identifier: GPL-3.0-or-later
"""**ADR-0086: a plugin declares itself in a manifest.**

The core reads these before a plugin is running, and a plugin's author cannot
see this device's log. So the rules are: refuse what cannot be drawn, say why,
and never let one bad manifest take the others down.
"""
from __future__ import annotations

import json

import pytest

from gexis_core import plugins
from gexis_core.plugins import BadManifest, parse


GOOD = {"id": "plexamp", "name": "Plexamp", "kind": "renderer",
        "unit": "plexamp.service", "label": "Plexamp Active",
        "accent": "#e5a00d", "status": "Ready"}


def _install(root, manifest, *, with_mark=False, name=None):
    d = root / (name or manifest.get("id", "broken"))
    d.mkdir(parents=True)
    (d / "plugin.json").write_text(json.dumps(manifest))
    if with_mark:
        (d / "mark.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    return d


def test_a_manifest_is_read_whether_or_not_the_plugin_runs(tmp_path):
    """The point of the file. A renderer that is switched off never connects
    and its Enabled row still has to be there to switch it on."""
    _install(tmp_path, GOOD)
    found = plugins.installed(tmp_path)
    assert [p.id for p in found] == ["plexamp"]
    assert found[0].unit == "plexamp.service"
    assert found[0].label == "Plexamp Active"


def test_the_mark_is_found_beside_the_manifest(tmp_path):
    _install(tmp_path, GOOD, with_mark=True)
    plugin = plugins.installed(tmp_path)[0]
    assert plugin.mark is not None
    assert plugin.to_json()["mark"] == "/plugins/plexamp/mark"


def test_no_mark_is_not_an_error(tmp_path):
    """A plugin with no glyph gets the generic one, rather than not loading."""
    _install(tmp_path, GOOD)
    plugin = plugins.installed(tmp_path)[0]
    assert plugin.mark is None
    assert plugin.to_json()["mark"] is None


@pytest.mark.parametrize("bad, why", [
    ({**GOOD, "id": ""}, "missing"),
    ({**GOOD, "name": ""}, "missing"),
    ({**GOOD, "unit": ""}, "missing"),
    ({**GOOD, "kind": "widget"}, "not one of"),
    ({**GOOD, "id": "Plexamp"}, "not a usable id"),
    ({**GOOD, "id": "../etc"}, "not a usable id"),
    ({**GOOD, "id": "a"}, "not a usable id"),
    ({**GOOD, "settings": {"key": "x"}}, "list of rows"),
    ({**GOOD, "settings": ["not a row"]}, "list of rows"),
])
def test_what_is_refused_and_why(bad, why):
    """Refused *with a reason*: the author cannot see this device's log, so
    the packager has to be able to."""
    with pytest.raises(BadManifest, match=why):
        parse(bad)


def test_an_id_that_is_not_its_directory_is_ignored(tmp_path):
    """The id is a URL path segment and a directory name. If they disagree,
    one of them is a lie and there is no way to know which."""
    _install(tmp_path, GOOD, name="something-else")
    assert plugins.installed(tmp_path) == []


def test_one_bad_manifest_does_not_take_the_others_down(tmp_path):
    """Somebody halfway through packaging a plugin must not stop the
    renderers loading."""
    _install(tmp_path, GOOD)
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "plugin.json").write_text("{ this is not json")
    _install(tmp_path, {**GOOD, "id": "qobuz", "name": "Qobuz", "unit": "qobuz.service"})

    assert sorted(p.id for p in plugins.installed(tmp_path)) == ["plexamp", "qobuz"]


def test_a_directory_without_a_manifest_is_not_a_plugin(tmp_path):
    (tmp_path / "leftovers").mkdir()
    (tmp_path / "leftovers" / "readme.txt").write_text("hello")
    assert plugins.installed(tmp_path) == []


def test_a_missing_directory_is_no_plugins(tmp_path):
    assert plugins.installed(tmp_path / "never-made") == []


def test_a_service_needs_no_capabilities_or_presentation(tmp_path):
    """The shape a Beszel agent has to fit. If this cannot be said, the
    contract is a renderer API wearing a plugin's name."""
    _install(tmp_path, {"id": "beszel", "name": "Beszel agent",
                        "kind": "service", "unit": "beszel-agent.service"})
    plugin = plugins.installed(tmp_path)[0]
    assert plugin.kind == "service"
    assert plugin.accent is None and plugin.status is None and plugin.mark is None
    assert plugin.settings == ()


def test_the_payload_carries_what_the_panel_draws_and_nothing_else(tmp_path):
    """`unit` and `label` are the core's business; a browser has no use for
    either and every reason not to be told."""
    _install(tmp_path, GOOD, with_mark=True)
    payload = plugins.installed(tmp_path)[0].to_json()
    assert set(payload) == {"id", "name", "kind", "accent", "status", "mark"}


# ---------------------------------------------------------------------------
# The three this repository ships.
# ---------------------------------------------------------------------------

from pathlib import Path  # noqa: E402

SHIPPED = (Path(__file__).resolve().parents[2] / "image" / "stage-gexis"
           / "03-core" / "files" / "plugins")


def test_the_built_ins_are_described_the_same_way():
    """**ADR-0086's reason for existing.** If the defaults keep a special path
    and plugins get a generic one, the generic one is drawn by code nothing
    exercises - and the first external plugin finds the hole."""
    found = {p.id: p for p in plugins.installed(SHIPPED)}
    assert set(found) == {"lms", "spotify", "bluetooth"}
    assert all(p.kind == "renderer" for p in found.values())


def test_each_names_the_unit_that_actually_opens_the_device():
    """The release ladder attributes a still-busy device to this unit
    (`alsa.device_held_by`), so a wrong name here is a ladder that escalates
    against the wrong process."""
    found = {p.id: p.unit for p in plugins.installed(SHIPPED)}
    assert found == {
        "lms": "squeezelite.service",
        "spotify": "go-librespot.service",
        "bluetooth": "bluealsa-aplay.service",
    }


def test_the_units_are_the_ones_the_adapters_declare():
    """Read from the adapters rather than repeated here, so the manifests
    cannot drift from the code that uses them."""
    from gexis_core.adapters.bluetooth import BluetoothAdapter
    from gexis_core.adapters.lms import LmsAdapter
    from gexis_core.adapters.spotify import SpotifyAdapter

    declared = {"lms": LmsAdapter.unit_name, "spotify": SpotifyAdapter.unit_name,
                "bluetooth": BluetoothAdapter.unit_name}
    assert {p.id: p.unit for p in plugins.installed(SHIPPED)} == declared


def test_the_labels_are_the_ones_the_moode_file_already_wrote():
    """`metadata_file.py`'s map becomes the manifest's `label` (ADR-0086). It
    has not moved yet, so this is what stops the two drifting in the meantime."""
    from gexis_core.metadata_file import RENDERER_LABELS

    assert {p.id: p.label for p in plugins.installed(SHIPPED)} == dict(RENDERER_LABELS)


def test_the_accents_are_tokens_the_panel_actually_defines():
    tokens = (Path(__file__).resolve().parents[2] / "ui" / "src" / "styles"
              / "tokens.css").read_text()
    for plugin in plugins.installed(SHIPPED):
        assert plugin.accent
        assert plugin.accent.lower() in tokens.lower(), f"{plugin.id}: {plugin.accent}"
