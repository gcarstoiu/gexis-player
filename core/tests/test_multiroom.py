"""ADR-0166: what a group does on each player - the chain, Snapcast, the
leader moving with the source, the group's Now Playing on a member, the group
volume - with several players simulated in one process."""
from __future__ import annotations

import asyncio

import pytest

from gexis_core import group as groups
from gexis_core import multiroom as mr
from gexis_core import outputs
from gexis_core.adapters.base import Capabilities, VolumeMechanism
from gexis_core.group import Member
from gexis_core.model import TrackMetadata
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
        self.latency = latency_ms

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
        # As the real list: only a player heard in the last round.
        player = self.net.players.get(player_id)
        return player.status_for_others() if player and player_id not in self.net.off else None


class Player:
    """One simulated player: its store, its source, its multiroom."""

    def __init__(self, net, member: Member, tmp_path, lyrion=None, after_client=None):
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
                if path == "/group/join":
                    # Decision 11: asked to add a player, the leader really does.
                    await net_.players[player_id].room.join(body["player"])
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
            async def told(_self, player=None):
                return True
            lms = type("Lms", (), {"player_id": lyrion[1], "server_id": lyrion[0], "sync_group": (None, ()),
                                   "power_on": told, "sync_with": told, "unsync": told})()
        self.room = Room(store=self.store, players=FakePlayers(net), snap=self.snap, me=lambda: member,
                         local_active=lambda: self.active, stop_source=stop_source, rechain=rechain,
                         chain_card=lambda: ("sndrpihifiberry", True, True), set_own_volume=set_volume,
                         set_own_mute=set_mute, screen=lambda: True, lms=lms, lms_on=lambda: bool(lyrion),
                         after_client=after_client or (lambda rate: 0.0),
                         group_path=tmp_path / f"{member.id}.json",
                         chain_path=tmp_path / f"{member.id}-chain.json", peers=FakePeers())
        # As at a core's start: every change of this player's state is looked
        # at (sofapi, 2026-10-31: without it no test saw what that look did).
        self.room.watch()

    def status_for_others(self):
        return {"id": self.member.id, "name": self.member.name, "host": self.member.host,
                **self.room.status()}

    def play(self, renderer):
        # A source that starts plays: its track is playing.
        self.active = renderer
        self.store.set_active(renderer)
        self.store.set_metadata(renderer, TrackMetadata(transport="playing", source_type=renderer))
        self.room.on_local_active(renderer)

    def come_up(self, renderer):
        """A source that becomes active and plays nothing - Lyrion at a core's
        start (the bar, 2026-10-28)."""
        self.active = renderer
        self.store.set_active(renderer)
        self.store.set_metadata(renderer, TrackMetadata(transport="stopped", source_type=renderer))
        self.room.on_local_active(renderer)

    def starts_playing(self, renderer):
        self.store.set_metadata(renderer, TrackMetadata(transport="playing", source_type=renderer))
        self.room._lead_if_playing()


class Net:
    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.players: dict[str, Player] = {}
        self.off: set[str] = set()
        self.posts = []

    def add(self, pid, name, lyrion=None, after_client=None) -> Player:
        player = Player(self, Member(pid, name, f"{pid}.local"), self.tmp, lyrion, after_client)
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


async def test_a_player_with_the_equaliser_on_plays_earlier_by_what_it_holds(tmp_path):
    """sofapi, 2026-10-28: with its equaliser on it played about 46 ms behind
    the bar. Snapcast keeps the clients in time at the device each opens;
    CamillaDSP's hold comes after it, so it is that client's latency, and
    only that client's."""
    from gexis_core import equaliser as eq
    net = Net(tmp_path)
    asked = []

    def eq_on(rate):
        asked.append(rate)
        return eq.latency_ms(rate or 44100)
    living = net.add("living", "Living Room", after_client=eq_on)
    kitchen = net.add("kitchen", "Kitchen")
    kitchen.play("spotify")
    await net.settle()
    await living.room.join("kitchen")
    await net.settle()
    assert living.snap.host == "127.0.0.1" and kitchen.snap.host == "living.local"
    assert living.snap.latency == 46, "two chunks of 1024 at 44.1 kHz"
    assert kitchen.snap.latency == 0
    assert asked, "the leader's own client asked too"


