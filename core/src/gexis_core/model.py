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

from gexis_core.adapters.base import TRANSPORT_COMMANDS, Capabilities


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
    #: The album's release year, as the library reports it. LMS carries one
    #: per track (songinfo tag `y`) and it is the library's own answer, so it
    #: is preferred over enrichment's `released` - which describes the
    #: *release* a lookup matched and can differ: a 1996 track on a 2025
    #: compilation reports 2025 there and 1996 here. Spotify and Bluetooth
    #: publish nothing, so the panel falls back to enrichment for those.
    year: str | None = None
    artwork: str | None = None
    sample_rate: int | None = None  # Hz
    position: float | None = None  # seconds
    duration: float | None = None  # seconds
    source_type: str | None = None  # renderer_id of whoever supplied this
    #: playing / paused / stopped, normalised across the three renderers'
    #: very different vocabularies (LMS's `mode`, go-librespot's event
    #: names, BlueZ's `MediaPlayer1.Status`). Phase 4 criterion 3 needs a
    #: paused state to be visibly distinguishable; nothing published it
    #: before 4a.
    #:
    #: It lives on this object rather than beside it because every
    #: adapter reports it in the same event that carries the track fields
    #: - one callback, one dedup, one publish path - and because moOde's
    #: own flat metadata record does the same (`state=` alongside
    #: `artist=`), which metadata_file.py already mirrors.
    transport: str | None = None
    #: Codec name for renderers whose sample rate would be misleading -
    #: Bluetooth only, today. ADR-0019: "the decode rate is the codec's,
    #: not the source's. '44.1 kHz' beside a lossy stream is true and
    #: misleading at once." Published *beside* `sample_rate` rather than
    #: shoved into it: which one a screen shows is a presentation
    #: decision (Phase 4 criterion 3 puts the codec in the sample-rate
    #: field's place for Bluetooth), not a reason to make one field hold
    #: two types.
    codec: str | None = None
    #: Declared transport commands that cannot work right now (ADR-0037 §2's
    #: "can now" layer): LMS's next and previous on a one-item playlist,
    #: which only restart the stream (Finding 028). Not published inside
    #: `metadata`; `PlaybackState.controls` turns it into what is available.
    unavailable: frozenset[str] = frozenset()
    #: The renderer's own shuffle and repeat, for a renderer that declares
    #: them (ADR-0037): shuffle on/off, repeat "off" / "all" / "one". None
    #: for a renderer with no such thing. Published under `controls`.
    shuffle: bool | None = None
    repeat: str | None = None

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
            "year": self.year,
            "artwork": self.artwork,
            "sample_rate": self.sample_rate,
            "codec": self.codec,
            "remaining_time": self.remaining_time,
            "source_type": self.source_type,
            "position": self.position,
            "duration": self.duration,
            "transport": self.transport,
        }


#: The blank metadata published when nobody holds the device (ADR-0027) -
#: every field None, matching ADR-0014's "blank the region" rule rather than
#: leaving the last active renderer's stale metadata on screen.
BLANK_METADATA = TrackMetadata()

@dataclass(frozen=True)
class Handoff:
    """A takeover in flight (Phase 4 criterion 4).

    The *pair* is the point, not just "something is happening": whether the
    UI shows a transition state at all is decided per pair on measured
    evidence (ADR-0010's "Handoff transition screen"), so the screen cannot
    make that decision without knowing which two renderers are involved.
    """

    from_renderer: str
    to_renderer: str

    def to_json(self) -> dict:
        return {"from": self.from_renderer, "to": self.to_renderer}


@dataclass(frozen=True)
class VolumeState:
    """The shared hardware mixer's level (Phase 4 criterion 8, ADR-0034).

    `percent` is the panel slider's position over -45..0dB, which is what a
    screen shows; `raw` and `db` are the hardware's own units.
    """

    raw: int
    db: float
    percent: int
    muted: bool = False

    def to_json(self) -> dict:
        return {"percent": self.percent, "raw": self.raw, "db": self.db, "muted": self.muted}


