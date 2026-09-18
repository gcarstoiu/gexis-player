"""Phase 7 step 3: library reads (ADR-0038 §1, §5-7).

The LMS replies here are made up (George, 2026-09-17: no library data from
George's server in this public repository). Their *shape* follows what Finding
029 recorded against LMS 9.1.1: which loop each list arrives in, which
fields are strings, that library playlists are `file:` URLs and plugin
ones are not, that `release_type` comes as LMS's combined values.
"""
from __future__ import annotations

import pytest
from aiohttp.test_utils import TestClient, TestServer

from gexis_core import library as library_module
from gexis_core.library import LibraryUnavailable, LmsLibrary, NoPlayer, NotFound
from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

BASE = "http://lms.test:9000"

ALBUMS = [
    {"id": 101, "album": "First Light", "artist": "Aria Nova", "artist_id": 7, "year": 2019,
     "artwork_track_id": "a1b2c3d4", "release_type": "ALBUM"},
    {"id": 102, "album": "Live at the Harbour", "artist": "Aria Nova", "artist_id": 7, "year": 0,
     "release_type": "ALBUM LIVE"},
    {"id": 103, "album": "Second Light", "artist": "Aria Nova", "artist_id": 7, "year": 2024,
     "release_type": "EP"},
]
ARTISTS = [
    {"id": 1, "artist": "4 Winds", "textkey": "4"},
    {"id": 7, "artist": "Aria Nova", "textkey": "N"},
    {"id": 9, "artist": "Çelik Band", "textkey": "Ç"},
    {"id": 11, "artist": "Íñigo Vega", "textkey": "Í"},
]
TRACKS = [
    {"id": 5001, "title": "Opening", "tracknum": "1", "disc": "1", "duration": 201.5,
     "artist": "Aria Nova", "coverid": "a1b2c3d4", "url": "file:///music/opening.flac"},
    {"id": 5002, "title": "Closing", "tracknum": "2", "duration": "180", "artist": "Aria Nova",
     "url": "file:///music/closing.flac"},
]
PLAYLISTS = [
    {"id": 900, "playlist": "Sunday", "url": "file:///playlist/Sunday.m3u"},
    {"id": 901, "playlist": "Streaming Mix", "url": "qobuz://123.qbz"},
    {"id": 902, "playlist": "Empty", "url": "file:///playlist/Empty.m3u"},
]


class FakeLms:
    """Answers `LmsLibrary._rpc` from the made-up data and records every
    command, so a test can tell a cached read from a fresh one."""

    def __init__(self):
        self.commands = []
        self.players = []
        self.lastscan = "1700000000"
        self.rescan = False
        self.unreachable = False
        self.control_count = 12

    async def __call__(self, command, player=""):
        self.commands.append(list(command))
        self.players.append(player)
        if self.unreachable:
            raise LibraryUnavailable("connection refused")
        what = command[0]
        args = [str(c) for c in command]
        if what == "playlistcontrol":
            return {"count": self.control_count} if self.control_count else {}
        if what == "serverstatus":
            return {"rescan": 1} if self.rescan else {"lastscan": self.lastscan}
        if what == "albums":
            if any(a.startswith("album_id:") for a in args):
                wanted = int(next(a for a in args if a.startswith("album_id:")).split(":")[1])
                loop = [a for a in ALBUMS if a["id"] == wanted]
            else:
                loop = ALBUMS[: int(command[2])]
            return {"count": len(ALBUMS), "albums_loop": loop}
        if what == "artists":
            return {"count": len(ARTISTS), "artists_loop": ARTISTS[int(command[1]):int(command[1]) + int(command[2])]}
        if what == "titles":
            return {"count": len(TRACKS), "titles_loop": TRACKS}
        if what == "playlists" and command[1] == "edit":
            return {}
        if what == "playlist" and command[1] in ("shuffle", "index", "delete", "clear"):
            return {}
        if what == "playlists" and command[1] == "tracks":
            pid = int(next(a for a in args if a.startswith("playlist_id:")).split(":")[1])
            tracks = TRACKS if pid == 900 else []
            return {"count": len(tracks), "playlisttracks_loop": tracks[: int(command[3])]}
        if what == "playlists":
            return {"count": len(PLAYLISTS), "playlists_loop": PLAYLISTS}
        raise AssertionError(f"unexpected command {command}")

    def reads(self):
        return [c for c in self.commands if c[0] != "serverstatus"]