async def test_a_player_alone_joins_another_group_as_a_whole(tmp_path):
    """ADR-0166 decision 11 (George, 2026-10-28): from a player in no group,
    another group is joined whole - its leader adds this player, and the
    group stays as it was with one player more."""
    net = Net(tmp_path)
    office, garage, study = net.add("office", "Office"), net.add("garage", "Garage"), net.add("study", "Study")
    office.play("spotify")
    await net.settle()
    await office.room.join("garage")
    await net.settle()
    study.play("lms")
    await study.room.enter("office")
    await net.settle()
    for p in (office, garage, study):
        assert p.room.record is not None and p.room.record.leader == "office"
        assert {m.id for m in p.room.record.members} == {"office", "garage", "study"}
    assert study.stopped == ["lms"], "C1: the joining player's own music stops"
    assert ("study", "office", "/group/join", {"player": "study"}) in net.posts


async def test_joining_another_group_is_refused_when_grouped_or_not_a_leader(tmp_path):
    net = Net(tmp_path)
    office, garage, study = net.add("office", "Office"), net.add("garage", "Garage"), net.add("study", "Study")
    await net.settle()
    await office.room.join("garage")
    await net.settle()
    with pytest.raises(mr.GroupError, match="does not lead"):
        await study.room.enter("garage")
    with pytest.raises(mr.GroupError, match="leave it first"):
        await garage.room.enter("office")


async def test_a_leader_joined_to_another_group_leaves_its_own_led_by_a_member(tmp_path):
    """The review of 1.16.1: the members it led were left silent, following
    a leader no longer in their group."""
    net = Net(tmp_path)
    living, kitchen, study = net.add("living", "Living Room"), net.add("kitchen", "Kitchen"), net.add("study", "Study")
    office = net.add("office", "Office")
    await living.room.join("kitchen")
    await living.room.join("study")
    living.play("spotify")
    await net.settle()
    await office.room.join("living")
    await net.settle()
    assert living.room.record.leader == "office" and living.stopped == ["spotify"], "C1"
    assert living.snap.host == "office.local"
    for p in (kitchen, study):
        assert p.room.record.ids() == ["kitchen", "study"] and p.room.record.leader == "kitchen"
    assert kitchen.snap.host == "127.0.0.1" and study.snap.host == "kitchen.local"


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


async def test_a_source_that_only_comes_up_on_a_member_does_not_take_the_lead(tmp_path):
    """The bar, 2026-10-28: three seconds after its core restarted, Lyrion came
    up as its active source and it took the group from sofapi, though nothing
    played. George: only music that plays here leads."""
    net = Net(tmp_path)
    living, kitchen = net.add("living", "Living Room"), net.add("kitchen", "Kitchen")
    living.play("spotify")
    await net.settle()
    await living.room.join("kitchen")
    await net.settle()
    kitchen.come_up("lms")
    await net.settle()
    assert kitchen.room.record.leader == "living" and living.room.record.leader == "living"
    # Then it really plays: now it leads, as decision 4 has it.
    kitchen.starts_playing("lms")
    await net.settle()
    assert kitchen.room.record.leader == "kitchen" and living.room.record.leader == "kitchen"


async def test_a_source_that_never_plays_on_a_member_is_stopped_after_its_wait(tmp_path, monkeypatch):
    monkeypatch.setattr(mr, "LEAD_WAIT_S", 0.3)
    net = Net(tmp_path)
    living, kitchen = net.add("living", "Living Room"), net.add("kitchen", "Kitchen")
    living.play("spotify")
    await net.settle()
    await living.room.join("kitchen")
    await net.settle()
    kitchen.come_up("lms")
    await net.settle()
    await net.settle()
    assert kitchen.stopped == ["lms"], "C1, once it has had its time to play"
    assert kitchen.room.record.leader == "living" and living.stopped == []


