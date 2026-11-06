# SPDX-License-Identifier: GPL-3.0-or-later
"""**The measurement microphone** (ADR-0175 item 9, decision 6): the miniDSP
UMIK-1, found by its USB identity, not its ALSA name (which carries its
gain); and what a run plays and hears through it.

**Played as music is** (item 4): into `output`, the renderers' own entry,
so the sweeps go through the same chain, card, volume and amplifier - the
stage in the path, which the run sets flat or to the cuts it checks.
**Heard at the microphone's own format** (24-bit at 48 kHz), through ALSA's
plug so a stereo and a mono unit read alike; its capture volume is set to
the full, which its sensitivity line is read at.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("gexis_core.room_mic")

#: miniDSP's UMIK-1 (research, 2026-11-05).
UMIK1 = "2752:0007"
NAME = "miniDSP UMIK-1"
PROC = Path("/proc/asound")
SOUND = Path("/sys/class/sound")
FS = 48000
#: How long the microphone listens before a signal starts and after it ends:
#: the chain's start (the loopback, CamillaDSP, the card) and the room's
#: decay.
LEAD_S = 0.3
TAIL_S = 1.5
PLAYBACK = "output"


@dataclass(frozen=True)
class Microphone:
    card: str           # ALSA's card id, e.g. U18dB
    gain_db: float | None   # from the product string: the gain its switches set

    @property
    def device(self) -> str:
        return f"plughw:CARD={self.card},DEV=0"


def _read(path: Path) -> str:
    try:
        return path.read_text()
    except OSError:
        return ""


def _product(number: str, sound: Path) -> str:
    try:
        device = (sound / number / "device").resolve()
    except OSError:
        return ""
    return " ".join(_read(device.parent / "product").split())


_GAIN = re.compile(r"Gain:\s*(-?\d+(?:\.\d+)?)\s*dB", re.IGNORECASE)


def find(proc: Path = PROC, sound: Path = SOUND) -> tuple[str, Microphone | None]:
    """**What is plugged in**: ("found", the UMIK-1), ("other", None) for a
    USB card that only records and is not one, or ("absent", None)."""
    other = False
    for card_dir in sorted(proc.glob("card[0-9]*")):
        usbid = _read(card_dir / "usbid").strip()
        if not usbid:
            continue
        if usbid == UMIK1:
            card = _read(card_dir / "id").strip()
            m = _GAIN.search(_product(card_dir.name, sound))
            if card:
                return "found", Microphone(card, float(m.group(1)) if m else None)
        records = any(card_dir.glob("pcm*c"))
        plays = any(card_dir.glob("pcm*p"))
        if records and not plays:
            other = True
    return ("other", None) if other else ("absent", None)


def spl_offset(cal, mic: Microphone | None = None) -> float:
    """**dB SPL from a level in dB of full scale** with this calibration: as
    REW reads the sensitivity line - the RMS level at 94 dB SPL with the
    capture at full volume. When the microphone's switches were changed
    from the gain the file was made at, the difference moves it."""
    offset = 94.0 - cal.sens_db
    made_at = getattr(cal, "gain_db", None)
    if mic is not None and mic.gain_db is not None and made_at is not None:
        offset -= mic.gain_db - made_at
    return offset


async def _exec(*args: str, stdin=None, stdout=None):
    return await asyncio.create_subprocess_exec(*args, stdin=stdin, stdout=stdout,
                                                stderr=asyncio.subprocess.PIPE)


class Audio:
    """What a run plays and hears, on the player."""

    def __init__(self, mic: Microphone, cal, playback: str = PLAYBACK, exec_=_exec):
        self.mic = mic
        self._cal = cal
        self._playback = playback
        self._exec = exec_

    def spl_offset(self, cal) -> float:
        return spl_offset(cal, self.mic)

    async def prepare(self) -> None:
        """The capture volume at its full and switched on, as the
        sensitivity line is read at (item 9: its gain set explicitly)."""
        proc = await self._exec("amixer", "-q", "-c", self.mic.card, "sset", "Mic", "100%", "cap",
                                stdout=asyncio.subprocess.DEVNULL)
        _, err = await proc.communicate()
        if proc.returncode:
            # A unit without a capture control has nothing to set.
            logger.info("room: %s's capture volume not set (%s)", self.mic.card, err.decode(errors="replace").strip())

    async def play(self, signal, channel: int | None, tail_s: float = TAIL_S):
        """`signal` played - to `channel` alone, to the channels of a tuple,
        or to both with None - while the microphone listens from `LEAD_S`
        before to `tail_s` after; the recording, as floats."""
        import numpy as np
        signal = np.clip(np.asarray(signal, dtype=float), -1.0, 1.0)
        frames = np.zeros((len(signal), 2))
        for c in ((0, 1) if channel is None else (channel,) if isinstance(channel, int) else tuple(channel)):
            frames[:, c] = signal
        data = (frames * (2 ** 31 - 1)).astype("<i4").tobytes()
        samples = int((LEAD_S + len(signal) / FS + tail_s) * FS)
        rec = await self._exec("arecord", "-q", "-D", self.mic.device, "-f", "S32_LE", "-r", str(FS),
                               "-c", "1", "-t", "raw", "-s", str(samples), stdout=asyncio.subprocess.PIPE)
        reading = asyncio.create_task(rec.stdout.read())
        play = None
        try:
            await asyncio.sleep(LEAD_S)
            play = await self._exec("aplay", "-q", "-D", self._playback, "-f", "S32_LE", "-r", str(FS),
                                    "-c", "2", "-t", "raw", stdin=asyncio.subprocess.PIPE,
                                    stdout=asyncio.subprocess.DEVNULL)
            _, perr = await play.communicate(data)
            if play.returncode:
                raise RuntimeError(f"aplay: {perr.decode(errors='replace').strip()}")
            raw = await asyncio.wait_for(reading, len(signal) / FS + LEAD_S + tail_s + 5)
            await rec.wait()
        except BaseException:
            # Cancelled (or broken) mid-signal: the sound stops now.
            for p in (play, rec):
                if p is not None and p.returncode is None:
                    p.kill()
            reading.cancel()
            raise
        if rec.returncode:
            err = (await rec.stderr.read()).decode(errors="replace").strip()
            raise RuntimeError(f"arecord: {err}")
        recording = np.frombuffer(raw[: len(raw) // 4 * 4], dtype="<i4").astype(float) / 2 ** 31
        if len(recording) < samples * 0.9:
            raise RuntimeError("the microphone stopped")
        return recording
