# Finding 018 — the four Phase 2c blockers: root causes

> **Outcome, 2026-09-12:** blockers 2 and (partly) 1 are answered by
> **[ADR-0027](../decisions/0027-lms-power-as-arbitration-mechanism.md)** —
> LMS's player power becomes the arbitration mechanism (record the transport
> state, `pause`, `power 0` on release; power-on is the acquisition; restore the
> recorded state on return). Blocker 4 is fixed and verified. Blocker 3 still
> needs a post-reboot reproduction with logs. **Read the ADR for the decision;
> this finding is the evidence behind it**, in the order it was actually
> discovered, including the routes that were measured and closed.

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

## Second pass, same day — deeper investigation of blockers 1 and 2

George: both present bad user experience and cannot be left as they are.
Everything below was measured on `gexis` after the first pass.

### Blocker 1: an explicit seek on resume removes the jump entirely

LMS re-anchors its clock if it is *told* a position. Measured, 25s away:

| | first reading on resume | correct? |
|---|---|---|
| plain resume (today) | 57.84, against a true 32.72 | **+25.1s wrong** |
| resume, then `time <P>` | 44.50, against a true 44.50 | **exact** |

With the seek the value is right from the first reading and simply holds
at P for ~1s before advancing normally — the jump never appears. `P` is
free to obtain: we already call LMS at release time, so the paused
position can be captured there.

**Cost, not yet measured:** a seek makes LMS re-request the stream at that
position, so it can add a small delay and is a plausible source of an
audible artefact at the resume point. That needs a listening test, which
is George's call to make - this project has been burned before by taking
a measurement as proof of an *audible* result.

### Blocker 1: holding LMS paused until the device is free is REFUTED

The obvious alternative - re-pause LMS the moment it acquires against a
busy device, resume once free - was tested and makes things **worse**:

```
CONTROL:  +0.02s time=11.06 (wrong), +0.33s time=6.45 (corrected)
HOLD:     +0.02s ... +2.83s  mode='pause' time=24.87  <- frozen, wrong, for the whole hold
```

Re-pausing freezes the bogus value on screen for as long as we hold it,
instead of letting it self-correct. Recorded so nobody proposes it again.

### Blocker 2: the race cannot be won, and `stop` does not help either

Added to the `-C 0` result from the first pass:

| LMS release command | measured |
|---|---|
| `pause 1` | 1.43s, 1.45s — tight |
| `stop` | 1.04s, 1.85s — **inconsistent, no better on average** |

`stop` also costs the resume position outright, so it buys nothing.

### Blocker 2: what go-librespot actually does, and the one real defect

Traced its `/events` stream and `/status` through real transfers:

- At `will_play`, **`/status` already carries the intended position** -
  `{"uri": ..., "position": 619, "duration": 96898}` - so the position is
  recoverable if we want it.
- When its ALSA open fails it emits **`inactive` + `stopped`** - an
  explicit, hookable failure signal.
- It then **retries by itself ~0.2s after the device frees** (much faster
  than assumed), and in controlled runs **the position was preserved**
  (captured 497ms → playing from ~2.1s; captured 1035ms → ~2.15s).
- **`active` never fires afterwards: 0 of 2 controlled runs, 0 of 3 of
  George's organic handoffs.** It fires only when the *first* open
  succeeds (seen once, 18:42:50).

So the audio recovers on its own in ~2-2.6s with the position usually
intact. The **persistent** defect is that the Connect session is never
marked active, which is what leaves the phone showing 0:00 and a 0
duration while sound plays - ADR-0010's "never show a state the user
cannot account for," broken by go-librespot's own state machine.

Driving the recovery ourselves was tested: `POST /player/play
{"uri": ..., "seek_ms": <captured>}` returns 200, starts real playback and
preserves position - **but `active` still does not fire** (0/2). It would
make the position deterministic; it would not make the session honest, so
on its own it does not fix what George is actually seeing. This is the
same wall Finding 014's `/player/resume` hit, reached from a different
direction, and is recorded here so the third attempt is not made blind.

