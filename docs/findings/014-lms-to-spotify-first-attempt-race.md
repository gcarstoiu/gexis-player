# Finding 014 — LMS-to-Spotify: a single, clean transfer attempt fails deterministically, not just under repeated calls

**Date:** 2026-09-11
**System:** `gexis`, same build as Finding 013 (`v0.2.1-15-g2396ea2-dirty`).
**Question:** Attempting to collect criterion 8's LMS-to-Spotify takeover-gap distribution (`tools/phase-2c/takeover_gap.py`, single attempt per round, 65s cooldown — the fix Finding 013 §3 already put in place) produced 0 successful rounds out of 4 attempted in the first trial. Why?
**Answer:** Finding 013 §3 attributed the earlier failures to the *harness's own* retry cadence colliding with go-librespot's backoff, and explicitly noted its mechanism "wasn't reachable from a single clean user action either." That's now shown to be wrong for at least one of the two failure modes below — a single, unhurried, non-repeated transfer attempt fails **every time** LMS is actively holding the device, via a race that has nothing to do with repetition.

## Method

Four isolated diagnostic runs on `gexis` (`tools/phase-2c/diag_one_transfer.py`, a throwaway script written for this investigation, kept in `tools/phase-2c/` since it reproduces the mechanism cleanly and may be needed again), each starting from LMS actively holding the device, calling `spotify_api.transfer_to_gexis(play=True)` **once**, then watching `gexis-core` and `go-librespot`'s own journals plus direct `pcm_holder` polling — no repeated calls except where explicitly noted as a second, deliberate attempt.

## Two distinct failure modes, both confirmed from journal timestamps

**Mode A — the ALSA-open race.** Confirmed with sub-second timestamps (2026-09-11 07:37:53–07:37:56):

- `07:37:53.375` — `will_play` fires, arbitration logs `acquire: spotify takes the device (was lms)` immediately.
- `07:37:53` (same second) — go-librespot's own log: `failed handling dealer request ... ALSA error at snd_pcm_open: Device or resource busy`.
- `07:37:56.473` — `release[lms]: freed within polite grace (3.1s)` — i.e. **~3.1 seconds after** the acquire that go-librespot had already tried and failed against.

go-librespot attempts its ALSA open within about a second of `will_play` — effectively immediately. LMS's polite release takes ~3.1s. Every clean attempt loses this race, because the release is structurally slower than go-librespot's own attempt. This directly contradicts the assumption `adapters/spotify.py`'s own comment states for why acquiring on `will_play` (rather than `active`) was expected to fix Finding 010's deadlock: *"the ALSA device is actually free by the time go-librespot's own retry (or the same call, once re-entered) tries to open it."* That assumption does not hold when go-librespot's own attempt happens faster than our release, which is the normal case, not an edge case.

**What does resolve it:** a **second**, distinct transfer call ~2-3s after the first reliably succeeds (confirmed: `07:37:56.171` second `will_play` → `07:37:56.706` `device became active`, in the same run). Not because go-librespot retried on its own in that short window — by the time the second call landed, LMS's *original* 3.1s release (started by the first call) had already almost finished, so the second attempt simply arrived once the device was actually free.

**Whether go-librespot retries the same failed attempt on its own, and how soon:** not established by this session's evidence either way. Finding 013 §3 measured a ~56s autonomous retry-then-reauth cycle, but under repeated harness calls, not a single isolated one — this session did not isolate that specific question (see "Not established" below).

**Mode B — the transfer request appears to be silently dropped during go-librespot's own AP reauthentication.** Confirmed twice (07:33:25 and 07:35:22), each from a single `transfer_to_gexis()` call against actively-held-by-LMS state:

