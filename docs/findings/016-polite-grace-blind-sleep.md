# Finding 016 — the polite rung sleeps blind, it does not poll

**Date:** 2026-09-11
**System:** source analysis of `core/src/gexis_core/arbitration.py` (current build's `stage-gexis`, `ExecStart` confirmed carrying `-C 1`) plus release-timing log lines collected on `gexis` from seven consecutive hand-driven LMS releases, all within a ten-minute window.
**Question:** why does every LMS takeover release land at 3.1-3.2s against the ladder's 3.0s `polite_grace` ceiling, with effectively no margin?

## The mechanism

`Supervisor._release_with_ladder` (`arbitration.py`, around line 162, pre-fix)
checked `_busy()` once before the polite-grace sleep and once after, with
nothing in between:

```python
if ladder.polite_grace > 0:
    await asyncio.sleep(ladder.polite_grace)
    if not await self._busy(renderer_id):
        logger.info("release[%s]: freed within polite grace (%.1fs)", ...)
```

The log line `"freed within polite grace (%.1fs)"` reads as a measurement of
how long the renderer took to release. It was not — it was measuring the
sleep itself (`ladder.polite_grace`, 3.0s) plus overhead, since nothing
checked in between. The only way a shorter number could appear was the
pre-sleep check at the top of the function succeeding, i.e. the device was
already free before the ladder even started.

## Evidence

Seven consecutive LMS releases, driven by hand from George's phone, current
build:

| Outcome | Time |
|---|---|
| "freed within polite grace" | 3.2s |
| "freed within polite grace" | 3.2s |
| "freed within polite grace" | 3.1s |
| "freed within polite grace" | 3.1s |
| "freed within polite grace" | 3.1s |
| "freed within polite grace" | 3.2s |
| "polite stop freed the device" | 0.1s |

The six 3.1-3.2s outcomes are the sleep plus overhead. The single 0.1s
outcome is the pre-sleep check at the top of `_release_with_ladder`
succeeding because the device was already free when the ladder started —
not a fast release measured through the sleep path at all.

For comparison, squeezelite's measured passive release with `-C 1` (which
**is** shipping in this build — `ExecStart` carries `-C 1`) was ~700ms in
isolated testing in an earlier session (`docs/decisions/0010-arbitration-slot-model.md`'s
2026-09-08 amendment). The ~700ms figure is carried over from that earlier,
separate measurement, not re-measured on this build — this finding has not
instrumented the actual release moment directly.

**Scope:** 7 samples, one build, one direction (LMS release only), all
within a ten-minute window, hand-driven rather than scripted. Not a
distribution in the sense criterion 8 requires. What it is not: a
measurement of Spotify's or Bluetooth's release paths, which mostly avoid
this code path already (Spotify typically logs via the pre-sleep check, per
HANDOFF's Finding 015 note) or use their own release ladders.

## Why it matters

1. **Feeds the restart-storm fuel.** Every LMS handoff was landing at
   3.1-3.2s against a 3.0s ceiling — effectively no margin. Anything
   marginally slower tips into escalation, and `LmsAdapter.signal_stop`
   always sends `SIGKILL` regardless of ladder rung (ADR-0010's 2026-09-11
   amendment), which is what makes `Restart=on-failure` fire and the storm
   begin. This plausibly explains why the storm appeared under Bluetooth
   connect/disconnect churn (rapid handoffs, no time to settle) but not
   across 35 clean scripted sequential rounds (each handoff given a full
   settle window) — not confirmed, a plausible mechanism consistent with
   both observations.
2. **Inflates criterion 8's numbers.** Finding 015's Spotify→LMS median
   (4170.9ms) almost certainly contains most of this sleep, since that
   direction's release-side wait sits in this same code path. LMS→Spotify
   (1827.8ms) is less affected, since that number is dominated by the
   acquisition side per Finding 015's own analysis, but should be
   re-checked once this fix is live.
3. **~2.5s of dead air** on every LMS handoff the user hears, for no
   mechanical reason — the device was very likely free well before the
   sleep ended.

## The fix

`_release_with_ladder`'s polite rung now polls `_busy()` every
`POLITE_POLL_INTERVAL` (0.1s) up to the same `polite_grace` ceiling,
returning as soon as the device reports free, rather than sleeping the
full grace blind. Unchanged: the 3.0s ceiling itself, escalation semantics,
the SIGTERM/SIGKILL rungs and their own graces — this is the same ladder
looking more than twice, not a redesign. Applies to all three renderers
(shared ladder code); Spotify and Bluetooth get the same benefit on the
rare occasions they actually need the grace period, though most of their
releases already resolve via the pre-sleep check and were largely
unaffected before this fix.

Expected effect, not yet confirmed on hardware: normal LMS handoff drops
from ~3.2s to ~0.7s (matching the `-C 1` figure above), moving the common
case away from the escalation edge instead of sitting right against it.

**Status: implemented in code (`core/src/gexis_core/arbitration.py`,
`core/tests/test_arbitration.py`), unit-tested (`test_polite_grace_polls_
instead_of_sleeping_blind` — verifies via recorded `asyncio.sleep` calls,
not wall-clock timing, following this file's own established pattern),
not yet hardware-verified.** Per George's order of work: next is deploying
to `gexis`, re-running the Bluetooth-churn pattern that broke Finding 013
§1's fix (LMS playing → Spotify → rapid Bluetooth connect/disconnect ×5-10
→ back to LMS, ×3), and re-collecting the release-timing distribution
before this goes into a `stage-gexis` rebuild. Explicitly out of scope for
this change: Finding 014's LMS-to-Spotify first-attempt race and Finding
013 §1's explicit-restart approach — both reverted, both stay reverted;
this finding's fix is evaluated on its own.

## What was not done

Not fixed, not attempted: any change to escalation semantics, the ceiling
values, or the SIGTERM/SIGKILL rungs. If escalation still occurs after
this fix restores real margin to the polite rung, that is a new finding to
investigate then — not assumed away here.
