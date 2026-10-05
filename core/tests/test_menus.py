"""ADR-0118: Lyrion's own menus, walked by handle. The shapes below are the
ones read from George's server on 2026-10-05 (Finding 111), trimmed."""
from __future__ import annotations

import pytest

from gexis_core.menus import LyrionMenus
from gexis_core.radio import UnknownHandle

HOME = [
    {"node": "home", "id": "myMusic", "text": "My Music", "weight": 11},
    {"node": "home", "id": "favorites", "text": "Favourites", "weight": 30,
     "actions": {"go": {"cmd": ["favorites", "items"], "params": {"menu": "favorites"}}}},
    {"node": "home", "id": "radios", "text": "Radio", "weight": 20},
    {"node": "home", "id": "opmlmyapps", "text": "My Apps", "weight": 45},
    {"node": "home", "id": "globalSearch", "text": "Search", "weight": 50, "input": {"len": 1}},
    {"node": "home", "id": "playerpower", "text": "Turn Off gexis", "weight": 100,
     "actions": {"do": {"cmd": ["power", "0"]}}},
    {"node": "home", "id": "someAppCategory", "text": "Podcasts Plus", "weight": 40,
     "actions": {"go": {"cmd": ["podplus", "items"], "params": {"menu": "podplus"}}}},
    {"node": "myMusic", "id": "myMusicArtistsAlbumArtists", "text": "Album Artists", "weight": 10,
     "actions": {"go": {"cmd": ["browselibrary", "items"], "params": {"mode": "artists", "role_id": "ALBUMARTIST"}}}},
    {"node": "myMusic", "id": "myMusicGenres", "text": "Genres", "weight": 60,
     "actions": {"go": {"cmd": ["browselibrary", "items"], "params": {"mode": "genres"}}}},
    {"node": "myMusic", "id": "myMusicPlaylists", "text": "Playlists", "weight": 80,
     "actions": {"go": {"cmd": ["browselibrary", "items"], "params": {"mode": "playlists"}}}},
    {"node": "myMusic", "id": "myMusicAlbums", "text": "Albums", "weight": 40,
     "actions": {"go": {"cmd": ["browselibrary", "items"], "params": {"mode": "albums"}}}},
    {"node": "settings", "id": "alarm", "text": "Alarm Clock", "weight": 10,
     "actions": {"go": {"cmd": ["alarm", "items"]}}},
]

QOBUZ_ALBUM_PAGE = {
    "count": 4,
    "base": {"actions": {
        "go": {"cmd": ["qobuz", "items"], "itemsParams": "params"},
        "play": {"cmd": ["qobuz", "playlist", "play"], "itemsParams": "params", "nextWindow": "nowPlaying"},
        "add": {"cmd": ["qobuz", "playlist", "add"], "itemsParams": "params"},
        "add-hold": {"cmd": ["qobuz", "playlist", "insert"], "itemsParams": "params"},
        "set-preset-1": {"cmd": ["jivefavorites", "set_preset", "key:1"], "itemsParams": "params"},
    }},
    "item_loop": [
        {"text": "Gjallarhorn\nAmon Amarth", "style": "itemplay", "goAction": "play",
         "params": {"item_id": "5.2.0"}},
        {"text": "Artist: Amon Amarth",
         "actions": {"go": {"cmd": ["qobuz", "items"], "params": {"menu": "qobuz", "item_id": "5.2.10"}}}},
        {"text": "Add Release 'The Allfather Awakens' to Qobuz favourites",
         "actions": {"go": {"cmd": ["qobuz", "items"], "nextWindow": "parent",
                            "params": {"menu": "qobuz", "item_id": "5.2.11"}}}},
        {"text": "Genre: Metal", "type": "text", "style": "itemNoAction"},
        {"text": "__TAGGEDINPUT__", "actions": {"go": {"cmd": ["qobuz", "items"], "params": {"item_id": "5.9"}}}},
    ],
}

APPS = {
    "count": 2,
    "base": {"actions": {"play": {"cmd": ["playlist", "play"]}, "add": {"cmd": ["playlist", "add"]}}},
    "item_loop": [
        {"text": "Qobuz", "type": "redirect", "icon": "plugins/Qobuz/html/images/qobuz.png",
         "actions": {"go": {"cmd": ["qobuz", "items"], "params": {"menu": "qobuz"}}}},
        {"text": "Spotty", "type": "redirect",
         "actions": {"go": {"cmd": ["spotty", "items"], "params": {"menu": "spotty"}}}},
    ],
}