async def test_lyrion_started_on_a_member_in_the_leaders_sync_plays_on(tmp_path, monkeypatch):
    """sofapi, 2026-10-31: synced in Lyrion with the group's leader, which
    played nothing; Lyrion started on sofapi was stopped before the leader's
    state said Lyrion, and that paused the sync on both."""
    monkeypatch.setattr(mr, "LEAD_WAIT_S", 0.3)
    net = Net(tmp_path)
    living = net.add("living", "Living Room", lyrion=("server-uuid", "player-a"))
    kitchen = net.add("kitchen", "Kitchen", lyrion=("server-uuid", "player-b"))
    await net.settle()
    await living.room.join("kitchen")
    await net.settle()
    assert kitchen.room.chain == outputs.BUT_LYRION
    kitchen.room._lms.sync_group = ("player-a", ("player-b",))
    kitchen.come_up("lms")
    await net.settle()
    await net.settle()
    assert kitchen.stopped == [], "Lyrion's own sync plays on"
    kitchen.starts_playing("lms")
    await net.settle()
    assert kitchen.room.record.leader == "living", "its leader plays it too: it does not lead"
    assert kitchen.stopped == [] and living.stopped == []


async def test_undo_keeps_the_music_on_the_leader_until_nothing_holds_the_device(tmp_path):
    net = Net(tmp_path)
    living, kitchen = net.add("living", "Living Room"), net.add("kitchen", "Kitchen")
    await living.room.join("kitchen")
    living.play("spotify")
    living.snap.rate = 44100
    await net.settle()
    await kitchen.room.undo()
    await net.settle()
    assert kitchen.room.record is None and kitchen.room.chain is None and not kitchen.snap.serving
    # The leader plays on through its own server, paused too, then alone.
    assert living.room.record is None and living.snap.serving and living.room.chain == outputs.ALL
    living.snap.rate = None
    living.room._changed()
    await net.settle()
    assert living.snap.serving, "paused, Spotify still holds the device: no restart"
    living.play(None)
    await net.settle()
    assert not living.snap.serving and living.room.chain is None


@pytest.mark.parametrize("asked", ["kitchen", "living"])
async def test_undo_while_the_leader_is_paused_waits_until_nothing_holds_the_device(tmp_path, asked):
    """B3 as amended, the review of 1.16.1: paused, the stream into the
    loopback has ended and Spotify still holds the device; going alone at
    the undo restarted it under the paused session."""
    net = Net(tmp_path)
    living, kitchen = net.add("living", "Living Room"), net.add("kitchen", "Kitchen")
    await living.room.join("kitchen")
    living.play("spotify")
    living.snap.rate = 44100
    await net.settle()
    living.store.set_metadata("spotify", TrackMetadata(transport="paused", source_type="spotify"))
    living.snap.rate = None
    await net.settle()
    rechains = living.rechains
    await net.players[asked].room.undo()
    await net.settle()
    assert living.room.record is None
    assert living.rechains == rechains and living.snap.serving, "paused, Spotify still holds the device"
    living.play(None)
    await net.settle()
    assert not living.snap.serving and living.room.chain is None and living.rechains == rechains + 1


async def test_undo_while_lyrion_plays_on_the_leaders_own_chain_goes_alone_at_once(tmp_path):
    # B2: Squeezelite keeps its chain going alone, so nothing waits for it.
    net = Net(tmp_path)
    living = net.add("living", "Living Room", lyrion=("server-uuid", "player-a"))
    kitchen = net.add("kitchen", "Kitchen", lyrion=("server-uuid", "player-b"))
    await net.settle()
    await living.room.join("kitchen")
    await net.settle()
    living.play("lms")
    await net.settle()
    await living.room.undo()
    await net.settle()
    assert living.room.chain is None and not living.snap.serving


async def test_a_source_taking_over_after_an_undo_is_not_restarted(tmp_path):
    """sofapi, 2026-10-28: the group undone while Bluetooth played; a cast
    took over, the stream ended between the two, and going alone restarted
    the renderers - the cast's among them, mid-start."""
    net = Net(tmp_path)
    living, kitchen = net.add("living", "Living Room"), net.add("kitchen", "Kitchen")
    await living.room.join("kitchen")
    living.play("spotify")
    living.snap.rate = 44100
    await net.settle()
    await kitchen.room.undo()
    await net.settle()
    rechains = living.rechains
    living.snap.rate = None
    living.play("lms")
    await net.settle()
    assert living.snap.serving and living.rechains == rechains, "the newcomer plays on, untouched"
    living.play(None)
    await net.settle()
    assert not living.snap.serving and living.room.chain is None