## Third pass: George's idea — release LMS by powering the player off

George proposed releasing the device by disabling the player in LMS for a
few seconds rather than killing squeezelite. Tested; it works, and it is
better than anything else examined for this race.

**It bypasses the `-C 1` idle timer completely** — the objection that
sank every other approach:

| LMS release command | device freed after |
|---|---|
| `pause 1` (as shipped) | 1.42s, 1.43s, 1.45s |
| `stop` | 1.04s, 1.85s (inconsistent) |
| **`power 0`** | **0.06s, 0.05s** |

0.06s lands far inside go-librespot's ~1s first-attempt window, so the
race that Findings 014/017 documented as unwinnable is won outright.
Measured end-to-end against a real Spotify transfer, `power 0` issued on
`will_play` exactly where the adapter would issue it:

| | `pause 1` (control) | `power 0` | `power 0` (repeat) |
|---|---|---|---|
| `will_play` count | 1 | 1 | 1 |
| first ALSA open succeeded | **no** | **yes** | **yes** |
| `inactive`/`stopped` (the failure signal) | — | none | none |
| **`active` fired** | **no** | **YES** | **YES** |
| spotify holding the PCM after | **never** | **0.7s** | **0.7s** |

`active` firing is the whole point: it is the event that has never once
appeared after a failed open (0/2 controlled, 0/3 of George's organic
handoffs), and it is what leaves the phone showing 0:00 against a 0
duration while sound plays. With this release path the first open
succeeds, so there is no retry, no reload at position 0, and the Connect
session is honest — all three halves of blocker 2 at once. The 0.7s
takeover is also far better than Finding 015's 1827.8ms LMS→Spotify
median, so criterion 8 should be re-measured on this.

**Two catches, both found in the same runs:**

1. **It does not fix blocker 1.** The elapsed-time jump survives a power
   cycle unchanged (+20.1s on resume). Blocker 1 still needs its own fix
   — the seek re-anchor above.
2. **`power 0` followed by a plain `play` restarts the track from 0.**
   Measured: released at 68.29, then `play` alone → `time=0`, climbing.
   `power 1` *then* `play` resumes correctly (60.22 → 60.55). This is the
   user pressing play in the LMS app while the player is off, and it
   turns blocker 2's symptom into an LMS-side one unless we power the
   player back on ourselves, or set the position explicitly. The seek
   re-anchor covers it, which is a reason to treat the two fixes as one
   design rather than two.

**Not yet established, and needed before this ships:** whether powering
off mid-playback is audible (a click at the cut); what it does to sync
group membership; whether it reduces the long-standing spurious LMS
reclaims (Findings 009/010 §4 — plausible, since a powered-off player
should not be told to play, but not tested); and Bluetooth's release path
is untouched by this, since `power` is an LMS concept only.

### Powering back on *during* the other renderer's session breaks it — measured

George's proposal was to power off "for 3 to 4 secs while the other
renderer takes over," then back on. Tested exactly that, and it does not
work — the player must stay off for as long as the other renderer holds
the device:

```
+0.52s  POWER 0
+1.02s  event: active        <- spotify's first open succeeds, as designed
        pcm=('spotify',)
+4.62s  POWER 1              <- powering LMS back on, spotify still playing
+5.58s  event: inactive      <- spotify kicked off
  +5s   pcm=('lms',)         <- LMS has taken the device back
```

**Why:** powering the player on restores its *previous transport state*,
which was `play` (it was playing when we powered it off). LMS therefore
resumes playback and squeezelite grabs the device back, evicting Spotify.
This is the spurious-reclaim shape, produced deterministically and on
demand — the first time that mechanism has been reproduced under control
rather than observed after the fact.

So the workable shape is: **stay powered off for the duration the other
renderer holds the device**, and power back on as part of LMS
re-acquiring. That is the version already measured as working (`active`
fires, first open succeeds, 0.7s takeover).

