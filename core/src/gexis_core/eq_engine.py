# SPDX-License-Identifier: GPL-3.0-or-later
"""**The equaliser on the loopback** (ADR-0162 D1, D2, D6, D7; Finding 138).

While the equaliser is on for the output in use, every renderer plays into
the ALSA loopback (`outputs.render(eq=True)`), and this runs what is behind
it: CamillaDSP (`gexis-equaliser.service`, waiting for a configuration on
its websocket) and a watch on the loopback's controls.

**One stream at a time, at its own rate** (Finding 138). The loopback takes
the rate, format and channels of whoever opens it first, and cannot be held
across a change of rate - so CamillaDSP is told nothing until a renderer has
opened it. The loopback says so on *PCM Slave Active* within a few
milliseconds, with the stream's rate, format and channels beside it; this
then starts CamillaDSP at exactly those, lowered by the headroom first (D3).
When the stream ends CamillaDSP lets the loopback go by itself
(`stop_on_inactive`), so the next one can open at whatever rate it has.
Measured: 12-24 ms off a stream's start, nothing inside it.

**A change is heard at once** (D2): the bands are patched into the running
CamillaDSP, the headroom moved on its fader, which ramps. When the headroom
rises it moves first, so a boost never arrives before the room for it.

**Native DSD goes past it** (D7, decision 5): a DSD stream on the loopback is
sent on to the card untouched (`alsaloop`), and the equaliser stands aside
until the next PCM one.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Awaitable, Callable

import aiohttp

from gexis_core import equaliser as eq
from gexis_core import outputs

logger = logging.getLogger("gexis_core.eq_engine")

UNIT = "gexis-equaliser.service"
PORT = 1234
LOOPBACK = f"hw:{outputs.LOOPBACK}"
#: The fader's ramp, and a little: how long a rising headroom is given before
#: the boost that needs it.
RAMP_S = eq.HEADROOM_RAMP_MS / 1000 + 0.03

#: ALSA's `snd_pcm_format_t`, as *PCM Slave Format* reports it, for the
#: formats a renderer sends (asound.h).
ALSA_FORMATS = {
    2: "S16_LE", 6: "S24_LE", 10: "S32_LE", 14: "FLOAT_LE", 16: "FLOAT64_LE", 32: "S24_3LE",
    48: "DSD_U8", 49: "DSD_U16_LE", 50: "DSD_U32_LE", 51: "DSD_U16_BE", 52: "DSD_U32_BE",
}


@dataclass(frozen=True)
class Stream:
    rate: int
    fmt: str
    channels: int

    @property
    def dsd(self) -> bool:
        return self.fmt.startswith("DSD_")


_CONTROL = re.compile(r"^numid=\d+,iface=PCM,name='PCM Slave (\w+)'(?:,device=(\d+))?(?:,subdevice=(\d+))?")


def parse_contents(text: str) -> Stream | None:
    """**What is playing into the loopback**, from `amixer contents`: the
    controls of device 1, subdevice 0 - where a stream played into device 0
    shows. None when nothing plays (or the format is one no renderer sends)."""
    values: dict[str, str] = {}
    which = None
    for line in text.splitlines():
        m = _CONTROL.match(line)
        if m:
            which = m.group(1) if (m.group(2) == "1" and (m.group(3) or "0") == "0") else None
            continue
        if which and line.strip().startswith(": values="):
            values[which] = line.split("=", 1)[1].strip()
            which = None
    if values.get("Active") != "on":
        return None
    try:
        rate, channels = int(values["Rate"]), int(values["Channels"])
        fmt = ALSA_FORMATS.get(int(values["Format"]))
    except (KeyError, ValueError):
        return None
    if fmt is None or rate <= 0 or channels <= 0:
        return None
    return Stream(rate, fmt, channels)


async def _run(*args: str, timeout: float = 5) -> str:
    proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE,
                                                stderr=asyncio.subprocess.DEVNULL)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return ""
    return out.decode(errors="replace")


async def _systemctl(*args: str) -> None:
    await _run("systemctl", *args, timeout=20)


class Camilla:
    """CamillaDSP's websocket: one connection, re-made when it drops."""

    def __init__(self, url: str = f"ws://127.0.0.1:{PORT}"):
        self.url = url
        self._session: aiohttp.ClientSession | None = None
        self._ws = None
        self._lock = asyncio.Lock()

    async def connect(self, wait_s: float = 8) -> bool:
        if self._ws is not None and not self._ws.closed:
            return True
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        deadline = asyncio.get_running_loop().time() + wait_s
        while True:
            try:
                self._ws = await self._session.ws_connect(self.url, timeout=aiohttp.ClientWSTimeout(ws_close=2))
                return True
            except (aiohttp.ClientError, OSError):
                if asyncio.get_running_loop().time() > deadline:
                    return False
                await asyncio.sleep(0.1)

    async def cmd(self, name: str, arg=None):
        """One command and its answer's value; raises on an error answer."""
        async with self._lock:
            if not await self.connect():
                raise ConnectionError("CamillaDSP does not answer")
            try:
                await self._ws.send_str(json.dumps(name if arg is None else {name: arg}))
                reply = json.loads(await asyncio.wait_for(self._ws.receive_str(), 5))
            except (aiohttp.ClientError, asyncio.TimeoutError, TypeError, ValueError) as exc:
                await self._drop()
                raise ConnectionError(f"CamillaDSP: {exc}") from exc
        answer = reply.get(name, {})
        if answer.get("result") != "Ok":
            raise RuntimeError(f"CamillaDSP refused {name}: {answer.get('result')}")
        return answer.get("value")

    async def _drop(self) -> None:
        if self._ws is not None:
            await self._ws.close()
        self._ws = None

    async def close(self) -> None:
        await self._drop()
        if self._session is not None:
            await self._session.close()
        self._session = None


