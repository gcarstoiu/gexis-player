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
from dataclasses import replace
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
        sources: tuple[dict, ...] = (),
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
        #: **ADR-0086.** How each source presents itself - name, accent,
        #: status line, mark - read from the manifests at startup. Beside
        #: `capabilities` because it is the same kind of thing: static for the
        #: process, and the panel cannot draw a source without it. The three
        #: built-ins are in here on the same footing as any plugin, which is
        #: the point: the generic path is the one exercised on every boot.
        self._sources = tuple(sources)
        self._handoff_exempt_pairs = tuple(tuple(p) for p in handoff_exempt_pairs)
        self._available: dict[str, bool] = {rid: False for rid in capabilities}
        self._metadata: dict[str, TrackMetadata] = {}
        self._queues: dict[str, object] = {}
        self._active: str | None = None
        self._handoff: Handoff | None = None
        self._volume: VolumeState | None = None
        self._fixed_output = False
        self._meters = True
        self._settings_revision = 0
        self._pictures_revision = 0
        self._pairing: dict | None = None
        #: **ADR-0081: the cover the daemon found for a renderer that sent
        #: none.** `renderer_id -> (track, url)`, applied in `state` below
        #: only where the renderer's own artwork is absent. Keyed on the
        #: track, not just the renderer: held per renderer and applied blind,
        #: a found cover would attach to the *next* Bluetooth track for as
        #: long as the next lookup took, and a wrong cover on screen is worse
        #: than none (ADR-0012).
        self._found_artwork: dict[str, tuple[tuple[str, str, str], str]] = {}
        self._subscribers: list[Callable[[PlaybackState], None]] = []

    def subscribe(self, callback: Callable[[PlaybackState], None]) -> None:
        """Registered once, by the WebSocket server - not per client. The
        server itself tracks connected clients and fans a single broadcast
        out to them; sending the current state to a newly-connected client
        is the server's job (wsserver.py), not this store's.
        """
        self._subscribers.append(callback)

    @staticmethod
    def _track_of(metadata: TrackMetadata) -> tuple[str, str, str]:
        """What `_found_artwork` is keyed on - enough to say "this is still
        the same track" and nothing that ticks while it plays."""
        return (metadata.artist or "", metadata.album or "", metadata.title or "")

    @property
    def state(self) -> PlaybackState:
        metadata = self._metadata.get(self._active, BLANK_METADATA) if self._active else BLANK_METADATA
        # ADR-0081. The renderer's own cover always wins; this fills the hole
        # where there is one, and only for the track it was found for.
        if self._active and metadata.artwork is None:
            found = self._found_artwork.get(self._active)
            if found is not None and found[0] == self._track_of(metadata):
                metadata = replace(metadata, artwork=found[1])
        return PlaybackState(
            active=self._active,
            queue=self._queues.get(self._active) if self._active else None,
            available=dict(self._available),
            metadata=metadata,
            capabilities=dict(self._capabilities),
            handoff=self._handoff,
            volume=self._volume,
            fixed_output=self._fixed_output,
            meters=self._meters,
            handoff_exempt_pairs=self._handoff_exempt_pairs,
            sources=self._sources,
            settings_revision=self._settings_revision,
            pictures_revision=self._pictures_revision,
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

    def add_renderer(self, renderer_id: str, capabilities) -> None:
        """**A renderer that arrived after this store was built** (ADR-0089).

        The three built-ins are passed in at construction and never move; a
        plugin renderer connects minutes later. Until it has a slot here the
        panel cannot draw it and `set_available` refuses it by name - which is
        how the first plugin written outside this repository failed, with
        `unknown renderer 'plexamp'`, after everything else about it worked.

        Idempotent, because a plugin that reconnects is the ordinary case and
        not an error. Its availability starts **false**: connecting says the
        plugin is running, not that its renderer is ready.
        """
        if renderer_id in self._capabilities:
            return
        self._capabilities[renderer_id] = capabilities
        self._available[renderer_id] = False
        logger.info("state: %s has a slot", renderer_id)
        self._notify()

    def drop_renderer(self, renderer_id: str) -> None:
        """Its plugin went away.

        **What it leaves behind is deliberate.** The slot goes, so the panel
        stops offering a source nothing is behind; the *source description* from
        the manifest stays, because a plugin that is installed and not running
        is still installed (ADR-0086), and that is what the manifest is for.
        """
        if self._capabilities.pop(renderer_id, None) is None:
            return
        self._available.pop(renderer_id, None)
        self._metadata.pop(renderer_id, None)
        self._queues.pop(renderer_id, None)
        logger.info("state: %s no longer has a slot", renderer_id)
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

    def set_found_artwork(self, renderer_id: str, metadata: TrackMetadata, url: str | None) -> None:
        """**A cover found for a track the renderer sent none for**
        (ADR-0081). Remembered against that track, so it cannot outlive it.

        `None` forgets, which is what a lookup that found nothing says: it
        stops a previous track's cover from applying if the metadata ever
        folds back to it.
        """
        if renderer_id not in self._available:
            raise ValueError(f"unknown renderer {renderer_id!r}")
        track = self._track_of(metadata)
        was = self._found_artwork.get(renderer_id)
        if url is None:
            if was is None:
                return
            del self._found_artwork[renderer_id]
        else:
            if was == (track, url):
                return
            self._found_artwork[renderer_id] = (track, url)
        logger.info(
            "state: %s cover for %s - %s",
            "found a" if url else "forgot the",
            track[2] or "nothing playing",
            url or "",
        )
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
        if self._fixed_output:
            # ADR-0046: nothing is attenuating, so there is no level to
            # publish. Swallowed here rather than at every caller, because
            # the mirrors and the monitor all still run.
            return
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

    def set_fixed_output(self, fixed: bool) -> None:
        """ADR-0046. **The level is cleared with it**: in fixed mode there
        is no level to show, and leaving the last one published would have
        the panel hiding a slider while the mini strip still knew a
        number."""
        if fixed == self._fixed_output:
            return
        logger.info("state: output is %s", "fixed" if fixed else "variable")
        self._fixed_output = fixed
        if fixed:
            self._volume = None
        self._notify()

    def set_meters(self, available: bool) -> None:
        """ADR-0055 §6: whether this output's chain can feed the
        visualiser."""
        if available == self._meters:
            return
        logger.info("state: visualiser levels %s", "available" if available else "unavailable")
        self._meters = available
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

    def bump_pictures_revision(self) -> None:
        """The library's pictures changed under the panel.

        **Once per sweep, not once per artist.** The panel's answer is to
        drop every artist photo it is holding and ask again, which is right
        after a run and ruinous 917 times during one.
        """
        self._pictures_revision += 1
        self._notify()

    def _notify(self) -> None:
        state = self.state
        for callback in self._subscribers:
            callback(state)
