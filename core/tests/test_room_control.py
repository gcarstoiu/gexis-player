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
    def __init__(self, mic="found", store=None, history=None):
        self.store = store or Store()
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
            run_options={"sleep": fast, "sweep_s": 1.0}, history=history)

    def names(self):
        return [c[0] for c in self.calls]

    async def run_to(self, step, position=None, checking=None, setup=None):
        run = self.control.run
        for _ in range(6000):
            s = run.state
            if s.step == step and (position is None or s.position == position) and \
                    (checking is None or s.checking == checking) and (setup is None or s.setup == setup) \
                    and run.waiting:
                return s
            if not run.running:
                raise AssertionError(f"ended: {run.ended}")
            await asyncio.sleep(0.01)
        raise AssertionError(f"never reached {step}: {run.state}")

    async def past_check(self):
        """ADR-0187: the speaker check - left and right at position 2, the
        list - then each position from the head."""
        await self.run_to("move", 2, setup=True)
        self.audio.position = 2
        await self.control.tap("next")
        await self.run_to("ready")
        await self.control.tap("next")
        for n in range(1, rc.POSITIONS + 1):
            await self.run_to("move", n, setup=False)
            self.audio.position = n
            await self.control.tap("next")

    async def measure(self, keep=True, skip=False):
        await self.control.calibration(CAL, "7071234_90deg.txt")
        await self.control.start()
        await self.run_to("place")
        await self.control.tap("start")
        await self.past_check()
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


async def check_alone(rig, tap="keep", louder=1.0):
    """ADR-0188: the speaker check on its own, to its list, then `tap`."""
    await rig.control.calibration(CAL, "7071234_90deg.txt")
    rig.audio.position = 1
    rig.audio.loudness = (louder, 1.0)
    await rig.control.start("speakers")
    await rig.run_to("place")
    await rig.control.tap("start")
    await rig.run_to("move", 2, setup=True)
    rig.audio.position = 2
    await rig.control.tap("next")
    state = await rig.run_to("ready")
    if tap:
        await rig.control.tap(tap)
    return state


async def test_the_speakers_checked_on_their_own():
    """ADR-0188 D1, C3: the check alone - three steps, its list, *Keep* -
    stores the alignment, switched on, and heard after the run with room
    correction never measured."""
    rig = Rig()
    rig.audio.delays = {n: (0.0080, 0.0086) for n in range(1, 6)}
    rig.audio.delays[2] = (0.0074, 0.0092)
    state = await check_alone(rig, louder=10 ** (1.5 / 20))
    assert state.mode == "speakers" and state.setup and not state.stale
    assert rig.summaries and any(x["run"] and x["run"]["mode"] == "speakers" for x in rig.summaries if x)
    await asyncio.wait_for(rig.control.run.wait(), 10)
    assert rig.control.run.ended["how"] == "kept"
    s = rig.control.snapshot()
    a = s["speakers"]
    assert a["on"] and a["sides"] == "right" and a["date"] == "2026-11-05" and a["right_db"] < -1.0
    assert a["delay_ms"][0] == pytest.approx(0.6, abs=0.03) and a["delay_ms"][1] == 0.0
    assert a["level_db"][0] < -1.0 and a["level_db"][1] == 0.0, "the louder left turned down"
    assert s["measured"] is None and s["row"] == "Speakers aligned" and not s["stale"]
    play = rig.control.stage(DAC.card)
    assert play.delay[0] == pytest.approx(0.6, abs=0.03) and play.cuts == ((), ())
    assert rig.control.in_path(DAC.card)


async def test_discard_and_nothing_read():
    """ADR-0188 C3: *Discard* keeps nothing; nothing read, no *Keep*."""
    rig = Rig()
    await check_alone(rig, tap="discard")
    await asyncio.wait_for(rig.control.run.wait(), 10)
    assert rig.control.run.ended["how"] == "discarded" and rig.control.snapshot()["speakers"] is None


