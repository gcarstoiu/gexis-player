# Phase 2c issues overview — for briefing a fresh session

**Date:** 2026-09-11
**Purpose:** self-contained summary of where Phase 2c's takeover-gap work
(criterion 8) currently stands and what's blocking it, written to be
pasted into a new session without requiring the full `HANDOFF.md`
history. Everything referenced here is committed on `phase-2c-takeover`.

## What Phase 2c is

Criteria 7-10 of Phase 2 (audio layer + arbitration): criterion 7 (attack
test - no two renderers ever hold the ALSA device at once) is **passing**.
Criteria 8-10 (measure the takeover gap between renderers, write it up,
decide if a UI transition screen is needed) are **in progress, currently
blocked** - see below.

## The system, briefly

One renderer plays at a time (LMS/squeezelite, Spotify Connect/
go-librespot, Bluetooth/bluealsa-aplay), arbitrated by `gexis-core`
(`core/src/gexis_core/`) - a `Supervisor` (`arbitration.py`) that takes a
renderer's acquisition event and releases whoever currently holds the
device via a timeout ladder (polite stop → SIGTERM → SIGKILL). LMS is the
permanent "base slot" - it pauses rather than disconnects, and must stay
running/connected to the LMS server at all times, whether or not it holds
the ALSA device. Full model in `docs/decisions/0010-arbitration-slot-model.md`
(ADR-0010) - long, but it's the one document that explains *why* each
piece is shaped the way it is, including several previously-tried-and-
reverted approaches.

## Today's session, in order

1. Built `takeover_gap.py`, a harness that measures the real gap (via
   peppyalsa's spectrum FIFO, not any renderer's self-reported state) for
   LMS↔Spotify handoffs.
