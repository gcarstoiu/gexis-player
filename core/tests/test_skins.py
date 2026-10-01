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
    installed,
    load,
    parse,
    preview_of,
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


def test_the_setting_selects_by_kind_and_all_takes_everything():
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
    assert len(picked("All")) == 3
    # `All` was called `Random` until 2026-09-22 and a device may still hold
    # the old word (George: *"rename Random to All since it makes more
    # sense"* - `skin_rotate` is the one that is random).
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


def test_the_registry_offers_exactly_those_six():
    """Six words since 2026-09-27 - turntables and tapes are their own (ADR-0096
    as amended) - and `Random` is not one of them any more: it survives in
    `CORPUS` only so a value stored before the rename still resolves."""
    from gexis_core.settings_registry import load_registry

    row = next(r for g in load_registry() for r in g["rows"] if r.get("key") == "skin_corpus")
    assert row["options"] == ["VU meters", "Spectrum", "VU meters + spectrum", "Turntables", "Tapes", "All"]
    assert row["default"] == "VU meters"
    assert set(row["options"]) < set(CHOICES)


# ── what the picker asks for (ADR-0050) ──────────────────────────────────


def _pack(root, templates, text, pictures=()):
    directory = root / templates / "1280x800"
    directory.mkdir(parents=True)
    (directory / "meters.txt").write_text(text)
    for name in pictures:
        (directory / name).write_bytes(b"\xff\xd8not really a jpeg")
    return directory


def test_every_pack_on_the_device_is_found_and_the_first_name_wins(tmp_path):
    """The device carries more than one pack, each with its own directories
    and its own files - so a skin is found *with* the directory its
    `screen.bgr` sits in, and a name two packs share resolves to the one
    that would be selected.

    **All of them, which is 99 on this device.** For a few hours on
    2026-09-22 this listed Gelo5's 84 alone, on the argument that the
    spectrum engine was pointed at Gelo5's sections - which described a
    hardcoded path rather than the device (ADR-0051 §2, amended). Narrowing
    to one pack is still possible and is nobody's default."""
    _pack(tmp_path / "gelo5", "templates", "[one]\nscreen.bgr = a.jpg\n", ["a.jpg"])
    _pack(tmp_path / "stock", "templates", "[one]\nscreen.bgr = b.jpg\n[two]\nscreen.bgr = c.jpg\n",
          ["b.jpg", "c.jpg"])
    found = installed(tmp_path)
    assert [skin.name for skin, _ in found] == ["one", "two"]
    first, directory = found[0]
    assert preview_of(first, directory).name == "a.jpg"

    assert [s.name for s, _ in installed(tmp_path, pack="stock")] == ["one", "two"]


def test_a_preview_is_the_file_the_skin_names_and_nothing_else(tmp_path):
    """ADR-0050: nothing is rendered, so a preview is a lookup - and a skin
    that names a path rather than a file names nothing."""
    directory = _pack(tmp_path / "pack", "templates",
                      "[good]\nscreen.bgr = ok.jpg\n"
                      "[missing]\nscreen.bgr = gone.jpg\n"
                      "[sneaky]\nscreen.bgr = ../../../etc/shadow\n"
                      "[silent]\nmeter.type = circular\n",
                      ["ok.jpg"])
    by_name = {skin.name: skin for skin, _ in installed(tmp_path, pack="pack")}
    assert preview_of(by_name["good"], directory).name == "ok.jpg"
    assert preview_of(by_name["missing"], directory) is None
    assert preview_of(by_name["sneaky"], directory) is None
    assert preview_of(by_name["silent"], directory) is None


def test_every_committed_skin_has_a_picture_to_show(corpus):
    """**This is what replaces a build step.** ADR-0050 removes the render
    and the cache, so the only thing that can make the picker empty is a
    skin that names no background - and every one of the 84 does."""
    meters, _ = corpus
    assert all((skin.options.get("screen.bgr") or "").strip() for skin in meters)


# ── what the renderer is told (ADR-0051) ─────────────────────────────────