async def test_a_check_that_leaves_the_correction_behind_and_keep_and_measure():
    """ADR-0188 D2, C3-C4: a speaker moved since the room was measured -
    *Keep*, *Keep and measure* or *Discard*; *Keep and measure* stores the
    alignment and goes on into the measurement, not checking again."""
    rig = Rig()
    await rig.measure()
    kept = rig.control.state().output(DAC.card).measured
    rig.audio.delays = {n: (0.0080, 0.0088) for n in range(1, 6)}
    rig.audio.delays[2] = (0.0074, 0.0094)
    state = await check_alone(rig, tap=None)
    assert state.stale and state.mode == "speakers"
    await rig.control.tap("again")
    await asyncio.sleep(0.05)
    assert rig.control.run.state.step == "ready", "no Check again here: the screen's three buttons"
    await rig.control.tap("keep_and_measure")
    await rig.run_to("move", 1, setup=False)
    assert rig.control.run.state.mode == "measure"
    here = rig.control.state().output(DAC.card)
    assert here.speakers.delay[0] == pytest.approx(0.8, abs=0.05) and here.stale
    assert here.measured == kept, "room correction as it was until measured again"
    for n in range(1, rc.POSITIONS + 1):
        await rig.run_to("move", n, setup=False)
        rig.audio.position = n
        await rig.control.tap("next")
    await rig.run_to("correction")
    await rig.control.tap("check")
    await rig.run_to("move", 1, checking=True)
    await rig.control.tap("skip")
    await rig.run_to("result")
    await rig.control.tap("keep")
    await asyncio.wait_for(rig.control.run.wait(), 10)
    here = rig.control.state().output(DAC.card)
    assert not here.stale and here.measured.delay == here.speakers.delay


@pytest.mark.parametrize("skip", [False, True])
async def test_the_ringing_and_the_dips_come_with_the_measurement(skip):
    """ADR-0187 D7-D8: each speaker's ringing at the head, after measured -
    or expected when the check was skipped - and the dips with their
    causes, kept and charted."""
    rig = Rig()
    await rig.measure(skip=skip)
    s = rig.control.snapshot()
    rings = s["chart"]["speakers"]["L"]["ringing"]
    assert rings and all(r["after"] is not None for r in rings), "the made-up room's modes ring"
    assert {r["hz"] for r in rings} <= set(rc_dsp().RING_BANDS)
    assert s["chart"]["after_kind"] == ("expected" if skip else "measured")
    assert isinstance(s["measured"]["dips"], list) and s["chart"]["dips"] == s["measured"]["dips"]
    for d in s["measured"]["dips"]:
        assert d["depth"] >= 3 and d["cause"] in ("cancel", "local", "wall", None)


def rc_dsp():
    from gexis_core import room_dsp
    return room_dsp


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
    # ADR-0185: the speakers' timing, read in the made-up room - the same.
    assert s["measured"]["distance_cm"] == pytest.approx(0.0, abs=1.0)
    assert rig.control.summary()["measured"]["delay_ms"] == [pytest.approx(0.0, abs=0.05)] * 2
    # ADR-0187 D2: the made-up speakers read within a fraction of a dB: the
    # louder one turned down by it.
    level = rig.control.summary()["measured"]["level_db"]
    assert min(level) > -1.0 and max(level) == 0.0


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
    assert rig.control.summary()["ended"] == {"how": "cancelled", "why": "cancel", "mode": "measure"}, "shown at once"
    assert rig.control.summary()["run"] is None
    await rig.control.run.wait()
    assert rig.control.frozen() is None and not rig.control.in_path("sndrpihifiberry")
    assert ("reopen", "room correction measured") in rig.calls, "the stage taken out again"
    assert rig.names()[-1] == "release"
    assert rig.control.summary()["ended"] == {"how": "cancelled", "why": "cancel", "mode": "measure"}
    await rig.control.tap("done")
    assert rig.control.summary()["ended"] is None


async def test_the_end_shown_before_the_player_is_put_back_stays_shown():
    """*Done* (or Back) on *Measuring cancelled* at once: the run's last
    publish, as it lets the player go, does not bring the end back (the
    review of 1.16.1: the page went back to *Measuring cancelled*)."""
    rig = Rig()
    await rig.control.calibration(CAL, "x_90deg.txt")
    await rig.control.start()
    await rig.run_to("place")
    await rig.control.tap("cancel")
    await rig.control.tap("done")
    assert rig.control.frozen() is not None, "before the player is put back"
    await rig.control.run.wait()
    assert rig.control.frozen() is None and rig.control.summary()["ended"] is None


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


async def test_done_on_nothing_to_correct_ends_the_run():
    """*Done* is the only button on *Nothing to correct*; as the phone sends
    it, through the control, it ends the run (the review of 1.16.1: the
    player was held for the ten minutes' timeout)."""
    rig = Rig()
    rig.audio = Audio(modes=(), broad=())
    await rig.control.calibration(CAL, "x_90deg.txt")
    await rig.control.start()
    await rig.run_to("place")
    await rig.control.tap("start")
    await rig.past_check()
    await rig.run_to("nothing")
    await rig.control.tap("done")
    await asyncio.wait_for(rig.control.run.wait(), 5)
    assert rig.control.frozen() is None and rig.names()[-1] == "release"
    assert rig.control.summary()["ended"]["how"] == "done" and rig.control.snapshot()["measured"] is None
    await rig.control.tap("done")
    assert rig.control.summary()["ended"] is None, "the end shown"


