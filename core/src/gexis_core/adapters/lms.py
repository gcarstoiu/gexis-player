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
from typing import Callable

import aiohttp

from gexis_core.adapters.base import Adapter, Capabilities, ReleaseAction, VolumeMechanism
from gexis_core.model import Queue, TrackMetadata
from gexis_core.systemd import kill_unit
from gexis_core.volume import DUMMY_CARD_LMS

logger = logging.getLogger("gexis_core.adapters.lms")

UNIT_NAME = "squeezelite.service"

#: How much of the queue the rail reads. The design shows what is coming
#: up, not a whole 500-track load.
QUEUE_LIMIT = 100

#: The size asked of LMS for the *current* track's artwork. The design's now
#: playing well is 500x500 (`design/data-contract.md`) and the Peppy screen
#: scales down from this too; `_o.jpg` is always a JPEG, where the bare
#: resize was a PNG twice the original's size for 5 of 20 albums (Finding
#: 029 §5). Unsized, LMS returns the original - up to 358 KB, blurred at
#: 72px behind the screen, which cost frames on the panel (George,
#: 2026-09-17).
ARTWORK_SIZE = 500

#: The queue rail's rows are 42px, and there can be `QUEUE_LIMIT` of them.
#: They were served the 500px cover above until Phase 7a step 1 - up to a
#: hundred images at more than ten times the size drawn, fetched the moment
#: the rail opens (George, 2026-09-18: everything on the panel is slow).
#: Same ladder as `library.py`'s.
ARTWORK_ROW = 100

#: Requested on every "status" query this adapter makes so pushed frames
#: carry metadata, not just power (Phase 3 criterion 1). Letters per the
#: CLI docs' songinfo tag table (LMS-CLI.md): a=artist, l=album, c=coverid,
#: d=duration, T=samplerate, K=artwork_url (a remote item's own artwork,
#: ADR-0038 §8a). title/time/duration (top-level, the player's *current*
#: values) come back regardless of tags - only the per-song fields need
#: asking for.
METADATA_TAGS = "aldcTKse"

#: How far the player's position may drift from what `release()` recorded
#: before `device_freed()` corrects it with a seek.
#:
#: There are two routes back to LMS and they behave differently. *Activating*
#: the player restores it paused at exactly the stored position, so nothing
#: needs correcting. Pressing *play* on a deactivated player makes LMS power
#: it on and **restart the track from zero** - measured on hardware
#: 2026-09-12 with arbitration stopped so nothing could correct it: paused
#: and powered off at 115.1s, pressing play reported time=0 and climbed
#: from there. That is LMS's own
#: documented auto-power-on (ADR-0010), not something this code does, and it
#: happens before our acquisition even reaches us, so it can only be
#: corrected afterwards.
#:
#: The tolerance exists so the correction costs nothing in the route that is
#: already right: a seek makes LMS re-request the stream, which is a
#: plausible source of an audible artefact at the resume point, so it is
#: worth avoiding when there is nothing to fix. A couple of seconds of drift
#: is not worth a re-request.
RESUME_POSITION_TOLERANCE_S = 3.0

_id_counter = itertools.count(1)


def _as_float(value) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


#: LMS's `playlist repeat` numbers against ADR-0037's names. LMS's order is
#: 0 off, 1 one song, 2 all (Finding 028) - not the design's off/all/one.
REPEAT_FROM_LMS = {0: "off", 1: "one", 2: "all"}
REPEAT_TO_LMS = {name: number for number, name in REPEAT_FROM_LMS.items()}


def _as_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _shuffle(result: dict) -> bool | None:
    """LMS has three states: 0 off, 1 by song, 2 by album (Finding 028). The
    design's toggle has two, so both 1 and 2 show as on, and turning it on
    from the panel means by song."""
    value = _as_int(result.get("playlist shuffle"))
    return None if value is None else value != 0


