# SPDX-License-Identifier: GPL-3.0-or-later
"""The visualisation service as a process (ADR-0011, Phase 5 criterion 1).

Its own systemd unit rather than part of `gexis-core`: it polls at 30 Hz for
as long as audio plays, and the state daemon's job is to stay responsive to
events, not to share a hot loop with it.

Three transports, one reader:

- **WebSocket** `/meter` — our UI and anything remote.
- **PeppyMeter HTTP** — `PUT {left,right,mono}` to a PeppyMeter web server,
  which is the only push shape upstream accepts (`vumeterhandler.py`).
  Configured off by default; it exists so an unmodified PeppyMeter elsewhere
  can be fed without touching this service.
- **Passthrough FIFOs** — what our own vendored PeppyMeter reads.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

import aiohttp
from aiohttp import web

from gexis_core.config import Config
from gexis_core.meters import (
    FifoPassthrough,
    FifoSource,
    Levels,
    attenuate,
    read_attenuation,
)

logger = logging.getLogger("gexis_core.meter_service")


class MeterServer:
    def __init__(self, source: FifoSource, *, passthrough: FifoPassthrough | None = None,
                 http_target: str = "", interval: float = 1 / 30,
                 attenuation_path: Path | None = None) -> None:
        self._source = source
        self._passthrough = passthrough
        self._http_target = http_target
        self._interval = interval
        #: ADR-0057. The dB the device is cutting right now, left by the
        #: daemon. Re-read only when the file changes: it is written on every
        #: hardware level change, and this loop runs 30 times a second.
        self._attenuation_path = attenuation_path
        self._attenuation_seen: tuple[int, int] | None = None
        self._attenuation = 0.0
        self._clients: set[web.WebSocketResponse] = set()
        self._session: aiohttp.ClientSession | None = None

    def make_app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/meter", self._handle)
        return app

    async def _handle(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._clients.add(ws)
        logger.info("meter: client connected (%d total)", len(self._clients))
        try:
            async for _ in ws:
                pass  # publish-only, like /state (ADR-0028)
        finally:
            self._clients.discard(ws)
        return ws

    async def publish(self, levels: Levels) -> None:
        if self._passthrough is not None:
            self._passthrough.publish(levels)
        if self._clients:
            payload = json.dumps(levels.to_json())
            for ws in list(self._clients):
                try:
                    await ws.send_str(payload)
                except (ConnectionResetError, RuntimeError):
                    self._clients.discard(ws)
        if self._http_target and self._session is not None:
            try:
                await self._session.put(
                    self._http_target,
                    json={"left": levels.left, "right": levels.right, "mono": levels.mono},
                    timeout=aiohttp.ClientTimeout(total=self._interval),
                )
            except (aiohttp.ClientError, asyncio.TimeoutError):
                pass  # a display that is not listening must not slow the loop

    def attenuation(self) -> float:
        """How much the device is attenuating, in dB."""
        if self._attenuation_path is None:
            return 0.0
        try:
            stat = os.stat(self._attenuation_path)
        except OSError:
            return 0.0
        key = (stat.st_mtime_ns, stat.st_size)
        if key != self._attenuation_seen:
            self._attenuation_seen = key
            self._attenuation = read_attenuation(self._attenuation_path)
        return self._attenuation

    async def run_loop(self) -> None:
        self._session = aiohttp.ClientSession() if self._http_target else None
        try:
            while True:
                await self.publish(attenuate(self._source.read(), self.attenuation()))
                await asyncio.sleep(self._interval)
        finally:
            if self._session is not None:
                await self._session.close()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = Config.load()
    source = FifoSource(config.meter_fifo, config.spectrum_fifo, bands=config.spectrum_bands)
    passthrough = FifoPassthrough(
        config.meter_passthrough,
        config.spectrum_passthrough,
        spectrum_consumer_config=config.spectrum_consumer_config,
    )
    server = MeterServer(
        source,
        passthrough=passthrough,
        http_target=config.meter_http_target,
        interval=1 / config.meter_frame_rate,
        attenuation_path=Path(config.attenuation_path),
    )
    runner = web.AppRunner(server.make_app())
    await runner.setup()
    await web.TCPSite(runner, config.state_host, config.meter_port).start()
    logger.info("meter: listening on ws://%s:%d/meter", config.state_host, config.meter_port)
    try:
        await server.run_loop()
    finally:
        source.close()
        passthrough.close()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
