"""Phase 8 step 3: LMS's own artist information (ADR-0040 §1).

The replies here are the shapes Finding 035 recorded against George's LMS
9.1.1 with the Music & Artist Information plugin: a `url` when it has a
photo, `{"error": "I'm sorry, didn't find any relevant information."}` when
it does not, and a dropped connection when the plugin is not installed at
all.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gexis_core.artistinfo import PHOTO_LARGE, PHOTO_THUMB, RECHECK_S, LmsArtistInfo

BASE = "http://192.168.178.188:9000"
NOTHING = {"error": "I'm sorry, didn't find any relevant information."}


class FakeLms:
    """Answers by artist id, and records what was asked."""

    def __init__(self, photos=None, biographies=None, absent=False):
        self._photos = photos or {}
        self._biographies = biographies or {}
        self.absent = absent
        self.commands = []
        self.timeouts = []

    async def __call__(self, command, player="", timeout=None):
        self.commands.append(list(command))
        self.timeouts.append(timeout)
        if self.absent:
            # LMS closes the socket on an unknown command rather than
            # answering an error (measured 2026-09-18).
            raise ConnectionResetError("Server disconnected")
        artist_id = int(next(c for c in command if str(c).startswith("artist_id:")).split(":")[1])
        if command[1] == "artistphoto":
            url = self._photos.get(artist_id)
            return {"artist_id": str(artist_id), "url": url} if url else dict(NOTHING)
        bio = self._biographies.get(artist_id)
        return {"artist_id": str(artist_id), "biography": bio} if bio else dict(NOTHING)


class FakeClock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


def _info(lms=None, **kwargs):
    return LmsArtistInfo(lms or FakeLms(), BASE, **kwargs)


# --- photos ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_photo_is_asked_for_at_the_size_the_panel_draws():
    """The plugin's own `url` is the unsized PNG - 93,939 bytes against
    17,999 for the same picture as a 200px JPEG (Finding 035)."""
    lms = FakeLms(photos={7452: "imageproxy/mai/artist/7452/image.png"})

    photos = await _info(lms).photos([7452])

    assert photos == {7452: f"{BASE}/imageproxy/mai/artist/7452/image_200x200_o.jpg"}


@pytest.mark.asyncio
async def test_the_artist_page_asks_for_a_larger_photo_than_the_grid():
    """A 132px card and a 262px disc, on ADR-0038 §7's ladder."""
    lms = FakeLms(photos={7452: "imageproxy/mai/artist/7452/image.png"})
    info = _info(lms)

    thumb = await info.photos([7452], PHOTO_THUMB)
    large = await info.photos([7452], PHOTO_LARGE)

    assert thumb[7452].endswith("image_200x200_o.jpg")
    assert large[7452].endswith("image_300x300_o.jpg")


@pytest.mark.asyncio
async def test_an_artist_with_no_photo_is_none_not_a_placeholder():
    """The trap this module exists for: `/music/artist_<id>/cover` answers
    200 with LMS's generic placeholder for every artist, including ones that
    do not exist. The plugin says no instead, and that is what is stored."""
    photos = await _info(FakeLms(photos={})).photos([7452])

    assert photos == {7452: None}


@pytest.mark.asyncio
async def test_a_second_ask_costs_nothing():
    lms = FakeLms(photos={7452: "imageproxy/mai/artist/7452/image.png"})
    info = _info(lms)

    await info.photos([7452, 7453])
    await info.photos([7452, 7453])

    assert len(lms.commands) == 2


@pytest.mark.asyncio
async def test_a_grid_of_artists_is_asked_for_in_one_go():
    """40 artists took 1,247 ms in series and 212 ms in parallel against
    George's server (Finding 035's addendum)."""
    lms = FakeLms(photos={i: f"imageproxy/mai/artist/{i}/image.png" for i in range(40)})

    photos = await _info(lms).photos(list(range(40)))

    assert len(photos) == 40 and all(photos.values())
    assert len(lms.commands) == 40


# --- a server without the plugin -------------------------------------------


@pytest.mark.asyncio
async def test_a_server_without_the_plugin_is_not_an_error():
    """ADR-0040 §1: the plugin is a bonus when present, never a requirement.
    The panel falls back to Phase 7's initials."""
    photos = await _info(FakeLms(absent=True)).photos([7452, 7453])

    assert photos == {7452: None, 7453: None}


@pytest.mark.asyncio
async def test_a_missing_plugin_is_not_asked_again_on_every_screen():
    """The first refusal stops the batch it is in as well as every batch
    after it - one artist is enough to learn the plugin is not there."""
    lms = FakeLms(absent=True)
    info = _info(lms)

    await info.photos([1, 2, 3])
    after_first_screen = len(lms.commands)
    await info.photos([4, 5, 6])

    assert after_first_screen == 1
    assert len(lms.commands) == after_first_screen


