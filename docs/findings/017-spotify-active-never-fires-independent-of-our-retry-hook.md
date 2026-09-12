# Finding 017 — Spotify's "active" event doesn't fire on the automatic retry either, independent of our own reverted hook

**Date:** 2026-09-11
**System:** `gexis`, live (hot-patched, Finding 016's fix deployed), current committed state otherwise (`SpotifyAdapter.device_freed()` confirmed the inherited no-op, byte-for-byte matching what was live at Phase 2b's close — see git evidence below).
**Question:** George reported LMS→Spotify handoffs tonight resetting elapsed time and not playing until "next" is pressed, and stated this pairing "used to work just fine at the end of Phase 2b — no issue whatsoever." This finding investigates whether that's a regression from tonight's changes, from the Finding 014 revert, or something else.

## The code hasn't changed for this path

Checked directly, not assumed:

- `SpotifyAdapter`'s acquisition logic (`will_play` as the early signal, no
  retry hook) is byte-for-byte identical right now to what was live when
  Phase 2b closed (2026-09-10). The `will_play` signal was added at
  13:13 that day (`d4048ef`); the only other same-day commit
  (`1afd17d`, 14:56) touched Bluetooth/volume code, not Spotify's
  acquisition path. `device_freed()` didn't exist yet at that point — it
  was added the next day (`554252e`, Finding 014) and reverted
  (`17dcdb3`) back to the exact same no-op.
- `LmsAdapter`'s release path is likewise unchanged since 2026-09-08
  (last touched by `adfe444`/`16ab8d2`/`0c128c3`, all before Phase 2b
  closed) — the Finding 013 §1 stop_unit/restart_after_release change
  landed and was reverted entirely within 2026-09-11, netting no change.
- Confirmed the live device isn't drifted from git either: diffed
  `arbitration.py`, `adapters/spotify.py`, `adapters/lms.py`, `alsa.py`,
  `volume.py` as actually installed in `/opt/gexis-core/venv/.../gexis_core/`
  against this repo's current HEAD — all five matched exactly.
- The only relevant systemd-unit change after Phase 2b closed is
  `2eec5f9` (2026-09-10 18:55, `StartLimitBurst` 5→20) — the restart
  burst ceiling, unrelated to release/acquisition timing.
- Tonight's own fix (Finding 016) only touches `arbitration.py`'s
  polling loop and, if anything, makes LMS's release *faster*
  (1.4-2.1s measured tonight vs. the pre-fix uniform 3.1-3.2s) — it
  narrows the race described below, it cannot have introduced it.

**Conclusion: whatever George saw tonight is not caused by any code
change since Phase 2b closed, including tonight's own fix.**

## What's actually happening, reproduced live tonight

Two pieces of evidence, both from tonight:

**1. Organic phone-driven handoffs (George's own testing, three LMS→Spotify
takeovers, 16:25-16:26).** Every one showed the identical shape in
`go-librespot`'s own log: a first `snd_pcm_open` attempt failing
(`Device or resource busy`) immediately on acquisition, followed
~1.4-3.5s later by a second, successful "loaded track" log line
(position 0ms, paused: false) — a real automatic retry, not driven by
any of our own code (`device_freed()` is the no-op). **`gexis-core`'s own
log never showed `device became active` for any of the three** —
confirmed by grepping the full window.

**2. A controlled, single-attempt diagnostic (`tools/phase-2c/
diag_one_transfer.py`, run live on `gexis` twice tonight to pin this
down).** One run hit a transient Spotify Web API 500 with no dealer
request reaching go-librespot at all (a separate, already-documented
flakiness — see `spotify_api.py`'s own comment). The second run
reproduced Mode A cleanly: `will_play` fired, `snd_pcm_open` failed busy,
LMS's release completed 1.5s later ("freed within polite grace"), and
**no automatic retry arrived in the remaining ~16.5s of the diagnostic's
own monitoring window** — the PCM holder went from `lms` straight to
empty and stayed empty. A bare single Spotify Web API transfer call, with
nothing else acting on it, just loses and stays lost.

## The important part: this isn't our own retry hook's bug

Finding 014's second half (the reason `device_freed()` was reverted)
attributed "audio plays, but Spotify's app shows disconnected and `next`
routes to the phone" specifically to our own `POST /player/resume` call
completing a *different* internal step than the one that emits `active`.
That attribution was too narrow. **Tonight's organic handoffs hit the
identical "will_play with no following active" gap with `device_freed()`
sitting at its inherited no-op the entire time** — the phone/Spotify
backend's own automatic retry (whatever triggers the "loaded track" log
line ~2-3s later) exhibits the same incompleteness on its own, with zero
code of ours involved. Reverting our hook removed our own contribution to
triggering this gap, but did not remove the gap itself, since go-librespot
apparently reaches it through its own retry path too.

## Why Phase 2b's close looked clean — best available explanation, not confirmed

LMS's own release latency (pause command round-trip to squeezelite
actually letting go) has never been measured under ~1.4s in any sample
this project has on record, from Finding 015's original data through
tonight's — it consistently misses the sub-second "pre-sleep check" path
that Spotify's own releases usually hit. Since go-librespot attempts its
ALSA open within about a second of acquisition (established in Finding
014), the shape of this race — first attempt likely loses, recovery
depends on an automatic retry that may or may not complete the `active`
handshake — has plausibly existed the whole time, including at Phase 2b's
close. The most likely explanation is that this specific failure mode
(visible reset-and-stall, needing a manual skip) simply wasn't hit or
wasn't noticed during whatever testing informed "Phase 2b closed" — not
that a mechanism actually changed. **Not proven** — no log evidence from
that day exists to check against, and George's own recollection is that
he tested this specifically and it was clean.

## Status

Not fixed. Reproduced and root-caused (a real, not-yet-explained gap
between "go-librespot loaded a track" and "go-librespot's own `active` WS
event fires," present in go-librespot's own retry path independent of any
of our code) — not yet turned into a fix candidate. George asked to
investigate this now, ahead of the originally-planned Bluetooth-churn
verification for Finding 016 — see HANDOFF.md for what's next.
