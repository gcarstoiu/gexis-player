"""ADR-0162 D3 as amended (George, 2026-10-26): the equaliser's lowering given
back at the volume control - the level unchanged everywhere above it, the
control `steps` higher, and over the top half as far.

A fake card holds each control's value: `_Mixer.set` writes it and `amixer
sget` reads it, so what is asserted is the value the control would hold."""
from __future__ import annotations

import asyncio

import pytest

from gexis_core import mixer_scale, outputs
from gexis_core import volume as vol
from gexis_core.volume import (
    GiveBack,
    VolumeBridge,
    from_control,
    get_raw,
    give_back,
    given_back_up_to,
    hardware_raw_to_renderer_value,
    renderer_value_to_hardware_raw,
    set_give_back,
    set_raw,
    slider_percent_to_raw,
    to_control,
)

DAC = mixer_scale.DAC2_HD
ROCK = GiveBack("DAC", 5.0, DAC)          # ten steps of the DAC2 HD's 0.5 dB


class Card:
    def __init__(self):
        self.values: dict[str, int] = {}
        self.writes: list[tuple[str, int]] = []


class FakeProcess:
    def __init__(self, out: bytes):
        self._out = out

    async def communicate(self):
        return self._out, b""


class FakeSpotify:
    renderer_id = "spotify"

    def __init__(self):
        self.told = []

    def on_volume_change(self, callback):
        pass

    async def get_volume_steps(self):
        return 100

    async def set_volume(self, value):
        self.told.append(value)


@pytest.fixture(autouse=True)
def card(monkeypatch):
    card = Card()

    def write(mixer, value):
        card.writes.append((mixer._control, value))
        card.values[mixer._control] = value
        return True

    async def exec_(*args, **kwargs):
        assert args[:2] == ("amixer", "-D") and args[3] == "sget"
        value = card.values.get(args[4])
        return FakeProcess(b"" if value is None else f"  Front Left: Playback {value} [50%]\n".encode())

    monkeypatch.setattr(vol._Mixer, "set", write)
    monkeypatch.setattr(vol.asyncio, "create_subprocess_exec", exec_)
    monkeypatch.setattr(vol, "GIVE_BACK_PAUSE_S", 0)
    monkeypatch.setattr(vol, "_MIXERS", {})
    monkeypatch.setattr(vol, "_written_as", {})
    monkeypatch.setattr(vol, "_ceiling_reader", lambda: None)
    monkeypatch.setattr(vol, "_fixed_output_reader", lambda: False, raising=False)
    vol.use_scale(DAC)
    set_give_back(None)
    yield card
    set_give_back(None)


def test_below_the_top_the_control_is_higher_by_the_lowering_and_plays_the_level():
    level = slider_percent_to_raw(60)
    control = to_control(level, ROCK)
    assert control == level + 10
    assert DAC.db(control) - ROCK.db == DAC.db(level), "lowered 5 dB, given 5 dB back: Flat's level"


def test_over_the_top_the_control_travels_half_as_far_and_never_stops():
    """Within twice the lowering of 0 dB: twenty level steps on ten of the
    control's - the slider still does something all the way up."""
    values = [to_control(r, ROCK) for r in range(DAC.top - 20, DAC.top + 1)]
    assert values[0] == DAC.top - 10 and values[-1] == DAC.top
    assert all(b >= a for a, b in zip(values, values[1:]))
    assert len(set(values)) == 11
    heard = [DAC.db(to_control(slider_percent_to_raw(p), ROCK)) - ROCK.db for p in (70, 80, 90, 100)]
    assert heard == sorted(heard) and len(set(heard)) == 4
    assert heard[-1] == -ROCK.db, "the top plays the lowering quieter than Flat"


def test_silence_and_the_top_are_themselves_and_an_audible_control_is_never_silence():
    assert to_control(DAC.raw_min, ROCK) == DAC.raw_min == from_control(DAC.raw_min, ROCK)
    assert to_control(DAC.top, ROCK) == DAC.top == from_control(DAC.top, ROCK)
    assert from_control(DAC.raw_min + 3, ROCK) == DAC.raw_min + 1


def test_the_inverse_is_exact_below_the_top_and_within_a_step_over_it():
    for level in range(DAC.raw_min + 1, DAC.top + 1):
        back = from_control(to_control(level, ROCK), ROCK)
        if level <= DAC.top - 20:
            assert back == level
        else:
            assert abs(back - level) <= 1


