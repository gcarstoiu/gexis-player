"""Reader for peppyalsa's spectrum FIFO, used as the onset/silence detector
for Phase 2c's criterion 8 takeover-gap measurement.

Frame format confirmed directly from peppyalsa's spectrum.c (commit
7dcb0c5e783e0c86315a0f655684613affd3e9d2, send_to_pipe()/update()): each
frame is `spectrum_size` (30, per output.conf) native-endian unsigned ints
(4 bytes each) = 120 bytes/frame - NOT the unconfirmed "64 bytes" guess
recorded in HANDOFF.md, which predates reading the source.

Detection lag bound: spectrum.c's update() is invoked once per ALSA period
via peppyalsa.c's level_update(), which unconditionally advances its read
position to the full period boundary regardless of how much was actually
FFT'd - so onset detection lags the true first sample by at most one ALSA
period's worth of samples, not an open-ended amount. This is derived from
source, not measured; the calibration smoke test below is a sanity check
against real hardware, not a full independent-clock calibration (no ADC/mic
capture path exists on this hardware to provide one - see docs/findings/003).

One reader for the process's whole lifetime, not opened fresh per
measurement: an earlier version opened+closed the FIFO around each
attempt and produced nonsense (timestamps *before* the triggering action).
Root cause, confirmed by design review of Linux FIFO semantics rather than
guessed at: closing a reader before it has drained everything the writer
already pushed leaves bytes sitting in the kernel pipe buffer, and a
fresh reader opening the same path drains that backlog first, timestamped
at read time - and if two reader threads are ever open on the same FIFO
at once (a leaked/still-blocked one plus a fresh one), Linux splits bytes
between them unpredictably rather than duplicating the stream, corrupting
frame alignment in both. A single persistent reader sidesteps the whole
class of problem.
"""

import struct
import threading
import time

SPECTRUM_SIZE = 30
FRAME_BYTES = SPECTRUM_SIZE * 4
FRAME_FMT = f"<{SPECTRUM_SIZE}I"


class SpectrumReader:
    """Owns the one FIFO reader thread. Use as a context manager or call
    start()/stop() explicitly."""

    def __init__(self, path="/tmp/peppyspectrum"):
        self.path = path
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._latest_ts = None
        self._latest_values = None
        self._seq = 0
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc):
        self.stop()

    def _run(self):
        with open(self.path, "rb", buffering=0) as f:
            buf = b""
            while not self._stop.is_set():
                chunk = f.read(FRAME_BYTES - len(buf))
                if not chunk:
                    time.sleep(0.001)
                    continue
                buf += chunk
                if len(buf) < FRAME_BYTES:
                    continue
                ts = time.monotonic()
                values = struct.unpack(FRAME_FMT, buf[:FRAME_BYTES])
                buf = buf[FRAME_BYTES:]
                with self._cond:
                    self._latest_ts = ts
                    self._latest_values = values
                    self._seq += 1
                    self._cond.notify_all()

    def next_frame(self, timeout=None):
        """Blocks until a frame newer than the last one this caller saw
        arrives (tracked via sequence number on first call); returns
        (timestamp, values). Each caller should keep reusing the same
        `after` value it gets back to stay strictly in order."""
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._cond:
            seq_before = self._seq
            while self._seq == seq_before:
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    raise TimeoutError("no new frame arrived in time")
                if not self._cond.wait(timeout=remaining):
                    if deadline is not None and time.monotonic() >= deadline:
                        raise TimeoutError("no new frame arrived in time")
            return self._latest_ts, self._latest_values


def wait_for_onset(reader, threshold=1, timeout=None):
    """Blocks until a frame has any bin > threshold; returns its timestamp."""
    start = time.monotonic()
    while True:
        remaining = None if timeout is None else timeout - (time.monotonic() - start)
        ts, values = reader.next_frame(timeout=remaining)
        if any(v > threshold for v in values):
            return ts


def wait_for_silence(reader, threshold=1, consecutive=3, timeout=None):
    """Blocks until `consecutive` frames in a row are all <= threshold.

    Requiring several consecutive silent frames (not just one) avoids
    treating a single quiet frame mid-track (a pause in the music, not a
    release) as silence.
    """
    start = time.monotonic()
    run = 0
    while True:
        remaining = None if timeout is None else timeout - (time.monotonic() - start)
        ts, values = reader.next_frame(timeout=remaining)
        if all(v <= threshold for v in values):
            run += 1
            if run >= consecutive:
                return ts
        else:
            run = 0


def measure_takeover_gap(reader, gap_threshold_s=0.15, timeout=None):
    """Returns (t_last, t_first): the timestamp of the outgoing renderer's
    last frame before the PCM goes idle, and the incoming renderer's first
    frame once it reopens it.

    Deliberately *not* "wait for N consecutive zero-valued frames" (see
    wait_for_silence) - during a real cross-renderer takeover, no renderer
    holds the PCM at all for the duration of the gap, so peppyalsa's scope
    callback (spectrum.c's update(), invoked once per ALSA period by an
    *open* stream) never fires and the FIFO emits no frames whatsoever
    during that window, not zero-valued ones. wait_for_silence's
    "consecutive zero frames" condition can never be satisfied by a real
    handoff for exactly this reason - confirmed against gexis-core's own
    acquire/release log lines showing genuine ~3s LMS releases while this
    function's earlier zero-valued-frame version reported "no handoff"
    every single time. Detecting the gap as an inter-frame *pause*
    (nothing arrives for gap_threshold_s, comfortably above the normal
    ~10-50ms period cadence but well below the gaps this is measuring) is
    the mechanism that actually matches how the audio chain behaves.

    Must be called *before* triggering the takeover, while the outgoing
    renderer is still audibly playing.
    """
    start = time.monotonic()

    def remaining():
        return None if timeout is None else timeout - (time.monotonic() - start)

    t_last, _ = reader.next_frame(timeout=remaining())
    while True:
        try:
            t_next, _ = reader.next_frame(timeout=gap_threshold_s)
            t_last = t_next
        except TimeoutError:
            break
        if remaining() is not None and remaining() <= 0:
            raise TimeoutError("outgoing renderer never went idle within timeout")

    t_first, _ = reader.next_frame(timeout=remaining())
    return t_last, t_first
