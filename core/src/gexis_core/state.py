# SPDX-License-Identifier: GPL-3.0-or-later
"""Owns the current PlaybackState (model.py) and notifies subscribers -
the WebSocket server, wsserver.py - whenever it changes.

Pure aggregation, no I/O of its own: the supervisor reports `active`
changes, each adapter reports its own availability and metadata, and this
module's only job is combining those into one coherent snapshot and firing
subscribers exactly when that snapshot actually changes - not on every
adapter event, so a metadata push from a renderer that is not currently
active does not spam a broadcast nobody's screen would show.
"""
from __future__ import annotations

import logging
from typing import Callable, Mapping

from gexis_core.adapters.base import Capabilities
from gexis_core.model import (
    BLANK_METADATA,
    Handoff,
    PlaybackState,
    TrackMetadata,
    VolumeState,
)
from gexis_core.volume import raw_to_db, raw_to_slider_percent

logger = logging.getLogger("gexis_core.state")


class StateStore:
    def __init__(
        self,
        capabilities: Mapping[str, Capabilities],
        *,
        handoff_exempt_pairs: tuple[tuple[str, str], ...] = (),
    ) -> None:
        """`capabilities` is the single source of truth for which
        renderers exist (Phase 3 criterion 2) - one dict, not a separate
        renderer-id list that could drift from it. Static for the process
        lifetime: every adapter declares the same contract regardless of
        configuration, so this is captured once here rather than re-read
        per broadcast.

        `handoff_exempt_pairs` is published, not applied here (Phase 4
        criterion 4) - this store has no opinion on whether a transition
        screen is shown; it only carries the evidence-gated list the UI
        decides from.
        """
        self._capabilities = dict(capabilities)
        self._handoff_exempt_pairs = tuple(tuple(p) for p in handoff_exempt_pairs)
        self._available: dict[str, bool] = {rid: False for rid in capabilities}
        self._metadata: dict[str, TrackMetadata] = {}
        self._queues: dict[str, object] = {}
        self._active: str | None = None
        self._handoff: Handoff | None = None
        self._volume: VolumeState | None = None
        self._settings_revision = 0
        self._pairing: dict | None = None
        self._subscribers: list[Callable[[PlaybackState], None]] = []

    def subscribe(self, callback: Callable[[PlaybackState], None]) -> None:
        """Registered once, by the WebSocket server - not per client. The
        server itself tracks connected clients and fans a single broadcast
        out to them; sending the current state to a newly-connected client
        is the server's job (wsserver.py), not this store's.
        """
        self._subscribers.append(callback)

    @property
    def state(self) -> PlaybackState:
        metadata = self._metadata.get(self._active, BLANK_METADATA) if self._active else BLANK_METADATA
        return PlaybackState(
            active=self._active,
            queue=self._queues.get(self._active) if self._active else None,
            available=dict(self._available),
            metadata=metadata,
            capabilities=dict(self._capabilities),
            handoff=self._handoff,
            volume=self._volume,
            handoff_exempt_pairs=self._handoff_exempt_pairs,
            settings_revision=self._settings_revision,
            pairing=self._pairing,
        )

    def set_active(self, renderer_id: str | None) -> None:
        """Called by the supervisor whenever its own `active` changes
        (arbitration.py's `acquire`/`relinquish`) - not derived by polling,
        so this reflects a takeover the moment it happens.
        """
        if renderer_id == self._active:
            return
        logger.debug("state: active %s -> %s", self._active or "nobody", renderer_id or "nobody")
        self._active = renderer_id
        self._notify()

    def set_available(self, renderer_id: str, available: bool) -> None:
        if renderer_id not in self._available:
            raise ValueError(f"unknown renderer {renderer_id!r}")
        if self._available[renderer_id] == available:
            return
        logger.info("state: %s availability -> %s", renderer_id, available)
        self._available[renderer_id] = available
        self._notify()

    def set_queue(self, renderer_id: str, queue) -> None:
        """Recorded per renderer like metadata, and published only for
        whoever is active. Only LMS reports one (ADR-0038 §5)."""
        if self._queues.get(renderer_id) == queue:
            return
        self._queues[renderer_id] = queue
        if renderer_id == self._active:
            self._notify()

    def set_metadata(self, renderer_id: str, metadata: TrackMetadata) -> None:
        """Recorded for every renderer regardless of whether it is active -
        so that becoming active immediately has metadata to show rather
        than a blank screen for however long the first push takes - but
        only broadcast when it belongs to whoever is currently active and
        actually differs from what was last published. The equality check
        matters on its own merits (any adapter re-reporting identical data
        would otherwise spam a broadcast for nothing), but it does not
        replace fixing a renderer's own over-reporting at the source: LMS's
        `time` field ticks every second during playback, so even with this
        check a currently-playing LMS session still broadcasts on every
        genuine CometD push - see adapters/lms.py's `subscribe:0` comment
        for why those pushes are change-driven, not a fixed heartbeat.
        """
        if self._metadata.get(renderer_id) == metadata:
            return
        self._metadata[renderer_id] = metadata
        if renderer_id == self._active:
            self._notify()

    def set_handoff(self, from_renderer: str | None, to_renderer: str | None) -> None:
        """Called by the supervisor at both edges of a takeover (Phase 4
        criterion 4) - the pair when one starts, `(None, None)` when it
        finishes. Only a takeover *from* someone has a pair to report: a
        cold acquisition with nobody holding the device is not a handoff
        and publishes nothing.
        """
        handoff = (
            Handoff(from_renderer=from_renderer, to_renderer=to_renderer)
            if from_renderer is not None and to_renderer is not None
            else None
        )
        if handoff == self._handoff:
            return
        logger.info(
            "state: handoff %s",
            f"{handoff.from_renderer} -> {handoff.to_renderer}" if handoff else "finished",
        )
        self._handoff = handoff
        self._notify()

    def set_volume_raw(
        self, raw: int, *, muted: bool = False, percent: int | None = None
    ) -> None:
        """The shared hardware mixer moved (Phase 4 criterion 8). Takes the
        raw 0-240 value - the only unit the hardware actually has - and
        derives dB and slider percent (ADR-0034) here, so no caller has to
        know either scale to report a level.

        **`percent` overrides the derivation** (ADR-0053). While a renderer
        holds the device the number shown is *its* number, not one derived
        from the DAC: measured, LMS at 25 puts the DAC at -30 dB, which
        derives as 33, and George asked for 25 because 25 is what every
        other control showing that player says. `raw` and `db` stay the
        hardware's own throughout - they are facts about the DAC, and the
        drawer's dB readout is not a renderer's opinion.
        """
        volume = VolumeState(
            raw=raw,
            db=raw_to_db(raw),
            percent=raw_to_slider_percent(raw) if percent is None else percent,
            muted=muted,
        )
        if volume == self._volume:
            return
        self._volume = volume
        self._notify()

    def set_pairing(self, pairing: dict | None) -> None:
        """A Bluetooth pairing request, or None once it is answered or gone
        (ADR-0045). **Published the moment the agent asks**: the agent is
        holding BlueZ's handshake open while this travels, and the panel has
        the agent's whole window to be told, not a share of it."""
        # **A dict, not the agent's own object.** This goes straight into
        # `json.dumps` in the broadcast, where a dataclass raises and takes
        # every other state update with it until the request closes.
        if pairing is not None and not isinstance(pairing, dict):
            raise TypeError(f"pairing must be a dict, got {type(pairing).__name__}")
        if pairing == self._pairing:
            return
        self._pairing = pairing
        self._notify()

    def bump_settings_revision(self) -> None:
        self._settings_revision += 1
        self._notify()

    def _notify(self) -> None:
        state = self.state
        for callback in self._subscribers:
            callback(state)
