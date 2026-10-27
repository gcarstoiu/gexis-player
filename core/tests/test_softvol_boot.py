"""ADR-0140: the software volume is set before any renderer starts (George,
2026-10-12: "Do it now").

A real settings store (the core's own `SettingsStore`, in a temporary
file) and a fake `amixer` on PATH that keeps each control's raw value in a
file and logs every call - so what is asserted is what the boot step would
run, not what it meant to."""
from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from gexis_core import mixer_scale, outputs, softvol_boot
from gexis_core.outputs import Output
from gexis_core.settings import SettingsStore

DAC = Output(card="sndrpihifiberry", label="HiFiBerry DAC+ HD", control="DAC",
             scale=mixer_scale.Scale(raw_min=0, raw_max=255, db_min=-103.5, db_step=0.5))
HDMI = Output(card="vc4hdmi0", label="HDMI 1", control=None)

FAKE_AMIXER = r'''#!/bin/sh
# amixer -D output sget|sset CONTROL [VALUE]
dir="$(dirname "$0")"
echo "$*" >> "$dir/calls"
control="$4"
if [ "$3" = sset ]; then echo "$5" > "$dir/ctl-$control"; exit 0; fi
[ -f "$dir/ctl-$control" ] || { echo "amixer: Unable to find simple control '$control',0" >&2; exit 1; }
echo "Simple mixer control '$control',0"
echo "  Front Left: Playback $(cat "$dir/ctl-$control") [50%]"
'''


