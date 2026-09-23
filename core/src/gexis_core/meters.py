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

import configparser
import errno
import logging
import math
import os
import stat
import struct
from pathlib import Path
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


def ensure_fifo(path: str) -> bool:
    """Create the FIFO if it is missing, writable by anyone.

    **Every writer is a different process under a different user** -
    peppyalsa loaded inside each renderer, this daemon for the passthrough
    pair - and the renderers are not ours to run as a chosen user. A FIFO in
    `/run/gexis` carries levels and nothing else, so the mode is permissive
    and the directory is what limits reach.

    Created here, by the daemon that runs as root, rather than left to
    whoever opens first: peppyalsa creates one itself if it can, and a
    renderer that cannot write the directory would simply go blind (ADR-0011,
    amended 2026-09-22).
    """
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        try:
            os.mkfifo(path, 0o666)
        except FileExistsError:
            if not stat.S_ISFIFO(os.stat(path).st_mode):
                logger.warning("meters: %s exists and is not a FIFO", path)
                return False
        os.chmod(path, 0o666)  # mkfifo's mode is masked by umask
        return True
    except OSError as exc:
        logger.warning("meters: cannot create %s: %s", path, exc)
        return False


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


#: **100 meter units of spectrum are this many dB.** peppyalsa's spectrum is
#: logarithmic (`logarithmic_amplitude 1`): it sends
#: `100 * log10(magnitude) / 4.82`, and a magnitude of 65535 is 96.3 dB above
#: one. So a unit is 0.963 dB, and attenuating the *spectrum* is a subtraction
#: where attenuating the linear VU level is a multiplication. Reading the two
#: as the same kind of number would put the bars in the wrong place at every
#: volume but full.
SPECTRUM_DB_FULL_SCALE = 20 * math.log10(65535)


def read_attenuation(path: Path) -> float:
    """The dB the device is cutting right now, from the file `volume.py`
    leaves it in. 0 when there is none, or when it cannot be read: a meter
    that shows the source is what this did before ADR-0057."""
    try:
        value = float(path.read_text().strip())
    except (OSError, ValueError):
        return 0.0
    return value if value > 0 else 0.0


#: **The dB a VU dial is marked for.** The faces in both packs run from −20
#: to about +3, and 0 VU sits around three quarters along the arc. Twenty dB
#: below that is the bottom stop.
VU_SCALE_DB = 20.0

#: **How much of the volume's travel the meters follow.**
#:
#: The volume curve spans 60 dB ([ADR-0054](../../../docs/decisions/0054-one-curve-and-the-renderers-own-number.md)),
#: and George has ruled that out of scope for changing: *"For sure we will
#: not narrow the volume curve though - that stays in place as is."* Applied
#: to the needle one-for-one, that travel is three times the dial's own, so
#: the needles reach the bottom stop at about 40% on the slider and the rest
#: of the range shows nothing - *"a bit quiet on the bottom part"*.
#:
#: **So the volume's full travel is mapped onto the dial's full travel**
#: rather than onto three of them. The meters still fall as the volume comes
#: down, by a third of the dB, which keeps the needle alive across the whole
#: slider. This is the one number that decides how far they fall; it is a
#: candidate for ADR-0022's inventory and is not on it.
METER_VOLUME_TRACKING = VU_SCALE_DB / 60.0


