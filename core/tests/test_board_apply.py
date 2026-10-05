"""ADR-0117 decision 3: the Sound card board setting, applied."""
from __future__ import annotations

from gexis_core import board_apply as ba

CONFIG = """dtparam=audio=on
dtoverlay=vc4-kms-v3d
[all]
disable_splash=1
"""


def test_the_options_start_with_found_by_itself_and_are_tagged():
    opts = ba.options()
    assert opts[0] == "Found by itself" and "IQaudIO/DAC Plus" in opts
    assert ba.tags()["HiFiBerry/DAC2 HD"] == "Tested" and ba.tags()["IQaudIO/DAC Plus"] == "Known"
    assert all(ba.by_label(o) for o in opts[1:])


def test_choosing_writes_one_block_and_leaves_the_rest(tmp_path):
    config, state = tmp_path / "config.txt", tmp_path / "board.json"
    config.write_text(CONFIG)
    assert ba.choose("IQaudIO/DAC Plus", config=config, state=state)
    text = config.read_text()
    assert text.startswith(CONFIG) and text.count("dtoverlay=iqaudio-dacplus\n") == 1
    assert ba.read_state(state) == {"chosen": "iqaudio-dacplus", "previous": None, "pending": True}
    assert ba.setting_value(state, config) == "IQaudIO/DAC Plus"
    # Another board replaces it; Found by itself removes it, and our [all].
    ba.choose("HiFiBerry/DAC2 HD", config=config, state=state)
    assert "iqaudio" not in config.read_text() and config.read_text().count("gexis: Sound card board") == 1
    ba.choose("Found by itself", config=config, state=state)
    assert config.read_text() == CONFIG
    assert not ba.choose("Found by itself", config=config, state=state), "nothing to change"


def test_a_board_whose_card_appears_is_kept(tmp_path):
    config, state = tmp_path / "config.txt", tmp_path / "board.json"
    config.write_text(CONFIG)
    ba.choose("IQaudIO/DAC Plus", config=config, state=state)
    assert ba.check(["Headphones", "IQaudIODAC"], config=config, state=state) is None
    assert ba.read_state(state)["pending"] is False and "iqaudio-dacplus" in config.read_text()
    assert ba.note(state) is None


def test_a_board_whose_card_does_not_appear_is_taken_back(tmp_path):
    config, state = tmp_path / "config.txt", tmp_path / "board.json"
    config.write_text(CONFIG)
    ba.choose("IQaudIO/DAC Plus", config=config, state=state)
    assert ba.check(["Headphones", "vc4hdmi0"], config=config, state=state) == "iqaudio-dacplus"
    assert config.read_text() == CONFIG
    assert ba.setting_value(state, config) == "Found by itself"
    assert "IQaudIO DAC Plus was not found" in ba.note(state)
    assert ba.check(["Headphones"], config=config, state=state) is None, "asked once"
