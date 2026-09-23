"""ADR-0054 §1 — Bluetooth's level comes from bluealsa, not from a mixer.

The mixer round trip it replaces was measured wrong one time in three - 59
of 179 in George's own session, five of them jumping straight to 127 -
because bluealsa's AVRCP curve is ~10 dB per doubling and the control was
linear in dB (Finding 047 §2).

**The value path cannot be tested without a phone.** What is tested here is
the encoding, which is the part that can be got wrong silently, and the
behaviour with nothing connected, which is most of the time.
"""
from __future__ import annotations

import pytest

from gexis_core.bluealsa_volume import STEPS, BluealsaVolume, decode, encode


class TestTheVolumeProperty:
    """`org.bluealsa.PCM1(7)`, read off the device: *"channel 1 (left) is
    stored in the upper byte, channel 2 is stored in the lower byte. The
    highest bit of both bytes determines whether channel is muted. A2DP:
    0-127."*"""

    def test_the_scale_is_avrcps_own(self):
        assert STEPS == 127

    def test_both_channels_carry_the_level(self):
        assert encode(100) == (100 << 8) | 100
        assert decode(encode(100)) == 100

    def test_every_level_survives_the_encoding(self):
        assert all(decode(encode(value)) == value for value in range(STEPS + 1))

    def test_a_level_out_of_range_is_clamped_rather_than_wrapped(self):
        """**The wrap is the whole reason this module exists**: the phone
        asked for 0 and got 127 back, five times in six minutes. Nothing
        here may ever produce that shape."""
        assert decode(encode(-5)) == 0
        assert decode(encode(999)) == STEPS
        assert encode(999) <= 0x7F7F

    def test_mute_is_read_through_rather_than_carried(self):
        """Mute shares the byte with the level. This device has its own
        mute (ADR-0034) which is not the phone's, and conflating them would
        let a phone's mute strand the panel showing a level nobody can
        hear."""
        assert decode(0xC0C0) == 64  # both channels muted at 64
        assert decode(0x4040) == 64  # neither muted, same level

    def test_the_louder_channel_wins_an_unbalanced_pair(self):
        assert decode((100 << 8) | 20) == 100
        assert decode((20 << 8) | 100) == 100


class TestWithNothingConnected:
    """Which is most of the time, and is also what a crashed bluealsa looks
    like - it has crashed before (Finding 045 §10) and may not take the
    daemon with it."""

    @pytest.mark.asyncio
    async def test_setting_a_level_with_no_phone_is_quiet_not_fatal(self):
        reported = []
        volume = BluealsaVolume(on_value=lambda v, s: reported.append((v, s)))

        await volume.set(80)

        assert reported == []
        assert volume.level is None

    def test_a_repeated_value_is_not_republished(self):
        reported = []
        volume = BluealsaVolume(on_value=lambda v, s: reported.append((v, s)))

        volume._report(encode(64))
        volume._report(encode(64))
        volume._report(encode(65))

        assert reported == [(64, STEPS), (65, STEPS)]

    def test_a_disconnect_forgets_the_level(self):
        """A stale level is what made a phone connect quiet while showing
        maximum - the old path pushed the last mixer value at it."""
        volume = BluealsaVolume(on_value=lambda v, s: None)
        volume._report(encode(64))
        assert volume.level == 64

        volume._forget()

        assert volume.level is None
