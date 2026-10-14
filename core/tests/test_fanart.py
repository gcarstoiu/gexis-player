"""ADR-0112: the artist's photos for the visualiser's fanart frame."""
from __future__ import annotations

import asyncio

from gexis_core import fanart as fa
from gexis_core.fanart import Fanart, first_artist, proxied

BASE = "http://lms:9000"


class FakeLms:
    def __init__(self, artists, photos):
        self.artists, self.photos, self.calls = artists, photos, []

    async def rpc(self, command, timeout=None):
        self.calls.append(command)
        if command[0] == "artists":
            name = command[3].removeprefix("search:").lower()
            return {"artists_loop": [{"artist": a, "id": i} for a, i in self.artists.items() if name in a.lower()]}
        artist_id = int(command[2].removeprefix("artist_id:"))
        return {"item_loop": [{"url": u} for u in self.photos.get(artist_id, [])]}


async def download(url):
    return b"jpeg:" + url.encode()


def run(coro):
    return asyncio.run(coro)


def test_a_collaboration_s_first_artist():
    assert first_artist("Snoop Dogg feat. Mystikal") == "Snoop Dogg"
    assert first_artist("Laura Pausini & Andrea Bocelli") == "Laura Pausini"
    assert first_artist("R. Greenawalt/D.Child/Steve Vai") == "R. Greenawalt"
    assert first_artist("Nick Cave") is None


def test_photos_go_through_lms_s_own_proxy():
    assert proxied(BASE, "https://i.discogs.com/x.jpeg") == f"{BASE}/imageproxy/https://i.discogs.com/x.jpeg/image_1280x1280_o.jpg"
    assert proxied(BASE, "imageproxy/mai/localartwork/abc/image.png") == f"{BASE}/imageproxy/mai/localartwork/abc/image_1280x1280_o.jpg"


def test_an_exact_name_or_else_the_first_artist_of_a_collaboration():
    """George, "B" and "Agree": a name matching nothing gets nothing; a
    collaboration that is no artist of its own gets its first artist's."""
    lms = FakeLms({"Simon & Garfunkel": 1, "Snoop Dogg": 2, "Snoop Dogg & Friends Band": 3}, {})
    f = Fanart(lms.rpc, download, BASE)
    assert run(f.artist_id("simon & garfunkel")) == 1, "a duo that is an artist of its own stays whole"
    assert run(f.artist_id("Snoop Dogg feat. Mystikal")) == 2
    assert run(f.artist_id("Snoopy")) is None, "a part of a name is not a match"


def test_photos_are_kept_at_most_ten_and_asked_once(tmp_path):
    lms = FakeLms({}, {7: [f"https://x/{n}.jpg" for n in range(14)]})
    f = Fanart(lms.rpc, download, BASE, directory=tmp_path)
    first = run(f.photos(7))
    assert len(first) == fa.PER_ARTIST and first[0].read_bytes().startswith(b"jpeg:")
    asked = len(lms.calls)
    assert run(f.photos(7)) == first and len(lms.calls) == asked, "on disk: not asked again"


def test_an_artist_with_none_is_remembered_as_none(tmp_path):
    lms = FakeLms({}, {})
    f = Fanart(lms.rpc, download, BASE, directory=tmp_path)
    assert run(f.photos(8)) == [] and run(f.photos(8)) == []
    assert len(lms.calls) == 1
    assert run(f.photos(None)) == []


def test_the_cache_keeps_the_most_recent_artists(tmp_path, monkeypatch):
    import os
    import time

    lms = FakeLms({}, {n: ["https://x/1.jpg"] for n in range(4)})
    f = Fanart(lms.rpc, download, BASE, directory=tmp_path)
    for n in range(4):
        run(f.photos(n))
        os.utime(tmp_path / str(n), (time.time() - 100 + n, time.time() - 100 + n))
    monkeypatch.setattr(fa, "ARTISTS_KEPT", 2)
    f._trim()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["2", "3"]


def test_lms_away_means_no_photos_not_a_failure(tmp_path):
    async def broken(command, timeout=None):
        raise ConnectionError("down")
    f = Fanart(broken, download, BASE, directory=tmp_path)
    assert run(f.artist_id("Anyone")) is None
    assert run(f.photos(3)) == []


def test_a_collaboration_lms_lists_as_its_own_artist_falls_back_to_the_first(tmp_path):
    """Found on George's server: "Snoop Dogg feat. Mystikal" is an LMS artist
    with no photos of its own."""
    lms = FakeLms({"Snoop Dogg feat. Mystikal": 12, "Snoop Dogg": 2}, {2: ["https://x/s.jpg"]})
    f = Fanart(lms.rpc, download, BASE, directory=tmp_path)
    assert len(run(f.for_artist("Snoop Dogg feat. Mystikal"))) == 1
    assert len(run(f.for_artist("Snoop Dogg feat. Mystikal", artist_id=12))) == 1, "by LMS id too"
    assert run(f.for_artist("Nick Cave")) == []


