"""ADR-0109: the screens gexis offers, seeded from foonerd's presets."""
from __future__ import annotations

import collections

from gexis_core import screens


def test_every_model_is_listed_and_the_two_modes_are_not():
    """Decision 1: all of them. *Auto Detect* and *Custom HDMI Timings* are
    not screens."""
    listed = screens.all_screens()
    # 192 models, less the 11 square and round ones George left out, less
    # the DPI screens, and a case listed once as its panel (2026-10-03): 106
    # HDMI; our own non-touch HMTECH 10.1" (2026-10-20): 107. ADR-0158: 58
    # DSI models and the Touch Display class: 166.
    assert len(listed) == 166
    assert {s.interface for s in listed} == {"hdmi", "dsi"}
    assert sum(s.interface == "hdmi" for s in listed) == 107
    assert not {s.id for s in listed} & screens.NOT_MODELS
    assert len({s.label for s in listed}) == len(listed), "the picker's labels are unique"


def test_george_s_bars_are_bars_used_sideways():
    """Finding 100: both are portrait panels driven sideways."""
    for screen_id, size in (("waveshare-7.9-hdmi", (1280, 400)), ("waveshare-11.9-hdmi", (1480, 320))):
        s = screens.by_id(screen_id)
        assert (s.width, s.height) == size and s.family == "bar" and s.rotation == 90


def test_the_standard_screens_are_standard():
    assert screens.by_id("waveshare-13.3-hdmi-h").family == "standard"
    assert screens.by_id("waveshare-10.1-hdmi-b").family == "standard"


def test_nothing_is_offered_upright():
    """Decision 6: portrait is not designed; 0° is the model's landscape."""
    assert all(s.width / s.height >= screens.SQUARE_BELOW for s in screens.all_screens())


def test_a_maker_never_contains_the_picker_s_separator():
    assert all("/" not in s.maker and "/" not in s.model for s in screens.all_screens())
    makers = collections.Counter(s.maker for s in screens.all_screens())
    assert makers["Waveshare"] > 30 and "GeeekPi" in makers and "Generic" in makers


def test_george_s_screens_are_the_tested_ones():
    """Decision 1: the four Waveshare HDMI screens George owns, from
    2026-10-20 the two HMTECHs tried on sofapi, and from 2026-10-23 the
    Hosyond 7" DSI on bedroompi with the class it is recognised as
    (ADR-0158)."""
    tested = {s.id for s in screens.all_screens() if s.tested}
    assert tested == set(screens.TESTED) and len(tested) == 8
    hdmi = {i for i in tested if screens.by_id(i).interface == "hdmi"}
    assert {screens.by_id(i).maker for i in hdmi} == {"Waveshare", "HMTECH"} and len(hdmi) == 6
    assert tested - hdmi == {"hosyond-7-dsi", screens.TOUCH_DISPLAY_CLASS}


def test_every_dsi_model_in_the_list_is_offered_with_its_overlay():
    """ADR-0158 D1 (George, 2026-10-23: *"For all that we have in the dsi
    list that we deferred until now"*): 58 models - 23 the firmware brings
    up by itself (nothing to write), 35 with the overlay the list gives
    them; the 3 that need KMS removed and the 2 on Waveshare's own overlay
    left out."""
    dsi = [s for s in screens.all_screens() if s.interface == "dsi" and s.id != screens.TOUCH_DISPLAY_CLASS]
    assert len(dsi) == 58
    assert sum(not s.overlays for s in dsi) == 23 and sum(bool(s.overlays) for s in dsi) == 35
    assert screens.by_id("hosyond-7-dsi").overlays == ()
    assert screens.by_id("rpi-touch-7inch").overlays == (), "the original: found by the firmware"
    assert screens.by_id("rpi-touch2-7inch").overlays == ("vc4-kms-dsi-ili9881-7inch",)
    for gone in ("waveshare-dsi-4.3-rev1-knockout", "btt-pitft50-v1.0", "dfrobot-dsi-5-tft-v1.0",
                 "waveshare-dsi-3.5e", "waveshare-dsi-3.5h"):
        assert screens.by_id(gone) is None, gone
    assert all(o.split(",", 1)[0] not in screens.FIRMWARE_FINDS for s in dsi for o in s.overlays)
    assert all(s.overlays == () for s in screens.all_screens() if s.interface == "hdmi")