SPOTTY = {
    "count": 3,
    "base": {"actions": {"go": {"cmd": ["spotty", "items"], "itemsParams": "params"},
                         "play": {"cmd": ["spotty", "playlist", "play"], "itemsParams": "params"}}},
    "item_loop": [
        {"text": "Search", "type": "search", "input": {"len": 1},
         "actions": {"go": {"cmd": ["spotty", "items"], "params": {"menu": "spotty", "search": "__TAGGEDINPUT__"}}}},
        {"text": "Top Tracks", "type": "playlist", "params": {"item_id": "3"}},
        {"text": "Transfer Playback", "type": "link", "icon": "plugins/Spotty/html/images/transfer.png",
         "actions": {"go": {"cmd": ["spotty", "items"], "params": {"item_id": "10"}}}},
    ],
}


class Lyrion:
    def __init__(self):
        self.asked = []

    async def __call__(self, command, player):
        self.asked.append(list(command))
        if command[0] == "menu":
            return {"item_loop": HOME}
        if command[:2] == ["myapps", "items"]:
            return APPS
        if command[:2] == ["qobuz", "items"]:
            return QOBUZ_ALBUM_PAGE
        if command[:2] == ["spotty", "items"]:
            return SPOTTY
        return {}


def menus(lyrion=None):
    return LyrionMenus(lyrion or Lyrion(), lambda: "88:a2:9e:79:e1:32", lambda: "http://lms:9000")


@pytest.mark.asyncio
async def test_the_tiles_are_my_music_favourites_apps_and_what_an_app_adds():
    """ADR-0118 A, C, F, G: no tile for Lyrion's Radio (ours stays), its
    global Search, or the player's power; a category an app adds gets one."""
    tiles = await menus().tiles()
    assert [(t["key"], t["id"]) for t in tiles] == [
        ("mymusic", "myMusic"), ("favorites", "favorites"), ("other", "someAppCategory"), ("apps", "opmlmyapps")]


@pytest.mark.asyncio
async def test_my_music_leaves_out_what_our_screens_already_are():
    """ADR-0118 C: Album Artists and Playlists, by id; in Lyrion's order."""
    m = menus()
    tiles = {t["key"]: t for t in await m.tiles()}
    page = await m.browse(tiles["mymusic"]["handle"])
    assert [r["label"] for r in page["items"]] == ["Albums", "Genres"]


@pytest.mark.asyncio
async def test_an_album_page_plays_its_tracks_and_hides_the_entry_that_writes():
    """ADR-0118 D and J: tracks play, add and play next as Lyrion offers;
    the favourites entry (nextWindow: parent) is not a folder and not shown;
    a text line is inert; preset buttons are never offered."""
    m = menus()
    m._handles["album"] = {"kind": "folder", "cmd": ["qobuz", "items"], "params": {"item_id": "5.2"}}
    page = await m.browse("album")
    rows = {r["label"]: r for r in page["items"]}
    assert set(rows) == {"Gjallarhorn", "Artist: Amon Amarth", "Genre: Metal"}
    assert rows["Gjallarhorn"]["kind"] == "play" and rows["Gjallarhorn"]["subtitle"] == "Amon Amarth"
    assert rows["Gjallarhorn"]["can"] == ["add", "next", "play"]
    assert rows["Artist: Amon Amarth"]["kind"] == "folder" and rows["Genre: Metal"]["kind"] == "text"


@pytest.mark.asyncio
async def test_apps_are_folders_and_transfer_playback_is_left_out():
    """A list's base offers play to every item in it; an app is still a
    folder. Spotty's Transfer Playback, by its icon."""
    m = menus()
    apps = await m.browse(next(t for t in await m.tiles() if t["key"] == "apps")["handle"])
    assert [(r["label"], r["kind"], r["can"]) for r in apps["items"]] == [("Qobuz", "folder", []), ("Spotty", "folder", [])]
    assert apps["items"][0]["image"] == "http://lms:9000/plugins/Qobuz/html/images/qobuz.png"
    spotty = await m.browse(apps["items"][1]["handle"])
    assert [(r["label"], r["kind"]) for r in spotty["items"]] == [("Search", "search"), ("Top Tracks", "container")]


