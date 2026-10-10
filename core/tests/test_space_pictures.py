"""ADR-0133: Space pictures downloaded from NASA and ESA - only what is
NASA's alone or ESA's own, kept on the device, refreshed in the background."""
from __future__ import annotations

import asyncio
import json
import random

from gexis_core import space_pictures as sp

JPEG = b"\xff\xd8" + b"x" * 100

FEED = """<rss><channel>
<item><title>Galaxies in a cosmic house of mirrors</title><link>https://esawebb.org/images/potm2609a/</link></item>
<item><title>A NASA-led release, mirrored</title><link>https://esawebb.org/images/weic9999a/</link></item>
</channel></rss>"""
PAGES = {
    "https://esawebb.org/images/potm2609a/": "<h1>Galaxies</h1><p>Credit:</p><p>ESA/Webb, NASA &amp; CSA, J. Lee</p><p>About the Image</p>",
    "https://esawebb.org/images/weic9999a/": "<p>Credit: NASA, ESA, CSA, STScI</p><p>About the Image</p>",
}


def nasa_item(nid, center="JSC", width=4000, height=2600, description="", title="Earth", photographer=""):
    return {"data": [{"nasa_id": nid, "center": center, "title": title, "description": description,
                      "photographer": photographer, "keywords": []}],
            "links": [{"href": f"https://images-assets.nasa.gov/image/{nid}/{nid}~large.jpg"},
                      {"href": f"https://images-assets.nasa.gov/image/{nid}/{nid}~orig.jpg", "width": width, "height": height}]}


NASA = {"collection": {"items": [
    nasa_item("iss071e001"),                                                       # kept
    nasa_item("iss071e002", description="Credit: NASA/ESA - Alexander Gerst"),     # a partner
    nasa_item("PIA0001", center="JPL", title="Hubble view"),                       # partner mission, no credit
    nasa_item("PIA0002", center="JPL", title="Hubble view of a nebula", description="Image credit: NASA/JPL"),  # credited NASA
    nasa_item("iss071e003", width=1200, height=800),                               # too small
    nasa_item("iss071e004", width=2000, height=3000),                              # portrait
    nasa_item("eso1234", center="ESO"),                                            # not a NASA centre
    nasa_item("GSFC_2024", center="GSFC", title="Former VP Al Gore at NASA Goddard"),   # people, not a scene
    nasa_item("iss071e005", title="ISS hardware close-up"),                        # not a scene
]}}


class Response:
    def __init__(self, status, body):
        self.status, self._body = status, body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    @property
    def content(self):
        body = self._body

        class Reader:
            """As aiohttp's: the body arrives in pieces."""
            async def read(self, n=-1):
                return body[:min(n, 10)] if n > 0 else body[:10]

            async def iter_chunked(self, size):
                for start in range(0, len(body), 7):
                    yield body[start:start + 7]
        return Reader()


class Web:
    """The internet these sources live on; `down` turns it off."""

    def __init__(self):
        self.down = False
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(url)
        if self.down:
            raise sp.aiohttp.ClientConnectionError("no network")
        if url.endswith("/feed/"):
            return Response(200, (FEED if "esawebb" in url else "<rss></rss>").encode())
        if url in PAGES:
            return Response(200, PAGES[url].encode())
        if url == sp.NASA_API:
            return Response(200, json.dumps(NASA).encode())
        if url.endswith(".jpg"):
            return Response(200, JPEG)
        return Response(404, b"")


def test_esa_keeps_only_its_own_releases():
    items = sp.esa_feed(FEED, "esawebb.org")
    assert [i["id"] for i in items] == ["esa-esawebb-potm2609a", "esa-esawebb-weic9999a"]
    assert items[0]["url"] == "https://cdn.esawebb.org/archives/images/wallpaper2/potm2609a.jpg"
    assert sp.esa_credit(PAGES["https://esawebb.org/images/potm2609a/"]) == "ESA/Webb, NASA & CSA, J. Lee"
    assert sp.esa_credit(PAGES["https://esawebb.org/images/weic9999a/"]).startswith("NASA")


def test_nasa_keeps_only_what_is_nasas_alone():
    kept = {i["id"] for i in sp.nasa_items(NASA)}
    assert kept == {"nasa-iss071e001", "nasa-PIA0002"}


async def _ready(walls):
    task = walls.refresh_soon()
    if task:
        await task


async def test_pictures_arrive_with_their_credit_and_are_served_by_name(tmp_path):
    web = Web()
    walls = sp.SpacePictures(web, tmp_path, rng=random.Random(3))
    await _ready(walls)
    seen = {}
    for _ in range(3):
        answer = await walls.next()
        seen[answer["file"]] = answer
    assert set(seen) == {"esa-esawebb-potm2609a.jpg", "nasa-iss071e001.jpg", "nasa-PIA0002.jpg"}
    esa = seen["esa-esawebb-potm2609a.jpg"]
    assert esa["by"] is None and esa["credit"] == "ESA/Webb, NASA & CSA, J. Lee · CC BY 4.0"
    nasa = seen["nasa-iss071e001.jpg"]
    assert nasa["credit"] == "Public domain" and nasa["by"] == "NASA (JSC)"
    assert walls.path_of("nasa-iss071e001.jpg").read_bytes() == JPEG   # whole, not the first piece
    assert walls.path_of("../state.json") is None and walls.path_of("other.jpg") is None


async def test_the_first_request_does_not_wait_for_the_sources(tmp_path):
    """The built-in set shows while the first refresh runs."""
    walls = sp.SpacePictures(Web(), tmp_path)
    assert await walls.next() is None          # nothing yet: the caller shows the built-in set
    await walls.refresh_soon() or asyncio.sleep(0)


async def test_offline_it_shows_what_it_kept_and_asks_again_only_after_an_hour(tmp_path):
    web = Web()
    now = [1000.0]
    walls = sp.SpacePictures(web, tmp_path, rng=random.Random(1), clock=lambda: now[0])
    await _ready(walls)
    first = await walls.next()
    web.down = True
    now[0] += sp.DAY_S + 1                       # due again, and the network is gone
    await _ready(walls)
    calls = len(web.calls)
    assert (await walls.next())["file"].endswith(".jpg")   # what is on the device
    assert walls.refresh_soon() is None or walls.refresh_soon().done()
    now[0] += 60
    walls.refresh_soon()
    assert len(web.calls) == calls             # not asked again within the hour
    assert first["file"]


async def test_only_the_newest_are_kept(tmp_path):
    web = Web()
    now = [0.0]

    def clock():
        now[0] += 1
        return now[0]
    walls = sp.SpacePictures(web, tmp_path, keep=2, rng=random.Random(2), clock=clock)
    await _ready(walls)
    for _ in range(3):
        await walls.next()
    assert len(list(tmp_path.glob("*.jpg"))) == 2
