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
    # ADR-0088: a variable name no shell can carry is a typo, and the plugin it
    # belongs to would otherwise start, run, and never authenticate.
    ({**GOOD, "settings": [{"key": "t", "env": "2TOKEN"}]}, "environment variable"),
    ({**GOOD, "settings": [{"key": "t", "env": "HUB URL"}]}, "environment variable"),
    ({**GOOD, "settings": [{"key": "t", "env": "HUB-URL"}]}, "environment variable"),
    ({**GOOD, "settings": [{"key": "t", "env": 7}]}, "environment variable"),
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


def test_a_row_may_name_an_environment_variable(tmp_path):
    """ADR-0088. Lowercase is allowed: the uppercase convention is not
    universal, and a manifest naming a variable this core refuses would be a
    plugin nobody could configure."""
    for name in ("TOKEN", "HUB_URL", "_x", "hub_url", "KEY2"):
        assert parse({**GOOD, "settings": [{"key": "k", "env": name}]}).settings[0]["env"] == name


def test_a_row_without_env_is_still_fine(tmp_path):
    """Most rows are the panel's business only. `env` is what a third-party
    binary needs, not what every row has."""
    plugin = parse({**GOOD, "settings": [{"key": "k", "type": "toggle"}]})
    assert "env" not in plugin.settings[0]


def test_a_synthesised_switch_reads_the_units_real_state(monkeypatch):
    """**Found on the device, 2026-09-25.** A manifest defaulting its switch to
    *on* beside an image that installs the unit *disabled* put a row on the
    screen reading "Enabled" for something that was neither running nor going
    to start. Asking systemd cannot disagree with systemd.
    """
    from gexis_core import systemd

    class Result:
        def __init__(self, out):
            self.stdout = out

    seen = []

    def fake_run(argv, **kw):
        seen.append(argv)
        return Result({"on.service": "enabled\n", "rt.service": "enabled-runtime\n",
                       "off.service": "disabled\n", "static.service": "static\n",
                       "masked.service": "masked\n", "gone.service": ""}[argv[-1]])

    monkeypatch.setattr(systemd.subprocess, "run", fake_run)
    assert systemd.is_enabled("on.service") is True
    assert systemd.is_enabled("rt.service") is True
    for unit in ("off.service", "static.service", "masked.service", "gone.service"):
        assert systemd.is_enabled(unit) is False
    assert all(argv[:2] == ["systemctl", "is-enabled"] for argv in seen)


BESZEL = (Path(__file__).resolve().parents[2] / "image" / "stage-gexis"
          / "07-beszel" / "files")


def test_the_shipped_beszel_manifest_is_what_the_record_says():
    """**ADR-0087's row list**, which George confirmed as a settings decision -
    so a drift here is a drift from a decision, not a detail."""
    plugin = parse(json.loads((BESZEL / "plugin.json").read_text()))
    assert (plugin.id, plugin.kind, plugin.unit) == (
        "beszel", "service", "beszel-agent.service")
    # No `enabled_row`, so ADR-0086's amendment synthesises the switch. That is
    # the point of this plugin: it proves the contract carries a non-renderer
    # without the core knowing its name.
    assert plugin.enabled_row is None
    assert [r["key"] for r in plugin.settings] == ["hub", "token", "key"]
    assert [r.get("env") for r in plugin.settings] == ["HUB_URL", "TOKEN", "KEY"]
    # **No row declares `onlyWhen`.** Every one hides behind the switch anyway -
    # the core applies that to every plugin row, so a manifest that forgot would
    # not leave fields on screen for a process nobody can reach (George,
    # 2026-09-25: *"when the toggle is off the entire subgroup is off"*).
    assert not any("onlyWhen" in r for r in plugin.settings)
    # The two credentials are masked on the panel; `hub` is an address.
    assert [bool(r.get("secret")) for r in plugin.settings] == [False, True, True]


def test_the_beszel_unit_reads_what_the_contract_writes():
    """The unit and ADR-0088 have to agree on one path, and nothing else checks
    it: the manifest names variables, the unit names the file they arrive in."""
    from gexis_core import plugin_env

    unit = (BESZEL / "beszel-agent.service").read_text()
    assert f"EnvironmentFile=-{plugin_env.path('beszel')}" in unit
    # ADR-0087, Finding 078: the agent opens an inbound SSH port on 45876 even in
    # outbound mode, and this is the flag that removes it. Not a settings row -
    # a security property, not a preference.
    assert "--listen -1" in unit
    assert "DATA_DIR=/var/lib/beszel-agent" in unit
    assert "StateDirectory=beszel-agent" in unit


def test_the_fingerprint_is_in_the_backup():
    """It is the identity the hub binds this system to. The Spotify pairing
    taught this the expensive way (ADR-0083, 2026-09-25)."""
    from gexis_core.backups import MEMBERS

    assert "var/lib/beszel-agent" in MEMBERS


def test_the_listen_check_runs_after_the_agent_has_started():
    """**Before would measure the wrong thing.** What matters is what the agent
    actually bound, not what it was asked to bind - `-1` is a value the flag
    parser happens to accept and an upgrade could start ignoring it."""
    unit = (BESZEL / "beszel-agent.service").read_text()
    assert "ExecStartPost=/usr/local/lib/gexis/beszel-agent-listen-check.sh" in unit
    assert "ExecStartPre=/usr/local/lib/gexis/beszel-agent-listen-check.sh" not in unit
    check = (BESZEL / "beszel-agent-listen-check.sh").read_text()
    assert "45876" in check


def test_a_changed_value_restarts_a_unit_that_is_enabled_even_if_it_failed(monkeypatch):
    """**The gap the device found** (Finding 079). Beszel's first real state was
    `failed` - switched on before anyone had typed a token, refusing to start
    without one. `try-restart` does nothing to a failed unit, so the token
    arrived and nothing used it until a reboot. The gate is *should this be
    running*, not *is it running*."""
    from gexis_core import systemd

    calls = []

    class Result:
        stdout = "enabled\n"

    def fake_run(argv, **kw):
        calls.append(argv[1])
        return Result()

    monkeypatch.setattr(systemd.subprocess, "run", fake_run)
    systemd.restart_if_enabled("beszel-agent.service")
    # `reset-failed` before `restart`: a unit that spent its StartLimitBurst
    # while unconfigured refuses a plain restart, and that is the expected path
    # here rather than an edge case.
    assert calls == ["is-enabled", "reset-failed", "restart"]


def test_a_disabled_unit_is_left_alone(monkeypatch):
    """Off stays off. A credential typed for a plugin nobody switched on is
    stored and exported and starts nothing."""
    from gexis_core import systemd

    calls = []

    class Result:
        stdout = "disabled\n"

    monkeypatch.setattr(systemd.subprocess, "run",
                        lambda argv, **kw: (calls.append(argv[1]), Result())[1])
    systemd.restart_if_enabled("beszel-agent.service")
    assert calls == ["is-enabled"]
