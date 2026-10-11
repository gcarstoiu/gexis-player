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


class _FakeMixer:
    def __init__(self):
        self.values = []

    def set(self, value):
        self.values.append(value)
        return True


async def test_silence_on_the_headphone_jack_is_its_bottom_not_raw_0():
    """**Code review, 2026-10-12.** Everything treated raw 0 as silence, which
    holds on the DAC2 HD's 0..240 and nowhere else: on the jack's -10239..400
    raw 0 is 0 dB. Mute, a renderer's 0 and the slider's 0% all wrote it -
    full scale into headphones - and every real (negative) level read back
    as 0%, which was then handed to Spotify and came back as full scale."""
    jack = ms.playback_controls(JACK)[0][1]
    try:
        volume.use_scale(jack)
        assert volume.hardware_silence() == -10239
        assert volume.renderer_value_to_hardware_raw(0, 100) == -10239
        assert volume.slider_percent_to_raw(0) == -10239
        assert volume.spotify_fraction_to_hardware_raw(0.0) == -10239
        # Real levels read back as themselves, not as 0%.
        assert volume.raw_to_slider_percent(volume.slider_percent_to_raw(50)) == 50
        assert volume.raw_to_slider_percent(-2000) > 0
        assert volume.raw_to_slider_percent(-10239) == 0

        writes = []

        async def write(raw):
            writes.append(raw)

        mute = volume.Mute(write, lambda: -2000)
        await mute.set(True)
        assert writes == [-10239], "mute writes the bottom, never 0 dB"
        mute.observe(-10239)
        assert mute.muted, "its own silence does not end mute"
        await mute.set(False)
        assert writes == [-10239, -2000]
    finally:
        volume.use_scale(None)
    assert volume.hardware_silence() == 0


async def test_a_level_given_to_another_scale_is_clamped_to_that_scale():
    """`set_raw` with a scale of its own clamped below at 0: the jack's
    -20 dB (raw -2000), handed back to the card when the software stage is
    switched off, was written as raw 0 - 0 dB there."""
    jack = ms.playback_controls(JACK)[0][1]
    fake = _FakeMixer()
    volume._MIXERS[("output", "PCM")] = fake
    try:
        await volume.set_raw("PCM", -2000, scale=jack)
        await volume.set_raw("PCM", -20000, scale=jack)
    finally:
        volume._MIXERS.pop(("output", "PCM"), None)
    assert fake.values == [-2000, -10239]
