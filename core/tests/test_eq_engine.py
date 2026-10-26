"""The equaliser's engine on the loopback (ADR-0162 D1-D7, Finding 138), with
CamillaDSP, systemd and ALSA's tools played by fakes."""
import asyncio
import json

import pytest

from gexis_core import eq_engine
from gexis_core import equaliser as eq
from gexis_core.eq_engine import EqEngine, Stream, parse_contents


def contents(active="on", rate=44100, fmt=10, channels=2):
    """`amixer -D hw:Loopback contents` as the loopback prints it: device 0's
    controls first (unused), then device 1's, where a stream shows."""
    def block(numid, name, value, where=""):
        return (f"numid={numid},iface=PCM,name='PCM Slave {name}'{where}\n"
                f"  ; type=INTEGER,access=r----v--,values=1,min=0,max=1,step=0\n"
                f"  : values={value}\n")
    return ("numid=1,iface=PCM,name='PCM Rate Shift 100000'\n  : values=100000\n"
            + block(3, "Active", "off") + block(4, "Format", 2) + block(5, "Rate", 48000) + block(6, "Channels", 2)
            + block(59, "Active", active, ",device=1") + block(60, "Format", fmt, ",device=1")
            + block(61, "Rate", rate, ",device=1") + block(62, "Channels", channels, ",device=1"))


def test_the_stream_is_read_from_device_1():
    assert parse_contents(contents()) == Stream(44100, "S32_LE", 2)
    assert parse_contents(contents(rate=96000, fmt=32)) == Stream(96000, "S24_3LE", 2)
    assert parse_contents(contents(fmt=52)).dsd
    assert parse_contents(contents(active="off")) is None
    assert parse_contents(contents(fmt=99)) is None, "a format no renderer sends"
    assert parse_contents("") is None


class FakeCamilla:
    def __init__(self):
        self.sent = []

    async def cmd(self, name, arg=None):
        self.sent.append((name, arg))
        return None

    async def close(self):
        self.sent.append(("close", None))


class Rig:
    def __init__(self, monkeypatch, tmp_path, takes_rate=lambda card, rate: True, give=False):
        self.camilla = FakeCamilla()

        async def give_back(db):
            # Into CamillaDSP's list, so the order between the two is seen.
            self.camilla.sent.append(("give", db))
        self.units = []
        self.amixer = contents(active="off")
        self.spawned = []

        async def systemctl(*args):
            self.units.append(args)

        self.modprobed = []

        async def run(*args, timeout=5):
            if args[0] == "modprobe":
                self.modprobed.append(args)
                return ""
            assert args[:3] == ("amixer", "-D", "hw:Loopback")
            return self.amixer

        self.statuses = []
        self.cards = tmp_path / "cards"
        self.cards.write_text(" 0 [sndrpihifiberry]: HifiberryDacp - snd_rpi_hifiberry_dacplus\n"
                              " 7 [Loopback       ]: Loopback - Loopback\n")
        self.engine = EqEngine(camilla=self.camilla, systemctl=systemctl, run=run,
                               on_change=self.statuses.append, takes_rate=takes_rate, cards=self.cards,
                               give_back=give_back if give else None)

        async def no_watch():
            await asyncio.sleep(3600)
        monkeypatch.setattr(self.engine, "_watching", no_watch)

        class Proc:
            returncode = None
            def terminate(self):
                self.returncode = 0
            def kill(self):
                self.returncode = -9
            async def wait(self):
                return 0

        async def exec_(*args, **kwargs):
            self.spawned.append(args)
            return Proc()
        monkeypatch.setattr(eq_engine.asyncio, "create_subprocess_exec", exec_)

    async def settle(self):
        for _ in range(20):
            await asyncio.sleep(0)
        if self.engine._push is not None:
            await self.engine._push


async def test_on_starts_camilladsp_and_waits_for_a_stream(monkeypatch, tmp_path):
    rig = Rig(monkeypatch, tmp_path)
    await rig.engine.configure("sndrpihifiberry", eq.PRESET["rock"].gains)
    assert ("start", eq_engine.UNIT) in rig.units
    await rig.engine._look()
    assert not [s for s in rig.camilla.sent if s[0] == "SetConfigJson"], "nothing plays: nothing to start"
    assert rig.engine.status()["running"] is True


