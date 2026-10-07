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
import json
import logging
import time
from dataclasses import dataclass, replace

from gexis_core.enrichment import fold, match_title
from gexis_core.providers import THEAUDIODB_BASE, theaudiodb_key

logger = logging.getLogger("gexis_core.artwork_sweep")

#: Namespaces in `enrichment.db`'s `notes` table.
#:
#: **Keyed on the folded name, never on an LMS id.** Finding 030's rule, from
#: Finding 029: a full rescan renumbers every artist and album id, and a
#: cache keyed on them quietly points at the wrong people afterwards.
ARTIST_NAMESPACE = "fanart-artist"
ALBUM_NAMESPACE = "fanart-album"
#: Where the last run's counts are kept, for the tile after a restart.
RUN_NAMESPACE = "sweep-run"

#: How long to leave between fanart calls. MusicBrainz's one-per-second is
#: enforced by `Http`'s own limiter; fanart's limit has never been readable
#: (Finding 030: their terms were behind a block), so this is deliberate
#: politeness rather than a measured ceiling. At ~0.4 s a call, 870 artists
#: take about ten minutes with this on top.
FANART_GAP_S = 0.3

#: How often the progress reaches the panel. A settings revision makes it
#: re-read the settings *and* reload the home strip, so publishing every
#: artist cost 279 strip reloads in two minutes (measured 2026-09-24).
PUBLISH_EVERY_S = 3.0

#: fanart's artist images, best first.
#:
#: `artistthumb` is the portrait a round tile wants. **`artistbackground` is
#: the fallback**, added 2026-09-24 after George looked at ten real examples
#: drawn as the grid draws them: fanart's backgrounds are photographs of the
#: artist, and they centre-crop to a circle like any portrait.
#:
#: **No logos.** `musiclogo`, `hdmusiclogo` and `musicbanner` are wide
#: wordmarks, and a square centre-crop cuts them to unreadable fragments -
#: `TRIN` for 4 Strings, `BOU` for La Bouche. Fitted whole they read
#: perfectly and sit small and letterboxed among full-bleed faces, which is
#: a different grid. George, 2026-09-24: *"only with the backgrounds, no
#: logos."* Measured: of 25 artists with no portrait, ~12% have a
#: background and ~24% only a logo; 72% have nothing at all.
ARTIST_KINDS = ("artistthumb", "artistbackground")

#: fanart's album images.
ALBUM_KINDS = ("albumcover",)


