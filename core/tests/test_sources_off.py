# SPDX-License-Identifier: GPL-3.0-or-later
"""**ADR-0077: a source that is off is not running.**

Two things are checked here and they are both the sort that pass by accident.

`set_enabled` is one `subprocess.run` call and its argv *is* the decision: a
`stop` without a `disable` is a row whose effect ends at the next boot, which
is a row that lies the second time you look at it. So the argv is asserted
literally.

The unit names are hardcoded strings naming files in another tree, which is
exactly how ADR-0022's inventory came to reference a
`gexis-bluetooth-trust.service` that does not exist (corrected 2026-09-25).
A name that stops matching the image would make `headless` silently disable
nothing at all - `systemctl disable` on an unknown unit fails and this module
only logs the failure.
"""
from __future__ import annotations

from pathlib import Path

from gexis_core import systemd
from gexis_core.__main__ import BLUETOOTH_SETUP_UNIT, RENDERER_ROWS, SCREEN_UNITS

REPO = Path(__file__).resolve().parents[2]


class FakeRun:
    def __init__(self, returncode=0, stderr=""):
        self.calls = []
        self._returncode = returncode
        self._stderr = stderr

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)

        class Result:
            returncode = self._returncode
            stderr = self._stderr
            stdout = ""

        return Result()


def test_on_is_enable_now(monkeypatch):
    run = FakeRun()
    monkeypatch.setattr(systemd.subprocess, "run", run)
    systemd.set_enabled("squeezelite.service", True)
    assert run.calls == [["systemctl", "enable", "--now", "squeezelite.service"]]


def test_off_is_disable_now(monkeypatch):
    """`--now` is what makes this stop the unit as well as un-want it; without
    it the renderer keeps playing until the next reboot."""
    run = FakeRun()
    monkeypatch.setattr(systemd.subprocess, "run", run)
    systemd.set_enabled("go-librespot.service", False)
    assert run.calls == [["systemctl", "disable", "--now", "go-librespot.service"]]


def test_never_mask(monkeypatch):
    """ADR-0077 rejects `mask` and states the condition that would bring it
    back. If that condition arrives this assertion is the thing to change."""
    run = FakeRun()
    monkeypatch.setattr(systemd.subprocess, "run", run)
    systemd.set_enabled("gexis-kiosk.service", False)
    assert "mask" not in run.calls[0]


def test_a_failure_is_logged_not_raised(monkeypatch, caplog):
    """The daemon must not come down because a unit it does not have could not
    be disabled."""
    run = FakeRun(returncode=1, stderr="Unit nope.service does not exist.\n")
    monkeypatch.setattr(systemd.subprocess, "run", run)
    systemd.set_enabled("nope.service", False)
    assert "nope.service" in caplog.text


def _image_units() -> set[str]:
    return {p.name for p in (REPO / "image").rglob("*.service")}


def test_the_units_headless_turns_off_are_units_this_image_ships():
    units = _image_units()
    assert units, "no unit files found at all - the glob is wrong, not the image"
    assert {unit for unit, _now in SCREEN_UNITS} <= units


def test_the_bluetooth_setup_unit_exists():
    assert BLUETOOTH_SETUP_UNIT in _image_units()


def test_every_source_row_is_a_row_in_the_registry():
    import json

    keys = {
        row["key"]
        for group in json.loads(
            (REPO / "core/src/gexis_core/settings_registry.json").read_text()
        )
        for row in group.get("rows", [])
        if "key" in row
    }
    assert set(RENDERER_ROWS.values()) <= keys


def test_the_warm_up_is_enabled_for_the_next_boot_not_started_now(monkeypatch):
    """Its own unit file: "if the kiosk has already started, warming is
    pointless - it is reading the pages Chromium is reading anyway, and
    competing with it"."""
    run = FakeRun()
    monkeypatch.setattr(systemd.subprocess, "run", run)
    systemd.set_enabled("gexis-panel-warmup.service", True, now=False)
    assert run.calls == [["systemctl", "enable", "gexis-panel-warmup.service"]]


def test_only_the_warm_up_skips_now():
    """The kiosk and the visualiser have to stop when the row says headless,
    not at the next boot."""
    assert dict(SCREEN_UNITS)["gexis-panel-warmup.service"] is False
    assert all(
        now for unit, now in SCREEN_UNITS if unit != "gexis-panel-warmup.service"
    )
