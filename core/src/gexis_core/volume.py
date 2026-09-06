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

**Echo suppression, amended 2026-09-06 after a real ratchet-to-zero was
measured on hardware.** Two scales (240 hardware steps, go-librespot's
own `volume_steps`, 100 on the tested build) cannot round-trip exactly,
and there are two feedback paths, not one: our own `set_raw` write shows
up on `alsactl monitor` as a change to sync outward again, *and*
go-librespot can echo our `POST /player/volume` back as its own
`"volume"` WS event, which this bridge would otherwise treat as a fresh
external change. A single boolean "skip exactly one incoming line" flag
(the previous approach) does not cover either case reliably: a single
mixer write can produce more than one `alsactl monitor` line (only the
first got skipped, the rest leaked through as "new" changes), and it did
nothing at all for the WS-echo path. Measured consequence, one real
sequence: 179, 172, 162, 140, 119, 97, 0/240, each hop ~50ms apart, one
direction, never stopping until it hit zero.

Replaced with a single shared timestamp, `_last_own_write`: anything
*we* write - either direction - arms a short window, and any incoming
signal (an `alsactl monitor` line, or a `"volume"` WS event) arriving
inside that window is treated as our own echo and dropped, however many
lines or events it produced. This is a mitigation, not a proof of
convergence: two independent *genuine* changes landing inside the same
window (a live slider drag against a near-simultaneous LMS change, say)
would have the second one dropped too. Not observed, but not excluded
either - the measured 325ms bridge round-trip (single deliberate
`amixer` change, logged separately) is the basis for the window below,
not a formal bound.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time

logger = logging.getLogger("gexis_core.volume")

# Covers the measured ~325ms round-trip (a single amixer change, through
# go-librespot and back) plus margin for a multi-line alsactl monitor
# burst from one write. Not a formal bound - see module docstring.
ECHO_WINDOW_S = 0.75

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
        self._last_own_write = 0.0
        spotify_adapter.on_volume_change(self._on_spotify_volume)

    def _within_echo_window(self) -> bool:
        return time.monotonic() - self._last_own_write < ECHO_WINDOW_S

    def _on_spotify_volume(self, value: int, max_: int) -> None:
        if max_ <= 0:
            logger.warning("volume: spotify reported max=%r, ignoring", max_)
            return
        if self._within_echo_window():
            logger.debug("volume: ignoring spotify volume event within echo window")
            return
        raw = round(value / max_ * HARDWARE_MAX)
        logger.info("volume: spotify -> hardware (%s/%s -> %s/240)", value, max_, raw)
        self._last_own_write = time.monotonic()
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
            if self._within_echo_window():
                # Our own set_raw write, possibly reported as more than
                # one line for a single change - every line inside the
                # window is our own echo, not just the first.
                continue
            raw = await get_raw(self._mixer_name)
            if raw is None or raw == last_raw:
                continue
            last_raw = raw
            steps = await self._spotify.get_volume_steps()
            logger.info("volume: hardware -> spotify (%s/240)", raw)
            self._last_own_write = time.monotonic()
            await self._spotify.set_volume(round(raw / HARDWARE_MAX * steps))
