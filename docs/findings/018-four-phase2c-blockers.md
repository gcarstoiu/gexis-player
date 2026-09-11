# Finding 018 — the four Phase 2c blockers: root causes

**Date:** 2026-09-11
**System:** `gexis`, freshly reflashed build (booted 18:36, SSH host key regenerated accordingly). **This image predates Finding 016's polling fix** — `POLITE_POLL_INTERVAL` was absent from the installed `arbitration.py`, so every measurement below marked "as shipped" was taken with the old blind 3.0s polite-grace sleep still in place.
**Question:** George reported four blockers after testing this build and asked for root causes, fixed on `gexis` first. Numbered here as he numbered them.

---

## Blocker 1 — LMS's elapsed time jumps ahead, then back

**Root cause: LMS's own server-side behaviour on resume. Not gexis-player,
and not fixable in gexis-player.**

Reproduced directly, with **no arbitration involved at all** — a plain LMS
pause/resume driven from the LMS CLI, no Spotify, no Bluetooth, no
takeover:

```
playing:  mode=play  time=157.69
paused:   mode=pause time=157.69
  (waited 30s - standing in for the other renderer's session)
still paused after 30s: time=157.69      <- the server clock does NOT drift
resumed; polling reported elapsed:
  +0.10s  mode='play' time=186.93   <-- AHEAD by 29.2s
  +0.41s  mode='play' time=158.33   <-- corrected
  +0.71s  mode='play' time=158.64
```

At the instant of resume LMS reports `paused_position + away_duration`
(157.69 + ~29.2 = 186.93), then corrects to the true position as soon as
squeezelite actually starts and reports where it really is. The pause
itself is clean — the server's stored position never moved during the 30s
wait, which rules out "the pause didn't take."

That is exactly George's description: correct, then ahead by the time the
other renderer was connected, then back. The "at the beginning of a track
it tries several times before it starts counting" part is the same
mechanism with a small position, corrected repeatedly as squeezelite's
first ALSA open fails and retries.

**What we control:** only *how long the wrong value is visible*. It shows
until squeezelite actually starts, which it cannot do until the outgoing
renderer releases the ALSA device. In the isolated test above (device
already free) the wrong value was visible for 0.3s. In a real takeover
it persists for the whole release — measured on this build at 2.5-2.9s
for Bluetooth and, with the blind sleep, up to 3.2s for LMS. Shortening
the release shortens the symptom; it cannot remove it.

**Scope:** one track, one LMS server, 30s away time, four resumes. Not
established: whether the size of the jump tracks the away duration exactly
at other durations (it matched to within 0.8s here), or how other LMS
clients render the same transient.

---

## Blocker 2 — Spotify's position resets instead of continuing

**Root cause: Finding 014's Mode A race, still open, now measured
end-to-end. The numbers say why it cannot currently be won.**

Measured on this build:

| Term | Measured |
|---|---|
| LMS release: pause command → squeezelite actually off the PCM | **1.43, 1.49, 1.43, 1.43s** (mean 1.44s, n=4) |
| go-librespot's own ALSA open attempt, after `will_play` | ~1s (Finding 014) |
| squeezelite's own recovery once the device *is* free | **0.96, 0.97, 0.96, 0.90s** (n=4) |

go-librespot attempts its open about 0.4s before LMS has let go. It loses,
and the retry that follows reloads the track at position 0 — which is the
reset George sees. When that retry is the phone/Spotify backend's own, the
Connect handshake often never completes, giving the other half of his
report: audio plays while the app shows elapsed 0 and duration 0 (this is
Finding 017 — the missing `active` event, which reproduces with our own
retry hook sitting at its inherited no-op, so it is not caused by the
reverted `/player/resume` fix).

**Three levers examined; all three are currently closed:**

1. **Release faster than go-librespot's ~1s attempt.** `-C 1` is the
   floor. Tested `-C 0` directly on the box: squeezelite then **never
   releases at all** (4/4 runs, no release within 20s) — `-C 0` disables
   the idle close rather than making it immediate. Reverted; `-C 1`
   confirmed restored at 1.43s. Of that 1.44s, roughly 0.44s is LMS
   server→squeezelite propagation and ~1s is the idle timer, so even a
   hypothetical sub-second `-C` only reaches ~0.44s, and squeezelite's
   own parser takes `-C` in whole seconds.
2. **Acquire on something earlier than `will_play`.** Traced go-librespot's
   `/events` stream through a real transfer: `will_play` is the **only**
   event emitted before the failed open. There is nothing earlier to hook
   — Finding 011 already moved us to the earliest signal that exists.
