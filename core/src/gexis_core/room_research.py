# SPDX-License-Identifier: GPL-3.0-or-later
"""**Phase 37's research build** (ADR-0187, never released): what a run
measured, kept on the player for analysis - each sweep's impulse response
and the timing step's arrivals, never a recording. Deleted after the
analysis."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

DIR = Path("/var/lib/gexis/room-research")
#: How much of each sweep's response is kept around its arrival (s).
BEFORE_S, AFTER_S = 0.02, 2.0
#: Around each of the timing step's three arrivals (s).
TIMING_BEFORE_S, TIMING_AFTER_S = 0.01, 0.2


class Keeper:
    """One run's responses, saved when the run ends (`save`)."""

    def __init__(self, fs: int) -> None:
        self.fs = fs
        self.stamp = time.strftime("%Y%m%d-%H%M%S")
        self.sweeps: list[dict] = []
        self.irs: list = []
        self.timings: list[dict] = []
        self.timing_irs: list = []
        self.noise: dict[str, list] = {}

    def sweep(self, *, position: int, channel: str, checking: bool, scale: float, ir_full,
              recording_len: int, mark: float | None = None) -> int:
        """A sweep's whole deconvolved response, kept from just before its
        arrival, and where its timing mark arrived (ADR-0187 C4, samples
        from the recording's start, on the same clock as `peak` and
        `start`); its index for `kept`."""
        import numpy as np
        ir_full = np.asarray(ir_full)
        peak = int(np.argmax(np.abs(ir_full[: len(ir_full) // 2])))
        a = max(0, peak - int(BEFORE_S * self.fs))
        part = ir_full[a:a + int((BEFORE_S + AFTER_S) * self.fs)]
        self.irs.append(np.asarray(part, dtype=np.float32))
        self.sweeps.append({"position": position, "channel": channel, "checking": checking,
                            "scale": float(scale), "peak": peak, "start": a,
                            "recording_len": int(recording_len), "kept": False,
                            "mark": None if mark is None else float(mark)})
        return len(self.sweeps) - 1

    def kept(self, ids, chosen) -> None:
        for k in chosen or ():
            self.sweeps[ids[k]]["kept"] = True

    def timing(self, *, position: int, ir_full, slot: int, got) -> None:
        """The timing step's three arrivals (left, right, left), each from
        just before it."""
        import numpy as np
        ir_full = np.asarray(ir_full)
        if len(ir_full) < 3 * slot:
            return
        first = int(np.argmax(np.abs(ir_full[:slot])))
        a = max(0, first - int(TIMING_BEFORE_S * self.fs))
        n = int((TIMING_BEFORE_S + TIMING_AFTER_S) * self.fs)
        parts = [ir_full[k * slot + a:k * slot + a + n] for k in range(3)]
        if any(len(p) < n for p in parts):
            return
        self.timing_irs.append(np.asarray(parts, dtype=np.float32))
        self.timings.append({"position": position, "first": first,
                             "late_s": None if got is None else got.late_s,
                             "same_polarity": None if got is None else got.same_polarity,
                             "alike": None if got is None else got.alike})

    def noise_curve(self, key, curve) -> None:
        self.noise[repr(key)] = [float(x) for x in curve]

    def save(self, meta: dict) -> None:
        """Everything kept, as one compressed file and its notes; nothing
        raised - a failure here never touches the run."""
        if not DIR.parent.is_dir():      # not on a player (the tests)
            return
        try:
            import numpy as np
            DIR.mkdir(parents=True, exist_ok=True)
            base = DIR / self.stamp
            arrays = {f"ir{k}": ir for k, ir in enumerate(self.irs)}
            arrays.update({f"timing{k}": t for k, t in enumerate(self.timing_irs)})
            np.savez_compressed(f"{base}.npz", **arrays)
            notes = dict(meta, fs=self.fs, sweeps=self.sweeps, timings=self.timings, noise=self.noise,
                         before_s=BEFORE_S, after_s=AFTER_S, timing_before_s=TIMING_BEFORE_S)
            Path(f"{base}.json").write_text(json.dumps(notes))
            logger.info("room research: %d sweeps and %d timing readings kept as %s",
                        len(self.irs), len(self.timing_irs), base)
        except Exception:  # noqa: BLE001
            logger.exception("room research: could not keep the run's responses")
