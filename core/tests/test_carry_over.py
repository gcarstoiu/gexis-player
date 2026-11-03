# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0174: ours that moved to the catalogue, carried over - data into the
plugin's own folder, the ones used recorded for the catalogue's install,
switched on again if they were on."""
from __future__ import annotations

from pathlib import Path

import pytest

from gexis_core import carry_over, uploads

AGENT = carry_over.Moved("beszel", "Beszel", "service", "beszel-agent.service",
                         (Path("agent-data"),), "gexis-beszel-agent", ("beszel",))


@pytest.fixture
def places(tmp_path, monkeypatch):
    old = tmp_path / "var-lib-beszel-agent"
    old.mkdir()
    (old / "fingerprint").write_text("48 bytes of identity")
    moved = carry_over.Moved(AGENT.id, AGENT.name, AGENT.kind, AGENT.unit, (old,), AGENT.package, ())
    wants = tmp_path / "wants"
    wants.mkdir()
    monkeypatch.setattr(carry_over, "subprocess", None)  # no user is touched here
    return {"old": old, "moved": moved, "wants": wants, "known": tmp_path / "known.json",
            "private": tmp_path / "private" / "gexis-uploaded"}


def _carry(places, *, stored=None, added=None, ours=frozenset(), versions=dict, stopped=None):
    return carry_over.carry(ours=set(ours), stored=lambda key: stored, added=added,
                            known=places["known"], private=places["private"], wants=places["wants"],
                            versions=versions, stop=(stopped if stopped is not None else []).append,
                            moved=[places["moved"]])


def test_a_plugin_that_was_on_is_moved_recorded_and_flagged_to_switch_on(places):
    assert _carry(places, stored=True) == ["beszel"]
    assert (places["private"] / "beszel" / "fingerprint").read_text() == "48 bytes of identity"
    assert not places["old"].exists(), "the old folder goes once empty"
    record = uploads.known(places["known"])["beszel"]
    assert record["origin"] == uploads.CATALOGUE and record["carried_on"] is True
    assert [m["id"] for m in uploads.missing(places["private"], places["known"])] == ["beszel"], \
        "the restore's path sees it as a catalogue plugin without its package"


def test_the_old_service_is_stopped_before_its_data_moves(places):
    """Found on sofapi, 2026-11-03: removing our package left its agent
    running, and it went on beside the catalogue's. Stopped first, every
    start, while the player does not ship it."""
    stopped = []
    _carry(places, stored=True, stopped=stopped)
    assert stopped == ["beszel-agent.service"]
    stopped.clear()
    _carry(places, stored=True, ours={"beszel"}, stopped=stopped)
    assert stopped == [], "not while the player still ships it"


def test_a_switch_nobody_touched_reads_the_old_unit_s_enable_link(places):
    link = places["wants"] / "beszel-agent.service"
    link.symlink_to("/usr/lib/systemd/system/beszel-agent.service")  # gone with its package
    assert _carry(places, stored=None) == ["beszel"]
    assert uploads.known(places["known"])["beszel"]["carried_on"] is True
    assert not link.is_symlink(), "the dangling link is cleared"


def test_added_but_off_is_carried_and_left_off(places):
    assert _carry(places, stored=False, added={"beszel"}) == ["beszel"]
    assert uploads.known(places["known"])["beszel"]["carried_on"] is False


def test_unused_its_data_still_moves_and_nothing_is_installed(places):
    assert _carry(places, stored=False, added=set()) == []
    assert (places["private"] / "beszel" / "fingerprint").exists(), "kept for when it is added again"
    assert uploads.known(places["known"]) == {}


def test_while_the_player_still_ships_it_nothing_happens(places):
    assert _carry(places, stored=True, ours={"beszel"}) == []
    assert (places["old"] / "fingerprint").exists()


def test_carried_once_not_twice(places):
    _carry(places, stored=True)
    assert _carry(places, stored=True) == []
    assert _carry(places, stored=True, versions=lambda: {"beszel": "0.21.1-1"}) == []


def test_a_file_the_plugin_already_has_is_not_overwritten(places):
    (places["private"] / "beszel").mkdir(parents=True)
    (places["private"] / "beszel" / "fingerprint").write_text("its own")
    _carry(places, stored=True)
    assert (places["private"] / "beszel" / "fingerprint").read_text() == "its own"
    assert (places["old"] / "fingerprint").exists(), "the old one stays where it was"


def test_switched_on_once_installed_and_only_once(places):
    _carry(places, stored=True)
    assert carry_over.to_switch_on(set(), places["known"]) == [], "not yet installed"
    assert carry_over.to_switch_on({"beszel"}, places["known"]) == ["beszel"]
    assert carry_over.to_switch_on({"beszel"}, places["known"]) == []


def test_remembering_installed_plugins_keeps_the_flag(places, tmp_path):
    _carry(places, stored=True)
    root = tmp_path / "plugins"
    (root / "beszel" / "0.21.1-1").mkdir(parents=True)
    (root / "beszel" / "0.21.1-1" / "plugin.json").write_text(
        '{"id": "beszel", "name": "Beszel", "kind": "service", "version": "0.21.1-1", "run": "run"}')
    (root / "beszel" / "current").symlink_to("0.21.1-1")
    uploads.remember(root, places["known"])
    assert uploads.known(places["known"])["beszel"]["carried_on"] is True


def test_the_shipped_set_is_what_adr_0174_moves():
    assert {m.id for m in carry_over.MOVED} == {"beszel", "beszel-hub"}
    assert {m.package for m in carry_over.MOVED} == {"gexis-beszel-agent", "gexis-beszel-hub"}