async def test_a_stream_starts_it_at_its_own_rate_lowered_first(monkeypatch, tmp_path):
    rig = Rig(monkeypatch, tmp_path)
    await rig.engine.configure("sndrpihifiberry", eq.PRESET["rock"].gains)
    rig.amixer = contents(rate=96000, fmt=6)
    await rig.engine._look()
    names = [s[0] for s in rig.camilla.sent if s[0] != "close"]
    assert names[:2] == ["SetFaderVolume", "SetConfigJson"], "the room before the boost"
    assert rig.camilla.sent[1] == ("SetFaderVolume", [1, -5.0])
    config = json.loads(next(a for n, a in rig.camilla.sent if n == "SetConfigJson"))
    assert config["devices"]["samplerate"] == 96000
    assert config["devices"]["capture"]["format"] == "S24_4_RJ_LE"
    assert config["devices"]["playback"]["device"] == "gexis_eq_out"
    assert config["filters"]["band_31"]["parameters"]["gain"] == 4


async def test_a_dragged_band_is_patched_and_the_headroom_moves_first(monkeypatch, tmp_path):
    rig = Rig(monkeypatch, tmp_path)
    monkeypatch.setattr(eq_engine, "RAMP_S", 0)
    await rig.engine.configure("sndrpihifiberry", eq.FLAT)
    rig.amixer = contents()
    await rig.engine._look()
    rig.camilla.sent.clear()
    await rig.engine.configure("sndrpihifiberry", (0, 0, 6, 0, 0, 0, 0, 0, 0, 0))
    await rig.settle()
    assert rig.camilla.sent[0] == ("SetFaderVolume", [1, -6.0]), "a rising headroom first"
    assert rig.camilla.sent[1] == ("PatchConfig", {"filters": {"band_125": {"parameters": {"gain": 6}}}})
    rig.camilla.sent.clear()
    await rig.engine.configure("sndrpihifiberry", eq.FLAT)
    await rig.settle()
    assert rig.camilla.sent == [("PatchConfig", {"filters": {"band_125": {"parameters": {"gain": 0}}}}),
                                ("SetFaderVolume", [1, -0.0])], "a falling one after the cut"


async def test_a_change_while_nothing_plays_waits_for_the_next_stream(monkeypatch, tmp_path):
    rig = Rig(monkeypatch, tmp_path)
    await rig.engine.configure("sndrpihifiberry", eq.FLAT)
    await rig.engine.configure("sndrpihifiberry", eq.PRESET["jazz"].gains)
    await rig.settle()
    assert not [s for s in rig.camilla.sent if s[0] in ("PatchConfig", "SetConfigJson")]
    rig.amixer = contents()
    await rig.engine._look()
    config = json.loads(next(a for n, a in rig.camilla.sent if n == "SetConfigJson"))
    assert config["filters"]["band_31"]["parameters"]["gain"] == 3


async def test_dsd_goes_past_it_untouched(monkeypatch, tmp_path):
    rig = Rig(monkeypatch, tmp_path)
    await rig.engine.configure("AUDIO", eq.PRESET["rock"].gains)
    rig.amixer = contents(rate=352800, fmt=52)
    await rig.engine._look()
    assert not [s for s in rig.camilla.sent if s[0] == "SetConfigJson"]
    alsaloop = rig.spawned[-1]
    assert alsaloop[0] == "alsaloop" and "hw:AUDIO" in alsaloop and "DSD_U32_BE" in alsaloop
    assert rig.engine.status()["dsd"] is True
    rig.amixer = contents(active="off")
    await rig.engine._look()
    assert rig.engine.status()["dsd"] is False


async def test_a_rate_the_card_lacks_is_converted_to_its_highest(monkeypatch, tmp_path):
    rig = Rig(monkeypatch, tmp_path, takes_rate=lambda card, rate: rate != 88200)
    monkeypatch.setattr(eq_engine.outputs, "top_rate", lambda card: 192000)
    await rig.engine.configure("Adapter", eq.FLAT)
    rig.amixer = contents(rate=88200)
    await rig.engine._look()
    d = json.loads(next(a for n, a in rig.camilla.sent if n == "SetConfigJson"))["devices"]
    assert d["capture_samplerate"] == 88200 and d["samplerate"] == 192000 and d["resampler"]["type"] == "AsyncSinc"


async def test_off_stops_it(monkeypatch, tmp_path):
    rig = Rig(monkeypatch, tmp_path)
    await rig.engine.configure("sndrpihifiberry", eq.FLAT)
    await rig.engine.configure(None, eq.FLAT)
    assert rig.units[-1] == ("stop", eq_engine.UNIT)
    assert rig.engine.status()["running"] is False