@dataclass(frozen=True)
class Progress:
    """What the settings row shows while this runs.

    George asked for it in these words: *"It should be honest - X out of Y
    processed (searched for), Z artist portraits found."* The third number
    matters: fanart has nothing for a real share of any library, so a run
    that ends at Y of Y with 60% found has worked perfectly.
    """

    kind: str = ""            # "all" | "portraits" | "covers" | ""
    running: bool = False
    processed: int = 0
    total: int = 0
    found: int = 0
    finished_at: float = 0.0
    cancelled: bool = False
    #: **"all"** (George, 2026-10-06: one tile for artists and albums): the
    #: albums looked at and the covers found, beside the artists' portraits
    #: in `found`.
    albums: int = 0
    covers: int = 0

    def to_json(self) -> dict:
        return {
            "kind": self.kind,
            "running": self.running,
            "processed": self.processed,
            "total": self.total,
            "found": self.found,
            "finished_at": self.finished_at or None,
            "cancelled": self.cancelled,
            "albums": self.albums,
            "covers": self.covers,
        }

    @classmethod
    def from_json(cls, data: dict) -> "Progress":
        return cls(kind=str(data.get("kind") or ""), running=False,
                   processed=int(data.get("processed") or 0), total=int(data.get("total") or 0),
                   found=int(data.get("found") or 0), finished_at=float(data.get("finished_at") or 0),
                   cancelled=bool(data.get("cancelled")), albums=int(data.get("albums") or 0),
                   covers=int(data.get("covers") or 0))

    @property
    def sentence(self) -> str:
        """The row's own text, in George's words."""
        if not self.kind:
            return "Never run"
        if self.kind == "all":
            artists = f"{self.processed:,} of {self.total:,} artists, {self.found:,} portraits"
            albums = f"{self.albums:,} albums, {self.covers:,} covers"
            if self.running:
                return f"Running - {artists} · {albums}"
            when = time.strftime("%-d %b %H:%M", time.localtime(self.finished_at)) if self.finished_at else ""
            head = "Stopped" if self.cancelled else "Last run"
            return f"{head}{f' {when}' if when else ''} - {artists} · {albums}"
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
                 theaudiodb_key=None, confidence=None, on_change=None, on_finish=None,
                 gap_s: float = FANART_GAP_S, publish_every_s: float = PUBLISH_EVERY_S,
                 clock=time.monotonic) -> None:
        self._library = library
        self._identity = identity
        self._http = http
        self._store = store
        self._fanart_key = fanart_key or (lambda: None)
        #: ADR-0120 §4: TheAudioDB after fanart.tv - the owner's key, or its
        #: shared test key without one, so a run needs no key at all now.
        self._theaudiodb_key = theaudiodb_key or (lambda: None)
        #: The score a MusicBrainz match must reach. `Head` resolved at 100
        #: and there is no way to know it is the right Head; below the
        #: threshold the artist keeps LMS's picture (ADR-0012, ADR-0059).
        self._confidence = confidence or (lambda: 0)
        self._on_change = on_change or (lambda: None)
        #: Called once when a run ends, so the panel can drop the pictures it
        #: is holding. Separate from `on_change`, which fires per artist.
        self._on_finish = on_finish or (lambda: None)
        self._gap_s = gap_s
        self._publish_every_s = publish_every_s
        self._clock = clock
        self._published_at = 0.0
        #: **The last run is kept** (George, 2026-10-06: "the status being
        #: displayed inside the tile itself, which will work also as
        #: history"): read back at start, so the tile says what was found
        #: after a restart too.
        self._progress = self._last_run()
        self._task: asyncio.Task | None = None

    def _last_run(self) -> Progress:
        if self._store is None:
            return Progress()
        try:
            raw = self._store.recall(RUN_NAMESPACE, "last")
            return Progress.from_json(json.loads(raw)) if raw else Progress()
        except KeyError:
            return Progress()
        except Exception as exc:  # a bad record must not stop the core
            logger.info("sweep: could not read the last run (%s)", exc)
            return Progress()

    def _keep_run(self) -> None:
        if self._store is None:
            return
        try:
            self._store.remember(RUN_NAMESPACE, "last", json.dumps(self._progress.to_json()))
        except Exception as exc:
            logger.info("sweep: could not keep the run (%s)", exc)

    # --- what the settings row reads ---------------------------------------

    @property
    def progress(self) -> Progress:
        return self._progress

    def _set(self, *, always: bool = False, **fields) -> None:
        """Update the progress, and tell the panel **at most every few
        seconds**.

        The first version told it on every artist. The panel treats a
        settings revision as a reason to re-read the settings *and* reload
        the home strip, so one run produced **279 strip reloads and 279
        settings reads in two minutes** on George's device - each strip
        reload an LMS browse. The number on screen does not need to be
        right 917 times; it needs to be moving.
        """
        self._progress = replace(self._progress, **fields)
        now = self._clock()
        if not always and now - self._published_at < self._publish_every_s:
            return
        self._published_at = now
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
        self._progress = Progress(kind=kind, running=True)
        self._published_at = self._clock()
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
            found = albums = covers = 0
            for index, (artist_id, name) in enumerate(artists, start=1):
                try:
                    got = await self._one(kind, artist_id, name)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # one bad artist must not end the run
                    logger.info("sweep: %s failed (%s)", name, exc)
                    got = Found()
                if kind == "covers":
                    found += 1 if got.covers else 0
                else:
                    found += 1 if got.portrait else 0
                albums += got.albums
                covers += got.covers
                self._set(processed=index, found=found, albums=albums, covers=covers)
            self._set(running=False, finished_at=time.time(), always=True)
            self._keep_run()
            # **The pictures changed under the panel.** Once, here, and not
            # 917 times on the way.
            self._on_finish()
            logger.info("sweep: %s finished - %s of %s, %s found",
                        kind, self._progress.processed, self._progress.total, found)
        except asyncio.CancelledError:
            self._set(running=False, cancelled=True, finished_at=time.time(), always=True)
            self._keep_run()
            self._on_finish()
            logger.info("sweep: %s cancelled at %s of %s",
                        kind, self._progress.processed, self._progress.total)
            raise
        except Exception as exc:
            self._set(running=False, finished_at=time.time(), always=True)
            self._keep_run()
            self._on_finish()
            logger.error("sweep: %s stopped: %s", kind, exc)

    async def _album_artists(self) -> list[tuple[int, str]]:
        """Every album artist LMS knows, `(id, name)`.

        Album artists, not contributors: 917 against thousands on George's own
        library, and the list the panel draws is theirs.
        """
        return await self._library.album_artists()

    async def _one(self, kind: str, artist_id: int, name: str) -> "Found":
        """One artist: their portrait, their albums' covers, or - "all" -
        both from the same lookups (they are largely the same calls,
        Finding 054 §9)."""
        folded = fold(name)
        if not folded:
            return Found()
        # **The raw name is what MusicBrainz is asked**; the folded one is
        # only the cache key (`providers.search_names`).
        resolved = await self._identity.resolve(folded, raw=name)
        if resolved is False:
            # Could not ask. **Never stored as "no picture"** - Finding 036's
            # most important line, and on a sweep of 870 it would poison the
            # whole library in one press.
            return Found()
        if not resolved:
            return Found()
        mbid, score = resolved
        if score < self._confidence():
            logger.info("sweep: %s scored %s, below the threshold", name, score)
            return Found()

        # fanart.tv first; TheAudioDB for what it has not (ADR-0120 §4).
        # **"Nothing" is stored only when both were asked and both said so**:
        # a source that could not be asked leaves what was remembered.
        art = await self._fanart(mbid) if self._fanart_key() else {}
        tadb = _Lazy(lambda: self._tadb_artist(mbid))

        portrait = False
        if kind in ("portraits", "all"):
            url = self._pick(art, ARTIST_KINDS) if art else None
            asked = True
            if url is None:
                artist = await tadb.get()
                url = _first(artist, TADB_ARTIST_FIELDS) if artist else None
                asked = not (url is None and (art is None or artist is None))
            if asked:  # a source that could not be asked leaves it be
                self._remember(ARTIST_NAMESPACE, folded, url)
                portrait = url is not None
            if kind == "portraits":
                return Found(portrait=portrait)

        mine = await self._library.album_titles(artist_id)
        if not mine:
            return Found(portrait=portrait)
        groups = await self._release_groups(mbid)
        albums = (art or {}).get("albums") or {}
        tadb_albums = _Lazy(lambda: self._tadb_albums(tadb))
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
            if url is None:
                theirs = await tadb_albums.get()
                if theirs is not None:
                    url = theirs.get(group_id) if group_id else None
                    url = url or theirs.get(match_title(title))
                if url is None and group_id and theirs is not None:
                    # **One album at a time**: the shared key's album list
                    # holds one album per artist (measured 2026-10-05,
                    # Coldplay), its per-album lookup answers for any.
                    one = await self._tadb_album(group_id)
                    if one is None:
                        theirs = None  # could not ask: leave it be
                    else:
                        url = one or None
                if url is None and (art is None or theirs is None):
                    continue  # a source could not be asked: leave it be
            # **Stored under the title the library has**, not the release
            # group's, because that is the key the panel looks up. `None` is
            # stored too: "asked, neither had one" is an answer.
            self._remember(ALBUM_NAMESPACE, f"{folded}\x1f{fold(title)}", url)
            stored += 1 if url else 0
        return Found(portrait=portrait, albums=len(mine), covers=stored)

    async def _tadb_artist(self, mbid: str) -> dict | None:
        """TheAudioDB's record of an artist: `{}` when it has none, None
        when it could not be asked."""
        body = await self._http.json(
            f"{THEAUDIODB_BASE}/{theaudiodb_key(self._theaudiodb_key())}/artist-mb.php", params={"i": mbid})
        if body is None:
            return None
        return (body.get("artists") or [None])[0] or {}

    async def _tadb_album(self, group_id: str) -> str | None:
        """One album's cover from TheAudioDB by its release group: the URL,
        `""` when it has none, None when it could not be asked."""
        body = await self._http.json(
            f"{THEAUDIODB_BASE}/{theaudiodb_key(self._theaudiodb_key())}/album-mb.php", params={"i": group_id})
        if body is None:
            return None
        album = (body.get("album") or [None])[0] or {}
        return album.get("strAlbumThumb") or ""

    async def _tadb_albums(self, tadb: "_Lazy") -> dict[str, str] | None:
        """TheAudioDB's covers for an artist, by release-group id and by
        matchable title; `{}` when it has none, None when it could not be
        asked. One call for the whole discography."""
        artist = await tadb.get()
        if artist is None:
            return None
        if not artist.get("idArtist"):
            return {}
        body = await self._http.json(
            f"{THEAUDIODB_BASE}/{theaudiodb_key(self._theaudiodb_key())}/album.php",
            params={"i": artist["idArtist"]})
        if body is None:
            return None
        covers: dict[str, str] = {}
        for album in body.get("album") or []:
            thumb = album.get("strAlbumThumb")
            if not thumb:
                continue
            if album.get("strMusicBrainzID"):
                covers.setdefault(album["strMusicBrainzID"], thumb)
            title = match_title(album.get("strAlbum") or "")
            if title:
                covers.setdefault(title, thumb)
        return covers

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


@dataclass(frozen=True)
class Found:
    """What one artist gave: their portrait, the albums looked at, the
    covers found."""

    portrait: bool = False
    albums: int = 0
    covers: int = 0


#: TheAudioDB's portrait first, then its fanart (ADR-0120 §4).
TADB_ARTIST_FIELDS = ("strArtistThumb", "strArtistFanart")


def _first(record: dict, fields: tuple[str, ...]) -> str | None:
    return next((record.get(f) for f in fields if record.get(f)), None)


class _Lazy:
    """One call, made only if something asks, and its answer kept."""

    def __init__(self, make) -> None:
        self._make = make
        self._done = False
        self._value = None

    async def get(self):
        if not self._done:
            self._value = await self._make()
            self._done = True
        return self._value


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