def _unavailable_controls(result: dict) -> frozenset[str]:
    """ADR-0037 §3: declared commands that cannot work right now.

    - **A one-item playlist** (a radio station): `jump_fwd` and `jump_rew`
      only restart the stream (Finding 028), and there is nothing to
      shuffle. A longer playlist wraps at both ends, even with repeat off,
      so it never runs out.
    - **A live stream** (`remote` with no duration): it has no end to repeat
      (George, 2026-09-16). A single *song* keeps repeat - looping it is a
      real use.

    Anything not reported disables nothing: a button that works is better
    than one wrongly greyed."""
    unavailable: set[str] = set()
    tracks = _as_int(result.get("playlist_tracks"))
    if tracks is not None and tracks <= 1:
        unavailable |= {"next", "previous", "shuffle"}
    if bool(_as_int(result.get("remote"))) and not _as_float(result.get("duration")):
        unavailable.add("repeat")
    return frozenset(unavailable)


class LmsAdapter(Adapter):
    renderer_id = "lms"
    release_action = ReleaseAction.PAUSE
    unit_name = UNIT_NAME
    # Phase 3 criterion 2. "power_on" is the one acquisition signal this
    # adapter treats as a takeover (ADR-0027 - not "play", which is a
    # separate intention afterwards). Artwork and sample rate both come
    # from the JSON-RPC "status" query's playlist_loop tags (coverid, T) -
    # confirmed against a real library track and a live radio stream,
    # 2026-09-12 (HANDOFF.md).
    capabilities = Capabilities(
        audio_connection="output",
        acquisition_events=frozenset({"power_on"}),
        supports_artwork=True,
        supports_sample_rate=True,
        volume_managed=True,
        volume_mechanism=VolumeMechanism.DUMMY_MIXER,
        dummy_mixer_card=DUMMY_CARD_LMS,
        # Phase 4 criterion 7: the first entry `controls` has ever had.
        # Criterion 2 left it deliberately empty in Phase 3 because nothing
        # could act on a user's command; `activate()` below now can, and
        # only for LMS - Spotify and Bluetooth are taken over by a phone
        # connecting, never by us asking.
        controls=frozenset({"activate", "play", "pause", "next", "previous", "shuffle", "repeat"}),
    )

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
        #: Both set by `release()` from the player's own state and consumed
        #: by `device_freed()`. `_resume_playing` False means "came back
        #: paused, send no play"; `_resume_position` is what the position is
        #: corrected back to if LMS restarted the track (see
        #: RESUME_POSITION_TOLERANCE_S). `_resume_timestamp` is the queue's
        #: `playlist_timestamp` when they were recorded: both are put back
        #: only if it is unchanged (Finding 029, defect A).
        self._resume_playing = False
        self._resume_position: float | None = None
        self._resume_timestamp: float | None = None
        self._on_metadata: Callable[[TrackMetadata], None] | None = None
        self._on_queue = None
        #: (playlist_timestamp, current index) when the queue was last read.
        self._queue_stamp: tuple | None = None
        self._artist_id: int | None = None
        self._album_id: int | None = None
        self._on_availability: Callable[[bool], None] | None = None
        #: The last reported transport, so `play()` can pick its command.
        self._last_transport: str | None = None

    @property
    def current_artist_id(self) -> int | None:
        """LMS's artist id for the track playing now, or None. Read by the
        enrichment service's LMS provider.

        A property, like `player_id` beside it: as a method it read as
        truthy at the call site and the LMS provider asked the plugin about
        a bound method, then fell through to Wikipedia without a word
        (found on hardware, 2026-09-18).
        """
        return self._artist_id

    @property
    def current_album_id(self) -> int | None:
        """LMS's album id for the track playing now, or None. A property, for
        the reason `current_artist_id` says."""
        return self._album_id

    @property
    def player_id(self) -> str | None:
        """This player's id on the server, resolved from its name at
        startup - `None` until then. The library plays on the same player
        this adapter arbitrates for (ADR-0038 §5)."""
        return self._player_id

    @property
    def last_transport(self) -> str | None:
        """The transport this adapter last reported: 'playing', 'paused',
        'stopped', or None before the first report."""
        return self._last_transport

    def on_queue_change(self, callback) -> None:
        """The queue rail's contents (ADR-0038 §1). Read only when LMS says
        the queue changed, not on every status push."""
        self._on_queue = callback

    async def _report_queue_if_changed(self, session, result: dict) -> None:
        """LMS's `playlist_timestamp` moves on a load, an add and a shuffle,
        and not on pause, skip or a power cycle (Finding 029, step 1a), so
        it says exactly when the queue is worth re-reading - a second query,
        because the metadata one asks for the current song alone."""
        if self._on_queue is None or self._player_id is None:
            return
        stamp = (_as_float(result.get("playlist_timestamp")), _as_int(result.get("playlist_cur_index")))
        if stamp == self._queue_stamp:
            return
        self._queue_stamp = stamp
        try:
            queued = await self._rpc(
                session, self._player_id, ["status", 0, QUEUE_LIMIT, f"tags:{METADATA_TAGS}"]
            )
        except aiohttp.ClientError as exc:
            logger.warning("lms: could not read the queue: %s", exc)
            return
        queue = queued.get("result", {})
        items = tuple(
            TrackMetadata(
                title=song.get("title"),
                artist=song.get("artist"),
                album=song.get("album"),
                artwork=(
                    f"{self._base}/music/{song['coverid']}/cover_{ARTWORK_ROW}x{ARTWORK_ROW}_o.jpg"
                    if song.get("coverid")
                    else None
                ),
                duration=_as_float(song.get("duration")),
                source_type="lms",
            )
            for song in queue.get("playlist_loop", [])
        )
        self._on_queue(
            Queue(
                items=items,
                index=_as_int(queue.get("playlist_cur_index")) or 0,
                name=queue.get("playlist_name"),
                id=_as_int(queue.get("playlist_id")),
                modified=bool(_as_int(queue.get("playlist_modified"))),
            )
        )

    def on_metadata_change(self, callback: Callable[[TrackMetadata], None]) -> None:
        """state.py hooks in here (Phase 3 criterion 1). Fired on every
        subscribed status push, not just power changes - the "status"
        query's own `subscribe:N` push-on-change behaviour (LMS-CLI.md)
        covers any player-state change, including a new track loading,
        which is exactly the edge criterion 6 needs to measure later.
        """
        self._on_metadata = callback

    def on_availability_change(self, callback: Callable[[bool], None]) -> None:
        """George's decision, 2026-09-12: "available" means the backend is
        reachable, independent of whether the player is powered on. True
        once the CometD handshake+subscribe succeeds, False while `run()`'s
        outer loop is in its retry sleep after losing the connection.
        """
        self._on_availability = callback

    def _report_metadata(self, result: dict) -> None:
        """`result` is a "status" query's JSON-RPC result, not the raw CLI
        tagged-parameter response LMS-CLI.md illustrates - JSON-RPC nests
        every per-song tag (title/artist/album/coverid/samplerate) inside
        `playlist_loop`, one entry per requested playlist item; player-level
        fields (power, mode, time, duration, current_title, remote) stay at
        the top level. Confirmed against community JSON-RPC examples, not
        against a live LMS server - **the playlist_loop nesting is not yet
        hardware-verified**, see HANDOFF.md.

        With `start="-"` and `itemsPerResponse=1` (every call site here),
        `playlist_loop` holds exactly the current song, so index 0 needs no
        cross-reference against `playlist_cur_index`.
        """
        song = (result.get("playlist_loop") or [{}])[0]
        if result.get("remote"):
            title, album, artwork = self._remote_fields(result, song)
        else:
            coverid = song.get("coverid")
            title, album = song.get("title"), song.get("album")
            artwork = (
                f"{self._base}/music/{coverid}/cover_{ARTWORK_SIZE}x{ARTWORK_SIZE}_o.jpg"
                if coverid
                else None
            )
        # LMS's `mode` is "play"/"pause"/"stop" (LMS-CLI.md's status query).
        # A powered-off player reports no mode at all, which is neither
        # playing nor paused - left as None rather than invented as
        # "stopped", since ADR-0027 makes deactivated a distinct state the
        # UI already learns about from `active`.
        transport = {"play": "playing", "pause": "paused", "stop": "stopped"}.get(
            result.get("mode")
        )
        # Recorded before the no-listener return: `play()` needs it either
        # way, and the volume bridge reads the transport (volume.py's
        # DummyMixerBridge: LMS's pause fade must not be mirrored).
        self._last_transport = transport
        # The `s` tag: LMS's own id for this track's artist, which is what
        # its artist-information plugin is keyed on (ADR-0040 §1). Kept here
        # rather than published in `TrackMetadata`, because it means nothing
        # to the other two renderers and nothing to the enrichment cache,
        # which is keyed on what a track *is* (ADR-0012).
        self._artist_id = _as_int(song.get("artist_id"))
        self._album_id = _as_int(song.get("album_id"))
        if self._on_metadata is None:
            return
        self._on_metadata(
            TrackMetadata(
                title=title,
                artist=song.get("artist"),
                album=album,
                artwork=artwork,
                # LMS-CLI.md's songinfo table documents tag T ("samplerate")
                # as "in KHz", but its own worked example returns a raw Hz
                # value (44100 for 44.1kHz content) - a known doc/reality
                # mismatch, not this project's assumption. Treated as Hz
                # here; **not yet confirmed against a live LMS server**, see
                # HANDOFF.md.
                sample_rate=int(song["samplerate"]) if "samplerate" in song else None,
                position=_as_float(result.get("time")),
                duration=_as_float(result.get("duration")),
                source_type="lms",
                transport=transport,
                unavailable=_unavailable_controls(result),
                shuffle=_shuffle(result),
                repeat=REPEAT_FROM_LMS.get(_as_int(result.get("playlist repeat"))),
            )
        )

    def _remote_fields(self, result: dict, song: dict) -> tuple[str | None, str | None, str | None]:
        """Title, album line and artwork for a stream (ADR-0038 §8a, George
        2026-09-17): the song is the title and the station the album line.

        `current_title` is the station for TuneIn today, but has been blank
        (KissFM, Phase 6) and "Artist - Title" (2026-09-08), so it is used
        only where the song fields leave a gap. A Qobuz track through LMS is
        `remote` too and carries a real album, which wins. The `coverid`
        artwork of a stream is LMS's generic radio placeholder (Finding 029),
        so without an `artwork_url` there is none, and the panel shows its
        own pending glyph.
        """
        song_title = (song.get("title") or "").strip() or None
        station = (result.get("current_title") or "").strip() or None
        title = song_title or station
        album = (song.get("album") or "").strip() or None
        if album is None and station and song_title and song_title not in station:
            album = station
        artwork_url = (song.get("artwork_url") or "").strip()
        if not artwork_url:
            artwork = None
        elif artwork_url.startswith(("http://", "https://")):
            artwork = artwork_url
        else:
            artwork = f"{self._base}/{artwork_url.lstrip('/')}"
        return title, album, artwork

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
                if self._on_availability is not None:
                    self._on_availability(False)
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
                        # "subscribe:0", not "subscribe:1" - LMS-CLI.md's
                        # own wording ("push on player change... the number
                        # indicates the interval between automatic
                        # generations in case nothing happened") means the
                        # digit is a heartbeat period, not an on/off flag.
                        # `subscribe:1` was pushing a fresh frame every
                        # second even when nothing changed - harmless
                        # before this file read anything but `power`, but
                        # once metadata (including a ticking `time`) was
                        # added to every push, that heartbeat alone made
                        # the WebSocket emit a new payload roughly once a
                        # second regardless of real activity. Found live,
                        # 2026-09-12, from George watching the raw output.
                        # `subscribe:0` keeps push-on-real-change (power,
                        # volume, track load - everything this adapter and
                        # criterion 6 depend on) and drops only the
                        # unconditional resend.
                        "request": [
                            self._player_id,
                            ["status", "-", 1, "subscribe:0", f"tags:{METADATA_TAGS}"],
                        ],
                    },
                    "id": str(next(_id_counter)),
                },
            )
            logger.info("lms: subscribed to %s", response_channel)
            if self._on_availability is not None:
                self._on_availability(True)

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
            status = await self._rpc(
                session, self._player_id, ["status", "-", 1, f"tags:{METADATA_TAGS}"]
            )
            result = status.get("result", {})
            last_power = result.get("power")
            self._report_metadata(result)
            await self._report_queue_if_changed(session, result)

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
                    data = frame.get("data") or {}
                    # Every push is a fresh full status result (the
                    # subscribed request carries the same tags as the seed
                    # query above), so this is the edge criterion 6 will
                    # measure later - not just power changes.
                    self._report_metadata(data)
                    # The queue changes far more often than power does, and
                    # every one of those changes arrives here rather than at
                    # the seed query above: a queue read only at subscribe
                    # time showed the rail a queue that could never grow
                    # (George, 2026-09-18 - two albums added, LMS had 27
                    # tracks, the panel still showed 1). The timestamp gate
                    # inside keeps this to one extra RPC per actual change.
                    await self._report_queue_if_changed(session, data)
                    power = data.get("power")
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
                        await self._note_position_if_unset(session)
                        on_release()
                    last_power = power

    async def _note_position_if_unset(self, session: aiohttp.ClientSession) -> None:
        """Record where the track was, for a power-off we did not make.

        `release()` captures this for a takeover, but the user deactivating
        the player themselves never goes through `release()` - and that is
        the more ordinary action, now that ADR-0027 makes deactivation a
        normal part of using the thing. Without this, pressing play
        afterwards restarts the track from zero with nothing recorded to
        put it back, which is exactly what George hit on 2026-09-12
        (log: `player powered off` with no preceding `paused and powered
        off at Xs`, then a return with no seek).

        Only fills a gap: if `release()` already recorded a position, that
        one is better - it was read *before* the pause, and it carries the
        play/pause state with it, which a powered-off player no longer
        reports. Deliberately does not touch `_resume_playing`: for a
        user's own deactivation LMS restores the transport state natively
        on power-on, so there is nothing for us to impose.
        """
        if self._resume_position is not None or self._player_id is None:
            return
        try:
            status = await self._rpc(session, self._player_id, ["status", "-", 1])
            position = status.get("result", {}).get("time")
        except aiohttp.ClientError as exc:
            logger.warning("lms: could not read the position at deactivation: %s", exc)
            return
        if isinstance(position, (int, float)):
            self._resume_position = float(position)
            self._resume_timestamp = _as_float(status.get("result", {}).get("playlist_timestamp"))
            logger.info("lms: noted position %.1fs at deactivation", self._resume_position)

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

    async def activate(self) -> bool:
        """Power the player on — Phase 4 criterion 7's control.

        **This is the first `power 1` this project has ever sent.**
        ADR-0027 recorded the asymmetry deliberately: "we only ever power
        *off*, and only as part of a takeover; we never power on", which is
        what makes provenance tracking unnecessary there — there is no user
        action we could accidentally undo. That reasoning is unchanged by
        this method, because this *is* the user's action, arriving from
        their own UI rather than being synthesised by arbitration.

        No `on_acquire()` is fired here. The CometD watch in `_watch` sees
        `power` go true and reports the acquisition through exactly the
        same path as the phone app doing it (measured at 0.52s to push,
        Finding 018) — this method deliberately does not shortcut that, so
        there is one acquisition path rather than two that can disagree.
        """
        if self._player_id is None:
            logger.warning("lms: activate() with no resolved player id")
            return False
        async with aiohttp.ClientSession() as session:
            try:
                await self._rpc(session, self._player_id, ["power", 1])
                logger.info("lms: activated (power 1) on request")
                return True
            except aiohttp.ClientError as exc:
                logger.warning("lms: activate failed: %s", exc)
                return False

    async def play(self) -> bool:
        """ADR-0037. `pause 0` resumes a paused player where it stopped; a
        stopped one has nothing to resume and needs `play` (Finding 028)."""
        return await self._command(["pause", 0] if self._last_transport == "paused" else ["play"])

    async def pause(self) -> bool:
        return await self._command(["pause", 1])

    async def next(self) -> bool:
        return await self._command(["button", "jump_fwd"])

    async def shuffle(self, on: bool) -> bool:
        return await self._command(["playlist", "shuffle", 1 if on else 0])

    async def repeat(self, mode: str) -> bool:
        return await self._command(["playlist", "repeat", REPEAT_TO_LMS[mode]])

    async def previous(self) -> bool:
        """`jump_rew`, not `playlist index -1`: the index always goes back a
        whole track, while the button restarts the track unless it is near
        its start - what LMS's own apps do (Finding 028)."""
        return await self._command(["button", "jump_rew"])

    async def _command(self, command: list) -> bool:
        """A user's transport command. Like `activate()`, it reports nothing
        itself: the CometD watch sees the result, so there is one path by
        which state changes, whoever caused them."""
        if self._player_id is None:
            logger.warning("lms: %s with no resolved player id", command)
            return False
        async with aiohttp.ClientSession() as session:
            try:
                await self._rpc(session, self._player_id, command)
            except aiohttp.ClientError as exc:
                logger.warning("lms: %s failed: %s", command, exc)
                return False
        logger.info("lms: %s on request", command)
        return True

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
                result = status.get("result", {})
                self._resume_playing = result.get("mode") == "play"
                position = result.get("time")
                self._resume_position = (
                    float(position) if isinstance(position, (int, float)) else None
                )
                self._resume_timestamp = _as_float(result.get("playlist_timestamp"))
                await self._rpc(session, self._player_id, ["pause", 1])
                await self._rpc(session, self._player_id, ["power", 0])
                logger.info(
                    "lms: paused and powered off at %s (will resume playing: %s)",
                    "?" if self._resume_position is None else f"{self._resume_position:.1f}s",
                    self._resume_playing,
                )
                return True
            except aiohttp.ClientError as exc:
                logger.warning("lms: pause/power-off failed: %s", exc)
                return False

    async def device_freed(self) -> None:
        """ADR-0027: put back what `release()` recorded - the transport state,
        and the position if LMS threw it away.

        Called by the supervisor on the *incoming* adapter once the outgoing
        renderer's release is confirmed, which is exactly when squeezelite can
        actually open the device.

        Only ever sends `play` for a player that was playing when it lost the
        device; one the user left paused comes back paused and gets nothing
        (George, 2026-09-12: the transport state on return is whatever the
        user left, never something we impose). The position correction is
        separate and *not* conditional on that flag, because LMS's
        auto-power-on restarts from zero whichever state the player was in.

        Neither is put back onto different content. LMS changes the queue's
        `playlist_timestamp` on every load, and on an add or a shuffle, but
        not on pause, skip, repeat or a power cycle (Finding 029). A load
        made while another renderer held the device - which is also what
        brings LMS back - was otherwise seeked to the old content's
        position. An edit while away loses the position too; George chose
        that over any chance of seeking into content just picked
        (2026-09-17, rule A).
        """
        resume_playing = self._resume_playing
        resume_position = self._resume_position
        resume_timestamp = self._resume_timestamp
        self._resume_playing = False
        self._resume_position = None
        self._resume_timestamp = None
        if self._player_id is None:
            return
        if not resume_playing and resume_position is None:
            return
        async with aiohttp.ClientSession() as session:
            try:
                status = await self._rpc(session, self._player_id, ["status", "-", 1])
                result = status.get("result", {})
                timestamp = _as_float(result.get("playlist_timestamp"))
                if timestamp != resume_timestamp:
                    logger.info(
                        "lms: queue changed since it was released (playlist_timestamp %s -> %s), "
                        "not restoring the old position or play state",
                        resume_timestamp,
                        timestamp,
                    )
                    return
                if resume_playing and result.get("mode") != "play":
                    await self._rpc(session, self._player_id, ["play"])
                    logger.info("lms: resumed playback the takeover interrupted")

                position = result.get("time")
                if (
                    resume_position is not None
                    and isinstance(position, (int, float))
                    and abs(position - resume_position) > RESUME_POSITION_TOLERANCE_S
                ):
                    await self._rpc(
                        session, self._player_id, ["time", f"{resume_position:.2f}"]
                    )
                    # Deliberately does not claim *why* the position was
                    # wrong. Two different things put it there - LMS
                    # restarting the track from zero on its own
                    # auto-power-on, and LMS briefly reporting
                    # position+away_duration from a stale anchor while
                    # squeezelite catches up - and one reading cannot tell
                    # them apart. Both are corrected the same way, so log
                    # the observation rather than an inference.
                    logger.info(
                        "lms: position was %.1fs, seeked back to the %.1fs it was released at",
                        position,
                        resume_position,
                    )
            except aiohttp.ClientError as exc:
                logger.warning("lms: restoring playback after release failed: %s", exc)

    async def signal_stop(self, force: bool) -> None:
        # Ignores `force` on purpose - see the class-level comment.
        # SIGTERM is a no-op against squeezelite ever coming back on its
        # own, so both ladder rungs use SIGKILL. The second call, if the
        # ladder ever reaches it, is a harmless no-op against an
        # already-dead process. restart_after_release was tried and
        # reverted here the same day - see the class-level comment;
        # Restart=on-failure is what brings squeezelite back again now.
        kill_unit(UNIT_NAME, force=True)