@pytest.fixture
def lms(monkeypatch):
    fake = FakeLms()
    monkeypatch.setattr(LmsLibrary, "_rpc", fake)
    return fake


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _lib(clock=None):
    return LmsLibrary(
        "lms.test", 9000, player_id=lambda: "aa:bb:cc:dd:ee:ff", clock=clock or Clock()
    )


# --- the reads -------------------------------------------------------------


@pytest.mark.asyncio
async def test_counts_are_album_artists_and_library_playlists_only(lms):
    counts = await _lib().counts()

    assert counts == {"albums": 3, "artists": 4, "playlists": 2}
    assert ["artists", 0, 1, "role_id:ALBUMARTIST"] in lms.commands


@pytest.mark.asyncio
async def test_new_music_asks_for_ten_newest_and_maps_artwork_as_o_jpg(lms):
    """Thumb-sized: the strip draws 176px cards, and ten 500px covers in
    them made it scroll unevenly on the panel (George, 2026-09-17)."""
    albums = await _lib().new_music()

    assert lms.reads()[0][:4] == ["albums", 0, library_module.NEW_MUSIC_COUNT, "sort:new"]
    assert albums[0] == {
        "id": 101,
        "title": "First Light",
        "artist": "Aria Nova",
        "artist_id": 7,
        "year": 2019,
        "release_type": "ALBUM",
        "artwork": f"{BASE}/music/a1b2c3d4/cover_200x200_o.jpg",
    }


@pytest.mark.asyncio
async def test_an_album_without_artwork_or_year_gets_none_for_both(lms):
    albums = await _lib().new_music()

    assert albums[1]["artwork"] is None
    assert albums[1]["year"] is None


@pytest.mark.asyncio
async def test_the_jump_rail_letter_folds_accents_and_digits(lms):
    """George, 2026-09-18: fold LMS's `Ç` and `Í` into C and I. The design's
    rail is `#` then A-Z, and LMS hands back an accented key for two artists
    on his server and a digit for each numeric name (Finding 029 §2). The
    order stays LMS's own (ADR-0038 §1a); only the rail letter is folded."""
    page = await _lib().artists()

    assert [a["letter"] for a in page["items"]] == ["#", "N", "C", "I"]
    assert page["count"] == 4
    assert "role_id:ALBUMARTIST" in lms.reads()[0]


@pytest.mark.asyncio
async def test_artists_page_passes_offset_and_limit(lms):
    page = await _lib().artists(offset=1, limit=1)

    assert page["offset"] == 1
    assert [a["name"] for a in page["items"]] == ["Aria Nova"]


@pytest.mark.asyncio
async def test_the_discography_is_newest_first_with_undated_albums_last(lms):
    """George, 2026-09-18: by year, newest on top. LMS returns them
    alphabetically; its release types are still taken as given."""
    albums = await _lib().artist_albums(7)

    assert [a["title"] for a in albums] == ["Second Light", "First Light", "Live at the Harbour"]
    assert [a["release_type"] for a in albums] == ["EP", "ALBUM", "ALBUM LIVE"]
    assert "artist_id:7" in lms.reads()[0]
    assert "role_id:ALBUMARTIST" in lms.reads()[0]


@pytest.mark.asyncio
async def test_album_carries_its_tracks_with_numbers_and_durations(lms):
    album = await _lib().album(101)

    assert album["title"] == "First Light"
    assert album["artwork"] == f"{BASE}/music/a1b2c3d4/cover_500x500_o.jpg"
    assert album["tracks"][0] == {
        "id": 5001,
        "title": "Opening",
        "artist": "Aria Nova",
        "tracknum": 1,
        "disc": 1,
        "duration": 201.5,
        # A row's thumbnail, not the page's cover.
        "artwork": f"{BASE}/music/a1b2c3d4/cover_200x200_o.jpg",
    }
    assert album["tracks"][1]["duration"] == 180.0
    assert album["tracks"][1]["disc"] is None
    assert "sort:tracknum" in lms.reads()[1]


@pytest.mark.asyncio
async def test_an_unknown_album_is_not_found(lms):
    with pytest.raises(NotFound):
        await _lib().album(999)