async def test_off_and_on_and_without():
    rig = Rig()
    await rig.measure()
    rig.calls.clear()
    s = await rig.control.update({"without": True})
    assert s["without"] and s["row"] == "Without · comparing, no correction"
    assert rig.names() == ["sync"], "compared at once, no reopening"
    assert rig.control.stage("sndrpihifiberry").cuts[0][0][1] == 0.0
    s = await rig.control.update({"on": False})
    assert not s["on"] and s["without"], "the speakers' alignment still on (ADR-0188)"
    assert s["row"] == "Without · comparing, no correction"
    s = await rig.control.update({"speakers": False})
    assert not s["on"] and not s["without"] and s["row"] == "Off"
    assert rig.names()[-1] == "reopen", "the equaliser off: the stage leaves the path"
    with pytest.raises(RoomError, match="Only while"):
        await rig.control.update({"without": True})
    await rig.control.update({"on": True, "speakers": True})
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
    await rig.past_check()
    await rig.run_to("correction")
    s = rig.control.snapshot()
    assert s["pending"]["chart"]["after_kind"] == "expected" and s["pending"]["cuts"]["L"]
    assert s["pending"]["above"]["L"] and s["pending"]["range"] == rc.FULL
    assert s["pending"]["within"] is not None and s["pending"]["nothing_to_correct"] is False
    assert s["measured"] is None, "nothing stored before Keep it"
    await rig.control.tap("cancel")


class _Engine:
    """What `EqualiserControl.sync` drives: the card it runs CamillaDSP for."""

    def __init__(self):
        self.card = None

    async def configure(self, card, gains, restart=False, room=None):
        self.card = card

    def status(self):
        return {}


@pytest.mark.parametrize("before, after", [(True, False), (False, True), (True, True), (False, False)])
async def test_the_chain_after_a_run_is_the_one_wanted_whatever_the_equaliser_did_during_it(before, after):
    """**The review of 1.16.1.** The equaliser on, switched off from the
    phone while the room was measured (its controller only syncs while a run
    needs the stage), and the run cancelled: the run had not taken the path,
    so it only synced too - CamillaDSP stopped and `output.conf` still sent
    every source into the loopback. Silent until a restart."""
    from gexis_core import eq_control
    from gexis_core.equaliser import Equaliser

    store, engine, audio, chain, room = Store(), _Engine(), Audio(), {}, {}
    out = SimpleNamespace(card=DAC.card, label=DAC.label, control=None, usb_id=None, scale=None)

    def eq_on(card):
        return Equaliser.from_settings(store.get(eq_control.KEY)).output(card).on

    def written():
        # `_rewrite_output_conf`: the loopback while `outputs.eq_in_path`.
        chain["to"] = "loopback" if (eq_on(DAC.card) or room["control"].in_path(DAC.card)) else "card"

    async def reopen(reason):
        written()
        await equaliser.sync(restart=True)
        audio.stage = room["control"].stage(DAC.card)

    async def sync():
        await equaliser.sync()
        audio.stage = room["control"].stage(DAC.card)

    async def nothing():
        pass

    async def fast(_s):
        await asyncio.sleep(0)

    equaliser = eq_control.EqualiserControl(
        store, engine, output=lambda: out, fixed=lambda: False, reopen=reopen,
        room_in_path=lambda card: room["control"].in_path(card),
        room_stage=lambda card: room["control"].stage(card),
        bypassed=lambda card: room["control"].eq_bypassed(card))
    room["control"] = control = RoomControl(
        store, output=lambda: out, kind=lambda o: "DAC", reopen=reopen, sync=sync,
        take=nothing, release=nothing, loud=nothing, quiet=nothing, eq_on=eq_on,
        find_mic=lambda: ("found", Microphone("U18dB", 18.0)), audio=lambda mic, cal: audio,
        today=lambda: "2026-11-05", run_options={"sleep": fast, "sweep_s": 1.0})
    store.set(eq_control.KEY, Equaliser.from_settings(None).set_on(DAC.card, before).to_settings())
    written()
    await equaliser.sync()
    await control.calibration(CAL, "7071234_90deg.txt")
    await control.start()
    run = control.run
    for _ in range(6000):
        if run.state.step == "place" and run.waiting:
            break
        await asyncio.sleep(0.01)
    assert chain["to"] == "loopback" and engine.card == DAC.card, "measured through the stage"
    await equaliser.update({"on": after})
    await control.tap("cancel")
    await asyncio.wait_for(run.wait(), 10)
    assert chain["to"] == ("loopback" if after else "card")
    assert engine.card == (DAC.card if after else None)


