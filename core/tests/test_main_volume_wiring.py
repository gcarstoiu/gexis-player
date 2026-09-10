"""Unit tests for __main__.py's volume-restore wiring.

Regression coverage for the bug found on hardware, 2026-09-08: Bluetooth
(unmanaged - Finding 006) was left at whatever the previous renderer's
mixer level happened to be, with nothing ensuring an audible starting
point. unmanaged_floor_raw is the pure decision logic; make_restore_volume
wires it (and the managed-renderer path) to actual I/O and isn't
exercised directly here - see this file's sibling tests (test_volume.py,
test_renderer_volume.py) for the pieces it composes.
"""
from __future__ import annotations

from gexis_core.__main__ import unmanaged_floor_raw
from gexis_core.volume import db_to_raw


def test_below_floor_bumps_up():
    assert unmanaged_floor_raw(60, floor_db=-40.0) == db_to_raw(-40.0)


def test_at_floor_is_left_alone():
    at_floor = db_to_raw(-40.0)
    assert unmanaged_floor_raw(at_floor, floor_db=-40.0) is None


def test_above_floor_is_left_alone():
    assert unmanaged_floor_raw(230, floor_db=-40.0) is None


def test_unknown_current_value_is_left_alone():
    # get_raw() returned None (amixer parse failed) - don't guess.
    assert unmanaged_floor_raw(None, floor_db=-40.0) is None
