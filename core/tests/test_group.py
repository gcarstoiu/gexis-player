"""ADR-0166 D3: the group's record, kept by every member, and its changes."""
from __future__ import annotations

import json

import pytest

from gexis_core import group as g

LIVING = g.Member("living", "Living Room", "livingroom.local")
KITCHEN = g.Member("kitchen", "Kitchen", "kitchen.local")
STUDY = g.Member("study", "Study", "study.local")
OFFICE = g.Member("office", "Office", "office.local")


class Clock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        self.now += 1
        return self.now


class Net:
    """Players that hand each other records as their HTTP API would."""

    def __init__(self, tmp_path):
        self.players: dict[str, g.Group] = {}
        self.applied: dict[str, list] = {}
        self.off: set[str] = set()
        self.tmp = tmp_path
        self.clock = Clock()

    def add(self, member: g.Member) -> g.Group:
        self.applied[member.id] = []

        async def send(to, record):
            if to.id in self.off or to.id not in self.players:
                raise OSError("not reachable")
            await self.players[to.id].receive(record)
            return True

        async def apply(old, new, pid=member.id):
            self.applied[pid].append((old, new))

        player = g.Group(me=lambda: member, send=send, apply=apply,
                         path=self.tmp / f"{member.id}.json", clock=self.clock)
        self.players[member.id] = player
        return player


def test_a_record_survives_its_json():
    record = g.Record.new(LIVING, KITCHEN, clock=lambda: 5.0)
    again = g.Record.from_json(json.loads(json.dumps(record.to_json())))
    assert again == record
    assert again.leader == "living" and again.ids() == ["living", "kitchen"]


def test_a_group_of_one_is_no_group():
    record = g.Record.new(LIVING, KITCHEN)
    assert record.without("kitchen", by="living").ended


def test_a_later_change_of_the_same_group_is_taken_and_an_earlier_one_not():
    record = g.Record.new(LIVING, KITCHEN, clock=lambda: 5.0)
    later = record.with_member(STUDY, by="living", clock=lambda: 6.0)
    assert g.accepts(record, later, "kitchen")
    assert not g.accepts(later, record, "kitchen")


def test_another_group_is_taken_only_by_a_player_in_it():
    mine = g.Record.new(OFFICE, KITCHEN, clock=lambda: 5.0)
    theirs = g.Record.new(LIVING, STUDY, clock=lambda: 7.0)
    assert not g.accepts(mine, theirs, "kitchen")
    joined = theirs.with_member(KITCHEN, by="living", clock=lambda: 8.0)
    assert g.accepts(mine, joined, "kitchen")


async def test_joining_makes_one_record_on_both_players_led_by_the_one_asked(tmp_path):
    net = Net(tmp_path)
    living, kitchen = net.add(LIVING), net.add(KITCHEN)
    record = await living.join(KITCHEN)
    assert living.record == kitchen.record == record
    assert record.leader == "living"
    # Each kept it, for the next start (decision 3).
    assert g.read(tmp_path / "kitchen.json") == record
    assert net.applied["kitchen"] == [(None, record)]


async def test_a_player_joined_from_another_group_leaves_it(tmp_path):
    net = Net(tmp_path)
    office, garage, living = net.add(OFFICE), net.add(g.Member("garage", "Garage", "garage.local")), net.add(LIVING)
    await office.join(g.Member("garage", "Garage", "garage.local"))
    await living.join(g.Member("garage", "Garage", "garage.local"))
    # Garage is in Living Room's group now; Office's group of one is gone.
    assert garage.record.ids() == ["living", "garage"]
    assert office.record is None


async def test_the_leader_cannot_be_removed_and_a_member_can(tmp_path):
    net = Net(tmp_path)
    living, kitchen, study = net.add(LIVING), net.add(KITCHEN), net.add(STUDY)
    await living.join(KITCHEN)
    await living.join(STUDY)
    with pytest.raises(g.GroupError):
        await kitchen.remove("living")
    record = await kitchen.remove("study")
    assert study.record is None
    assert living.record == kitchen.record == record and record.ids() == ["living", "kitchen"]


async def test_undo_ends_the_group_on_every_member(tmp_path):
    net = Net(tmp_path)
    living, kitchen, study = net.add(LIVING), net.add(KITCHEN), net.add(STUDY)
    await living.join(KITCHEN)
    await living.join(STUDY)
    await kitchen.undo()
    assert living.record is kitchen.record is study.record is None
    assert not (tmp_path / "living.json").exists()


