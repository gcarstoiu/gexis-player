# Finding 013 — Phase 2c attack test and takeover-gap harness: four reliability defects found

**Date:** 2026-09-10/11
**System:** `gexis` — rebuilt 2026-09-10 (`v0.2.1-15-g2396ea2-dirty`, includes Finding 011's two signal fixes and the manifest-annotation fix).
**Question:** Criterion 7's attack test (can adversarial, repeated takeover attempts ever leave the system in a bad state?) and, in the course of building criterion 8's takeover-gap harness, whether that harness could get a trustworthy measurement at all.
**Answer:** Criterion 7's own invariant — no two renderers ever hold the device at once — held cleanly across every scripted race (0 violations, LMS↔Spotify and Bluetooth-involving pairs, including scenarios specifically designed to reproduce Finding 009/010's still-open LMS-reclaim item). But the attack test and the measurement harness together surfaced four distinct reliability defects, none of which are "two renderers holding the device simultaneously." Recorded together because they all surfaced from the same session's work and three of the four are Spotify/go-librespot-specific.

| # | Defect | Status |
|---|---|---|
| 1 | squeezelite's systemd restart-rate limit exhausted by legitimate arbitration activity | **Mitigated, not cured** — commit `2eec5f9` raised the limit 5→20; recurred 2026-09-11 under ordinary paced measurement, exceeding even the raised limit (24) |
| 2 | go-librespot rapid (50-300ms) acquisition retry storm under repeated transfer calls | **Deferred**, George's decision — not seen in normal use |
| 3 | go-librespot's own retry-then-reauth backoff after a failed device open is ~56s, not immediate | Documented; harness fixed to stop provoking it |
| 4 | go-librespot can report itself actively playing a real track while never having opened the ALSA device at all | Documented; **not fixed, not root-caused** — most direct match yet for an old unexplained symptom |

---

## 1. squeezelite's restart-rate limit can be exhausted by legitimate arbitration activity

**Root cause, confirmed from `journalctl -u squeezelite`:** rapid adversarial takeovers during the criterion 7 attack test caused the arbitration ladder to `SIGKILL` squeezelite while the ALSA device was still busy (held by whichever renderer had just taken over). squeezelite's restart raced the same busy device, failed immediately (`test_open:281 playback open error: Device or resource busy`), exited, and systemd restarted it again — five times within about 15 seconds, tripping `StartLimitBurst=5`/`StartLimitIntervalSec=60`. Once tripped, `squeezelite.service` went to a **permanently failed state** with no further auto-restart. `gexis` silently dropped off the LMS server's player list from that point on ("player count 1", only "Moode" registered) until a manual `systemctl reset-failed squeezelite && systemctl start squeezelite`.

