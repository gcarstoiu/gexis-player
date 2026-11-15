# SPDX-License-Identifier: GPL-3.0-or-later
"""**What a station says it is playing, as Now Playing's lines** (ADR-0180
item 4).

A station sends one line, ICY's `StreamTitle`, most often *Artist - Title*
(Finding 146: four of nine stations sent one, and one of RMF FM's two was
not in that form). It is split at its first `" - "` when both halves are
there - artist, then title - and is the title whole otherwise. A line that
only repeats the station's name, or is empty, is nothing sent.

An Ogg stream may carry its own `ARTIST` and `TITLE` instead; mpv gives
those in the same `metadata` property, and they are taken as they are.
"""
from __future__ import annotations

SEPARATOR = " - "


def split_title(line: str | None, station: str | None = None) -> tuple[str | None, str | None]:
    """`(artist, title)` from one `StreamTitle` line."""
    if not isinstance(line, str):
        return None, None
    line = " ".join(line.split())
    if not line or line in (SEPARATOR.strip(), "-") or _same(line, station):
        return None, None
    artist, sep, title = line.partition(SEPARATOR)
    artist, title = artist.strip(), title.strip()
    if sep and artist and title:
        return artist, title
    return None, line


def from_metadata(metadata, station: str | None = None) -> tuple[str | None, str | None]:
    """`(artist, title)` from mpv's `metadata` property: `icy-title` first,
    then an Ogg stream's own artist and title tags."""
    if not isinstance(metadata, dict):
        return None, None
    tags = {str(k).lower(): v for k, v in metadata.items() if isinstance(v, str)}
    if "icy-title" in tags:
        return split_title(tags["icy-title"], station)
    title = " ".join(tags.get("title", "").split()) or None
    artist = " ".join(tags.get("artist", "").split()) or None
    if title is None or _same(title, station):
        return None, None
    return artist, title


def _same(text: str, station: str | None) -> bool:
    return bool(station) and text.casefold() == " ".join(station.split()).casefold()