def test_the_corpus_word_decides_which_names_the_picker_offers(tmp_path):
    """The pool is what a skin *shows*, and it spans both of the pack's
    template directories - which is the whole point: the directory the
    engine loads holds 71 meters and no spectrum at all, so "Spectrum"
    against one directory is an empty picker."""
    _pack(tmp_path / "gelo5", "templates",
          "[01G5_Needle]\nscreen.bgr = a.jpg\n")
    _pack(tmp_path / "gelo5", "templates_spectrum",
          "[101G5_Bars]\nspectrum.visible = True\nmeter.visible = False\n"
          "[102G5_Both]\nspectrum.visible = True\n")

    from gexis_core.skins import names

    assert names(tmp_path, "VU meters") == ["01G5_Needle"]
    assert names(tmp_path, "Spectrum") == ["101G5_Bars"]
    assert names(tmp_path, "VU meters + spectrum") == ["102G5_Both"]
    assert names(tmp_path, "Random") == ["01G5_Needle", "101G5_Bars", "102G5_Both"]
    # An unknown word is every skin rather than none: a screen drawing the
    # wrong pool beats a screen drawing nothing.
    assert names(tmp_path, "nonsense") == names(tmp_path, "Random")


def test_the_selection_is_published_whole_or_not_at_all(tmp_path):
    """The driver reads this inside a frame hook, so it must never see half
    a file (ADR-0051 §1): written to a temporary name and renamed."""
    from gexis_core.skins import write_selection
    import json

    path = tmp_path / "run" / "visualisation.json"
    assert write_selection("Spectrum", "101G5_Bars", False, path) is True
    assert json.loads(path.read_text()) == {
        "corpus": "Spectrum", "skin": "101G5_Bars", "rotate": False,
        "motion": True, "record_rpm": 33.0, "smooth": False,
    }
    assert not list(path.parent.glob("*.tmp"))

    # A second write replaces it, and nothing else is left behind.
    assert write_selection("Random", None, True, path) is True
    assert json.loads(path.read_text())["skin"] is None


def test_a_selection_that_cannot_be_written_is_not_fatal(tmp_path):
    """The setting is stored either way. A screen still drawing the previous
    skin beats a daemon that fell over publishing a preference."""
    from gexis_core.skins import write_selection

    blocked = tmp_path / "file"
    blocked.write_text("not a directory")
    assert write_selection("Random", None, True, blocked / "visualisation.json") is False


def test_a_skin_named_broken_is_not_offered(tmp_path):
    """The mechanism, exercised against a name put there by the test.

    `BROKEN` itself is empty (Finding 050): the two skins that were on it
    are fixed and offered again. The machinery stays, because the next one
    seen to render wrong should be removable in one line."""
    from gexis_core import skins

    pack = tmp_path / "gelo5" / "templates_spectrum" / skins.RESOLUTION
    pack.mkdir(parents=True)
    (pack / "meters.txt").write_text(
        "[a bad one]\nmeter.type = circular\n\n"
        "[a good one]\nmeter.type = circular\n"
    )

    skins.BROKEN["a bad one"] = "put here by this test"
    try:
        offered = [s.name for s, _ in skins.installed(tmp_path)]
    finally:
        del skins.BROKEN["a bad one"]

    assert "a good one" in offered
    assert "a bad one" not in offered


def test_the_broken_list_says_why_for_each(tmp_path):
    """A name with no reason is a name nobody can ever remove again.

    Empty is the expected state: five models of "which skins are broken"
    were built from the numbers and all five were wrong, so a name only
    belongs here once someone has seen it render wrong."""
    from gexis_core import skins

    assert all(len(why) > 20 for why in skins.BROKEN.values())


# --- ADR-0096: the animated packs ------------------------------------------

ANIMATED_PACKS = sorted((CORPUS / "animated").glob("*/meters.txt"))


def test_the_four_animated_packs_are_here_and_validate():
    """48 turntables, 20 tape recorders and 15 cassette decks at 1280x720, and
    Pakit S's seven at 1280x800 - kept exactly as upstream ships them."""
    counts = {p.parent.name: len(parse(p.read_text(encoding="utf-8", errors="replace")))
              for p in ANIMATED_PACKS}
    assert counts == {
        "1280x720_g5_710_Turntables": 48,
        "1280x720_g5_711_Tape_Recorder": 20,
        "1280x720_g5_712_Cassette": 15,
        "1280x800_t1800_pack7": 7,
    }
    for pack in ANIMATED_PACKS:
        validate(parse(pack.read_text(encoding="utf-8", errors="replace")), animated=True)