def test_less_than_a_step_is_nothing():
    set_give_back(GiveBack("DAC", 0.2, DAC))
    assert give_back() is None


def test_up_to_where_it_is_all_given_back(monkeypatch):
    assert given_back_up_to(None) is None
    assert 64 <= given_back_up_to(ROCK) <= 65, "twice Rock's 5 dB below the top: about 65 %"
    monkeypatch.setattr(vol, "_ceiling_reader", lambda: 60)
    assert given_back_up_to(ROCK) == 100, "a ceiling below the top's halved travel never reaches it"


async def test_the_level_control_is_written_given_back_and_read_back_as_the_level(card):
    set_give_back(ROCK)
    await set_raw("DAC", 200)
    assert card.values["DAC"] == 210
    assert await get_raw("DAC") == 200
    await set_raw("Other", 200)
    assert card.values["Other"] == 200, "only the level control"
    card.values["Master"] = 150
    assert await get_raw("Master", device="hw:gexislmsvol") == 150


async def test_our_own_write_over_the_top_reads_back_as_the_level_written(card):
    """231 and 232 share the control's 236: the inverse alone would hand one
    of them back a step away, and the bridge would take it for a turn."""
    set_give_back(ROCK)
    await set_raw("DAC", 231)
    assert card.values["DAC"] == 236 and await get_raw("DAC") == 231
    await set_raw("DAC", 232)
    assert card.values["DAC"] == 236 and await get_raw("DAC") == 232


async def test_given_back_the_control_glides_up_and_the_level_stays(card):
    bridge = VolumeBridge("DAC", FakeSpotify(), get_active_renderer=lambda: "spotify")
    await bridge.write_hardware(200)
    card.writes.clear()
    await bridge.give_back(ROCK)
    assert [v for _, v in card.writes] == list(range(201, 211)), "half a decibel a step"
    assert give_back() == ROCK and bridge._last_written == 200
    assert [vol._as_level("DAC", "output", v) for v in range(201, 211)] == [200] * 10, \
        "every step's echo is the level, so the monitor tells nobody"
    card.writes.clear()
    await bridge.give_back(None)
    assert [v for _, v in card.writes] == list(range(209, 199, -1))
    assert give_back() is None and card.values["DAC"] == 200


async def test_what_a_renderer_is_told_does_not_move(card):
    """Lyrion at 60 stays at 60: the level read back is the one written,
    whatever the equaliser gives back."""
    await set_raw("DAC", renderer_value_to_hardware_raw(60, 100))
    bridge = VolumeBridge("DAC", FakeSpotify(), get_active_renderer=lambda: "lms")
    for target in (ROCK, GiveBack("DAC", 6.0, DAC), None):
        await bridge.give_back(target)
        assert hardware_raw_to_renderer_value(await get_raw("DAC"), 100) == 60


async def test_a_change_of_control_carries_the_level_it_holds(card):
    """Hardware to Software: the software stage was written the level before
    the give-back moved to it, so it is read as written, then given back."""
    soft = GiveBack(outputs.SOFTVOL_CONTROL, 5.0, outputs.SOFTVOL_SCALE)
    vol.use_scale(outputs.SOFTVOL_SCALE)
    set_give_back(ROCK)
    card.values[outputs.SOFTVOL_CONTROL] = 280
    bridge = VolumeBridge(outputs.SOFTVOL_CONTROL, FakeSpotify(), get_active_renderer=lambda: None)
    await bridge.give_back(soft)
    assert card.values[outputs.SOFTVOL_CONTROL] == 280 + soft.steps
    assert give_back() == soft


async def test_under_fixed_nothing_is_written(card, monkeypatch):
    monkeypatch.setattr(vol, "fixed_output", lambda: True)
    card.values["DAC"] = DAC.top
    bridge = VolumeBridge("DAC", FakeSpotify(), get_active_renderer=lambda: None)
    await bridge.give_back(ROCK)
    assert card.writes == [] and give_back() == ROCK
    assert await get_raw("DAC") == DAC.top, "full scale is full scale under any give-back"


async def test_one_give_back_at_a_time(card):
    bridge = VolumeBridge("DAC", FakeSpotify(), get_active_renderer=lambda: None)
    await set_raw("DAC", 100)
    await asyncio.gather(bridge.give_back(ROCK), bridge.give_back(GiveBack("DAC", 2.0, DAC)))
    assert give_back() == GiveBack("DAC", 2.0, DAC) and card.values["DAC"] == 104
    assert await get_raw("DAC") == 100
