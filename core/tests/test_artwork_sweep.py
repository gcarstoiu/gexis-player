# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0059's two buttons.

George, 2026-09-24: *"there should be a trigger in settings enrichment for a
user to trigger an automatic update of album artists portraits, with a
progress bar and completion status."*
"""
import asyncio

import pytest

from gexis_core.artwork_sweep import (
    ALBUM_NAMESPACE,
    ARTIST_NAMESPACE,
    ArtworkSweep,
    Progress,
    remembered,
)


class FakeStore:
    def __init__(self):
        self.rows = {}

    def remember(self, namespace, key, value):
        self.rows[(namespace, key)] = value

    def recall(self, namespace, key):
        try:
            return self.rows[(namespace, key)]
        except KeyError:
            raise KeyError(key)


class FakeLibrary:
    def __init__(self, artists):
        self._artists = artists

    async def album_artists(self):
        return self._artists


class FakeIdentity:
    def __init__(self, answers):
        self.answers = answers
        self.asked = []

    async def resolve(self, folded):
        self.asked.append(folded)
        return self.answers.get(folded, None)


class FakeHttp:
    def __init__(self, bodies):
        self.bodies = bodies
        self.calls = []

    async def json(self, url, params=None, headers=None):
        self.calls.append(url)
        for fragment, body in self.bodies.items():
            if fragment in url:
                return body
        return None


def build(**kw):
    store = kw.pop("store", FakeStore())
    library = kw.pop("library", FakeLibrary([(1, "Isaac Hayes")]))
    identity = kw.pop("identity", FakeIdentity({"isaac hayes": ("MB1", 100)}))
    http = kw.pop("http", FakeHttp({}))
    sweep = ArtworkSweep(
        library, identity, http, store,
        fanart_key=kw.pop("fanart_key", lambda: "KEY"),
        confidence=kw.pop("confidence", lambda: 0),
        gap_s=0,
        **kw,
    )
    return sweep, store, identity, http


async def run(sweep, kind):
    assert sweep.start(kind) is True
    await sweep._task


class TestTheProgressSentence:
    """George's own wording: *"X out of Y processed (searched for), Z artist
    portraits found."* The third number is the point: fanart has nothing for
    a real share of any library, so Y of Y with 60% found is a clean run."""

    def test_it_says_all_three_numbers(self):
        p = Progress(kind="portraits", running=True, processed=40, total=870, found=26)
        assert p.sentence == "40 of 870 processed, 26 portraits found"

    def test_a_finished_run_still_says_what_it_found(self):
        p = Progress(kind="portraits", processed=870, total=870, found=612)
        assert "870 of 870" in p.sentence and "612" in p.sentence

    def test_never_run_says_so(self):
        assert Progress().sentence == "Never run"

    def test_a_cancelled_run_does_not_pretend_to_be_complete(self):
        p = Progress(kind="covers", processed=12, total=870, found=3, cancelled=True)
        assert p.sentence.startswith("Stopped at 12 of 870")


class TestPortraits:
    async def test_it_stores_the_thumb_under_the_folded_name(self):
        sweep, store, _, _ = build(http=FakeHttp({
            "fanart.tv": {"artistthumb": [{"url": "https://fan/thumb.jpg"}]},
        }))
        await run(sweep, "portraits")
        assert store.rows[(ARTIST_NAMESPACE, "isaac hayes")] == "https://fan/thumb.jpg"
        assert sweep.progress.processed == 1
        assert sweep.progress.found == 1

    async def test_nothing_found_is_stored_as_nothing(self):
        """*"fanart has no picture for this one"* is an answer, and the
        fallback reads it as "keep LMS's"."""
        sweep, store, _, _ = build(http=FakeHttp({"fanart.tv": {"artistthumb": []}}))
        await run(sweep, "portraits")
        assert store.rows[(ARTIST_NAMESPACE, "isaac hayes")] is None
        assert sweep.progress.found == 0

    async def test_a_503_is_never_stored_as_nothing(self):
        """Finding 036's most important line, and on a sweep of 870 it would
        poison the whole library in one press."""
        sweep, store, _, _ = build(http=FakeHttp({}))  # json() answers None
        await run(sweep, "portraits")
        assert (ARTIST_NAMESPACE, "isaac hayes") not in store.rows

    async def test_a_low_score_keeps_lms_picture(self):
        """`Head` resolved at 100 and there is no telling it is the right
        Head; below the threshold nothing is stored at all."""
        sweep, store, _, http = build(
            identity=FakeIdentity({"isaac hayes": ("MB1", 40)}),
            confidence=lambda: 80,
            http=FakeHttp({"fanart.tv": {"artistthumb": [{"url": "u"}]}}),
        )
        await run(sweep, "portraits")
        assert store.rows == {}
        assert http.calls == []

    async def test_an_unresolvable_artist_is_not_an_error(self):
        sweep, store, _, _ = build(identity=FakeIdentity({}))
        await run(sweep, "portraits")
        assert sweep.progress.processed == 1
        assert sweep.progress.found == 0


class TestCovers:
    async def test_one_fanart_call_answers_every_album(self):
        """Finding 054 §9: fanart returns the albums in the *artist* call, so
        a cover sweep makes no per-album request."""
        sweep, store, _, http = build(http=FakeHttp({
            "webservice.fanart.tv": {
                "artistthumb": [{"url": "https://fan/thumb.jpg"}],
                "albums": {
                    "RG1": {"albumcover": [{"url": "https://fan/one.jpg"}]},
                    "RG2": {"albumcover": [{"url": "https://fan/two.jpg"}]},
                },
            },
            "musicbrainz.org": {"release-groups": [
                {"id": "RG1", "title": "Hot Buttered Soul"},
                {"id": "RG2", "title": "Black Moses"},
                {"id": "RG3", "title": "Nothing Fanart Has"},
            ]},
        }))
        await run(sweep, "covers")
        assert store.rows[(ALBUM_NAMESPACE, "isaac hayes\x1fhot buttered soul")] == "https://fan/one.jpg"
        assert store.rows[(ALBUM_NAMESPACE, "isaac hayes\x1fblack moses")] == "https://fan/two.jpg"
        # asked for, and fanart had none: stored as nothing, not skipped
        assert store.rows[(ALBUM_NAMESPACE, "isaac hayes\x1fnothing fanart has")] is None
        # one fanart call and one MusicBrainz lookup, for three albums
        assert sum("fanart" in c for c in http.calls) == 1
        assert sum("musicbrainz" in c for c in http.calls) == 1


class TestOneAtATime:
    """They share MusicBrainz and fanart, and by Finding 054 §9 they are
    largely the same calls - so a second run would spend its time on the
    first's limiter. Refused, not queued: a button that silently queues is a
    progress bar that lies."""

    async def test_the_second_button_is_refused_while_the_first_runs(self):
        started = asyncio.Event()
        release = asyncio.Event()

        class SlowLibrary:
            async def album_artists(self):
                started.set()
                await release.wait()
                return []

        sweep, _, _, _ = build(library=SlowLibrary())
        assert sweep.start("portraits") is True
        await started.wait()
        assert sweep.start("covers") is False
        assert sweep.progress.kind == "portraits"
        release.set()
        await sweep._task

    async def test_no_key_means_nothing_to_ask(self):
        sweep, _, _, _ = build(fanart_key=lambda: None)
        assert sweep.start("portraits") is False


class TestWhatTheCallersRead:
    def test_three_outcomes_are_told_apart(self):
        store = FakeStore()
        store.remember(ARTIST_NAMESPACE, "a", "https://u")
        store.remember(ARTIST_NAMESPACE, "b", None)
        assert remembered(store, ARTIST_NAMESPACE, "a") == "https://u"
        assert remembered(store, ARTIST_NAMESPACE, "b") is None      # asked, nothing
        assert remembered(store, ARTIST_NAMESPACE, "c") is False     # never asked
        assert remembered(None, ARTIST_NAMESPACE, "a") is False
