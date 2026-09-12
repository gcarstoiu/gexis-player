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
from gexis_core.model import BLANK_METADATA, PlaybackState, TrackMetadata

logger = logging.getLogger("gexis_core.state")


class StateStore:
    def __init__(self, capabilities: Mapping[str, Capabilities]) -> None:
        """`capabilities` is the single source of truth for which
        renderers exist (Phase 3 criterion 2) - one dict, not a separate
        renderer-id list that could drift from it. Static for the process
        lifetime: every adapter declares the same contract regardless of
        configuration, so this is captured once here rather than re-read
        per broadcast.
        """
        self._capabilities = dict(capabilities)
        self._available: dict[str, bool] = {rid: False for rid in capabilities}
        self._metadata: dict[str, TrackMetadata] = {}
        self._active: str | None = None
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
            available=dict(self._available),
            metadata=metadata,
            capabilities=dict(self._capabilities),
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

    def _notify(self) -> None:
        state = self.state
        for callback in self._subscribers:
            callback(state)
