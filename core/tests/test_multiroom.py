"""ADR-0166: what a group does on each player - the chain, Snapcast, the
leader moving with the source, the group's Now Playing on a member, the group
volume - with several players simulated in one process."""
from __future__ import annotations

import asyncio

import pytest

from gexis_core import multiroom as mr
from gexis_core import outputs
from gexis_core.adapters.base import Capabilities, VolumeMechanism
from gexis_core.group import Member
from gexis_core.state import StateStore

CAPS = Capabilities(audio_connection="output", acquisition_events=frozenset(), supports_artwork=True,
                    supports_sample_rate=True, volume_managed=True,
                    volume_mechanism=VolumeMechanism.SOFTWARE_API,
                    controls=frozenset({"play", "pause", "next", "previous"}))


class Snap:
    def __init__(self):
        self.on_change = lambda: None
        self.serving = False
        self.host = None
        self.rate = None
        self.connected = {}

    card = True

    async def ensure_card(self, before=None, after=None):
        if not self.card and before is not None:
            await before()
        return self.card

    def card_loaded(self):
        return self.card

    async def serve(self, on):
        self.serving = on

    async def listen(self, host, host_id="", sampleformat=None, latency_ms=0):
        self.host = host

    @property
    def listening(self):
        return self.host is not None

    def caught_up(self, host_id, settle_s=1.5):
        return host_id in self.connected


class FakePeers:
    """The other members' states, set by the test (no network)."""

    def __init__(self):
        self.states, self.reachable = {}, {}

    def follow(self, members):
        for m in members:
            self.reachable.setdefault(m.id, True)

    def stop(self):
        self.states, self.reachable = {}, {}


class FakePlayers:
    def __init__(self, net):
        self.net = net
        self.addresses = {}
        self.on_refresh = None

    def status_of(self, player_id):
        player = self.net.players.get(player_id)
        return player.status_for_others() if player else None


class Player:
    """One simulated player: its store, its source, its multiroom."""

    def __init__(self, net, member: Member, tmp_path, lyrion=None):
        self.member = member
        self.store = StateStore({"spotify": CAPS, "lms": CAPS},
                                sources=({"id": "spotify", "name": "Spotify"}, {"id": "lms", "name": "Lyrion"}))
        self.store.set_volume_raw(100, percent=50)
        self.active = None
        self.stopped = []
        self.rechains = 0
        self.levels = []
        self.lyrion = lyrion
        self.snap = Snap()
        net_ = net

        class Room(mr.Multiroom):
            async def _send(inner, to, record):
                if to.id in net_.off:
                    raise OSError("off")
                await net_.players[to.id].room.receive(record.to_json())
                return True

            async def _post(inner, player_id, path, body):
                if player_id in net_.off:
                    return False
                net_.posts.append((self.member.id, player_id, path, body))
                return True

        async def stop_source():
            was, self.active = self.active, None
            if was:
                self.stopped.append(was)
                self.store.set_active(None)
            return was

        async def rechain():
            self.rechains += 1

        async def set_volume(percent):
            self.levels.append(percent)
            return True

        async def set_mute(muted):
            return True

        lms = None
        if lyrion:
            lms = type("Lms", (), {"player_id": lyrion[1], "server_id": lyrion[0], "sync_group": (None, ())})()
        self.room = Room(store=self.store, players=FakePlayers(net), snap=self.snap, me=lambda: member,
                         local_active=lambda: self.active, stop_source=stop_source, rechain=rechain,
                         chain_card=lambda: ("sndrpihifiberry", True, True), set_own_volume=set_volume,
                         set_own_mute=set_mute, screen=lambda: True, lms=lms, lms_on=lambda: bool(lyrion),
                         group_path=tmp_path / f"{member.id}.json",
                         chain_path=tmp_path / f"{member.id}-chain.json", peers=FakePeers())

    def status_for_others(self):
        return {"id": self.member.id, "name": self.member.name, "host": self.member.host,
                **self.room.status()}

    def play(self, renderer):
        self.active = renderer
        self.store.set_active(renderer)
        self.room.on_local_active(renderer)


class Net:
    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.players: dict[str, Player] = {}
        self.off: set[str] = set()
        self.posts = []

    def add(self, pid, name, lyrion=None) -> Player:
        player = Player(self, Member(pid, name, f"{pid}.local"), self.tmp, lyrion)
        self.players[pid] = player
        return player

    async def settle(self):
        for _ in range(6):
            await asyncio.sleep(0.07)
        statuses = {pid: p.status_for_others() for pid, p in self.players.items() if pid not in self.off}
        for p in self.players.values():
            p.room._statuses = statuses


async def test_joining_puts_both_players_in_the_groups_chain_and_the_member_plays_from_the_leader(tmp_path):
    net = Net(tmp_path)
    living, kitchen = net.add("living", "Living Room"), net.add("kitchen", "Kitchen")
    kitchen.play("spotify")
    await net.settle()
    await living.room.join("kitchen")
    await net.settle()
    # C1: Kitchen's own music stops; both rewrite their chain for the group.
    assert kitchen.stopped == ["spotify"]
    assert living.rechains == kitchen.rechains == 1
    assert living.room.chain == kitchen.room.chain == outputs.ALL, "no Lyrion here: C3's chain"
    assert living.snap.serving and kitchen.snap.serving
    assert living.snap.host == "127.0.0.1" and kitchen.snap.host == "living.local"
    view = kitchen.store.state.group
    assert [m["id"] for m in view["members"]] == ["living", "kitchen"] and view["leader"] == "living"


