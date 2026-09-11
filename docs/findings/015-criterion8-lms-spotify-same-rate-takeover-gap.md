# Finding 015 — Criterion 8, LMS↔Spotify same-rate takeover-gap distribution

**Date:** 2026-09-11
**System:** `gexis`, `v0.2.1-15-g2396ea2-dirty` plus this session's live-deployed, uncommitted-to-image fixes (Finding 014's `SpotifyAdapter.device_freed`, Finding 013 §1's `stop_unit`/`restart_after_release`) - not yet folded into a rebuilt image.
**Question:** criterion 8 - "time from stop of renderer A to first sample of renderer B" - for the LMS↔Spotify pair at the same sample rate, ≥20 runs per direction.
**Scope:** both renderers playing 44.1kHz content, confirmed directly (`/proc/asound/card5/pcm0p/sub0/status`'s `hw_params` showed `rate: 44100` for LMS's track; go-librespot's own `/status` reported `"sample_rate": 44100` for Spotify's), not assumed from either side's format label alone. Both directions measured entirely via `tools/phase-2c/spectrum_fifo.py`'s `measure_takeover_gap` (one instrument for both edges of the gap - see `takeover_gap.py`'s own module docstring for why). **Not in scope here:** cross-rate LMS↔Spotify, any Bluetooth-involving pair (both still need their own setup/George live as the audio source, per HANDOFF's next actions) - this finding is the same-rate LMS↔Spotify leg only.

## Method note: two of the three batches predate a same-day fix

Three real batches went into the combined LMS-to-Spotify numbers below,
run across the session in which Finding 014 (the ALSA-open race) and
Finding 013 §1's recurrence (the restart-storm) were found and fixed:

- Batch 1 (n=5): immediately after deploying Finding 014's fix, before
  the restart-storm recurrence was found.
- Batch 2 (n=20 attempted, 16 succeeded): where the restart-storm
  recurrence happened, at round 16 - the 4 skipped rounds are excluded
  from the stats below, not counted as failed gap measurements (they
  never produced one; see Finding 013 §1's addendum for what happened).
- Batch 3 (n=15): after deploying the restart-storm fix, zero
  interruptions.

All three batches used the *same* gap-measurement mechanism throughout
(the spectrum FIFO instrument, unaffected by which squeezelite-restart
mechanism happened to be active) - only the *reliability* of collecting
a full batch changed between them, not what a successful round measured.
Combining all 36 successful individual measurements across all three
batches is therefore a like-for-like aggregate, not a mix of different
things being measured.

## Results

### LMS → Spotify (n=36, combined across all three batches)

| | |
|---|---|
| min | 895.5 ms |
| max | 2593.0 ms |
| mean | 1631.5 ms |
| median | 1827.8 ms |
| stdev | 400.3 ms |

### Spotify → LMS (n=20, one clean batch, zero skips)

| | |
|---|---|
| min | 4107.5 ms |
| max | 4235.5 ms |
| mean | 4173.3 ms |
| median | 4170.9 ms |
| stdev | 33.2 ms |

## A real, notable asymmetry - not yet explained

Spotify→LMS is both **~2.5x slower** and **~12x more consistent**
(stdev 33.2ms vs. 400.3ms) than LMS→Spotify. Two very different-shaped
distributions, not just different means:

- **LMS→Spotify's spread** is plausibly explained by this session's own
  evidence: Finding 014's `device_freed()` retry and go-librespot's own
  near-immediate ALSA-open attempt interact with LMS's own release timing
  (typically well under a second, occasionally needing the polite-grace
  window or beyond) in a way that varies round to round - the two
  fastest measurements (895.5ms, 899.7ms) and the slowest (2593.0ms) came
  from otherwise-identical rounds.
- **Spotify→LMS's tightness** (a ~130ms spread across all 20 rounds)
  suggests a much more deterministic mechanism on this side - consistent
  with go-librespot's own release (`/player/stop`, measured elsewhere in
  this project at <100ms) freeing the device quickly and predictably,
  with LMS/squeezelite's own acquisition-side startup work (not its
  release path) dominating the total and behaving consistently.

**Neither side of this asymmetry is root-caused here** - this finding
reports the distribution, not why LMS's own acquisition takes ~4.1-4.2s
where Spotify's takes ~0.9-2.6s. Squeezelite's own startup sequence
(mixer check, ALSA device open, LMS's own status handshake) is the
likely place to look, not chased further this session.

## What this means for criteria 9 and 10

**Criterion 9** (write the actual takeover-gap finding once real numbers
exist) is satisfied for this one pair/rate combination by this finding -
cross-rate and Bluetooth pairs still need their own measurement before
criterion 9 is fully closed.

**Criterion 10** (does the measured gap need a UI transition screen -
George's call) now has real numbers to decide against for this pair:
LMS→Spotify's median 1.8s and Spotify→LMS's ~4.2s are both long enough
that a user would plausibly notice silence and wonder whether anything
is happening, particularly on the slower leg - but this is data for
George's decision, not a recommendation made here.