async def _until(rig, done):
    for _ in range(5000):
        if done(rig.control.run.state, rig.control.run):
            return
        await asyncio.sleep(0.001)
    raise AssertionError(f"at {rig.control.run.state}")


@pytest.mark.parametrize("when", ["at_once", "countdown", "measure"])
async def test_a_second_measure_here_is_not_kept_for_the_next_position(when):
    """A tap is for the screen it was sent on: a second *Measure here* (a
    double tap, or a second phone) never answers the next position's (the
    review of 1.16.1: position 3 was swept where position 2 was)."""
    rig = Rig()
    await rig.control.calibration(CAL, "x_90deg.txt")
    await rig.control.start()
    await rig.run_to("place")
    await rig.control.tap("start")
    await rig.run_to("move", 2, setup=True)
    rig.audio.position = 2
    await rig.control.tap("next")
    await rig.run_to("ready")
    await rig.control.tap("next")
    await rig.run_to("move", 1, setup=False)
    await rig.control.tap("next")
    await rig.run_to("move", 2, setup=False)
    rig.audio.position = 2
    await rig.control.tap("next")
    if when != "at_once":
        await _until(rig, lambda s, _run: (s.step, s.position) == (when, 2))
    await rig.control.tap("next")
    await _until(rig, lambda s, run: s.position == 3 and (s.step != "move" or run.waiting))
    s = rig.control.run.state
    assert (s.step, s.position, rig.control.run.waiting) == ("move", 3, True), "waits for Measure here"
    await rig.control.tap("cancel")
    await rig.control.run.wait()


async def test_a_second_try_again_is_not_kept_for_the_next_too_quiet():
    rig = Rig()
    rig.audio = Audio(offset=45.0)
    await rig.control.calibration(CAL, "x_90deg.txt")
    await rig.control.start()
    await rig.run_to("place")
    await rig.control.tap("start")
    await _until(rig, lambda s, run: s.too_quiet and run.waiting)
    once = len(rig.audio.plays)
    await rig.control.tap("again")
    await rig.control.tap("again")
    await _until(rig, lambda s, run: s.too_quiet and run.waiting)
    await asyncio.sleep(0.05)
    assert rig.control.run.waiting and len(rig.audio.plays) == 2 * once, "one more try, not two"
    await rig.control.tap("cancel")
    await rig.control.run.wait()


# ---- kept from before ADR-0175's amendment (George, 2026-11-17) -----------------


def _as_before(m, both=True, phase29=False):
    """A stored measurement made to look kept from before the amendment:
    each speaker's own cuts, checked, a position found worse."""
    m.pop("bass_from", None)
    m["checked"], m["worse"] = True, [[3, 2.3]]
    m["speakers"]["L"]["cuts"] = [{"freq": 121.0, "gain": -11.1, "q": 2.1}]
    m["speakers"]["R"]["cuts"] = [{"freq": 63.0, "gain": -5.0, "q": 4.0}]
    for sp in m["speakers"].values():
        sp.pop("checks", None)      # kept from 2026-11-25 only
    if not both:
        del m["speakers"][rc.BOTH]
    if phase29:
        # Phase 29's: to 500 Hz, for the bass only.
        n = len(rc.grid(122))
        del m["range"]
        for sp in m["speakers"].values():
            sp.pop("above", None)
            sp.pop("after_bass", None)
            for k in ("before", "target", "after"):
                sp[k] = sp[k][:n]
            sp["positions"] = [p[:n] for p in sp["positions"]]
    return m


@pytest.mark.parametrize("phase29", [False, True])
async def test_a_measurement_kept_from_before_is_redesigned_from_both_when_the_player_starts(phase29):
    rig = Rig()
    await rig.measure()
    out = rig.store.rows[rc.KEY]["outputs"][DAC.card]
    _as_before(out["measured"], phase29=phase29)
    again = Rig(store=rig.store)
    m = again.control.state().output(DAC.card).measured
    assert m.bass_from == rc.BOTH and not m.checked and m.worse == ()
    assert m.cuts("L") == m.cuts("R") == m.speakers[rc.BOTH].cuts and m.cuts("L")
    assert all(len(m.speakers[k].after) == len(m.speakers[k].before) for k in rc.SWEPT)
    assert rig.store.rows[rc.KEY]["outputs"][DAC.card]["measured"]["bass_from"] == rc.BOTH, "stored"
    assert again.control.state().output(DAC.card).on, "still on"
    s = again.control.snapshot()
    assert s["chart"]["after_kind"] == "expected"
    if phase29:
        assert m.range == rc.BASS and m.above("L") == () and len(m.speakers["L"].before) == 122