Its one real cost stands: a plain `play` against a powered-off player
auto-powers-on and **restarts the track from 0**, where `power 1` *then*
`play` resumes correctly (60.22 → 60.55). Since the user's play is what
triggers the acquisition in the first place, LMS has already restarted
from 0 by the time we see it — which is what makes the blocker 1 seek
re-anchor load-bearing rather than cosmetic: capturing the position at
release and seeking back to it on acquisition is what restores it. One
mechanism, both blockers.

### Verifying the power-as-acquisition signal — and a correction

The design rests on the LMS adapter being able to see, and act on, a
power-on before squeezelite needs the device. Measured on `gexis`, with a
subscriber built exactly like `LmsAdapter._watch()`.

**The two easy questions pass:**

- `power` **is** carried in the CometD push. Full key set captured:
  `can_seek, digital_volume_control, duration, mixer volume, mode,
  player_connected, player_ip, player_name, playlist mode, playlist
  repeat, playlist shuffle, playlist_cur_index, playlist_loop,
  playlist_timestamp, playlist_tracks, power, randomplay, rate, seq_no,
  signalstrength, time, use_volume_control`.
- Changing power **does** trigger a push, in **0.523s and 0.517s** — two
  rounds, consistent.

**The hard question fails.** squeezelite attempts its ALSA open
**58 milliseconds** after the power-on command (`power 1` sent
22:55:20.723; `alsa_open ... Device or resource busy` logged
22:55:20.781). Our notification arrives at ~520ms. **We are ~460ms too
late — the window is negative, not positive.** There is no arrangement in
which we release the outgoing renderer before squeezelite's first attempt.

**And losing that attempt costs 5 seconds.** squeezelite retries on a
strict 5.00s cadence — measured 22:55:20.781, 22:55:25.782, 22:55:30.783
— and **nothing shortens it**:

| after the device is free | squeezelite took it |
|---|---|
| do nothing | 2.53s |
| re-issue LMS `play` | 2.50s |
| power cycle the player | 2.42s |

All three simply wait for the next scheduled tick (the test deliberately
freed the device mid-way between ticks so there was ~2.5s to save).

**Correction to this finding's own earlier numbers, both measured wrong:**

1. "squeezelite's own recovery once the device *is* free: 0.96, 0.97,
   0.96, 0.90s" — **wrong**. That test freed the device about a second
   before a scheduled tick, so it measured the alignment, not a recovery
   time. The real behaviour is a 5.00s tick: 0-5s wait, ~2.5s average.
2. The first power-push run measured a "4.5s window" — **contaminated**.
   `gexis-core` was running throughout and released Spotify itself via the
   existing `mode`-based path, so that measured today's behaviour, not
   squeezelite's own timing.

**This explains Finding 015's Spotify→LMS number.** A median of 4170.9ms
with a stdev of just 33.2ms was always suspiciously deterministic for
something supposedly dominated by buffering and startup work. It is
squeezelite's 5s retry tick. It also explains George's own description of
blocker 1 self-correcting "in 3 to 5 seconds" — that is the remaining time
on the tick.

**What this does and does not change about the design:**

- **LMS as the outgoing renderer (power off): unaffected and still the
  win.** 0.06s release, Spotify's first open succeeds, `active` fires,
  0.7s takeover. Blocker 2 stands fixed by this.
- **LMS as the incoming renderer (power on as acquisition): does not fix
  the slow LMS takeover.** squeezelite races ahead of any signal we could
  receive, loses, and then waits out its tick. It is **no worse** than
  today — the same thing happens on the current `mode -> play` path — but
  it is not fixed, and it should not be claimed as fixed.
- Blocker 1's *visible duration* is therefore governed by this tick, not
  by the release. The seek re-anchor fixes the *size* of the wrong value;
  the tick decides how long it stays up.

**Open, and worth its own investigation:** whether squeezelite's retry
interval is tunable at all (no such option in `squeezelite -?`; `-C`
governs close-on-idle, not retry-on-busy), or whether the only route is
ensuring the first attempt never fails.

### The retry is not tunable — but pausing before powering off means we never need it