@pytest.fixture
def amixer(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "amixer"
    script.write_text(FAKE_AMIXER)
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(outputs, "configured", lambda: None)
    monkeypatch.setattr(outputs, "create_softvol_control", lambda: True)

    class Fake:
        def calls(self) -> list[str]:
            path = bin_dir / "calls"
            return path.read_text().splitlines() if path.exists() else []

        def value(self, control: str) -> int | None:
            path = bin_dir / f"ctl-{control}"
            return int(path.read_text()) if path.exists() else None

        def preset(self, control: str, raw: int) -> None:
            (bin_dir / f"ctl-{control}").write_text(f"{raw}\n")

        def writes(self) -> list[str]:
            return [c for c in self.calls() if " sset " in f" {c} "]
    return Fake()


def _store(tmp_path, **rows) -> Path:
    path = tmp_path / "settings.db"
    store = SettingsStore(path)
    for key, value in rows.items():
        store.set(key, value)
    store.close()
    return path


def _output(monkeypatch, output):
    monkeypatch.setattr(outputs, "resolve", lambda stored, *a, **k: output)


def test_software_mode_sets_the_remembered_level(tmp_path, monkeypatch, amixer):
    _output(monkeypatch, HDMI)
    path = _store(tmp_path, output_device="HDMI 1", _software_level_db=-42.5)
    outcome = softvol_boot.restore(path)
    assert amixer.value("Gexis") == outputs.SOFTVOL_SCALE.raw(-42.5)
    assert amixer.writes() == [f"-D output sset Gexis {outputs.SOFTVOL_SCALE.raw(-42.5)}"]
    assert "-42.50 dB" in outcome


def test_hdmi_on_the_default_hardware_row_is_software(tmp_path, monkeypatch, amixer):
    """ADR-0127 §2: Hardware on an output with no control of its own is
    Software - HDMI after a power cut is the case this exists for."""
    _output(monkeypatch, HDMI)
    path = _store(tmp_path, output_mode="Hardware", _software_level_db=-20.0)
    softvol_boot.restore(path)
    assert amixer.value("Gexis") == outputs.SOFTVOL_SCALE.raw(-20.0)


@pytest.mark.parametrize("mode", ["Hardware", "Fixed"])
def test_any_other_volume_type_writes_nothing(tmp_path, monkeypatch, amixer, mode):
    _output(monkeypatch, DAC)
    path = _store(tmp_path, output_mode=mode, _software_level_db=-20.0)
    assert "nothing to set" in softvol_boot.restore(path)
    assert amixer.writes() == []


def test_nothing_remembered_takes_the_cards_own_level_as_the_core_does(tmp_path, monkeypatch, amixer):
    _output(monkeypatch, DAC)
    amixer.preset("DAC", 150)          # -28.5 dB on this scale
    path = _store(tmp_path, output_mode="Software")
    softvol_boot.restore(path)
    assert amixer.value("Gexis") == outputs.SOFTVOL_SCALE.raw(DAC.scale.db(150))
    assert amixer.value("DAC") == 150, "the card's own control is the core's to park"


def test_nothing_remembered_and_no_card_level_is_quiet(tmp_path, monkeypatch, amixer):
    _output(monkeypatch, HDMI)
    path = _store(tmp_path)
    softvol_boot.restore(path)
    assert amixer.value("Gexis") == outputs.SOFTVOL_SCALE.raw(softvol_boot.SOFTWARE_LEVEL_FIRST_DB)


def test_never_above_what_the_core_sets(tmp_path, monkeypatch, amixer):
    """One rule for both: what the boot step writes is what the core's
    `_start_software_volume` then writes, for every case above."""
    from gexis_core.__main__ import start_level as core_rule
    assert core_rule is softvol_boot.start_level
    assert softvol_boot.start_level(-12.0, -3.0) == -12.0
    assert softvol_boot.start_level(None, -3.0) == -3.0
    assert softvol_boot.start_level(None, None) == softvol_boot.SOFTWARE_LEVEL_FIRST_DB


def test_the_store_is_only_read(tmp_path, monkeypatch, amixer):
    _output(monkeypatch, HDMI)
    path = _store(tmp_path, _software_level_db=-42.5)
    before = path.read_bytes()
    softvol_boot.restore(path)
    assert path.read_bytes() == before


def test_no_store_writes_nothing_and_does_not_fail(tmp_path, amixer):
    assert "no settings store" in softvol_boot.restore(tmp_path / "missing.db")
    assert amixer.calls() == []


def test_a_control_that_does_not_take_is_reported_not_raised(tmp_path, monkeypatch, amixer):
    _output(monkeypatch, HDMI)
    monkeypatch.setattr(softvol_boot, "set_raw", lambda control, raw: None)
    path = _store(tmp_path, _software_level_db=-42.5)
    assert "did not take" in softvol_boot.restore(path)


def test_main_never_fails_the_boot(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("no card")
    monkeypatch.setattr(softvol_boot, "restore", boom)
    assert softvol_boot.main() == 0


def test_a_missing_card_is_waited_for_briefly_then_left(tmp_path, monkeypatch, amixer):
    _output(monkeypatch, HDMI)
    monkeypatch.setattr(outputs, "configured", lambda: "vc4hdmi0")
    cards = tmp_path / "cards"
    cards.write_text(" 0 [Headphones     ]: bcm2835_headpho - bcm2835 Headphones\n")
    monkeypatch.setattr(outputs, "CARDS", cards)
    monkeypatch.setattr(softvol_boot, "CARD_WAIT_S", 0.2)
    path = _store(tmp_path, _software_level_db=-42.5)
    assert "not listed" in softvol_boot.restore(path)
    assert amixer.writes() == []
    cards.write_text(cards.read_text() + " 1 [vc4hdmi0       ]: vc4-hdmi - vc4-hdmi-0\n")
    softvol_boot.restore(path)
    assert amixer.value("Gexis") == outputs.SOFTVOL_SCALE.raw(-42.5)


def test_the_unit_runs_before_every_renderer():
    unit = (Path(__file__).resolve().parents[2] / "image/stage-gexis/03-core/files/"
            "gexis-softvol-restore.service").read_text()
    before = " ".join(line.split("=", 1)[1] for line in unit.splitlines() if line.startswith("Before="))
    for renderer in ("squeezelite.service", "go-librespot.service", "bluealsa-aplay.service",
                     "plexamp.service"):
        assert renderer in before
    assert "Type=oneshot" in unit
    assert "-m gexis_core.softvol_boot" in unit


def test_with_the_equaliser_on_the_control_is_written_as_the_core_writes_it(tmp_path, monkeypatch, amixer):
    """ADR-0162 D3 as amended: the level with the headroom given back, which
    is what the core reads it back through - else the core read it 5 dB low
    and every slider showed it so."""
    from gexis_core import equaliser as eq
    from gexis_core import eq_control, volume
    _output(monkeypatch, HDMI)
    rock = eq.Equaliser().set_on("vc4hdmi0", True).choose("vc4hdmi0", "rock").to_settings()
    path = _store(tmp_path, output_device="HDMI 1", _software_level_db=-30.0, **{eq_control.KEY: rock})
    outcome = softvol_boot.restore(path)
    level = outputs.SOFTVOL_SCALE.raw(-30.0)
    given = volume.GiveBack(outputs.SOFTVOL_CONTROL, 5.0, outputs.SOFTVOL_SCALE)
    assert amixer.value("Gexis") == volume.to_control(level, given) == level + 20
    assert "5.0 dB of the equaliser's given back" in outcome
    off = eq.Equaliser().set_on("vc4hdmi0", False).choose("vc4hdmi0", "rock").to_settings()
    (tmp_path / "off").mkdir()
    softvol_boot.restore(_store(tmp_path / "off", output_device="HDMI 1", _software_level_db=-30.0,
                                **{eq_control.KEY: off}))
    assert amixer.value("Gexis") == level, "off: the level as it is"
