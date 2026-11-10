"""Room correction as the player keeps it and shows it (ADR-0175, ADR-0177):
the switches, how far it reaches, the calibration given from the phone, and a
run held against the rest of the player."""
import asyncio
from types import SimpleNamespace

import pytest

np = pytest.importorskip("numpy")

from gexis_core import room_correction as rc  # noqa: E402
from gexis_core.room_control import RoomControl, day  # noqa: E402
from gexis_core.room_correction import RoomError  # noqa: E402
from gexis_core.room_mic import Microphone  # noqa: E402

from room_sim import Audio  # noqa: E402

DAC = SimpleNamespace(card="sndrpihifiberry", label="HiFiBerry DAC2 HD")

CAL = """"Sens Factor =-0.667dB, AGain =18dB, SERNO: 7071234"
"Auto-generated 90-degree calibration file"
""" + "\n".join(f"{10 * 1.02 ** k:.3f}\t0.0" for k in range(400)) + "\n"


class Store:
    def __init__(self):
        self.rows = {}

    def get(self, key):
        return self.rows.get(key)

    def set(self, key, value):
        self.rows[key] = value


class Rig:
    def __init__(self, mic="found"):
        self.store = Store()
        self.calls = []
        self.eq = False
        self.grouped = False
        self.mic = mic
        self.audio = Audio()
        self.summaries = []

        def hook(name):
            async def call(*args):
                self.calls.append((name, *args))
                if name in ("sync", "reopen"):
                    # The made-up room hears what the stage plays now.
                    self.audio.stage = self.control.stage(DAC.card)
            return call

        async def fast(_s):
            await asyncio.sleep(0)

        def find():
            if self.mic == "found":
                return "found", Microphone("U18dB", 18.0)
            return self.mic, None

        self.control = RoomControl(
            self.store, output=lambda: DAC, kind=lambda o: "DAC", reopen=hook("reopen"), sync=hook("sync"),
            take=hook("take"), release=hook("release"), loud=hook("loud"), quiet=hook("quiet"),
            eq_on=lambda card: self.eq, grouped=lambda: self.grouped, find_mic=find,
            audio=lambda mic, cal: self.audio, publish=self.summaries.append, today=lambda: "2026-11-05",
            run_options={"sleep": fast, "sweep_s": 1.0})

    def names(self):
        return [c[0] for c in self.calls]

    async def run_to(self, step, position=None, checking=None):
        run = self.control.run
        for _ in range(6000):
            s = run.state
            if s.step == step and (position is None or s.position == position) and \
                    (checking is None or s.checking == checking) and run.waiting:
                return s
            if not run.running:
                raise AssertionError(f"ended: {run.ended}")
            await asyncio.sleep(0.01)
        raise AssertionError(f"never reached {step}")

    async def measure(self, keep=True, skip=False):
        await self.control.calibration(CAL, "7071234_90deg.txt")
        await self.control.start()
        await self.run_to("place")
        await self.control.tap("start")
        for n in range(2, rc.POSITIONS + 1):
            await self.run_to("move", n)
            self.audio.position = n
            await self.control.tap("next")
        await self.run_to("correction")
        if skip:
            await self.control.tap("check")
            await self.run_to("move", 1, checking=True)
            await self.control.tap("skip")
        else:
            await self.control.tap("check")
            for n in range(1, rc.POSITIONS + 1):
                await self.run_to("move", n, checking=True)
                self.audio.position = n
                await self.control.tap("next")
        await self.run_to("result")
        await self.control.tap("keep" if keep else "discard")
        await asyncio.wait_for(self.control.run.wait(), 10)


def test_the_day_as_the_screens_say_it():
    assert day("2026-11-03") == "3 November"
    assert day("2026-11-03", year=True) == "3 November 2026"


async def test_never_measured():
    rig = Rig()
    s = rig.control.snapshot()
    assert s["row"] == "Not measured yet" and s["on"] is False and s["chart"] is None
    assert s["microphone"]["state"] == "found" and s["microphone"]["calibration"] is None
    assert (s["can_measure"], s["why_not"]) == (False, "calibration")
    with pytest.raises(RoomError, match="Measure first"):
        await rig.control.update({"on": True})


