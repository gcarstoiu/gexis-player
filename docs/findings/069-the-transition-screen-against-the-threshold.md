# Finding 069 — The transition screen against the threshold

**Date:** 2026-09-25
**Question:** Does the handoff screen actually wait for `handoff_threshold`,
and does the row drive it? ([ADR-0078](../decisions/0078-the-transition-screen-waits-for-the-threshold.md))
**Scope:** `gexis`, the panel on its own screen, Chromium 153.0.8010.47, core
rsynced from `phase-8-plan` at ADR-0078. The handoff is **synthetic** — see
*What this did not test*. Five runs, one per row, no repeats.

## Method

The only non-exempt pairs involve Bluetooth, and Finding 020 already recorded
that Bluetooth takeovers are not scriptable. So the handoff was published
directly: a throwaway hook in the *deployed* daemon (never committed) called
`state_store.set_handoff("bluetooth", "lms")`, waited a chosen number of
milliseconds, and cleared it.

The panel was then sampled over CDP every 100 ms for `document.querySelector(
'.handoff')` — the transition screen's own element — for 2.4 s from the
trigger.

## Result

`#` is a sample where the screen was on the panel, `.` one where it was not.
Each row is 24 samples at 100 ms.

| `handoff_threshold` | handoff length | screen | samples |
|---|---|---|---|
| 1.0 s | 400 ms | **not shown** | `........................` |
| 1.0 s | 2200 ms | **shown** | `..........##############` |
| 0 | 400 ms | **shown** | `.################.......` |
| 2.5 s | 2200 ms | **not shown** | `........................` |
| 0.5 s | 800 ms | **shown** | `......################..` |

**The threshold is visible in the traces.** Same 400 ms handoff, rows 1 and 3:
at 1 s it is never announced, at 0 the screen is up by the first sample. Same
2200 ms handoff, rows 2 and 4: at 1 s the screen starts at sample 10 (≈1.0 s),
at 2.5 s it never appears. Row 5's 0.5 s threshold puts the start at sample 6.

**`0` reproduces the old behaviour exactly**, which is what makes the bottom of
the bar the escape hatch rather than a new state.

The screen outlasting the handoff in rows 3 and 5 is `handoff_duration`'s 1.4 s
hold, unchanged by this work.

## The first run was measuring the old bundle

The first pass reported **SHOWN** for 1 s / 400 ms — the change appearing not
to work. The cause was not the change: `ui/dist` had been rsynced to
`/opt/gexis-ui` and the daemon restarted, but **the kiosk's page was never
reloaded**, so Chromium was still running the bundle it had loaded before the
deploy. A `Page.navigate` to the same URL, then the same probe, gave the table
above.

This is [LESSONS](../LESSONS.md) case 36's shape again — *"are you sure the
change is in the panel"* — and the reason the probe now reloads before it
samples.

## What this did not test

- **A real takeover.** The handoff was published synthetically, so the
  *arbitration* path is untested here. What is tested is the panel's response
  to a handoff of a known length, which is the whole of what ADR-0078 changed.
- **The exempt pairs.** LMS ↔ Spotify never reaches the timer, by design, and
  that path is unchanged.
- **Anything about the audible gap.** Finding 020's medians are silence
  measured through the spectrum FIFO; nothing here is comparable to them, which
  is exactly why ADR-0078 declined to seed a live measurement store with them.
- **Whether 1 s is the right default.** It is ADR-0010's number, kept.
