"""Unit tests for per-renderer volume memory (criterion 5, George's
decision 2026-09-07)."""
from __future__ import annotations

from pathlib import Path

import pytest

from gexis_core.renderer_volume import RendererVolumeMemory
from gexis_core.volume import db_to_raw

# Matches today's real declaration (LmsAdapter/SpotifyAdapter.capabilities.
# volume_managed) - tests pass it explicitly now that criterion 3 removed
# the module's own hardcoded MANAGED_RENDERERS tuple.
MANAGED = frozenset({"lms", "spotify"})


def test_unknown_renderer_returns_none(tmp_path: Path):
    memory = RendererVolumeMemory(tmp_path / "volume.json", managed_renderers=MANAGED)
    assert memory.get("lms") is None


def test_remember_then_get(tmp_path: Path):
    memory = RendererVolumeMemory(tmp_path / "volume.json", managed_renderers=MANAGED)
    memory.remember("lms", 120)
    assert memory.get("lms") == 120


def test_bluetooth_is_out_of_scope_and_silently_ignored(tmp_path: Path):
    """Scope decision recorded in the module docstring: Bluetooth's own
    volume path isn't understood well enough yet to restore a remembered
    level for it (docs/findings/006-bluetooth-volume-partial-software.md).
    """
    memory = RendererVolumeMemory(tmp_path / "volume.json", managed_renderers=MANAGED)
    memory.remember("bluetooth", 200)
    assert memory.get("bluetooth") is None


def test_persists_across_instances(tmp_path: Path):
    path = tmp_path / "volume.json"
    RendererVolumeMemory(path, managed_renderers=MANAGED).remember("spotify", 90)

    reloaded = RendererVolumeMemory(path, managed_renderers=MANAGED)
    assert reloaded.get("spotify") == 90


def test_missing_state_file_is_not_an_error(tmp_path: Path):
    memory = RendererVolumeMemory(tmp_path / "does-not-exist.json", managed_renderers=MANAGED)
    assert memory.get("lms") is None


def test_corrupt_state_file_is_not_fatal(tmp_path: Path):
    path = tmp_path / "volume.json"
    path.write_text("not valid json{{{")
    memory = RendererVolumeMemory(path, managed_renderers=MANAGED)
    assert memory.get("lms") is None


class TestResolveRestore:
    """Regression coverage for the bug found on hardware, 2026-09-08:
    Bluetooth acquisitions were falling through to the boot-safe default
    (-90dB), silently muting it regardless of the phone's own volume."""

    def test_unmanaged_renderer_returns_none(self, tmp_path: Path):
        memory = RendererVolumeMemory(tmp_path / "v.json", managed_renderers=MANAGED)
        assert (
            memory.resolve_restore("bluetooth", boot_default=60, floor_db=-40.0)
            is None
        )

    def test_no_memory_yet_uses_boot_default_unfloored(self, tmp_path: Path):
        # boot_default (60 raw = -90dB) is below the floor (-40dB) on
        # purpose in this test - it must NOT be clamped. The floor only
        # applies to a *remembered* value.
        memory = RendererVolumeMemory(tmp_path / "v.json", managed_renderers=MANAGED)
        assert memory.resolve_restore("lms", boot_default=60, floor_db=-40.0) == 60

    def test_remembered_value_above_floor_is_used_as_is(self, tmp_path: Path):
        memory = RendererVolumeMemory(tmp_path / "v.json", managed_renderers=MANAGED)
        memory.remember("spotify", 200)  # well above -40dB
        assert memory.resolve_restore("spotify", boot_default=60, floor_db=-40.0) == 200

    def test_remembered_value_below_floor_is_clamped_up(self, tmp_path: Path):
        memory = RendererVolumeMemory(tmp_path / "v.json", managed_renderers=MANAGED)
        memory.remember("lms", 60)  # -90dB, below a -40dB floor
        raw = memory.resolve_restore("lms", boot_default=60, floor_db=-40.0)
        assert raw == 160  # db_to_raw(-40.0)


def test_managed_renderers_is_declared_not_hardcoded(tmp_path: Path):
    """Criterion 3: a renderer outside the declared set is unmanaged, even
    if it happens to be named "lms" - proves the set is actually used,
    not a vestigial parameter shadowing an internal constant."""
    memory = RendererVolumeMemory(tmp_path / "v.json", managed_renderers=frozenset({"spotify"}))
    memory.remember("lms", 200)
    assert memory.get("lms") is None
    assert memory.resolve_restore("lms", boot_default=60, floor_db=-40.0) is None