@dataclass(frozen=True)
class Queue:
    """What the active renderer has queued up, for the queue rail on now
    playing (ADR-0038 §1, design/data-contract.md).

    LMS only: the other two renderers hand us a stream and have no queue
    (`design/README.md`'s source table). `name`/`id` are the playlist it was
    loaded from, when it was - LMS reports them until the queue is changed,
    and `modified` says it has been (Finding 029 §7), which is what lets the
    rail say "from this playlist" honestly.
    """

    items: tuple[TrackMetadata, ...] = ()
    #: Which of `items` is playing.
    index: int = 0
    name: str | None = None
    id: int | None = None
    modified: bool = False

    def to_json(self) -> dict:
        return {
            "items": [item.to_json() for item in self.items],
            "index": self.index,
            "name": self.name,
            "id": self.id,
            "modified": self.modified,
        }


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
    #: renderer_id -> its declared contract (Phase 3 criterion 2,
    #: ADR-0013). Static for the process lifetime - included in every
    #: broadcast anyway (cheap, unchanging) rather than split into a
    #: separate one-off message, so a client never has to remember state
    #: from two different message shapes to render anything.
    capabilities: dict[str, Capabilities] = field(default_factory=dict)
    #: A takeover in flight, or None. Criterion 4's transition state.
    handoff: Handoff | None = None
    #: The shared hardware mixer's level, or None before it has been read
    #: once (a real startup window, not an error).
    volume: VolumeState | None = None
    #: Renderer pairs whose measured takeover gap is fast enough that a
    #: transition state would be a flicker rather than information
    #: (ADR-0010: threshold 1s, currently same-rate LMS<->Spotify at
    #: 224.6/335.2ms medians, Finding 020). **Published rather than
    #: hardcoded in the UI** because the criterion is explicit that this
    #: is "data, not a constant" - a pair earns exemption by being
    #: measured and loses it if a later measurement moves it back.
    handoff_exempt_pairs: tuple[tuple[str, str], ...] = ()
    #: Bumped on every settings write (ADR-0035); a client refetches
    #: `GET /settings` when it moves.
    settings_revision: int = 0
    #: The active renderer's queue, or None where it has no such thing.
    queue: Queue | None = None
    #: A Bluetooth pairing request waiting for an answer, or None
    #: (ADR-0045). Published here rather than on a channel of its own
    #: because the panel already subscribes to this and a request has to
    #: reach it within the agent's thirty seconds - and because the frame
    #: is dismissed by this going away, not by the panel's own countdown
    #: reaching zero.
    pairing: dict | None = None

    @property
    def controls(self) -> dict | None:
        """ADR-0037 §2: the active renderer's transport commands that would
        work now - declared, minus what it reports unavailable. None when
        nobody is active."""
        if self.active is None or self.active not in self.capabilities:
            return None
        declared = self.capabilities[self.active].controls & TRANSPORT_COMMANDS
        return {
            "available": sorted(declared - self.metadata.unavailable),
            "shuffle": self.metadata.shuffle if "shuffle" in declared else None,
            "repeat": self.metadata.repeat if "repeat" in declared else None,
        }

    def __post_init__(self) -> None:
        # Defensive copy: a caller mutating the dict it passed in must not
        # silently mutate an already-published state. `object.__setattr__`
        # is needed because the dataclass is frozen.
        object.__setattr__(self, "available", dict(self.available))
        object.__setattr__(self, "capabilities", dict(self.capabilities))
        object.__setattr__(
            self, "handoff_exempt_pairs", tuple(tuple(p) for p in self.handoff_exempt_pairs)
        )

    def to_json(self) -> dict:
        return {
            "active": self.active,
            "available": dict(self.available),
            "metadata": self.metadata.to_json(),
            "capabilities": {rid: cap.to_json() for rid, cap in self.capabilities.items()},
            "handoff": self.handoff.to_json() if self.handoff else None,
            "volume": self.volume.to_json() if self.volume else None,
            "handoff_exempt_pairs": [list(pair) for pair in self.handoff_exempt_pairs],
            "settings_revision": self.settings_revision,
            "controls": self.controls,
            "queue": self.queue.to_json() if self.queue else None,
            "pairing": self.pairing,
        }
