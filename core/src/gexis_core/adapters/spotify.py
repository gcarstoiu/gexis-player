# SPDX-License-Identifier: GPL-3.0-or-later
"""Spotify Connect adapter, via go-librespot's HTTP + WebSocket API.

Transport confirmed against devgianlu/go-librespot's own docs (API.md,
api-spec.yml) before writing this, not assumed:
  - server must be enabled in config.yml (`server.enabled: true`) - done in
    this same change, see image/stage-gexis/02-renderers/files/
    go-librespot-config.yml. Binds 127.0.0.1:3678 by default.
  - WS /events streams `{"type": "...", "data": {...}}` frames. "active"
    fires when a device is selected in the app - this is the acquisition
    event (ADR-0010's table).
  - The exact `data` shape for "active"/"inactive"/"volume" is undocumented
    upstream (checked API.md and api-spec.yml, neither gives it) - so this
    adapter only depends on `type`, never on `data`'s shape, for anything
    that must not silently break. Volume-event parsing is best-effort and
    logs loudly rather than guessing quietly if the shape doesn't match.
  - **Also acquire on "will_play" (added 2026-09-10, Finding 010's "LMS
    doesn't release to Spotify" symptom traced to a real cause, not
    guessed):** read upstream's own source (devgianlu/go-librespot
    daemon/controls.go, both the "transfer" and "play" command paths via
    loadContext -> loadCurrentTrackOrSkip -> loadCurrentTrack) to find
    that ApiEventTypeActive is emitted only *after*
    loadCurrentTrackOrSkip() returns successfully - which means it opens
    the ALSA device first. If that open fails (EBUSY, because LMS still
    holds the device - exactly gexis's case), the function returns an
    error and "active" is never emitted at all. Confirmed directly
    against gexis's own log: LMS reclaimed the device, go-librespot
    logged four consecutive "ALSA error at snd_pcm_open: Device or
    resource busy" over ~13s trying to resume a transferred session, and
    no "active" event fired until 37s after the reclaim - by which point
    the phone had given up and re-initiated the transfer from scratch.
    "will_play" (emitted in loadCurrentTrack, before any ALSA access -
    confirmed from the same source read) is upstream's own earlier,
    device-independent "about to try playing" signal - the same "control
    plane, not stream start" shape ADR-0010 already uses for the other
    two renderers, not a new kind of trade-off. Acquiring LMS's release on
    this signal instead means the ALSA device is actually free by the
    time go-librespot's own retry (or the same call, once re-entered)
    tries to open it, breaking the deadlock rather than depending on
    the phone re-initiating a fresh transfer to escape it by chance.
  - POST /player/stop disconnects the session - this is ADR-0010's
    "Spotify Connect: disconnect" release action.
  - POST /player/volume body is `{"volume": <int32>}` (confirmed from
    api-spec.yml's `setVolume` schema).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from typing import Callable

import aiohttp

from gexis_core.adapters.base import Adapter, ReleaseAction
from gexis_core.model import TrackMetadata
from gexis_core.systemd import kill_unit

logger = logging.getLogger("gexis_core.adapters.spotify")

UNIT_NAME = "go-librespot.service"


def _ms_to_s(value) -> float | None:
    return value / 1000.0 if isinstance(value, (int, float)) else None


class SpotifyAdapter(Adapter):
    renderer_id = "spotify"
    release_action = ReleaseAction.DISCONNECT
    unit_name = UNIT_NAME

    def __init__(self, host: str, port: int) -> None:
        self._base = f"http://{host}:{port}"
        self._on_volume: Callable[[int, int], None] | None = None
        self._on_metadata: Callable[[TrackMetadata], None] | None = None
        self._on_availability: Callable[[bool], None] | None = None
        self._volume_steps: int | None = None
        #: The last "metadata" event's position/duration, seconds - a "seek"
        #: event (API.md) carries a fresh position/duration but no track
        #: name/artist/album, so reporting it needs the rest of the last
        #: known metadata rather than emitting a mostly-blank update.
        self._last_metadata: TrackMetadata | None = None

    def on_volume_change(self, callback: Callable[[int, int], None]) -> None:
        """Volume bridge hooks in here: callback(value, max) fires whenever
        go-librespot reports its own volume changed (e.g. from the phone).
        """
        self._on_volume = callback

    def on_metadata_change(self, callback: Callable[[TrackMetadata], None]) -> None:
        """state.py hooks in here (Phase 3 criterion 1). Fired on go-
        librespot's own "metadata" event (a new track loaded) and "seek"
        (position moved within the same track) - API.md documents both.
        """
        self._on_metadata = callback

    def on_availability_change(self, callback: Callable[[bool], None]) -> None:
        """George's decision, 2026-09-12: "available" means go-librespot's
        API is reachable, independent of whether a Spotify Connect session
        is active. True once /events connects, False while `run()`'s outer
        loop is in its retry sleep after losing the connection.
        """
        self._on_availability = callback

    async def run(self, on_acquire, on_release) -> None:
        while True:
            try:
                await self._watch_events(on_acquire, on_release)
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
                logger.warning("spotify: /events connection lost (%s), retrying in 5s", exc)
                if self._on_availability is not None:
                    self._on_availability(False)
                await asyncio.sleep(5)

    async def _watch_events(self, on_acquire, on_release) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(f"{self._base}/events") as ws:
                logger.info("spotify: connected to %s/events", self._base)
                if self._on_availability is not None:
                    self._on_availability(True)
                async for msg in ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue
                    try:
                        frame = msg.json()
                    except ValueError:
                        logger.warning("spotify: non-JSON event frame: %r", msg.data)
                        continue
                    event_type = frame.get("type")
                    if event_type == "active":
                        logger.info("spotify: device became active (acquisition)")
                        on_acquire()
                    elif event_type == "will_play":
                        logger.info("spotify: will_play (acquisition, ahead of ALSA open)")
                        on_acquire()
                    elif event_type == "inactive":
                        # George, 2026-09-12: found live via the state
                        # WebSocket - a Spotify disconnect never told the
                        # supervisor, so `active`/metadata stayed pointed
                        # at Spotify indefinitely instead of going back to
                        # "nobody" (ADR-0027). An oversight in the
                        # original ADR-0027 work, not a deliberate
                        # deferral - fixed by reporting API.md's own
                        # "inactive" event. Safe to call unconditionally:
                        # Supervisor.relinquish() ignores this unless
                        # spotify is still the active renderer, so the
                        # echo of our own takeover-driven /player/stop
                        # (which fires this same event) is a no-op.
                        logger.info("spotify: device became inactive (release)")
                        on_release()
                    elif event_type == "volume":
                        self._handle_volume_event(frame.get("data") or {})
                    elif event_type == "metadata":
                        self._handle_metadata_event(frame.get("data") or {})
                    elif event_type == "seek":
                        self._handle_seek_event(frame.get("data") or {})

    def _handle_metadata_event(self, data: dict) -> None:
        if self._on_metadata is None:
            return
        metadata = TrackMetadata(
            title=data.get("name"),
            artist=", ".join(data["artist_names"]) if data.get("artist_names") else None,
            album=data.get("album_name"),
            artwork=data.get("album_cover_url"),
            sample_rate=data.get("sample_rate"),
            position=_ms_to_s(data.get("position")),
            duration=_ms_to_s(data.get("duration")),
            source_type="spotify",
        )
        self._last_metadata = metadata
        self._on_metadata(metadata)

    def _handle_seek_event(self, data: dict) -> None:
        # API.md: "seek" carries only context_uri/uri/position/duration/
        # play_origin - not name/artist/album, so this replaces just the
        # timing on top of the last "metadata" event rather than reporting
        # a mostly-blank update.
        if self._on_metadata is None or self._last_metadata is None:
            return
        metadata = replace(
            self._last_metadata,
            position=_ms_to_s(data.get("position")),
            duration=_ms_to_s(data.get("duration")),
        )
        self._last_metadata = metadata
        self._on_metadata(metadata)

    def _handle_volume_event(self, data: dict) -> None:
        if self._on_volume is None:
            return
        try:
            value, max_ = data["value"], data["max"]
        except (KeyError, TypeError):
            logger.warning(
                "spotify: 'volume' event data didn't have the expected "
                "value/max fields (%r) - upstream shape may have changed, "
                "not guessing further",
                data,
            )
            return
        self._on_volume(value, max_)

    async def release(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self._base}/player/stop") as resp:
                    return resp.status < 300
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logger.warning("spotify: /player/stop failed: %s", exc)
            return False

    async def get_volume_steps(self) -> int:
        """go-librespot's own volume scale (its /status "volume_steps"
        field), cached after the first successful read - queried rather
        than hardcoded, same reasoning as never hardcoding an ALSA card
        index: it's the renderer's own value, not ours to assume.
        """
        if self._volume_steps is not None:
            return self._volume_steps
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self._base}/status") as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    self._volume_steps = int(data["volume_steps"])
                    return self._volume_steps
        except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, ValueError) as exc:
            logger.warning("spotify: /status volume_steps read failed (%s), assuming 65535", exc)
            return 65535

    async def set_volume(self, value: int) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(f"{self._base}/player/volume", json={"volume": value})
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logger.warning("spotify: /player/volume failed: %s", exc)

    # device_freed was overridden here, 2026-09-11 through 2026-09-11
    # (Finding 014, ADR-0010's matching amendment): POST /player/resume
    # rescued the ALSA-open race (go-librespot losing to LMS's polite
    # release) reliably in this session's own testing (three-for-three
    # manual rescues, then a clean 5/5 and 16/20 batch through the real
    # supervisor path). **Reverted the same day**, live hardware use
    # found a worse failure it didn't catch in testing: /player/resume
    # can get go-librespot to genuinely resume local ALSA playback
    # without going through the Spotify Connect handshake that emits the
    # "active" WS event - confirmed directly in gexis-core's own log,
    # several acquisitions in a row showed "will_play" and real audio
    # but never "device became active". Spotify's own app then shows
    # "gexis disconnected" while audio is genuinely playing, and a
    # remote "next" command routes to the phone instead of gexis - ADR-
    # 0010's own core rule violated ("never show a state the user cannot
    # account for"), and worse than the race it fixed (a slow/racy first
    # attempt is at least a state the user can account for - nothing
    # audible happens for a bit). Back to the pre-Finding-014 behavior
    # (inherited no-op) until a fix is found that doesn't bypass the
    # Connect handshake - see Finding 014's own follow-up note.

    async def signal_stop(self, force: bool) -> None:
        # Ignores `force` on purpose, same reasoning and same regression
        # shape as LmsAdapter (see its class-level comment): go-librespot
        # exits *cleanly* on SIGTERM (exit 0), which `Restart=on-failure`
        # never counts as a failure, so it never comes back on its own -
        # reproduced live 2026-09-08, "Spotify Connect died and didn't
        # restart" after an LMS takeover escalated past SIGTERM. Normally
        # the ladder should not even reach here: release()'s own
        # `/player/stop` frees the device in <100ms (adapters/base.py's
        # release_ladder comment). It escalated this time chiefly because
        # of the device_held_by bug fixed alongside this - but *if* it
        # ever legitimately needs to escalate, SIGKILL is the only signal
        # that reliably brings the unit back.
        kill_unit(UNIT_NAME, force=True)