def test_the_static_corpus_is_still_held_to_what_it_was():
    """The motion and deferred keys are admitted for the animated packs only."""
    with pytest.raises(SkinError, match="unknown key 'vinyl.filename'"):
        validate([Skin("x", {"meter.type": CIRCULAR, "vinyl.filename": "v.png"})])
    with pytest.raises(SkinError, match="unknown key 'progress.pos'"):
        validate([Skin("x", {"meter.type": CIRCULAR, "progress.pos": "1,2"})])


def test_an_animated_pack_still_fails_on_a_key_nobody_placed():
    """Admitting the deferred families by prefix must not admit everything."""
    with pytest.raises(SkinError, match="unknown key 'sparkle'"):
        validate([Skin("x", {"meter.type": CIRCULAR, "sparkle": "1", "tonearm.filename": "a"})],
                 animated=True)


def test_a_skin_with_no_screen_background_is_previewed_by_its_meters(tmp_path):
    """ADR-0096: 80 of the 90 animated skins set no `screen.bgr` and showed
    as blank tiles. Their meter's background is the full picture."""
    directory = _pack(tmp_path / "pack", "templates",
                      "[turntable]\nbgr.filename = deck.png\n"
                      "[both]\nscreen.bgr = ok.jpg\nbgr.filename = deck.png\n"
                      "[sneaky]\nbgr.filename = ../../../etc/shadow\n",
                      ["ok.jpg", "deck.png"])
    by_name = {skin.name: skin for skin, _ in installed(tmp_path, pack="pack")}
    assert preview_of(by_name["turntable"], directory).name == "deck.png"
    assert preview_of(by_name["both"], directory).name == "ok.jpg"
    assert preview_of(by_name["sneaky"], directory) is None


def test_a_record_or_reels_make_a_turntable_or_a_tape(tmp_path):
    """ADR-0096 as amended, George: "One for turntables and another for
    tapes." By what a skin declares, never by its directory."""
    _pack(tmp_path / "pack", "templates",
          "[deck]\nmeter.type = circular\nvinyl.filename = v.png\n"
          "[arm only]\nmeter.type = circular\ntonearm.filename = a.png\n"
          "[reels]\nmeter.type = linear\nreel.left.filename = r.png\n"
          "[needles]\nmeter.type = circular\n",
          [])
    kinds = {s.name: s.kind for s, _ in installed(tmp_path, pack="pack")}
    assert kinds == {"deck": "turntable", "arm only": "turntable", "reels": "tape", "needles": "meters"}
    found = [s for s, _ in installed(tmp_path, pack="pack")]
    from gexis_core.skins import in_corpus
    assert [s.name for s in in_corpus(found, "Turntables")] == ["deck", "arm only"]
    assert [s.name for s in in_corpus(found, "Tapes")] == ["reels"]
    assert [s.name for s in in_corpus(found, "VU meters")] == ["needles"]
    assert len(in_corpus(found, "All")) == 4


def test_the_record_speed_word_is_a_number():
    from gexis_core.skins import record_rpm
    assert record_rpm("45 rpm") == 45.0
    assert record_rpm("33 rpm") == 33.0
    assert record_rpm(None) == 33.0


def test_a_pack_of_another_size_is_read_from_its_own_folder(tmp_path):
    """ADR-0111: `<root>/<folder>/templates/<W>x<H>`, not always 1280x800."""
    from gexis_core import skins

    folder = tmp_path / "gelo5" / "templates" / "800x480"
    folder.mkdir(parents=True)
    (folder / "meters.txt").write_text("[small]\nmeter.type = linear\nscreen.bgr = bg.png\n")
    assert [s.name for s, _ in skins.installed(tmp_path, resolution="800x480")] == ["small"]
    assert skins.installed(tmp_path) == []