def test_lms_away_or_the_plugin_not_there_yet_is_not_remembered_as_no_photos(tmp_path):
    """Review, 2026-10-12: on a fresh player the plugin is installed only
    after Lyrion restarts; every artist played before then kept an empty
    `.done` for good, and a failed name lookup was kept as "no artist"."""
    lms = FakeLms({"Example Artist": 7}, {7: ["https://x/1.jpg"]})
    down = True

    async def rpc(command, timeout=None):
        if down:
            raise ConnectionError("Lyrion restarting")
        return await lms.rpc(command, timeout)
    f = Fanart(rpc, download, BASE, directory=tmp_path)
    assert run(f.for_artist("Example Artist")) == []
    assert run(f.photos(7)) == []
    assert not (tmp_path / "7" / ".done").exists()
    down = False
    assert len(run(f.for_artist("Example Artist"))) == 1, "asked again once LMS answers"
    assert len(run(Fanart(rpc, download, BASE, directory=tmp_path).photos(7))) == 1, "and after a restart"


def test_photos_named_but_none_downloaded_are_asked_for_again(tmp_path):
    lms = FakeLms({}, {7: ["https://x/1.jpg", "https://x/2.jpg"]})
    offline = True

    async def fetch(url):
        return None if offline else b"jpeg"
    f = Fanart(lms.rpc, fetch, BASE, directory=tmp_path)
    assert run(f.photos(7)) == [] and not (tmp_path / "7" / ".done").exists()
    offline = False
    assert len(run(f.photos(7))) == 2


def test_a_no_photos_answer_is_asked_again_after_thirty_days(tmp_path):
    """George, 2026-10-12 (answer 7): an artist found with no photos is asked
    again once the answer is a month old - which also clears the empty
    answers players kept from before LMS-away stopped being one."""
    import os
    import time

    lms = FakeLms({}, {})
    f = Fanart(lms.rpc, download, BASE, directory=tmp_path)
    assert run(f.photos(8)) == []
    marker = tmp_path / "8" / ".done"
    young = time.time() - fa.EMPTY_RECHECK_S + 3600
    os.utime(marker, (young, young))
    assert run(f.photos(8)) == [] and len(lms.calls) == 1, "younger than 30 days: believed"
    lms.photos[8] = ["https://x/1.jpg"]
    old = time.time() - fa.EMPTY_RECHECK_S - 3600
    os.utime(marker, (old, old))
    assert len(run(f.photos(8))) == 1 and len(lms.calls) == 2, "older: asked again"


def test_an_answer_with_photos_is_not_asked_again_however_old(tmp_path):
    import os
    import time

    lms = FakeLms({}, {7: ["https://x/1.jpg"]})
    f = Fanart(lms.rpc, download, BASE, directory=tmp_path)
    assert len(run(f.photos(7))) == 1
    old = time.time() - 10 * fa.EMPTY_RECHECK_S
    os.utime(tmp_path / "7" / ".done", (old, old))
    assert len(run(f.photos(7))) == 1 and len(lms.calls) == 1


def test_a_rescan_that_renumbers_an_artist_drops_its_photos(tmp_path):
    """Finding 125 #22 (2026-10-14): the photos on disk are kept by LMS
    artist id, and nothing dropped them when a rescan gave the id to someone
    else, or another server numbered its own - the frame showed A's photos
    during B's tracks. They now go when the artist photos' do, by the same
    names check (`LmsArtistInfo.on_renumber`)."""
    from pathlib import Path

    from gexis_core.artistinfo import SCOPE_CHECK_S, LmsArtistInfo
    from gexis_core.enrichment import Cache

    names = {"123": "Artist A", "9": "Artist C"}
    photos = {123: ["https://x/a.jpg"], 9: ["https://x/c.jpg"]}
    server = {"lastscan": "1700000000"}
    calls = []
    now = [100.0]

    async def rpc(command, timeout=None, player=""):
        calls.append(command)
        if command[0] == "serverstatus":
            return dict(server)
        if command[0] == "artists" and len(command) > 3:
            wanted = command[3].removeprefix("search:").lower()
            return {"artists_loop": [{"artist": n, "id": int(i)} for i, n in names.items() if n.lower() == wanted]}
        if command[0] == "artists":
            return {"artists_loop": [{"artist": n, "id": int(i)} for i, n in names.items()]}
        artist_id = int(command[2].removeprefix("artist_id:"))
        return {"item_loop": [{"url": u} for u in photos.get(artist_id, [])]}

    async def scenario():
        info = LmsArtistInfo(rpc, BASE, store=Cache(Path(":memory:")), clock=lambda: now[0])
        f = Fanart(rpc, download, BASE, directory=tmp_path, before=info.check_scope)
        info.on_renumber(f.drop)
        assert b"a.jpg" in (await f.for_artist("Artist A", 123))[0].read_bytes()
        assert b"c.jpg" in (await f.for_artist("Artist C"))[0].read_bytes()
        server["lastscan"] = "1800000000"           # 123 is someone else now
        names["123"] = "Artist B"
        photos[123] = ["https://x/b.jpg"]
        now[0] += SCOPE_CHECK_S
        assert b"b.jpg" in (await f.for_artist("Artist B", 123))[0].read_bytes()
        asked = len(calls)
        assert b"c.jpg" in (await f.for_artist("Artist C"))[0].read_bytes()
        assert not [c for c in calls[asked:] if c[0] != "serverstatus"], "C unchanged: kept, name and photos"
        other = LmsArtistInfo(rpc, "http://server-b:9000", store=info._store, clock=lambda: now[0])
        other.on_renumber(f.drop)
        await other.check_scope()                   # another server: everything goes
        assert not [p for p in tmp_path.iterdir() if p.is_dir()]

    run(scenario())
