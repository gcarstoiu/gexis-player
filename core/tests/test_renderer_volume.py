"""Unit tests for per-renderer volume memory (criterion 5, George's
decision 2026-09-07)."""
from __future__ import annotations

from pathlib import Path

from gexis_core.renderer_volume import RendererVolumeMemory


def test_unknown_renderer_returns_none(tmp_path: Path):
    memory = RendererVolumeMemory(tmp_path / "volume.json")
    assert memory.get("lms") is None


def test_remember_then_get(tmp_path: Path):
    memory = RendererVolumeMemory(tmp_path / "volume.json")
    memory.remember("lms", 120)
    assert memory.get("lms") == 120


def test_bluetooth_is_out_of_scope_and_silently_ignored(tmp_path: Path):
    """Scope decision recorded in the module docstring: Bluetooth's own
    volume path isn't understood well enough yet to restore a remembered
    level for it (docs/findings/006-bluetooth-volume-partial-software.md).
    """
    memory = RendererVolumeMemory(tmp_path / "volume.json")
    memory.remember("bluetooth", 200)
    assert memory.get("bluetooth") is None


def test_persists_across_instances(tmp_path: Path):
    path = tmp_path / "volume.json"
    RendererVolumeMemory(path).remember("spotify", 90)

    reloaded = RendererVolumeMemory(path)
    assert reloaded.get("spotify") == 90


def test_missing_state_file_is_not_an_error(tmp_path: Path):
    memory = RendererVolumeMemory(tmp_path / "does-not-exist.json")
    assert memory.get("lms") is None


def test_corrupt_state_file_is_not_fatal(tmp_path: Path):
    path = tmp_path / "volume.json"
    path.write_text("not valid json{{{")
    memory = RendererVolumeMemory(path)
    assert memory.get("lms") is None


class TestResolveRestore:
    """Regression coverage for the bug found on hardware, 2026-09-08:
    Bluetooth acquisitions were falling through to the boot-safe default
    (-90dB), silently muting it regardless of the phone's own volume."""

    def test_unmanaged_renderer_returns_none(self, tmp_path: Path):
        memory = RendererVolumeMemory(tmp_path / "v.json")
        assert (
            memory.resolve_restore("bluetooth", boot_default=60, floor_db=-40.0)
            is None
        )

    def test_no_memory_yet_uses_boot_default_unfloored(self, tmp_path: Path):
        # boot_default (60 raw = -90dB) is below the floor (-40dB) on
        # purpose in this test - it must NOT be clamped. The floor only
        # applies to a *remembered* value.
        memory = RendererVolumeMemory(tmp_path / "v.json")
        assert memory.resolve_restore("lms", boot_default=60, floor_db=-40.0) == 60

    def test_remembered_value_above_floor_is_used_as_is(self, tmp_path: Path):
        memory = RendererVolumeMemory(tmp_path / "v.json")
        memory.remember("spotify", 200)  # well above -40dB
        assert memory.resolve_restore("spotify", boot_default=60, floor_db=-40.0) == 200

    def test_remembered_value_below_floor_is_clamped_up(self, tmp_path: Path):
        memory = RendererVolumeMemory(tmp_path / "v.json")
        memory.remember("lms", 60)  # -90dB, below a -40dB floor
        raw = memory.resolve_restore("lms", boot_default=60, floor_db=-40.0)
        assert raw == 160  # db_to_raw(-40.0)