@pytest.mark.asyncio
async def test_a_dropped_connection_is_retried_because_it_may_be_a_restart():
    """A server that was restarting looks exactly like one without the
    plugin, so "absent" is a belief with an expiry."""
    clock = FakeClock()
    lms = FakeLms(absent=True)
    info = _info(lms, clock=clock)

    await info.photos([7452])
    lms.absent = False
    lms._photos = {7452: "imageproxy/mai/artist/7452/image.png"}
    clock.advance(RECHECK_S + 1)
    photos = await info.photos([7452])

    assert photos[7452].endswith("image_200x200_o.jpg")


@pytest.mark.asyncio
async def test_a_call_that_did_not_reach_the_plugin_is_not_remembered_as_no_photo():
    """The same distinction enrichment.py draws: a provider that could not be
    asked has not said there is nothing."""
    clock = FakeClock()
    lms = FakeLms(absent=True)
    info = _info(lms, clock=clock)

    await info.photos([7452])
    lms.absent = False
    lms._photos = {7452: "imageproxy/mai/artist/7452/image.png"}
    clock.advance(RECHECK_S + 1)

    assert (await info.photos([7452]))[7452] is not None


# --- biographies -----------------------------------------------------------


@pytest.mark.asyncio
async def test_a_biography_comes_back_as_text():
    lms = FakeLms(biographies={7452: "  2 Unlimited are a Belgian-Dutch dance act.  "})

    assert await _info(lms).biography(7452) == "2 Unlimited are a Belgian-Dutch dance act."


@pytest.mark.asyncio
async def test_no_biography_is_none():
    assert await _info(FakeLms()).biography(7452) is None


@pytest.mark.asyncio
async def test_a_rescan_drops_what_was_remembered():
    """A full rescan renumbers every artist id (Finding 029 §4), so a
    remembered photo may belong to a different artist afterwards."""
    lms = FakeLms(photos={7452: "imageproxy/mai/artist/7452/image.png"})
    info = _info(lms)
    await info.photos([7452])

    info.forget()
    await info.photos([7452])

    assert len(lms.commands) == 2


# --- the route -------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_route_answers_a_url_per_artist():
    from aiohttp.test_utils import TestClient, TestServer

    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    lms = FakeLms(photos={7452: "imageproxy/mai/artist/7452/image.png"})
    server = StateServer(StateStore({}), artistinfo=_info(lms))

    async with TestClient(TestServer(server.make_app())) as client:
        body = await (await client.get("/library/artist-photos?ids=7452,7453")).json()

    assert body == {"7452": f"{BASE}/imageproxy/mai/artist/7452/image_200x200_o.jpg",
                    "7453": None}


@pytest.mark.asyncio
async def test_the_route_is_503_when_artist_info_is_not_wired():
    from aiohttp.test_utils import TestClient, TestServer

    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    server = StateServer(StateStore({}))

    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.get("/library/artist-photos?ids=1")).status == 503


@pytest.mark.asyncio
async def test_the_route_refuses_a_size_the_panel_does_not_draw():
    """Otherwise the network-facing API is a way to make LMS resize an image
    to any dimensions somebody asks for (ADR-0028 binds 0.0.0.0)."""
    from aiohttp.test_utils import TestClient, TestServer

    from gexis_core.state import StateStore
    from gexis_core.wsserver import StateServer

    server = StateServer(StateStore({}), artistinfo=_info())

    async with TestClient(TestServer(server.make_app())) as client:
        assert (await client.get("/library/artist-photos?ids=1&size=4000")).status == 400
        assert (await client.get("/library/artist-photos?ids=nope")).status == 400


# --- slow is not missing ---------------------------------------------------


class SlowLms(FakeLms):
    """A plugin that goes to the network for an artist it has not seen. The
    library wraps the timeout in its own exception `from` the original, which
    is how this is told apart from a dropped connection."""

    async def __call__(self, command, player="", timeout=None):
        self.commands.append(list(command))
        try:
            raise TimeoutError()
        except TimeoutError as exc:
            from gexis_core.library import LibraryUnavailable
            raise LibraryUnavailable(str(exc)) from exc


@pytest.mark.asyncio
async def test_a_slow_plugin_is_not_mistaken_for_a_missing_one():
    """**The defect this test exists for.** An uncached artist costs the
    plugin 500-900 ms because it goes to the network; sixteen at once ran
    past the library's 10 s RPC timeout, and a timeout read as "no plugin
    here" turned photos off for ten minutes - on a server that has one
    (hardware, 2026-09-18)."""
    lms = SlowLms()
    info = _info(lms)

    await info.photos([1, 2, 3])
    await info.photos([4, 5, 6])

    # Every artist was still asked about: nothing was switched off.
    assert len(lms.commands) == 6


