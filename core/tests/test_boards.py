"""ADR-0117: the boards gexis knows, from Volumio's list, read and corrected."""
from __future__ import annotations

from gexis_core import boards as b


def test_the_raspberry_pi_rows_are_read_and_most_are_offered():
    every = b.all_boards()
    assert len(every) == 99, "Volumio's 98, and the Pi-DAC PRO (Finding 114)"
    # Nine rows need an init script, which is not run here; the IQaudio
    # DAC+'s was corrected away.
    assert sum(not x.offered for x in every) == 8
    assert all(x.overlay and x.overlay == x.overlay.strip() for x in every)


def test_the_dac2_hd_names_itself_and_is_tested():
    board, state = b.identify("sndrpihifiberry", product="DAC 2 HD")
    assert board.id == "hifiberry-dac2hd" and state == "Tested"


def test_the_pi_dac_pro_names_itself_and_is_tested():
    """Finding 114: George's IQaudio board, by its EEPROM; the card it makes
    is shared, so the EEPROM is what tells it apart."""
    board, state = b.identify("IQaudIODAC", product="Pi-DAC PRO")
    assert board.id == "iqaudio-pi-dac-pro" and board.name == "IQaudIO Pi-DAC PRO" and state == "Tested"
    assert b.by_id("iqaudio-dacplus").tested is False, "the DAC+ itself is not tested"


def test_the_iqaudio_dac_plus_row_is_corrected():
    board = b.by_id("iqaudio-dacplus")
    assert board.dtoverlay == "dtoverlay=iqaudio-dacplus" and board.offered
    assert b.by_id("iqaudio-amp").dtoverlay == "dtoverlay=iqaudio-dacplus,unmute_amp"


def test_a_card_several_boards_make_is_known_and_the_choice_names_it():
    assert b.identify("IQaudIODAC") == (None, "Known")
    board, state = b.identify("IQaudIODAC", chosen="iqaudio-dacplus")
    assert board.name == "IQaudIO DAC Plus" and state == "Known"
    assert b.mixer_for("IQaudIODAC") == "Digital"


def test_a_choice_for_another_card_is_not_believed():
    assert b.identify("Katana", chosen="iqaudio-dacplus") == (None, "Known")


def test_an_unlisted_card_is_detected_and_the_pi_s_own_have_no_state():
    assert b.identify("UACDemoV10") == (None, "Detected")
    assert b.identify("Headphones") == (None, None)


def test_the_eeprom_is_read_without_its_trailing_nul(tmp_path):
    hat = tmp_path / "product"
    hat.write_bytes(b"DAC 2 HD \x00")
    assert b.hat_product(hat) == "DAC 2 HD"
    assert b.hat_product(tmp_path / "none") is None


def test_the_list_s_control_is_preferred_on_a_card_with_several(monkeypatch):
    from gexis_core import outputs
    # The analogue gain listed first, as a card may order them.
    contents = """numid=1,iface=MIXER,name='Analogue Playback Volume'
  ; type=INTEGER,access=rw---R--,values=2,min=0,max=1,step=0
  : values=1,1
  | dBscale-min=-6.00dB,step=6.00dB,mute=0
numid=3,iface=MIXER,name='Digital Playback Volume'
  ; type=INTEGER,access=rw---R--,values=2,min=0,max=255,step=0
  : values=207,207
  | dBscale-min=-103.50dB,step=0.50dB,mute=1
"""
    monkeypatch.setattr(outputs, "_run", lambda *a: contents)
    name, scale = outputs.playback_control("IQaudIODAC")
    assert name == "Digital" and scale.top == 207
    assert outputs.playback_control("SomeUSB")[0] == "Analogue"


def test_an_output_is_offered_with_its_state_and_found_by_its_old_name():
    from gexis_core.outputs import Output, resolve
    dac = Output(card="sndrpihifiberry", label="HiFiBerry DAC2 HD", control="DAC",
                 state="Tested", aka="HiFiBerry DAC+ HD")
    jack = Output(card="Headphones", label="Headphones (3.5 mm)", control="PCM")
    assert dac.option == "HiFiBerry DAC2 HD — Tested" and jack.option == "Headphones (3.5 mm)"
    for stored in ("HiFiBerry DAC+ HD", "HiFiBerry DAC2 HD — Tested", "HiFiBerry DAC2 HD"):
        assert resolve(stored, [jack, dac], current="Headphones") is dac
