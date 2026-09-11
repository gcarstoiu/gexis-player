# Finding 013 — Phase 2c attack test: squeezelite's restart-limit exhaustion, and a go-librespot acquisition retry storm

**Date:** 2026-09-10
**System:** `gexis` — the image-built target, rebuilt same day (`v0.2.1-15-g2396ea2-dirty`, includes Finding 011's two signal fixes).
**Question:** Criterion 7's attack test — can adversarial, repeated takeover attempts across LMS/Spotify/Bluetooth ever leave the system in a bad state, even if no two renderers ever hold the device at once?
**Answer:** Two distinct defects found, neither of which is "two renderers holding the device simultaneously" (that invariant held throughout, 0 violations across every scripted race — see the session's attack-test runs). Both are documented here because an attack test is specifically supposed to surface exactly this class of problem.

---

## 1. squeezelite's restart-rate limit can be exhausted by legitimate arbitration activity

**Root cause, confirmed from `journalctl -u squeezelite`:** rapid adversarial takeovers during the criterion 7 attack test caused the arbitration ladder to `SIGKILL` squeezelite while the ALSA device was still busy (held by whichever renderer had just taken over). squeezelite's restart raced the same busy device, failed immediately (`test_open:281 playback open error: Device or resource busy`), exited, and systemd restarted it again — five times within about 15 seconds, tripping `StartLimitBurst=5`/`StartLimitIntervalSec=60`. Once tripped, `squeezelite.service` went to a **permanently failed state** with no further auto-restart. `gexis` silently dropped off the LMS server's player list from that point on ("player count 1", only "Moode" registered) until a manual `systemctl reset-failed squeezelite && systemctl start squeezelite`.

**Consequence while it lasted:** every LMS-side test command sent afterward (`play`, `pause`) was silently accepted by the LMS server and had zero effect, because the target player no longer existed. This produced about 20 minutes of confusing, hard-to-diagnose session behavior before the actual cause (squeezelite's own unit state, not any arbitration logic) was found.

**Fixed:** `StartLimitBurst` raised 5→20 (`image/stage-gexis/02-renderers/files/squeezelite.service`, commit `2eec5f9`), applied live on `gexis` and ported into the image source. 20 gives real adversarial racing enough headroom while a genuinely misconfigured unit (wrong flags, missing device — the scenario the original limit of 5 was sized for, per the unit's own comment) still gives up within the same 60-second window at `RestartSec=2`.

**Not fixed, and arguably the more correct fix if this needs revisiting:** the underlying race — SIGKILL firing before the device is confirmed free — still exists. Raising the burst limit is a safety margin, not a cure; see `docs/DEVELOPMENT.md`'s own note on this in the "things that will bite" pattern. Not chased further this session.

---

## 2. go-librespot can enter a rapid internal acquisition-retry storm

**Observed:** during the criterion 8 measurement harness's testing (which calls Spotify's Web API `PUT /me/player` — "transfer playback to gexis" — repeatedly, retrying every ~12s across up to 4 attempts per round, across 5 rounds), `gexis-core`'s log showed `spotify: will_play (acquisition, ahead of ALSA open)` fire **roughly 90 times in about 18 seconds** (18:23:37.637–18:23:55.930, this session's log), i.e. every 50–300ms — far faster than anything my own script was doing (my own retries are ~12s apart). The system recovered on its own: the storm stopped, then a single clean `will_play` → `device became active` pair followed a few seconds later.

**Isolation test, done specifically to answer "would a real user's single action trigger this":** with LMS confirmed genuinely playing (holding the device), I made **exactly one** `transfer_to_gexis()` call — the same API action a phone tapping "gexis" in the Spotify Connect device picker performs — and this time got a single clean cycle: one `will_play`, immediate `acquire: spotify takes the device`, `release[lms]: freed within polite grace (3.1s)`. No storm.

**What this establishes and what it doesn't:**

- **Confirmed:** the storm is real, reproducible under repeated/rapid transfer calls, and self-resolving (not a permanent hang, in the one case observed).
- **Confirmed:** a single, isolated transfer call under the same precondition (LMS actively holding the device) does **not** reproduce it.
- **Not established:** the exact number or pattern of repeated calls needed to trigger it. It happened somewhere within a test sequence of up to ~20 calls spread over several minutes; it did not happen with 1 call. The boundary in between was not isolated further this session — doing so would mean more rounds of the same repeated-API-call testing that produced the storm in the first place, which trades investigation time for a more precise number without changing what to do about it.
- **Not established:** the exact internal trigger inside go-librespot. The pattern (`will_play` — "emitted in `loadCurrentTrack`, before any ALSA access", per `SpotifyAdapter`'s own docstring — firing every 50-300ms) is consistent with go-librespot's own internal retry-on-failed-ALSA-open logic spinning much faster than its normal call cadence once something puts it in that state, but this is read from the *symptom*, not from go-librespot's own source (unlike Finding 011's `will_play` trigger point, which was confirmed against `daemon/controls.go` directly).

### How this could happen to a real user, not just an automated test

The single-call isolation test shows that **just selecting "gexis" once in the Spotify app while something else is playing is not, by itself, enough** to cause this. What's needed is *repeated* transfer/play attempts landing close together while the device is busy. Realistic ways that happens without any test script involved:

- **The Spotify app's own network retry behaviour.** If the initial "transfer to this device" request doesn't get a prompt acknowledgement — plausible if go-librespot is momentarily slow because ALSA is busy with LMS or Bluetooth — many mobile clients retry the request automatically over a flaky or slow connection, without the user doing anything else.
- **An impatient repeat tap.** A user selects "gexis," hears nothing for a second or two (during LMS's ~3s release), and taps "gexis" again or hits play again. Each tap is a fresh transfer call landing on the same busy-device condition.
- **More than one client acting on the same account near-simultaneously** — e.g. a phone and a tablet, or two family members, both selecting "gexis" around the same time.
- **A possible connection to an already-open, unexplained item:** `gexis-core`'s log has separately shown go-librespot periodically re-authenticating with Spotify's backend ("loading previously persisted zeroconf credentials" / "authenticated AP" cycles with no service restart, on no fixed timer) with no explanation yet found for what triggers it. If one of those cycles happens to coincide with the device being busy, it's a plausible (not confirmed) additional source of repeated internal retries beyond anything the user or an app does directly.

None of these require anything exotic — the common thread is just "try to switch to Spotify while another renderer is actively playing," which is the single most ordinary use of this whole arbitration system, not an edge case.

### Implications for the user, if it happens

- **The main symptom is silence lasting much longer than the normal handoff gap.** Every `will_play` during the storm is go-librespot failing to open the busy ALSA device and retrying — no Spotify audio plays for the storm's whole duration (18 seconds, in the one case measured; not established as a fixed or bounded duration).
- **This is a strong candidate explanation for an already-reported, previously unexplained symptom:** HANDOFF's own session log records "Spotify showing 'connected' but not sustaining a takeover from LMS." A storm exactly matches that description from the user's side — the phone shows Spotify connected to "gexis" (the Connect handshake itself succeeded), but no sound plays because go-librespot is stuck retrying the actual device open. Flagged as a plausible match, not a confirmed root cause of that specific past report — nothing ties this storm to that exact prior incident directly.
- **It self-resolved in the one instance observed**, recovering into a normal, working playback state a few seconds after the storm ended, with no service restart needed. Whether it can persist indefinitely or contribute to further problems (e.g. compounding with the squeezelite restart-limit issue above, if LMS is also being hammered at the same time) is not established.
- **No evidence of data loss or corruption** — this is a responsiveness/silence problem, not a playback-correctness one.

### Not fixed

Nothing has been changed in `SpotifyAdapter` or go-librespot's own configuration for this. Given the single-call test shows normal single-action use is unaffected, and the storm both requires unusual repeated-call conditions and self-resolved in the one observed case, this is being recorded as a finding rather than acted on immediately — worth a decision on whether it needs a debounce/rate-limit on repeated transfer calls (in `SpotifyAdapter`, separate from arbitration's existing "already current, ignore" check, which does not prevent go-librespot's own internal retries) or whether it's rare/self-healing enough to leave alone.