@pytest.mark.asyncio
async def test_a_timed_out_artist_is_asked_again_rather_than_remembered():
    lms = SlowLms()
    info = _info(lms)
    await info.photos([7452])

    assert (await info.photos([7452]))[7452] is None
    assert len(lms.commands) == 2


# --- kept between restarts -------------------------------------------------


def _store():
    from gexis_core.enrichment import Cache

    return Cache(Path(":memory:"))


@pytest.mark.asyncio
async def test_a_photo_survives_a_restart():
    """**The gap George asked about (2026-09-18).** Photo URLs were held in
    memory only, so the first scroll through 917 artists after a daemon
    restart paid LMS's uncached 500-900 ms per artist all over again."""
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        from gexis_core.enrichment import Cache

        path = Path(folder) / "enrichment.db"
        lms = FakeLms(photos={7452: "imageproxy/mai/artist/7452/image.png"})
        store = Cache(path)
        await LmsArtistInfo(lms, BASE, store=store).photos([7452])
        store.close()

        restarted = FakeLms()  # the plugin would answer "nothing" now
        photos = await LmsArtistInfo(restarted, BASE, store=Cache(path)).photos([7452])

    assert photos[7452].endswith("image_200x200_o.jpg")
    assert restarted.commands == []


@pytest.mark.asyncio
async def test_an_artist_with_no_photo_is_remembered_as_having_none():
    """Otherwise every restart re-asks about every artist that has none,
    which on this library is most of the slow half."""
    lms = FakeLms(photos={})
    store = _store()

    await LmsArtistInfo(lms, BASE, store=store).photos([7452])
    again = FakeLms(photos={})
    photos = await LmsArtistInfo(again, BASE, store=store).photos([7452])

    assert photos == {7452: None}
    assert again.commands == []


@pytest.mark.asyncio
async def test_a_rescan_drops_the_stored_photos_too():
    """A rescan renumbers every artist id (Finding 029 §4), so a stored URL
    may belong to somebody else afterwards."""
    lms = FakeLms(photos={7452: "imageproxy/mai/artist/7452/image.png"})
    store = _store()
    info = LmsArtistInfo(lms, BASE, store=store)
    await info.photos([7452])

    info.forget()
    await LmsArtistInfo(lms, BASE, store=store).photos([7452])

    assert len(lms.commands) == 2


@pytest.mark.asyncio
async def test_a_store_that_fails_is_not_fatal():
    """A cold or broken cache means slow, not broken."""
    class Broken:
        def recall(self, namespace, key):
            raise RuntimeError("disk gone")

        def remember(self, namespace, key, value):
            raise RuntimeError("disk gone")

    lms = FakeLms(photos={7452: "imageproxy/mai/artist/7452/image.png"})

    photos = await LmsArtistInfo(lms, BASE, store=Broken()).photos([7452])

    assert photos[7452].endswith("image_200x200_o.jpg")


# --- the plugin answers in two shapes --------------------------------------


@pytest.mark.asyncio
async def test_a_photo_the_server_holds_is_served_by_path():
    lms = FakeLms(photos={7452: "imageproxy/mai/artist/7452/image.png"})

    photos = await _info(lms).photos([7452])

    assert photos[7452] == f"{BASE}/imageproxy/mai/artist/7452/image_200x200_o.jpg"


@pytest.mark.asyncio
async def test_a_photo_that_lives_elsewhere_goes_through_the_image_proxy():
    """**The defect this test exists for.** For some artists the plugin
    answers with an absolute URL at the other end - a Discogs CDN on
    George's server - and splicing that into the local shape produced
    `http://lms:9000/https://i.discogs.com/…`, which is nothing at all
    (2026-09-18)."""
    remote = "https://i.discogs.com/abc/rs:fit/g:sm/q:90/h:230/w:300/xyz.jpeg"
    lms = FakeLms(photos={7700: remote})

    photos = await _info(lms).photos([7700])

    assert photos[7700] == f"{BASE}/imageproxy/{remote}/image_200x200_o.jpg"
    assert "9000/https://" not in photos[7700]


@pytest.mark.asyncio
async def test_a_remote_photo_can_still_be_asked_for_at_page_size():
    remote = "https://i.discogs.com/abc/xyz.jpeg"
    info = _info(FakeLms(photos={7700: remote}))

    large = await info.photos([7700], PHOTO_LARGE)

    assert large[7700].endswith("image_300x300_o.jpg")


@pytest.mark.asyncio
async def test_the_plugin_is_given_longer_than_the_library_allows_itself():
    """An artist it has not looked up goes to the network on its behalf, and
    the library's 10 s was cutting those off - the panel then showed initials
    for an artist whose picture exists (2026-09-18)."""
    from gexis_core.artistinfo import CALL_TIMEOUT_S

    lms = FakeLms(photos={7452: "imageproxy/mai/artist/7452/image.png"})

    await _info(lms).photos([7452])

    assert lms.timeouts == [CALL_TIMEOUT_S]