class EqEngine:
    """Runs the equaliser for whichever output has it on.

    `configure(card, gains)` is all the core calls: the card the equaliser
    is on for (None when it is not in the path) and the bands. `on_change`
    hears the state worth showing (whether DSD is standing it aside)."""

    def __init__(self, *, camilla: Camilla | None = None,
                 systemctl: Callable[..., Awaitable[None]] = _systemctl,
                 run: Callable[..., Awaitable[str]] = _run,
                 on_change: Callable[[dict], None] = lambda status: None,
                 takes_rate: Callable[[str, int], bool | None] = outputs.takes_rate):
        self._camilla = camilla or Camilla()
        self._systemctl = systemctl
        self._run = run
        self._on_change = on_change
        self._takes_rate = takes_rate
        self._card: str | None = None
        self._gains: tuple[int, ...] = eq.FLAT
        self._watch: asyncio.Task | None = None
        self._stream: Stream | None = None
        self._applied: tuple[tuple[int, ...], float] | None = None   # what CamillaDSP has now
        self._push: asyncio.Task | None = None
        self._forward: asyncio.subprocess.Process | None = None
        self._status: dict = {}

    # -- what the core calls ------------------------------------------------

    async def configure(self, card: str | None, gains, restart: bool = False) -> None:
        """`restart` after `output.conf` was rewritten under a running
        CamillaDSP, which reads ALSA's configuration only when it starts."""
        gains = eq.gains_from(gains)
        if card is None:
            if self._card is not None or self._watch is not None:
                self._card = None
                await self._stop()
            return
        started = self._card is None
        moved = self._card is not None and self._card != card
        self._card, self._gains = card, gains
        if started or moved or restart:
            await self._start(restart=not started)
        else:
            self._kick()

    def status(self) -> dict:
        return dict(self._status)

    # -- running -------------------------------------------------------------

    async def _start(self, restart: bool) -> None:
        await self._end_stream()
        await self._camilla.close()
        await self._systemctl("restart" if restart else "start", UNIT)
        if self._watch is None or self._watch.done():
            self._watch = asyncio.create_task(self._watching())
        else:
            asyncio.create_task(self._look())
        self._set_status()
        logger.info("equaliser: on for %s", self._card)

    async def _stop(self) -> None:
        if self._watch is not None:
            self._watch.cancel()
            self._watch = None
        await self._end_stream()
        await self._camilla.close()
        await self._systemctl("stop", UNIT)
        self._set_status()
        logger.info("equaliser: out of the path")

    async def _watching(self) -> None:
        """`alsactl monitor` on the loopback, for as long as the equaliser is
        on; every *PCM Slave* change is looked at."""
        while True:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "stdbuf", "-oL", "alsactl", "monitor", LOOPBACK,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            except OSError as exc:
                logger.warning("equaliser: cannot watch the loopback: %s", exc)
                await asyncio.sleep(5)
                continue
            try:
                # Subscribed before the first look, so a stream that starts
                # in between is not missed (Finding 138's first run was).
                await asyncio.sleep(0.2)
                await self._look()
                assert proc.stdout is not None
                while line := await proc.stdout.readline():
                    if b"PCM Slave" in line:
                        await self._look()
            except asyncio.CancelledError:
                proc.kill()
                raise
            finally:
                if proc.returncode is None:
                    proc.kill()
            logger.warning("equaliser: the loopback's monitor exited; again in 2 s")
            await asyncio.sleep(2)

    async def _look(self) -> None:
        stream = parse_contents(await self._run("amixer", "-D", LOOPBACK, "contents"))
        if stream == self._stream:
            return
        await self._end_stream()
        self._stream = stream
        if stream is None or self._card is None:
            self._set_status()
            return
        if stream.dsd:
            await self._forward_dsd(stream)
        else:
            await self._start_stream(stream)
        self._set_status()

    async def _start_stream(self, stream: Stream) -> None:
        gains = self._gains
        headroom = eq.headroom_db(gains)
        config = eq.camilla_config(stream.rate, stream.fmt, stream.channels, gains, outputs.EQ_OUT)
        if self._takes_rate(self._card, stream.rate) is False:
            # A rate the card lacks (ADR-0155): to its highest, as
            # Squeezelite's own resampler would - which sees the loopback
            # now, and the loopback takes every rate.
            top = outputs.top_rate(self._card)
            if top:
                config["devices"].update(samplerate=top, capture_samplerate=stream.rate,
                                         chunksize=eq.chunksize(top),
                                         resampler={"type": "AsyncSinc", "profile": "Balanced"})
        try:
            await self._camilla.cmd("SetFaderVolume", [eq.HEADROOM_FADER, -headroom])
            await self._camilla.cmd("SetConfigJson", json.dumps(config))
            self._applied = (gains, headroom)
            logger.info("equaliser: %d Hz %s, %d channels, lowered %.1f dB",
                        stream.rate, stream.fmt, stream.channels, headroom)
        except (ConnectionError, RuntimeError) as exc:
            self._applied = None
            logger.warning("equaliser: could not start on the stream (%s)", exc)
        self._kick()

    async def _end_stream(self) -> None:
        self._stream = None
        self._applied = None
        if self._forward is not None:
            if self._forward.returncode is None:
                self._forward.terminate()
                try:
                    await asyncio.wait_for(self._forward.wait(), 2)
                except asyncio.TimeoutError:
                    self._forward.kill()
            self._forward = None

    async def _forward_dsd(self, stream: Stream) -> None:
        """Native DSD, untouched, from the loopback to the card."""
        try:
            self._forward = await asyncio.create_subprocess_exec(
                "alsaloop", "-C", f"{LOOPBACK},1,0", "-P", f"hw:{self._card}",
                "-f", stream.fmt, "-r", str(stream.rate), "-c", str(stream.channels),
                "-S", "captshift", "-t", "50000",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            logger.info("equaliser: DSD %d Hz goes past it to %s", stream.rate, self._card)
        except OSError as exc:
            logger.warning("equaliser: cannot send DSD on: %s", exc)

    # -- live changes (D2) ------------------------------------------------------

    def _kick(self) -> None:
        """Bring CamillaDSP to the bands wanted now: one change in flight,
        the latest wanted after it, so a dragged band never queues up."""
        if self._push is None or self._push.done():
            self._push = asyncio.create_task(self._pushing())

    async def _pushing(self) -> None:
        while self._applied is not None and self._stream is not None and not self._stream.dsd:
            gains, headroom = self._gains, eq.headroom_db(self._gains)
            old_gains, old_headroom = self._applied
            if (gains, headroom) == (old_gains, old_headroom):
                return
            try:
                if headroom > old_headroom:
                    await self._camilla.cmd("SetFaderVolume", [eq.HEADROOM_FADER, -headroom])
                    await asyncio.sleep(RAMP_S)
                changed = {eq.filter_name(i): {"parameters": {"gain": g}}
                           for i, (g, was) in enumerate(zip(gains, old_gains)) if g != was}
                if changed:
                    await self._camilla.cmd("PatchConfig", {"filters": changed})
                if headroom < old_headroom:
                    await self._camilla.cmd("SetFaderVolume", [eq.HEADROOM_FADER, -headroom])
                self._applied = (gains, headroom)
            except (ConnectionError, RuntimeError) as exc:
                logger.warning("equaliser: a change did not reach CamillaDSP (%s)", exc)
                return

    def _set_status(self) -> None:
        status = {"running": self._card is not None,
                  "dsd": bool(self._stream and self._stream.dsd),
                  "rate": self._stream.rate if self._stream else None}
        if status != self._status:
            self._status = status
            self._on_change(dict(status))