**Not tunable, confirmed from the complete option list.** `squeezelite -?`
(2.0.0-1517) has no retry-on-busy setting at all: `-C` is close-on-idle,
`-a` is buffer/period/format/mmap, `-r` is sample rates. Nothing governs
how often a failed ALSA open is retried.

**But the failed attempt is avoidable.** squeezelite only attempts an open
because power-on restores the player's previous transport state, which was
`play`. If the player is **paused before being powered off**, LMS restores
*paused*, squeezelite has nothing to play, and it never makes the attempt:

| release | state on power-on | squeezelite ALSA attempts | took the device after it was free |
|---|---|---|---|
| `power 0` while playing | `mode=play` | **1 (failed)** | 1.98s (waiting out its tick) |
| `pause` then `power 0` | `mode=pause` | **0** | **0.17s** |
| `pause` then `power 0` (repeat) | `mode=pause` | **0** | **0.07s** |

And pausing first costs nothing on the release side — measured
`pause 1` immediately followed by `power 0`: **0.06s, 0.07s, 0.07s,
0.11s**, indistinguishable from bare `power 0`.

So the 5s tick stops being something to live with: it is never reached,
because the first attempt is made against a device that is already free.
The sequence is release the outgoing renderer (~0.1s), then issue the
`play` the user's activation implied, and squeezelite takes the device in
under 0.2s.

**Blocker 1 is much improved but not eliminated by this alone.** Power-on
itself is clean — the player returns paused at *exactly* the stored
position, delta **+0.00s** in both runs, where powering off while playing
showed the usual away-duration error. But issuing the `play` re-introduces
the jump briefly, because LMS extrapolates from its stale anchor on any
play:

