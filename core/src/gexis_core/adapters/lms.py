# SPDX-License-Identifier: GPL-3.0-or-later
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
from gexis_core.systemd import kill_unit

logger = logging.getLogger("gexis_core.adapters.lms")

UNIT_NAME = "squeezelite.service"

_id_counter = itertools.count(1)


class LmsAdapter(Adapter):
    renderer_id = "lms"
    release_action = ReleaseAction.PAUSE
    unit_name = UNIT_NAME

    # No release_ladder override - -C 1 on squeezelite.service (measured
    # ~700ms release against a commanded pause) makes the supervisor's
    # default 3s polite grace work fine for LMS in the ordinary case,
    # same as every other adapter. See ADR-0010's amended implementation
    # note for the two reverted attempts that preceded this.
    #
    # signal_stop's escalation mechanism has gone through a full
    # revert-then-restore-then-revert since, for two different reasons -
    # both still relevant to why it looks like this:
    #
    # 2026-09-07/08: plain SIGTERM doesn't work at all - squeezelite exits
    # *cleanly* on it (exit 0), which Restart=on-failure never counts as
    # a failure, so it never came back. Fixed by sending SIGKILL
    # regardless of the ladder rung that called this - an uncaught fatal
    # signal always counts as a failure, so Restart=on-failure fires.
    #
    # 2026-09-11 (Finding 013 §1's recurrence, same day): SIGKILL solved
    # "doesn't come back" but introduced a worse problem - Restart=on-
    # failure then restarts squeezelite immediately and automatically,
    # racing squeezelite's own ALSA-open startup test against whoever
    # just took the device over, independently of anything the
    # arbitration ladder itself is doing, exhausting even a raised
    # StartLimitBurst under heavy churn. Tried `stop_unit` (suppresses
    # automatic restart entirely) plus an explicit `restart_after_release`
    # bringing squeezelite back once, under this code's own timing -
    # unit-tested, then hardware-verified clean across 35 real rounds
    # the same day. **Reverted the same day anyway**: live use afterward
    # (rapid Bluetooth reconnect churn) reproduced the exact residual risk
    # that fix's own docs already named - the one explicit restart lost
    # its own race against the still-busy device, `Restart=on-failure`
    # (never actually disabled, just no longer the *first* path) took
    # over from there, and the burst limit tripped again regardless.
    # Back to plain SIGKILL + `Restart=on-failure` (the well-tested,
    # if imperfect, prior behaviour) until a design that survives real
    # churn - not just a clean scripted batch - is found. See Finding
    # 013 §1's own follow-up note and ADR-0010's matching amendment.

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

            # Seed with the *actual* current mode, not None. The
            # subscription (`subscribe:1`) pushes on any status field
            # changing - volume included, not just play/pause - and
            # each push's `mode` is just whatever mode currently is, not
            # a statement that it just changed. Starting from None meant
            # the first push after *any* reconnect (network blip, LMS
            # restart, or just this being a fresh process) would read as
            # a fresh "-> play" edge if the player happened to already
            # be playing - and fire a real, wrong acquisition if some
            # other renderer currently held the device. Root-caused,
            # 2026-09-07, from George's report of an LMS app volume
            # button press taking over an active Spotify session -
            # volume is exactly the kind of unrelated field change that
            # would trigger this via `subscribe:1`.
            status = await self._rpc(session, self._player_id, ["status", "-", 1])
            last_mode = status.get("result", {}).get("mode")

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
                        # Debounce, found necessary on hardware, 2026-09-08:
                        # while paused for arbitration (not powered off -
                        # ADR-0010's PAUSE action stays connected), LMS's
                        # own mode intermittently reports "play" for well
                        # under a second before reverting - observed
                        # correlated with squeezelite's own retried
                        # `alsa_open` against a device another renderer
                        # currently holds (e.g. mid-Spotify-playback), not
                        # with anything the user did. Firing on_acquire()
                        # on the raw push repeatedly yanked the device back
                        # from Spotify every time this happened - "shows
                        # connected but never actually takes over".
                        # Re-confirming via a fresh RPC status query after
                        # a short wait filters the transient case: a real
                        # user-initiated play stays "play" past this
                        # window, a bounce does not. Costs ~0.4s of extra
                        # latency on every genuine LMS acquisition.
                        await asyncio.sleep(0.4)
                        confirm = await self._rpc(session, self._player_id, ["status", "-", 1])
                        confirmed_mode = confirm.get("result", {}).get("mode")
                        if confirmed_mode != "play":
                            logger.debug(
                                "lms: mode->play did not hold past debounce (now %r), "
                                "not treating as acquisition",
                                confirmed_mode,
                            )
                            last_mode = confirmed_mode
                            continue
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
        # Ignores `force` on purpose - see the class-level comment.
        # SIGTERM is a no-op against squeezelite ever coming back on its
        # own, so both ladder rungs use SIGKILL. The second call, if the
        # ladder ever reaches it, is a harmless no-op against an
        # already-dead process. restart_after_release was tried and
        # reverted here the same day - see the class-level comment;
        # Restart=on-failure is what brings squeezelite back again now.
        kill_unit(UNIT_NAME, force=True)