async def test_a_source_started_on_a_member_makes_it_the_leader_and_stops_the_old_ones(tmp_path):
    net = Net(tmp_path)
    living, kitchen = net.add("living", "Living Room"), net.add("kitchen", "Kitchen")
    await living.room.join("kitchen")
    await net.settle()
    living.play("spotify")
    await net.settle()
    kitchen.play("spotify")  # Spotify moved to Kitchen
    await net.settle()
    assert living.room.record.leader == kitchen.room.record.leader == "kitchen"
    assert living.stopped == ["spotify"], "C1: only the leader's source plays"
    assert kitchen.snap.host == "127.0.0.1" and living.snap.host == "kitchen.local"


async def test_undo_keeps_the_music_on_the_leader_until_its_stream_ends(tmp_path):
    net = Net(tmp_path)
    living, kitchen = net.add("living", "Living Room"), net.add("kitchen", "Kitchen")
    await living.room.join("kitchen")
    living.play("spotify")
    living.snap.rate = 44100
    await net.settle()
    await kitchen.room.undo()
    await net.settle()
    assert kitchen.room.record is None and kitchen.room.chain is None and not kitchen.snap.serving
    # The leader plays on through its own server, then alone.
    assert living.room.record is None and living.snap.serving and living.room.chain == outputs.ALL
    living.snap.rate = None
    living.room._changed()
    await net.settle()
    assert not living.snap.serving and living.room.chain is None


async def test_a_member_shows_the_leaders_now_playing_and_sends_it_the_controls(tmp_path):
    net = Net(tmp_path)
    living, kitchen = net.add("living", "Living Room"), net.add("kitchen", "Kitchen")
    await living.room.join("kitchen")
    await net.settle()
    kitchen.room.peers.states["living"] = {
        "active": "spotify", "capabilities": {"spotify": CAPS.to_json()},
        "controls": {"available": ["pause", "next"], "shuffle": None, "repeat": None},
        "sources": [{"id": "spotify", "name": "Spotify", "mark": "/plugins/spotify/mark"}],
        "metadata": {"title": "Trenulet", "artist": "Gasca Zurli", "artwork": "/artwork/abc.jpg",
                     "transport": "playing", "duration": 132.0, "position": 64.0}}
    kitchen.room.peers.reachable["living"] = True
    kitchen.room._changed()
    await net.settle()
    state = kitchen.store.state
    assert state.active == "spotify" and state.metadata.title == "Trenulet"
    assert state.metadata.artwork == "http://living.local:8090/artwork/abc.jpg", "a picture from the leader"
    assert state.controls["available"] == ["next", "pause"]
    assert kitchen.room.mirroring()
    assert await kitchen.room.forward_transport("next")
    assert net.posts[-1] == ("kitchen", "living", "/transport/next", None)
    # Its own source starting ends the mirror - and makes it the leader.
    kitchen.play("lms")
    await net.settle()
    assert kitchen.store.state.active == "lms"


async def test_the_all_slider_moves_every_variable_member_by_one_step(tmp_path):
    net = Net(tmp_path)
    living, kitchen, study = net.add("living", "Living Room"), net.add("kitchen", "Kitchen"), net.add("study", "Study")
    await living.room.join("kitchen")
    await living.room.join("study")
    await net.settle()
    room = living.room
    room.peers.states.update({"kitchen": {"volume": {"percent": 48, "muted": True}},
                              "study": {"fixed_output": True, "fixed_mute": False}})
    room.peers.reachable.update({"kitchen": True, "study": True})
    room._changed()
    await net.settle()
    moved = await room.group_volume(59, {"living": 50, "kitchen": 48, "study": 30})
    assert moved == {"living": 60, "kitchen": 58}, "Study is Fixed: never moved"
    assert living.levels[-1] == 60
    assert ("living", "kitchen", "/volume", {"percent": 58}) in net.posts
    assert ("living", "kitchen", "/volume/mute", {"muted": False}) in net.posts, "the drag unmutes"


async def test_one_lyrion_server_for_every_member_keeps_squeezelite_on_its_own_chain(tmp_path):
    net = Net(tmp_path)
    living = net.add("living", "Living Room", lyrion=("server-uuid", "player-a"))
    kitchen = net.add("kitchen", "Kitchen", lyrion=("server-uuid", "player-b"))
    await net.settle()
    await living.room.join("kitchen")
    await net.settle()
    assert living.room.chain == kitchen.room.chain == outputs.BUT_LYRION
    # Lyrion playing here in the group's sync frees the card for Squeezelite.
    kitchen.room.peers.states["living"] = {"active": "lms"}
    kitchen.room.peers.reachable["living"] = True
    kitchen.play("lms")
    await net.settle()
    assert kitchen.snap.host is None and kitchen.room.record.leader == "living", \
        "the group plays Lyrion already: its sync, not a new leader"


def test_a_leaders_relative_pictures_are_made_reachable():
    assert mr.absolute("/music/1/cover.jpg", "http://living.local:8090/") == \
        "http://living.local:8090/music/1/cover.jpg"
    assert mr.absolute("http://lms:9000/x.jpg", "http://living.local:8090/") == "http://lms:9000/x.jpg"
    assert mr.absolute(None, "http://living.local:8090/") is None


async def test_without_the_groups_loopback_a_member_still_hears_the_group(tmp_path):
    """sofapi, 2026-10-28: the module stayed in use under the equaliser, the
    reload failed, and the chain named a card that was not there."""
    net = Net(tmp_path)
    living, kitchen = net.add("living", "Living Room"), net.add("kitchen", "Kitchen")
    kitchen.snap.card = False
    await living.room.join("kitchen")
    await net.settle()
    assert kitchen.room.chain == outputs.WITHOUT_LOOPBACK
    assert kitchen.snap.host == "living.local", "it plays the group's music through its own chain"
    assert living.room.chain == outputs.ALL
