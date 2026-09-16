# Finding 024 — peppyalsa's two FIFOs, measured on a live stream

**Date:** 2026-09-16
**Question:** ADR-0011 recorded the FIFO byte format as undetermined. Reading
the consumers' source (2026-09-16) said what they *expect*; this is what
peppyalsa actually writes.
**System:** `gexis` on the current image, music playing (George), peppyalsa
configured as ADR-0011 records: `meter_max 100`, `spectrum_max 100`,
`spectrum_size 30`.

## Measured

| pipe | read size | frame | values seen |
|---|---|---|---|
| `/tmp/peppymeter` | 4 bytes, never more | `<HH` — left, right, little-endian `uint16` | 60, 63 |
| `/tmp/peppyspectrum` | **exactly 120 bytes, every one of 97 reads** | 30 × `<I`, little-endian `uint32` per band | 26-62 across bands, changing per frame |

Both match what `PeppyMeter/datasource.py` and `PeppySpectrum/spectrum.py`
expect, so the consumers' reading of the format is confirmed rather than
merely plausible. Values sit inside 0-100, consistent with the configured
maxima; no scaling of our own is needed to feed either consumer.

The meter pipe yielded one frame per read — peppyalsa writes a frame at a
time and a reader gets the newest, which is why both consumers discard
everything but the last frame rather than draining a backlog.

## Not established

- **Frame rate.** Reads were polled at 50 Hz and 97 landed in 2 s; that
  measures the poll, not peppyalsa's write rate.
- **Behaviour at silence and at clipping** — one sample of ordinary music.
- **Two readers.** Not attempted. ADR-0011's amendment assumes bytes would be
  split between them; that is standard FIFO behaviour, not something measured
  here.