class TestNoRestoreCeiling:
    """ADR-0052 §1 built a `restore_ceiling` and the amendment withdrew it
    the same day, before it was ever surfaced.

    It clamped the hardware on a restore and told nobody: LMS reconnects at
    100, the DAC goes to -20 dB, and every number in sight still reads 100 -
    so the first nudge of a slider, which is not a restore and so not
    clamped, delivered the whole 20 dB at once. George: *"what looks like an
    error because the sound jumps up or down with the first move of the
    volume."*

    These tests pin the absence, because the hazard §1 aimed at is real and
    measured (53 dB thirteen seconds after a boot, untouched - Finding 045
    §5) and somebody reading that will be tempted to put the clamp back. The
    answer to it is §4's ramp and `max_ceiling`, neither of which lies about
    where the level is.
    """

    @staticmethod
    def _memory(tmp_path, remembered):
        memory = RendererVolumeMemory(tmp_path / "volumes.json", managed_renderers=MANAGED)
        for renderer_id, raw in remembered.items():
            memory.remember(renderer_id, raw)
        return memory

    def test_a_remembered_level_at_full_scale_is_restored_untouched(self, tmp_path):
        memory = self._memory(tmp_path, {"spotify": 240})  # 0 dB, full scale
        assert memory.resolve_restore("spotify", boot_default=60, floor_db=-40.0) == 240

    def test_the_floor_still_guards_a_level_too_quiet_to_be_meant(self, tmp_path):
        memory = self._memory(tmp_path, {"spotify": 100})  # -70 dB
        raw = memory.resolve_restore("spotify", boot_default=60, floor_db=-40.0)
        assert raw == db_to_raw(-40.0)

    def test_resolve_restore_takes_no_ceiling_argument(self, tmp_path):
        """The signature is the contract: there is nowhere to pass one."""
        memory = self._memory(tmp_path, {"spotify": 240})
        with pytest.raises(TypeError):
            memory.resolve_restore(
                "spotify", boot_default=60, floor_db=-40.0, ceiling_db=-20.0
            )


class TestThePerRendererRow:
    """ADR-0022's `per_renderer_volume`, wired 2026-09-23. George's decision
    of 2026-09-07 made the behaviour unconditional; the row has been
    inventoried as `[R][H]` since."""

    @staticmethod
    def _memory(tmp_path, enabled):
        memory = RendererVolumeMemory(
            tmp_path / "volumes.json",
            managed_renderers=MANAGED,
            enabled=lambda: enabled[0],
        )
        return memory

    def test_off_means_every_renderer_starts_from_the_boot_level(self, tmp_path):
        enabled = [True]
        memory = self._memory(tmp_path, enabled)
        memory.remember("spotify", 200)

        enabled[0] = False

        assert memory.resolve_restore("spotify", boot_default=60, floor_db=-40.0) == 60

    def test_off_does_not_throw_away_what_is_already_stored(self, tmp_path):
        """So that turning it back on returns the device to where it was,
        rather than to silence."""
        enabled = [True]
        memory = self._memory(tmp_path, enabled)
        memory.remember("spotify", 200)

        enabled[0] = False
        memory.remember("spotify", 111)  # ignored
        enabled[0] = True

        assert memory.resolve_restore("spotify", boot_default=60, floor_db=-40.0) == 200

    def test_an_unmanaged_renderer_is_still_untouched_either_way(self, tmp_path):
        """`None` is "not ours to touch at all", which is a different thing
        from "start from the boot level"."""
        enabled = [False]
        memory = self._memory(tmp_path, enabled)

        assert memory.resolve_restore("bluetooth", boot_default=60, floor_db=-40.0) is None

    def test_the_row_is_read_per_call_not_captured(self, tmp_path):
        """A change from the phone applies to the next acquisition rather
        than the next restart."""
        enabled = [True]
        memory = self._memory(tmp_path, enabled)
        memory.remember("spotify", 200)
        assert memory.resolve_restore("spotify", boot_default=60, floor_db=-40.0) == 200

        enabled[0] = False
        assert memory.resolve_restore("spotify", boot_default=60, floor_db=-40.0) == 60