async def test_another_output_restarts_camilladsp(monkeypatch, tmp_path):
    rig = Rig(monkeypatch, tmp_path)
    await rig.engine.configure("sndrpihifiberry", eq.FLAT)
    await rig.engine.configure("vc4hdmi0", eq.FLAT)
    assert rig.units[-1] == ("restart", eq_engine.UNIT), "it reads output.conf only when it starts"


async def test_the_loopback_is_loaded_when_it_is_not_there(monkeypatch, tmp_path):
    rig = Rig(monkeypatch, tmp_path)
    await rig.engine.configure("sndrpihifiberry", eq.FLAT)
    assert rig.modprobed == [], "loaded at boot"
    await rig.engine.configure(None, eq.FLAT)
    rig.cards.write_text(" 0 [sndrpihifiberry]: HifiberryDacp - snd_rpi_hifiberry_dacplus\n")
    await rig.engine.configure("sndrpihifiberry", eq.FLAT)
    assert rig.modprobed == [("modprobe", "snd-aloop")], "updated since the last boot"


# ---- D3 as amended: the volume gives the headroom back ---------------------------


async def test_while_nothing_plays_the_headroom_is_given_back_at_once(monkeypatch, tmp_path):
    rig = Rig(monkeypatch, tmp_path, give=True)
    await rig.engine.configure("sndrpihifiberry", eq.PRESET["rock"].gains)
    await rig.engine.configure("sndrpihifiberry", eq.PRESET["late"].gains)
    await rig.engine.configure("sndrpihifiberry", eq.PRESET["late"].gains)
    assert [s for s in rig.camilla.sent if s[0] == "give"] == [("give", 5.0), ("give", 6.0)], "once a change"
    await rig.engine.configure(None, eq.FLAT)
    assert rig.camilla.sent[-1] == ("give", 0.0), "off: taken back, after CamillaDSP stopped"


async def test_a_rising_headroom_is_given_back_after_the_lowering_and_a_falling_one_before(monkeypatch, tmp_path):
    """The quiet side of each change: the volume never gives back what the
    equaliser has not yet lowered, so a change is a short dip, never louder."""
    rig = Rig(monkeypatch, tmp_path, give=True)
    monkeypatch.setattr(eq_engine, "RAMP_S", 0)
    await rig.engine.configure("sndrpihifiberry", eq.FLAT)
    rig.amixer = contents()
    await rig.engine._look()
    rig.camilla.sent.clear()
    await rig.engine.configure("sndrpihifiberry", (0, 0, 6, 0, 0, 0, 0, 0, 0, 0))
    await rig.settle()
    assert [s[0] for s in rig.camilla.sent] == ["SetFaderVolume", "PatchConfig", "give"]
    assert rig.camilla.sent[-1] == ("give", 6.0)
    rig.camilla.sent.clear()
    await rig.engine.configure("sndrpihifiberry", eq.FLAT)
    await rig.settle()
    assert rig.camilla.sent == [("give", 0.0),
                                ("PatchConfig", {"filters": {"band_125": {"parameters": {"gain": 0}}}}),
                                ("SetFaderVolume", [1, -0.0])]


async def test_a_stream_starts_with_the_headroom_already_given_back(monkeypatch, tmp_path):
    rig = Rig(monkeypatch, tmp_path, give=True)
    await rig.engine.configure("sndrpihifiberry", eq.PRESET["rock"].gains)
    rig.amixer = contents()
    await rig.engine._look()
    sent = [s for s in rig.camilla.sent if s[0] != "close"]
    assert sent[0] == ("give", 5.0) and [s[0] for s in sent[1:3]] == ["SetFaderVolume", "SetConfigJson"]
    assert [s for s in sent if s[0] == "give"] == [("give", 5.0)]


async def test_a_volume_that_cannot_give_back_does_not_stop_the_equaliser(monkeypatch, tmp_path):
    rig = Rig(monkeypatch, tmp_path)

    async def broken(db):
        raise OSError("no control")
    rig.engine._give_back = broken
    await rig.engine.configure("sndrpihifiberry", eq.PRESET["rock"].gains)
    rig.amixer = contents()
    await rig.engine._look()
    assert any(s[0] == "SetConfigJson" for s in rig.camilla.sent)
