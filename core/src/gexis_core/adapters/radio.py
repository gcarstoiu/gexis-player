# SPDX-License-Identifier: GPL-3.0-or-later
"""**Internet radio: the core's own renderer, mpv** (ADR-0180 items 3-5).

Unlike the other renderers, nothing outside the core starts it: a station is
played because someone tapped it, on the panel, the phone or Home Assistant.
The route acquires the device for `radio` through the supervisor first
(another source is released as in any takeover), then calls `play`, which
starts `gexis-radio.service` - mpv, idle, with its JSON socket - and loads
the station. The unit runs only while a station plays (decision 7: it costs
nothing until then); a stop stops it.

**What mpv is asked for** (Finding 146): FFmpeg's reconnect on and a 5 s
network timeout, in the unit, so a cut or a freeze goes unheard on a station
that buffers more than 5 s; stereo, as a mono station otherwise decodes as
one channel; a stream at 32 kHz or below converted to 48 kHz, so the
equaliser and room correction still apply (`runs_at`).

**The watchdog** (ADR-0022 [H]): mpv reports a cut and a station gone as an
ordinary end of file, and a freeze as nothing at all, so any stop of the
audio while a station should be playing counts. After 10 s without audio
the station is loaded again, three times, 10 s apart; then the radio stops
with *The station is not answering*. Counted from the audio stopping, not
from the drop - the buffer plays first, 3 to 30 s in Finding 146.

A station is live: it stops rather than pauses, and Play after a stop starts
it afresh. No position, no seek. Next and Previous step through the
favourites while a favourite plays (decision 6), and are unavailable for any
other station.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, replace
from typing import Awaitable, Callable

from gexis_core import radio_lines
from gexis_core.adapters.base import Adapter, Capabilities, ReleaseAction, VolumeMechanism
from gexis_core.model import TrackMetadata
from gexis_core.mpv_ipc import Mpv, MpvError
from gexis_core.radio_directory import Station
from gexis_core.systemd import kill_unit, start_unit, stop_unit

logger = logging.getLogger("gexis_core.adapters.radio")

RENDERER_ID = "radio"
UNIT_NAME = "gexis-radio.service"
#: The unit's `RuntimeDirectory`, where mpv opens its socket.
SOCKET = "/run/gexis-radio/mpv.sock"
#: How long the unit has to open its socket once started.
SOCKET_WAIT_S = 5.0

#: ADR-0022 [H]: no audio for this long, the station is loaded again ...
WATCHDOG_S = 10.0
#: ... this many times; then the radio stops with a message.
TRIES = 3
#: Audio this long without a stop starts the count again.
SETTLED_S = 30.0
#: ADR-0022 [H]: a stream at this rate or below is converted up to 48 kHz.
LOW_RATE = 32000
TARGET_RATE = 48000
#: The filter's label, so it is added once and removed by name.
RATE_FILTER = "@gexisrate"

#: What `state` names (`radio` in the published state).
CONNECTING = "connecting"
PLAYING = "playing"
RECONNECTING = "reconnecting"
STOPPED = "stopped"
NOT_ANSWERING = "not_answering"

#: The properties mpv reports as they change.
OBSERVED = ("core-idle", "metadata", "audio-params", "audio-codec-name")

#: mpv's decoder names as the screens write a codec, beside the directory's.
CODECS = {"mp3": "MP3", "mp3float": "MP3", "aac": "AAC", "aac_fixed": "AAC", "opus": "OPUS",
          "vorbis": "OGG", "flac": "FLAC", "mp2": "MP2", "alac": "ALAC"}


def codec_name(mpv_name) -> str | None:
    """`aac` → *AAC*; a name not here is shown as mpv gives it, upper case."""
    if not isinstance(mpv_name, str) or not mpv_name:
        return None
    return CODECS.get(mpv_name.lower(), mpv_name.upper())


@dataclass(frozen=True)
class RadioState:
    """What the radio is doing, beside the track (the Radio screen and Now
    Playing's reconnecting and not-answering states)."""

    station: Station | None = None
    state: str = STOPPED
    #: Which reload the watchdog is on, 1 to `TRIES`; 0 otherwise.
    attempt: int = 0
    #: What the station sent for Now Playing's lines (the design's `lines`):
    #: `split` (artist and title), `whole` (one line, the title) or `none`
    #: (nothing: the station's name is the title, George 2026-11-14).
    lines: str = "none"

    def to_json(self) -> dict:
        return {"station": self.station.to_json() if self.station else None,
                "state": self.state, "attempt": self.attempt, "tries": TRIES,
                "lines": self.lines}


class Units:
    """systemd, off the event loop: `systemctl` waits for the unit."""

    async def start(self) -> None:
        await asyncio.to_thread(start_unit, UNIT_NAME)

    async def stop(self) -> None:
        await asyncio.to_thread(stop_unit, UNIT_NAME)

    async def kill(self) -> None:
        await asyncio.to_thread(kill_unit, UNIT_NAME, force=True)


class RadioAdapter(Adapter):
    renderer_id = RENDERER_ID
    release_action = ReleaseAction.DISCONNECT
    unit_name = UNIT_NAME
    capabilities = Capabilities(
        audio_connection="output",
        # A tap on a station, from any of the three places - the core's own
        # route, never an outside app's event.
        acquisition_events=frozenset({"station_played"}),
        supports_artwork=True,
        supports_sample_rate=True,
        # The panel's slider is the output's own level: mpv plays at its
        # own 100 % and has no number of its own to keep (ADR-0053).
        volume_managed=False,
        volume_mechanism=VolumeMechanism.OUTPUT,
        controls=frozenset({"play", "pause", "next", "previous"}),
    )

    def __init__(self, *, user_agent: str, resolve: Callable[[Station], Awaitable[str]],
                 step: Callable[[str, int], Station | None],
                 is_favourite: Callable[[str], bool],
                 units: Units | None = None, socket_path: str = SOCKET,
                 connect: Callable[..., Mpv] = Mpv,
                 logo_path: Callable[[str | None], str | None] = lambda url: url) -> None:
        """`resolve` gives the address to play a station at (the directory's
        now, counted, or the kept one); `step` the favourite before or after
        one; `is_favourite` whether a station is one."""
        self._user_agent = user_agent
        self._resolve = resolve
        self._step = step
        self._is_favourite = is_favourite
        self._units = units or Units()
        self._socket_path = socket_path
        self._connect = connect
        #: The player's own address for a station's logo (`radio_logos`).
        self._logo_path = logo_path
        self._mpv: Mpv | None = None
        self._on_metadata: Callable[[TrackMetadata], None] | None = None
        self._on_state: Callable[[RadioState], None] | None = None
        self._on_release: Callable[[], None] | None = None
        self._on_availability: Callable[[bool], None] | None = None
        self._on_learned: Callable[[Station], None] | None = None
        self._state = RadioState()
        self._metadata = TrackMetadata()
        #: Whether a station should be sounding now: the watchdog's question.
        self._wanted = False
        self._idle = True
        self._url: str | None = None
        self._rate_filter = False
        self._watchdog: asyncio.Task | None = None
        self._settled: asyncio.Task | None = None
        #: One play, stop or step at a time: a second tap waits for the first.
        self._lock = asyncio.Lock()
        #: Raised by every stop and release, outside the lock: a play still
        #: looking its station up when another source takes over sees it
        #: changed and goes no further, so mpv never starts behind the new
        #: source's back.
        self._generation = 0

    # --- hooks -----------------------------------------------------------

    def on_metadata_change(self, callback: Callable[[TrackMetadata], None]) -> None:
        self._on_metadata = callback

    def on_state_change(self, callback: Callable[[RadioState], None]) -> None:
        self._on_state = callback

    def on_station_learned(self, callback: Callable[[Station], None]) -> None:
        """A station that came without its codec or bitrate (one added by its
        address) has them from mpv once it sounds."""
        self._on_learned = callback

    def on_availability_change(self, callback: Callable[[bool], None]) -> None:
        """Available while the source is on: there is no daemon of its own to
        lose, and mpv is started for each station."""
        self._on_availability = callback

    @property
    def wants_sound(self) -> bool:
        """Whether a station should be playing now."""
        return self._wanted

    @property
    def state(self) -> RadioState:
        return self._state

    async def run(self, on_acquire, on_release) -> None:
        """Nothing to watch outside the core: a station starts from a route.
        Kept for `on_release`, and so the unit is never left running from a
        core that stopped: at the start, nothing plays."""
        self._on_release = on_release
        if not self._wanted:
            try:
                await self._units.stop()
            except Exception:  # noqa: BLE001 - a stop that failed is logged by systemd
                logger.exception("radio: stopping the unit at start failed")
        if self._on_availability is not None:
            self._on_availability(True)
        await asyncio.Event().wait()

    # --- what the routes call --------------------------------------------

    async def play_station(self, station: Station) -> bool:
        """Play `station` now. The caller has acquired the device."""
        async with self._lock:
            return await self._play(station)

    async def play(self) -> bool:
        """Play after a stop: the same station, afresh."""
        async with self._lock:
            if self._state.station is None:
                return False
            return await self._play(self._state.station)

    async def pause(self) -> bool:
        """A live station stops rather than pauses (item 4)."""
        self._generation += 1
        async with self._lock:
            await self._stop(STOPPED)
            return True

    async def reopen(self) -> None:
        """**The chain was rewritten under a playing station** (a change of
        output, of the group, of the visualiser's tuning): every renderer was
        stopped so the new `output.conf` is read when the device opens
        again. The station is loaded again now rather than after the
        watchdog's ten seconds."""
        async with self._lock:
            if not self._wanted or self._url is None:
                return
            logger.info("radio: the chain changed, loading the station again")
            if await self._ensure_mpv():
                try:
                    await self._load(self._url)
                except MpvError as exc:
                    logger.info("radio: loading again failed: %s", exc)
            self._arm_watchdog()

    async def next(self) -> bool:
        return await self._step_by(+1)

    async def previous(self) -> bool:
        return await self._step_by(-1)

    async def refresh_favourite(self) -> None:
        """The favourites changed: whether Next and Previous work now may
        have too."""
        if self._state.station is not None:
            self._publish_metadata(self._metadata)

    # --- arbitration -----------------------------------------------------

    async def release(self) -> bool:
        """Another source takes the device, or the source was switched off:
        the stream is stopped, and the unit with it, which is what frees the
        device."""
        self._generation += 1
        self._wanted = False
        async with self._lock:
            await self._stop(STOPPED)
        return True

    async def signal_stop(self, force: bool) -> None:
        await self._units.kill()

    # --- underneath ------------------------------------------------------

    async def _step_by(self, by: int) -> bool:
        async with self._lock:
            current = self._state.station
            if current is None:
                return False
            target = self._step(current.id, by)
            if target is None:
                return False
            return await self._play(target)

    async def _play(self, station: Station) -> bool:
        self._cancel_timers()
        self._generation += 1
        generation = self._generation
        self._wanted = True
        self._set_state(RadioState(station=station, state=CONNECTING))
        self._publish_metadata(self._station_metadata(station, transport="playing"))
        try:
            url = await self._resolve(station)
        except Exception:  # noqa: BLE001 - the kept address still plays
            logger.exception("radio: resolving %s failed", station.id)
            url = station.url
        if generation != self._generation:
            logger.info("radio: %s was stopped before it started", station.id)
            return False
        self._url = url
        if not await self._ensure_mpv():
            await self._stop(NOT_ANSWERING)
            return False
        if generation != self._generation:
            await self._stop(STOPPED)
            return False
        try:
            await self._load(url)
        except MpvError as exc:
            logger.warning("radio: loading %s failed: %s", station.id, exc)
        # Whatever happened, the watchdog decides from here.
        self._arm_watchdog()
        logger.info("radio: playing %s (%s)", station.name, station.id)
        return True

    async def _load(self, url: str) -> None:
        if self._rate_filter:
            try:
                await self._mpv.command("af", "remove", RATE_FILTER)
            except MpvError:
                pass
            self._rate_filter = False
        await self._mpv.command("loadfile", url, "replace")

    async def _ensure_mpv(self) -> bool:
        if self._mpv is not None and self._mpv.connected:
            return True
        await self._units.start()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + SOCKET_WAIT_S
        while True:
            try:
                mpv = self._connect(self._on_event, self._on_closed)
                await mpv.connect(self._socket_path)
                break
            except (OSError, MpvError) as exc:
                if loop.time() >= deadline:
                    logger.warning("radio: mpv's socket did not open (%s)", exc)
                    return False
                await asyncio.sleep(0.1)
        self._mpv = mpv
        try:
            await mpv.command("set_property", "user-agent", self._user_agent)
            for number, name in enumerate(OBSERVED, start=1):
                await mpv.command("observe_property", number, name)
        except MpvError as exc:
            logger.warning("radio: setting mpv up failed: %s", exc)
            return False
        return True

    async def _stop(self, why: str) -> None:
        self._wanted = False
        self._cancel_timers()
        mpv, self._mpv = self._mpv, None
        if mpv is not None:
            await mpv.close()
        await self._units.stop()
        self._idle = True
        self._rate_filter = False
        station = self._state.station
        self._set_state(RadioState(station=station, state=why))
        if station is not None:
            self._publish_metadata(replace(self._metadata, transport="stopped"))

    def _on_closed(self) -> None:
        """mpv went away. Ours (a stop) is already handled; otherwise the
        watchdog finds no audio and loads the station again."""
        if self._wanted:
            logger.warning("radio: mpv's connection ended while a station played")
            self._mpv = None
            self._idle = True
            self._arm_watchdog()

    def _on_event(self, message: dict) -> None:
        event = message.get("event")
        if event == "property-change":
            self._on_property(message.get("name"), message.get("data"))
        elif event == "end-file":
            # Any end while a station should play is a drop (Finding 146);
            # a redirect is a playlist handing over, and a stop is ours.
            reason = message.get("reason")
            if self._wanted and reason not in ("redirect", "stop", "quit"):
                logger.info("radio: the stream ended (%s)", reason)

    def _on_property(self, name, value) -> None:
        if name == "core-idle":
            idle = value is not False
            if idle == self._idle:
                return
            self._idle = idle
            if not self._wanted:
                return
            if idle:
                self._arm_watchdog()
            else:
                self._sounding()
        elif name == "metadata":
            station = self._state.station
            if station is None:
                return
            artist, title = radio_lines.from_metadata(value, station.name)
            lines = "split" if artist else "whole" if title else "none"
            if lines != self._state.lines:
                self._set_state(replace(self._state, lines=lines))
            metadata = self._lines(station, artist, title)
            if (metadata.artist, metadata.title, metadata.album) != \
                    (self._metadata.artist, self._metadata.title, self._metadata.album):
                self._publish_metadata(replace(self._metadata, artist=metadata.artist,
                                               title=metadata.title, album=metadata.album))
        elif name == "audio-params":
            rate = value.get("samplerate") if isinstance(value, dict) else None
            if isinstance(rate, int) and rate > 0:
                if rate != self._metadata.sample_rate:
                    self._publish_metadata(replace(self._metadata, sample_rate=rate))
                if rate <= LOW_RATE and not self._rate_filter and self._mpv is not None:
                    self._rate_filter = True
                    asyncio.ensure_future(self._raise_rate(rate))
        elif name == "audio-codec-name":
            pass  # The directory's codec is shown; mpv's is in the log.

    async def _raise_rate(self, rate: int) -> None:
        mpv = self._mpv
        if mpv is None:
            return
        try:
            await mpv.command("af", "add", f"{RATE_FILTER}:format=srate={TARGET_RATE}")
            logger.info("radio: %d Hz converted to %d Hz", rate, TARGET_RATE)
        except MpvError as exc:
            self._rate_filter = False
            logger.warning("radio: converting %d Hz failed: %s", rate, exc)

    def _sounding(self) -> None:
        """Audio is coming out: no watchdog; and once it has for a while,
        the tries start again."""
        if self._watchdog is not None:
            self._watchdog.cancel()
            self._watchdog = None
        if self._state.state != PLAYING:
            self._set_state(replace(self._state, state=PLAYING))
        if self._settled is None and self._state.attempt:
            self._settled = asyncio.ensure_future(self._settle())
        asyncio.ensure_future(self._learn())

    async def _learn(self) -> None:
        """**What is playing, asked of mpv once it sounds** (found on sofapi,
        2026-11-14): mpv reports a property only when it changes, so after a
        station at the same rate as the one before, the rate never came and
        Now Playing had none. And a station that came without its codec or
        bitrate - one added by its address - takes mpv's."""
        mpv, station = self._mpv, self._state.station
        if mpv is None or station is None:
            return
        try:
            params = await mpv.command("get_property", "audio-params")
            name = await mpv.command("get_property", "audio-codec-name")
            bits = await mpv.command("get_property", "audio-bitrate")
        except MpvError:
            return
        if self._state.station is not station:
            return
        rate = params.get("samplerate") if isinstance(params, dict) else None
        if isinstance(rate, int) and rate > 0 and rate != self._metadata.sample_rate:
            self._publish_metadata(replace(self._metadata, sample_rate=rate))
        codec = station.codec or codec_name(name)
        bitrate = station.bitrate or (round(bits / 1000) if isinstance(bits, (int, float)) and bits > 0 else None)
        if (codec, bitrate) != (station.codec, station.bitrate):
            learned = replace(station, codec=codec, bitrate=bitrate)
            self._set_state(replace(self._state, station=learned))
            self._publish_metadata(replace(self._metadata, codec=codec))
            if self._on_learned is not None:
                self._on_learned(learned)

    async def _settle(self) -> None:
        try:
            await asyncio.sleep(SETTLED_S)
            if self._wanted and not self._idle:
                self._set_state(replace(self._state, attempt=0))
        finally:
            self._settled = None

    def _arm_watchdog(self) -> None:
        if self._settled is not None:
            self._settled.cancel()
            self._settled = None
        if self._watchdog is None or self._watchdog.done():
            self._watchdog = asyncio.ensure_future(self._watch())

    async def _watch(self) -> None:
        """No audio for `WATCHDOG_S`: load the station again, `TRIES` times,
        each `WATCHDOG_S` apart; then stop with a message."""
        try:
            while self._wanted and self._idle:
                await asyncio.sleep(WATCHDOG_S)
                if not (self._wanted and self._idle):
                    return
                attempt = self._state.attempt + 1
                if attempt > TRIES:
                    logger.warning("radio: %s is not answering, stopping",
                                   self._state.station.name if self._state.station else "?")
                    self._watchdog = None
                    await asyncio.shield(self._give_up())
                    return
                logger.info("radio: no audio for %.0f s, loading again (%d of %d)",
                            WATCHDOG_S, attempt, TRIES)
                self._set_state(replace(self._state, state=RECONNECTING, attempt=attempt))
                # **Once begun, a reload finishes** (found by this file's own
                # tests): audio coming back mid-reload cancels this watch, and
                # a cancel between connecting to mpv and asking it for its
                # properties left mpv playing with nothing watching it.
                await asyncio.shield(self._reload())
        except asyncio.CancelledError:
            pass
        finally:
            if self._watchdog is asyncio.current_task():
                self._watchdog = None

    async def _reload(self) -> None:
        async with self._lock:
            if not self._wanted:
                return
            if await self._ensure_mpv() and self._url:
                try:
                    await self._load(self._url)
                except MpvError as exc:
                    logger.info("radio: loading again failed: %s", exc)

    async def _give_up(self) -> None:
        async with self._lock:
            if self._wanted:
                await self._stop(NOT_ANSWERING)

    def _cancel_timers(self) -> None:
        current = asyncio.current_task()
        for task in (self._watchdog, self._settled):
            if task is not None and task is not current:
                task.cancel()
        self._watchdog = self._settled = None

    def _station_metadata(self, station: Station, transport: str) -> TrackMetadata:
        """The track's cover is looked up as for any renderer that sends none
        (ADR-0081); the station's logo, through the player, is shown until one
        is found, and when none is."""
        return replace(self._lines(station, None, None),
                       fallback_artwork=self._logo_path(station.logo),
                       codec=station.codec, source_type=RENDERER_ID, transport=transport)

    @staticmethod
    def _lines(station: Station, artist: str | None, title: str | None) -> TrackMetadata:
        """**Now Playing's lines** (item 4; George, 2026-11-14): what the
        station sent, with its name on the album line - or, when it sent
        nothing, its name as the title and no album line."""
        if title is None:
            return TrackMetadata(title=station.name)
        return TrackMetadata(artist=artist, title=title, album=station.name)

    def _publish_metadata(self, metadata: TrackMetadata) -> None:
        station = self._state.station
        favourite = station is not None and self._is_favourite(station.id)
        metadata = replace(metadata, unavailable=frozenset() if favourite
                           else frozenset({"next", "previous"}))
        self._metadata = metadata
        if self._on_metadata is not None:
            self._on_metadata(metadata)

    def _set_state(self, state: RadioState) -> None:
        self._state = state
        if self._on_state is not None:
            self._on_state(state)

