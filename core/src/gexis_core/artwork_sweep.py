# SPDX-License-Identifier: GPL-3.0-or-later
"""Fill the library's artist portraits and album covers from fanart.tv.

**A button, not a background job** ([ADR-0059](../../../docs/decisions/0059-artist-portraits-in-the-list.md)).
George, 2026-09-24: *"there should be a trigger in settings enrichment for a
user to trigger an automatic update of album artists portraits, with a
progress bar and completion status."*

**One walk serves both buttons.** fanart returns an artist's albums in the
artist call - 17 release groups for Isaac Hayes, each with its own cover -
so an album sweep needs no per-album request (Finding 054 §9). The pieces:

1. the album artists, from LMS;
2. each one's MusicBrainz id, searched by name and remembered
   (`providers.ArtistIdentity`);
3. `artist/<mbid>?inc=release-groups`, a 145 ms *lookup* rather than a
   search, for the ids of everything that artist released;
4. one fanart call, which answers the portrait and every cover at once.

**Nothing here is on a screen's path.** The panel reads what this leaves
behind; a cold library simply looks the way it looks today.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, replace

from gexis_core.enrichment import fold

logger = logging.getLogger("gexis_core.artwork_sweep")

#: Namespaces in `enrichment.db`'s `notes` table.
#:
#: **Keyed on the folded name, never on an LMS id.** Finding 030's rule, from
#: Finding 029: a full rescan renumbers every artist and album id, and a
#: cache keyed on them quietly points at the wrong people afterwards.
ARTIST_NAMESPACE = "fanart-artist"
ALBUM_NAMESPACE = "fanart-album"

#: How long to leave between fanart calls. MusicBrainz's one-per-second is
#: enforced by `Http`'s own limiter; fanart's limit has never been readable
#: (Finding 030: their terms were behind a block), so this is deliberate
#: politeness rather than a measured ceiling. At ~0.4 s a call, 870 artists
#: take about ten minutes with this on top.
FANART_GAP_S = 0.3

#: fanart's artist images, best first. `artistthumb` is the portrait a round
#: tile wants; `musicbanner` is the fallback that at least has the artist in
#: it. `artistbackground` is deliberately absent - it is 1920x1080 scenery
#: and looks wrong in a 64px circle.
ARTIST_KINDS = ("artistthumb", "musicbanner")

#: fanart's album images.
ALBUM_KINDS = ("albumcover",)


#: Everything an edition adds to a title. LMS shows what the tagger wrote -
#: `12 x 5 (2006, Japan Mini LP)`, `[1997] MTV Unplugged [EP]`,
#: `57th & 9th (Deluxe Edition)` - and MusicBrainz's release group is called
#: `12 X 5`, `MTV Unplugged`, `57th & 9th`. Comparing them as they stand
#: matched nothing for **43% of George's albums** (measured 2026-09-24), and
#: that was the matcher falling short rather than fanart having no cover.
_BRACKETS = re.compile(r"[\(\[\{][^\)\]\}]*[\)\]\}]")

#: Words an edition is usually announced with, when there are no brackets to
#: strip - `Abbey Road Remastered`, `Nevermind Deluxe Edition`.
_EDITION = re.compile(
    r"\b(deluxe|expanded|remaster(ed)?|anniversary|edition|version|reissue|"
    r"mono|stereo|bonus|disc \d+|cd \d+|vol(ume)? \d+)\b.*$"
)


def match_title(title: str) -> str:
    """A title reduced to what two catalogues can agree on.

    Brackets first, then a trailing edition phrase, then the ordinary fold.
    **Only for matching** - what is stored and looked up is still the folded
    title as the library has it, so the panel finds it by the name it knows.
    """
    folded = fold(_BRACKETS.sub(" ", title or "")) or fold(title)
    # **Never empty.** A title that is nothing *but* an edition phrase -
    # `(Deluxe Edition)` - would reduce to "", and an empty key matches every
    # other album that reduced to "" as well. Each step falls back to the one
    # before it rather than to nothing.
    return fold(_EDITION.sub("", folded)) or folded


@dataclass(frozen=True)
class Progress:
    """What the settings row shows while this runs.

    George asked for it in these words: *"It should be honest - X out of Y
    processed (searched for), Z artist portraits found."* The third number
    matters: fanart has nothing for a real share of any library, so a run
    that ends at Y of Y with 60% found has worked perfectly.
    """

    kind: str = ""            # "portraits" | "covers" | ""
    running: bool = False
    processed: int = 0
    total: int = 0
    found: int = 0
    finished_at: float = 0.0
    cancelled: bool = False

    def to_json(self) -> dict:
        return {
            "kind": self.kind,
            "running": self.running,
            "processed": self.processed,
            "total": self.total,
            "found": self.found,
            "finished_at": self.finished_at or None,
            "cancelled": self.cancelled,
        }

    @property
    def sentence(self) -> str:
        """The row's own text, in George's words."""
        if not self.kind:
            return "Never run"
        noun = "portraits" if self.kind == "portraits" else "covers"
        if self.running:
            return f"{self.processed} of {self.total} processed, {self.found} {noun} found"
        if self.cancelled:
            return f"Stopped at {self.processed} of {self.total}, {self.found} {noun} found"
        return f"{self.processed} of {self.total} processed, {self.found} {noun} found"


class ArtworkSweep:
    """Both buttons, and the state the settings row reads.

    **One at a time.** They share MusicBrainz and fanart, and by Finding 054
    §9 they are largely the same calls - so the second would spend its time
    waiting on the first's limiter anyway. Starting one while the other runs
    is refused rather than queued, because a button that silently queues is
    a button whose progress bar lies.
    """

    def __init__(self, library, identity, http, store, *, fanart_key=None,
                 confidence=None, on_change=None, gap_s: float = FANART_GAP_S) -> None:
        self._library = library
        self._identity = identity
        self._http = http
        self._store = store
        self._fanart_key = fanart_key or (lambda: None)
        #: The score a MusicBrainz match must reach. `Head` resolved at 100
        #: and there is no way to know it is the right Head; below the
        #: threshold the artist keeps LMS's picture (ADR-0012, ADR-0059).
        self._confidence = confidence or (lambda: 0)
        self._on_change = on_change or (lambda: None)
        self._gap_s = gap_s
        self._progress = Progress()
        self._task: asyncio.Task | None = None

    # --- what the settings row reads ---------------------------------------

    @property
    def progress(self) -> Progress:
        return self._progress

    def _set(self, **fields) -> None:
        self._progress = replace(self._progress, **fields)
        try:
            self._on_change()
        except Exception as exc:  # a display that fails must not stop the run
            logger.info("sweep: could not publish progress (%s)", exc)

    # --- the buttons -------------------------------------------------------

    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self, kind: str) -> bool:
        """Begin a run. False when one is already going."""
        if self.running():
            logger.info("sweep: %s asked for while %s is running", kind, self._progress.kind)
            return False
        if not self._fanart_key():
            logger.warning("sweep: no fanart.tv key, nothing to ask")
            return False
        self._progress = Progress(kind=kind, running=True)
        self._on_change()
        self._task = asyncio.ensure_future(self._run(kind))
        return True

    def cancel(self) -> bool:
        if not self.running():
            return False
        self._task.cancel()
        return True

    # --- the walk ----------------------------------------------------------

    async def _run(self, kind: str) -> None:
        try:
            artists = await self._album_artists()
            self._set(total=len(artists))
            found = 0
            for index, (artist_id, name) in enumerate(artists, start=1):
                try:
                    hit = await self._one(kind, artist_id, name)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # one bad artist must not end the run
                    logger.info("sweep: %s failed (%s)", name, exc)
                    hit = False
                found += 1 if hit else 0
                self._set(processed=index, found=found)
            self._set(running=False, finished_at=time.time())
            logger.info("sweep: %s finished - %s of %s, %s found",
                        kind, self._progress.processed, self._progress.total, found)
        except asyncio.CancelledError:
            self._set(running=False, cancelled=True, finished_at=time.time())
            logger.info("sweep: %s cancelled at %s of %s",
                        kind, self._progress.processed, self._progress.total)
            raise
        except Exception as exc:
            self._set(running=False, finished_at=time.time())
            logger.error("sweep: %s stopped: %s", kind, exc)

    async def _album_artists(self) -> list[tuple[int, str]]:
        """Every album artist LMS knows, `(id, name)`.

        Album artists, not contributors: 917 against 7,296 on George's own
        library, and the list the panel draws is theirs.
        """
        return await self._library.album_artists()

    async def _one(self, kind: str, artist_id: int, name: str) -> bool:
        """One artist. True when something was stored for them."""
        folded = fold(name)
        if not folded:
            return False
        resolved = await self._identity.resolve(folded)
        if resolved is False:
            # Could not ask. **Never stored as "no picture"** - Finding 036's
            # most important line, and on a sweep of 870 it would poison the
            # whole library in one press.
            return False
        if not resolved:
            return False
        mbid, score = resolved
        if score < self._confidence():
            logger.info("sweep: %s scored %s, below the threshold", name, score)
            return False

        art = await self._fanart(mbid)
        if art is None:
            return False  # could not ask; leave whatever is remembered

        if kind == "portraits":
            url = self._pick(art, ARTIST_KINDS)
            self._remember(ARTIST_NAMESPACE, folded, url)
            return url is not None

        mine = await self._library.album_titles(artist_id)
        if not mine:
            return False
        groups = await self._release_groups(mbid)
        albums = art.get("albums") or {}
        # **Their catalogue, indexed the way ours can be matched against it.**
        by_title: dict[str, str] = {}
        for group_id, title in groups.items():
            key = match_title(title)
            if key:
                by_title.setdefault(key, group_id)

        stored = 0
        for title in mine:
            group_id = by_title.get(match_title(title))
            url = self._pick(albums.get(group_id) or {}, ALBUM_KINDS) if group_id else None
            # **Stored under the title the library has**, not the release
            # group's, because that is the key the panel looks up. `None` is
            # stored too: "asked, fanart had none" is an answer.
            self._remember(ALBUM_NAMESPACE, f"{folded}\x1f{fold(title)}", url)
            stored += 1 if url else 0
        return stored > 0

    async def _fanart(self, mbid: str):
        """fanart's whole answer for one artist, or None when it could not
        be asked. Portraits *and* albums, in one call."""
        key = self._fanart_key()
        if not key:
            return None
        await asyncio.sleep(self._gap_s)
        return await self._http.json(
            f"https://webservice.fanart.tv/v3/music/{mbid}", params={"api_key": key}
        )

    async def _release_groups(self, mbid: str) -> dict[str, str]:
        """`{release-group id: title}` for one artist.

        **A lookup, not a search.** Finding 036 measured the lookup endpoint
        at 4 of 4 and the search endpoint at 4 of 9; this one answered in
        145 ms with all 25 of an artist's release groups.
        """
        body = await self._http.json(
            f"https://musicbrainz.org/ws/2/artist/{mbid}",
            params={"inc": "release-groups", "fmt": "json"},
        )
        if not body:
            return {}
        return {
            group["id"]: group.get("title") or ""
            for group in (body.get("release-groups") or [])
            if group.get("id")
        }

    @staticmethod
    def _pick(art: dict, kinds: tuple[str, ...]) -> str | None:
        """The first image fanart offers, in our order of preference."""
        for kind in kinds:
            entries = art.get(kind) or []
            for entry in entries:
                url = entry.get("url") if isinstance(entry, dict) else None
                if url:
                    return url
        return None

    def _remember(self, namespace: str, key: str, url: str | None) -> None:
        """`None` is stored too: *"fanart has nothing for this one"* is an
        answer, and the fallback reads it as "use LMS's"."""
        if self._store is None:
            return
        try:
            self._store.remember(namespace, key, url)
        except Exception as exc:
            logger.info("sweep: could not store %s/%s (%s)", namespace, key, exc)


def remembered(store, namespace: str, key: str) -> str | None | bool:
    """What the sweep left for `key`: a URL, `None` for *"asked, nothing"*,
    or `False` for *"never asked"* - which the callers read as "fall back to
    LMS" in both of the last two cases, and tell apart only in the logs."""
    if store is None:
        return False
    try:
        return store.recall(namespace, key)
    except KeyError:
        return False
    except Exception as exc:
        logger.info("sweep: could not read %s/%s (%s)", namespace, key, exc)
        return False
