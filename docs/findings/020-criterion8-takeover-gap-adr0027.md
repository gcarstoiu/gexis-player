# Finding 020 — Criterion 8: the takeover gap under ADR-0027

**Date:** 2026-09-12
**System:** `gexis`, flashed image `v0.2.1-51-g89dca15-dirty` — the first image containing ADR-0027, Finding 016's polling fix and blocker 4's volume fix. Nothing hot-patched; everything measured here is what the image ships.
**Question:** criterion 8 — "time from stop of renderer A to first sample of renderer B", as a distribution over ≥20 runs.
**Supersedes:** [Finding 015](015-criterion8-lms-spotify-same-rate-takeover-gap.md)'s numbers entirely. Those were measured against the release mechanism ADR-0027 replaced and are now only of historical interest.

## Result

| direction | n | min | max | mean | **median** | stdev |
|---|---|---|---|---|---|---|
| LMS → Spotify | **33** | 192.0 | 781.2 | 263.1 | **224.6 ms** | 128.2 |
| Spotify → LMS | **27** | 215.5 | 447.0 | 345.8 | **335.2 ms** | 61.3 |

Against Finding 015, same pair, same rate, same instrument:

| direction | Finding 015 | this finding | |
|---|---|---|---|
| LMS → Spotify | 1827.8 ms | **224.6 ms** | 8.1× faster |
| Spotify → LMS | 4170.9 ms | **335.2 ms** | 12.4× faster |

**Spotify → LMS is the result that matters.** Finding 015 measured 4170.9 ms
with a stdev of only 33.2 ms, and flagged that determinism as unexplained.
It was squeezelite's ALSA retry tick — a fixed 5.00s cadence, not tunable
(`squeezelite -?` has no retry-on-busy option). ADR-0027's pause-before-
power-off means squeezelite never makes a failed open, so the tick is never
reached rather than merely shortened. That direction is now the *tighter*
of the two.

## Two passes, reported separately as well as combined

| | n | median | stdev | max |
|---|---|---|---|---|
| LMS → Spotify, pass 1 | 19 | 226.8 | 165.6 | 781.2 |
| LMS → Spotify, pass 2 | 14 | 222.8 | **38.0** | 312.6 |
| Spotify → LMS, pass 1 | 15 | 343.1 | 52.6 | 447.0 |
| Spotify → LMS, pass 2 | 12 | 312.1 | 72.4 | 438.1 |

Medians agree closely across passes (226.8 vs 222.8; 343.1 vs 312.1), which
is what justifies combining them — the same like-for-like argument Finding
015 made for its three batches. **The spread does not agree**, and that is
worth keeping visible rather than averaging away: pass 1's LMS→Spotify
stdev is 165.6 ms against pass 2's 38.0 ms, driven entirely by two outliers
(781.2 ms and 710.7 ms). Both sat immediately beside rounds that Spotify's
backend refused, and pass 2 — which lost no rounds in that direction — has
no outlier at all. The most likely reading is Spotify session
re-establishment rather than anything in the handoff path. **Not proven:**
the outliers were not instrumented individually at the time.

## What the harness counts, and one thing it still counts wrongly

72 rounds were attempted; 60 produced a measurement. **Every round in which
Spotify's backend actually routed to the device produced a clean handoff.
Zero product-side failures.** Across both runs the daemon logged no ladder
escalation, no warnings, no errors, and `NRestarts=0` on squeezelite and
`gexis-core`.

The 12 lost rounds were all Spotify Web API failures — `404 Not found`,
`404 Device not found`, `500 Server error` — caused by `gexis` dropping out
of Spotify's device list when go-librespot's idle session lapses (it
re-authenticated 15 times in the 3.5h after boot).

Mid-collection the harness was changed to separate these from real
failures, because a "skip" that can mean either is useless evidence:

- **`NOT ATTEMPTED`** — Spotify would not route to the device, so no handoff
  was ever tried. The harness now re-resolves the device and retries up to
  5 times before giving up; **it recovered 4 rounds in pass 2 this way**,
  and pass 2's LMS→Spotify leg lost nothing at all against pass 1's 3.
- **`SKIPPED`** — a handoff was attempted and not observed. A product result.

**The split is still incomplete, stated here rather than left to be
discovered.** The retry covers "device absent from the list" but not a
`500` returned by the transfer call itself, which `spotify_api`'s
`best_effort=True` swallows. So pass 2's **two `SKIPPED` rounds were
actually Spotify 500s, not failed handoffs** — currently misclassified in
the direction that makes the product look worse, which is the safe
direction, but still wrong. Fixing it means propagating the HTTP status out
of `transfer_to_gexis`.

## Scope

- **Same-rate LMS↔Spotify only**, both sides confirmed at 44.1 kHz.
  Cross-rate and every Bluetooth-involving pair are **deferred by George's
  decision, 2026-09-12** — cross-rate has no content to test with (a
  60,974-track library scan found zero non-44.1kHz files), and Bluetooth
  pairs are not scriptable. Criterion 8's cross-rate half is **unmet and
  stays unmet**.
- **LMS is driven by activation** (`power 1`), ADR-0027's designed
  acquisition. The **press-play route is a different path and is not
  measured here**: LMS's own auto-power-on restarts the track from zero and
  `device_freed()` corrects it with a seek, so it has more work in it and
  need not have the same gap. The harness takes the route as an argument;
  this run used `activate` throughout. Measuring press-play is outstanding.
- T0 and T1 both come from one instrument in one pass
  (`spectrum_fifo.measure_takeover_gap`), whose own detection lag was
  validated at 19.5-40 ms and largely cancels in the difference. `pcm_holder`
  is used only as a pre/post sanity check, never as the timing source.
- Two passes in one session on one build, roughly 90 minutes apart.
- The card index was 5 this boot, having been 3 on the previous one
  (Finding 005 again) — harmless only because nothing references it.
