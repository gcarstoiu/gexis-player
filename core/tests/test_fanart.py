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
