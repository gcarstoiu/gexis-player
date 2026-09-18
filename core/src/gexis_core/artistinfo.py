# SPDX-License-Identifier: GPL-3.0-or-later
"""LMS's own artist information (ADR-0040 §1, Finding 035).

George asked whether LMS already had artist photos before Phase 8 went and
fetched them from elsewhere. It does - not core LMS, but the **Music &
Artist Information** plugin (`musicartistinfo`), which answers photos and
biographies for an LMS artist id.

**Three things this module exists to get right**, all measured:

- **`/music/artist_<id>/cover` is not artist artwork.** It answers `200` with
  LMS's generic placeholder, byte-identical for every artist including one
  that does not exist (Finding 035). Only the plugin's own URL is a photo.
  Nothing here constructs that URL.
- **The plugin says no when it means no**: for an artist it has nothing for,
  it answers `{"error": "I'm sorry, didn't find any relevant information."}`
  rather than a placeholder URL. So a returned `url` is evidence.
- **An absent plugin drops the connection.** LMS closes the socket on an
  unknown command rather than answering an error (measured 2026-09-18), so
  the RPC raises. That is the detection signal, and because a dropped
  connection can also mean a restarting server, it is retried rather than
  believed forever.
- **A timeout is not an absent plugin.** Found on hardware the same day: an
  *uncached* artist costs the plugin 500-900 ms because it goes to the
  network, 16 of those at once ran past the library's 10 s RPC timeout, and
  this module read the timeout as "no plugin here" and turned photos off for
  ten minutes. Slow and absent are now told apart by what the failure was.

**Photos are asked for one artist at a time but not one after another.** 40
artists took 1,247 ms in series and 212 ms in parallel against George's
server (2026-09-18), so a page's worth is fetched concurrently and bounded
by `CONCURRENCY`. The panel asks only for the artists it is about to draw:
917 of them at once is neither necessary nor kind.
"""
from __future__ import annotations

import asyncio
import logging
import time

logger = logging.getLogger("gexis_core.artistinfo")

#: What the panel draws: a 132px card in the grid, a 262px disc on the artist
#: page. ADR-0038 §7's ladder, and `.jpg` because the plugin's PNG is 93,939
#: bytes against 17,999 for the same 200px picture (Finding 035).
PHOTO_THUMB = 200
PHOTO_LARGE = 300

#: At most this many plugin calls in flight. Measured 2026-09-18: an artist
#: the plugin has already looked up costs 7 ms, one it has not costs
#: 500-900 ms, because it goes to the network. Sixteen of the slow kind at
#: once ran past the library's own 10 s RPC timeout; four leaves room.
CONCURRENCY = 4

#: How long an apparently absent plugin is left alone before being tried
#: again. A dropped connection is also what a restarting server looks like.
RECHECK_S = 600.0


def _is_absent(exc: BaseException) -> bool:
    """Does this failure mean "no such command", or just "not yet"?

    The library wraps every RPC failure in its own exception with
    `from exc`, so the original is on `__cause__`. A dropped connection is
    LMS refusing a command it does not know; a timeout is a plugin that went
    to the network and took longer than the RPC would wait.
    """
    seen = []
    while exc is not None and exc not in seen:
        seen.append(exc)
        if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
            return False
        if isinstance(exc, (ConnectionResetError, ConnectionError)):
            return True
        if type(exc).__name__ in ("ServerDisconnectedError", "ClientOSError"):
            return True
        exc = exc.__cause__
    # Unrecognised: treat as transient. Turning photos off for ten minutes
    # is the more expensive mistake of the two.
    return False


