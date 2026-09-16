# SPDX-License-Identifier: GPL-3.0-or-later
"""The visualisation service (Phase 5 criterion 1, ADR-0011).

Reads peppyalsa's two FIFOs and republishes on three transports. **Sole
reader by necessity**: a FIFO splits its bytes between readers, so the
vendored PeppyMeter cannot read peppyalsa's pipes while this does — it is fed
from the passthrough pipes here (ADR-0011, amended 2026-09-16).

Frame formats are Finding 024's, measured on a live stream: the meter pipe
carries one 4-byte frame (two little-endian `uint16`, left and right), the
spectrum pipe exactly `bands` × 4 bytes of little-endian `uint32`. Both sit
in 0-100 already, so nothing is rescaled here.
"""
from __future__ import annotations

import errno
import logging
import os
import struct
from dataclasses import dataclass

logger = logging.getLogger("gexis_core.meters")

METER_FRAME = 4
SPECTRUM_BANDS = 30
SPECTRUM_FRAME = SPECTRUM_BANDS * 4
#: Read generously and keep the last whole frame: both upstream consumers do
#: the same, because a backlog of levels is worthless - only the newest is
#: true of the audio playing now.
READ_CHUNK = 65536


@dataclass(frozen=True)
class Levels:
    left: int
    right: int
    bands: tuple[int, ...]

    @property
    def mono(self) -> int:
        return round((self.left + self.right) / 2)

    def to_json(self) -> dict:
        return {"left": self.left, "right": self.right, "mono": self.mono, "bands": list(self.bands)}


def parse_meter(frame: bytes) -> tuple[int, int]:
    return struct.unpack("<HH", frame)


def parse_spectrum(frame: bytes) -> tuple[int, ...]:
    return struct.unpack(f"<{len(frame) // 4}I", frame)


def open_fifo(path: str) -> int | None:
    """Non-blocking, so a pipe nobody is writing to never stalls this service
    (Finding 002: peppyalsa does not block on a missing reader either)."""
    try:
        return os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError as exc:
        logger.warning("meters: cannot open %s: %s", path, exc)
        return None


def read_latest_frame(fd: int, frame_size: int) -> bytes | None:
    """The newest whole frame available, or None when nothing is queued."""
    try:
        data = os.read(fd, READ_CHUNK)
    except BlockingIOError:
        return None
    except OSError as exc:
        if exc.errno == errno.EAGAIN:
            return None
        raise
    if len(data) < frame_size:
        return None
    end = len(data) - (len(data) % frame_size)
    return data[end - frame_size : end]


class FifoSource:
    """Both pipes, polled together."""

    def __init__(self, meter_path: str, spectrum_path: str, bands: int = SPECTRUM_BANDS) -> None:
        self._meter_path = meter_path
        self._spectrum_path = spectrum_path
        self._spectrum_frame = bands * 4
        self._bands = bands
        self._meter_fd: int | None = None
        self._spectrum_fd: int | None = None
        self._last = Levels(0, 0, (0,) * bands)

    def open(self) -> None:
        if self._meter_fd is None:
            self._meter_fd = open_fifo(self._meter_path)
        if self._spectrum_fd is None:
            self._spectrum_fd = open_fifo(self._spectrum_path)

    def read(self) -> Levels:
        """The current levels. Unchanged values when a pipe has nothing new:
        silence and "no frame this tick" are different things, and only the
        source knows which - holding the last frame is what both upstream
        consumers do."""
        self.open()
        left, right = self._last.left, self._last.right
        bands = self._last.bands

        if self._meter_fd is not None:
            frame = read_latest_frame(self._meter_fd, METER_FRAME)
            if frame is not None:
                left, right = parse_meter(frame)
        if self._spectrum_fd is not None:
            frame = read_latest_frame(self._spectrum_fd, self._spectrum_frame)
            if frame is not None:
                bands = parse_spectrum(frame)

        self._last = Levels(left, right, bands)
        return self._last

    def close(self) -> None:
        for fd in (self._meter_fd, self._spectrum_fd):
            if fd is not None:
                os.close(fd)
        self._meter_fd = self._spectrum_fd = None


class FifoPassthrough:
    """ADR-0011's compatibility transport, and how our own PeppyMeter is fed:
    its `data.source type = pipe` points here, not at peppyalsa.

    Opening a FIFO for writing blocks until a reader arrives, so this opens
    non-blocking and simply has nowhere to write until PeppyMeter starts.
    """

    def __init__(self, meter_path: str, spectrum_path: str) -> None:
        self._paths = {"meter": meter_path, "spectrum": spectrum_path}
        self._fds: dict[str, int | None] = {"meter": None, "spectrum": None}
        for path in self._paths.values():
            self._make(path)

    @staticmethod
    def _make(path: str) -> None:
        try:
            os.mkfifo(path, 0o644)
        except FileExistsError:
            pass
        except OSError as exc:
            logger.warning("meters: cannot create %s: %s", path, exc)

    def _fd(self, which: str) -> int | None:
        if self._fds[which] is None:
            try:
                self._fds[which] = os.open(self._paths[which], os.O_WRONLY | os.O_NONBLOCK)
            except OSError:
                return None  # no reader yet; normal
        return self._fds[which]

    def publish(self, levels: Levels) -> None:
        self._write("meter", struct.pack("<HH", levels.left, levels.right))
        self._write("spectrum", struct.pack(f"<{len(levels.bands)}I", *levels.bands))

    def _write(self, which: str, payload: bytes) -> None:
        fd = self._fd(which)
        if fd is None:
            return
        try:
            os.write(fd, payload)
        except BlockingIOError:
            # The reader is behind. Dropping this frame is correct: the next
            # one is truer than a queued stale one.
            pass
        except OSError as exc:
            logger.info("meters: %s reader went away (%s)", which, exc)
            os.close(fd)
            self._fds[which] = None

    def close(self) -> None:
        for which, fd in self._fds.items():
            if fd is not None:
                os.close(fd)
            self._fds[which] = None