async def test_a_player_that_left_keeps_its_own_music_when_the_old_leader_returns(tmp_path):
    """The review of 1.16.1 (C2): the leader off, Kitchen left the silent
    group and played Spotify; the leader came back with the group it kept,
    and Kitchen took it and stopped Spotify."""
    net = Net(tmp_path)
    living, kitchen, study = net.add("living", "Living Room"), net.add("kitchen", "Kitchen"), net.add("study", "Study")
    await living.room.join("kitchen")
    await living.room.join("study")
    await net.settle()
    net.off.add("living")
    await kitchen.room.leave()
    kitchen.play("spotify")
    await net.settle()
    net.off.clear()
    statuses = {pid: p.status_for_others() for pid, p in net.players.items()}
    await living.room._seen({k: v for k, v in statuses.items() if k != "living"})
    await net.settle()
    assert kitchen.room.record is None and kitchen.stopped == [] and kitchen.room.chain is None


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


async def test_the_leader_hears_a_source_it_starts_after_lyrion(tmp_path):
    """sofapi and the bar, 2026-10-28: Spotify cast to the leader after
    Lyrion played on the bar and not on the leader, whose client Lyrion's
    sync had stopped."""
    net = Net(tmp_path)
    living = net.add("living", "Living Room", lyrion=("server-uuid", "player-a"))
    kitchen = net.add("kitchen", "Kitchen", lyrion=("server-uuid", "player-b"))
    await net.settle()
    await living.room.join("kitchen")
    await net.settle()
    living.play("lms")
    await net.settle()
    assert living.snap.host is None, "Squeezelite plays to the card itself"
    living.play("spotify")
    await net.settle()
    assert living.room.record.leader == "living"
    assert living.snap.host == "127.0.0.1"


async def test_a_chain_changed_on_a_round_keeps_the_member_hearing_the_group(tmp_path):
    """The bar, 2026-10-28: its chain changed on the half-minute round, the
    client was stopped for the rewrite and never started again."""
    net = Net(tmp_path)
    living = net.add("living", "Living Room", lyrion=("server-uuid", "player-a"))
    kitchen = net.add("kitchen", "Kitchen", lyrion=("server-uuid", "player-b"))
    await net.settle()
    await living.room.join("kitchen")
    await net.settle()
    assert kitchen.room.chain == outputs.BUT_LYRION and kitchen.snap.host == "living.local"
    statuses = {pid: p.status_for_others() for pid, p in net.players.items()}
    statuses["living"] = {**statuses["living"], "lyrion": {"server": "another-server", "player": "player-a"}}
    await kitchen.room._seen(statuses)
    await net.settle()
    assert kitchen.room.chain == outputs.ALL
    assert kitchen.snap.host == "living.local", "the client back after the rewrite"


@pytest.mark.parametrize("kept", [None, outputs.WITHOUT_LOOPBACK])
async def test_a_group_kept_without_its_chain_is_put_in_force_at_the_start(tmp_path, kept):
    """The review of 1.16.1: a member started again after the fallback (its
    chain not read at a start) or stopped between keeping the group and its
    chain came up with `output.conf` written for a player alone and the
    group's chain only written down: silent in the group."""
    record = groups.Record.new(Member("living", "Living Room", "living.local"),
                               Member("kitchen", "Kitchen", "kitchen.local"))
    groups.write(record, tmp_path / "kitchen.json")
    if kept:
        mr.write_chain(kept, tmp_path / "kitchen-chain.json")
    net = Net(tmp_path)
    net.add("living", "Living Room")
    kitchen = net.add("kitchen", "Kitchen")
    assert kitchen.room.chain is None, "as `output.conf` was written at this start"
    await kitchen.room.start()
    await net.settle()
    assert kitchen.room.chain == outputs.ALL and kitchen.rechains == 1
    assert mr.read_chain(tmp_path / "kitchen-chain.json") == outputs.ALL
    assert kitchen.snap.host == "living.local"


