"""Volume bridge (criterion 5).

The hardware mixer is the single source of truth (ADR-0018: "one global
control shared by all renderers"). This keeps go-librespot's own volume in
sync with it. Reads and writes go through `amixer -D output ...` - the
same "output" ctl indirection squeezelite-mixer-check.sh uses, not a
direct `hw:sndrpihifiberry` reference (ADR-0009).

**Subscribed, not polled** (ADR-0018): `alsactl monitor` is spawned once
and read as a line stream, rather than periodically re-reading `amixer`.

**Scope, matching ADR-0018's own "Unverified" section:** the
hardware -> Spotify direction is implemented with confidence (amixer plus
go-librespot's documented POST /player/volume). The reverse direction
(Spotify -> hardware) depends on the "volume" WS event's undocumented
payload shape (adapters/spotify.py) and is best-effort. No bluez-alsa
AVRCP bridging is implemented - ADR-0018 leaves whether that's even
possible as an open question, not something to guess an implementation
for here.
"""
from __future__ import annotations

import asyncio
import logging
import re

logger = logging.getLogger("gexis_core.volume")

MIXER_DEVICE = "output"
HARDWARE_MAX = 240  # ADR-0018: 240 steps, 0=mute, 240=0dB
_VALUE_RE = re.compile(rb"Playback (\d+) \[")


async def get_raw(mixer_name: str) -> int | None:
    proc = await asyncio.create_subprocess_exec(
        "amixer",
        "-D",
        MIXER_DEVICE,
        "sget",
        mixer_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    m = _VALUE_RE.search(out)
    return int(m.group(1)) if m else None


async def set_raw(mixer_name: str, value: int) -> None:
    value = max(0, min(HARDWARE_MAX, value))
    proc = await asyncio.create_subprocess_exec(
        "amixer",
        "-D",
        MIXER_DEVICE,
        "sset",
        mixer_name,
        f"{value}",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()


class VolumeBridge:
    def __init__(self, mixer_name: str, spotify_adapter) -> None:
        self._mixer_name = mixer_name
        self._spotify = spotify_adapter
        self._suppress_echo = False
        spotify_adapter.on_volume_change(self._on_spotify_volume)

    def _on_spotify_volume(self, value: int, max_: int) -> None:
        if max_ <= 0:
            logger.warning("volume: spotify reported max=%r, ignoring", max_)
            return
        raw = round(value / max_ * HARDWARE_MAX)
        logger.info("volume: spotify -> hardware (%s/%s -> %s/240)", value, max_, raw)
        self._suppress_echo = True
        asyncio.create_task(set_raw(self._mixer_name, raw))

    async def run(self) -> None:
        """Watch `alsactl monitor` and push hardware changes to Spotify."""
        proc = await asyncio.create_subprocess_exec(
            "alsactl",
            "monitor",
            stdout=asyncio.subprocess.PIPE,
        )
        assert proc.stdout is not None
        last_raw: int | None = None
        while True:
            line = await proc.stdout.readline()
            if not line:
                logger.warning("volume: alsactl monitor exited, restarting in 5s")
                await asyncio.sleep(5)
                return await self.run()
            if self._suppress_echo:
                # The write we just issued will itself show up as an
                # event; skip exactly one round rather than re-derive
                # "did this event come from us".
                self._suppress_echo = False
                continue
            raw = await get_raw(self._mixer_name)
            if raw is None or raw == last_raw:
                continue
            last_raw = raw
            steps = await self._spotify.get_volume_steps()
            logger.info("volume: hardware -> spotify (%s/240)", raw)
            await self._spotify.set_volume(round(raw / HARDWARE_MAX * steps))
