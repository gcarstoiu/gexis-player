# Finding 008 — Arbitration release-ladder defects and the dummy-control volume fix

**Date:** 2026-09-08
**System:** `gexis` — live hardware, patched in place via SSH and verified
before being folded into the image build. `gexis-core`, `squeezelite`,
`go-librespot`, `bluealsa-aplay` all running their normal systemd units
throughout; no synthetic harness.
**Scope:** four defects found from a single round of hardware testing
(George: Bluetooth volume audible-changed-by-LMS, Spotify Connect dying
and not restarting, LMS's track starting three times, and — after the
first three fixes — Spotify not sustaining a takeover). All four
diagnosed from live logs, not guessed. Three are fixed and verified live
on `gexis` as described below; the fourth (dummy mixer controls) is
implemented and its mechanism verified live, but a full multi-switch
end-to-end retest was still in progress when this session moved to
rebuilding the image — that retest is **not yet confirmed**, and should
happen on the rebuilt image, not assumed from this finding.

---

## 1. False "still holds the device" escalation (Spotify Connect died)

**Root cause, confirmed from `journalctl` timestamps.**
`Supervisor.acquire()` (`arbitration.py`) marks the incoming renderer
active and restores its volume *before* releasing the outgoing one. The
incoming renderer isn't driven by our own code — LMS tells squeezelite to
play independently of `acquire()` — so it can legitimately grab the ALSA
device while the outgoing renderer's release ladder is still checking
whether it's free. `alsa.device_busy()` asked "is anyone holding the
PCM" — once the incoming renderer holds it, that's `True` forever,
regardless of whether the outgoing renderer ever let go.

Live evidence: go-librespot exited cleanly on its own `/player/stop` at
07:36:25 (`Deactivated successfully`, journal same second), but the
ladder logged `release[spotify]: still holds the device after SIGTERM,
sending SIGKILL` at the same second and `STILL holds the device after
SIGKILL (8.3s)` three seconds later — both false, against a process
already gone. Compounded by a second, independent defect: go-librespot
exits with status 0 on SIGTERM (a clean exit, matching squeezelite's
already-documented ADR-0010 defect), which `Restart=on-failure` never
treats as failure — so once wrongly SIGKILLed (SIGKILL after an
already-dead SIGTERM is a no-op against nothing), go-librespot stayed
dead with nothing to restart it.

**Fixed:**
- `alsa.device_held_by(unit)` — checks whether *that unit's own PID*
  (via `systemctl show <unit> --property=MainPID`) is among `fuser`'s
  holder list for the PCM node, not whether the list is merely
  non-empty. `Supervisor._busy()` now takes the renderer_id being
  checked and calls `device_busy(renderer_id)`, wired in `__main__.py`
  to `alsa.device_held_by(adapters[renderer_id].unit_name)`.
- `SpotifyAdapter.signal_stop` always sends SIGKILL now, mirroring
  `LmsAdapter`'s existing fix for the identical shape.

**Verified:** unit test
`test_release_not_confused_by_incoming_renderer_already_holding_device`
(`core/tests/test_arbitration.py`) reproduces the race directly. Live on
`gexis`: restarted go-librespot (dead from the pre-fix session), ran a
real Spotify → LMS → Spotify sequence; no false "still holds"/"STILL
holds" log lines appeared across ~20 minutes and several switches in
either direction (see raw `journalctl` excerpt kept in this session's
transcript, not reproduced here).

## 2. LMS's mode-tracking fires spurious acquisitions

**Found after fix 1 was live** — Spotify no longer died, but kept getting
bumped back to LMS moments after a genuine takeover, i.e. "shows
connected but doesn't take over."