async def test_a_group_kept_with_its_chain_is_not_written_again_at_the_start(tmp_path):
    record = groups.Record.new(Member("living", "Living Room", "living.local"),
                               Member("kitchen", "Kitchen", "kitchen.local"))
    groups.write(record, tmp_path / "kitchen.json")
    mr.write_chain(outputs.ALL, tmp_path / "kitchen-chain.json")
    net = Net(tmp_path)
    net.add("living", "Living Room")
    kitchen = net.add("kitchen", "Kitchen")
    await kitchen.room.start()
    await net.settle()
    assert kitchen.room.chain == outputs.ALL and kitchen.rechains == 0
    assert kitchen.snap.host == "living.local"


async def test_a_member_silent_for_a_round_does_not_change_the_chain(tmp_path):
    """The bar, 2026-10-28: sofapi, starting a 192 kHz stream, missed one
    round, and the bar's chain went to `all` and back half a minute later."""
    net = Net(tmp_path)
    living = net.add("living", "Living Room", lyrion=("server-uuid", "player-a"))
    kitchen = net.add("kitchen", "Kitchen", lyrion=("server-uuid", "player-b"))
    await net.settle()
    await living.room.join("kitchen")
    await net.settle()
    rechains = kitchen.rechains
    net.off.add("living")
    await kitchen.room._seen({"kitchen": kitchen.status_for_others()})
    assert kitchen.room.chain == outputs.BUT_LYRION and kitchen.rechains == rechains


async def test_lyrion_playing_in_the_leaders_sync_is_not_stopped_on_joining(tmp_path):
    """The bar, 2026-10-28: synced with sofapi in a Lyrion app while it
    played Lyrion, it joined sofapi's group and paused its own player - which
    in Lyrion's sync paused them both."""
    net = Net(tmp_path)
    living = net.add("living", "Living Room", lyrion=("server-uuid", "player-a"))
    kitchen = net.add("kitchen", "Kitchen", lyrion=("server-uuid", "player-b"))
    await net.settle()
    # Synced in a Lyrion app: Lyrion plays the master's stream on both.
    living.play("lms")
    kitchen.play("lms")
    living.room._lms.sync_group = ("player-a", ("player-b",))
    kitchen.room._lms.sync_group = ("player-a", ("player-a",))
    await net.settle()
    await living.room.join("kitchen")
    kitchen.room.peers.states["living"] = {"active": "lms"}
    await net.settle()
    assert kitchen.room.record.leader == "living"
    assert kitchen.stopped == [] and living.stopped == [], "Lyrion's own sync plays on"
    assert kitchen.room.chain == outputs.BUT_LYRION and kitchen.snap.host is None


async def test_lyrion_playing_on_its_own_is_stopped_on_joining(tmp_path):
    net = Net(tmp_path)
    living = net.add("living", "Living Room", lyrion=("server-uuid", "player-a"))
    kitchen = net.add("kitchen", "Kitchen", lyrion=("server-uuid", "player-b"))
    await net.settle()
    kitchen.play("lms")
    await net.settle()
    await living.room.join("kitchen")
    await net.settle()
    assert kitchen.stopped == ["lms"], "C1: not synced with the leader, its own music stops"


class LyrionServer:
    """One Lyrion server, as far as a group needs it: its syncs, and a pause
    on any synced player pausing every one (the bar, 2026-10-28)."""

    def __init__(self):
        self.syncs: list[set[str]] = []
        self.paused: set[str] = set()
        self.unsynced: list[str] = []

    def sync_of(self, player):
        return next((s for s in self.syncs if player in s), {player})

    def take(self, room_player, player):
        """`room_player`'s Lyrion on this server, as `player`; its stop is the
        adapter's release, `pause 1` then `power 0`."""
        server = self

        class Lms:
            player_id, server_id = player, "server-uuid"

            @property
            def sync_group(self):
                others = tuple(sorted(server.sync_of(player) - {player}))
                return (min(server.sync_of(player)) if others else None, others)

            async def power_on(self, other):
                return True

            async def sync_with(self, other):
                joined = server.sync_of(player) | server.sync_of(other)
                server.syncs = [s for s in server.syncs if not s & joined] + [joined]
                return True

            async def unsync(self, other=None):
                target = other or player
                server.unsynced.append(target)
                server.syncs = [s - {target} for s in server.syncs if len(s - {target}) > 1]
                return True
        room_player.room._lms = Lms()
        stop = room_player.room._stop_source

        async def stop_source():
            if room_player.active == "lms":
                server.paused |= server.sync_of(player)
            return await stop()
        room_player.room._stop_source = stop_source