async def test_one_without_both_sweeps_is_kept_as_it_is():
    rig = Rig()
    await rig.measure()
    out = rig.store.rows[rc.KEY]["outputs"][DAC.card]
    _as_before(out["measured"], both=False)
    kept = rc.Measurement.from_dict(out["measured"])
    again = Rig(store=rig.store)
    m = again.control.state().output(DAC.card).measured
    assert m == kept and m.bass_from == rc.EACH


async def test_a_redesign_that_fails_never_stops_the_start(monkeypatch):
    from gexis_core import room_run

    def broken(m, dsp=None):
        raise ValueError("made up")
    rig = Rig()
    await rig.measure()
    _as_before(rig.store.rows[rc.KEY]["outputs"][DAC.card]["measured"])
    monkeypatch.setattr(room_run, "redesign", broken)
    again = Rig(store=rig.store)
    assert again.control.state().output(DAC.card).measured.bass_from == rc.EACH


# ---- ADR-0189: the history ------------------------------------------------------------

def _clock():
    import datetime
    at = [datetime.datetime(2026, 11, 25, 11, 0)]

    def now():
        at[0] += datetime.timedelta(minutes=7)
        return at[0]
    return now


async def test_every_measurement_is_kept_and_one_can_be_gone_back_to(tmp_path):
    """ADR-0189 D2, C2-C3: each measurement kept is an entry, newest first,
    the one playing marked; going back plays the older one's correction,
    the switches as they were, and marks it."""
    from gexis_core.room_history import History
    rig = Rig(history=History(tmp_path, now=_clock()))
    await rig.measure()
    first = rig.control.state().output(DAC.card)
    await rig.measure()
    rows = rig.control.snapshot()["history"]
    assert [r["kind"] for r in rows] == ["room", "room"] and rows[0]["id"] > rows[1]["id"]
    assert [r["playing"] for r in rows] == [True, False]
    assert rows[1]["time"] and rows[1]["checked"] is True and rows[1]["differs"] is False
    opened = rig.control.history_entry(rows[1]["id"])
    assert opened["chart"] is not None and opened["checked"] is True
    await rig.control.restore(rows[1]["id"], "its")
    here = rig.control.state().output(DAC.card)
    assert here.entry == rows[1]["id"] and here.measured.as_dict() == first.measured.as_dict()
    assert here.on and here.aligning and not here.stale
    assert [r["playing"] for r in rig.control.snapshot()["history"]] == [False, True]
    with pytest.raises(RoomError):
        await rig.control.restore("../../etc/passwd", "its")
    with pytest.raises(RoomError):
        await rig.control.restore(rows[0]["id"], "neither")


async def test_a_speaker_check_on_its_own_is_kept_and_marked_while_it_plays(tmp_path):
    """ADR-0189 C2, C4: the check alone is an entry of its own, with its
    delay and level; its alignment marked while it plays."""
    from gexis_core.room_history import History
    rig = Rig(history=History(tmp_path, now=_clock()))
    await rig.measure()
    await check_alone(rig, louder=1.5)
    await asyncio.wait_for(rig.control.run.wait(), 10)
    rows = rig.control.snapshot()["history"]
    assert [r["kind"] for r in rows] == ["speakers", "room"]
    assert rows[0]["aligned"] is True and rows[0]["level_db"] is not None


async def test_a_measurement_kept_before_the_history_is_its_first_entry(tmp_path):
    """ADR-0189 C2: once, dated by the measurement, its time unknown."""
    from gexis_core.room_history import History
    rig = Rig()
    await rig.measure()
    again = Rig(store=rig.store, history=History(tmp_path, now=_clock()))
    rows = again.control.snapshot()["history"]
    assert len(rows) == 1 and rows[0]["playing"] and rows[0]["time"] is None
    assert rows[0]["date"] == rig.control.state().output(DAC.card).measured.date
    third = Rig(store=again.store, history=History(tmp_path, now=_clock()))
    assert len(third.control.snapshot()["history"]) == 1, "never twice"