def test_a_four_lane_model_is_offered_only_where_the_board_has_four_lanes(tmp_path):
    """ADR-0158 D6."""
    four = {s.id for s in screens.all_screens() if s.lanes == 4}
    assert four == {"waveshare-dsi-v2-8.0a-4lane", "waveshare-dsi-v2-9.0b-4lane", "waveshare-dsi-v2-10.1a-4lane",
                    "waveshare-dsi-v2-10.1b-4lane", "waveshare-dsi-v2-12.3a-4lane", "waveshare-dsi-13.3-4lane"}
    assert screens.by_id("waveshare-dsi-v2-10.1a").lanes == 2 and screens.by_id("waveshare-dsi-13.3-2lane").lanes == 2
    model = tmp_path / "model"
    model.write_text("Raspberry Pi 4 Model B Rev 1.5\x00")
    assert screens.board_lanes(model) == 2
    pi4 = screens.offered(model)
    assert not four & {s.id for s in pi4}
    dsi = [s for s in pi4 if s.interface == "dsi" and s.id != screens.TOUCH_DISPLAY_CLASS]
    assert len(dsi) == 52 and sum(bool(s.overlays) for s in dsi) == 29
    assert screens.by_id("waveshare-dsi-v2-10.1a-4lane").label.endswith("4-lane (800x1280)"), \
        "a choice already made keeps its name"
    for board in ("Raspberry Pi 5 Model B Rev 1.0", "Raspberry Pi Compute Module 4 Rev 1.0",
                  "Raspberry Pi Compute Module 5 Rev 1.0"):
        model.write_text(board + "\x00")
        assert screens.board_lanes(model) == 4 and screens.offered(model) == screens.all_screens(), board
    model.write_text("Raspberry Pi 500 Rev 1.0\x00")
    assert screens.board_lanes(model) == 2, "the keyboard Pi 5 is not a Pi 5 Model B"
    model.write_text("Some other board\x00")
    assert screens.offered(model) == screens.all_screens()
    assert screens.offered(tmp_path / "absent") == screens.all_screens()


def test_a_recognised_dsi_panel_is_named_for_its_class():
    """ADR-0158 D2: nothing the Pi reads tells the Touch Display's makers
    apart, so a panel recognised and not chosen is the class - 800 x 480,
    Standard, nothing written - and a model picked keeps its own name."""
    cls = screens.by_id(screens.TOUCH_DISPLAY_CLASS)
    assert cls.interface == "dsi" and (cls.width, cls.height) == (800, 480) and cls.family == "standard"
    assert cls.overlays == () and cls.tested
    assert cls.label == "Raspberry Pi/Touch Display or compatible (DSI, 800x480)"
    assert screens.by_label('Hosyond/7" DSI Display (800x480)').id == "hosyond-7-dsi"


def test_a_case_is_listed_once_as_its_panel():
    """George, 2026-10-03: "In general the box and non box i would say are the
    same" - his 10.1" (B) came in its case and was offered twice."""
    names = [s.model for s in screens.all_screens() if s.maker == "Waveshare"]
    assert not any("with Case" in n for n in names)
    assert len(names) == len(set(names))
    panel = screens.by_id("waveshare-10.1-hdmi-b")
    assert panel.tested
    assert screens.by_id("waveshare-10.1-hdmi-b-case") == panel, "a choice saved by id still finds it"
    assert screens.by_label('Waveshare/10.1" HDMI LCD (B) with Case (1280x800)') == panel
    alone = screens.by_id("waveshare-10.1-hdmi-d-case")
    assert alone is not None and alone.model == '10.1" HDMI LCD (D) (1024x600)', "no bare twin: renamed"


def test_a_screen_from_its_own_mode_is_found_by_its_name():
    """ADR-0109 (George, 2026-10-12): Settings names one "Other screen/W × H",
    and the name has to lead back to a screen - from a backup too, on a card
    whose screen state is not the backup's."""
    found = screens.by_label("Other screen/1920 × 1080")
    assert found is not None and found.id == "other-1920x1080" and found.rotation == 0
    assert screens.by_label("Other screen/1920 x 1080") is None


def test_our_own_entry_is_listed_beside_the_vendored_one():
    """George's HMTECH 10.1" has no touch; the list's HMTECH 10.1" is the
    touch model. Both are listed; only ours is tested."""
    ours, theirs = screens.by_id("hmtech-10.1-hdmi-monitor"), screens.by_id("hmtech-10.1-hdmi")
    assert ours.tested and not theirs.tested
    assert (ours.width, ours.height) == (1024, 600) and ours.maker == "HMTECH"
