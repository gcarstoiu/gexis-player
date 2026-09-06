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
  - POST /player/stop disconnects the session - this is ADR-0010's
    "Spotify Connect: disconnect" release action.
  - POST /player/volume body is `{"volume": <int32>}` (confirmed from
    api-spec.yml's `setVolume` schema).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable

import aiohttp

from gexis_core.adapters.base import Adapter, ReleaseAction
from gexis_core.systemd import kill_unit

logger = logging.getLogger("gexis_core.adapters.spotify")

UNIT_NAME = "go-librespot.service"


class SpotifyAdapter(Adapter):
    renderer_id = "spotify"
    release_action = ReleaseAction.DISCONNECT

    def __init__(self, host: str, port: int) -> None:
        self._base = f"http://{host}:{port}"
        self._on_volume: Callable[[int, int], None] | None = None
        self._volume_steps: int | None = None

    def on_volume_change(self, callback: Callable[[int, int], None]) -> None:
        """Volume bridge hooks in here: callback(value, max) fires whenever
        go-librespot reports its own volume changed (e.g. from the phone).
        """
        self._on_volume = callback

    async def run(self, on_acquire) -> None:
        while True:
            try:
                await self._watch_events(on_acquire)
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
                logger.warning("spotify: /events connection lost (%s), retrying in 5s", exc)
                await asyncio.sleep(5)

    async def _watch_events(self, on_acquire) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(f"{self._base}/events") as ws:
                logger.info("spotify: connected to %s/events", self._base)
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
                    elif event_type == "volume":
                        self._handle_volume_event(frame.get("data") or {})

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

    async def signal_stop(self, force: bool) -> None:
        kill_unit(UNIT_NAME, force=force)
