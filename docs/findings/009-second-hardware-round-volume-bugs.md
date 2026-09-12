# Finding 009 — Second hardware round: three confirmed volume bugs fixed, two issues narrowed but still open

**Date:** 2026-09-08
**System:** `gexis` — live hardware, patched in place via SSH per George's
"fix live, verify, then rebuild" preference, same as Finding 008. Logs
pulled from `journalctl -b` covering George's own test session
(13:43-15:26), plus live reproduction/verification after each fix.
**Scope:** George ran the image built after Finding 008's fixes (the
release-ladder correction, LMS debounce, and B2's dummy-control volume
isolation) and reported five symptoms. Three have confirmed root causes,
fixed and verified live on hardware. Two are narrowed with new evidence
but not fixed - reported honestly as still open rather than guessed at.

---

## 1. Spotify volume "finicky" — FIXED, confirmed from the log

**Symptom:** volume felt behind the phone's own display, grew with a
delay, was sometimes absent, and once was observed inverted (phone
showed the level dropping while the speaker got louder). Stabilised
after LMS was used.

**Root cause, traced directly from `journalctl` timestamps.**
`restore_volume()` (`__main__.py`) wrote the remembered volume straight
to the real DAC via `set_raw()` on every acquisition - bypassing
`VolumeBridge`'s echo window entirely. That write still shows up on
`alsactl monitor` like any other change, so `VolumeBridge.run()`'s loop
read it as a *genuine external change* and echoed it straight back out
to go-librespot via `_spotify.set_volume()`. Live evidence: on the very
first Spotify acquisition in the log, `restore_volume` wrote 60/240 at
`15:11:59.737`; 159ms later `_on_spotify_volume` independently wrote
240/240 (go-librespot's own fresh-connect self-report); 3ms after that,
`VolumeBridge`'s monitor loop reported "hardware -> spotify (60/240)" -
the restore's own write, misread as external, sent back to spotify and
racing its own legitimate report. Two writers, no ordering guarantee,
racing on every single acquisition.

**Fixed:** added `VolumeBridge.write_hardware(raw)` - arms the echo
window, then writes. `restore_volume` and the unmanaged-renderer floor
bump (`__main__.py`) now go through it instead of calling `set_raw()`
directly; `_on_spotify_volume` also refactored onto the same method for
consistency. `main()` reordered so `volume_bridge` exists before
`restore_volume`/`Supervisor` are constructed.

**Verified:** unit test
`test_write_hardware_arms_the_echo_window` (`test_volume.py`). Not
independently re-run against a live Spotify session this round (no
phone reachable from this SSH session) - the mechanism is the same one
`_on_spotify_volume` already relied on and is unit-tested; live
confirmation is George's next test.

## 2. LMS volume curve — FIXED, confirmed on hardware directly

**Symptom:** "below 75% it's completely silent."

**Root cause, measured empirically, not inferred.** Set LMS's volume to
0/25/50/75/100% via its own RPC and read the resulting dummy-control raw
value after each: 0%→-50 (the dummy's own floor), 25%→-23, 50%→18,
75%→59, 100%→100 (the dummy's ceiling). **Squeezelite derives its own
percent-to-dB curve from the declared TLV range of whatever control it's
pointed at** - against the dummy (-45dB total span) this produces a
gentler curve than it would ever compute against the real DAC directly
(-120dB span, ADR-0018). `dummy_raw_to_hardware_raw()`'s original
formula rescaled *by fractional position* between the two ranges,
which re-stretched that gentle curve back out across the DAC's full
120dB - recreating, on the real hardware, exactly the "everything
audible crammed into the last quarter" compression a wide-range
control is notorious for. This was never a B2 regression to reproduce
faithfully; the dummy's narrower declared range was accidentally
producing a *better* curve than direct-DAC ever had, and the rescaling
was throwing that away.

**Fixed:** `dummy_raw_to_hardware_raw()` now does a direct dB copy (no
rescaling), clamped to the DAC's range. Full reasoning in the
function's own docstring.

**Verified, live, before/after:**

| LMS % | Dummy raw | Old formula (hw dB) | New formula (hw dB, live-measured) |
|---|---|---|---|
| 0 | -50 | -120.0 (mute) | **-45.00** |
| 25 | -23 | -98.4 | **-37.00** |
| 50 | 18 | -65.6 | **-24.50** |
| 75 | 59 | -32.8 | **-12.50** |
| 100 | 100 | 0.0 | 0.00 |

The "new formula" column is a live `amixer -D output sget DAC` reading
after each RPC call, not computed - matches the function's own math
exactly. 75% now sits at -12.5dB, clearly audible; even 0% no longer
reaches for true mute (see the dummy control's own floor above), which
is accepted - silence is what pause/mute are for, not the bottom of a
renderer's own slider.

## 3. Negative dummy readings were silently mis-parsed — found while verifying #2, FIXED

**Not one of George's five reported symptoms directly, but found while
re-testing #2 and serious enough to record on its own.** The dummy
controls' range is -50..100 (unlike the DAC's 0..240), and
`_VALUE_RE`'s `\d+` doesn't match a leading `-` - every negative
reading parsed as its own absolute value ("-50" read as `50`). Silent,
not a crash: `re.search` still matched, just the wrong number. Confirmed
live: testing the fixed curve (finding #2) initially produced *no*
mirror log line at all for 0%, 25%, or a manual 30% test, while 50/75/100%
worked - exactly the pattern a sign-dropping bug produces, since a
mis-parsed negative reading can coincidentally equal an unrelated real
positive reading from earlier or later in the session and get deduped
against it (`raw == last_raw`), silently swallowing the update. Affected
roughly the bottom third of LMS/Bluetooth's own volume range - invisible
on the real DAC's own reads (`VolumeBridge`), which never goes negative,
so this was specific to `DummyMixerBridge`.

**Fixed:** `_VALUE_RE` changed to `-?\d+`. Unit tests added
(`TestGetRawNegativeValues`) covering both a live-captured negative
reading and a positive one, mocking `asyncio.create_subprocess_exec`
directly rather than a real subprocess.

**Verified, live:** re-ran finding #2's curve test after this fix; all
five percentages (0/25/50/75/100%) now produce a mirror log line and the
correct hardware value, matching the table above exactly.

## 4 & 5. LMS repeatedly reclaims the device; first seconds of a takeover are silent — narrowed, still open

**Symptoms, George's words:** "Spotify cannot takeover lms if [L]ms is
not paused... maybe it's better to pause [L]ms and let -C1 work" and
"when lms takes over the first seconds are silent."

**This is the same family already flagged as unresolved in Finding 008
§2 / ADR-0010's 2026-09-08 amendment** - LMS's CometD stream reporting
`mode: play` in a way that repeatedly reclaims the device from whoever
just took over. The 0.4s debounce added after Finding 008 only ever
covered a *sub-second* bounce; this round's log shows the pattern
persisting far longer - Spotify failing to open the device
(`ALSA error at snd_pcm_open: Device or resource busy`) repeatedly
across **over a minute** after a single LMS reclaim, eventually giving
up and transferring playback back to the phone.

**New this round: squeezelite itself is ruled out empirically, not by
inference.** Paused LMS via RPC, then held the ALSA device open with an
unrelated `aplay` process for 12 seconds while watching
`journalctl -u squeezelite -f` - zero open attempts logged. Squeezelite
does not retry spontaneously while genuinely paused. This means the
repeated `mode: play` genuinely originates from LMS *server*, sustained
well past any reasonable debounce window each time, not a client-side
artefact - and George's own suggested framing ("pause LMS... rather than
killing it") already matches what the code does (`LmsAdapter.release()`
sends `pause`, confirmed fast and successful in every instance in this
session's log - never once escalated to a kill). The mechanism causing
LMS server to keep re-sending play is not established: no sync group, no
repeat/random-mix setting active in LMS's own status, nothing in
`gexis-core`'s code sends LMS a play command.

**Not fixed this round.** No further code change was made here - the
evidence available from `gexis`'s own logs and live testing has been
exhausted; making further progress needs either LMS server's own logs
(a different machine, `192.168.178.188`, out of reach from `gexis`) or
context only George has (another LMS client left open during testing, a
sync group, anything else that could be issuing play commands
independently).

## 1 (numbered per George's report). LMS→Bluetooth takeover failed once, then worked

**Not independently investigated this round** - a single occurrence, no
logs were captured pointing at a specific cause at the time. Noted in
ADR-0010's existing "Bluetooth's release ladder doesn't actually release
the device" open item as a plausible match (stale state from a previous
session colliding with a fresh connect attempt), not as a new, separate
defect. Revisit together if it recurs with logs available.

---

## Not established

- The mechanism causing LMS server to repeatedly re-send `mode: play`
  (§4/§5) - narrowed to "not squeezelite, not our own code," nothing
  further.
- Whether §1 (Bluetooth first-time takeover failure) shares a cause with
  ADR-0010's already-open Bluetooth release-ladder item, or is unrelated.
- Full end-to-end reconfirmation of the Spotify volume fix (§1 above)
  against a real phone session - the mechanism is verified by unit test
  and by the same pattern already relied on for Spotify's own live
  reporting, but not independently re-run live this round.
