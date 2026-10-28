# SPDX-License-Identifier: GPL-3.0-or-later
"""**The group's audio for every source but Lyrion** (ADR-0166 D1 as amended
2026-10-28, Finding 139).

While a player is in a group its renderers play into a second loopback,
`Multiroom` (`outputs.render(group=...)`), and this runs what is behind it:

- **snapserver** (`gexis-snapserver.service`), on every player of the group,
  so that whichever of them a source starts on can lead at once. It reads
  one pipe per rate (`RATES`), declared in its configuration: Finding 139
  found that its ALSA source holds the loopback's capture - which fixes the
  rate for the next stream - and that removing such a stream at runtime
  ends the server.
- **the feeder**: while something plays into the loopback, `arecord` copies
  the loopback's capture into the pipe of that stream's rate, and the
  server's clients are moved to that pipe's stream. When the stream ends
  `arecord` stops, the capture is let go, and the next stream opens at its
  own rate - as CamillaDSP's `stop_on_inactive` does for the equaliser.
- **snapclient** (`gexis-snapclient.service`), pointed at the leader -
  the leader's own included, so every player is equally late - and playing
  into `gexis_group_in`: this player's own chain, its meter, equaliser,
  volume and card (`outputs.GROUP_IN`).

Snapcast's own volume is never used (`--mixer none`, the server's at 100 %):
each player's level is its own control's (D6). The server is kept off the
system bus, so it announces nothing on the network (Finding 139 #7); the
clients are always given the leader's address.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Callable

from gexis_core import outputs
from gexis_core.eq_engine import parse_contents

logger = logging.getLogger("gexis_core.snapcast")

SERVER_UNIT = "gexis-snapserver.service"
CLIENT_UNIT = "gexis-snapclient.service"
#: The members' clients reach the leader's server here; the control port
#: answers this player only.
STREAM_PORT = 1704
CONTROL_PORT = 1705
#: Every rate a stream may have. Each is a pipe and a stream of the server's
#: from its start, idle until fed.
RATES = (44100, 48000, 88200, 96000, 176400, 192000, 352800, 384000)
#: `output` pads every integer format to this on the way in (as the
#: equaliser's chain does), so one width per rate: 32 bits, bit-perfect.
BITS = 32
#: **The buffer: as short as measured safe** (D7, decision 7) - the end-to-end
#: delay from the loopback to every card. Measured before it is called done.
BUFFER_MS = 400
#: FLAC needs about 26 ms a chunk (snapserver's own note).
CHUNK_MS = 26
#: Where the server's pipes and its own data live (the unit's
#: RuntimeDirectory), and the files this writes for the two units.
RUN_DIR = Path("/run/gexis-snap")
SERVER_CONF = Path("/run/gexis/snapserver.conf")
CLIENT_ENV = Path("/run/gexis/snapclient.env")
LOOPBACK = f"hw:{outputs.GROUP_CARD}"
#: The client closes its card after this long without audio (Finding 139 #6).
CLIENT_IDLE_S = 5.0


def stream_id(rate: int) -> str:
    return f"r{rate}"


def server_config(buffer_ms: int = BUFFER_MS, run_dir: Path = RUN_DIR) -> str:
    """snapserver's configuration: no HTTP, control on loopback only, the
    stream port for the members, and a pipe per rate."""
    sources = "\n".join(
        f"source = pipe://{run_dir}/{rate}?name={stream_id(rate)}&mode=create"
        f"&sampleformat={rate}:{BITS}:2"
        for rate in RATES)
    return f"""# Written by gexis-core (ADR-0166); not read from /etc.
[server]
datadir = {run_dir}
threads = 2

[http]
enabled = false

[tcp]
enabled = true
bind_to_address = 127.0.0.1
port = {CONTROL_PORT}

[stream]
bind_to_address = ::
port = {STREAM_PORT}
codec = flac
chunk_ms = {CHUNK_MS}
buffer = {buffer_ms}
send_to_muted = false
{sources}

[streaming_client]
initial_volume = 100

[logging]
sink = system
filter = *:notice
"""


def client_env(host: str, host_id: str, latency_ms: int = 0, sampleformat: str | None = None) -> str:
    """The client unit's environment: the leader to play from, this player's
    stable id, the card's own delay, and a format only where the card cannot
    take the stream's (`sample_format_for`)."""
    opts = f"--sampleformat {sampleformat}" if sampleformat else ""
    return (f"GEXIS_SNAP_HOST={host}\nGEXIS_SNAP_PORT={STREAM_PORT}\nGEXIS_SNAP_ID={host_id}\n"
            f"GEXIS_SNAP_LATENCY={int(latency_ms)}\nGEXIS_SNAP_OPTS={opts}\n")