2. Found and fixed a real bug (**Finding 014**): a single, clean
   LMS-to-Spotify handoff attempt failed almost every time - go-librespot
   tries to open the ALSA device within ~1s of its own acquisition
   signal, while LMS's own release takes ~3.1s, so it reliably loses that
   race. George picked a fix: `SpotifyAdapter` would retry itself via
   `POST /player/resume` (go-librespot's own local API) once LMS's
   release was confirmed. Verified against 21 real rounds (5 + 16)
   through the actual arbitration path.
3. Collecting the ≥20-run distribution then hit a **second** bug
   (**Finding 013 §1's recurrence**): squeezelite's systemd unit crashed
   into a restart-rate-limit failure (a previously-known defect, burst
   limit already raised 5→20 as a mitigation) - the raised limit was
   still exceeded (24 restarts) under repeated real rounds. Root cause:
   SIGKILL makes `Restart=on-failure` fire, but that automatic restart
   then races squeezelite's own ALSA-open startup test against whoever
   just took over, on systemd's own clock, independent of the
   arbitration ladder. George picked "fix the race, not raise the limit
   again": switched to `systemctl stop` (suppresses automatic restart
   entirely) plus an explicit, adapter-driven restart once the incoming
   renderer had its own chance at the device. Verified clean across 35
   scripted rounds (15 + 20) through the real arbitration path.
4. Both fixes together produced a clean **Finding 015**: the actual
   same-rate LMS↔Spotify takeover-gap distribution (LMS→Spotify n=36,
   median 1827.8ms; Spotify→LMS n=20, median 4170.9ms).
5. Rebuilt and reflashed the image with both fixes baked in (not just
   hot-patched). Also added build-filename versioning (unrelated,
   separate ask) and confirmed a full 60,974-track library scan found no
   non-44.1kHz content (blocks the cross-rate leg on content, not
   mechanism).
6. **Continued live use (not scripted testing) found both of today's
   fixes cause real regressions - both reverted the same day.** See below.

## Blocker 1: Finding 014's fix broke Spotify Connect's own state

**Symptom, from George, live:** after an LMS-to-Spotify handoff, audio
plays correctly through `gexis`, but the Spotify app shows "gexis
disconnected." Pressing "next" moves playback to the phone instead of
`gexis`.

**Confirmed mechanism** (not just inferred from the symptom - checked
directly in `gexis-core`'s own log): some `will_play` acquisitions were
followed by the normal `spotify: device became active` line (the proper
Spotify Connect handshake completing); others - the ones where
`/player/resume`'s rescue must have been what actually got audio playing
- were never followed by `device became active` at all, for the
remainder of that Spotify session. `POST /player/resume` can get
go-librespot to resume real local ALSA playback of an already-loaded
track without completing whatever internal step actually tells Spotify's
own cloud backend "gexis is genuinely the active device." Audio flows
locally; Spotify's own Connect state never finds out.

**Why scripted testing didn't catch it:** every check in this project's
own harness (and every ad hoc check made while building the fix)
verifies real PCM activity as the definition of success - correctly, per
this project's standing rule not to trust a renderer's self-reported
state. But *Spotify's own cloud-side Connect state* is a third thing,
separate from both "PCM is open" and "gexis's local `/status`" - nothing
checked it, because nothing before this fix had ever caused it to
diverge from local reality.

**Current state:** reverted. `SpotifyAdapter.device_freed()` is back to
a no-op (inherited from the base `Adapter` class). The underlying race
Finding 014 describes (a lone LMS-to-Spotify attempt loses to LMS's
release almost every time) is **unresolved again**.

**What a real fix needs:** something that completes Spotify Connect's
actual handshake, not just gets ALSA audio flowing. Two unstarted leads:
reading go-librespot's own source (`daemon/controls.go` was already read
once for a different signal, per ADR-0010/Finding 011 - the same kind of
read is needed here) to find what internally triggers `"active"`, and
checking whether go-librespot exposes any *other* local endpoint that
completes that handshake properly (only `/player/resume` was tried).

## Blocker 2: Finding 013 §1's fix survived scripted testing but not real use

**Symptom:** squeezelite (LMS's renderer) crashed into systemd's
`StartLimitBurst` failure state again, hours after 35 clean scripted
rounds had passed with the fix in place. `gexis` silently drops off the
LMS server's player list when this happens (confirmed pattern from the
original Finding 013 §1).

**Confirmed mechanism, the recurrence:** the fix (`systemctl stop`
instead of a raw kill signal, plus an adapter-driven explicit restart
once the incoming renderer had a chance to settle) had a residual risk
its own documentation already named: if that one explicit restart also
finds the device still busy, `Restart=on-failure` (never actually
disabled) takes over from there, and the same restart-storm can still
happen. It happened for real after continued use with Bluetooth
connecting and reconnecting several times in a row - plausibly the rapid
churn kept re-triggering LMS's kill-and-restart cycle faster than the
device could reliably settle.

**Current state:** reverted. `LmsAdapter.signal_stop` is back to plain
`kill_unit(force=True)`; the explicit `restart_after_release` override is
removed. `Restart=on-failure` is squeezelite's only path back again -
the original, longer-tested (if imperfect) behaviour, with the burst
limit still at its already-raised value of 20.

**What a real fix needs:** something that survives *sustained, real
usage with Bluetooth churn*, not just a clean scripted batch run
back-to-back. The 35-round verification this session did was real
evidence for the load pattern it tested, and it was still not enough -
a next attempt should specifically include a Bluetooth
connect/disconnect/reconnect cycle repeated several times while LMS↔
Spotify switching is also happening, not just one or the other in
isolation.

## What's NOT blocked

- Criterion 7 (attack test) - still passing, unaffected by any of this.
- The measurement harness itself (`takeover_gap.py`, `spectrum_fifo.py`'s
  FIFO-based gap detection) - the mechanism is sound; Finding 015's
  actual numbers (collected while both fixes were live) are believed
  accurate as *measurements*, just not representative of what's shipping
  now that the mechanisms that produced them are reverted.
- Bluetooth pairing/connection itself, mechanically - needed three
  attempts to first connect after this session's reflash, then was
  stable. Not investigated, not currently blocking, but worth knowing if
  it recurs.

## Where to pick this up

- `HANDOFF.md`'s own Phase 2c section (search "Same day: image rebuilt")
  has the full session narrative with timestamps.
- `docs/findings/014-lms-to-spotify-first-attempt-race.md` and
  `docs/findings/013-phase2c-attack-test-and-spotify-reliability-defects.md`
  (§1's addendum) have the full evidence trail for each blocker,
  including the "Reverted" sections added the same day.
- `docs/decisions/0010-arbitration-slot-model.md` has both amendments and
  both reverts, with the reasoning for each.
- The image currently flashed on `gexis` has both reverts baked in - check
  its own version string (`/opt/gexis-core` or the build's `.info`
  manifest, once shipped onto the image - see HANDOFF's own "Build
  self-identification gap" note, still open) before assuming which
  behaviour is live.