3. **Nudge the incoming renderer once the device is free.** Already
   reverted for Spotify (`/player/resume` completes playback without
   completing the Connect handshake — ADR-0010). Tested the LMS analogue
   too, and it is not needed there: re-issuing LMS play the moment the
   device frees made **no difference** (0.97s and 0.90s, against 0.96s
   for doing nothing) because squeezelite already retries on its own
   ~1s cadence.

**Not fixed.** Every remaining option is a trade-off this project has
already paid for once (killing squeezelite → restart storms; resuming
go-librespot → a lying Connect session). This needs George's decision, not
another unilateral attempt — the two reverts this week both came from
shipping a fix for this exact race before its cost was understood.

---

## Blocker 3 — Bluetooth doesn't connect on the first try after a reboot

**Not root-caused. Every static cause is ruled out, and the run-time
evidence does not exist yet.**

Checked on this build, all correct:

- `bluealsa-aplay` is ordered `After=bluealsa.service` (the race from the
  2026-09-07 session is genuinely fixed in this image)
- rfkill: soft blocked `no`, hard blocked `no`
- the phone is paired **and** `Trusted: yes`
- `gexis-bluetooth-setup` and `gexis-bluetooth-trust` both enabled

And on the one boot available, **the first connect actually succeeded** at
the profile level: phone connected 18:37:18, A2DP endpoints registered,
`MediaTransport1` appeared, arbitration acquired for Bluetooth. Audio
started at 18:42:18 — five minutes later, consistent with nobody pressing
play until then rather than with a failure.

**Why there is nothing more to go on:** `journalctl --list-boots` shows
exactly one boot. The image was flashed at 18:36, so no earlier boot's
logs exist. `/var/log/journal` *is* present and `Storage=auto`, so logs
**will** persist from here on — meaning the next reboot's first connect
attempt is capturable, and this is diagnosable as soon as it is
reproduced once with logs. Until then, any root cause would be a guess.

---

## Blocker 4 — Spotify's volume range is smaller than Bluetooth's

**Root cause found, fixed, and verified on hardware.**

`VolumeBridge`'s echo suppression was a blanket 750ms time window: after
any write of our own, *every* incoming volume event was discarded for
750ms. A real slider drag is a rapid burst of genuine, different values,
so the first one through armed the window and the rest — including the
value the user let go on — were thrown away.

Measured on the shipped build, driving go-librespot's own volume API:

| Ramp to 100/100 | go-librespot | hardware DAC |
|---|---|---|
| fast (0.15s apart, like a drag) | 100/100 | **226/240 — 7.0dB low** |
| slow (1.5s apart, control) | 100/100 | 240/240, correct |
| fast (repeat) | 100/100 | **226/240 — 7.0dB low** |

Both dummy controls (LMS, Bluetooth) reach 0dB at their own maximum and
**lost their echo windows** when `DummyMixerBridge` was fixed on
2026-09-08 — that fix's own docstring describes this identical bug and
names "Bluetooth's usable maximum reading quieter than Spotify/LMS's" as
its symptom. Spotify was simply the one renderer still carrying it, which
inverted the comparison into what George reported.

**Fix: value-matched echo suppression instead of a time window.** We record
the exact value we wrote in each direction and drop exactly one incoming
signal carrying *that* value; anything different is genuine and is applied
however fast it arrives. The record expires after `ECHO_WINDOW_S` so a lost
or differently-rounded echo cannot suppress a later genuine change.

**Verified on hardware after deploying:** fast ramp now reaches **240/240**,
matching the slow ramp, reproducibly (3/3). **Ratchet regression checked
explicitly** — the failure the original window existed to prevent: a single
deliberate `amixer sset DAC 200` while Spotify was active held at exactly
200/240 across 16 consecutive readings over 8s, with no downward walk. The
two scales are stable inverses to within one step (raw 226 → 84/100 → raw
226, checked against the live control), so a round trip either matches the
expectation and stops or lands one step away and stops on the next hop.

---

## What is deployed on `gexis` right now

Hot-patched into `/opt/gexis-core/venv/.../gexis_core/`, service restarted,
**not yet in an image**: the blocker 4 volume fix, and Finding 016's
polling fix (absent from this build, re-deployed because it shortens
blocker 1's visible window). Pre-patch copies of both files are at
`/tmp/volume.py.bak` and `/tmp/arbitration.py.bak` on the device.