@pytest.mark.asyncio
async def test_playlists_are_library_ones_with_track_counts(lms):
    """George, 2026-09-17: LMS library playlists only, not a plugin's."""
    playlists = await _lib().playlists()

    assert playlists == [
        {"id": 900, "name": "Sunday", "tracks": 2},
        {"id": 902, "name": "Empty", "tracks": 0},
    ]


@pytest.mark.asyncio
async def test_a_plugin_playlist_cannot_be_opened_by_id(lms):
    with pytest.raises(NotFound):
        await _lib().playlist(901)


@pytest.mark.asyncio
async def test_a_playlist_page_has_its_tracks(lms):
    page = await _lib().playlist(900, offset=0, limit=1)

    assert page["name"] == "Sunday"
    assert page["count"] == 2
    assert [t["title"] for t in page["items"]] == ["Opening"]


# --- the cache -------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_second_read_comes_from_the_cache(lms):
    lib = _lib()
    await lib.album(101)
    before = len(lms.reads())

    await lib.album(101)

    assert len(lms.reads()) == before


@pytest.mark.asyncio
async def test_lastscan_is_not_asked_again_within_the_check_interval(lms):
    clock = Clock()
    lib = _lib(clock)
    await lib.new_music()
    clock.now += library_module.LASTSCAN_CHECK_S - 1

    await lib.new_music()

    assert [c[0] for c in lms.commands].count("serverstatus") == 1


@pytest.mark.asyncio
async def test_a_rescan_drops_the_cache(lms):
    """A full rescan renumbers every id (Finding 029 §4)."""
    clock = Clock()
    lib = _lib(clock)
    await lib.album(101)
    lms.lastscan = "1700009999"
    clock.now += library_module.LASTSCAN_CHECK_S
    before = len(lms.reads())

    await lib.album(101)

    assert len(lms.reads()) > before


@pytest.mark.asyncio
async def test_nothing_is_cached_while_a_scan_runs(lms):
    lms.rescan = True
    clock = Clock()
    lib = _lib(clock)
    await lib.new_music()
    clock.now += library_module.LASTSCAN_CHECK_S
    before = len(lms.reads())

    await lib.new_music()

    assert len(lms.reads()) > before


@pytest.mark.asyncio
async def test_playlists_are_never_cached(lms):
    """They change from any LMS app without a scan."""
    lib = _lib()
    await lib.playlists()
    before = len(lms.reads())

    await lib.playlists()

    assert len(lms.reads()) > before


# --- actions ---------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind, item_id, action, expected",
    [
        ("album", 101, "play", ["playlistcontrol", "cmd:load", "album_id:101"]),
        ("artist", 7, "play", ["playlistcontrol", "cmd:load", "artist_id:7"]),
        ("track", 5001, "play", ["playlistcontrol", "cmd:load", "track_id:5001"]),
        ("playlist", 900, "play", ["playlistcontrol", "cmd:load", "playlist_id:900"]),
        ("album", 101, "add", ["playlistcontrol", "cmd:add", "album_id:101"]),
    ],
)
async def test_each_kind_and_action_sends_one_playlistcontrol(lms, kind, item_id, action, expected):
    """Finding 029 §7 measured all of these on the real player."""
    result = await _lib().act(kind, item_id, action)

    assert lms.commands[-1] == expected
    assert result == {"tracks": 12}


@pytest.mark.asyncio
async def test_play_turns_shuffle_off_first(lms):
    """George, 2026-09-18: Play means in order. With LMS's shuffle on, a
    freshly loaded album starts at a random track and an artist mid-album."""
    await _lib().act("album", 101, "play")

    assert lms.commands[-2:] == [
        ["playlist", "shuffle", 0],
        ["playlistcontrol", "cmd:load", "album_id:101"],
    ]


@pytest.mark.asyncio
async def test_shuffle_turns_it_on_and_loads(lms):
    """The design's Shuffle all: the same load, with LMS's shuffle the other
    way round (George, 2026-09-18)."""
    await _lib().act("playlist", 900, "shuffle")

    assert lms.commands[-2:] == [
        ["playlist", "shuffle", 1],
        ["playlistcontrol", "cmd:load", "playlist_id:900"],
    ]


