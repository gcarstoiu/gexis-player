"""ADR-0053 — the panel's volume control is the active renderer's.

The defect these are about, measured on the device (Finding 046 §1): LMS at
25 put the DAC at -30 dB, which the panel published as **33**. George: *"If
LMS is at 25 I expect the volume on the panel to also 25."*
"""
from __future__ import annotations

import pytest

from gexis_core.remote_volume import RemoteVolume


class Recorder:
    """A renderer's channel out, and a count of how often it was used - the
    invariant below is about that count being zero."""

    def __init__(self):
        self.sent: list[int] = []

    async def send(self, value: int) -> None:
        self.sent.append(value)


@pytest.fixture
def world():
    state = {"active": None, "published": 0}
    remote = RemoteVolume(
        get_active_renderer=lambda: state["active"],
        on_change=lambda: state.__setitem__("published", state["published"] + 1),
    )
    return remote, state


class TestTheNumberIsTheRenderersOwn:
    @pytest.mark.asyncio
    async def test_what_the_panel_sends_is_what_the_panel_shows(self, world):
        """LMS's scale is the panel's, so 25 travels unchanged - and the
        number moves with the finger rather than waiting for LMS, whose own
        confirmation is measured at ~525 ms (Finding 046 §8)."""
        remote, state = world
        lms = Recorder()
        remote.register("lms", steps=100, send=lms.send)
        state["active"] = "lms"

        assert await remote.send(25) is True

        assert lms.sent == [25]
        assert remote.percent() == 25

    @pytest.mark.asyncio
    async def test_a_change_made_elsewhere_moves_the_panels_number(self, world):
        remote, state = world
        remote.register("lms", steps=100, send=Recorder().send)
        state["active"] = "lms"

        remote.report("lms", 62)

        assert remote.percent() == 62

    def test_an_inactive_renderers_report_does_not_move_the_number(self, world):
        remote, state = world
        remote.register("lms", steps=100)
        remote.register("spotify", steps=100)
        state["active"] = "spotify"
        remote.report("spotify", 40)
        published = state["published"]

        remote.report("lms", 90)

        assert remote.percent() == 40
        assert state["published"] == published

    def test_a_takeover_switches_whose_number_is_shown(self, world):
        remote, state = world
        remote.register("lms", steps=100)
        remote.register("bluetooth", steps=127)
        remote.report("lms", 30)
        remote.report("bluetooth", 127)

        state["active"] = "lms"
        assert remote.percent() == 30
        state["active"] = "bluetooth"
        assert remote.percent() == 100

    def test_nothing_playing_has_no_number_of_its_own(self, world):
        """None means "not a remote for anything", and the caller falls back
        to the hardware's own percentage - which is what the panel showed
        before this record."""
        remote, state = world
        remote.register("lms", steps=100)
        remote.report("lms", 30)

        assert remote.percent() is None

    def test_a_renderer_that_has_not_said_where_it_is_has_no_number(self, world):
        remote, state = world
        remote.register("lms", steps=100)
        state["active"] = "lms"

        assert remote.percent() is None

    def test_a_scale_that_arrives_late_reinterprets_the_value(self, world):
        """go-librespot's `volume_steps` is read from `/status`, so the
        wiring is in place before the answer is."""
        remote, state = world
        remote.register("spotify", steps=100)
        state["active"] = "spotify"
        remote.report("spotify", 50)
        assert remote.percent() == 50

        remote.set_steps("spotify", 200)

        assert remote.percent() == 25


class TestTheInvariant:
    """**A renderer's own value is never sent back to it.**

    Not layering fussiness: 101 panel positions cannot name AVRCP's 128
    values, so a Bluetooth level shown as a percentage and pushed back out
    lands somewhere else for 27 of them (test_volume.py pins the 27). Every
    turn of that loop is another AVRCP write, which is Finding 045 §12's
    ratchet - the one that ended with bluealsa dying of it.
    """

    def test_a_report_never_sends(self, world):
        remote, state = world
        phone = Recorder()
        remote.register("bluetooth", steps=127, send=phone.send)
        state["active"] = "bluetooth"

        for value in range(128):
            remote.report("bluetooth", value)

        assert phone.sent == []
        assert remote.percent() == 100

    @pytest.mark.asyncio
    async def test_the_phones_own_echo_of_our_write_does_not_move_anything(self, world):
        """80% sends 102. The phone echoes 102 back, and the number stays
        80 - no second write, nothing to ratchet against."""
        remote, state = world
        phone = Recorder()
        remote.register("bluetooth", steps=127, send=phone.send)
        state["active"] = "bluetooth"

        await remote.send(80)
        assert phone.sent == [102]
        assert remote.percent() == 80

        remote.report("bluetooth", 102)

        assert phone.sent == [102]
        assert remote.percent() == 80

    @pytest.mark.asyncio
    async def test_a_phone_that_quantises_our_value_wins_and_is_not_argued_with(
        self, world
    ):
        """If the phone answers 100 where we asked for 102, 100 is the
        truth and the panel shows 79. **Nothing corrects it back**, which is
        exactly what a ratchet would be."""
        remote, state = world
        phone = Recorder()
        remote.register("bluetooth", steps=127, send=phone.send)
        state["active"] = "bluetooth"
        await remote.send(80)

        remote.report("bluetooth", 100)

        assert remote.percent() == 79
        assert phone.sent == [102]


class TestWhenThePanelKeepsItsOwnSlider:
    @pytest.mark.asyncio
    async def test_nothing_active_falls_back_to_the_hardware(self, world):
        remote, state = world
        assert await remote.send(40) is False

    @pytest.mark.asyncio
    async def test_a_readable_renderer_with_no_way_in_falls_back_too(self, world):
        """Its number is still shown - that half works - but the panel's
        slider stays the panel's."""
        remote, state = world
        remote.register("bluetooth", steps=127)
        state["active"] = "bluetooth"
        remote.report("bluetooth", 64)

        assert await remote.send(40) is False
        assert remote.percent() == 50

    @pytest.mark.asyncio
    async def test_a_renderer_that_refuses_does_not_take_the_daemon_with_it(
        self, world
    ):
        """LMS is on the house network and go-librespot is a process that
        can die. A volume command is not worth an unhandled exception in the
        HTTP handler."""
        remote, state = world

        async def refuse(value):
            raise ConnectionError("LMS is not there")

        remote.register("lms", steps=100, send=refuse)
        state["active"] = "lms"

        assert await remote.send(30) is True
        assert remote.percent() == 30
