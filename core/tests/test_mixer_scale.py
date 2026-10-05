"""ADR-0117 decision 1: a volume control's scale comes from the card."""
from __future__ import annotations

from gexis_core import mixer_scale as ms
from gexis_core import volume

# As `amixer -c <card> contents` gives them on gexis, 2026-10-04.
DAC2_HD = """numid=2,iface=MIXER,name='DAC Playback Switch'
  ; type=BOOLEAN,access=rw------,values=1
  : values=off
numid=1,iface=MIXER,name='DAC Playback Volume'
  ; type=INTEGER,access=rw---R--,values=2,min=0,max=240,step=0
  : values=202,202
  | dBscale-min=-120.00dB,step=0.50dB,mute=1
"""
JACK = """numid=1,iface=MIXER,name='PCM Playback Volume'
  ; type=INTEGER,access=rw---R--,values=1,min=-10239,max=400,step=0
  : values=0
  | dBscale-min=-102.39dB,step=0.01dB,mute=1
"""
NO_DB = """numid=1,iface=MIXER,name='Master Playback Volume'
  ; type=INTEGER,access=rw------,values=2,min=0,max=255,step=0
  : values=200,200
"""
# A PCM512x (the IQaudio DAC+): the digital volume goes to +24 dB, and the
# analogue one is a two-step gain. Constructed from the codec's ranges, not
# read from a board.
PCM512X = """numid=3,iface=MIXER,name='Digital Playback Volume'
  ; type=INTEGER,access=rw---R--,values=2,min=0,max=255,step=0
  : values=207,207
  | dBscale-min=-103.50dB,step=0.50dB,mute=1
numid=1,iface=MIXER,name='Analogue Playback Volume'
  ; type=INTEGER,access=rw---R--,values=2,min=0,max=1,step=0
  : values=1,1
  | dBscale-min=-6.00dB,step=6.00dB,mute=0
"""


def test_the_dac2_hd_reads_as_adr_0018_measured_it():
    [(name, scale)] = ms.playback_controls(DAC2_HD)
    assert name == "DAC" and scale == ms.DAC2_HD
    assert scale.top == 240 and scale.db(202) == -19.0


def test_a_control_above_0_db_tops_out_at_0_db():
    [(_, jack)] = ms.playback_controls(JACK)
    assert jack.top == 0 and jack.db(jack.top) == 0.0 and jack.raw(-20.0) == -2000
    digital = ms.playback_controls(PCM512X)[0][1]
    assert digital.top == 207 and digital.db(207) == 0.0


def test_a_control_without_db_has_no_scale():
    assert ms.playback_controls(NO_DB) == [("Master", None)]


def test_the_player_writes_on_the_chosen_output_s_scale():
    try:
        volume.use_scale(ms.playback_controls(JACK)[0][1])
        assert volume.hardware_max() == 0
        assert volume.db_to_raw(-30.0) == -3000 and volume.raw_to_db(-3000) == -30.0
        assert volume.db_to_raw(+3.0) == 0, "never above 0 dB"
    finally:
        volume.use_scale(None)
    assert volume.hardware_max() == 240 and volume.raw_to_db(240) == 0.0