async def test_a_source_started_on_a_member_makes_it_the_leader(tmp_path):
    net = Net(tmp_path)
    living, kitchen = net.add(LIVING), net.add(KITCHEN)
    await living.join(KITCHEN)
    record = await kitchen.lead()
    assert record.leader == "kitchen" and living.record.leader == "kitchen"


async def test_a_member_that_was_off_is_brought_up_to_date_when_seen(tmp_path):
    net = Net(tmp_path)
    living, kitchen, study = net.add(LIVING), net.add(KITCHEN), net.add(STUDY)
    await living.join(KITCHEN)
    await living.join(STUDY)
    net.off.add("study")
    record = await living.remove("kitchen")
    assert study.record.has("kitchen")  # it missed the change
    net.off.clear()
    await living.reconcile({"study": {"id": "study", "group": g.summary(study.record)},
                            "kitchen": {"id": "kitchen", "group": None}})
    assert study.record == record


async def test_the_leader_gone_leaves_the_others_grouped(tmp_path):
    # C2: the group is never undone by a player's absence alone.
    net = Net(tmp_path)
    living, kitchen, study = net.add(LIVING), net.add(KITCHEN), net.add(STUDY)
    await living.join(KITCHEN)
    await living.join(STUDY)
    net.off.add("living")
    await kitchen.reconcile({"study": {"id": "study", "group": g.summary(study.record)}})
    assert kitchen.record.leader == "living" and kitchen.record.ids() == ["living", "kitchen", "study"]
    # The next source started on one of them leads; the leader hears of it later.
    await study.lead()
    assert kitchen.record.leader == "study" and living.record.leader == "living"
    net.off.clear()
    await study.reconcile({"living": {"id": "living", "group": g.summary(living.record)},
                           "kitchen": {"id": "kitchen", "group": g.summary(kitchen.record)}})
    assert living.record.leader == "study"


def test_a_player_older_than_multiroom_is_no_member():
    assert g.member_of({"id": "x", "name": "Old", "host": "old.local"}) is None
    assert g.member_of({"id": "x", "name": "New", "host": "new.local", "multiroom": 1}) == \
        g.Member("x", "New", "new.local")


def test_the_all_slider_moves_every_member_by_the_same_step_within_0_to_100():
    levels = {"living": 62, "kitchen": 48, "study": 35}  # mean 48.3
    assert g.step_levels(levels, 58.3333) == {"living": 72, "kitchen": 58, "study": 45}
    assert g.step_levels(levels, 0) == {"living": 14, "kitchen": 0, "study": 0}
    # From the levels when the drag began, the way back keeps the balance.
    assert g.step_levels(levels, 48.3333) == levels


class Peers:
    def __init__(self, states, reachable):
        self.states, self.reachable = states, reachable


def test_the_view_puts_the_leader_first_and_means_the_variable_members():
    record = g.Record.new(LIVING, KITCHEN, STUDY)
    me = g.Live("kitchen", {"volume": {"percent": 48, "muted": False}, "fixed_output": False})
    peers = Peers({"living": {"volume": {"percent": 62, "muted": False}, "active": "lms",
                              "sources": [{"id": "lms", "name": "Lyrion"}],
                              "metadata": {"title": "Rempompi", "transport": "playing"}},
                   "study": {"fixed_output": True, "fixed_mute": False}},
                  {"living": True, "study": True})
    view = g.view(record, me, peers, mode="lyrion", joining=set(), screens={}, urls={})
    assert [m["id"] for m in view["members"]] == ["living", "kitchen", "study"]
    assert view["members"][0]["leads"] and view["members"][1]["me"]
    assert view["members"][2]["fixed"] and view["members"][2]["volume"] is None
    assert view["level"] == 55 and not view["muted"]
    assert view["source"]["name"] == "Lyrion" and view["title"] == "Rempompi"
    assert not view["silent"]


def test_the_leader_gone_makes_the_group_silent():
    record = g.Record.new(LIVING, KITCHEN)
    me = g.Live("kitchen", {"volume": {"percent": 42, "muted": False}})
    view = g.view(record, me, Peers({}, {"living": False}), mode="snapcast", joining=set(),
                  screens={}, urls={})
    assert view["silent"] and view["source"] is None
    assert not view["members"][0]["reachable"] and view["level"] == 42