- The only journal activity following the call was go-librespot's own `loading previously persisted zeroconf credentials` → `authenticated AP` → `authenticated Login5` sequence.
- **No `will_play`, no `active`, no ALSA error, nothing else at all** — watched for 100 seconds straight in one case (07:35:22, `diag_one_transfer.py`'s successor test) with zero further activity from either `gexis-core` or `go-librespot`.
- A subsequent, distinct transfer call (issued manually, not automatically) succeeded and produced a normal `will_play` cycle (Mode A's race) — i.e. Mode B's own dropped attempt did not resolve itself; only a fresh external call moved things forward.

**Not established:** what triggers go-librespot to need this reauth cycle on some calls and not others (it did not correlate cleanly with simple call-to-call spacing in this session's small sample — an early call ~52s after the previous one needed no reauth, while a later call ~65s after that one did). Needs go-librespot's own source or a larger sample, not guessed at here.

## Why this changes Finding 013 §3's framing

§3 said the ~56s-backoff mechanism "wasn't reachable from a single clean user action either," treating the earlier failures as an artifact of the harness's and go-librespot's cadences colliding. This session's isolated, non-repeated attempts show at least Mode A **is** reachable from one single, ordinary action — selecting "gexis" once while LMS is playing loses the race essentially every time, deterministically, not as a rare collision. Mode B may or may not be — its trigger condition isn't pinned down.

## What this means for a real user

Combined with Finding 013 §2's own read of ordinary usage: a user selecting "gexis" in the Spotify app while LMS is actively playing should expect the **first** selection to silently do nothing (Mode A: audible silence for as long as go-librespot's own backoff takes to retry, unmeasured but bounded below by Finding 013 §3's ~56s figure if it applies here; Mode B: unbounded in this session's 100s observation window). An impatient second tap, made within a few seconds, reliably works (Mode A's case, confirmed) — which is plausibly why field reports have described this as "finicky" or "sometimes doesn't sustain" rather than "never works": most real users tap again well within a few seconds of nothing happening.

## What this means for criterion 8

**The LMS-to-Spotify leg cannot currently be measured as "the gap of a single ordinary takeover action"** — a single clean action's outcome is dominated by which of these two race outcomes it happens to hit, not by the arbitration/rendering gap the criterion is meant to characterise. Collecting a distribution would currently mostly measure "how often does a lone Web API call happen to arrive fast enough or slow enough relative to LMS's release," which is not the criterion 8 question. Recommend **not** continuing blind `takeover_gap.py` collection for this leg until one of the following is decided:

1. **Shrink LMS's release time below go-librespot's attempt latency** (currently ~3.1s vs. ~1s) — reopens the exact trade-off already settled once for a different reason (`-C 1` vs. killing squeezelite, HANDOFF's 2026-09-08 session): a faster release previously meant killing squeezelite outright, which cost the restart-limit and sync-group problems that `-C 1` was chosen specifically to avoid. A different, non-kill way to shrink this specific 3.1s number hasn't been investigated.
2. **Have the harness (and, more importantly, a real fix in `SpotifyAdapter`) explicitly retry the acquisition path itself** once LMS's release is confirmed complete, rather than relying on go-librespot's own backoff or a lucky/impatient second external call. This is implementable in `gexis-core` (it already knows the moment LMS's release completes) but there is no known local go-librespot endpoint to "retry the pending transfer" without a fresh Web-API-level call, which only the phone/Spotify backend can issue — needs checking whether go-librespot exposes anything else locally that could substitute (unchecked this session).
3. **Change what criterion 8 measures for this leg** — e.g. measure from the *second* (successful) attempt only, explicitly documenting that the first attempt's outcome is currently unreliable rather than part of the "gap." A measurement choice, not a mechanism fix.

None of these were picked this session — this is new evidence for George's call, same as Finding 013's own open items.

## Fixed and verified, 2026-09-11 (same day, second session)

**George's decision: option 2** - `SpotifyAdapter` retries itself once the
outgoing renderer's release is confirmed, rather than depending on a
second Spotify Web API call (which only the phone/Spotify's backend can
issue) or shrinking LMS's release time (reopening the kill-vs-pause
trade-off ADR-0010 already settled 2026-09-08).

**Mechanism:** `POST /player/resume` against go-librespot's own local HTTP
API (`127.0.0.1:3678`) - no Spotify Web API call, no account credentials,
unlike `spotify_api.transfer_to_gexis()`. Confirmed manually first
(`tools/phase-2c/diag_resume_rescue.py`, three-for-three rescues of a
reproduced Mode A busy failure) and confirmed harmless when called after
an attempt that already succeeded (status 200, no pause/restart, track
position kept advancing across the call - checked directly against
`/status` before and after).

**Implemented** as `Adapter.device_freed()` (`adapters/base.py`), a new
optional hook defaulting to a no-op, called by `Supervisor.acquire()`
(`arbitration.py`) on the incoming renderer's adapter once the outgoing
renderer's release is confirmed and its volume restored. `SpotifyAdapter`
overrides it with the `/player/resume` call above; every other adapter
keeps the default no-op. Unit-tested at the supervisor call-site level
(fires on the incoming adapter only, once per acquisition, after volume
restore) - the HTTP call itself is hardware-verified only, matching this
project's existing convention for adapter network code (see
`adapters/base.py`'s docstring and `test_lms_adapter.py`'s own module
docstring for the same reasoning applied to LMS).

**Verified against the real harness, deployed live on `gexis` (hot-patch,
no rebuild):** LMS-to-Spotify, 5 of 5 real handoffs succeeded (one
additional round skipped for an unrelated LMS-side precondition timing
issue, not this mechanism) - gaps 895.5-1900.2ms, mean 1603.5ms, n=5.
Baseline before the fix was 0 of 4. Not yet a full ≥20-run distribution,
and Mode B (the transfer request dropped during go-librespot's own
reauth cycle, no `will_play` at all) was not specifically re-tested this
round - the fix targets Mode A only. If Mode B recurs during full
collection, it needs its own investigation; it wasn't observed in this
verification pass.

## Not chased further this session

- Whether go-librespot's own unprompted retry timer (if one exists at all for Mode A, separate from Mode B's apparent full drop) is real, and if so its actual interval when isolated from repeated external calls.
- Mode B's trigger condition.
- Whether Mode A's ~1s go-librespot attempt latency is itself variable, or a fixed near-immediate response to `will_play`'s underlying dealer message.
- Reading go-librespot's own source for either mechanism, the way Finding 011 did for the acquisition signals — flagged as needed, not done.