def attenuate(levels: Levels, db: float, tracking: float = METER_VOLUME_TRACKING) -> Levels:
    """`levels` as they would be after the device's own volume control.

    **The meter tap is upstream of it.** `pcm.output` is a `type meter` over
    the card, and the DAC attenuates in hardware afterwards, so the needles
    and the bars show the recording rather than what is coming out of the
    speakers ([ADR-0057](../../../docs/decisions/0057-the-meters-follow-the-volume.md)).
    George, 2026-09-23: *"Shouldn't the vu meters and spectrum amplitude be
    based on volume?"*

    **`tracking` scales the dB before it is applied**, because the volume's
    60 dB is three times what a VU dial is drawn for. See
    `METER_VOLUME_TRACKING`. At 1.0 this is the physically exact thing and
    the needles are at a tenth of scale by 40% on the slider.

    **The two scales are different kinds of number.** peppyalsa's meter
    level is linear amplitude, so this is a multiplication. Its spectrum is
    logarithmic - `100·log10(magnitude)/4.82`, a unit being 0.963 dB - so it
    is a subtraction. Treating them alike would put the bars in the wrong
    place at every volume but full.

    **Nothing to do at 0 dB**, which is also what fixed output looks like -
    there the device is not attenuating, so the meters show the source and
    no special case is needed to arrange it.
    """
    db = db * tracking
    if db <= 0:
        return levels
    gain = 10 ** (-db / 20)
    shift = db * 100 / SPECTRUM_DB_FULL_SCALE
    return Levels(
        max(0, round(levels.left * gain)),
        max(0, round(levels.right * gain)),
        tuple(max(0, round(b - shift)) for b in levels.bands),
    )


def read_declared_size(path: str) -> int | None:
    """`size` from the spectrum engine's `[current]` section, or None."""
    try:
        parser = configparser.ConfigParser(strict=False)
        parser.read(path)
        return parser.getint("current", "size")
    except (configparser.Error, ValueError, OSError):
        return None


def resample(bands: tuple[int, ...], want: int | None) -> tuple[int, ...]:
    """`bands` folded down to `want` values, by taking each group's peak.

    **Why this exists at all.** peppyalsa measures 30 bands; a skin draws as
    many bars as its artwork has room for, which is 20 to 22
    ([Finding 049](../../../docs/findings/049-the-spectrum-draws-more-bars-than-it-has-room-for.md)).
    A FIFO carries bytes, not messages, and PeppySpectrum reads `4 * size`
    of them at a time - so a 120-byte record read 88 bytes at a time makes
    every bar show a different band from one refresh to the next
    ([Finding 051](../../../docs/findings/051-the-spectrum-pipe-and-the-bars-must-agree.md)).
    The frame that goes down the pipe has to be the frame the reader expects.

    **The peak of each group, not the mean.** A bar on a spectrum display
    stands for the loudest thing in its range; averaging would pull every
    doubled band down and make the display quieter than the music.

    **Never upward.** Asked for more values than there are measurements this
    returns what it has: the pipe would then disagree with the reader again,
    which is bad, but inventing bands is worse and it cannot happen - the
    count is capped at the band count where it is computed.
    """
    have = len(bands)
    if not want or want == have or want > have or want < 1:
        return bands
    return tuple(max(bands[(i * have) // want : ((i + 1) * have) // want]) for i in range(want))


class FifoPassthrough:
    """ADR-0011's compatibility transport, and how our own PeppyMeter is fed:
    its `data.source type = pipe` points here, not at peppyalsa.

    Opening a FIFO for writing blocks until a reader arrives, so this opens
    non-blocking and simply has nowhere to write until PeppyMeter starts.
    """

    def __init__(
        self,
        meter_path: str,
        spectrum_path: str,
        spectrum_consumer_config: str | None = None,
    ) -> None:
        self._paths = {"meter": meter_path, "spectrum": spectrum_path}
        self._fds: dict[str, int | None] = {"meter": None, "spectrum": None}
        self._consumer_config = spectrum_consumer_config
        self._config_seen: tuple[int, int] | None = None
        self._declared: int | None = None
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

    def declared_bands(self) -> int | None:
        """How many bars the spectrum engine is about to draw, from its own
        config file. Re-read only when the file changes - the driver rewrites
        it on every skin change, and this is polled at the frame rate."""
        if not self._consumer_config:
            return None
        try:
            stat = os.stat(self._consumer_config)
        except OSError:
            return None
        key = (stat.st_mtime_ns, stat.st_size)
        if key != self._config_seen:
            self._config_seen = key
            self._declared = read_declared_size(self._consumer_config)
            logger.info("meters: the spectrum engine declares %s bars", self._declared)
        return self._declared

    def publish(self, levels: Levels) -> None:
        self._write("meter", struct.pack("<HH", levels.left, levels.right))
        bands = resample(levels.bands, self.declared_bands())
        self._write("spectrum", struct.pack(f"<{len(bands)}I", *bands))

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
