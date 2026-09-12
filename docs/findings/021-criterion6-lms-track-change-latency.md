# Finding 021 — Criterion 6: LMS track-change latency on the state WebSocket

**Date:** 2026-09-12
**System:** `gexis`, `gexis-core` hand-installed over SSH from
`phase-3-core-daemon` commit `02fc0dc` into the existing
`/opt/gexis-core/venv` (not baked into a rebuilt image — see HANDOFF.md's
note on this session's hand-install workflow). LMS server
`192.168.178.188:9000`, player `e4:5f:01:58:89:07`.
**Question:** Phase 3 criterion 6 — "Track change on LMS appears on the
WebSocket within a bounded time, measured and recorded."

## Result

20/20 rounds produced a measurement. No timeouts, no dropped connections.

| n | min | median | max |
|---|---|---|---|
| 20 | 644.0 ms | **699.5 ms** | 787.3 ms |

All 20 values, sorted (ms): 644.0, 655.8, 656.5, 659.2, 671.3, 672.0,
681.0, 687.3, 688.3, 698.7, 699.5, 748.2, 749.1, 751.5, 753.0, 755.2,
756.2, 765.7, 774.1, 787.3.

Tight and unimodal — no outliers, no bimodal split the way Finding 020
saw on a different pair. The full range spans 143.3 ms.

## Method

One long-lived script, run on `gexis` itself (not from a separate
machine — deliberately, so nothing beyond LMS's own real network hop to
`192.168.178.188` is added to the timing, per this project's own
"wrong-host" lesson): a single WebSocket client connected to
`ws://127.0.0.1:8090/state`, alternating `playlist play <url>` JSON-RPC
calls between two distinct local library tracks (Snow Patrol / Yiruma,
chosen only because their `artist` fields are unambiguous to match on)
so every round is a genuine, unmistakable track change — never the same
track re-queued, which the WebSocket's own change-dedup would not
re-broadcast at all.

**T0** is taken immediately before the `playlist play` HTTP POST is
issued to LMS — this is what a real trigger (a phone app pressing next,
say) would experience, LMS's own processing time and CometD push
included, not just gexis-core's internal handling after the fact.
**T1** is the first WebSocket frame whose `metadata.artist` matches the
newly-requested track. 20 rounds, 1s pause between each.

## Scope

- **One pass, one session, 20 rounds** — clears this project's usual
  ≥20-run bar (Phase 2's own convention) but is still a single sitting on
  one build, not repeated across sessions or images the way some Phase 2
  findings were.
- **Local library tracks only, both 44.1 kHz** (the same content-scope
  limit Finding 020 recorded — the library has no non-44.1kHz content to
  test cross-rate with).
- **LMS was already active (`power 1`) throughout** — this measures a
  track change during an ongoing session, not a track change racing an
  acquisition. Findings 018/020 cover the acquisition-timing question
  separately; this finding is additive to those, not a replacement.
- **No explicit numeric bound was specified anywhere in this project's
  own records for what "bounded" means** (DEVELOPMENT.md's criterion 6
  wording, ARCHITECTURE.md's "CometD or track changes will visibly lag"
  rationale) — this finding reports the measured distribution as the
  record, rather than asserting a pass/fail line against an
  unspecified number. ~650-790ms is fast enough that a track change
  reads as immediate to a listener glancing at a screen, which is the
  concern ARCHITECTURE.md actually names (polling lag), but that
  judgement is not encoded as a formal threshold here.
- **Hand-installed code, not a rebuilt image** — same caveat as the rest
  of this session's Phase 3 work (HANDOFF.md).