def sample_format_for(card: str | None, chain_takes_32: bool, rate: int | None = None,
                      any_rate: bool = True) -> str | None:
    """**What this player's client asks for**, as `<rate>:<bits>:<channels>`,
    or None to play the stream as it comes (32 bits, its own rate). A chain
    that cannot take 32 bits - a card offering 16 or 24 only, with no
    equaliser or conversion in front of it - gets the widest it takes;
    padding is undone exactly, so a 16-bit source arrives as it left. A rate
    the card lacks, where nothing in front of it converts (`any_rate`: the
    equaliser's resampler, HDMI's conversion), is converted to the card's
    highest, as the equaliser and Squeezelite's own resampler do."""
    bits = "*"
    if not chain_takes_32 and card is not None:
        formats = outputs.formats_of(card)
        if formats and "S32_LE" not in formats:
            bits = "24" if "S24_LE" in formats else "16" if "S16_LE" in formats else "*"
    to = "*"
    if rate and not any_rate and card is not None and outputs.takes_rate(card, rate) is False:
        top = outputs.top_rate(card)
        if top:
            to = str(top)
    return None if bits == "*" and to == "*" else f"{to}:{bits}:*"


async def _run(*args: str, timeout: float = 20) -> tuple[int, str]:
    try:
        proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE,
                                                    stderr=asyncio.subprocess.STDOUT)
    except OSError as exc:
        return 127, str(exc)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return 124, "timed out"
    return proc.returncode or 0, out.decode(errors="replace")


class Control:
    """**The server's JSON-RPC on its control port: one connection, kept**
    (bedroompi, 2026-10-28: a connection a call, every second, wrote two
    lines a time into a journal kept in memory). Replies are matched by id;
    the server's own notices - a client connecting or going, a stream
    starting - are passed to `on_notice`."""

    def __init__(self, port: int = CONTROL_PORT) -> None:
        self._port = port
        self._id = 0
        self._pending: dict[int, asyncio.Future] = {}
        self._writer: asyncio.StreamWriter | None = None
        self._reader: asyncio.Task | None = None
        self._connecting = asyncio.Lock()
        self.on_notice: Callable[[str, dict], None] = lambda method, params: None

    async def _connect(self, timeout: float) -> asyncio.StreamWriter:
        async with self._connecting:
            if self._writer is not None and not self._writer.is_closing():
                return self._writer
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", self._port), timeout)
            self._writer = writer
            self._reader = asyncio.create_task(self._read(reader))
            return writer

    async def _read(self, reader: asyncio.StreamReader) -> None:
        try:
            while line := await reader.readline():
                try:
                    message = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(message, dict):
                    continue
                waiting = self._pending.pop(message.get("id"), None) if "id" in message else None
                if waiting is not None:
                    if not waiting.done():
                        waiting.set_result(message)
                elif "method" in message:
                    try:
                        self.on_notice(message["method"], message.get("params") or {})
                    except Exception:  # noqa: BLE001 - a notice must not end the connection
                        logger.exception("multiroom: a server notice could not be handled")
        except (OSError, asyncio.IncompleteReadError):
            pass
        finally:
            self._writer = None
            for waiting in self._pending.values():
                if not waiting.done():
                    waiting.set_exception(ConnectionError("the server closed the control connection"))
            self._pending.clear()

    async def call(self, method: str, params: dict | None = None, timeout: float = 3.0) -> dict:
        writer = await self._connect(timeout)
        self._id += 1
        want = self._id
        answer = asyncio.get_running_loop().create_future()
        self._pending[want] = answer
        body = {"id": want, "jsonrpc": "2.0", "method": method, "params": params or {}}
        writer.write((json.dumps(body) + "\r\n").encode())
        try:
            await writer.drain()
            message = await asyncio.wait_for(answer, timeout)
        finally:
            self._pending.pop(want, None)
        if "error" in message:
            raise RuntimeError(f"{method}: {message['error']}")
        return message.get("result") or {}

    async def close(self) -> None:
        if self._writer is not None:
            self._writer.close()
            self._writer = None
        if self._reader is not None:
            self._reader.cancel()
            self._reader = None