**Consequence while it lasted:** every LMS-side test command sent afterward (`play`, `pause`) was silently accepted by the LMS server and had zero effect, because the target player no longer existed. This produced about 20 minutes of confusing, hard-to-diagnose session behaviour before the actual cause (squeezelite's own unit state, not any arbitration logic) was found.

**Fixed:** `StartLimitBurst` raised 5→20 (`image/stage-gexis/02-renderers/files/squeezelite.service`, commit `2eec5f9`), applied live on `gexis` and ported into the image source. 20 gives real adversarial racing enough headroom while a genuinely misconfigured unit (wrong flags, missing device — the scenario the original limit of 5 was sized for, per the unit's own comment) still gives up within the same 60-second window at `RestartSec=2`.

**Not fixed, and arguably the more correct fix if this needs revisiting:** the underlying race — SIGKILL firing before the device is confirmed free — still exists. Raising the burst limit is a safety margin, not a cure. Not chased further this session.

**Recurred, 2026-09-11, under ordinary well-paced measurement, not adversarial racing - sharpens the original characterization.** Collecting criterion 8's actual ≥20-run distribution (Finding 014's fix deployed, `takeover_gap.py`, single attempt per round, 1.5s settle either side, no rapid retries) tripped this again: `squeezelite.service` failed with restart counter at 24 - past the raised 20 limit - and stayed failed until a manual `systemctl reset-failed && systemctl start`. `gexis-core`'s own log shows the trigger precisely: round 16's takeover found LMS still holding the device after the full 3s polite grace (every one of the 15 rounds before it had freed within 3.1-3.2s, no escalation), escalated through `LmsAdapter`'s always-SIGKILL `signal_stop` twice (the ladder's "SIGTERM" rung already sends a real SIGKILL for this adapter, per ADR-0010), finally freeing at 8.3s - by which point squeezelite had already restarted and failed busy several times on its own, racing the still-completing release. **This is a materially different trigger than the original characterization** ("legitimate adversarial arbitration activity," attack-test-style rapid racing): this session's rounds were evenly paced, ~6-8s apart, each one settled before the next began - closer to ordinary repeated use than an attack. Root cause of *why* round 16 specifically failed to free within the normal window, after 15 consecutive successes, not established - not chased further this session, recovery took priority. **Consequence: the raised burst limit (5→20) is not sufficient headroom for a full ≥20-round same-direction collection on its own** - it was exceeded (24) by the time it tripped. Blocks resuming criterion 8's Spotify-to-LMS leg until addressed, since every round of that leg failed this session purely because squeezelite was dead throughout, not because of anything specific to that direction (see Finding 014's follow-up note, criterion 8 section of HANDOFF).

---

## 2. go-librespot can enter a rapid internal acquisition-retry storm

**Observed:** during the criterion 8 measurement harness's early testing (which called Spotify's Web API `PUT /me/player` repeatedly, retrying every ~12s across up to 4 attempts per round), `gexis-core`'s log showed `spotify: will_play (acquisition, ahead of ALSA open)` fire **roughly 90 times in about 18 seconds** (18:23:37.637–18:23:55.930), i.e. every 50–300ms — far faster than anything the harness itself was doing (its own retries are ~12s apart). The system recovered on its own afterward: the storm stopped, then a single clean `will_play` → `device became active` pair followed a few seconds later.

**Isolation test, done specifically to check whether a real user's single action could trigger this:** with LMS confirmed genuinely playing (holding the device), a **single** `transfer_to_gexis()` call — the same API action a phone tapping "gexis" in the Spotify Connect device picker performs — produced a clean, single cycle: one `will_play`, immediate `acquire: spotify takes the device`, `release[lms]: freed within polite grace (3.1s)`. No storm.

**What this establishes and what it doesn't:**

