# ADR-0010 — Arbitration: base slot, connection acquisition, uniform disconnect

**Status:** Accepted
**Date:** 2026-09-04
**Amended:** 2026-09-04 — the silence rule was restated. See "Rules" below.
**Amended:** 2026-09-08 — two more hardware-found defects in the release
ladder and LMS's own acquisition detection, both fixed. See "Implementation
note" below.
**Amended:** 2026-09-11 — Spotify's own acquisition retries itself once the
outgoing renderer's release is confirmed (Finding 014). See "Open" below.
**Amended:** 2026-09-11 (same day, third amendment) — squeezelite's kill
escalation no longer relies on systemd's automatic restart at all (Finding
013 §1's recurrence). See the Implementation note's final entry.
**Reverted:** 2026-09-11 (same day, fourth amendment) — both of the above
caused worse live regressions than the problems they fixed. Both back to
their pre-2026-09-11 behaviour. See "Open" and the Implementation note's
own final entries, and the standalone Phase 2c issues overview for the
full picture.
**Amended:** 2026-09-11 (same day, fifth amendment) — the polite rung's
grace period was a blind sleep, not a poll, so "freed within polite grace"
was measuring the sleep, not the renderer (Finding 016). Fixed to poll.
See the Implementation note's final entry.
**PARTLY SUPERSEDED:** 2026-09-12 by
[ADR-0027](0027-lms-power-as-arbitration-mechanism.md). **Read that first
for anything about LMS's acquisition, LMS's release, the base slot, or
power state.** Four things in this record are no longer true: the base
slot (LMS is no longer permanently the base, and "no renderer holds the
device" is now a normal state), LMS's acquisition row (powering the player
*on* is the acquisition, not play), LMS's release row (pause *then*
`power 0`, recording the transport state to restore on return), and the
"LMS power state" section below (power is now precisely the mechanism it
says it is not). Everything else here stands unchanged — the no-stack
rule, the accountability rule, the rejected alternatives, and the
non-LMS release table.
**Answers:** ADR-0004 (one active renderer — semantics were left open)

## Context

One renderer plays at a time. No dmix. The question was what "one at a time"
means in practice: how a renderer takes the device, what happens to the one it
takes it from, and what happens when it lets go.

This model went through four revisions during design. The rejected versions are
recorded below because they will look reasonable again later and the reasons
they were dropped will not be obvious.

## Decision

### Slot model

> **Superseded in part by [ADR-0027](0027-lms-power-as-arbitration-mechanism.md)
> (2026-09-12).** The base slot is gone: LMS is no longer permanently current,
> and "no renderer holds the device" is a normal state. The *not a stack, no
> history* rule below survives intact.

**Base slot + active slot. Not a stack. No history.**

- **Base slot** is permanently LMS. Squeezelite's connection to the server is
  structural, not a user session.
- **Active slot** holds at most one other renderer.
- Release empties the active slot; the base becomes current. Nothing is
  restored, because nothing was stored.

### Acquisition — on connection

Connection is a deliberate user act, so the user owns the consequence. Connect
events are also D-Bus signals and API state changes, which are more reliable
than hooking stream starts.

Each adapter declares its acquisition events:

> **LMS's row superseded by [ADR-0027](0027-lms-power-as-arbitration-mechanism.md)
> (2026-09-12):** powering the player *on* is the acquisition. A connect-like
> event does exist after all — it just isn't the TCP connection. The other rows
> are unchanged.

| Renderer | Acquisition |
|---|---|
| LMS | explicit play or resume — no connect event exists, it is always connected |
| Spotify Connect | device selected in the app |
| Bluetooth | A2DP profile connect |
| Qobuz Connect | device selected in the app |

### Release — disconnect, uniformly

**Takeover disconnects the outgoing renderer. LMS is the only exception and
pauses instead, because it is the base.**

> **LMS's row superseded by [ADR-0027](0027-lms-power-as-arbitration-mechanism.md)
> (2026-09-12):** record the transport state, `pause`, then `power 0` — which
> frees the device in 0.06-0.11s instead of 1.44s. The player stays deactivated
> until the user activates it. The other rows are unchanged.

| Renderer | On losing the device |
|---|---|
| LMS | pause, stay connected |
| Bluetooth | disconnect |
| Spotify Connect | disconnect |
| Qobuz Connect | disconnect |

### Rules

- **No auto-resume.** Release never starts playback. Release of the active slot
  leaves LMS current but not playing, which means the idle screen.
- **Takeover acts through the outgoing renderer's control channel.** Blocking
  the audio path is not sufficient — the source would still show "playing" into
  a silent room. Adapters must disconnect or pause on demand and report success
  or failure.
- **Never show a state the user cannot account for.** This is the rule that
  matters, and it is broader than the wording it replaces.

  The failure it exists to prevent is specific: the system believes it is
  playing, the room is silent, and the user has no way to understand why.
  Handoff is therefore a displayed state, and a renderer must not lose the
  device without its source being told.

  It is **not** a prohibition on silence. Several legitimate states are silent
  while playing, and all of them pass because the user caused them, they are
  displayed, and they are reversible by the same action:

  - **Mute** (ADR-0018) — user-initiated, indicated, one action to undo
  - **Fixed output into a powered-down amplifier** — nothing we can detect, and
    nothing the user needs told
  - **Volume at minimum** — self-evident from the control

  The earlier wording — "never show playing while silent" — would have required
  an exception for each of these, and the list would keep growing. The rule is
  about accountability, not about silence.

