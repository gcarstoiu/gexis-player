# SPDX-License-Identifier: GPL-3.0-or-later
"""The radio's favourites (ADR-0180 item 5, decisions 4 and 6)."""
from __future__ import annotations

import pytest

from gexis_core import radio_favourites as rf
from gexis_core.radio_directory import Station


def make_station(n: int, **changes) -> Station:
    fields = dict(id=f"id-{n}", name=f"Station {n}", url=f"http://example.org/{n}",
                  codec="MP3", bitrate=128)
    fields.update(changes)
    return Station(**fields)


class Store(dict):
    def set(self, key, value):
        self[key] = value


@pytest.fixture
def store():
    return Store()


def favourites(store, changes=None):
    return rf.Favourites(store.get, store.set,
                         on_change=(lambda: changes.append(1)) if changes is not None else None)


def test_added_at_the_end_once(store):
    changes = []
    fav = favourites(store, changes)
    assert fav.add(make_station(1)) and fav.add(make_station(2))
    assert not fav.add(make_station(1))
    assert fav.ids() == ["id-1", "id-2"]
    assert len(changes) == 2
    # Kept as plain data the settings store and a backup can carry.
    assert store[rf.KEY][0] == make_station(1).to_json()


def test_kept_across_a_new_reader(store):
    favourites(store).add(make_station(3, logo="https://example.org/3.png"))
    assert favourites(store).all() == [make_station(3, logo="https://example.org/3.png")]


def test_remove(store):
    fav = favourites(store)
    for n in (1, 2, 3):
        fav.add(make_station(n))
    assert fav.remove("id-2")
    assert not fav.remove("id-2")
    assert fav.ids() == ["id-1", "id-3"]


def test_order_must_name_every_favourite_once(store):
    fav = favourites(store)
    for n in (1, 2, 3):
        fav.add(make_station(n))
    assert fav.order(["id-3", "id-1", "id-2"])
    assert fav.ids() == ["id-3", "id-1", "id-2"]
    assert not fav.order(["id-1", "id-2"])                   # one missing
    assert not fav.order(["id-1", "id-1", "id-2", "id-3"])   # one twice
    assert not fav.order(["id-1", "id-2", "id-9"])           # one unknown
    assert fav.ids() == ["id-3", "id-1", "id-2"]


def test_step_goes_round_the_ends_like_presets(store):
    fav = favourites(store)
    for n in (1, 2, 3):
        fav.add(make_station(n))
    assert fav.step("id-1", +1).id == "id-2"
    assert fav.step("id-3", +1).id == "id-1"
    assert fav.step("id-1", -1).id == "id-3"
    assert fav.step("id-9", +1) is None
    fav.order(["id-2", "id-1", "id-3"])
    assert fav.step("id-2", +1).id == "id-1"


def test_one_favourite_steps_to_itself(store):
    fav = favourites(store)
    fav.add(make_station(1))
    assert fav.step("id-1", +1).id == "id-1"


def test_renew_keeps_the_address_the_directory_gave(store):
    fav = favourites(store)
    fav.add(make_station(1))
    fav.renew("id-1", "http://moved.example.org/1")
    assert fav.get("id-1").url == "http://moved.example.org/1"


def test_a_damaged_list_is_read_past(store):
    store[rf.KEY] = [make_station(1).to_json(), "nonsense", {"id": "x"},
                     make_station(1).to_json(), make_station(2).to_json()]
    assert favourites(store).ids() == ["id-1", "id-2"]
    store[rf.KEY] = {"not": "a list"}
    assert favourites(store).all() == []


def test_the_list_has_an_end(store, monkeypatch):
    monkeypatch.setattr(rf, "MOST", 2)
    fav = favourites(store)
    fav.add(make_station(1))
    fav.add(make_station(2))
    with pytest.raises(rf.Full):
        fav.add(make_station(3))


def test_a_long_name_is_cut(store):
    fav = favourites(store)
    fav.add(make_station(1, name="x" * 500))
    assert len(fav.get("id-1").name) == rf.NAME_MOST


def test_address_id_is_stable_and_trims():
    assert rf.address_id("http://a/b") == rf.address_id(" http://a/b ")
    assert rf.address_id("http://a/b") != rf.address_id("http://a/c")


def test_complete_fills_only_what_is_missing(store):
    fav = favourites(store)
    fav.add(make_station(1, codec=None, bitrate=None))
    fav.add(make_station(2))
    fav.complete("id-1", "AAC", 96)
    fav.complete("id-2", "FLAC", 1411)
    assert (fav.get("id-1").codec, fav.get("id-1").bitrate) == ("AAC", 96)
    assert (fav.get("id-2").codec, fav.get("id-2").bitrate) == ("MP3", 128)