async def test_the_calibration_file_from_the_phone():
    rig = Rig()
    s = await rig.control.calibration(CAL, "7071234_90deg.txt")
    assert s["microphone"]["calibration"] == {"serial": "707-1234", "angle": 90, "date": "2026-11-05",
                                              "again": False}
    assert s["can_measure"] is True
    with pytest.raises(RoomError, match="0° file"):
        await rig.control.calibration(CAL.replace('"Auto-generated 90-degree calibration file"\n', ""),
                                      "7071234.txt")


async def test_a_calibration_kept_by_phase_29_is_asked_for_again():
    """Kept to 2 kHz only, it is given again before the full range is
    measured (George, 2026-11-08: *Choose its file again*)."""
    rig = Rig()
    await rig.control.calibration(CAL, "7071234_90deg.txt")
    stored = rig.store.rows[rc.KEY]
    stored["microphones"]["7071234"]["points"] = [p for p in stored["microphones"]["7071234"]["points"]
                                                  if p[0] <= 2000]
    s = rig.control.snapshot()
    assert s["microphone"]["calibration"]["again"] is True and s["microphone"]["calibration"]["serial"] == "707-1234"
    assert (s["can_measure"], s["why_not"]) == (False, "calibration")
    with pytest.raises(RoomError, match="again"):
        await rig.control.start()
    s = await rig.control.calibration(CAL, "7071234_90deg.txt")
    assert s["microphone"]["calibration"]["again"] is False and s["can_measure"] is True


@pytest.mark.parametrize("mic, why", [("absent", "microphone"), ("other", "microphone")])
async def test_no_measuring_without_the_umik(mic, why):
    rig = Rig(mic=mic)
    await rig.control.calibration(CAL, "x_90deg.txt")
    s = rig.control.snapshot()
    assert s["microphone"]["state"] == mic and (s["can_measure"], s["why_not"]) == (False, why)
    with pytest.raises(RoomError, match="Plug in the UMIK-1"):
        await rig.control.start()


async def test_no_measuring_in_a_group():
    rig = Rig()
    await rig.control.calibration(CAL, "x_90deg.txt")
    rig.grouped = True
    with pytest.raises(RoomError, match="Leave the group"):
        await rig.control.start()


async def test_a_run_kept_switches_it_on():
    rig = Rig()
    await rig.measure()
    names = rig.names()
    assert names[:3] == ["take", "reopen", "loud"], "the stage brought into the path for the run"
    assert ("reopen", "room correction measures") in rig.calls
    assert names[-3:] == ["quiet", "sync", "release"], "kept: the stage stays, with the cuts"
    s = rig.control.snapshot()
    assert s["on"] and not s["without"] and s["measured"]["checked"]
    assert s["row"] == "Full range · measured 5 November"
    assert s["chart"]["after_kind"] == "measured"
    assert s["reach"] == rc.FULL and s["measured"]["range"] == rc.FULL, "a new measurement starts at the full range"
    assert s["above"]["L"] and s["measured"]["within"] < s["measured"]["room_within"]
    play = rig.control.stage("sndrpihifiberry")
    assert play.cuts[0] and play.above[0] and play.lift, "the corrections on the stage, with their headroom"
    assert rig.control.frozen() is None and not rig.control.in_path("vc4hdmi0")


async def test_while_it_runs_the_player_is_held_and_the_equaliser_flat():
    rig = Rig()
    await rig.control.calibration(CAL, "x_90deg.txt")
    await rig.control.start()
    await rig.run_to("place")
    assert rig.control.frozen() == "the room is being measured"
    assert rig.control.in_path("sndrpihifiberry") and rig.control.eq_bypassed("sndrpihifiberry")
    assert rig.control.stage("sndrpihifiberry") is None, "the room as it is"
    assert rig.control.summary()["run"]["step"] == "place"
    with pytest.raises(RoomError, match="Not while"):
        await rig.control.update({"on": False})
    await rig.control.tap("cancel")
    assert rig.control.summary()["ended"] == {"how": "cancelled", "why": "cancel"}, "shown at once"
    assert rig.control.summary()["run"] is None
    await rig.control.run.wait()
    assert rig.control.frozen() is None and not rig.control.in_path("sndrpihifiberry")
    assert ("reopen", "room correction measured") in rig.calls, "the stage taken out again"
    assert rig.names()[-1] == "release"
    assert rig.control.summary()["ended"] == {"how": "cancelled", "why": "cancel"}
    await rig.control.tap("done")
    assert rig.control.summary()["ended"] is None