class Snapcast:
    """The server, its feeder and the client, for one player.

    `serve(True)` while the player is in a group; `listen(host)` points the
    client at the leader (None stops it). `on_change` is told when the
    feeder's stream or the clients connected change, for the group's state.
    """

    def __init__(self, on_change: Callable[[], None] = lambda: None, *, run=_run,
                 control: Control | None = None, cards: Path = Path("/proc/asound/cards")) -> None:
        #: Told when the stream fed or the clients connected change.
        self.on_change = on_change
        self._run = run
        self._control = control or Control()
        self._cards = cards
        self._serving = False
        self._watch: asyncio.Task | None = None
        self._feeder: asyncio.subprocess.Process | None = None
        #: The rate being fed now, or None.
        self.rate: int | None = None
        #: What the client was last started with, or None while stopped.
        self._client: str | None = None
        #: Host ids of the clients connected to this player's server.
        self.connected: dict[str, float] = {}
        self._poll: asyncio.Task | None = None
        self._looking: asyncio.Task | None = None
        if hasattr(self._control, "on_notice"):
            self._control.on_notice = self._notice

    # -- the loopback ----------------------------------------------------------

    def card_loaded(self) -> bool:
        try:
            return f"[{outputs.GROUP_CARD}" in self._cards.read_text()
        except OSError:
            return False

    async def ensure_card(self, before_reload=None, after_reload=None) -> bool:
        """**The group's loopback, made if it is not there.** A player updated
        since its last start has the module's new options and not the card
        (Finding 139: guestpi's loopback was not even loaded). Loaded as the
        options say; loaded with the equaliser's card only, it is unloaded
        and loaded again, with the equaliser stopped around it
        (`before_reload`, `after_reload`)."""
        if self.card_loaded():
            return True
        code, _ = await self._run("modprobe", "snd-aloop")
        if self.card_loaded():
            return True
        if before_reload is not None:
            await before_reload()
        for _ in range(20):
            code, out = await self._run("modprobe", "-r", "snd-aloop")
            if code == 0:
                break
            # Something still holds it: a process letting go takes a moment.
            await asyncio.sleep(0.25)
        else:
            _, holders = await self._run("fuser", "-v", *[str(p) for p in Path("/dev/snd").glob("*")])
            logger.error("multiroom: snd-aloop stays in use (%s); held by: %s",
                         out.strip(), " ".join(holders.split())[:300])
        code, out = await self._run("modprobe", "snd-aloop")
        if after_reload is not None:
            await after_reload()
        if not self.card_loaded():
            logger.error("multiroom: no %s loopback after loading snd-aloop again (%s)",
                         outputs.GROUP_CARD, out.strip())
            return False
        logger.info("multiroom: snd-aloop loaded again with the %s card", outputs.GROUP_CARD)
        return True

    # -- the server ------------------------------------------------------------

    async def serve(self, on: bool) -> None:
        if on == self._serving:
            return
        self._serving = on
        if on:
            try:
                SERVER_CONF.parent.mkdir(parents=True, exist_ok=True)
                SERVER_CONF.write_text(server_config())
            except OSError as exc:
                logger.error("multiroom: cannot write %s: %s", SERVER_CONF, exc)
            await self._run("systemctl", "restart", SERVER_UNIT)
            self._watch = asyncio.create_task(self._watching())
            self._poll = asyncio.create_task(self._polling())
            logger.info("multiroom: the server is up")
        else:
            for task in (self._watch, self._poll):
                if task is not None:
                    task.cancel()
            self._watch = self._poll = None
            await self._stop_feeder()
            if hasattr(self._control, "close"):
                await self._control.close()
            await self._run("systemctl", "stop", SERVER_UNIT)
            self.connected = {}
            logger.info("multiroom: the server is down")
        self.on_change()

    async def _watching(self) -> None:
        """`alsactl monitor` on the group's loopback, as the equaliser watches
        its own: every *PCM Slave* change is looked at."""
        missing = False
        while True:
            if not self.card_loaded():
                # Said once, and looked at again now and then: the card comes
                # back only with the module (`ensure_card`).
                if not missing:
                    logger.warning("multiroom: no %s loopback to watch", outputs.GROUP_CARD)
                    missing = True
                await asyncio.sleep(30)
                continue
            missing = False
            try:
                proc = await asyncio.create_subprocess_exec(
                    "stdbuf", "-oL", "alsactl", "monitor", LOOPBACK,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
            except OSError as exc:
                logger.warning("multiroom: cannot watch the loopback: %s", exc)
                await asyncio.sleep(5)
                continue
            try:
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
            logger.warning("multiroom: the loopback's monitor exited; again in 2 s")
            await asyncio.sleep(2)

    async def _look(self) -> None:
        _, out = await self._run("amixer", "-D", LOOPBACK, "contents", timeout=5)
        stream = parse_contents(out)
        rate = stream.rate if stream is not None else None
        if stream is not None and (stream.fmt != "S32_LE" or stream.channels != 2):
            logger.warning("multiroom: a %s stream of %d channels cannot be sent to the group",
                           stream.fmt, stream.channels)
            rate = None
        if rate is not None and rate not in RATES:
            logger.warning("multiroom: %d Hz is not a rate the group carries", rate)
            rate = None
        if rate == self.rate and (rate is None or self._feeding()):
            return
        await self._stop_feeder()
        if rate is not None:
            await self._feed(rate)
        self.on_change()

    def _feeding(self) -> bool:
        return self._feeder is not None and self._feeder.returncode is None

    async def _feed(self, rate: int) -> None:
        pipe = RUN_DIR / str(rate)
        try:
            # **Read-write, never write-only** (guestpi, 2026-10-28): between
            # its reads the server has the pipe closed, and a write-only open
            # then fails (ENXIO) or waits. On Linux a pipe opened for both
            # opens at once, and the server finds a writer whenever it looks.
            fd = os.open(pipe, os.O_RDWR)
        except OSError as exc:
            logger.warning("multiroom: the server's %d Hz pipe is not open (%s)", rate, exc)
            return
        try:
            self._feeder = await asyncio.create_subprocess_exec(
                "arecord", "-q", "-D", f"{LOOPBACK},1,0", "-f", "S32_LE", "-r", str(rate),
                "-c", "2", "-t", "raw", "--buffer-time=40000",
                stdout=fd, stderr=asyncio.subprocess.DEVNULL)
        except OSError as exc:
            logger.warning("multiroom: cannot capture the loopback: %s", exc)
            return
        finally:
            os.close(fd)
        self.rate = rate
        await self.point_clients()
        logger.info("multiroom: the group plays %d Hz", rate)

    async def _stop_feeder(self) -> None:
        self.rate = None
        if self._feeder is not None:
            if self._feeder.returncode is None:
                self._feeder.terminate()
                try:
                    await asyncio.wait_for(self._feeder.wait(), 2)
                except asyncio.TimeoutError:
                    self._feeder.kill()
            self._feeder = None

    async def point_clients(self) -> None:
        """Every client of this server to the stream being fed (a client that
        connects later is pointed by `_polling`)."""
        if self.rate is None:
            return
        try:
            status = await self._control.call("Server.GetStatus")
            for group in status.get("server", {}).get("groups", []):
                if group.get("stream_id") != stream_id(self.rate):
                    await self._control.call("Group.SetStream",
                                             {"id": group["id"], "stream_id": stream_id(self.rate)})
        except (OSError, asyncio.TimeoutError, ConnectionError, RuntimeError) as exc:
            logger.warning("multiroom: could not point the clients at %d Hz: %s", self.rate, exc)

    def _notice(self, method: str, params: dict) -> None:
        """A client came or went, or a stream changed: who is connected is
        looked at again, once, at once."""
        if method.startswith(("Client.", "Server.", "Group.")):
            if self._looking is None or self._looking.done():
                self._looking = asyncio.get_running_loop().create_task(self._clients())

    async def _polling(self) -> None:
        """The clients, every 15 s besides the server's notices: a member
        that joins is pointed at the stream playing, and the group's state
        says who has caught up."""
        await asyncio.sleep(1.0)
        while True:
            await self._clients()
            await asyncio.sleep(15.0)

    async def _clients(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            status = await self._control.call("Server.GetStatus")
        except (OSError, asyncio.TimeoutError, ConnectionError, RuntimeError):
            return
        seen: dict[str, float] = {}
        stale = False
        for group in status.get("server", {}).get("groups", []):
            if self.rate is not None and group.get("stream_id") != stream_id(self.rate):
                stale = True
            for client in group.get("clients", []):
                # The client's id is the `--hostID` it was started with: the
                # member's stable id.
                cid = client.get("id")
                if client.get("connected") and cid:
                    seen[cid] = self.connected.get(cid, loop.time())
        if stale:
            await self.point_clients()
        if seen.keys() != self.connected.keys():
            self.connected = seen
            self.on_change()

    def caught_up(self, host_id: str, settle_s: float = 1.5) -> bool:
        """Whether `host_id`'s client is connected to this server and has had
        the buffer's time to fill."""
        since = self.connected.get(host_id)
        return since is not None and asyncio.get_running_loop().time() - since >= settle_s

    # -- the client ------------------------------------------------------------

    async def listen(self, host: str | None, host_id: str = "", sampleformat: str | None = None,
                     latency_ms: int = 0) -> None:
        """The client to the leader at `host` (this player's own server:
        `127.0.0.1`), or stopped with None. Restarted only when what it
        plays from changes."""
        wanted = None if host is None else client_env(host, host_id, latency_ms, sampleformat)
        if wanted == self._client:
            return
        self._client = wanted
        if wanted is None:
            await self._run("systemctl", "stop", CLIENT_UNIT)
            logger.info("multiroom: the client is stopped")
            return
        try:
            CLIENT_ENV.parent.mkdir(parents=True, exist_ok=True)
            CLIENT_ENV.write_text(wanted)
        except OSError as exc:
            logger.error("multiroom: cannot write %s: %s", CLIENT_ENV, exc)
            return
        await self._run("systemctl", "restart", CLIENT_UNIT)
        logger.info("multiroom: the client plays from %s", host)

    @property
    def listening(self) -> bool:
        return self._client is not None
