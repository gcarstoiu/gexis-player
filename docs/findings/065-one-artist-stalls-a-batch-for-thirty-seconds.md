# Finding 065 — One artist stalls a batch for thirty seconds, once per restart

**Date:** 2026-09-24
**Question:** Found while building
[ADR-0068](../decisions/0068-the-sweeps-portrait-is-asked-for-first.md): why
does asking for the whole library's portraits take 31 seconds after a daemon
restart and 180 ms after that?
**Scope:** `gexis`, 2026-09-24, 917 album artists, batches of 50 against
`/library/artist-photos`. George's own library and LMS server.

## What ADR-0068 fixed, and what it did not

Splitting the library by where its portrait comes from, each half asked cold
after a `gexis-core` restart:

| | cold | warm |
| --- | --- | --- |
| the 625 the sweep answers | **160 ms** | 160 ms |
| the 292 LMS answers | **30,461 ms** | 88 ms |

**The sweep's two thirds are now free, cold or warm** — that is ADR-0068
working. The rest is not about LMS being slow in general.

## It is one artist, not 292

Timing each batch of the 292:

```
292 LMS-backed, cold: 30,646 ms, 1 slow batch
   ids 250-291:  30,541 ms
```

**Five batches are instant and one takes 30.5 seconds.** That batch holds a
single artist with no stored answer, and `CALL_TIMEOUT_S` is 30 s: one
lookup that never comes back holds the whole batch, because the batch is
gathered and answered together.

Asked one at a time, the same ids are 5 ms — they come from the store.

## Why it comes back after every restart

`artistinfo` already knows about this artist. A call that does not come back
sets `_slow_until[artist_id]`, so it is left alone for `SLOW_COOLDOWN_S`
(300 s) — and that is deliberately **not** written to the store, because
[Finding 036](036-key-free-providers-against-real-tracks.md)'s
rule says a provider that could not be asked has not told us there is
nothing.

The rule is right and the consequence is that **the marker lives in memory
only**, so every `gexis-core` restart pays the 30 seconds again. Measured
three times across three restarts: 30,327 ms, 30,461 ms, 30,646 ms.

## What it costs in use

- **Not on the critical path.** ADR-0068's prefetch is not awaited, so the
  grid opens in 146–169 ms regardless and portraits appear with the cards.
  What stalls is one batch of the background fill.
- **It is on the path for a person**, though: anyone who scrolls to that
  artist waits for the same 30 s call, and always did.

## Fixed the next day

[ADR-0069](../decisions/0069-what-a-lookup-cost-is-remembered.md), 2026-09-25,
on George's ruling that *"a fix that turns into a 30 seconds wait is worse
than before"*: what a lookup **cost** is remembered in its own namespace,
for a day. Its **answer** still is not, so Finding 036's rule is intact —
nothing says this artist has no picture.

| asking for all 917 | before | after |
| --- | --- | --- |
| straight after a restart | 30,327–30,646 ms | **116–200 ms** |
| warm | 180 ms | 180 ms |

The store holds exactly one marker, for **artist id 9934** — the single
artist all 31 seconds belonged to.

## What this does not settle

- **Which artist**, and why the plugin cannot answer for them. The id was
  not chased.
- **Whether 30 s is the right timeout.** `CALL_TIMEOUT_S` predates this and
  a lookup that ran past four minutes is why it exists (2026-09-18).
- **Whether one slow id should hold a batch at all.** Answering the batch
  with what it has and letting the straggler arrive later is a different
  design and was not measured.