@pytest.mark.asyncio
async def test_adding_to_the_queue_leaves_shuffle_alone(lms):
    """Adding does not start anything, so it has no business changing how
    the player is set."""
    await _lib().act("album", 101, "add")

    assert not [c for c in lms.commands if c[:2] == ["playlist", "shuffle"]]


@pytest.mark.asyncio
async def test_an_action_goes_to_the_adapter_s_player(lms):
    """The library plays on the player the renderer adapter arbitrates for,
    never one named here."""
    await _lib().act("album", 101, "play")

    assert lms.players[-1] == "aa:bb:cc:dd:ee:ff"


@pytest.mark.asyncio
async def test_an_unknown_kind_or_action_is_not_found(lms):
    for kind, action in (("genre", "play"), ("album", "delete")):
        with pytest.raises(NotFound):
            await _lib().act(kind, 1, action)
    assert not [c for c in lms.commands if c[0] == "playlistcontrol"]


@pytest.mark.asyncio
async def test_an_id_lms_acts_on_nothing_for_is_not_found(lms):
    """LMS answers an unknown id with no count rather than an error."""
    lms.control_count = 0

    with pytest.raises(NotFound):
        await _lib().act("album", 999, "play")


@pytest.mark.asyncio
async def test_nothing_is_sent_before_the_player_is_resolved():
    """The adapter resolves the player from its name at startup; until then
    there is nothing to play on."""
    library = LmsLibrary("lms.test", 9000, player_id=lambda: None, clock=Clock())

    with pytest.raises(NoPlayer):
        await library.act("album", 101, "play")


# --- the routes ------------------------------------------------------------


async def _get(path, library):
    server = StateServer(StateStore({}), library=library)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.get(path)
        return resp.status, await resp.json()


async def _post(path, library, body):
    server = StateServer(StateStore({}), library=library)
    async with TestClient(TestServer(server.make_app())) as client:
        resp = await client.post(path, json=body)
        return resp.status, await resp.json()


@pytest.mark.asyncio
async def test_routes_answer_503_when_the_library_is_not_wired():
    status, body = await _get("/library/counts", None)

    assert status == 503


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path, expect",
    [
        ("/library/counts", lambda b: b["albums"] == 3),
        ("/library/new", lambda b: b[0]["id"] == 101),
        ("/library/artists?offset=2&limit=5", lambda b: b["offset"] == 2 and b["items"][0]["id"] == 9),
        ("/library/artists/7/albums", lambda b: len(b) == 3),
        ("/library/albums/101", lambda b: len(b["tracks"]) == 2),
        ("/library/playlists", lambda b: len(b) == 2),
        ("/library/playlists/900", lambda b: b["name"] == "Sunday"),
    ],
)
async def test_each_read_has_a_route(lms, path, expect):
    status, body = await _get(path, _lib())

    assert status == 200
    assert expect(body)


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/library/radio", "/library/albums", "/library/albums/101/tracks"])
async def test_an_unknown_read_is_404(lms, path):
    status, _ = await _get(path, _lib())

    assert status == 404


@pytest.mark.asyncio
async def test_a_missing_album_is_404(lms):
    status, body = await _get("/library/albums/999", _lib())

    assert status == 404
    assert "not found" in body["error"]


@pytest.mark.asyncio
async def test_a_non_numeric_id_is_400(lms):
    status, _ = await _get("/library/albums/abc", _lib())

    assert status == 400


@pytest.mark.asyncio
async def test_lms_unreachable_is_502(lms):
    lms.unreachable = True

    status, body = await _get("/library/new", _lib())

    assert status == 502
    assert "LMS unreachable" in body["error"]


@pytest.mark.asyncio
async def test_the_action_route_answers_503_when_the_library_is_not_wired():
    status, _ = await _post("/library/action", None, {"kind": "album", "id": 1})

    assert status == 503


@pytest.mark.asyncio
async def test_the_action_route_plays_an_album(lms):
    status, body = await _post("/library/action", _lib(), {"kind": "album", "id": 101, "action": "play"})

    assert status == 200
    assert body == {"tracks": 12}
    assert lms.commands[-1] == ["playlistcontrol", "cmd:load", "album_id:101"]


