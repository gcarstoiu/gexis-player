"""The driver's own rules (ADR-0051).

The driver is a script in the image stage, not a package: it is loaded here
by path, the way the image installs it, so what is tested is the file that
ships. Everything below is the part that decides *what to draw* - no pygame
surface, no engine.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

DRIVER = (
    Path(__file__).parents[2]
    / "image/stage-gexis/05-peppy/files/gexis-peppy-driver.py"
)


_ABSENT = object()


def _driver():
    """Loaded with a stand-in for pygame.

    The driver imports it at the top and uses it only where a surface is
    involved; none of what is tested here touches one. Stubbing it keeps
    these rules testable on a machine with no pygame, which is every machine
    but the device.
    """
    stub = types.ModuleType("pygame")
    # The one thing the driver reads at import: the touch events it filters
    # for. Everything else it wants from pygame needs a surface, and nothing
    # here has one.
    stub.MOUSEBUTTONUP = 1025
    stub.FINGERUP = 1795
    was = sys.modules.get("pygame", _ABSENT)
    sys.modules["pygame"] = stub
    try:
        spec = importlib.util.spec_from_file_location("gexis_peppy_driver", DRIVER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        # **Put it back**, whatever it was. Left in place, the stub answers
        # the neighbouring suite's `importorskip("pygame")` and turns its
        # clean skip into fifteen errors on a machine with no pygame.
        if was is _ABSENT:
            del sys.modules["pygame"]
        else:
            sys.modules["pygame"] = was


driver = _driver()


# ── what a skin shows ────────────────────────────────────────────────────


def test_a_kind_comes_from_what_the_skin_declares():
    """The same derivation the daemon makes (`gexis_core.skins.Skin.kind`),
    and for the same reason: `templates/` is not the meter corpus."""
    assert driver.kind_of({}) == driver.METERS
    assert driver.kind_of({"meter.visible": "True"}) == driver.METERS
    assert driver.kind_of({"spectrum.visible": "True"}) == driver.BOTH
    assert (
        driver.kind_of({"spectrum.visible": "True", "meter.visible": "False"})
        == driver.SPECTRUM
    )
    # Spelling is the corpus's, not ours.
    assert driver.kind_of({"spectrum.visible": " true "}) == driver.BOTH


# ── the selection file ───────────────────────────────────────────────────


def _write(path, **fields):
    path.write_text(json.dumps(fields))


def test_a_selection_is_read_once_per_change(tmp_path):
    path = tmp_path / "visualisation.json"
    selection = driver.Selection(path)
    # Nothing there yet: the defaults stand and nothing has changed.
    assert selection.reload() is False
    assert (selection.corpus, selection.skin, selection.rotate) == ("All", None, True)

    _write(path, corpus="Spectrum", skin="101G5_Bars", rotate=False)
    assert selection.reload() is True
    assert (selection.corpus, selection.skin, selection.rotate) == (
        "Spectrum",
        "101G5_Bars",
        False,
    )
    # Unmoved: a stat, and no read.
    assert selection.reload() is False


def test_a_selection_that_will_not_parse_leaves_what_we_had(tmp_path):
    """The settings database is the record and this is a projection of it,
    so a truncated file is a reason to keep drawing, not to stop."""
    path = tmp_path / "visualisation.json"
    _write(path, corpus="Spectrum", skin="101G5_Bars", rotate=False)
    selection = driver.Selection(path)
    selection.reload()

    path.write_text('{"corpus": "Spec')
    assert selection.reload() is False
    assert selection.corpus == "Spectrum"


SKINS = {
    "01G5_Needle": {},
    "101G5_Bars": {"spectrum.visible": "True", "meter.visible": "False"},
    "102G5_Both": {"spectrum.visible": "True"},
}


def test_the_corpus_word_decides_the_pool():
    selection = driver.Selection()
    for word, expected in [
        ("VU meters", ["01G5_Needle"]),
        ("Spectrum", ["101G5_Bars"]),
        ("VU meters + spectrum", ["102G5_Both"]),
        ("All", list(SKINS)),
        # still understood, for a file written before the 2026-09-22 rename
        ("Random", list(SKINS)),
    ]:
        selection.corpus = word
        assert selection.pool(SKINS) == expected


def test_a_pool_is_never_empty():
    """A word we do not know, or one this pack cannot satisfy, draws from
    everything rather than from nothing: a wrong pool beats a black screen."""
    selection = driver.Selection()
    selection.corpus = "nonsense"
    assert selection.pool(SKINS) == list(SKINS)
    selection.corpus = "Spectrum"
    assert selection.pool({"01G5_Needle": {}}) == ["01G5_Needle"]


# ── the corpus is the pack, not the directory ────────────────────────────


def _pack(root, templates, text):
    directory = root / "gelo5" / templates / "1280x800"
    directory.mkdir(parents=True)
    (directory / "meters.txt").write_text(text)
    return directory


def test_both_template_directories_are_loaded_with_where_each_skin_lives(tmp_path):
    meters = _pack(tmp_path, "templates", "[01G5_Needle]\nmeter.type = circular\n")
    spectra = _pack(
        tmp_path,
        "templates_spectrum",
        "[101G5_Bars]\nmeter.type = linear\nspectrum.visible = True\n",
    )
    skins, homes = driver.load_corpus(meters.parent, "1280x800")
    assert list(skins) == ["01G5_Needle", "101G5_Bars"]
    assert homes == {"01G5_Needle": meters, "101G5_Bars": spectra}


def test_every_pack_is_loaded_and_the_configured_one_comes_first(tmp_path):
    """99 skins on this device, not one pack's 84 (ADR-0051 §2, amended
    2026-09-22). The configured pack is first so a fresh device still starts
    on the skin it has always started on."""
    gelo = _pack(tmp_path, "templates", "[01G5_Needle]\nmeter.type = circular\n")
    stock = (tmp_path / "stock" / "templates" / "1280x800")
    stock.mkdir(parents=True)
    (stock / "meters.txt").write_text("[s.one]\nmeter.type = linear\n")

    skins, homes = driver.load_corpus(gelo.parent, "1280x800")
    assert list(skins) == ["01G5_Needle", "s.one"]
    assert homes["s.one"] == stock


def test_a_skins_spectrum_sections_come_from_its_own_pack(tmp_path):
    """The stock pack's skins name `s.1`…`s.9`, which Gelo5 has never heard
    of: the engine has to be pointed at the pack the skin belongs to."""
    home = tmp_path / "skins" / "stock" / "templates" / "1280x800"
    assert driver.spectrum_base(home) == tmp_path / "skins" / "stock" / "templates_spectrum"


def test_a_name_in_both_directories_resolves_to_the_first(tmp_path):
    meters = _pack(tmp_path, "templates", "[same]\nmeter.type = circular\n")
    _pack(tmp_path, "templates_spectrum", "[same]\nmeter.type = linear\n")
    skins, homes = driver.load_corpus(meters.parent, "1280x800")
    assert list(skins) == ["same"]
    assert homes["same"] == meters


def test_a_pack_with_one_directory_is_still_a_corpus(tmp_path):
    meters = _pack(tmp_path, "templates", "[01G5_Needle]\nmeter.type = circular\n")
    skins, _ = driver.load_corpus(meters.parent, "1280x800")
    assert list(skins) == ["01G5_Needle"]
