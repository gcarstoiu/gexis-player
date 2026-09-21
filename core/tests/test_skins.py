"""Phase 5 criteria 2 and 3 — the corpus validator (tier 4).

Runs against the real 84 skins in `skins/`, not a fixture: the point of this
check is that a skin pack breaking the contract fails the build.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from gexis_core.skins import (
    BOTH,
    CIRCULAR,
    LINEAR,
    METERS,
    SPECTRUM,
    Skin,
    SkinError,
    in_corpus,
    load,
    parse,
    validate,
)
from gexis_core.skins import CORPUS as CHOICES

CORPUS = Path(__file__).parents[2] / "skins"


@pytest.fixture(scope="module")
def corpus():
    return load(CORPUS)


def test_the_whole_corpus_is_84_skins_of_two_types(corpus):
    meters, spectrum = corpus
    assert len(meters) == 84
    assert sum(1 for s in meters if s.meter_type == CIRCULAR) == 66
    assert sum(1 for s in meters if s.meter_type == LINEAR) == 18
    assert len(spectrum) == 13


def test_the_whole_corpus_validates(corpus):
    meters, spectrum = corpus
    validate(meters, spectrum)


def test_spectrum_links_resolve_by_name(corpus):
    meters, spectrum = corpus
    linked = [s for s in meters if s.spectrum_name]
    assert len(linked) == 13
    names = {s.name for s in spectrum}
    assert all(s.spectrum_name in names for s in linked)


def test_the_link_is_by_name_not_position(corpus):
    """This corpus happens to list spectrum sections in the same order as the
    skins that link to them, so order alone proves nothing — reversing the
    spectrum list must not change the outcome."""
    meters, spectrum = corpus

    validate(meters, list(reversed(spectrum)))

    with pytest.raises(SkinError, match="matches no spectrum section"):
        validate(meters, [Skin(f"renamed-{i}", s.options) for i, s in enumerate(spectrum)])


def test_meter_visible_false_is_honoured(corpus):
    meters, _ = corpus
    hidden = [s for s in meters if not s.visible]
    assert hidden, "the corpus has spectrum-only skins with meter.visible = False"
    assert all(s.options.get("meter.visible", "").lower() == "false" for s in hidden)


def test_comments_and_blank_lines_are_not_options():
    skins = parse("[a]\n# comment\nmeter.type = linear\n\n\n[b]\nmeter.type = circular\n")
    assert [s.name for s in skins] == ["a", "b"]
    assert skins[0].options == {"meter.type": "linear"}


def test_an_unknown_meter_type_fails_the_build():
    with pytest.raises(SkinError, match="meter.type 'wobbly'"):
        validate([Skin("x", {"meter.type": "wobbly"})])


def test_an_unknown_key_fails_the_build():
    with pytest.raises(SkinError, match="unknown key 'sparkle'"):
        validate([Skin("x", {"meter.type": "circular", "sparkle": "1"})])


def test_a_key_from_the_other_meter_type_fails_the_build():
    """`steps.per.degree` is circular-only; a linear skin carrying it is a
    mistake the permissive runtime parser would ignore."""
    with pytest.raises(SkinError, match="unknown key 'steps.per.degree'"):
        validate([Skin("x", {"meter.type": LINEAR, "steps.per.degree": "4"})])


def test_a_dangling_spectrum_link_fails_the_build():
    with pytest.raises(SkinError, match="matches no spectrum section"):
        validate([Skin("x", {"meter.type": CIRCULAR, "spectrum.name": "Nope"})], [])


def test_every_problem_is_reported_not_just_the_first():
    with pytest.raises(SkinError) as err:
        validate([Skin("x", {"meter.type": CIRCULAR, "a": "1", "b": "2"})])
    assert "2 problem(s)" in str(err.value)

# ── what a skin shows, which is not where it lives (9h) ───────────────────

SHAPES = """
[01G5_Accuphase]
meter.type = circular
bgr.filename = Accuphase_Hybrid_1280_vu.png

[103G5_Marschal Spectrum]
meter.type = linear
meter.visible = False
spectrum.visible = True

[101G5_Free S+M]
meter.type = linear
meter.visible = True
spectrum.visible = True
"""


def test_a_skin_says_what_it_shows_and_absence_means_a_meter():
    """Measured over the shipped corpus, 2026-09-21: **77 of its 99 skins
    declare neither key**, and every one of them is a VU face. So an absent
    `meter.visible` means a meter and an absent `spectrum.visible` means no
    spectrum - an asymmetry that is the corpus's, not ours."""
    assert {skin.name: skin.kind for skin in parse(SHAPES)} == {
        "01G5_Accuphase": METERS,
        "103G5_Marschal Spectrum": SPECTRUM,
        "101G5_Free S+M": BOTH,
    }


def test_the_setting_selects_by_kind_and_random_takes_all():
    """George, 2026-09-21: three kinds where the setting offered two, plus
    one that takes any of them. **The two it offered were directories** -
    and `templates/` is not the meter corpus: the stock pack's copy of it
    holds six spectrum-only skins and three that show both, so "Meter only"
    would have handed a spectrum to someone who asked for a needle."""
    corpus = parse(SHAPES)
    picked = lambda choice: [s.name for s in in_corpus(corpus, choice)]
    assert picked("VU meters") == ["01G5_Accuphase"]
    assert picked("Spectrum") == ["103G5_Marschal Spectrum"]
    assert picked("VU meters + spectrum") == ["101G5_Free S+M"]
    assert len(picked("Random")) == 3
    # An unknown choice is every skin rather than none: a screen with
    # nothing to draw is worse than one drawing from the wrong pool.
    assert len(picked("whatever the registry said last year")) == 3


def test_the_shipped_corpus_has_all_three_kinds(corpus):
    """The committed Gelo5 pack, counted. The device carries the stock pack
    as well (15 more: 6, 6 and 3), which is where the 99 in the docstrings
    comes from - this asserts the part that is in the repository."""
    meters, _ = corpus
    counted = {kind: sum(1 for s in meters if s.kind == kind)
               for kind in (METERS, SPECTRUM, BOTH)}
    assert counted == {METERS: 71, SPECTRUM: 3, BOTH: 10}


def test_the_registry_offers_exactly_those_four():
    from gexis_core.settings_registry import load_registry

    row = next(r for g in load_registry() for r in g["rows"] if r.get("key") == "skin_corpus")
    assert row["options"] == list(CHOICES)
    assert row["default"] == "VU meters"
