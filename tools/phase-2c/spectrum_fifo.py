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
"""

import struct
import time

SPECTRUM_SIZE = 30
FRAME_BYTES = SPECTRUM_SIZE * 4
FRAME_FMT = f"<{SPECTRUM_SIZE}I"


def read_frames(path="/tmp/peppyspectrum"):
    """Yields (monotonic_timestamp, tuple_of_30_bin_values) as frames arrive.

    Blocking read, one frame at a time. A short read (FIFO writer restarted,
    reader/writer desync) is treated as a resync point, not an error -
    matches peppyalsa's own tolerance of readers attaching/detaching freely
    (Finding 002's side finding).
    """
    with open(path, "rb", buffering=0) as f:
        buf = b""
        while True:
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
            yield ts, values


def wait_for_onset(path="/tmp/peppyspectrum", threshold=1, timeout=None):
    """Blocks until a frame has any bin > threshold; returns its timestamp.

    threshold=1 (not 0) because "silence" should read as exactly all-zero
    bins on this chain - a threshold of 1 rejects a single stray nonzero
    bin from FFT/quantisation noise on a true-silence frame without
    requiring a calibrated noise floor. Revisit if false-positives appear
    empirically.
    """
    start = time.monotonic()
    for ts, values in read_frames(path):
        if any(v > threshold for v in values):
            return ts
        if timeout is not None and (time.monotonic() - start) > timeout:
            raise TimeoutError(f"no onset within {timeout}s")


def wait_for_silence(path="/tmp/peppyspectrum", threshold=1, consecutive=3, timeout=None):
    """Blocks until `consecutive` frames in a row are all <= threshold.

    Requiring several consecutive silent frames (not just one) avoids
    treating a single quiet frame mid-track (a pause in the music, not a
    release) as silence.
    """
    start = time.monotonic()
    run = 0
    for ts, values in read_frames(path):
        if all(v <= threshold for v in values):
            run += 1
            if run >= consecutive:
                return ts
        else:
            run = 0
        if timeout is not None and (time.monotonic() - start) > timeout:
            raise TimeoutError(f"no silence within {timeout}s")