class LmsArtistInfo:
    """One per daemon. Holds what the plugin has answered, and whether it is
    there at all."""

    def __init__(self, rpc, base_url: str, *, clock=time.monotonic) -> None:
        #: The library's `rpc`, so this shares the daemon's one HTTP session.
        self._rpc = rpc
        self._base = base_url.rstrip("/")
        self._clock = clock
        self._photos: dict[int, str | None] = {}
        self._absent_until: float | None = None
        self._semaphore = asyncio.Semaphore(CONCURRENCY)

    # --- the plugin --------------------------------------------------------

    def _believed_absent(self) -> bool:
        return self._absent_until is not None and self._clock() < self._absent_until

    async def _ask(self, command: list) -> dict | None:
        """One plugin call, or None if the plugin is not answering."""
        if self._believed_absent():
            return None
        async with self._semaphore:
            try:
                result = await self._rpc(command)
            except Exception as exc:
                if _is_absent(exc):
                    # An unknown command closes the socket, which is what a
                    # server without the plugin looks like.
                    if self._absent_until is None:
                        logger.info("artistinfo: the plugin closed the connection (%r); "
                                    "not asking again for %.0fs", exc, RECHECK_S)
                    self._absent_until = self._clock() + RECHECK_S
                else:
                    # Slow, not missing. Nothing is remembered and nothing is
                    # turned off: this artist simply keeps its initials for
                    # now (found on hardware, 2026-09-18).
                    logger.debug("artistinfo: %s timed out", command)
                return None
        self._absent_until = None
        return result or {}

    def _url(self, result: dict | None, size: int) -> str | None:
        """The plugin's URL, at the size the panel draws.

        Its `url` is the unsized `image.png`; the sized form is the same path
        with `image_<W>x<H>_o.jpg`, which is a fifth of the bytes.
        """
        if not result or result.get("error") or not result.get("url"):
            return None
        path = str(result["url"]).strip("/")
        base, _, _ = path.rpartition("/")
        return f"{self._base}/{base}/image_{size}x{size}_o.jpg"

    # --- reads -------------------------------------------------------------

    async def photos(self, artist_ids, size: int = PHOTO_THUMB) -> dict[int, str | None]:
        """A photo URL per artist, or None where the plugin has none. Asked
        concurrently; already-known artists cost nothing."""
        wanted = [i for i in dict.fromkeys(artist_ids) if i not in self._photos]
        if wanted and not self._believed_absent():
            results = await asyncio.gather(*(
                self._ask(["musicartistinfo", "artistphoto", 0, 1, f"artist_id:{artist_id}"])
                for artist_id in wanted
            ))
            for artist_id, result in zip(wanted, results):
                # A call that did not reach the plugin is not an answer, so
                # it is not remembered as "no photo" (the same distinction
                # enrichment.py draws between MISSING and UNAVAILABLE).
                if result is None:
                    continue
                self._photos[artist_id] = self._url(result, PHOTO_THUMB)
        out = {}
        for artist_id in dict.fromkeys(artist_ids):
            url = self._photos.get(artist_id)
            if url and size != PHOTO_THUMB:
                url = url.replace(f"image_{PHOTO_THUMB}x{PHOTO_THUMB}_o.jpg",
                                  f"image_{size}x{size}_o.jpg")
            out[artist_id] = url
        return out

    async def biography(self, artist_id: int) -> str | None:
        """The plugin's biography for an artist, or None. 386-1005 ms against
        George's server where a photo URL is 9-23 ms (Finding 035), so this
        is never on a screen's path."""
        result = await self._ask(["musicartistinfo", "biography", 0, 1, f"artist_id:{artist_id}"])
        if not result or result.get("error"):
            return None
        biography = result.get("biography")
        return str(biography).strip() or None if biography else None

    async def album_note(self, album_id: int) -> str | None:
        """The plugin's review of a release, or None. Measured on George's
        server 2026-09-18: it answers one for albums it knows, in the same
        shape as a biography."""
        result = await self._ask(["musicartistinfo", "albumreview", 0, 1, f"album_id:{album_id}"])
        if not result or result.get("error"):
            return None
        note = result.get("albumreview")
        return str(note).strip() or None if note else None

    def forget(self) -> None:
        """Drop what is remembered - after a rescan, when every artist id may
        mean a different artist (Finding 029 §4)."""
        self._photos.clear()