@pytest.mark.asyncio
async def test_the_action_route_defaults_to_playing(lms):
    status, _ = await _post("/library/action", _lib(), {"kind": "album", "id": 101})

    assert status == 200
    assert lms.commands[-1][1] == "cmd:load"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body", [{"kind": "album"}, {"id": 1}, {"kind": "album", "id": "abc"}, {}]
)
async def test_a_malformed_action_is_400(lms, body):
    status, _ = await _post("/library/action", _lib(), body)

    assert status == 400


@pytest.mark.asyncio
async def test_an_unknown_kind_is_404(lms):
    status, _ = await _post("/library/action", _lib(), {"kind": "genre", "id": 1})

    assert status == 404


@pytest.mark.asyncio
async def test_no_player_yet_is_409(lms):
    library = LmsLibrary("lms.test", 9000, player_id=lambda: None, clock=Clock())

    status, body = await _post("/library/action", library, {"kind": "album", "id": 101})

    assert status == 409
    assert "player" in body["error"]


@pytest.mark.asyncio
async def test_lms_unreachable_on_an_action_is_502(lms):
    lms.unreachable = True

    status, _ = await _post("/library/action", _lib(), {"kind": "album", "id": 101})

    assert status == 502


# --- adding to a playlist --------------------------------------------------


@pytest.mark.asyncio
async def test_an_album_is_added_to_a_playlist_one_track_at_a_time(lms):
    """LMS has no command that adds a whole album: `playlists edit cmd:add`
    takes one url, and ignores album_id without an error (Finding 029 §3)."""
    result = await _lib().act("album", 101, "playlist", playlist_id=900)

    added = [c for c in lms.commands if c[:3] == ["playlists", "edit", "cmd:add"]]
    assert [c[-1] for c in added] == [
        "url:file:///music/opening.flac",
        "url:file:///music/closing.flac",
    ]
    assert all(c[3] == "playlist_id:900" for c in added)
    assert result == {"tracks": 2}


@pytest.mark.asyncio
async def test_an_albums_tracks_are_added_in_track_order(lms):
    await _lib().act("album", 101, "playlist", playlist_id=900)

    query = next(c for c in lms.commands if c[0] == "titles")
    assert "sort:tracknum" in query
    assert "album_id:101" in query


@pytest.mark.asyncio
async def test_a_plugin_playlist_cannot_be_added_to(lms):
    """Only the LMS library's own playlists are ours to write to
    (ADR-0038 §1); 901 is a Qobuz one."""
    with pytest.raises(NotFound):
        await _lib().act("track", 5001, "playlist", playlist_id=901)

    assert not [c for c in lms.commands if c[:2] == ["playlists", "edit"]]


@pytest.mark.asyncio
async def test_adding_without_naming_a_playlist_is_not_found(lms):
    with pytest.raises(NotFound):
        await _lib().act("album", 101, "playlist")


@pytest.mark.asyncio
async def test_the_action_route_adds_to_a_playlist(lms):
    status, body = await _post(
        "/library/action",
        _lib(),
        {"kind": "album", "id": 101, "action": "playlist", "playlist_id": 900},
    )

    assert status == 200
    assert body == {"tracks": 2}


# --- the queue rail --------------------------------------------------------


@pytest.mark.asyncio
async def test_the_rail_jumps_to_a_position(lms):
    """The rail addresses the queue by position, which is what LMS's own
    commands take and what the rail shows."""
    result = await _lib().act("queue", 4, "play")

    assert lms.commands[-1] == ["playlist", "index", 4]
    assert result == {"index": 4}


@pytest.mark.asyncio
async def test_the_rail_removes_a_position(lms):
    await _lib().act("queue", 2, "remove")

    assert lms.commands[-1] == ["playlist", "delete", 2]


@pytest.mark.asyncio
async def test_the_rail_clears_the_whole_queue(lms):
    """The design's Clear button. It empties the queue where the rows act on
    one track each, so it is the one queue action that carries no position -
    `playlist clear 0` would be a different command."""
    await _lib().act("queue", 0, "clear")

    assert lms.commands[-1] == ["playlist", "clear"]


@pytest.mark.asyncio
async def test_an_unknown_queue_action_is_not_found(lms):
    with pytest.raises(NotFound):
        await _lib().act("queue", 1, "shuffle")