@pytest.mark.asyncio
async def test_only_what_lyrion_offers_is_done_and_only_by_an_issued_handle():
    lyrion = Lyrion()
    m = menus(lyrion)
    m._handles["album"] = {"kind": "folder", "cmd": ["qobuz", "items"], "params": {}}
    track = next(r for r in (await m.browse("album"))["items"] if r["kind"] == "play")
    await m.act(track["handle"], "next")
    assert lyrion.asked[-1] == ["qobuz", "playlist", "insert", "item_id:5.2.0"]
    folder = next(r for r in (await m.browse("album"))["items"] if r["kind"] == "folder")
    with pytest.raises(UnknownHandle):
        await m.act(folder["handle"], "play")
    with pytest.raises(UnknownHandle):
        await m.act("not-ours", "play")


@pytest.mark.asyncio
async def test_a_search_takes_the_typed_text_where_lyrion_asks_for_it():
    """ADR-0118 E: the phone's text in place of __TAGGEDINPUT__."""
    lyrion = Lyrion()
    m = menus(lyrion)
    apps = await m.browse(next(t for t in await m.tiles() if t["key"] == "apps")["handle"])
    spotty = await m.browse(apps["items"][1]["handle"])
    found = await m.search(spotty["items"][0]["handle"], "  daft   punk ")
    assert "search:daft punk" in lyrion.asked[-1] and found["handle"]
    with pytest.raises(UnknownHandle):
        await m.search(spotty["items"][1]["handle"], "x")


class Settings:
    def __init__(self, **values):
        self.values = values

    def value(self, key):
        return self.values.get(key)


@pytest.mark.asyncio
async def test_the_routes_answer_only_with_extended_navigation_on():
    """ADR-0118 B: off by default - no tiles, and browsing refused."""
    from aiohttp.test_utils import TestClient, TestServer

    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    settings = Settings(lms_enabled=True)
    server = StateServer(StateStore({}), settings=settings, menus=menus())
    async with TestClient(TestServer(server.make_app())) as client:
        assert await (await client.get("/menus")).json() == {"on": False, "tiles": []}
        assert (await client.get("/menus/browse?at=x")).status == 409
        settings.values["lms_extended_nav"] = True
        body = await (await client.get("/menus")).json()
        assert body["on"] is True and [t["key"] for t in body["tiles"]][0] == "mymusic"
        page = await (await client.get(f"/menus/browse?at={body['tiles'][0]['handle']}")).json()
        assert [r["label"] for r in page["items"]] == ["Albums", "Genres"]
        assert (await client.post("/menus/act", json={"handle": "nope", "action": "play"})).status == 404
        assert (await client.post("/menus/act", json={"handle": "nope", "action": "delete"})).status == 404
        # The Lyrion client off takes Extended navigation with it.
        settings.values["lms_enabled"] = False
        assert (await (await client.get("/menus")).json())["on"] is False



@pytest.mark.asyncio
async def test_entries_say_what_they_are_and_a_menu_says_it_is_one():
    """2026-10-05, George on the screenshots: My Music and Genres in grey.
    The panel draws them by kind; the core says the kind from Lyrion's own
    parameters, and My Music's entries carry their ids."""
    m = menus()
    tiles = {t["key"]: t for t in await m.tiles()}
    page = await m.browse(tiles["mymusic"]["handle"])
    assert page["node"] == "myMusic"
    assert [r["id"] for r in page["items"]] == ["myMusicAlbums", "myMusicGenres"]
    genres = await m.browse(page["items"][1]["handle"])
    assert genres  # the fake answers nothing for browselibrary; the hint is read from params:
    from gexis_core.menus import _hint
    assert _hint({"commonParams": {"genre_id": "601"}}, {}) == "genre"
    assert _hint({"params": {"year": "1987"}}, {}) == "year"
    assert _hint({"text": "Qobuz"}, {}) is None
    assert _hint({"commonParams": {"genre_id": "601", "album_id": "9"}}, {}) == "album"
    # As George's server sends a genre: its own id, a role beside it.
    assert _hint({"commonParams": {"genre_id": "601"}}, {"params": {"role_id": "1,5", "genre_id": "601"}}) == "genre"
    assert _hint({"type": "redirect", "text": "Qobuz"}, {}) == "app"
