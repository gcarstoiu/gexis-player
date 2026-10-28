"""ADR-0166 D1 as amended (Finding 139): snapserver reads one pipe per rate,
fed from the group's loopback while something plays into it."""
from __future__ import annotations

import asyncio

import pytest

from gexis_core import outputs, snapcast

PLAYING_44 = """numid=3,iface=PCM,name='PCM Slave Active',device=1
  ; type=BOOLEAN,access=r-------,values=1
  : values=on
numid=4,iface=PCM,name='PCM Slave Format',device=1
  ; type=INTEGER,access=r-------,values=1,min=0,max=52,step=0
  : values=10
numid=5,iface=PCM,name='PCM Slave Rate',device=1
  ; type=INTEGER,access=r-------,values=1,min=8000,max=768000,step=0
  : values=44100
numid=6,iface=PCM,name='PCM Slave Channels',device=1
  ; type=INTEGER,access=r-------,values=1,min=1,max=1024,step=0
  : values=2
"""
IDLE = PLAYING_44.replace(": values=on", ": values=off")


def test_the_server_answers_this_player_only_and_has_a_pipe_per_rate(tmp_path):
    conf = snapcast.server_config(400, run_dir=tmp_path)
    assert "[http]\nenabled = false" in conf, "no web page, no HTTP control"
    assert "bind_to_address = 127.0.0.1\nport = 1705" in conf, "control on loopback only"
    assert "port = 1704" in conf and "buffer = 400" in conf
    for rate in snapcast.RATES:
        assert f"pipe://{tmp_path}/{rate}?name=r{rate}&mode=create&sampleformat={rate}:32:2" in conf
    assert "initial_volume = 100" in conf, "D6: Snapcast's own volume never scales"


def test_the_client_is_told_the_leader_its_id_and_only_a_format_its_card_needs():
    env = snapcast.client_env("192.0.2.7", "abc123", 0, None)
    assert "GEXIS_SNAP_HOST=192.0.2.7\n" in env and "GEXIS_SNAP_ID=abc123\n" in env
    assert "GEXIS_SNAP_OPTS=\n" in env
    assert "GEXIS_SNAP_OPTS=--sampleformat *:16:*" in snapcast.client_env("h", "i", 0, "*:16:*")


def test_a_card_without_32_bits_is_given_the_widest_it_takes(monkeypatch):
    formats = {"Headphones": frozenset({"S16_LE"}), "usb": frozenset({"S16_LE", "S24_LE"}),
               "dac": frozenset({"S16_LE", "S24_LE", "S32_LE"})}
    monkeypatch.setattr(outputs, "formats_of", lambda card: formats.get(card, frozenset()))
    assert snapcast.sample_format_for("Headphones", False) == "*:16:*"
    assert snapcast.sample_format_for("usb", False) == "*:24:*"
    assert snapcast.sample_format_for("dac", False) is None
    assert snapcast.sample_format_for("Headphones", True) is None, "the equaliser's chain takes 32"
    assert snapcast.sample_format_for("unknown", False) is None, "not asked: as it comes"


class FakeControl:
    def __init__(self, groups):
        self.groups = groups
        self.calls = []

    async def call(self, method, params=None, timeout=3.0):
        self.calls.append((method, params))
        if method == "Server.GetStatus":
            return {"server": {"groups": self.groups}}
        if method == "Group.SetStream":
            for g in self.groups:
                if g["id"] == params["id"]:
                    g["stream_id"] = params["stream_id"]
        return {}


@pytest.fixture
def pipes(tmp_path, monkeypatch):
    monkeypatch.setattr(snapcast, "RUN_DIR", tmp_path)
    import os
    for rate in snapcast.RATES:
        os.mkfifo(tmp_path / str(rate))
    return tmp_path


async def test_a_stream_into_the_loopback_is_fed_to_its_rates_pipe_and_the_clients_moved_to_it(pipes, monkeypatch):
    import os
    reader = os.open(pipes / "44100", os.O_RDONLY | os.O_NONBLOCK)
    contents = {"text": PLAYING_44}
    started = []

    async def run(*args, timeout=20):
        return 0, contents["text"] if args[:1] == ("amixer",) else ""

    class Proc:
        returncode = None

        def terminate(self):
            self.returncode = 0

        async def wait(self):
            return 0

    async def spawn(*args, **kwargs):
        started.append(args)
        return Proc()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    control = FakeControl([{"id": "g1", "stream_id": "r48000", "clients": []}])
    snap = snapcast.Snapcast(run=run, control=control)
    await snap._look()
    assert snap.rate == 44100
    assert started and started[0][0] == "arecord" and "44100" in started[0]
    assert "Multiroom" in " ".join(started[0]) and "S32_LE" in started[0]
    assert control.groups[0]["stream_id"] == "r44100"
    # The stream ends: the capture is let go, so the next opens at its own rate.
    contents["text"] = IDLE
    await snap._look()
    assert snap.rate is None and snap._feeder is None
    os.close(reader)


async def test_a_stream_the_group_cannot_carry_is_not_fed(pipes):
    async def run(*args, timeout=20):
        return 0, PLAYING_44.replace(": values=44100", ": values=22050")
    snap = snapcast.Snapcast(run=run, control=FakeControl([]))
    await snap._look()
    assert snap.rate is None


async def test_a_client_is_restarted_only_when_what_it_plays_from_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(snapcast, "CLIENT_ENV", tmp_path / "snapclient.env")
    calls = []

    async def run(*args, timeout=20):
        calls.append(args)
        return 0, ""
    snap = snapcast.Snapcast(run=run, control=FakeControl([]))
    await snap.listen("192.0.2.7", "me")
    await snap.listen("192.0.2.7", "me")
    assert calls == [("systemctl", "restart", snapcast.CLIENT_UNIT)]
    await snap.listen(None)
    assert calls[-1] == ("systemctl", "stop", snapcast.CLIENT_UNIT) and not snap.listening


async def test_the_groups_card_is_made_again_when_only_the_equalisers_is_there(tmp_path):
    cards = tmp_path / "cards"
    cards.write_text(" 6 [Loopback       ]: Loopback - Loopback\n")
    calls = []

    async def run(*args, timeout=20):
        calls.append(args)
        if args == ("modprobe", "snd-aloop") and ("modprobe", "-r", "snd-aloop") in calls:
            cards.write_text(cards.read_text() + " 7 [Multiroom      ]: Loopback - Loopback\n")
        return 0, ""
    stopped = []

    async def before():
        stopped.append(True)
    snap = snapcast.Snapcast(run=run, control=FakeControl([]), cards=cards)
    assert await snap.ensure_card(before_reload=before)
    assert stopped and ("modprobe", "-r", "snd-aloop") in calls