@pytest.mark.parametrize("study_lyrion", [None, ("another-server", "player-c")])
async def test_a_player_off_the_groups_lyrion_joining_does_not_pause_the_group(tmp_path, study_lyrion):
    """The review of 1.16.1 (C3): the group played Lyrion in Lyrion's own
    sync; a player without Lyrion, or on another server, joined, and
    Kitchen's Lyrion - still synced - was stopped as its own music, with
    Lyrion's pause, which paused the leader's too."""
    server = LyrionServer()
    net = Net(tmp_path)
    living = net.add("living", "Living Room", lyrion=("server-uuid", "player-a"))
    kitchen = net.add("kitchen", "Kitchen", lyrion=("server-uuid", "player-b"))
    net.add("study", "Study", lyrion=study_lyrion)
    server.take(living, "player-a")
    server.take(kitchen, "player-b")
    await net.settle()
    await living.room.join("kitchen")
    await net.settle()
    assert server.sync_of("player-a") == {"player-a", "player-b"}, "the group's own sync (D2)"
    living.play("lms")
    kitchen.room.peers.states["living"] = {"active": "lms"}
    kitchen.play("lms")
    await net.settle()
    await living.room.join("study")
    for _ in range(3):
        await net.settle()
    assert living.room.chain == kitchen.room.chain == outputs.ALL
    assert "player-a" not in server.paused, "the leader's Lyrion plays on"
    assert server.unsynced == ["player-b"], "out of Lyrion's sync, which cannot carry the group"
    kitchen.room._changed()  # Lyrion's word that it stopped there
    await net.settle()
    assert kitchen.stopped == ["lms"], "C1, once out of the sync"
    assert "player-a" not in server.paused and living.stopped == []


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


async def test_without_the_groups_loopback_arbitration_asks_about_the_players_own_chain(tmp_path, monkeypatch):
    """The review of 1.16.1: without the group's loopback, arbitration was
    still pointed at it - the card missing - so every look at who holds the
    device raised, and a joining member's change stopped before its client
    started."""
    from gexis_core import __main__ as core_main
    from gexis_core import alsa
    cards = tmp_path / "cards"
    cards.write_text(" 0 [sndrpihifiberry]: HifiberryDac - snd_rpi_hifiberry_dac\n"
                     "                      snd_rpi_hifiberry_dac\n"
                     " 1 [Loopback       ]: Loopback - Loopback\n"
                     "                      Loopback 1\n")
    resolve = alsa.resolve_card_number
    monkeypatch.setattr(alsa, "resolve_card_number", lambda card_id=None, cards_file=None: resolve(card_id, cards))
    monkeypatch.setattr(alsa, "_card", "sndrpihifiberry")
    monkeypatch.setattr(alsa, "_renderers_card", None)
    monkeypatch.setattr(alsa, "_also_card", None)
    monkeypatch.setattr(outputs, "eq_in_path", lambda card: False)
    net = Net(tmp_path)
    living, kitchen = net.add("living", "Living Room"), net.add("kitchen", "Kitchen")
    kitchen.snap.card = False
    monkeypatch.setattr(outputs, "group_in_path", lambda: kitchen.room.chain)

    async def rechain():
        # As `_group_rechain`: who holds the device first, then the cards
        # watched (`_equaliser_follows`) and the client back.
        kitchen.rechains += 1
        alsa.playback_pcm_node()
        core_main._watch_renderers_cards("sndrpihifiberry")
        await kitchen.room.relisten()
    kitchen.room._rechain = rechain
    await living.room.join("kitchen")
    await net.settle()
    assert kitchen.room.chain == outputs.WITHOUT_LOOPBACK
    assert alsa.renderers_card() == "sndrpihifiberry"
    assert kitchen.snap.host == "living.local", "it hears the group"
    assert kitchen.rechains == 1, "the fallback's chain written once"