| | wrong value visible for |
|---|---|
| today | 3-5s (George's own report; the retry tick) |
| pause-before-power-off | **0.3s** and **1.6s** (two runs) |
| plus the seek re-anchor | **0** (exact from the first reading) |

Down from seconds to a flicker, and the seek removes the flicker.

**Harness note, not a product issue:** LMS intermittently returns a
gzipped body to a plain `urllib` POST, which crashed one diagnostic run
mid-measurement. The real adapter uses `aiohttp`, which decompresses
transparently, so this affects throwaway scripts only.

### A paused LMS never contends at all — so the broken case is always the playing one

George's refinement: on activation the player should be in whatever
transport state the user left it in, and since "in most cases the player
is paused," we should not trigger a play. Measured what "paused" actually
means for contention:

```
LMS playing, pcm=('lms',)
LMS paused (NOT powered off), pcm=()      <- -C 1 closed the device
  event: will_play / metadata / active / playing
  spotify took the pcm at: 0.93s
  will_play count: 1        (first open succeeded)
  ACTIVE fired: True
  inactive/stopped seen: False
```

**A paused LMS holds nothing**, so a takeover from it is already clean —
one `will_play`, first open succeeds, `active` fires, 0.93s. Blocker 2
**only ever manifests when LMS is actually playing** at the moment of
takeover.

That inverts the significance of "most cases are paused": those cases were
never broken. The contended case is always the playing case — and by
George's own rule, a player left playing must come back **playing**, which
is exactly the case that races squeezelite into its 5s tick.

**LMS already preserves transport state across a power cycle by itself:**
power off while playing → power on → `mode=play` and it resumes; pause
then power off → power on → `mode=pause`. So George's rule is satisfiable
with *zero* bookkeeping, simply by not pausing first. The decision is
therefore narrow and concrete:

| | paused case (never broken) | playing case (the broken one) | who issues the play |
|---|---|---|---|
| **plain `power 0`** | clean, 0.93s | resumes, but squeezelite races and loses → **0-5s** silence; full elapsed jump for that whole time | LMS, natively |
| **`pause` + `power 0` + restore** | clean, 0.93s | **0.07-0.17s**, no failed attempt; jump 0.3-1.6s, or zero with the seek | us, from one remembered bit |

Both honour "the state the user left it in". They differ only in whether
the resume command comes from LMS's own power-on restore or from us
replaying a state we recorded — and therefore in whether the only broken
case stays broken.

**This changes a decision, not just an implementation.** ADR-0010 states
that power state plays no role in arbitration ("A powered-off player is
one that will not play; it neither acquires nor releases"). Using power
as *the* release mechanism contradicts that directly, and it changes what
the user sees in the LMS app during another renderer's session (powered
off rather than paused — arguably more honest by ADR-0010's own
accountability rule, but a visible behaviour change either way). Per this
project's own rule it needs an ADR amendment before implementation, and
that is George's call.

## Follow-up, 2026-09-12: is LMS genuinely the loudest at full volume?

George, after testing 2d: "feels like LMS is still the loudest of the
three at full volume." Checked the whole gain path rather than assumed.

**All three map their own maximum onto the same DAC value, verified
directly** rather than derived from the formulas:

| renderer | at its own 100% | DAC |
|---|---|---|
| LMS | dummy `100 [0.00dB]` | **240 [0.00dB]** |
| LMS at 50%, as a control | dummy `18 [-24.60dB]` | 191 [-24.50dB] |
| Spotify | `volume 100/100` | **240 [0.00dB]** |
| Bluetooth | dummy max → 0dB by the same dB copy | 240 |

**No renderer has a hidden software stage at maximum:**

- **squeezelite** runs `-V Master` against the dummy card, i.e. *hardware*
  volume mode - its own help text is explicit that `-V <control>`
  replaces software volume adjustment. The stream leaves at full scale.
- **bluealsa-aplay** has `SoftVolume=false` on the PCM it actually reads
  (`a2dpsnk/source`, confirmed in `/var/lib/bluealsa/<MAC>`), so it passes
  through rather than attenuating. The stored `Volume=-562` matches the
  dummy's live `-5.70dB`, i.e. the **phone's own AVRCP position is in the
  chain** - Bluetooth is only as loud as the phone's slider.
- **go-librespot** has two knobs our config never sets -
  `normalisation_disabled` and `external_volume` - and they were the
  obvious suspects. **Measured, and they are not the cause.** Same track,
  Spotify at 100%, DAC at 240 in every run, level read off the peppyalsa
  spectrum FIFO:

  | config | mean level | peak | vs as-shipped |
  |---|---|---|---|
  | as shipped (neither set) | 40.8 | 70 | — |
  | `normalisation_disabled: true` | 41.0 | 71 | 1.00x |
  | + `external_volume: true` | 41.4 | 71 | 1.01x |

  At maximum, go-librespot's software volume is unity and normalisation is
  not attenuating, so neither knob buys anything. (They would still matter
  *below* maximum, where go-librespot's software volume and our hardware
  mixer both act on the same number - but that is a curve question, not a
  headroom one, and George's report is specifically about full volume.)

**So the gain path is equal and nothing was missed in it.** The level
difference that remains is source material: LMS's track `Rempompi` read
mean 50.2 / peak 78 at DAC 240, against Spotify's `Just Like That - Boom,
Clap` at mean 40.8 / peak 70 at the same DAC 240. **Different recordings,
so that gap is mastering, not routing** - it is not a fair loudness
comparison and should not be read as one. A conclusive test would need the
same recording through both services, which is not practically arrangeable.

**Scope:** one track per renderer, one session, levels read from the
spectrum FIFO (a relative meter, not a calibrated one). Bluetooth's own
maximum was not measured - it needs the phone's slider at maximum, which
needs George. What *is* established is that no renderer loses headroom to
a software stage of ours at full volume.

## What is deployed on `gexis` right now

Hot-patched into `/opt/gexis-core/venv/.../gexis_core/`, service restarted,
**not yet in an image**: the blocker 4 volume fix, and Finding 016's
polling fix (absent from this build, re-deployed because it shortens
blocker 1's visible window). Pre-patch copies of both files are at
`/tmp/volume.py.bak` and `/tmp/arbitration.py.bak` on the device.
