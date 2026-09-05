# Finding 004 — the tail artefact is `snd-aloop`, not the meter plugin

**Date:** 2026-09-04
**System:** `rig` — as Finding 003.
**Question:** Does the meter plugin cause the terminal frame mismatch reported in
Finding 003?
**Answer:** No. The same artefact occurs with the plugin removed.

---

## Why this test was run

Finding 003 concluded the meter plugin lost the final 768 frames of a stream at
S32_LE/192000, on the evidence of one run with the plugin and one control run
without.

A subsequent grid sweep, run twice by chance, showed the same cell producing
different results between runs. That variance made a single-run control
insufficient, so the A/B was repeated properly.

## Method

One condition — **S32_LE / 192000**, chosen because it was the cell that had
reproduced most consistently. Five seconds of white noise, nine-second capture
window, twenty runs through each path.

```
METER    aplay -D looptest              (type meter + peppyalsa scope)
CONTROL  aplay -D hw:Loopback,0,0       (no plugin)
```

The comparison distinguishes a contiguous terminal run from scattered
differences, which the earlier grid script did not.

## Result

| Path | Clean | Failed | Bytes differing on failure |
|---|---|---|---|
| METER (`looptest`) | 8 / 20 | 12 / 20 | 6094, every time |
| CONTROL (`hw:Loopback,0,0`) | 14 / 20 | 6 / 20 | 6102, every time |

**Both paths fail. The control fails.**

Three observations:

**The plugin is not the cause.** A defect appearing with the plugin removed
cannot be attributed to the plugin. Finding 003's causal conclusion is
withdrawn.

**A single clean control run proves nothing.** The control was clean in 14 of 20
runs — about 70%. The original control run being clean was more likely than not
by chance alone.

**No failure is a tail.** Every failure in both paths is classified SCATTER, not
TAIL. Finding 003's "768 frames lost" and the grid's apparently compelling
constant of 4 ms across rates both depended on assuming a contiguous run to the
end of the file. There is no such run.

## Interpretation, stated as inference

The differing byte counts are **identical within each path across every failing
run** — 6094 for the meter path, 6102 for the control. A timing artefact would
be expected to vary. Constant counts suggest something deterministic: most
plausibly the capture window catching a fixed region of `snd-aloop` ring-buffer
content after playback ends, with the 8-byte difference between paths
corresponding to a one-frame offset.

**This is inference from the numbers, not a mechanism established by
investigation.** The `snd-aloop` implementation has not been read.

## What this means for the product

**The metering path has no known defect.** The bit-transparency result in
Finding 003 stands and is strengthened: eight fully clean runs through the meter
plugin, and no interior difference in any run.

**This is a limitation of the measurement rig, not of the audio chain.**
`snd-aloop` runs playback and capture as independent free-running streams, and
the artefact is a property of that arrangement.

**Any future test using `snd-aloop` must be repeated.** A single run has roughly
a 30% chance of a spurious failure and a 70% chance of a spurious pass,
depending on which way it is used. Test tooling built on this rig should run a
condition multiple times and report the distribution, not a single verdict.

## Not established

- The mechanism. `snd-aloop` has not been read, and the constant-byte-count
  explanation above is inference.
- Whether the artefact would disappear with a synchronised start, a longer
  drain, or `--disable-resample`-style options on `aplay` and `arecord`.
- Whether it varies with rate or format. Only one condition was tested twenty
  times; the grid data is unreliable for the reasons in Finding 003.
- Whether any comparable artefact exists on the real DAC path. It cannot be
  tested the same way — the DAC2 HD has no ADC.

## Reproduction

The script is `ab.sh`, structured as: generate one source file, then for each of
`looptest` and `hw:Loopback,0,0`, run twenty capture-and-compare cycles and print
verdict, differing byte count, and frames lost where the differences form a
contiguous terminal run.

**Stopping point.** Investigation stopped here deliberately. The question that
mattered — does the meter plugin alter samples — is answered. Establishing the
mechanism of an `snd-aloop` measurement artefact would cost more than the answer
is worth, since the artefact affects only the rig and not the product.
