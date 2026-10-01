"""ADR-0109: the screens gexis offers, seeded from foonerd's presets."""
from __future__ import annotations

import collections

from gexis_core import screens


def test_every_model_is_listed_and_the_two_modes_are_not():
    """Decision 1: all of them. *Auto Detect* and *Custom HDMI Timings* are
    not screens."""
    listed = screens.all_screens()
    # 192 models, less the 11 square and round ones George left out.
    assert len(listed) == 181
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
    assert makers["Waveshare"] > 90 and "GeeekPi" in makers and "Generic" in makers


def test_george_s_four_are_the_tested_ones():
    """Decision 1: the four Waveshare HDMI screens George owns."""
    tested = {s.id for s in screens.all_screens() if s.tested}
    assert tested == set(screens.TESTED) and len(tested) == 4
    assert all(screens.by_id(i).maker == "Waveshare" and screens.by_id(i).interface == "hdmi" for i in tested)
