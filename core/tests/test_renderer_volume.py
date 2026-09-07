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
