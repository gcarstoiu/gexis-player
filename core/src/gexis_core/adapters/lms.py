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

    # ADR-0027, 2026-09-12: this adapter no longer fights squeezelite for
    # the ALSA device. The player's own LMS *power* state is the
    # arbitration mechanism - `pause` then `power 0` on release, and
    # powering on is the acquisition.
    #
    # Why, in one measurement: a commanded pause takes 1.44s to actually
    # free the device (`-C 1`'s idle timer dominating), while go-librespot
    # attempts its ALSA open about a second after its own acquisition
    # event - so Spotify lost that race every time, retried, and never
    # emitted the `active` event that tells its app the session is real.
    # Powering the player off frees the device in 0.06-0.11s, which wins
    # the race outright. Full evidence and the six approaches that were
    # measured and rejected first: Finding 018.
    #
    # `signal_stop` below is now only an escalation safety net that
    # normal operation never reaches, and the SIGKILL-not-SIGTERM point it
    # encodes remains true if it ever is reached: squeezelite exits
    # *cleanly* on SIGTERM (exit 0), which `Restart=on-failure` never
    # counts as a failure, so it would not come back. That was confirmed
    # twice, including a live reproduction from the ladder's own genuine
    # escalation. Two attempts to route around the same problem by
    # stopping and explicitly restarting the unit were shipped and
    # reverted within a day each (restart storms under real Bluetooth
    # churn) - see ADR-0010's implementation note and Finding 013 §1
    # before proposing a third.

    def __init__(self, host: str, port: int, player_name: str) -> None:
        self._base = f"http://{host}:{port}"
        self._player_name = player_name
        self._player_id: str | None = None
        #: Set by `release()` from the player's own state, consumed by
        #: `device_freed()`. False means "came back paused, send nothing".
        self._resume_playing = False

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

    async def run(self, on_acquire, on_release) -> None:
        while True:
            try:
                await self._watch(on_acquire, on_release)
            except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as exc:
                logger.warning("lms: connection/subscription failed (%s), retrying in 5s", exc)
                await asyncio.sleep(5)

    async def _watch(self, on_acquire, on_release) -> None:
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

            # Seed with the player's *actual* current power state, so the
            # first push after connecting isn't read as a fresh edge. The
            # same trap as the old mode-based seeding: a subscription push
            # carries whatever the value currently is, not a statement that
            # it just changed, so starting from None made the first push
            # after any reconnect look like a transition and fire a real,
            # wrong acquisition.
            #
            # Watching `power` rather than `mode` is ADR-0027's acquisition
            # change, and it retires the 0.4s debounce that used to sit
            # here. That debounce existed because LMS's `mode` bounces to
            # "play" on its own while a player is paused for arbitration -
            # the spurious-reclaim problem in Findings 009/010 - which
            # meant re-confirming every edge with a second RPC and paying
            # 0.4s of latency on every genuine acquisition. `power` does
            # not bounce that way, so the whole mechanism goes.
            status = await self._rpc(session, self._player_id, ["status", "-", 1])
            last_power = status.get("result", {}).get("power")

            # If the player is *already* on when we start watching, it has
            # already met this adapter's acquisition condition - so say so,
            # rather than leaving the supervisor believing nobody holds the
            # device. Without this, the first takeover after a daemon start
            # would find no outgoing renderer to release and hand Spotify a
            # device squeezelite was still holding, which is precisely the
            # race ADR-0027 exists to win. The old base-slot model dodged
            # this by assuming LMS was current at all times; with the base
            # slot gone the startup state has to be read, not assumed.
            if last_power:
                logger.info("lms: player already powered on at startup (acquisition)")
                on_acquire()

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
                    power = (frame.get("data") or {}).get("power")
                    if power is None:
                        continue
                    if power and not last_power:
                        # ADR-0027: activating the player is the
                        # acquisition. Play is a separate intention
                        # afterwards - if the user left it playing, the
                        # resume is replayed in device_freed() below,
                        # once the device is actually free.
                        logger.info("lms: player powered on (acquisition)")
                        on_acquire()
                    elif last_power and not power:
                        # Either the user deactivated the player, or this
                        # is the echo of our own release. The supervisor
                        # tells them apart by whether we are still the
                        # active renderer - see Supervisor.relinquish.
                        logger.info("lms: player powered off")
                        on_release()
                    last_power = power

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
        """ADR-0027: record the transport state, pause, then power off.

        The pause is not redundant with the power-off, and the order
        matters. Powering off a *playing* player makes LMS restore it as
        playing when it comes back, which fires squeezelite's ALSA open
        58ms later - long before we are told anything - against a device
        the incoming renderer has not released yet. That attempt fails and
        squeezelite then waits out a fixed, untunable 5s retry tick.
        Pausing first means the player is restored *paused*, makes no
        attempt at all, and its first open lands on a free device
        (0.07-0.17s measured, against 1.98s). `device_freed` below puts the
        playing state back.
        """
        if self._player_id is None:
            return False
        async with aiohttp.ClientSession() as session:
            try:
                status = await self._rpc(session, self._player_id, ["status", "-", 1])
                self._resume_playing = status.get("result", {}).get("mode") == "play"
                await self._rpc(session, self._player_id, ["pause", 1])
                await self._rpc(session, self._player_id, ["power", 0])
                logger.info(
                    "lms: paused and powered off (will resume playing: %s)",
                    self._resume_playing,
                )
                return True
            except aiohttp.ClientError as exc:
                logger.warning("lms: pause/power-off failed: %s", exc)
                return False

    async def device_freed(self) -> None:
        """ADR-0027: put back the transport state `release()` recorded.

        Called by the supervisor on the *incoming* adapter once the
        outgoing renderer's release is confirmed - which is exactly when
        squeezelite can actually open the device, so the play we send here
        is the one LMS would have sent itself on power-on, just landing
        after the device is free instead of 460ms before it.

        Only ever sends `play`, and only for a player that was playing when
        it lost the device. A player the user left paused comes back paused
        and we send nothing (George, 2026-09-12: the transport state on
        return is whatever the user left, never something we impose).
        """
        if not self._resume_playing:
            return
        self._resume_playing = False
        if self._player_id is None:
            return
        async with aiohttp.ClientSession() as session:
            try:
                await self._rpc(session, self._player_id, ["play"])
                logger.info("lms: resumed playback the takeover interrupted")
            except aiohttp.ClientError as exc:
                logger.warning("lms: resume after release failed: %s", exc)

    async def signal_stop(self, force: bool) -> None:
        # Ignores `force` on purpose - see the class-level comment.
        # SIGTERM is a no-op against squeezelite ever coming back on its
        # own, so both ladder rungs use SIGKILL. The second call, if the
        # ladder ever reaches it, is a harmless no-op against an
        # already-dead process. restart_after_release was tried and
        # reverted here the same day - see the class-level comment;
        # Restart=on-failure is what brings squeezelite back again now.
        kill_unit(UNIT_NAME, force=True)
