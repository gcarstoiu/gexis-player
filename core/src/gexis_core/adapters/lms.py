"""LMS (base slot) adapter, per ARCHITECTURE.md §8: "CometD subscribe for
push; JSON-RPC on :9000 for calls."

`/jsonrpc.js` (`{"method": "slim.request", "params": [playerid,
[cmd, ...]]}`) is a stable, widely-documented interface. `players 0 99`
enumerates connected players so the adapter finds squeezelite's playerid
by name (`-n gexis` in squeezelite.service) rather than hardcoding a MAC -
matching the project's standing "never hardcode an identifier that
differs across machines" rule (applied elsewhere to ALSA card indices).

**CometD subscription confirmed live, 2026-09-06.** The earlier "LMS
unreachable" note in HANDOFF.md was a false negative - a bare GET to
`/jsonrpc.js` with no body times out (LMS presumably only handles POST
there), which is what the original reachability check used. A real POST
proved the server was reachable all along, and running this adapter's
`run()` against it end-to-end - handshake, `/slim/subscribe`, then
triggering real playback (`playlist play <url>`) on the live "gexis"
player - produced a genuine `mode -> play` push within 4 seconds and
fired `on_acquire()`. **Not independently reconfirmed:** whether
`release()`'s `pause` call takes effect within any particular time bound
- the JSON-RPC call itself returned success, but the test that exercised
it moved on to clearing the playlist before checking the player's mode
again, so pause's timing specifically wasn't isolated. The acquisition
path (the part criterion 3 actually needs) is the one that was watched
end-to-end.
"""
from __future__ import annotations

import asyncio
import itertools
import logging

import aiohttp

from gexis_core.adapters.base import Adapter, ReleaseAction
from gexis_core.arbitration import TimeoutLadder
from gexis_core.systemd import kill_unit

logger = logging.getLogger("gexis_core.adapters.lms")

UNIT_NAME = "squeezelite.service"

_id_counter = itertools.count(1)


class LmsAdapter(Adapter):
    renderer_id = "lms"
    release_action = ReleaseAction.PAUSE

    # George's decision, 2026-09-06, from the release-timing measurement
    # above `release()`'s docstring: don't wait out squeezelite's `-C`
    # idle timer at all. `polite_grace=0` means the supervisor checks
    # once right after the pause call and, finding the device still
    # held (expected - pause alone never releases it in any UI-tolerable
    # time), escalates to SIGTERM immediately rather than sleeping first.
    # sigterm/sigkill grace are left at the supervisor's defaults -
    # only the "wait and hope -C helps" step is being skipped, not the
    # confirmation that a sent signal actually worked.
    release_ladder = TimeoutLadder(polite_grace=0.0)

    def __init__(self, host: str, port: int, player_name: str) -> None:
        self._base = f"http://{host}:{port}"
        self._player_name = player_name
        self._player_id: str | None = None

    async def _rpc(self, session: aiohttp.ClientSession, player: str, command: list) -> dict:
        body = {"id": next(_id_counter), "method": "slim.request", "params": [player, command]}
        async with session.post(f"{self._base}/jsonrpc.js", json=body) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _resolve_player_id(self, session: aiohttp.ClientSession) -> str:
        result = await self._rpc(session, "", ["players", 0, 99])
        players = result.get("result", {}).get("players_loop", [])
        for player in players:
            if player.get("name") == self._player_name:
                return player["playerid"]
        raise RuntimeError(
            f"lms: no player named {self._player_name!r} found in {players!r}"
        )

    async def run(self, on_acquire) -> None:
        while True:
            try:
                await self._watch(on_acquire)
            except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as exc:
                logger.warning("lms: connection/subscription failed (%s), retrying in 5s", exc)
                await asyncio.sleep(5)

    async def _watch(self, on_acquire) -> None:
        async with aiohttp.ClientSession() as session:
            if self._player_id is None:
                self._player_id = await self._resolve_player_id(session)
                logger.info("lms: resolved player %r to id %s", self._player_name, self._player_id)

            client_id = await self._cometd_handshake(session)
            response_channel = f"/{client_id}/slim/playerstatus/{self._player_id}"

            # Subscribe on the Bayeux side to the channel LMS will publish
            # status pushes to...
            await self._cometd_post(
                session,
                {
                    "channel": "/meta/subscribe",
                    "clientId": client_id,
                    "subscription": response_channel,
                    "id": str(next(_id_counter)),
                },
            )
            # ...then tell LMS, via its own request/response convention, to
            # start pushing this player's status to that channel.
            await self._cometd_post(
                session,
                {
                    "channel": "/slim/subscribe",
                    "clientId": client_id,
                    "data": {
                        "response": response_channel,
                        "request": [self._player_id, ["status", "-", 1, "subscribe:1"]],
                    },
                    "id": str(next(_id_counter)),
                },
            )
            logger.info("lms: subscribed to %s", response_channel)

            last_mode: str | None = None
            while True:
                frames = await self._cometd_post(
                    session,
                    {
                        "channel": "/meta/connect",
                        "clientId": client_id,
                        "connectionType": "long-polling",
                        "id": str(next(_id_counter)),
                    },
                    timeout=aiohttp.ClientTimeout(total=90),
                )
                for frame in frames:
                    if frame.get("channel") != response_channel:
                        continue
                    mode = (frame.get("data") or {}).get("mode")
                    if mode == "play" and last_mode != "play":
                        logger.info("lms: player mode -> play (acquisition)")
                        on_acquire()
                    last_mode = mode

    async def _cometd_handshake(self, session: aiohttp.ClientSession) -> str:
        frames = await self._cometd_post(
            session,
            {
                "channel": "/meta/handshake",
                "version": "1.0",
                "supportedConnectionTypes": ["long-polling"],
                "id": str(next(_id_counter)),
            },
        )
        frame = frames[0]
        if not frame.get("successful"):
            raise RuntimeError(f"lms: CometD handshake failed: {frame}")
        return frame["clientId"]

    async def _cometd_post(self, session, message: dict, timeout=None) -> list:
        kwargs = {"timeout": timeout} if timeout else {}
        async with session.post(f"{self._base}/cometd", json=[message], **kwargs) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def release(self) -> bool:
        if self._player_id is None:
            return False
        async with aiohttp.ClientSession() as session:
            try:
                await self._rpc(session, self._player_id, ["pause", 1])
                return True
            except aiohttp.ClientError as exc:
                logger.warning("lms: pause call failed: %s", exc)
                return False

    async def signal_stop(self, force: bool) -> None:
        kill_unit(UNIT_NAME, force=force)
