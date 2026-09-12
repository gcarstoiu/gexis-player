# SPDX-License-Identifier: GPL-3.0-or-later
"""The normalised playback model (Phase 3 criterion 1, DEVELOPMENT.md:346).

ADR-0014's seven skin fields (title, artist, album, artwork, sample rate,
remaining time, source type) plus position and duration - the minimum every
renderer adapter supplies, with absent fields left blank rather than the
screen blanked (ADR-0014's "blank that region, never the screen").

**Availability, George's decision 2026-09-12:** "backend reachable" - not
whether a renderer has a live session. LMS's CometD/JSON-RPC connection
being up, go-librespot's API responding, BlueZ being reachable with the
adapter powered - regardless of whether anything is actually playing on
that renderer right now. This is deliberately the minimum the UI needs:
only LMS ever gets an "activate" control from our own UI (Phase 4), and
`available` is what gates/explains that one control. Spotify and Bluetooth
are always taken over passively (a phone connects), so their availability
only ever feeds a status line, not a button - richer session-awareness
("is a phone actually connected right now") was explicitly deferred, not
built ahead of a criterion that would use it.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TrackMetadata:
    """One renderer's current-track metadata. All fields default to blank
    (None) - a renderer that cannot supply one (Bluetooth's artwork and
    sample rate, ADR-0014) simply omits it, and JSON serialisation turns
    that into `null` for the UI to blank, never into a placeholder value.
    """

    title: str | None = None
    artist: str | None = None
    album: str | None = None
    artwork: str | None = None
    sample_rate: int | None = None  # Hz
    position: float | None = None  # seconds
    duration: float | None = None  # seconds
    source_type: str | None = None  # renderer_id of whoever supplied this

    @property
    def remaining_time(self) -> float | None:
        if self.position is None or self.duration is None:
            return None
        return max(self.duration - self.position, 0.0)

    def to_json(self) -> dict:
        return {
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "artwork": self.artwork,
            "sample_rate": self.sample_rate,
            "remaining_time": self.remaining_time,
            "source_type": self.source_type,
            "position": self.position,
            "duration": self.duration,
        }


#: The blank metadata published when nobody holds the device (ADR-0027) -
#: every field None, matching ADR-0014's "blank the region" rule rather than
#: leaving the last active renderer's stale metadata on screen.
BLANK_METADATA = TrackMetadata()


@dataclass(frozen=True)
class PlaybackState:
    """The whole payload published over the state WebSocket."""

    #: The renderer currently holding the device, or None - a routine state
    #: since ADR-0027 removed the permanent base slot, not an error.
    active: str | None
    #: renderer_id -> reachable, independent of `active` (see module
    #: docstring). Always has an entry for every known renderer.
    available: dict[str, bool] = field(default_factory=dict)
    #: The active renderer's metadata, or BLANK_METADATA when `active` is
    #: None - there is nothing to show, not something broken.
    metadata: TrackMetadata = field(default_factory=lambda: BLANK_METADATA)

    def __post_init__(self) -> None:
        # Defensive copy: a caller mutating the dict it passed in must not
        # silently mutate an already-published state. `object.__setattr__`
        # is needed because the dataclass is frozen.
        object.__setattr__(self, "available", dict(self.available))

    def to_json(self) -> dict:
        return {
            "active": self.active,
            "available": dict(self.available),
            "metadata": self.metadata.to_json(),
        }
