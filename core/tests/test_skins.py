"""Phase 5 criteria 2 and 3 — the corpus validator (tier 4).

Runs against the real 84 skins in `skins/`, not a fixture: the point of this
check is that a skin pack breaking the contract fails the build.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from gexis_core.skins import (
    CIRCULAR,
    LINEAR,
    Skin,
    SkinError,
    load,
    parse,
    validate,
)

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