### LMS power state

> **REVERSED by [ADR-0027](0027-lms-power-as-arbitration-mechanism.md)
> (2026-09-12).** Power is now exactly the mechanism this section says it is
> not: powering on is LMS's acquisition, and pause-then-power-off is its
> release. Kept here unedited because the reasoning below is what a later
> reader will otherwise re-derive — it was sound given what was known, and what
> changed is the evidence (power-off frees the ALSA device in 0.06s against a
> commanded pause's 1.44s, which is the difference between winning and losing
> the race against go-librespot's own ALSA open), not the logic.

Power on/off in the LMS interface plays no role in arbitration. A powered-off
player is one that will not play; it neither acquires nor releases. If someone
presses play on a powered-off player, LMS powers it on and starts — still play,
still acquisition, no special case.

Our UI shows nothing special for a player powered off in LMS. It is not a state
a person standing in front of the device can act on. Power state matters for
multiroom sync groups, which is LMS's concern.

## Rejected alternatives

### Stack ordered by connection time

Considered so that releasing Bluetooth would return to a still-connected
Spotify rather than to LMS.

Rejected because **stack order is invisible state.** The user cannot see it, so
cannot predict it. A Spotify session connected an hour ago and forgotten should
not win the device back because Bluetooth dropped. The slot model always returns
to one known place.

### Acquisition on stream start rather than connection

Rejected on the grounds that connection is the deliberate act and stream-start
detection is mechanically fiddlier.

Accepted cost: A2DP connect does not open the PCM, so a phone can connect and
send nothing. **This makes a UI requirement non-optional:** the screen must say
"Bluetooth connected — waiting for audio", not show an empty now-playing.

### Pausing Bluetooth via AVRCP instead of disconnecting

Designed in full and then rejected. The intent was to avoid tearing down the
A2DP profile link, since on some phones an unexpected disconnect bounces audio
to the phone's own speaker.

It fails because **no signal available to us distinguishes deliberate playback
from incidental audio.** If a paused-but-connected phone reacquires on stream
start, then a notification chirp, an autoplaying video in a feed, or a
navigation prompt all count as acquisition. Music stops because someone scrolled
past a video. That is routine, not an edge case.

Three fixes were examined and none works:

- **Duration threshold** — delays every legitimate start and does not help with
  a long autoplaying video.
- **Signal level** — notification sounds are often loud. No separation.
- **App identity** — A2DP does not carry it. AVRCP session state does not
  reliably reflect where audio is going: a phone that has handed Spotify
  playback to our Connect renderer may still report "playing", because Spotify
  *is* playing, just elsewhere. Treating that as acquisition ping-pongs the
  device.

The speaker-bounce objection is largely addressed by pausing before
disconnecting, so it does not outweigh the notification problem.

## Consequences

- The supervisor is simple: it receives "renderer X wants the device" and
  applies one policy. Per-renderer weirdness lives in adapters.
- Disconnect is self-explaining. The phone shows the device gone rather than
  showing "playing" into silence. No invisible state anywhere.
- **Cost:** Bluetooth reacquisition requires reconnecting from the phone. This
  is mitigated in the UI, not the audio layer — the idle and now-playing screens
  list recently-connected devices and can initiate an inbound connection, which
  BlueZ supports for trusted devices. **Unverified:** how reliably a phone that
  has moved on accepts it.

## Implementation note

Squeezelite holds the ALSA device open by default. `-C <seconds>` makes it close
after idle, which is part of how release is implemented, not a tuning option.

**Amended, 2026-09-06, measured on `gexis`:** `-C` alone is not fast
enough for a takeover. A commanded LMS pause does not make squeezelite
release the device any faster than `-C`'s own idle timer — measured
~8.5s from an LMS CLI pause to the ALSA device actually freeing, against
`-C 10`. That is well past what a user tolerates as a takeover gap.
Contrast go-librespot, which frees the device in under 100ms via its own
`/player/stop`. One shared release mechanism cannot serve both
renderers. **Decision (George):** the supervisor does not wait out `-C`
during a takeover — it sends the LMS pause as a courtesy (so LMS's own
state reflects "paused," not "disconnected," consistent with this
record's release table) and then drives squeezelite's release actively,
with no polite-grace wait (`LmsAdapter.release_ladder`,
`core/src/gexis_core/adapters/lms.py`). `-C 10` still governs the
*non-arbitration* idle case (LMS stops on its own, nothing else wants
the device) — only the takeover path bypasses it.

**Amended again, 2026-09-07:** the active step is `SIGKILL`, not
`SIGTERM` as first implemented. squeezelite exits *cleanly* on
`SIGTERM` (systemd sees `Result=success`), so `Restart=on-failure` never
fired and squeezelite did not come back after a takeover — found on
hardware. `LmsAdapter.signal_stop` now sends `SIGKILL` regardless of
which ladder rung called it; see the "Open" section's sync-group item
below for the three options weighed and why. Release timing is
unaffected (~100ms measured either way — SIGKILL has no clean-shutdown
handler to run, if anything it should be faster, not slower).

**Reverted, 2026-09-08 — the active-kill approach itself was the wrong
fix.** Measured on hardware: `-C 1` releases the device in ~700ms
against a commanded pause, with no audible clicks, pops or dropouts
across track boundaries or a deliberate 2-3s pause-then-resume (the
case that actually forces a close and reopen). 700ms is a plausible
handoff gap. This removes the reason to kill squeezelite at all —
`squeezelite.service` now runs `-C 1`, and `LmsAdapter` has no
`release_ladder` override: it uses the supervisor's plain default ladder
timing like every other adapter. This resolves the restart defect and
the sync-group loss below in the ordinary case, without needing either
of the two prior amendments' timing machinery. Scope of the `-C 1`
measurement: single timing run, 100ms poll granularity with `sudo
fuser` latency in the loop; squeezelite's own help text documents `-C`
in whole seconds, sub-second values are otherwise untested; the
listening test for artefacts was subjective, not instrumented. `-C` is
squeezelite-only — it says nothing about Bluetooth's own release
mechanism, which is a separate, still-open

**Correction, same day, after this reverted too far:** `signal_stop`
was also reverted to respect the ladder's `force` parameter normally,
on the reasoning that escalation would now be rare enough not to
matter. Wrong — reproduced live within hours: a real takeover needed
the full ladder (still busy after the 3s polite grace, `SIGTERM` at
21:20:45, still busy, `SIGKILL` at 21:20:48), squeezelite exited via
the `SIGTERM` (clean, exit 0), and because that exit is clean,
`Restart=on-failure` never fired — the identical defect, reproduced
from the ladder's own genuine escalation rather than a contrived one.
`-C 1`'s timing fix and `signal_stop`'s signal choice are **independent
decisions**: the first makes escalation rare, the second determines
what happens the rare time it's still needed. `signal_stop` now ignores
`force` again and always sends `SIGKILL` for this renderer — SIGTERM
is not "less aggressive," it is simply the wrong signal for squeezelite
regardless of how often it's reached, since it never makes
`Restart=on-failure` fire.
problem (see "Open," below).

**Amended, 2026-09-08 — the release ladder's own busy check was
misattributing "still held" and driving false escalation.**
`device_busy()` asked "is anyone holding the PCM", a global check. But
`Supervisor.acquire()` marks the incoming renderer active and restores
its volume *before* releasing the outgoing one — and the incoming
renderer isn't driven by our own code (LMS tells squeezelite to play
independently of `acquire()`), so it can legitimately grab the device
while the outgoing renderer's ladder is still running its checks. At
that point the global check reports "busy" regardless of whether the
outgoing renderer ever let go. Reproduced live: go-librespot exited
cleanly on its own `/player/stop` at 07:36:25 ("Deactivated
successfully" in the journal), but the ladder logged "still holds the
device after SIGTERM" at the same second and "STILL holds the device
after SIGKILL" three seconds later — both false, against a process
already gone. Combined with go-librespot's own SIGTERM-is-a-clean-exit
behaviour (same shape as squeezelite's already-documented defect above),
this escalation left go-librespot dead with nothing to restart it -
reported as "Spotify Connect died and didn't restart."

Fixed two ways:

1. **The busy check is now renderer-specific.** `alsa.device_held_by(unit)`
   checks whether *that unit's own PID* is among the PCM's holders (via
   `fuser` + `systemctl show ... MainPID`), not whether the holder list
   is merely non-empty. `Supervisor._busy()` now takes the renderer_id
   being checked; `device_busy` (kept, unchanged) remains available for
   anything that genuinely wants "is anyone holding it at all."
2. **`SpotifyAdapter.signal_stop` now always sends SIGKILL**, mirroring
   `LmsAdapter`'s existing fix for the identical failure shape:
   go-librespot exits cleanly (exit 0) on SIGTERM, which
   `Restart=on-failure` never treats as a failure. Fix (1) makes
   escalation rare again (a correctly-attributed busy check means the
   ladder stops at "polite" almost every time, matching go-librespot's
   own documented <100ms release via `/player/stop`) - fix (2) is the
   same defence-in-depth this ADR already applies to LMS, for the rare
   case escalation is still reached.

Unit-tested: a new regression test
(`test_release_not_confused_by_incoming_renderer_already_holding_device`,
`core/tests/test_arbitration.py`) reproduces the exact race - the
outgoing renderer's release frees the device *to* the incoming renderer
(not to nobody), and the ladder must read that as released, not busy.

**Amended, 2026-09-11 - the polite rung's grace period was a blind sleep,
not a poll (Finding 016).** `_release_with_ladder` checked `_busy()` once
before `asyncio.sleep(ladder.polite_grace)` and once after, with nothing
in between - so the `"freed within polite grace (%.1fs)"` log line was
measuring the 3.0s sleep itself, not how long the renderer actually took
to release. Confirmed directly: seven consecutive hand-driven LMS releases
on the current build (`-C 1` shipping) logged 3.1-3.2s six times running,
against squeezelite's own ~700ms passive-release measurement two amendments
above - the two numbers should not have been that far apart. This mattered
beyond the misleading log line: every LMS handoff was landing at 3.1-3.2s
against the ladder's 3.0s `polite_grace` ceiling, effectively no margin,
which is fuel for a restart storm the moment anything is marginally
slower (escalation still always sends `SIGKILL` per the amendment above,
which still fires `Restart=on-failure`). It also means Finding 015's
Spotify→LMS median (4170.9ms) almost certainly contains most of this sleep
rather than measuring the renderer.

**Fixed:** the polite rung now polls `_busy()` every `POLITE_POLL_INTERVAL`
(0.1s, `arbitration.py`) up to the same `polite_grace` ceiling, returning
as soon as the device reports free. Ceiling, escalation semantics, and the
SIGTERM/SIGKILL rungs are unchanged - this is the same ladder checked more
than twice, not a redesign. Shared ladder code, so all three renderers get
it; Spotify and Bluetooth mostly resolve via the pre-sleep check already
and were largely unaffected in practice, but get the same benefit the rare
time they do need the grace period. Unit-tested
(`test_polite_grace_polls_instead_of_sleeping_blind`, records
`asyncio.sleep` calls rather than trusting wall-clock timing, matching this
file's own established pattern) - **not yet hardware-verified.** Expected
effect: normal LMS handoff drops from ~3.2s to ~0.7s. Full detail,
including what re-verification this needs before it goes into a rebuild,
in Finding 016.

**Amended, 2026-09-08 — LMS's own mode-tracking fires spurious
acquisitions, unrelated to anything the user did.** Separate from the
above: even with the busy-check fixed, Spotify kept getting bumped back
to LMS moments after a genuine takeover. Traced to a real, repeating
pattern in the logs - every occurrence of squeezelite's own retried
`alsa_open` against a device another renderer legitimately held was
followed, within one second, by LMS's CometD stream reporting a fresh
`mode: play`. Confirmed this is not a stale/reconnect artefact (the
subscription's `last_mode` tracking never reconnected in the affected
window) - LMS's server-side mode genuinely bounces while paused-for-
arbitration (connected, not powered off - this record's own release
table), not just while genuinely idle. `LmsAdapter._watch()` now
debounces: on seeing `mode: play`, it waits ~0.4s and re-confirms via a
fresh RPC status query before calling `on_acquire()`. A bounce doesn't
survive the wait; a real "user pressed play" does. Costs ~0.4s of extra
latency on every genuine LMS acquisition - not measured against the
takeover-gap criteria (Phase 2c, below), worth checking against those
once they're run. Root mechanism inside squeezelite/LMS not fully
traced - the fix targets the observed pattern, not a confirmed root
cause; flagged as such, not asserted with more confidence than the
evidence supports.

**Amended again, 2026-09-08 (later the same day) - the debounce above
only ever covered the *sub-second* case, and George's next hardware
round showed the same symptom family persisting well beyond it: Spotify
struggling to open the device for over a minute after a genuine LMS
reclaim, and a separate report that Spotify "cannot take over LMS unless
LMS is paused" - both consistent with `mode: play` being reported by LMS
*repeatedly, sustained well past 0.4s each time*, not a momentary bounce.
**Squeezelite itself is now ruled out as the source, empirically, not by
inference:** paused LMS via RPC, held the ALSA device open with an
unrelated `aplay` process for 12s, and squeezelite logged zero open
attempts throughout - it does not retry spontaneously while genuinely
paused. The repeated `mode: play` has to be LMS server itself re-sending
play to squeezelite, for a reason not established - no sync group, no
random-mix/repeat setting active, nothing in `gexis-core`'s own code
sends LMS a play command. **Still open** - the 0.4s debounce is a partial
mitigation for the fast case, not a fix for this one, and nothing further
was changed here this round. Needs either LMS server-side logs (a
different machine, out of reach from `gexis`) or George's own account of
what else might be issuing play commands during a test (another LMS
client left open, a sync group, anything) to make progress. Full detail
in Finding 009.

**Refined, 2026-09-08 (third session) - George reproduced it again
("Lms doesn't release to Spotify unless paused"), and this session's log
narrows the shape further, not just confirms it.** In the captured
session, the reclaim happened **once** per Spotify acquisition, not as a
sustained fight - LMS reclaimed the device ~50s into a Spotify session,
Spotify then struggled to get it back for about a minute (same
resource-busy pattern as before), but once it succeeded a second time it
held the device cleanly for over a minute afterward with no further
reclaim, until a Bluetooth connection intentionally interrupted it. That
changes the likely shape of the root cause from "LMS server keeps
re-asserting play indefinitely" to "LMS server sends one delayed,
late-arriving play notification shortly after being paused, which our
code correctly treats as a fresh acquisition since nothing distinguishes
it from a genuine one." Still not fixed - the 0.4s debounce can't tell
a slow, single delayed echo of the *previous* pause from a genuinely new
user action, since both look identical from a sub-second window, and
widening the window further only trades a real, if rare, false takeover
for added latency on every genuine one. Full detail in Finding 010.

**Amended again, 2026-09-11 (Finding 013 §1's recurrence) - SIGKILL
solved "doesn't come back" but caused a worse, independent problem:
systemd's own automatic `Restart=on-failure` then races squeezelite's
own startup device-open test against whoever just took the device over,
on its own fixed cadence (`RestartSec=2`), completely decoupled from
anything the arbitration ladder itself is doing.** For as long as the
device stays busy, squeezelite keeps failing that test and systemd keeps
restarting it - measured exhausting even the raised `StartLimitBurst`
(24 restarts against a limit of 20), under ordinary paced measurement
rounds this time, not adversarial racing (see Finding 013 §1's own
addendum for the full evidence). **George's decision: fix the race, not
raise the limit again.** `LmsAdapter.signal_stop` now calls `stop_unit`
(`systemctl stop`, not a raw kill signal) - systemd does not
automatically restart a unit that was asked to stop, regardless of how
the process actually exits getting there, so nothing races in the
background anymore. A new adapter hook, `restart_after_release`
(`adapters/base.py`, default no-op), brings squeezelite back explicitly
instead - called by the supervisor as the very last step of `acquire()`,
after the incoming renderer's own `device_freed()` retry and volume
restore, so the device's ownership has had the best available chance to
settle first. Idempotent (a no-op if squeezelite was never actually
stopped - the ordinary case).

**Residual risk, named rather than assumed away:** if that one explicit
restart also finds the device still busy, squeezelite exits again and
`Restart=on-failure` (still configured, as a safety net for genuine
unrelated crashes) *does* still govern recovery from that fresh failure
- the same class of race, just now requiring both "a kill was needed at
all" (already rare - 15 of 16 rounds this session needed no escalation)
*and* "the explicit restart's own timing also lost the race against the
incoming renderer," rather than firing on every kill as before. Not
proven impossible, only made meaningfully rarer. Unit-tested at the
mechanism level (`stop_unit`/`start_unit` called correctly, in the right
order, on the right adapter) - the actual "does this survive a real busy
race" question is hardware-verification territory, matching this
project's existing convention for adapter network/process code.

**Verified on hardware, same day.** The core guarantee - `systemctl stop`
suppresses automatic restart entirely - confirmed directly: stopped
squeezelite by hand while it held the device, watched `systemctl
is-active` stay `inactive` for 9 seconds (well past what `RestartSec=2`
would ever need if `Restart=on-failure` were going to fire), then brought
it back with a plain `systemctl start`. That same manual `start`, issued
while Spotify still held the device, *did* trigger `Restart=on-failure`
and climb `NRestarts` - the exact residual risk this amendment names, not
just a mechanism proven in the abstract. Then, through the real
integrated path (`Supervisor.acquire()`, not a manual test): two full
batches, 15 consecutive LMS-to-Spotify rounds and 20 consecutive
Spotify-to-LMS rounds, **zero restart-storm recurrences, all units
healthy throughout** (`NRestarts` unchanged across both batches - the
kill-escalation path wasn't even needed in either one, which is itself
consistent with escalation being rare, not with the fix being unexercised
in anger by the harness). Criterion 8's same-rate LMS↔Spotify distribution
collected cleanly on both legs as a result - see Finding 015.

**Reverted, same day (second session) - the named residual risk
recurred under real, sustained use, not scripted rounds.** George
continued using the system normally afterward (LMS/Spotify switching,
Bluetooth connecting and reconnecting several times) and squeezelite
failed into the identical restart-storm state again about two hours
later - consistent with rapid Bluetooth reconnect churn repeatedly
re-triggering LMS's kill-and-explicit-restart cycle, with the explicit
restart itself losing its own race against a still-busy device often
enough, across enough repetitions, to trip the burst limit regardless.
"Meaningfully rarer" (this amendment's own words) was not the same as
fixed. **Reverted:** `signal_stop` back to raw `kill_unit(force=True)`,
`restart_after_release` removed (back to the inherited no-op) -
`Restart=on-failure` is squeezelite's only path back again, same as
before this amendment. The 35 clean scripted rounds above are real
evidence the mechanism works under *that* load pattern; they are not
evidence it survives *this* one - the gap between the two is exactly
what a future attempt needs to close, not just re-run the same batch
again. Full detail in Finding 013 §1's own follow-up and the standalone
Phase 2c issues overview.

## Open

- **Sync group interaction — deferred, with a known cost, by decision.**
  Squeezelite stays in its LMS group while another renderer holds the
  device, so a group play command becomes an acquisition that
  interrupts. Consistent with the rule, possibly surprising. **Criterion
  3 (Phase 2b) ships without resolving this** — a decision, not an
  oversight; see `docs/DEVELOPMENT.md`.

  **The cost is concrete, not theoretical, as of 2026-09-06.** The LMS
  release mechanism is `SIGTERM` on squeezelite (see the Implementation
  note below), which removes it from LMS entirely rather than merely
  pausing it within its group: it drops out of any sync group it
  belonged to and reappears as a fresh player on restart
  (`Restart=on-failure`). A user who had `gexis` grouped with another
  player, and who then casts Spotify to it, will find the grouping gone
  afterwards with no explanation. Measured on hardware, not inferred.

  **Three options were considered, so a later reader does not re-derive
  them:**
  1. Accept the breakage. **Chosen.**
  2. Capture group membership before the kill and restore it after
     restart, via the LMS CLI.
  3. Lower `-C` enough that pausing frees the device fast enough that
     killing squeezelite is never needed. Untested — nobody has measured
     whether a short `-C` actually behaves fast enough in practice, only
     that the default (`-C 10`) does not.

  **George's decision: stays deferred, option 1, for now.** Not an
  oversight — the cost is accepted, not unknown.

  **Found, then fixed, 2026-09-07: squeezelite did not come back after
  the SIGTERM above at all.** `Restart=on-failure` never fired, because
  squeezelite exits *cleanly* on SIGTERM (`Result=success`,
  `ExecMainStatus=0`), which systemd does not count as a failure. LMS
  was gone from the system until a manual restart or a reboot — a
  player with no players has no sync group to lose, which is what
  briefly superseded this item entirely.

  **Three options were weighed (recorded in HANDOFF.md in full):**
  1. SIGKILL instead of SIGTERM for LMS's escalation — an uncaught
     fatal signal is not clean by systemd's own accounting, so
     `Restart=on-failure` fires normally. Smallest change; same class
     of systemd-exit-status assumption that produced the defect.
  2. The adapter explicitly relaunches squeezelite after confirming
     release, decoupled from `Restart=` semantics entirely.
  3. Lower `-C` enough that pausing alone frees the device, so killing
     is never needed — sidesteps the question rather than answering it.

  **George's decision: option 1.** Option 3 is the architecturally
  cleanest — no kill, no restart question at all — but cannot reach the
  ~100ms release tempo SIGKILL already measured; a `-C` short enough to
  compete was untested and unlikely to get there. `LmsAdapter.
  signal_stop` now ignores the ladder's `force` parameter and always
  sends `SIGKILL` for this renderer specifically (`kill_unit(...,
  force=True)` on both the "SIGTERM" and "SIGKILL" rungs — the second
  call, if ever reached, is a harmless no-op against an already-dead
  process).

  This reopens the sync-group question above rather than mooting it —
  squeezelite returns again, so it has a sync group to lose again.
  That deferral (option 1 there too: accept the breakage) stands as
  recorded.

  **Resolved for real, 2026-09-08: `-C 1` replaced the kill approach
  entirely** (see the Implementation note's own final amendment,
  above). squeezelite is no longer killed during an ordinary takeover
  at all — `SIGTERM`/`SIGKILL` are the ladder's escalation safety net,
  not the primary path — so there is no longer a sync-group loss to
  accept. The deferral above is now moot in the good sense: not
  "accepted cost" but "cost no longer occurs in normal operation."
  Still theoretically reachable if `-C 1` ever fails to free the device
  within the polite grace window and the ladder actually escalates —
  same shape as the original 2026-09-04 note, now genuinely rare rather
  than the routine path it briefly was.
- **Empty base slot — ANSWERED, 2026-09-12, by
  [ADR-0027](0027-lms-power-as-arbitration-mechanism.md)** (was: deferred,
  undefined behaviour, valid if run headless with no LMS). It is no longer an
  edge case to define — with LMS deactivated on every takeover and staying
  deactivated, "no renderer holds the device" is a routine state the system
  must represent.
- **Takeover gap — not deferred, scheduled.** Unmeasured, same-rate and
  cross-rate. This is Phase 2c, criteria 8-10 — active work, not a
  deferral.
- **Bluetooth's release ladder doesn't actually release the device —
  deferred, George's decision, 2026-09-10 (was "open, not deferred"
  until then).** Found on hardware, 2026-09-08: `release()` (`Device1.Disconnect()`), then the full
  ladder — `SIGTERM`, then `SIGKILL` on `bluealsa-aplay.service` — ran
  and the device was **still held after `SIGKILL`** (10.7s). Two
  threads, neither confirmed:
  - `bluealsa-aplay.service`'s stock unit (`bluez-alsa-utils` package)
    sets `Restart=on-failure` with no explicit `RestartSec` — systemd's
    default is 100ms. A killed process could plausibly restart and
    reopen the PCM well before the ladder's own `sigkill_grace` (2s
    default) check runs, which would read as "still held" even though
    what's actually holding it is a *new* process, not survival of the
    old one. Checked the static unit file, not measured live.
  - Separately, and not explained by the above: **`bluealsa-aplay` was
    observed (via `fuser`) holding the PCM open even after its own IO
    worker exits on phone disconnect** — i.e. `Device1.Disconnect()`
    succeeding doesn't reliably free the device either, which is the
    step that's supposed to make killing unnecessary in the first
    place (same shape as squeezelite's fix above: use the renderer's
    own release path, don't rely on process death). If this holds up,
    Bluetooth's real fix looks more like "why doesn't disconnect free
    the PCM" than "how do we kill it more reliably."
  - **Recurred, 2026-09-08, with logs this time - a real, precisely
    evidenced race, not confirmed as the same cause as the item above but
    likely related.** `bluealsa-aplay` attempts to open its ALSA playback
    PCM as soon as BlueZ's A2DP *transport* starts
    (`ba-transport.c:1075: Starting transport`) - a signal that, in the
    captured log, fired a full **~1 second before** `MediaPlayer1
    appeared`, the signal `BluetoothAdapter` uses for acquisition
    (chosen, per that adapter's own docstring, because ADR-0010 wants
    "A2DP profile connect," not stream start - deliberately not the
    earliest possible signal). That second matters: `bluealsa-aplay`'s
    own PCM-open attempt can race ahead of our own release-the-previous-
    renderer logic, which hasn't even been *triggered* yet. Confirmed
    directly in the log: `bluealsa-aplay` logged "Couldn't open ALSA
    playback PCM: Device or resource busy" at the transport-start
    signal, then retried and succeeded ~1s later once `MediaPlayer1`
    triggered our own acquisition and released Spotify. This time the
    retry recovered on its own within the same second; a first-connect
    failure serious enough that a phone has to fully reconnect is
    consistent with the same race landing worse (e.g. the previous
    renderer needing the full ~3s polite-grace release rather than the
    ~0.1-0.3s usually seen), not confirmed.

    **Not fixed** - the acquisition signal (`MediaPlayer1` vs. transport
    start) is the kind of trade-off ADR-0010 already deliberated
    (stream-start detection was explicitly rejected as an acquisition
    trigger for Spotify/Bluetooth generally - see "Rejected
    alternatives" above), so swapping it for Bluetooth specifically needs
    George's call, not a unilateral change. Full detail in Finding 010.

  **The original "still held after SIGKILL" failure (10.7s, 2026-09-08)
  itself was never specifically re-reproduced after the fixes above.**
  Every Bluetooth release measured since (Findings 011/012, several
  sessions) succeeded via polite stop alone, 2.0-3.2s, never escalating
  - plausible that it's now moot (the busy-check fix, Finding 008 §1,
  removed a false-"still held" misattribution that could explain the
  original symptom without a real device-still-open bug at all), but
  that's a plausible explanation, not a confirmed one - the escalation
  path itself hasn't been forced and watched since. **George's decision,
  2026-09-10: defer, same treatment as the sync-group and empty-base-slot
  items above.** Criterion 4 (Phase 2b) ships without a targeted
  re-reproduction of this specific failure mode - a decision, not an
  oversight.

  **George's decision, 2026-09-08: proceed with an earlier acquisition
  signal for Bluetooth.** Not the same trade-off "Rejected alternatives"
  rejected above - that rejection was about detecting actual *stream
  start* (audio flowing). What's added here (Finding 011) is
  `org.bluez.MediaTransport1` appearing at its `.../dev_XX/fdN` object
  path, confirmed against BlueZ's own `doc/media-api.txt` and directly
  in `gexis`'s bluealsa log - the transport *object*, in "idle" or
  "pending" state, created once profile negotiation begins, independent
  of whether audio is flowing. Same "control plane, not stream start"
  shape as `MediaPlayer1`, just earlier in BlueZ's own sequence -
  `BluetoothAdapter` now acquires on whichever of the two fires first,
  the other a harmless idempotent re-fire (`Supervisor.acquire()` is a
  no-op for an already-current renderer). **Deployed live on `gexis`,
  not yet verified against a real connect/disconnect cycle** - the next
  test session should confirm before this is folded into an image
  build.

- **Spotify's own acquisition signal could never fire while the device
  was busy - a real deadlock, not a race. Found with evidence, fixed,
  not yet live-verified.** Finding 010 §4 narrowed "LMS doesn't release
  to Spotify" to a single delayed LMS reclaim with no server-side
  visibility to explain it. This round's log (Finding 011) explains the
  *downstream* half precisely, from upstream source, not guessed:
  `SpotifyAdapter` acquires on go-librespot's `"active"` WS event, whose
  docstring assumed it "fires when a device is selected in the app."
  Reading devgianlu/go-librespot's own `daemon/controls.go` shows that's
  wrong - `ApiEventTypeActive` is only emitted *after*
  `loadCurrentTrackOrSkip()` returns successfully, which requires
  opening the ALSA device first. If that open fails, the function
  returns an error and `"active"` is never emitted at all. Confirmed
  directly against `gexis`'s log: after LMS reclaimed the device,
  go-librespot logged four consecutive `"ALSA error at snd_pcm_open:
  Device or resource busy"` over ~13s trying to resume a transferred
  session, and no `"active"` event fired until 37s after the reclaim -
  by which point the phone had given up and re-initiated the transfer
  from scratch, and the second attempt happened to land in a moment the
  device was free. Not a race with a ~1s window like Bluetooth's - a
  genuine catch-22 that only resolved by chance.

  **Fix: also acquire on go-librespot's `"will_play"` event**, which the
  same source read shows is emitted earlier in the same call chain
  (`loadCurrentTrack`, before any ALSA access), for both the "transfer"
  and "play" command paths. Same "control plane, not stream start" shape
  already established for the other two renderers - not a new kind of
  trade-off, a corrected signal choice. **Deployed live on `gexis`, not
  yet verified against a real LMS-playing -> Spotify-takeover cycle** -
  next test session should confirm.

  **Both confirmed working, 2026-09-10** - George: "Testing on the
  device after the last fixes show clear improvement on all fronts."

  **Sharpened, then fixed, 2026-09-11 (Finding 014) - the race is
  deterministic on a single clean attempt, not just under repeated
  calls.** Attempting criterion 8's LMS-to-Spotify measurement with the
  harness already fixed for Finding 013 §3 (single attempt per round, no
  rapid retry) still produced 0 successes in 4 rounds. Isolated,
  instrumented single-call testing pinned the mechanism precisely:
  go-librespot attempts its ALSA open within about a second of
  `will_play` firing, while LMS's own polite release takes ~3.1s - a lone
  attempt loses that race essentially every time, which directly
  contradicts this record's own 2026-09-10 assumption that acquiring on
  `will_play` would leave the device free by the time go-librespot's
  retry (or the same call, re-entered) lands. A second, distinct
  transfer call 2-3s later reliably succeeded in testing, once the
  original release had actually finished - but a real fix can't depend on
  a second Spotify Web API call, which only the phone/Spotify's backend
  can issue.

  **George's decision: option 2 from Finding 014 - have `SpotifyAdapter`
  retry itself.** `POST /player/resume` is go-librespot's own local HTTP
  API (no Spotify account credentials, unlike the Web API calls only the
  test harness has) - confirmed on `gexis`, three-for-three, reliably
  resuming real playback within a second of the device actually being
  free, and confirmed harmless when called after an attempt that already
  succeeded (status 200, no pause or restart, track position continues
  advancing normally). Implemented as `Adapter.device_freed()`
  (`adapters/base.py`), a new optional hook defaulting to a no-op, which
  `Supervisor.acquire()` calls on the *incoming* renderer's adapter once
  the outgoing renderer's release is confirmed and its volume restored -
  `SpotifyAdapter` is the only override so far. Unit-tested at the
  supervisor call-site level (ordering, and that it fires on the incoming
  adapter only, once) - the actual `/player/resume` HTTP call is
  hardware-verified only, matching this file's own established pattern
  for every other adapter's network-touching code (see
  `adapters/base.py`'s own reasoning for why this wasn't mocked in a unit
  test).

  **Verified against a live `takeover_gap.py` run, same day.** Deployed
  live on `gexis` (hot-patched into the running venv, service restarted -
  no rebuild). LMS-to-Spotify: **5 of 5 real attempts succeeded** (one
  additional round skipped for an unrelated reason - LMS itself didn't
  acquire the PCM within the harness's own precondition window, nothing
  to do with this fix), where the pre-fix baseline was 0 of 4. Gaps
  895.5-1900.2ms (mean 1603.5ms, n=5) - not yet the ≥20-run distribution
  criterion 8 needs, but the deterministic first-attempt failure this
  amendment exists to fix is gone in every attempt observed so far.

  **Reverted, same day (second session) - a real live regression the
  scripted testing above never caught.** After collecting a full ≥20-run
  distribution with this fix live (Finding 015), continued ordinary use
  found that `POST /player/resume` can get go-librespot to resume real
  local ALSA playback without completing whatever step actually emits
  the `"active"` WS event - confirmed directly in `gexis-core`'s own log,
  several `will_play` acquisitions never followed by `device became
  active` for the rest of that Spotify session. Audio played correctly,
  but Spotify's own app showed "gexis disconnected," and a remote "next"
  command routed to the phone instead of `gexis` - exactly the failure
  shape this record's own core rule forbids ("never show a state the
  user cannot account for"), and arguably worse than the race it fixed
  (silence for a bit is at least accountable; playing correctly while the
  controlling app is wrong about it is not). **`SpotifyAdapter.
  device_freed()` reverted to the inherited no-op** - the hook itself and
  `Supervisor.acquire()`'s call site are untouched, only this adapter's
  action was pulled. Mode A's original race (this amendment's own
  opening paragraph) is unresolved again as a result - full detail in
  Finding 014's own follow-up.

- **`acquire()` wrote the incoming renderer's volume to the shared real
  DAC before releasing the outgoing one - a real ordering bug, fixed
  2026-09-10 (Finding 012).** Not a signal-choice trade-off like the two
  above; a straightforward correctness fix. Confirmed directly in
  `gexis`'s log: a Bluetooth->LMS handoff wrote the real DAC to LMS's
  240/240 target at the moment of acquisition, 2.3s before Bluetooth's
  own release ladder actually finished - audible as a loud blip on
  Bluetooth's still-playing audio (George: "for a fraction of a second
  before LMS takes over, the sound gets louder on the song playing on
  bluetooth"). Not Bluetooth-specific - a property of the shared
  physical DAC, applies to any renderer pair; Bluetooth's release ladder
  (2-3s polite-stop grace, measured repeatedly) just makes the gap
  noticeable where LMS's ~0.1s usually isn't. Fixed by releasing the
  outgoing renderer first, restoring the incoming renderer's volume only
  after - the incoming renderer generally can't produce sound yet at
  `acquire()`-time anyway (the device is still held by whoever's being
  released), so this costs nothing. **Confirmed working, 2026-09-10** -
  George tested both this and the SoftVolume fix (docs/decisions/0018)
  live: "both fixes look good."