**Pattern, confirmed from logs, 4/4 occurrences in one session:** every
instance of squeezelite's own retried `alsa_open` (`Device or resource
busy`, logged while another renderer legitimately held the device) was
followed, within one second, by LMS's CometD subscription reporting a
fresh `mode: play`, which `LmsAdapter._watch()` correctly (by its own
narrow contract) treated as a genuine acquisition request. Ruled out a
client-side artefact: the subscription's `last_mode` tracking never
reconnected in the affected windows (only one `lms: subscribed to ...`
line across the whole ~20-minute session), so this is LMS's own
server-side mode genuinely bouncing while paused-for-arbitration
(connected, not powered off — ADR-0010's release table), not a stale
frame replayed after a reconnect.

**Not fully root-caused** — the mechanism inside squeezelite/LMS that
produces this bounce (buffer/retry state, a keep-alive re-assertion, or
something else) was not traced to source. The fix targets the observed,
consistently-correlated pattern, not a confirmed root cause.

**Fixed:** debounce. On seeing `mode: play`, `LmsAdapter._watch()` now
waits ~0.4s and re-confirms via a fresh RPC `status` query before calling
`on_acquire()`. A transient bounce doesn't survive the wait; a genuine
user-initiated play does. Costs ~0.4s of added latency on every real LMS
acquisition — not measured against Phase 2c's takeover-gap criteria, and
should be checked against those once run, since it adds directly to that
number for this one direction.

**Verified, live:** issued a real LMS play command after the fix landed;
`status` reported `mode: play, time: 2.8s` a few seconds later (i.e. the
track was genuinely advancing, not restarting) — consistent with, though
not full confirmation of, George's separately-reported "LMS track
starting three times" clearing up. No dedicated repro of that specific
symptom was run after the fix; it was inferred from the shared mechanism
(both symptoms correlate with the same squeezelite-retry pattern).

## 3. Dummy mixer controls — cross-renderer volume isolation (B2)

Full mechanism and investigation already recorded in this session's
conversation; summarised here for the record with what was additionally
found while implementing it.

**Mechanism:** `snd-dummy` (present on this kernel, no build step)
loaded with `enable=1,1 id=gexislmsvol,gexisbtvol pcm_devs=0,0` — two
independent, named virtual cards, each exposing a standard ALSA
simple-mixer `Master` control with no audio path behind it.
`squeezelite -O hw:gexislmsvol -V Master` and `bluealsa-aplay
--mixer-device=hw:gexisbtvol --mixer-name=Master` point each renderer's
own volume control at its private dummy instead of the real `DAC`.
`gexis-core`'s new `DummyMixerBridge` (`volume.py`) mirrors a dummy
control's value onto the real `DAC`, and only while that control's
renderer is the currently active one.

**Two implementation bugs found and fixed while wiring this up, neither
guessable from documentation, both confirmed by direct command-line
testing on `gexis` before being fixed in code:**

- `alsactl monitor <card>` requires the `hw:` prefix
  (`alsactl monitor hw:gexislmsvol`) — a bare card id
  (`alsactl monitor gexislmsvol`) fails with `Invalid CTL`, despite
  `alsactl(1)`'s own SYNOPSIS listing `<card # or id>` without
  mentioning this. Affected both the pre-existing real-card monitor
  (now correctly scoped to `hw:sndrpihifiberry` — previously
  unscoped/global, which would have double-processed the new dummy
  cards' own events once they existed) and the two new
  `DummyMixerBridge` instances.
- `amixer sget` formats a control's value line differently depending on
  whether the control has distinct playback/capture volumes. The real
  DAC's line (`Front Left: Playback 216 [90%] [-12.00dB]`) includes the
  word "Playback"; a dummy card's `Master` control
  (`Front Left: 30 [53%] [-21.00dB] Capture [off]`) does not. The
  existing parsing regex (`_VALUE_RE`, added for the DAC originally) only
  matched the first form, so `get_raw()` against any dummy control
  silently returned `None` until the regex was widened to
  `Front Left: (?:Playback )?(\d+) \[`.

**Verified, live, both directions:**
- **Mirrors when active.** With LMS the (default) active renderer,
  wrote `50` directly to `hw:gexislmsvol`'s `Master` control; the real
  DAC moved to `160/240` within ~1s, and the log recorded
  `volume: lms -> hardware (dummy 50 -> 160/240)` — matches
  `dummy_raw_to_hardware_raw(50)` computed by hand.
- **Does not mirror when inactive.** Stopped the real `gexis-core`
  daemon, ran an isolated `DummyMixerBridge` instance with
  `get_active_renderer` stubbed to return `"bluetooth"` (not `"lms"`),
  wrote `5` to the same dummy control — the real DAC's value was
  unchanged afterward. (An earlier attempt at this same test, with the
  real daemon still running, produced a misleading result: the real
  daemon's own — correctly gated, genuinely active-LMS — instance
  mirrored the write, which looked like a gating failure until the real
  daemon was stopped and the test re-run in isolation.)
- **Real playback unaffected.** Issued a real LMS play command after all
  of the above; audio played, `status` reported the track's elapsed time
  advancing normally.

**Not yet done:** a full multi-switch end-to-end retest (Spotify ↔ LMS ↔
Bluetooth, checking that raising one renderer's volume never moves what's
audible from another) on the *rebuilt* image. Everything above was
verified against the live-patched running system, which matches what the
rebuild encodes, but the rebuild itself has not yet been tested.

## Not established

- The exact mechanism inside squeezelite/LMS producing the mode bounce
  in §2 — the fix addresses the symptom, confirmed by pattern-matching
  logs, not a traced root cause.
- Whether the ~0.4s LMS acquisition debounce is acceptable against
  Phase 2c's (not yet run) takeover-gap criteria.
- Full multi-switch retest of the dummy-control volume isolation on the
  rebuilt image (see "Not yet done" above).
- Bluetooth's own release ladder ("still held after SIGKILL", ADR-0010's
  "Open" section) — unrelated to and not touched by any of the above;
  still open.
