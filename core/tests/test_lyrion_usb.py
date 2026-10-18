"""ADR-0115 decisions 20-24: the folders Lyrion reads from USB drives."""

import json

import pytest

from gexis_core import lyrion_usb as lu


class Store(dict):
    def set(self, key, value):
        self[key] = value

    def delete(self, key):
        self.pop(key, None)


def _usb(tmp_path, store=None):
    root = tmp_path / "usb"
    (root / "AAAA" / "Music" / "Jazz" / "Miles").mkdir(parents=True)
    (root / "AAAA" / "Music" / "Rock").mkdir(parents=True)
    (root / "AAAA" / "System Volume Information").mkdir()
    (root / "AAAA" / ".Trashes").mkdir()
    (root / "AAAA" / "cover.jpg").write_bytes(b"")
    return lu.UsbFolders(store if store is not None else Store(), root=root, is_mount=lambda p: p.endswith("AAAA"),
                         by_uuid=tmp_path / "by-uuid", by_label=tmp_path / "by-label")


def test_browsing_shows_folders_only_and_whether_they_go_deeper(tmp_path):
    usb = _usb(tmp_path)
    assert usb.browse("AAAA", "") == [{"name": "Music", "folder": "Music", "deeper": True}]
    assert usb.browse("AAAA", "Music") == [
        {"name": "Jazz", "folder": "Music/Jazz", "deeper": True},
        {"name": "Rock", "folder": "Music/Rock", "deeper": False},
    ]


def test_browsing_never_leaves_the_drive_or_reads_one_unplugged(tmp_path):
    usb = _usb(tmp_path)
    with pytest.raises(ValueError):
        usb.browse("AAAA", "../..")
    with pytest.raises(ValueError):
        usb.browse("BBBB", "")


def test_a_folder_already_read_is_refused_and_a_wider_one_replaces_those_inside(tmp_path):
    store = Store()
    usb = _usb(tmp_path, store)
    usb.add("AAAA", "Music/Jazz", "MUSIC")
    usb.add("AAAA", "Music/Rock", "MUSIC")
    with pytest.raises(ValueError):
        usb.add("AAAA", "Music/Jazz/Miles", "MUSIC")
    usb.add("AAAA", "Music", "MUSIC")
    assert [e["folder"] for e in usb.all()] == ["Music"]
    assert usb.paths(usb.all()) == [str(tmp_path / "usb" / "AAAA" / "Music")]
    usb.remove("AAAA/Music")
    assert usb.all() == []


def test_the_rows_say_what_is_added_and_offer_a_new_drive_without_adding_it(tmp_path):
    usb = _usb(tmp_path)
    usb.add("CCCC", "", "OLD")
    items = usb.items(usb.all(), ["AAAA"], {"AAAA": "MUSIC"})
    assert items[0]["name"] == "Whole drive" and "OLD" in items[0]["meta"] and "Unplugged" in items[0]["meta"]
    assert items[0]["address"] == "CCCC/"
    assert items[1]["name"] == "MUSIC" and items[1]["meta"].startswith("Not added yet")
    assert "address" not in items[1]


def test_a_label_is_read_from_the_links_udev_makes(tmp_path):
    (tmp_path / "dev").mkdir()
    (tmp_path / "dev" / "sda1").write_bytes(b"")
    (tmp_path / "by-uuid").mkdir()
    (tmp_path / "by-label").mkdir()
    (tmp_path / "by-uuid" / "AAAA").symlink_to(tmp_path / "dev" / "sda1")
    (tmp_path / "by-label" / "My\\x20Music").symlink_to(tmp_path / "dev" / "sda1")
    usb = _usb(tmp_path)
    assert usb.label_of("AAAA") == "My Music"
    assert usb.label_of("ZZZZ") is None


def test_remove_takes_all_three_settings(tmp_path):
    store = Store({lu.KEY: json.dumps([{"drive": "A", "folder": ""}]), lu.MUSIC_KEY: True, lu.SWITCH_KEY: True})
    _usb(tmp_path, store).forget_all()
    assert store == {}


def test_a_player_already_running_lyrion_keeps_its_folders(tmp_path):
    """ADR-0115 decision 21: the update must not take a folder out of
    Lyrion's list - Lyrion would wipe the library and scan it all again."""
    from gexis_core import settings_migrations as sm
    from gexis_core import lyrion_folders as lf

    seen = tmp_path / "seen.json"
    seen.write_text(json.dumps({f"{lf.USB}/AAAA": 1, f"{lf.USB}/BBBB": 2, "/elsewhere/x": 3}))
    store = Store({"lyrion-server.enabled": True})
    sm._lyrion_keeps_its_folders(store, seen)
    assert store[lu.MUSIC_KEY] is True and store[lu.SWITCH_KEY] is True
    assert [e["drive"] for e in json.loads(store[lu.KEY])] == ["AAAA", "BBBB"]
    assert all(e["folder"] == "" for e in json.loads(store[lu.KEY]))

    off = Store({"lyrion-server.enabled": False})
    sm._lyrion_keeps_its_folders(off, seen)
    assert off == {"lyrion-server.enabled": False}


def test_the_migration_runs_only_on_a_player_already_set_up():
    from gexis_core import settings_migrations as sm

    step = sm.MIGRATIONS[-1]
    assert "lyrion-server" in step.note and step.existing_only


def test_the_sheet_names_what_each_drive_has_added(tmp_path):
    usb = _usb(tmp_path)
    for folder in ("Music/Jazz", "Music/Rock", "Podcasts", "Audiobooks"):
        usb.add("AAAA", folder, None)
    meta = usb.sheet_items(usb.all(), ["AAAA"], {})[0]["meta"]
    assert meta.startswith("Added: Jazz, Rock and 2 more")
