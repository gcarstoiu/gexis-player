# ADR-0027 — LMS power is the arbitration mechanism; no permanent base slot

**Status:** Accepted
**Date:** 2026-09-12
**Supersedes:** parts of [0010](0010-arbitration-slot-model.md) — the permanent
base slot, LMS's acquisition and release rows, and "power state plays no role in
arbitration". Everything else in 0010 (the no-stack rule, the accountability
rule, the rejected alternatives, the non-LMS release table) stands.
**Evidence:** [Finding 018](../findings/018-four-phase2c-blockers.md), measured
on `gexis` 2026-09-11/12.

## Context

Two defects reported as non-deferrable blockers, both traced to the same root
cause: **the outgoing renderer still holds the ALSA device when the incoming one
tries to open it.**

- **Spotify's takeover** (blocker 2): go-librespot attempts its ALSA open ~1s
  after `will_play`; LMS's commanded pause took **1.44s** to actually free the
  device (`-C 1`'s idle timer dominating). It lost by ~0.4s, every time. The
  retry that followed reloaded the track at position 0, and — worse —
  go-librespot never emitted its `active` event afterwards (0 of 2 controlled
  runs, 0 of 3 organic), leaving the phone showing 0:00 against a 0 duration
  while audio played. That is ADR-0010's "never show a state the user cannot
  account for", broken.
- **LMS's elapsed time** (blocker 1): on resume LMS reports
  `position + away_duration` until squeezelite actually starts and corrects it.
  How long that wrong value stays on screen is governed by how long the device
  stays busy.

Every route that left the mechanism alone was measured and closed:

| Attempt | Result |
|---|---|
| `-C 0` (no idle wait) | squeezelite **never releases** — 4/4, `-C 0` disables the close |
| `stop` instead of `pause` | 1.04s, 1.85s — inconsistent, no better, and it loses the position |
| An earlier acquisition signal | `will_play` is the **only** event go-librespot emits before the failed open |
| `POST /player/resume` (Finding 014) | plays audio without completing the Connect handshake — reverted |
| `POST /player/play` at the captured position | works, position preserved, but `active` still never fires (0/2) |
| Killing squeezelite | reverted twice for restart storms (Finding 013 §1) |

## Decision

**LMS's player power is what takes and gives up the device.** George's call,
2026-09-11/12, after the measurements below.

### Release — pause, then power off

On takeover, the supervisor **records the player's transport state**, sends
`pause`, then `power 0`.

- **Measured: the device is free in 0.06-0.11s** (n=4), against 1.42-1.45s for
  `pause` alone. Power-off bypasses `-C`'s idle timer entirely.
- That lands inside go-librespot's ~1s first-attempt window, so **Spotify's
  first open succeeds**: one `will_play`, no `inactive`/`stopped`, **`active`
  fires** (2/2), Spotify holding the PCM 0.7s after the transfer, against
  *never* in the control run. No retry means no reload at position 0.
- The `pause` before the power-off is what makes the *return* fast (below) and
  costs nothing on this side.

### Acquisition — on power on

**Powering the player on is the acquisition**, replacing "explicit play or
resume". This makes LMS's row consistent with the other renderers: the
deliberate connect-like act takes the device, and play is a separate intention
afterwards.

Consequences that fall out of it, all of them wanted:

- The **0.4s acquisition debounce is retired**, and with it the whole
  spurious-reclaim class (Findings 009/010 §4) — a stray server-side
  `mode: play` is no longer an acquisition signal at all.
- Verified the signal exists and is usable: the CometD `playerstatus` push
  **does** carry `power`, and a change triggers a push in **0.52s** (n=2).

### Return — restore the recorded transport state

Once the outgoing renderer's release is confirmed, the supervisor restores the
state it recorded at release time: **`play` only if the player was playing**.
A player the user left paused comes back paused, and we send nothing.

**Why we issue that play rather than letting LMS's own power-on restore do it.**
LMS restores transport state across a power cycle by itself, so the rule needs
no bookkeeping in principle. But its restore fires ~58ms after power-on — long
before we are told anything — and squeezelite's ALSA attempt goes out with it,
against a device the outgoing renderer has not released yet. A lost attempt
costs up to **5 seconds**, because squeezelite retries on a strict 5.00s tick
(measured 20.781 / 25.782 / 30.783) which **is not tunable** — squeezelite
2.0.0-1517 has no retry-on-busy option, and nothing shortens the wait
(do nothing 2.53s, re-issue play 2.50s, power cycle 2.42s: all just wait for the
tick).

Pausing before the power-off removes the attempt entirely, because a player
restored to `paused` has nothing to play:

| release | state on power-on | failed ALSA attempts | took the device once free |
|---|---|---|---|
| `power 0` while playing | `mode=play` | **1** | 1.98s (waiting out the tick) |
| `pause` then `power 0` | `mode=pause` | **0** | **0.17s** |
| `pause` then `power 0` (repeat) | `mode=pause` | **0** | **0.07s** |

So the play we send is the same one LMS would have sent itself; the difference
is only that ours lands *after* the device is free instead of 460ms before it.

### Deactivation persists

**A deactivated player stays deactivated until the user activates it again.**
No automatic, invisible re-activation. We only ever power *off*, and only as
part of a takeover; we never power on.

This makes provenance tracking unnecessary — there is no user action we could
accidentally undo, because we never issue the action that would undo one.

Tested and rejected: powering the player back on a few seconds later, while the
other renderer is still playing. Power-on restores the previous transport state
(`play`), so LMS resumes and **evicts the renderer that just took over** —
`inactive` within a second, device back to squeezelite. That is the
spurious-reclaim failure, produced on demand.

### No permanent base slot

LMS is no longer the base. **A state where no renderer holds the device is
normal**, not an error: every renderer can be off at once. ADR-0010's "release
always returns to base" no longer holds, and its deferred "empty base slot —
undefined behaviour" item is answered rather than deferred.

Note that a *paused* LMS already held nothing before this decision — `-C 1`
closes the device about a second after it goes idle, and a Spotify takeover from
a paused LMS was already clean (first open succeeds, `active` fires, 0.93s).
Contention only ever existed while LMS was **playing**.

## Consequences

**Accepted costs, named rather than discovered later:**

- **After any Spotify or Bluetooth session, LMS is off and stays off** until the
  user activates it. Casting to gexis in the morning means LMS will not respond
  that evening until it is turned back on.
- Other people's LMS clients show `gexis` powered off during another renderer's
  session. Arguably more honest than showing it paused — the player genuinely is
  not available — but it is a visible change.
- The UI (Phase 4+) must represent "no renderer holds the device", which the
  base-slot model never required.
- We send one transport command (`play`) the user did not literally press, in
  the case where they left the player playing. It reproduces the state they
  left, and only in that case.

**What this fixes:**

- Blocker 2, at the root: Spotify's first open succeeds, position is not reset,
  and `active` fires so the phone's own state is honest.
- The LMS takeover gap in the contended case: **0.07-0.17s** instead of up to 5s.
- Blocker 1 substantially: the wrong elapsed value goes from 3-5s on screen to
  0.3-1.6s. **Not eliminated** — see Open.
- The restart-storm class (Finding 013 §1) stops being reachable in normal
  operation, since LMS is never killed to make it release.

**Sync groups:** unchanged, per George — a group plays only on active devices,
so a deactivated player simply does not play. This is a cleaner outcome than the
kill approach, which dropped squeezelite out of its group entirely.

**Crash behaviour:** if `gexis-core` dies while the player is off, the player
stays off — a *valid* state the user restores the same way they always would,
not a broken one. With the daemon down there is no arbitration at all and
activating LMS will take the device from a playing renderer, which is true today
and not made worse.

## Criterion 10 — the transition screen

Answered 2026-09-12 and recorded in
[ADR-0010](0010-arbitration-slot-model.md#handoff-transition-screen--shown-by-default-skipped-only-where-measured-fast)
rather than duplicated here: the screen is **shown by default and skipped
only for a pair measured below 1 second**. This ADR is what moved
LMS↔Spotify into the exempt column — 224.6 ms and 335.2 ms medians
(Finding 020) against the 1827.8 ms and 4170.9 ms this mechanism replaced.
Bluetooth pairs are unmeasured and Bluetooth's own release is untouched by
this decision, so they show the screen.

## What this changes in the plan

Recorded here because the decision creates work that did not previously
exist anywhere. Full wording is in `docs/DEVELOPMENT.md`.

- **Phase 2b is reopened as 2d.** Criteria 3 and 4 were verified in 2b
  (2026-09-10) against wording this ADR invalidates — criterion 3 described
  a base slot and deferred empty-base-slot behaviour as undefined; criterion
  4's LMS half describes a kill path that is now unreachable. 2b's work was
  correct under the wording it was checked against; the wording changed.
- **Criteria 7-10 need re-running.** Every number in Finding 015 was measured
  against the mechanism this ADR replaces.
- **Phase 3's published model must express "no renderer" and per-renderer
  availability.** The old model could always name a current renderer because
  LMS was permanently the base. It cannot now, and the UI cannot offer to
  activate LMS unless the model says LMS is deactivated.
- **Phase 4 gains two criteria** (George's decision, 2026-09-12): a
  first-class "nobody holds the device" screen state, and **the ability to
  activate LMS from our own UI**. The second is load-bearing: this ADR never
  re-activates LMS silently, so without it the only route back to LMS is the
  LMS phone app — unacceptable on an appliance with its own screen. It was
  pulled into Phase 4 rather than left to Phase 6's capability-driven
  transport controls for that reason.
- **Accepted interim regression:** between this ADR shipping and Phase 4's
  activation control shipping, the box hands over cleanly but comes back only
  via the phone app. Knowingly accepted.
- Phases 5 and 7-9 are unaffected. Nothing is removed.

## Open

**Listening results, George, 2026-09-12, on the deployed 2d build:** the
power-*off* produces no click at all. The power-*on* has "a fraction of a
second click - barely audible", which he judged not worth spending time
on. Recorded as observed-and-accepted rather than left as an open
question. Takeovers behaved correctly, and the logs for that session show
no ladder escalation of any kind and zero go-librespot "resource busy"
failures - the signature blocker 2 used to leave on every LMS→Spotify
handoff.

**Both of the first two items below are DEFERRED by George's decision,
2026-09-12** — not unresolved, and not blocking implementation. Revisit if
either turns out to be audible or annoying in real use.

- **Blocker 1 is not fully fixed by this.** Power-on itself is clean — the
  player returns paused at exactly the stored position (delta +0.00s) — but
  issuing the `play` re-introduces LMS's stale-anchor jump for 0.3-1.6s
  (measured, n=2) before it corrects. An explicit seek to the captured position
  removes it completely (44.50 against a true 44.50, versus 57.84 against a true
  32.72 without). **Not adopted here:** a seek makes LMS re-request the stream,
  which may be audible at the resume point, and that has not been listened to.
  Decide after hearing the fix without it.
- **Powering off mid-playback has not been listened to** for a click at the cut.
- **Bluetooth is untouched by this.** `power` is an LMS concept, so this helps
  only where LMS is the outgoing renderer. Bluetooth's own release still
  measures 2.5-2.9s and remains ADR-0010's open item, which keeps
  Bluetooth→LMS the slowest handoff.
- **Pressing *play* rather than activating loses the position.** Confirmed on
  hardware 2026-09-12, after George asked whether the auto-power-on was ours:
  it is LMS's own, documented since ADR-0010 ("if someone presses play on a
  powered-off player, LMS powers it on and starts"), and our source contains no
  `power 1` call at all — only `power 0`. But LMS's auto-power-on starts the
  track **from zero**: deactivated at 24.4s, a plain `play` came back at 2.3s.
  `device_freed()`'s resume cannot help here, because LMS is already playing
  from 0 by the time we see the acquisition. **This gives the deferred seek
  re-anchor a second, more substantive justification than the elapsed-time
  flicker it was deferred over** — recording the *position* at release, not just
  the playing flag, would fix the position loss as well as the flicker. Worth
  reconsidering the deferral on those grounds.
- **Bare power-on with nothing playing** takes the device and produces silence
  until the user presses play. Consistent with Bluetooth connecting without
  streaming, and with this ADR's own "play is a separate intention" — recorded
  as intended behaviour, not an oversight.
- Criterion 8's takeover-gap numbers (Finding 015) were measured against the old
  mechanism and need re-collecting. The 0.7s LMS→Spotify figure seen here is far
  better than that finding's 1827.8ms median.
