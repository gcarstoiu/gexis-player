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
    match_title,
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
    def __init__(self, artists, albums=None):
        self._artists = artists
        self._albums = albums or {}

    async def album_artists(self):
        return self._artists

    async def album_titles(self, artist_id):
        return self._albums.get(artist_id, [])


class FakeIdentity:
    def __init__(self, answers):
        self.answers = answers
        self.asked = []

    async def resolve(self, folded, raw=None):
        # The sweep asks with the folded key *and* the raw name: the key is
        # ours, the name is what MusicBrainz is searched with.
        self.asked.append((folded, raw))
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
    library = kw.pop("library", FakeLibrary(
        [(1, "Isaac Hayes")],
        {1: ["Hot Buttered Soul", "Black Moses (Deluxe Edition)", "Nothing Fanart Has"]},
    ))
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
        # **The edition suffix is stripped for matching and kept for the key**:
        # the panel looks it up by the name the library has.
        assert store.rows[
            (ALBUM_NAMESPACE, "isaac hayes\x1fblack moses deluxe edition")
        ] == "https://fan/two.jpg"
        # asked for, and fanart had none: stored as nothing, not skipped
        assert store.rows[(ALBUM_NAMESPACE, "isaac hayes\x1fnothing fanart has")] is None
        # **Only what this library holds.** Their catalogue had a release
        # group we do not own; storing it put 16,391 rows in a 4,567-album
        # store and none of the extras was ever read.
        assert len(store.rows) == 3
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


class TestMatchingTwoCatalogues:
    """**43% of George's albums matched nothing** before this (measured
    2026-09-24), and it was the matcher rather than fanart's coverage: LMS
    shows what the tagger wrote and MusicBrainz shows its own title."""

    @pytest.mark.parametrize("theirs, ours", [
        ("12 X 5", "12 x 5 (2006, Japan Mini LP)"),
        ("MTV Unplugged", "[1997] MTV Unplugged [EP]"),
        ("57th & 9th", "57th & 9th (Deluxe Edition)"),
        ("Abbey Road", "Abbey Road (Remastered)"),
        ("Nevermind", "Nevermind - Deluxe Edition"),
        ("OK Computer", "OK Computer"),
    ])
    def test_an_edition_matches_the_release_group(self, theirs, ours):
        assert match_title(theirs) == match_title(ours)

    def test_it_does_not_collapse_different_albums(self):
        """Stripping too much would hand one cover to two records."""
        assert match_title("Kid A") != match_title("Amnesiac")
        assert match_title("Vol. 1") != match_title("Greatest Hits")

    def test_a_title_that_is_only_an_edition_word_survives(self):
        """`fold` of nothing is nothing, and a key of "" would match every
        other album with an empty key."""
        assert match_title("Remastered") == "remastered"
        assert match_title("(Deluxe Edition)") == "deluxe edition"


class TestProgressDoesNotFloodThePanel:
    """**279 strip reloads and 279 settings reads in two minutes**, measured
    on George's device during the first run. The panel treats a settings
    revision as a reason to re-read the settings *and* reload the home strip,
    and the first version published one per artist.
    """

    async def test_it_publishes_on_a_timer_not_per_artist(self):
        ticks = {"now": 0.0}
        published = []

        library = FakeLibrary(
            [(i, f"Artist {i}") for i in range(20)],
            {i: [] for i in range(20)},
        )
        sweep, _, _, _ = build(
            library=library,
            identity=FakeIdentity({}),          # nothing resolves; the walk still runs
            on_change=lambda: published.append(ticks["now"]),
            publish_every_s=3.0,
            clock=lambda: ticks["now"],
        )
        assert sweep.start("portraits") is True
        await sweep._task
        # start, and the end - not twenty
        assert len(published) <= 3, published

    async def test_the_end_is_always_published(self):
        published = []
        sweep, _, _, _ = build(
            library=FakeLibrary([(1, "A")], {1: []}),
            identity=FakeIdentity({}),
            on_change=lambda: published.append(1),
            publish_every_s=999.0,
            clock=lambda: 0.0,
        )
        await run(sweep, "portraits")
        assert len(published) >= 2, "the final number must reach the panel"
        assert sweep.progress.running is False

    async def test_the_pictures_signal_fires_once_at_the_end(self):
        """The panel drops every face it holds when this changes, so it must
        not fire per artist."""
        finished = []
        sweep, _, _, _ = build(
            library=FakeLibrary([(i, f"A{i}") for i in range(10)], {}),
            identity=FakeIdentity({}),
            on_finish=lambda: finished.append(1),
            clock=lambda: 0.0,
        )
        await run(sweep, "portraits")
        assert finished == [1]
