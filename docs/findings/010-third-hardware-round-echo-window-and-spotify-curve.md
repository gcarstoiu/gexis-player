# Finding 010 — Third hardware round: DummyMixerBridge's echo window and Spotify's curve, both fixed; Bluetooth race and LMS reclaim narrowed further

**Date:** 2026-09-08
**System:** `gexis` — live hardware, patched in place via SSH, same
pattern as Findings 008/009. Logs pulled from `journalctl -b` covering
George's test session (16:07-16:38), plus live reproduction after each
fix.
**Scope:** George tested the image built after Finding 009's three
volume fixes and reported four symptoms. Two have confirmed root causes,
fixed and verified live. Two are narrowed with new, more precise
evidence but not fixed - reported honestly rather than guessed at,
matching Finding 009's own convention.

---

## 1. Spotify volume compressed into the last part of the slider — FIXED

**Symptom:** "at 60% volume there is no sound coming."

**Root cause: the identical bug LMS had (Finding 009 §2), on the
renderer that fix never touched.** `_on_spotify_volume` mapped Spotify's
own `value/max_` fraction *linearly in raw steps* onto the DAC's full
0..240 - and raw steps are dB-linear, not perceptually linear (already
established, `raw_to_db`'s own docstring). Confirmed directly from the
log: at Spotify's own reported 60%, the mirrored hardware value was
144/240 = -48dB - quiet enough to read as silent in a normal room,
exactly George's report. This bug was never new; it's plausible George
couldn't have reliably assessed Spotify's curve *before* this round,
since Finding 009 §1's echo-window bug made Spotify's volume racy and
unpredictable until that was fixed - the curve was always wrong, but
only became something a person could actually judge once the control
itself became deterministic.

**Fixed the same way LMS was:** `spotify_fraction_to_hardware_raw()` and
its inverse `hardware_raw_to_spotify_fraction()` map dB-linearly across
-45..0dB - the same effective span LMS's own curve settled on via the
dummy control (Finding 009 §2), chosen here for consistency across
renderers' sliders rather than derived from anything Spotify-specific
(Spotify has no hardware control of its own to derive a span from).
`_on_spotify_volume` and `VolumeBridge.run()`'s hardware-changed path
both go through it now.

**Verified by unit test and hand computation**, not live: 60% now
computes to -18dB (raw 204) instead of -108dB (raw 144). Round-trip
tests confirm the reverse direction recovers the original fraction
within one raw step's rounding. **Not independently re-verified against
a live phone-driven volume change this round** - go-librespot's own
`/player/volume` HTTP endpoint (which our code calls) does not echo the
change back over its WS event stream the way a phone-driven change does,
so there's no way to trigger `_on_spotify_volume` from this SSH session
without a real Connect session. Confidence is high (identical formula
shape, unit-tested, already validated live for LMS's own case), but this
specific renderer's live confirmation is the next test.

## 2. Bluetooth's usable maximum quieter than Spotify/LMS, and a session with zero mirrored volume changes — FIXED, a real bug in `DummyMixerBridge`

**Symptom:** "Bluetooth max volume is smaller than Spotify or Lms."

**Root cause, confirmed by re-reading the code, not just the log: an
echo window that could only ever do harm.** `DummyMixerBridge` was
carrying an echo-window mechanism copied from `VolumeBridge` when it was
written (B2, Finding 008) without re-deriving whether it actually
applied - it doesn't. `VolumeBridge` both *watches* and *writes* the
same real-DAC `alsactl` stream, so its own writes genuinely echo back on
it, and the window exists specifically to recognise "that was us, not a
new external change." `DummyMixerBridge` watches the *dummy* card but
writes to the *real DAC* - two different ALSA cards. A write to the real
DAC cannot possibly show up on the dummy card's own monitor stream. The
window could therefore never see a genuine echo of its own write; all it
ever did was silently swallow *real* updates from squeezelite/
bluealsa-aplay arriving within 0.75s of the previous mirror.

This session's log shows exactly the mechanism this predicts:
bluealsa's own AVRCP volume updates during the captured slider drag
landed **as little as ~35ms apart** (`16:19:31.751` through
`16:19:31.787`, six updates inside half a second) - well under the old
0.75s window. Every successful mirror re-armed the window before the
next genuine update could get through, so a fast enough chain of updates
could silence itself indefinitely. Explains both symptoms at once:
**zero** `"bluetooth -> hardware"` mirror log lines appear anywhere in
this session's log despite a full, active slider drag from AVRCP 61 to
127 while Bluetooth was confirmed active the whole time, and a drag
toward maximum landing short of it (whichever mirror happened to slip
through last, not the true maximum) explains the "smaller than
Spotify/LMS" report.

**Fixed: removed the echo-window mechanism from `DummyMixerBridge`
entirely** (constructor, `_within_echo_window`, and the arm-on-write
call) - it was pure liability, no benefit. `raw == last_raw` already
dedupes the one legitimate case an echo window would have covered
(multiple `alsactl monitor` lines reporting the same underlying value,
e.g. one per stereo channel).

**Verified live, directly:** wrote five values to `hw:gexislmsvol` 150ms
apart and two negative values 200ms apart - all seven mirrored to the
real DAC correctly. Before this fix, that exact cadence (well under the
old 750ms window) would have silenced itself after the first write or
two, matching the mechanism above precisely.

## 3. Bluetooth first-connect still unreliable — narrowed with precise new evidence, not fixed

**Symptom, recurring from Finding 009 §1:** "Bluetooth first time connect
still doesn't work. after a few tries it actually works fine."

**This time there are logs, and they show a real, precisely timed
race**, not just a plausible-but-unconfirmed connection to ADR-0010's
already-open Bluetooth release-ladder item. `bluealsa-aplay` attempts to
open its ALSA playback PCM as soon as BlueZ's A2DP *transport* starts -
confirmed in the log, this fired **~1 second before**
`MediaPlayer1 appeared`, the signal `BluetoothAdapter` uses for
acquisition (a deliberate choice per ADR-0010's "acquisition is profile
connect, not stream start" - not the earliest possible signal). That
second matters: `bluealsa-aplay` can and does try to open the device
*before* our own arbitration has even been told Bluetooth wants it, let
alone released whoever held it. Confirmed directly: `bluealsa-aplay`
logged `"Couldn't open ALSA playback PCM: Device or resource busy"` at
the transport-start signal, retried, and succeeded about a second later
once `MediaPlayer1`'s later arrival triggered our own acquisition and
released Spotify. This particular instance recovered within the same
second via `bluealsa-aplay`'s own retry; a connection serious enough to
need a full phone reconnect is consistent with the same race landing
worse (e.g. the outgoing renderer needing the full ~3s polite-grace
release rather than the usual ~0.1-0.3s), not confirmed this round.

**Not fixed.** Changing the acquisition signal (to something closer to
transport-start, trading ADR-0010's deliberate "not stream start"
choice for faster-but-more-eager acquisition) is a real design
trade-off already touched on in that record's "Rejected alternatives" -
needs George's call, not a unilateral change made here.

## 4. LMS doesn't release to Spotify unless paused — reproduced, narrowed, still open

**Symptom:** "Lms doesn't release to Spotify unless paused (didn't test
with Bluetooth)."

Same family as Finding 009 §4/5 - reproduced again this round, confirming
it's not a one-off. **This session's log narrows the shape**: the
reclaim happened exactly **once** in this session's Spotify
acquisition, not as a sustained, repeated fight - LMS reclaimed the
device once, Spotify then struggled for about a minute to get it back
(the same resource-busy retry pattern already documented), but once it
succeeded again it held the device cleanly for over a minute with no
further reclaim, until an unrelated Bluetooth connection intentionally
took over. This shifts the likely mechanism from "LMS server keeps
sustained-reasserting play" toward "LMS server sends one delayed,
late-arriving play notification shortly after being paused" - which our
code, correctly by its own contract, can't distinguish from a genuine
fresh acquisition, since both look identical from inside a debounce
window regardless of how that window is sized.

**Not fixed** - same reasoning as Finding 009: no LMS-server-side
visibility from `gexis`, and widening the debounce further trades a
rare false takeover for latency on every genuine one, without a way to
confirm it would even help.

---

## Not established

- Whether `hardware_raw_to_spotify_fraction`'s live behaviour matches
  the unit-tested/hand-computed math against a real phone-driven volume
  change (§1) - not yet exercised live, no Spotify client reachable from
  this session.
- The mechanism causing LMS server to send a delayed play notification
  after being paused (§4) - narrowed from "sustained" to "single delayed
  event" this round, but the cause itself is still not established.
- Whether swapping Bluetooth's acquisition signal to something closer to
  A2DP transport-start would fix §3 without reintroducing the problems
  ADR-0010's original "not stream start" choice was made to avoid - not
  evaluated, a decision for George, not investigated further this round.