- **Confirmed:** the storm is real, reproducible under repeated/rapid transfer calls, and self-resolving (not a permanent hang, in the one case observed).
- **Confirmed:** a single, isolated transfer call under the same precondition (LMS actively holding the device) does **not** reproduce it.
- **Not established:** the exact number or pattern of repeated calls needed to trigger it, or the exact internal go-librespot mechanism (read from the *symptom*, not from source, unlike Finding 011's `will_play` trigger point).

### How this could happen to a real user, not just an automated test

Selecting "gexis" once in the Spotify app while something else is playing is not, by itself, enough (per the isolation test). What plausibly *is* enough, without any test script involved:

- **The Spotify app's own network retry behaviour** — if the initial transfer request doesn't get a prompt acknowledgement (plausible if go-librespot is momentarily slow because ALSA is busy with LMS or Bluetooth), many mobile clients retry automatically over a flaky or slow connection.
- **An impatient repeat tap** — a user selects "gexis," hears nothing for a second or two (during LMS's ~3s release), taps again or hits play again.
- **More than one client acting on the same account near-simultaneously** — a phone and a tablet, or two family members, both selecting "gexis" around the same time.

None of this requires anything exotic — the common thread is just "try to switch to Spotify while another renderer is actively playing," the single most ordinary use of this arbitration system.

### Implications for the user, if it happens

The main symptom is silence lasting much longer than the normal handoff gap — no Spotify audio plays for the storm's duration (18 seconds, in the one case measured; not established as a bound). It self-resolved in the one instance observed, with no service restart needed, into normal playback. No evidence of data loss or corruption.

### Not fixed — George's decision, 2026-09-10

Deferred, not chased further for now: it hasn't shown up in any of the last several builds' worth of normal hands-on testing, only under this session's own repeated-API-call attack test. Revisit as soon as it's seen happening under normal use again — this note exists so a recurrence gets connected to this finding immediately rather than re-investigated from scratch.

---

## 3. go-librespot's own retry-then-reauth backoff after a failed device open is roughly 56 seconds, not immediate

**Found while building criterion 8's measurement harness**, not the attack test itself, but the same "repeated calls confuse go-librespot" family as §2.

**Observed:** running the criterion 8 harness's LMS-to-Spotify direction repeatedly (once every ~53-56s, one round after another, each round retrying its own trigger up to 4 times within a 12s-per-attempt budget) produced a sustained cycle, for at least 14 consecutive rounds (~13 minutes): arbitration correctly acquired Spotify and released LMS every single time (`release[lms]: freed within polite grace`, 3.1-3.2s, every cycle — arbitration itself never misbehaved), but go-librespot's own log showed it repeatedly failing `snd_pcm_open` as busy, followed roughly 56 seconds later by "loading previously persisted zeroconf credentials" / re-authentication, then another failed open attempt — a track's reported playback position never advancing (stuck at ~96s of a 128s track across the entire window). Real, working audio never once resulted from any of these 14 rounds.

**Confirmed not spontaneous:** the moment the harness was stopped, the cycle stopped completely — a 130-second idle watch of `gexis-core`/`go-librespot`'s logs afterward showed zero activity of any kind. This was a self-inflicted interaction between the harness's own retry cadence and go-librespot's own retry cadence, not a standalone new bug.

**The mechanism, as best explained by the evidence:** go-librespot does not retry a failed track load immediately once the device frees up — it appears to wait on the order of ~56 seconds before trying again, and that retry is bundled with a full fresh re-authentication handshake (persisted credentials reload → AP auth → Login5 auth), not just a plain retry of the ALSA open. The harness's own next round reclaimed the device (via a fresh LMS `play`) on almost exactly the same ~53-56s cadence, meaning every time go-librespot's slow retry timer was about to land on a freshly-freed device, the harness had already taken it back. Arbitration's own behaviour was correct throughout — the device genuinely was free for a window each cycle — it just never stayed free long enough to line up with go-librespot's own, much slower, retry schedule.

**Why this matters beyond the harness:** this looks like a strong candidate explanation for an item that has been an open, unexplained mystery in this project for longer than today's session — go-librespot's periodic "loading previously persisted zeroconf credentials" / re-authentication cycles observed with "no service restart between them and no matching 'accepted zeroconf from <device>' line... not tied to a fixed timer (gaps of 5m and 1m seen)". A ~56s backoff-then-reauth cycle, triggered whenever go-librespot's own track load fails against a busy device for any reason (not necessarily this harness — ordinary contention with LMS or Bluetooth in normal use would look the same from go-librespot's side), matches that description closely. Not proven to be the same mechanism — nothing directly ties the two together beyond the pattern matching — but it's the first concrete, evidenced hypothesis either has had. (See also §4 below, found immediately after this — a single-cycle defect that may be an even closer match for a *different* old unexplained report.)

**Consequence for criterion 8's own measurement:** the `takeover_gap.py` harness's retry design (re-firing the trigger every 12s) was itself provoking this — not measuring real takeover gaps at all in these runs, just perpetually racing go-librespot's backoff. **Fixed in the harness:** retries removed in favour of a single attempt per round with a 65-second cooldown and a clean-state check before the next round, so the harness stops interacting with go-librespot on a cadence close to its own retry timer.

**Not fixed in go-librespot/`SpotifyAdapter` itself** — a real product-facing consequence (ordinary contention — LMS still finishing up, say — could in principle leave Spotify silently stuck for up to a minute or more before its own next retry, rather than recovering promptly once the device is actually free) but not chased further this session, since it wasn't reachable from a single clean user action either (§2's isolation test) and needs its own dedicated investigation of go-librespot's retry/backoff logic — reading its source the way Finding 011 did for the acquisition signals, rather than inferring the exact timer from symptoms alone.