async def test_with_the_equaliser_on_the_path_never_changes():
    rig = Rig()
    rig.eq = True
    await rig.measure()
    assert "reopen" not in rig.names()


async def test_skipped_it_is_kept_not_checked():
    rig = Rig()
    await rig.measure(skip=True)
    s = rig.control.snapshot()
    assert s["measured"]["checked"] is False and s["chart"]["after_kind"] == "expected"


async def test_discarded_nothing_changes():
    rig = Rig()
    await rig.measure(keep=False)
    s = rig.control.snapshot()
    assert s["measured"] is None and not s["on"]
    assert rig.control.summary()["ended"]["how"] == "discarded"


async def test_off_and_on_and_without():
    rig = Rig()
    await rig.measure()
    rig.calls.clear()
    s = await rig.control.update({"without": True})
    assert s["without"] and s["row"] == "Without · comparing, no correction"
    assert rig.names() == ["sync"], "compared at once, no reopening"
    assert rig.control.stage("sndrpihifiberry").cuts[0][0][1] == 0.0
    s = await rig.control.update({"on": False})
    assert not s["on"] and not s["without"] and s["row"] == "Off"
    assert rig.names()[-1] == "reopen", "the equaliser off: the stage leaves the path"
    with pytest.raises(RoomError, match="Only while"):
        await rig.control.update({"without": True})
    await rig.control.update({"on": True})
    assert rig.control.snapshot()["row"] == "Full range · measured 5 November"


async def test_the_reach_is_heard_at_once_and_kept_while_off():
    """ADR-0177: Bass or Full range, a tap heard at once - only the gains,
    never the path; saved, and kept through off and on."""
    rig = Rig()
    await rig.measure()
    rig.calls.clear()
    s = await rig.control.update({"reach": rc.BASS})
    assert s["reach"] == rc.BASS and rig.names() == ["sync"] and s["row"] == "Bass · measured 5 November"
    play = rig.control.stage("sndrpihifiberry")
    assert all(g == 0.0 for _, g, _ in play.above[0]) and any(g for _, g, _ in play.cuts[0])
    assert rig.summaries[-1]["reach"] == rc.BASS, "on /state"
    await rig.control.update({"on": False})
    with pytest.raises(RoomError, match="Only while"):
        await rig.control.update({"reach": rc.FULL})
    s = await rig.control.update({"on": True})
    assert s["reach"] == rc.BASS, "kept through off and on"
    with pytest.raises(RoomError, match="bass or full"):
        await rig.control.update({"reach": "all"})


async def test_a_measurement_from_before_is_held_at_the_bass():
    rig = Rig()
    await rig.measure()
    stored = rig.store.rows[rc.KEY]
    m = stored["outputs"]["sndrpihifiberry"]["measured"]
    del m["range"]
    for sp in m["speakers"].values():
        sp.pop("above", None)
    s = rig.control.snapshot()
    assert s["reach"] == rc.BASS and s["measured"]["range"] == rc.BASS and s["above"] == {"L": [], "R": []}
    assert s["row"] == "Bass · measured for the bass only"
    assert s["chart"]["range"] == rc.BASS
    with pytest.raises(RoomError, match="covers the bass only"):
        await rig.control.update({"reach": rc.FULL})


async def test_the_pending_measurement_is_shown_before_it_is_kept():
    rig = Rig()
    await rig.control.calibration(CAL, "x_90deg.txt")
    await rig.control.start()
    await rig.run_to("place")
    await rig.control.tap("start")
    for n in range(2, rc.POSITIONS + 1):
        await rig.run_to("move", n)
        rig.audio.position = n
        await rig.control.tap("next")
    await rig.run_to("correction")
    s = rig.control.snapshot()
    assert s["pending"]["chart"]["after_kind"] == "expected" and s["pending"]["cuts"]["L"]
    assert s["pending"]["above"]["L"] and s["pending"]["range"] == rc.FULL
    assert s["pending"]["within"] is not None and s["pending"]["nothing_to_correct"] is False
    assert s["measured"] is None, "nothing stored before Keep it"
    await rig.control.tap("cancel")