---

## 4. go-librespot can report an actively-playing state while never having opened the ALSA device at all

**Observed, after the harness fix in §3 removed the retry-storm confound:** a single, clean, unhurried arbitration cycle — LMS acquired (via one `cli.play()` call), then Spotify acquired (`will_play` → `acquire: spotify takes the device` → `release[lms]: freed within polite grace`, 3.1s, exactly the normal pattern, no storm, no rapid retries anywhere in this cycle) — completed according to `gexis-core`'s own log. Checked several seconds later:

- go-librespot's own `/status` endpoint: `"stopped": false`, a real, correct track name and metadata — it believes it is actively playing.
- `/proc/asound/card5/pcm0p/sub0/status`: **`closed`** — no PCM stream open on the DAC at all.
- `sudo fuser -v /dev/snd/pcmC5D0p`: no holder.
- `/proc/<go-librespot's own pid>/fd`: no file descriptor to anything under `/dev/snd/`.

Three independent, direct checks (not just this project's own `pcm_holder.py` tooling) agree: the hardware was never touched. go-librespot's internal belief that it succeeded is simply wrong.

**This is not the same defect as §2 or §3** — no repeated calls, no storm, no extended backoff cycle. One ordinary-looking takeover, and the renderer's own status was already lying about whether real audio was flowing by the time anyone checked.

**Confirms and sharpens Finding 011's own caveat** ("adapter-level signals aren't a proxy for 'sound is playing'" — noted there for a different reason, go-librespot's `active` event firing before ALSA access) — this shows the unreliability goes further: even a *later*, steady-state status read (well after acquisition, not just the initial event) cannot be trusted as evidence that audio is actually playing.

**Likely a better match than §3 for an old unexplained report:** HANDOFF's session history records "Spotify showing 'connected' but not sustaining a takeover from LMS" as unexplained. §3's ~56s-backoff theory requires *repeated* contention to explain that symptom; this finding shows it can happen from a **single, ordinary takeover attempt**, which fits an organically-reported symptom better. Neither is proven to be the actual historical cause — recorded as the best available candidate explanations, not a confirmed root cause.

### Implications for the user

A user could see "Connected to gexis" with a track name showing in the Spotify app, and hear nothing, indefinitely — not for a bounded window like §2's storm, but potentially until some other action (a fresh transfer, an app restart, a device reconnect) resets go-librespot's internal state. This was not tested to see how long it persists on its own; the one instance observed was still in this state when checked, and testing moved on rather than waiting it out further.

### Not fixed, not root-caused

Would need reading go-librespot's own source, the way Finding 011 did for its acquisition signals, to understand why its internal "playing" state can diverge this completely from actual ALSA device state. Not chased further this session — three of today's four findings are now specifically in go-librespot's own reliability, which is a bigger investigation than fits inside a Phase 2c criterion-8 measurement session.

---

## What this means for criterion 8

Given §3 and §4, any measurement of the Spotify leg of the takeover gap that trusts go-librespot's own reported state, rather than independently verifying real PCM activity (which `takeover_gap.py` already does — it uses `pcm_holder` and the spectrum FIFO as ground truth, not `spotify_api`'s status), would silently record false "successful, fast" handoffs when no audio ever played. The harness's design was already right to not trust it; the practical cost is that a meaningful fraction of measurement rounds may fail to produce a real handoff at all (for reasons unrelated to arbitration), which will make collecting a genuine ≥20-run distribution for the Spotify leg slower and noisier than for the LMS-only side. Not yet resolved — this is where testing paused for the session.
