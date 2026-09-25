# Handoff archive

Dated history moved out of `HANDOFF.md` on 2026-09-14, when that file had
reached 2,800 lines and ~24,000 words — most of it narrative that had already
done its job. `HANDOFF.md` is what the next session reads; this is what it
reads only when it needs to know *why* something ended up the way it did.

**Nothing here was edited.** The blocks below are verbatim, in their original
order, so a `git log -p` trail still matches. What was removed from
`HANDOFF.md` is exactly what appears here — the split was line-counted, not
eyeballed.

**So the links in them do not work, and that is deliberate**
([ADR-0082](decisions/0082-the-archive-keeps-its-dead-links.md), George,
2026-09-25: *"Keep it."*). They were written at the repository root, where
`docs/decisions/0027-…` is the right path; from inside `docs/` it is not. All
74 of them name the record's number in the link text, so the way to follow one
is to look it up by number. `core/tests/test_docs_links.py` skips this file for
that reason and checks every other.

**Where the durable conclusions went instead.** History was moved, not lost,
but the *rules* it produced live elsewhere and are the things to act on:

- `docs/LESSONS.md` — how verification itself has failed here, four instances
- `docs/decisions/` — every decision, with its rejected alternatives
- `docs/findings/` — the measured numbers, each with its scope
- `HANDOFF.md`'s "Things that will bite if forgotten" — the traps
- `image/README.md` — the build environment and its failure modes

If you are reading this to answer "has this been tried before", search here
first and then `docs/findings/`.


## Dated session logs, Phases 2a-2d (2026-09-06 to 2026-09-12)

### Hardware session, 2026-09-06: reflashed with the Phase 2b build

**Baseline carried forward cleanly:** mixer-check success line in the
journal on a real boot, all four units active, `sudo -n true` OK.

**DAC card index also varies across rebuilds of the same image on the
same hardware** — card 2 this time, card 1 on the Phase 0 build.
Finding 005 said index varies *across machines*; this is a stronger
version (same machine, same source, different build) and has been added
to that finding. Doesn't change anything already built — `output` was
already never referencing an index — recorded because it sharpens the
finding, not because it's actionable.

**Defect found at boot: squeezelite couldn't open the device while
go-librespot held it.** `alsa_open:360 playback open error: Device or
resource busy` logged every 5s; `fuser` showed go-librespot (PID 872)
on `/dev/snd/pcmC2D0p`. All four systemd units reported "active"
throughout — `is-active` looked healthy while squeezelite could not
play at all, a real gap in what "active" tells you about this system.
Only happened while LMS had something to play; squeezelite acquires on
demand, not at boot, so this was contention between two renderers both
trying to hold the device, not eager acquisition by squeezelite. **This
is exactly the failure mode Phase 2b's arbitration supervisor exists to
prevent — expected in the absence of a running, correctly-wired
supervisor, not a new defect in the renderers themselves.**

**UNEXPLAINED — George observed pressing play in LMS started playback in
Spotify, not LMS.** Attempted reproduction the same session, on `gexis`:
with go-librespot idle/stopped (`/status`: `stopped: true, track: null`)
and a WebSocket watcher attached to its `/events`, sent a plain LMS
`play` for the `gexis` player. LMS's mode went to `play` as expected;
go-librespot's status did not change and **no event fired at all** on
`/events`. Single clean attempt, did not reproduce.

While investigating, found `gexis-core.service` is running on this
build and its Spotify adapter is **completely broken right now**:
it's built against `Config.go_librespot_port`'s default (3678), but
this build predates the port-pinning fix (see below) so go-librespot is
actually listening on an ephemeral port (39773 at the time of testing)
— every Spotify-adapter call has been failing with connection-refused
since boot (`journalctl -u gexis-core` confirms this on a loop). This
**rules out the arbitration core itself** as the mechanism behind
George's original observation, on this build at least — it structurally
cannot reach go-librespot's API to do anything to it. The LMS side is
confirmed working correctly on the live daemon, separately: the
acquisition test above logged `lms: player mode -> play (acquisition)`
right on cue.

Also found while reading the journal: go-librespot logs repeated
`loading previously persisted zeroconf credentials` / `authenticated
AP` / `authenticated Login5` cycles with no service restart between
them and no matching `accepted zeroconf from <device>` line (which
*did* appear once, at initial pairing) — i.e. something is making it
periodically re-authenticate with Spotify's backend using its stored
credentials, without a fresh local pairing handshake. Not tied to a
fixed timer (gaps of 5m and 1m seen). Left unexplained; noted as the
most plausible lead for George's observation (a phone-side or
session-refresh event, not a pairing event) without being confirmed as
the cause of it. **Not blocking further work** — see below for why: the
arbitration core couldn't have acted on it either way, given the port
bug above, and George has since given the criterion 4 decision (below)
that this session acted on.

**go-librespot's API port is ephemeral by default — breaks a hardcoded-
port assumption.** `ss -tlnp` across a single `systemctl restart` showed
both of go-librespot's listeners reassigned: the loopback API
46227→39773, and a second, all-interfaces listener 42769→36043. Fixed
now: `server.port: 3678` added explicitly to
`image/stage-gexis/02-renderers/files/go-librespot-config.yml` (the
arbitration core's `Config.go_librespot_port` already defaulted to
3678, so this makes that default true rather than lucky). The
all-interfaces listener is Zeroconf pairing, not the API — it's
*supposed* to be network-reachable (that's how the phone app finds and
pairs with the device at all), left as upstream's own random-per-start
default since nothing on this device needs to address it by a fixed
port. The same config file's comment previously claimed the whole
server was "loopback-only, so nothing outside this machine can reach
it" — false, conflated the two listeners; corrected in the same commit
that fixed the port, credited to direct measurement (`ss -tlnp`), not a
doc.

**Release-timing data, input to criterion 4 — decided and implemented
this session:**

| Renderer | Release path | Measured |
|---|---|---|
| go-librespot | `POST /player/stop` | device free before first 100ms poll (single run, so "<100ms", not "100ms") |
| squeezelite | LMS CLI pause | ~8500ms after the pause command (single run; an earlier ~7000ms UI-pause run had unmeasured lead time, so this is the cleaner figure). Consistent with `-C 10`. |

Both single runs, neither the ≥20-run distribution criterion 8 requires.
**George's decision:** drive squeezelite's release actively rather than
wait out `-C` — the LMS pause is still sent, as a courtesy so LMS's own
state reflects "paused" not "disconnected," but the supervisor no
longer waits on it during a takeover and escalates straight to
`SIGTERM`. Implemented via a new per-adapter `release_ladder` override
(`Adapter.release_ladder`, `core/src/gexis_core/adapters/base.py`) so
this didn't need a bespoke code path — `LmsAdapter` sets
`polite_grace=0.0`. `-C 10` still governs the non-arbitration idle case
(LMS stops on its own, nothing else wants the device); only the
takeover path bypasses it now. ADR-0010's implementation note amended —
it previously said `-C` was "what actually frees the device," which
this measurement showed isn't fast enough on its own. New test
(`test_adapter_specific_ladder_skips_the_polite_wait`) verifies the skip
via recorded `asyncio.sleep` calls, not wall-clock timing — 10 tests
total, still no hardware needed. **Not yet reflashed or hardware-
verified** — this build predates the change.

**LMS details for testing:** CLI on port 9090 (works from `gexis` via
`bash`'s `/dev/tcp`; telnet and `nc` aren't on the image). `gexis`
registers with playerid `e4:5f:01:58:89:07` — the **wlan0** MAC, not
eth0 (the machine has both). moOde is also registered
(`88:a2:9e:79:e1:32`), useful as a second player for takeover testing.

**Volume is confirmed global across renderers, as criterion 5 expects:**
moving it via LMS moves the hardware mixer, which then also affects
go-librespot, since the mixer is one physical control shared by the
card. Expected, not a defect.

**Image tooling gaps, added to "things that will bite" below:** `bc` is
not on the image (also not `xxd`, `telnet`, `nc`). `od`, `curl`, `ss`,
`fuser` are.

### Hardware session, 2026-09-06 (later): reflashed again, three real bugs found and fixed

Card index moved again — 3 this time (1, then 2, then 3 across three
consecutive builds of the same image on the same hardware). Amended
into Finding 005 alongside the earlier update.

**Bug 1 — `alsa.py`'s card-id regex never matched our own card.**
`/proc/asound/cards` pads the bracketed id to a fixed 15 characters.
`sndrpihifiberry` is exactly 15 characters, so there's no padding left
for `\S+` to stop at — it ran past the closing bracket and the colon
after it. Shorter ids (`vc4hdmi0`) have trailing spaces inside the
brackets and happened to work, which is presumably why this went
unnoticed until hardware testing hit our exact id. Fixed
(`re.match(r"\s*(\d+)\s+\[([^\]]+)\]", line)`); new test fixture covers
both the padded and exact-fit cases in one file so this can't regress
to only-the-padded-case again.

**Bug 2 — the hardware mixer was stuck at 0%, restored on every boot.**
Root cause: the stock image ships `alsa-restore.service` enabled
(`alsactl restore` on boot, `alsactl store` on shutdown), which is
exactly the restoring ADR-0018 forbids. Some earlier session's level
got stored on a clean shutdown; `gexis-boot-volume.service`'s own
explicit set raced it with no guaranteed order (both only declared
`After=sound.target`) and evidently lost. **This is what George heard
at the speakers**: LMS showing "playing" with no sound, fixed by
nudging the volume — the stream was fine, the mixer was at zero.
Likely also explains "finicky" Spotify takeovers (connected, silent,
fixed by disconnect/reconnect — probably the same zero-volume state,
not a takeover defect). Fixed by masking `alsa-restore.service`
entirely, which is more correct than winning the race: it makes "never
restored" actually true rather than "restored, then immediately
overwritten."

**Bug 3 — the volume bridge could ratchet the mixer to zero.** Two
independent feedback paths, not one: our own `set_raw` write shows up
on `alsactl monitor` (sometimes as more than one line per write), *and*
go-librespot can echo our `POST /player/volume` back as its own
`"volume"` WS event. The old "skip exactly one incoming line" boolean
covered neither reliably. One real logged sequence: 179, 172, 162, 140,
119, 97, 0/240, ~50ms apart, one direction, never stopping until it hit
zero — a candidate mechanism for Bug 2's zero, though not proven (could
also have been a held phone volume-down gesture). A single deliberate
change (`amixer sset DAC 50%`) converged after exactly one echo,
~325ms round trip — the good case, when it works. Fixed with a single
shared "last own write" timestamp: anything we write, either direction,
arms a short window (750ms), and anything arriving inside it — however
many lines or events — is dropped as our own echo, rather than trying
to count exactly one. Documented as a mitigation, not a proof of
convergence, in the code itself.

**Not fixed, recorded as a finding:** LMS's "mixer volume" (0-100) and
the hardware's 240 steps don't map linearly or by a dB-linear curve
either — `mixer volume 30` produced hardware `170/240` (71%). Something
in squeezelite's own volume mapping, not this bridge (the bridge only
observes the hardware value afterwards; squeezelite writes it directly
via `-V DAC`, outside the bridge entirely). Worth pinning down — it's
the visible "jump" George noticed switching between LMS- and
Spotify-set volume — but no owner or fix decided yet.

**Bluetooth: two separate blockers, one fix each.** Naming: BlueZ's
adapter name relies on the hostname-derived default rather than an
explicit `main.conf` `Name=`, and George saw an unrecognisable name
while attempting to pair — fixed with a targeted `sed` setting
`Name = gexis` explicitly (ADR-0022's "one name everywhere" intent).
Pairing: failed with a PIN error. Investigating traced this past the
PIN itself to something more fundamental — **the adapter was rfkill
soft-blocked** (`hciconfig hci0 up` → `Can't init device hci0:
Operation not possible due to RF-kill (132)`; confirmed at the sysfs
level, `/sys/class/rfkill/rfkill0/soft = 1`). Nothing in Raspberry Pi OS
Lite's unattended boot ever clears this — it's normally done by
`raspi-config`'s interactive country-code step, which `firstrun.sh`'s
headless flow never runs, so **Bluetooth has likely never actually been
pairable on any build of this image before now**, criterion 1's
"installed and writing to output" check having no way to catch it.
Fixed: `gexis-bluetooth-setup.service` runs `rfkill unblock bluetooth`,
powers the adapter on, and sets it pairable/discoverable.

Once unblocked, PIN-free pairing needed its own fix regardless:
**George's decision (ADR-0024, new)** — pair without a PIN at this
installation, now and after a display exists (a screen changes what
*could* be shown during pairing, not whether confirmation is *needed*
here). Implemented with `bt-agent --capability=NoInputNoOutput`
("Just Works"), registered as the default agent. The ADR states the
consequence plainly — anyone within range can pair and play audio with
no on-device confirmation — and that this is a per-installation choice,
not a shipping default: a flat with neighbours in range is a different
threat model, and this shouldn't be read as the answer for that case.
Recorded in `decisions/README.md`'s deferred-items table as needing
ADR-0022's settings infrastructure before it can be anything but
hardcoded.

**None of the Bluetooth fixes above have been hardware-verified with an
actual phone pairing yet** — verified individually (rfkill unblocks,
adapter powers on, `bt-agent` registers as default agent with the
right capability) but not as one real end-to-end pairing attempt. First
thing to check on the next reflash.

**Port fix and criterion 4 decision both validated on hardware this
session:** go-librespot now listens on the fixed `127.0.0.1:3678`;
`gexis-core` connects to it (`spotify: connected to
http://127.0.0.1:3678/events`) — the config comment describing the two
listeners (fixed API port, ephemeral-by-design Zeroconf port on all
interfaces) was re-checked against the file and is already accurate,
no further edit needed. Squeezelite's SIGTERM release measured ~100ms
against the idle timeout's ~8500ms — roughly 85x faster, confirming
last session's decision. **Cost worth carrying forward:** SIGTERM kills
squeezelite outright rather than pausing it — it restarts
(`Restart=on-failure`) but drops out of its LMS sync group on the way.
ADR-0010's sync-group-interaction item was already deferred as
*theoretical*; this makes it concrete. Flagged as possibly needing
un-deferring — not decided, George's call. Criterion 4's wording
amended to say LMS is a two-rung exception, so it doesn't read as
"met literally, intent unchecked" the way earlier defects on this
project have.

The earlier LMS-play-starts-Spotify behaviour did **not** recur this
session.

### Hardware session, 2026-09-07: Bluetooth confirmed working; criterion 3 blocked

**Bluetooth pairs and plays, no PIN.** rfkill was the real blocker, as
suspected — first successful pairing on any build of this image.

**DEFECT — criterion 3 not met: squeezelite does not come back after a
takeover.** After a takeover kills it: `is-active: inactive`,
`Result=success`, `ExecMainStatus=0`, `NRestarts=0`. squeezelite exits
*cleanly* on SIGTERM, so systemd sees success, not failure, and
`Restart=on-failure` never fires. LMS is gone from the system — not
paused, not paused-and-resumable, gone — until a manual restart or a
reboot. **Takeover from LMS works exactly once, in one direction.** The
unit tests couldn't have caught this: they verify the adapter *sends*
SIGTERM, not what systemd does with the resulting exit code. Recorded
in ADR-0010, which also notes this supersedes the sync-group deferral —
a player with no players has no sync group to lose.

**Not fixed — this is a policy decision, not a config tweak, and George
asked for options rather than a unilateral pick.** `Restart=always`
brings squeezelite back, but then the supervisor can't deliberately
stop it at all — systemd would relaunch it (and it could reopen the
device) immediately, defeating the ladder's SIGTERM/SIGKILL escalation
as a way to actually force a release. Three options, not one obviously
right:

1. **Send `SIGKILL` instead of `SIGTERM` for LMS's escalation.**
   squeezelite handling `SIGTERM` as a graceful, "successful" shutdown
   is well-behaved software on its own terms — it's just the wrong
   behaviour for what we need from it. An uncaught fatal signal (which
   `SIGKILL` always is) is *not* clean by systemd's own accounting, so
   `Restart=on-failure` should fire normally, no config change needed
   beyond what signal `LmsAdapter` sends. Smallest change; keeps every
   renderer on the same `Restart=on-failure` semantics. Release timing
   should stay fast (SIGKILL has no cleanup handler to run at all,
   likely faster than the ~100ms measured for SIGTERM, not slower).
   Risk: still depends on systemd's exit-status classification being
   what we think it is — exactly the kind of assumption that produced
   this defect in the first place with SIGTERM.
2. **Have the adapter explicitly relaunch squeezelite** (`systemctl
   start squeezelite.service`) once release is confirmed, rather than
   relying on `Restart=` semantics at all. Fully decoupled from how
   systemd happens to classify a given exit — deterministic, doesn't
   depend on getting an exit-code assumption right a second time. Costs
   a small amount of new bookkeeping in the adapter (when exactly to
   relaunch, and confirming it actually came back) that options 1 and 3
   don't need.
3. **Lower `-C` enough that pausing alone frees the device fast enough
   that killing squeezelite is never necessary**, sidestepping the
   restart question by not causing it. Already logged as ADR-0010's
   option 3 for the sync-group question too, and still untested there
   for the same reason: nobody has measured whether a short `-C`
   actually behaves fast enough in practice, only that the default
   (`-C 10`) does not.

**Leaning towards option 1** for being the smallest change that keeps
the existing signal-based design intact, but it carries the same class
of risk (an assumption about systemd's own behaviour) that caused this
defect — worth being clear-eyed about that before picking it over
option 2's more self-contained determinism.

**Volume: George's decision, implemented this session.** Each renderer
keeps its own volume, restored when it becomes active — not reset to
the safe level on every takeover, only at boot (criterion 6 as
written). A renderer with no remembered level gets the safe one.
Implemented as `renderer_volume.RendererVolumeMemory` (small JSON state
file, survives the daemon restarting) plus a `restore_volume` hook the
supervisor calls right after a takeover completes. **Scoped to LMS and
Spotify only** — see Finding 006 below for why Bluetooth is left out
for now. Unit-tested (arbitration's hook, the bridge's attribution and
active-renderer gating, and the memory class itself — 26 tests total,
still no hardware needed) but **not yet exercised on hardware.**

**Finding 006 (new): Bluetooth volume is hardware above ~96%, something
else below it.** Mixer stayed at 230/240 (96%, -5dB) across two
readings while the sound kept getting audibly quieter as the phone's
slider was dragged down — something other than the shared hardware
mixer is attenuating it below that point, which is exactly the kind of
undisclosed attenuation `ctl.output`/ADR-0009 exists to prevent. Which
component, and whether it's upstream of encode or on our own side, is
not established — full detail and what's not yet known in the finding
itself. Also: Bluetooth's own slider mapping is at least as bad as
LMS's (half the slider spans 5dB); Bluetooth and Spotify sound the same
at 100%, ruling out a simple fixed offset.

**Fixed: the LMS-app-volume-buttons-took-over-Spotify bug.** Root
cause, not just a workaround: the CometD subscription pushes on *any*
status field changing (volume included, not just play/pause), and
`last_mode` was reset to `None` on every reconnect — so the first
status push after any reconnect (a network blip, an LMS restart, or
just this process starting) read as a fresh "→ play" edge if the
player already happened to be playing, firing a real acquisition
against whatever renderer actually held the device. A volume-button
press is exactly the kind of unrelated field change that would trigger
this. Fixed by seeding `last_mode` with an actual status query before
entering the subscription loop. **Not independently reconfirmed on
hardware** — LMS's `/jsonrpc.js` `POST` endpoint was returning empty
replies (connection accepted, request received, no HTTP response at
all) while investigating this, unrelated to the fix itself; plain `GET`
requests to the same server still worked fine. Needs a live recheck
once that clears — worth checking LMS's own logs/state before assuming
it's transient.

**Takeover gap, Bluetooth → LMS: worse than expected, not yet
explained.** LMS shows itself trying to play for *several seconds*
before sound actually appears. Both directions' release timings were
measured at ~100ms last session, so whatever's adding the delay is on
the acquisition/start side, not release — device open, buffer fill, or
LMS/squeezelite startup behaviour are the candidates, none checked.
Worth investigating before criterion 8's formal takeover-gap
measurement, since a multi-second real-world gap would badly skew what
that measurement is supposed to characterise.

**Also observed, not yet acted on:**
- Spotify ↔ Bluetooth switching works cleanly both ways — no volume or
  timing complaints on this pair specifically.
- Bluetooth → Spotify Connect while playing pauses the Spotify track
  *and* resets its progress; only way to resume is skipping to the next
  track. Plausibly an inherent consequence of ADR-0010's own release
  table (Spotify: disconnect, not pause) rather than a defect to fix —
  reconnecting to a fully-disconnected Spotify Connect session not
  preserving exact scrub position is ordinary behaviour on other
  Connect-capable devices too, not something unique to this
  implementation. Not confirmed either way; noted, not chased.

### Hardware session, 2026-09-08: three bugs diagnosed, one design result

**Design result: `-C 1` replaces killing squeezelite entirely.**
Measured: `-C 10` (original) ~8500ms to release; `-C 1` ~700ms; SIGTERM
~100ms. 700ms is a plausible handoff gap — tested with no clicks, pops
or dropouts across track boundaries, or on a deliberate 2-3s
pause-then-resume (the case that actually forces a close and reopen).
This removes the reason to kill squeezelite on takeover at all, and
with it every side effect the kill approach cost across the last two
sessions: the `Restart=on-failure` defect, the sync-group loss, and
(expected, not yet reverified) the session-state reset George's third
reported issue described. **Reverted**: `squeezelite.service` is back
to a plain pause release, `-C 1` instead of `-C 10`; `LmsAdapter` has no
ladder override anymore. `-C` is squeezelite-only — it does nothing for
Bluetooth's release problem, below. Scope: single timing run, 100ms
poll granularity with `sudo fuser` latency in the loop; sub-second `-C`
values are undocumented in squeezelite's own help text; the listening
test was subjective, not instrumented.

**BUG, still open: the kill ladder does not release Bluetooth at all.**
Disconnect, then SIGTERM, then SIGKILL on `bluealsa-aplay.service` — all
ran, and the device was **still held after SIGKILL** (10.7s). Two
candidate causes, neither confirmed: the stock unit's `Restart=
on-failure` has no explicit `RestartSec`, so systemd's 100ms default
could restart-and-reopen well before the ladder's 2s check runs; and,
observed separately with `fuser`, `bluealsa-aplay` holds the PCM open
even after its own IO worker exits on phone disconnect — meaning
`Device1.Disconnect()` succeeding doesn't reliably free the device
either, which undercuts "kill it more reliably" as the fix (same shape
as squeezelite's own resolution: fix the renderer's own release path,
don't fight process death). Recorded in ADR-0010's "Open" section.
**Not fixed — needs its own investigation.**

**BUG, fixed: per-renderer volume memory was muting Bluetooth on every
acquisition.** `restore_volume: bluetooth to 60/240` (−90dB, inaudible)
logged on every Bluetooth acquisition, regardless of the phone's own
volume — **this alone was the entire cause of "Bluetooth outputs no
sound,"** not `bluealsa-aplay`, not routing. Root cause: `restore_
volume` fell through to the boot-safe default for *any* renderer with
no remembered level, including Bluetooth, which was never supposed to
be volume-managed at all (Finding 006). Fixed: `resolve_restore()` now
returns `None` for anything outside `MANAGED_RENDERERS`, meaning
"leave the mixer alone," not "apply a fallback." Also fixes the design
error underneath it: this control is dB-linear per raw step, not
perceptually linear (230/240 is −5dB, 60/240 is −90dB — a quarter of
the range reads as "inaudible," not "a quarter as loud"), which is also
the root cause of the LMS/Spotify scale mismatches reported earlier.
Added `raw_to_db`/`db_to_raw` and a restore-only dB floor
(`restore_volume_floor_db`, placeholder −40dB, **not confirmed by
George**) so a remembered-but-degenerate level can never be restored as
effective silence — applied only to a *remembered* value, never to the
boot default, which stays exactly the confirmed −90dB regardless.

**BUG, fixed: `bluealsa-aplay`'s mixer args were missing from the
override.** `Couldn't open ALSA mixer: Mixer element not found` — it
was looking for ALSA's own defaults (`name=default elem=Master`), which
don't exist on this image, not the `output`/`DAC` control LMS and
Spotify already use. Fixed by hand and verified:
`--mixer-device=output --mixer-name=DAC` added to the override; mixer
then opened cleanly. Flag names checked against this build's own
`bluealsa-aplay --help` before committing, not assumed. **Possible
connection to Finding 006** (Bluetooth volume partly software below
~96%): `--volume` defaults to `auto`, and a failed mixer lookup is a
plausible reason it fell back to software for the *entire* range, not
just the bottom of it — flagged in the finding as an unconfirmed
candidate, needs re-testing against the finding's original observation.

**BUG, fixed: PIN-free pairing doesn't set trust.** `bluetoothctl info`
showed `Trusted: no` for the paired phone even after a successful
PIN-free pairing; with trust unset, `bluealsa-aplay` opened the PCM and
then immediately logged `BT device marked as inactive` on a loop,
pulling no audio. `bluetoothctl trust <mac>` fixed it by hand — George:
"manual trust is not acceptable as a step for a user." Fixed with a new
`gexis-bluetooth-trust.service`: polls BlueZ every 2s for paired-but-
untrusted devices and sets `Trusted` itself via D-Bus. Polling, not a
`PropertiesChanged` subscription — deliberate given pairing is a rare,
human-paced event where a couple of seconds is imperceptible, not the
ADR-0018 "subscribed, not polled" principle being set aside (that
principle is about not adding lag to a *live-updating* value). **Not
yet verified on real hardware** — written and import-checked, no
`bluetoothd` available to test the actual D-Bus calls against here.

**Method note, from George's own report:** two earlier misdiagnoses
this session (a claimed missing device-tree overlay, then a claimed
hardware fault) both traced back to `speaker-test` on `output` and
`hw:sndrpihifiberry` appearing silent while Spotify was actually
playing normally the whole time — nothing in the audio hardware path
was broken. Worth remembering: the HiFiBerry overlay loads from the
HAT's own EEPROM, not `config.txt`, which is why `config.txt` has no
hifiberry line on any build — its absence is normal, not a defect.

**Status of George's three originally reported issues**, per this
session:
1. **Bluetooth silent** → the volume-memory bug above, plus the trust
   and mixer-args bugs. All three fixed, none reverified on a rebuilt
   image yet.
2. **squeezelite not restarting** → moot: `-C 1` means it's never
   killed in normal operation, so `Restart=on-failure` never needs to
   fire.
3. **Position reset on renderer switch** → expected to resolve now that
   LMS is paused rather than killed on takeover. **Not yet reverified**
   — check specifically on the next hardware pass.

**State the box was left in:** `squeezelite.service` and
`bluealsa-aplay.service` stopped; a hand-run `squeezelite` (`-C 1`,
name `gexis-test`) and possibly a hand-run `bluealsa-aplay` were left in
foreground shells for the testing above. Nothing hand-edited on disk
except `bluetoothctl trust` (persists). Superseded by the next reflash
— not cleaned up separately since the whole rootfs gets replaced.

### Hardware session, 2026-09-07 (v0.2.0 build): two regressions found live, both diagnosed and fixed

George reported two symptoms after reflashing v0.2.0: Bluetooth
connecting unreliably and playing silent even at max volume, and
squeezelite crashing and not recovering. Investigated live over SSH
(box was on, George wasn't near speakers) rather than guessed at —
`journalctl` across `gexis-core`, `bluealsa`, `bluealsa-aplay` and
`bluetooth.service` for the actual session gave a full, consistent
picture for both.

**squeezelite: the SIGTERM regression came back, self-inflicted.**
`systemctl status squeezelite.service` showed `code=exited,
status=0/SUCCESS`, `Deactivated successfully`, no restart.
`gexis-core`'s own log gave the exact sequence: `21:20:41` Spotify
acquired, `21:20:45` "still holds the device after polite stop, sending
SIGTERM" (so `-C 1`'s ~700ms measurement didn't hold this time — single-
run variance, exactly the caveat that measurement already carried),
`21:20:48` SIGKILL. squeezelite exited on the SIGTERM specifically
(clean, `Restart=on-failure` never fires on a clean exit) — the
*identical* defect from two sessions ago, reproduced live from the
ladder's own genuine escalation. Root cause of the regression: reverting
`signal_stop` back to respecting the ladder's `force` parameter was
bundled into the same change as the (correct) `-C 1` timing fix, but
they're independent decisions — `-C 1` makes escalation *rare*, it
doesn't make SIGTERM the right signal on the rare occasions escalation
still happens. **Fixed:** `signal_stop` ignores `force` again, always
sends SIGKILL, `-C 1` and the plain ladder timing stay as they were.

**Bluetooth: mechanically working, just never given an audible starting
volume.** The mixer-args and trust fixes from last session are both
confirmed correct in this session's own logs — `bluealsa-aplay` opened
`name=output elem=DAC` cleanly on every connection (no "Mixer element
not found" this time), and `bluealsa`'s log showed AVRCP volume updates
from the phone landing on the hardware mixer correctly once the phone's
slider was actually moved ("Updating A2DP volume: 91 [-4.80 dB]"). What
was actually missing: Bluetooth is deliberately unmanaged by the
per-renderer volume system (Finding 006 — its own volume path isn't
understood well enough to restore a remembered level for it), which
meant *nothing* set a starting level when it acquired the device — the
mixer just carried over whatever LMS or Spotify had last left it at.
That explains the exact sequence George described: silent at first
because the inherited level was quiet, then "the volume increased" and
a fraction-of-a-second of audible Bluetooth right as LMS's takeover
restored its own (louder) remembered level and Bluetooth's audio was
still draining out. **Fixed, one-directional:** on any unmanaged
renderer's acquire, bump the mixer up to the same audible floor used
for remembered LMS/Spotify levels if it's below that — never push down,
never fight an already-reasonable level, still not "managing"
Bluetooth's own curve.

**George's suggestion to revert everything Bluetooth-related back to
two builds ago was not taken** — the evidence pointed to a specific,
fixable gap (no starting volume) rather than the mixer-args or trust
fixes themselves being wrong, and both of those fixes are independently
confirmed correct by this session's own logs. Reverting them would
restore the two problems they were written to solve (mixer element not
found; PIN-free pairing needing a manual trust step) without a clear
reason to expect it would touch the actual cause. Flagging this
explicitly rather than silently overriding the suggestion — worth a
second look if the floor fix above doesn't hold up.

**Also fixed, likely explanation for "doesn't connect the first time,
works every time after":** `bluealsa-aplay` logged `Couldn't get
BlueALSA PCM list: The name org.bluealsa was not provided by any
.service files` right at boot — the stock unit has no `After=` on
`bluealsa.service`, so it can start before `bluealsa` registers on
D-Bus. Survivable (it picks up connections later via D-Bus signals
regardless, and every connection attempted after boot this session did
work), so this is a hygiene fix for a confirmed race, not a proven fix
for the specific symptom — but the shape matches closely. Added
`After=`/`Wants=bluealsa.service`.

**Not yet re-verified on a rebuilt image** — all four fixes above are
committed, none are on hardware yet.

### 2026-09-08: PeppyMeter adoption research and licence decision

George decided to adopt foonerd's PeppyMeter/PeppySpectrum fork (the
engine and skin rendering, not a browser reimplementation) rather than
write a renderer from scratch. Ordered research done before any
vendoring, all in **Finding 007**: licence facts for all three upstream
repos (read from source headers, not repo badges — `PeppyMeter` and
`PeppySpectrum` are GPL v3, `peppy_screensaver`'s handler files carry no
licence header of their own and only function combined with the GPL
engine), the NEON/pygame blocker (Debian Trixie's stock `python3-pygame`
tested clean under the same Docker+QEMU pipeline this project already
uses — likely dissolves the blocker, pending a hardware frame-rate
measurement), and the remaining ADR-0015 open items (`distance`,
font faces, the format-icon set — all confirmed from source).

**George's licence ruling: gexis-player is GPL v3** (personal project,
costs nothing we'd otherwise want, vendoring the engine is the whole
point). Recorded as **ADR-0025**, with the `LICENSE` file (already
present, unmodified GPLv3 text) and `# SPDX-License-Identifier:
GPL-3.0-or-later` headers added to every file in `core/src/gexis_core/`.
The convention is documented in `docs/DEVELOPMENT.md`.

**Integration approach proposed and accepted as ADR-0026**, after
surfacing (not silently overriding) a real conflict: running the actual
PeppyMeter engine reverses ADR-0015/0019's "renderer lives in the
browser" premise those records were built on. Both amended to point at
ADR-0026 rather than left contradicted. George confirmed the mechanism:
an always-on native PeppyMeter process, pre-rendering continuously,
with labwc-mediated raise/hide against the Chromium kiosk (mirrors
ADR-0019's original "no process to start, only a state change"
principle, just via compositor stacking instead of DOM visibility). The
exact labwc-side mechanism is flagged **unverified, needs a spike** —
not guessed at from memory. Scope: meters and spectrum only; turntable
and cassette handlers not vendored, pending George's ruling on whether
they're needed.

**Not yet done, by design:** no vendoring. Step 5 was "propose an
approach," not "implement it" — the actual vendoring and handler-adapter
work is future Phase 5 work.

**Process note:** this work landed on `phase-2b-arbitration` (the
current branch) because that's what was checked out — it's Phase 5
content, not Phase 2b. Flagging rather than silently rewriting history;
worth moving to its own branch before a PR, if that matters before the
next one.

### 2026-09-08 (continued): four live-fixed defects, dummy-control volume isolation

George ran a hardware test round and reported four symptoms: Bluetooth's
volume audibly changing when LMS's volume was adjusted from its own app
(even with Bluetooth actively playing), Spotify Connect dying and never
restarting, LMS's track appearing to start three times, and — after the
first fixes landed — Spotify showing "connected" but not sustaining a
takeover from LMS. All four diagnosed live over SSH against `gexis`
before any fix, per George's request this round ("make the fixes on the
device first"), then folded back into the repo. Full detail, evidence
and what's confirmed vs not in **Finding 008** — summary:

1. **Spotify Connect dying:** the release ladder's busy check asked "is
   anyone holding the device," which reports busy forever once the
   *incoming* renderer (not driven by our own code — LMS tells
   squeezelite to play independently of `acquire()`) has already grabbed
   it, regardless of whether the outgoing one ever let go. Confirmed
   from logs: go-librespot exited cleanly on its own `/player/stop`, but
   the ladder logged false "still holds"/"STILL holds" lines seconds
   later and escalated to SIGKILL against a process already gone.
   Compounded by go-librespot exiting cleanly (status 0) on SIGTERM,
   which `Restart=on-failure` never treats as failure — same defect
   shape ADR-0010 already documents for squeezelite, just never ported
   to `SpotifyAdapter`. **Fixed:** `alsa.device_held_by(unit)` checks
   the specific unit's own PID against the PCM's holders, not "anyone";
   `SpotifyAdapter.signal_stop` always sends SIGKILL now. ADR-0010
   amended.
2. **LMS starting a track three times:** same family as (1), still open
   after it — squeezelite's own retried `alsa_open` (while another
   renderer legitimately holds the device) correlates 1-for-1 with LMS's
   CometD stream reporting a fresh `mode: play`, kicking whichever
   renderer just took over back off. Confirmed not a reconnect/stale-
   frame artefact. Root mechanism inside squeezelite/LMS not traced —
   the fix (a ~0.4s debounce with a re-confirming status query before
   `LmsAdapter` fires an acquisition) targets the observed pattern, not
   a proven cause. Live-verified LMS play advancing normally
   (`time: 2.8s` after issuing play) after the fix; the specific
   "starts three times" repro wasn't independently re-run.
3. **Bluetooth volume changing when LMS's volume changes:** confirmed
   mechanism — `squeezelite -V DAC` and `bluealsa-aplay
   --mixer-name=DAC` both write straight to the one shared hardware
   mixer whenever their own upstream says to, with no awareness of
   arbitration state; only Spotify's path was ever isolated (via
   go-librespot's own software volume). **Fixed (B2, George's decision):
   dummy mixer controls.** Each of squeezelite and bluealsa-aplay now
   points its volume control at its own private `snd-dummy` card
   (`hw:gexislmsvol`, `hw:gexisbtvol` — no audio path behind either), and
   a new `DummyMixerBridge` (`core/src/gexis_core/volume.py`) mirrors
   whichever one belongs to the active renderer onto the real DAC. No
   software attenuation introduced anywhere. ADR-0018 amended. Two
   non-obvious implementation bugs found and fixed along the way:
   `alsactl monitor <card>` needs the `hw:` prefix (undocumented in its
   own SYNOPSIS), and `amixer`'s value-line format differs between the
   real DAC's control and a dummy control (parsing regex widened).
   Verified live, both directions (mirrors when active; does not touch
   hardware when inactive, confirmed with the real daemon stopped and an
   isolated instance run in its place) — **but a full multi-switch
   end-to-end retest has not yet been done**, and should happen on the
   rebuilt image.

**Everything above is committed to `phase-2b-arbitration` and about to
be rebuilt** — George will reflash and retest on the new image rather
than trusting the live-patched state further.

### 2026-09-08 (third session): hardware round on the rebuilt image — three volume bugs fixed, two issues still open

George tested the rebuilt image (with the fixes above) and reported five
symptoms. Full detail and evidence in **Finding 009**; summary:

**Fixed and verified live, all three volume-related:**
- **Spotify volume "finicky" (behind, delayed, sometimes absent, once
  inverted).** `restore_volume()` wrote straight to the real DAC on every
  acquisition, bypassing `VolumeBridge`'s echo window - its own write got
  misread as an external change and echoed straight back to Spotify,
  racing go-librespot's own volume report. Added
  `VolumeBridge.write_hardware()`; `restore_volume` and the unmanaged-
  renderer floor bump now go through it.
- **LMS volume silent below ~75%.** Measured directly: squeezelite
  derives its percent-to-dB curve from *whatever control's own declared
  range it's pointed at* - against the dummy control (-45dB span) this
  is a much gentler curve than it'd ever compute against the real DAC
  (-120dB span). `dummy_raw_to_hardware_raw()`'s fractional-position
  rescaling was undoing that gentleness, re-stretching the curve back
  across the DAC's full range. Fixed: direct dB copy, no rescaling.
  Verified live, before/after table in Finding 009 - 75% went from
  -32.8dB to -12.5dB.
- **Found while verifying the above, not one of George's five:** the
  mixer-value parsing regex silently dropped minus signs (`\d+` doesn't
  match `-`), wrong for the dummy controls' -50..100 range - a *wrong*
  parsed value, not a failure, affecting roughly the bottom third of
  LMS/Bluetooth's own volume range. Fixed: `-?\d+`.

**Narrowed but still open, both the same underlying family already
flagged in Finding 008/ADR-0010:**
- **LMS repeatedly reclaims the device from whoever just took it over**
  ("Spotify cannot takeover LMS unless LMS is paused"; Spotify failing to
  open the device for over a minute after a single LMS reclaim). New this
  round: squeezelite itself is now ruled out empirically (paused it,
  held the ALSA device open with an unrelated process for 12s, watched
  its log - zero retry attempts). The repeated `mode: play` must
  genuinely originate from LMS *server*, sustained well past the
  existing 0.4s debounce each time - mechanism not established, needs
  either LMS server's own logs (a different machine, out of reach from
  `gexis`) or context only George has.
- **LMS→Bluetooth takeover failed once, then worked.** Single
  occurrence, no logs captured pointing at a cause - noted against
  ADR-0010's already-open Bluetooth release-ladder item as a plausible
  match, not treated as a new defect.

All three volume fixes are committed and included in the next rebuild.
The two open items are **not** blocking that rebuild - they're
pre-existing, already-tracked gaps, not regressions from this round's
work.

### 2026-09-08 (fourth session): DummyMixerBridge's echo window and Spotify's curve fixed; Bluetooth race and LMS reclaim narrowed further

George tested the rebuilt image again and reported four more symptoms.
Full detail in **Finding 010**; summary:

**Fixed and verified live:**
- **Spotify's volume compressed into the last part of the slider ("60%
  = no sound").** The exact same raw-linear-not-dB-linear bug LMS had
  (Finding 009 §2), just on the renderer that fix never touched -
  plausibly always broken, only assessable once Finding 009 §1's echo
  bug stopped making Spotify's volume racy. Fixed the same way:
  `spotify_fraction_to_hardware_raw()`, dB-linear across -45..0dB
  (matching LMS's own effective span). Unit-tested and hand-verified;
  not yet re-confirmed against a live phone-driven change (go-librespot
  doesn't echo API-driven changes back over its own event stream, so
  there's no way to trigger this from SSH alone).
- **Bluetooth's usable maximum quieter than Spotify/LMS, and a session
  with zero mirrored Bluetooth volume changes despite a full slider
  drag.** Real bug in `DummyMixerBridge`: it carried an echo window
  copied from `VolumeBridge` without checking whether it applied - it
  didn't. `VolumeBridge` watches and writes the *same* card, so its own
  writes genuinely echo back; `DummyMixerBridge` watches the *dummy*
  card but writes to the *real DAC* - different cards, so a write here
  can never echo on what it's watching. The window could only ever
  swallow genuine rapid updates, and Bluetooth's AVRCP updates during a
  slider drag land as little as ~35ms apart - a fast enough chain could
  silence itself indefinitely. Fixed: removed the echo window entirely
  (`raw == last_raw` already covers the one legitimate case). Verified
  live: seven writes 150-200ms apart all mirrored correctly afterward -
  previously that cadence would have gone silent after the first one or
  two.

**Narrowed but still open, both refined with new evidence rather than
just reconfirmed:**
- **Bluetooth's unreliable first connect** now has a precisely-timed
  cause in the logs: `bluealsa-aplay` tries to open its ALSA PCM as soon
  as the A2DP *transport* starts, which fired ~1 second *before*
  `MediaPlayer1 appeared` (the signal we use for acquisition, chosen
  deliberately per ADR-0010 to not be stream-start). That second is
  enough for `bluealsa-aplay` to race ahead of our own release-the-
  previous-renderer logic. Confirmed one such race recovering via
  `bluealsa-aplay`'s own retry within the same second; a full-failure
  case is consistent with the same race landing worse, not confirmed.
  Not fixed - swapping the acquisition signal is a real ADR-0010
  trade-off, needs George's call.
- **LMS reclaiming the device from Spotify** reproduced again, but this
  session's log shows it happening *once* per Spotify session, not as a
  sustained fight - narrows the likely mechanism from "LMS server keeps
  re-asserting play" to "a single delayed play notification arrives
  shortly after LMS was paused." Still not fixed - a debounce can't tell
  a slow, single delayed echo from a genuine new user action.

Both volume fixes are committed and included in the next rebuild.

### 2026-09-10 (fifth session): two acquisition-signal fixes for the takeover deadlocks, two floor/fallback values flagged for George

George tested the rebuilt image again and reported four more symptoms
after a 2026-09-08 session; investigation was interrupted mid-way by a
context limit and picked back up 2026-09-10 against the same captured
log (`journalctl -b`, still present on `gexis`). Full detail in
**Finding 011**; summary:

**Implemented and deployed live on `gexis`, but NOT yet verified
against a real connect/takeover cycle** (George unavailable to test
this round) **- do not rebuild the image around these until that
verification happens:**
- **Bluetooth's ~1s acquisition race (Finding 010)** - George approved
  moving the trigger earlier. `BluetoothAdapter` now also acquires on
  `org.bluez.MediaTransport1` appearing (the A2DP transport object, at
  `.../dev_XX/fdN`), confirmed against BlueZ's own `doc/media-api.txt`
  and against `gexis`'s own log (the transport object appears several
  seconds before `bluealsa-aplay`'s own PCM-open attempt, not just ~1s
  before it) - alongside the existing `MediaPlayer1` trigger, not
  instead of it.
- **"Spotify cannot take over from LMS while LMS is playing" traced to
  a real deadlock, not a race.** Read go-librespot's own source
  (`daemon/controls.go`): its `"active"` WS event - the only signal
  `SpotifyAdapter` acquired on - is emitted only *after* the ALSA device
  opens successfully, so it can never fire while another renderer holds
  the device. Confirmed directly in `gexis`'s log: after LMS reclaimed
  the device, go-librespot logged four straight `Device or resource
  busy` failures over ~13s, and `"active"` didn't fire until 37s later,
  once the phone gave up and re-initiated the transfer from scratch (an
  opportunistic recovery, not a fix). `SpotifyAdapter` now also acquires
  on `"will_play"`, emitted earlier in the same call chain, before any
  ALSA access - confirmed from the same source read.

**Flagged, deliberately not changed - both need George's call on a
number, not a mechanism fix:**
- **Spotify's first-ever acquisition of a session falls back to the
  same -90dB boot-safety default used at true cold boot**, even when
  it's 20+ minutes into a session where LMS has already been playing
  loud - confirmed in the log (`restoring spotify to 60/240`, Spotify's
  first acquisition of that session). `RendererVolumeMemory.
  resolve_restore()`'s own docstring already documents this as
  deliberate, so it's ADR-0018's boot-safety rationale not covering the
  case it's actually firing on, not an oversight.
- **Bluetooth's unmanaged-floor bump fired correctly and reached
  hardware** (confirmed: `bumping to the -40.0dB floor` in the log) **but
  George still reported "no sound"** until LMS separately raised the
  real DAC to a loud level. The mechanism (`unmanaged_floor_raw`) is
  doing exactly what it was built to do; `-40.0dB` just isn't loud
  enough on his hardware/room.
- Confirmed, no action needed: **"the volume curves are good"** -
  Finding 009/010's dB-linear curve fixes are holding up in real use.

Both signal fixes are committed. **Neither is included in a rebuild
yet** - next step is a live verification pass (real Bluetooth
connect/disconnect, real Spotify takeover while LMS is actively
playing), then rebuild.

### 2026-09-10 (sixth session): Finding 011's two signal fixes confirmed; Bluetooth's frozen volume ceiling and a blip on takeover fixed

George tested and confirmed: "Testing on the device after the last
fixes show clear improvement on all fronts." One Bluetooth volume issue
remained - full detail in **Finding 012**:

**Root cause 1, confirmed directly on `gexis`, closes Finding 006:**
BlueALSA's own persisted per-device state (`/var/lib/bluealsa/<MAC>`)
had `SoftVolume=true` for the paired phone - `bluealsa-aplay`'s own
source skips writing to our ALSA mixer entirely whenever that's set, so
the real DAC's gain during a Bluetooth session was frozen at whatever
it inherited at acquire time, never tracking the phone's own slider.
Confirmed: zero `"bluetooth -> hardware"` mirror lines across two full
boot sessions despite dozens of real AVRCP volume changes in bluealsa's
own log. Fixed: `--volume=mixer` added to `bluealsa-aplay`'s
`ExecStart`, confirmed against this build's own `--help` first. This
was Finding 006's "Bluetooth volume partly software" open item, now
closed - it was the whole range, not "below ~96%".

**Root cause 2, a general ordering bug, not Bluetooth-specific:**
`Supervisor.acquire()` wrote the incoming renderer's volume to the
shared real DAC *before* releasing the outgoing one. Confirmed in the
log: a Bluetooth→LMS handoff wrote the DAC to LMS's 240/240 target 2.3s
before Bluetooth's own release ladder finished - a loud, audible blip
on Bluetooth's still-playing audio, exactly George's "fraction of a
second louder" report. Fixed by reordering `acquire()` to release
first, restore volume after; all 56 tests pass unchanged.

Both deployed live on `gexis` and **confirmed by George**: "just
tested, both fixes look good." Image rebuilt (`v0.2.1-13-g6f7f3e4`,
14m13s, `--volume=mixer` in the version tag comes from a commit not yet
tagged - the `-dirty` suffix `git describe` reports is only the known
`pi-gen` submodule `EXPORT_IMAGE` artefact, not an uncommitted change of
ours).

### Phase 2b closed, 2026-09-10

Checked criteria 3-6 against this week's evidence (not assumed from the
list alone):

- **Criterion 3** (arbitration model) - passes, exercised extensively
  all week across all three renderers.
- **Criterion 4** (timeout ladder) - mechanism passes; one item
  deferred, George's decision: Bluetooth's release ladder was once
  found (2026-09-08) to still hold the device after a full SIGKILL
  escalation, and that specific failure mode hasn't been re-reproduced
  since (every Bluetooth release measured this phase succeeded via
  polite stop alone, 2.0-3.2s). Recorded in ADR-0010's "Open" section.
- **Criterion 5** (volume bridge, variable/fixed) - variable mode
  passes, hardware-verified end to end (Finding 012). Fixed output mode
  isn't implemented anywhere in `gexis_core` - no config toggle, no
  mixer-lock code path - deferred, George's decision, same session.
  Recorded in ADR-0018's "To be recorded once resolved".
- **Criterion 6** (boot volume) - passes, confirmed at every boot in
  the logs.

`docs/DEVELOPMENT.md`'s Phase 2b entry marked done, matching 2a's own
convention. PR from `phase-2b-arbitration` into `phase-2-arbitration`
(its home branch, same pattern as 2a) is next.

### Phase 2c started, 2026-09-10/11: criterion 7 passing, criterion 8 in progress, four reliability defects found (Finding 013)

**PR #6 (`phase-2b-arbitration` → `phase-2-arbitration`) merged** before
this session started - found already done, not redone. Branched
`phase-2c-takeover` off the now-updated `phase-2-arbitration`.

**Prerequisites, all done before touching criteria 7-10 themselves:**
Finding 011's two live signal fixes (Bluetooth `MediaTransport1`, Spotify
`will_play`) verified clean on a real hardware round (Bluetooth
connect/disconnect, Spotify takeover while LMS played) - George confirmed
"all went fine." Image rebuilt (`v0.2.1-15-g2396ea2-dirty`, 12m50s) and
reflashed; found and fixed a real bug in the process - the `Makefile`'s
version-annotation step silently failed once more than one build's
`.info` manifest existed in `image/deploy/` (every build after the
first), so neither the 2026-09-08 nor the 2026-09-10 manifest ever got
its version line despite the build printing a false "Annotated..."
success message. Fixed with `ls -t | head -1` instead of a bare glob.
Spotify Web API app registered by George; one-time PKCE authorization
done together to get a refresh token, verified end-to-end against the
live API. `gexis`'s Spotify device_id is **not** cached anywhere it
matters - `spotify_api.py` resolves it by name on every call, since a
reflash resets go-librespot's zeroconf identity (confirmed: it changed
after this session's own reflash) the same way Finding 005's card index
and the pre-pinning ephemeral API port did; a fresh reflash still needs
one manual phone-side pairing (Spotify app, select "gexis" once) before
the name lookup finds anything, since the Web API alone can't bootstrap
that handshake.

**New test tooling, `tools/phase-2c/`** (gitignored credentials file
`spotify.local.env`, added to `test-gitignored-credentials.sh`'s standing
list): `lms_cli.py` (LMS CLI port 9090), `spotify_api.py` (Spotify Web
API, PKCE), `pcm_holder.py` (independent "who holds the PCM" ground
truth via `sudo fuser` + `/proc/<pid>/comm` - plain `fuser` can't see
another process's fds here, Yama `ptrace_scope`, even same-user),
`spectrum_fifo.py` (onset/silence detection via peppyalsa's spectrum
FIFO, chosen over an `snd-aloop` tap - ALSA's `type multi` turned out to
be for channel-remapping, not a clean broadcast-duplicate, and reusing
the FIFO avoids touching the live `output.conf` slave chain during
testing), `attack_test.py` / `bt_attack_test.py` (criterion 7),
`takeover_gap.py` (criterion 8). `spectrum_fifo.py`'s frame format (30 x
4-byte native-endian uint = 120 bytes, read directly from peppyalsa's
`spectrum.c`) corrects an earlier unconfirmed "64 bytes" guess this file
used to carry. The onset detector's own lag was measured at 19.5-40ms
against real hardware (`onset_smoketest.py`, using `/proc`'s PCM
`trigger_time` against a known silence-then-tone WAV, no mic/ADC path
exists on this hardware to calibrate any other way) - small next to the
gaps being measured.

**Criterion 7 (attack test): passing.** 0 violations of "no two renderers
hold the device at once" across every scripted race - LMS↔Spotify both
directions plus a scripted reclaim-spam pattern (15 rounds, clean once
run against an isolated LMS session rather than George's own real
background listening, which had confounded an earlier attempt and
produced what first looked like a live reproduction of Finding 009/010's
still-open LMS-reclaim item - retracted once isolated), and
Bluetooth-involving pairs (George live as the audio source; scripted
`bluetoothctl connect` reliably reconnects the Bluetooth profile but does
**not** reliably resume real audio streaming, so several rounds ended up
uncontested rather than genuine races - noted, not fixed, a harness
limitation not a product defect).

**Four reliability defects found along the way, all in Finding 013:**

1. **squeezelite's restart-rate limit (`StartLimitBurst=5`/60s) can be
   exhausted by legitimate adversarial arbitration activity**, not just a
   misconfigured unit (what it was sized for) - SIGKILL firing while the
   device is still busy raced squeezelite's own restart into 5 failures
   within 15s, permanently failing the unit with no further auto-restart.
   `gexis` silently dropped off the LMS server's player list until a
   manual `systemctl reset-failed`. **Fixed:** burst raised to 20
   (`image/stage-gexis/02-renderers/files/squeezelite.service`, commit
   `2eec5f9`), applied live and ported into the image source.
2. **go-librespot can enter a rapid (50-300ms) internal acquisition-retry
   storm** under repeated Spotify Connect transfer calls - confirmed real
   and self-resolving, confirmed **not** reproducible from a single
   isolated transfer call under the same busy-device precondition.
   **Deferred, George's decision** - hasn't shown up in normal hands-on
   testing across recent builds, only under this session's own
   repeated-API-call testing. Revisit immediately on any real recurrence.
3. **go-librespot's own retry-then-reauth backoff after a failed device
   open is ~56s, not immediate** - the takeover-gap harness's own retry
   cadence (every ~12s) was landing right on top of this, producing a
   sustained 14-round (~13 minute) cycle where arbitration behaved
   perfectly (LMS released cleanly every time) but go-librespot never
   once got real audio playing, confirmed to stop completely the instant
   the harness itself stopped (not spontaneous). Read as the likely
   mechanism behind a much older, previously-unexplained item - go-
   librespot's periodic "loading previously persisted zeroconf
   credentials" cycles with no known trigger. **Harness fixed** (single
   attempt per round, 65s cooldown on failure instead of rapid retry);
   go-librespot itself not touched.
4. **go-librespot can report itself actively playing a real track while
   never having opened the ALSA device at all** - found immediately after
   fixing #3, from a single clean, unhurried arbitration cycle (no
   repeated calls, no storm). Confirmed independently three ways
   (`/proc/asound/.../status` showing `closed`, `sudo fuser` showing no
   holder, the process's own `/proc/<pid>/fd` showing no handle to
   `/dev/snd/`) - not just this project's own `pcm_holder.py`. Sharpens
   Finding 011's own caveat that adapter-level signals aren't proof audio
   is flowing: this shows even a later, steady-state status read can't be
   trusted either, not just the initial acquisition event. Plausibly a
   **better-fitting explanation than #3** for the old "Spotify showing
   'connected' but not sustaining a takeover from LMS" report, since it
   needs only one ordinary takeover, not repeated contention - neither is
   confirmed as the actual historical cause. **Not fixed, not
   root-caused** - needs reading go-librespot's own source to explain,
   not chased further this session.

**Criterion 8 (takeover-gap measurement): in progress, not complete.**
The FIFO-based measurement mechanism itself is validated (source-read
frame format, measured detection lag, and - after two real bugs found and
fixed in the reader design itself: a multi-reader FIFO corruption issue
from reopening per attempt rather than using one persistent reader, and a
wrong assumption that "silence" shows up as zero-valued frames rather
than an absence of frames during a real cross-renderer gap, since no
renderer has the PCM open at all during a genuine handoff) - confirmed
correct via direct instrumented testing. But defects #2-#4 above kept
interrupting actual measurement runs before a clean ≥20-run distribution
could be collected for even the LMS↔Spotify same-rate pair. This is
where testing paused for the session - see "Next actions" below.

### Eighth session, 2026-09-11: LMS→Spotify criterion 8 collection attempted, blocked on a sharper version of Finding 013 §3

The FIFO-reader fixes and `takeover_gap.py`/`bt_attack_test.py` described
above were still uncommitted at the start of this session (git showed
them as working-tree changes, not landed) despite the narrative already
describing them as done - committed now (`ec44674`), no code changes,
just catching git up to what was already true.

**A 5-round trial of `takeover_gap.py`'s `lms-to-spotify` direction
(single attempt per round, 65s cooldown - Finding 013 §3's own fix)
produced 0 successes in 4 rounds** before being stopped deliberately
rather than run blind to n=20. Instrumented, isolated follow-up
(`tools/phase-2c/diag_one_transfer.py`, four clean single-call runs, no
harness retry logic involved) found the failure is **not** the harness
colliding with go-librespot's own retry cadence, as Finding 013 §3
framed it - it reproduces on a single, unhurried, non-repeated transfer
call, deterministically. Full detail, exact timestamps and two distinct
failure modes in **Finding 014**:

- **Mode A:** go-librespot attempts its ALSA open within about a second
  of `will_play` firing; LMS's polite release takes ~3.1s. Every clean
  attempt loses this race. This directly contradicts
  `adapters/spotify.py`'s own comment justifying the `will_play` trigger
  (that the device would already be free by the time go-librespot's own
  retry, or re-entered call, tried again) - confirmed false when
  go-librespot's attempt is faster than the release, which this session's
  evidence says is the normal case. **A second, distinct transfer call
  ~2-3s after the first reliably succeeds** (by then the *original*
  release has finished) - consistent with why field reports have called
  this "finicky" rather than "broken": an impatient second tap plausibly
  rescues most real attempts.
- **Mode B:** some calls instead produce **no `will_play` at all** - only
  go-librespot's own credential-reload/reauth cycle, then nothing, for at
  least 100 seconds watched. Trigger condition not established.

**Criterion 8's LMS→Spotify leg is not currently collectible as "the gap
of one ordinary takeover action"** - a lone attempt's outcome is
dominated by which race outcome it hits, not by the thing criterion 8 is
meant to characterise. Recommend against further blind `takeover_gap.py`
collection for this leg until George picks one of Finding 014's three
options: shrink LMS's ~3.1s release (reopens the kill-vs-pause trade-off
already settled once, 2026-09-08, for a different reason), have
`SpotifyAdapter` itself retry once LMS's release is confirmed complete
(no known local go-librespot endpoint for this yet - unchecked whether
one exists), or redefine what criterion 8 measures for this leg
(first-successful-attempt only, documented as such).

**Not attempted this session, still open:** cross-rate LMS↔Spotify,
Bluetooth-involving pairs (both already blocked on their own prerequisites
per the "Next actions" list below) - stopped once the LMS-Spotify same-
rate leg turned out to be blocked, rather than moving on to legs that
would hit the same underlying defect from a different angle.

`gexis`'s state at the end of this session: LMS paused, no PCM holder,
`tools/phase-2c/` synced to `~/phase-2c` on `gexis` via `rsync` (not
committed there - it's a deploy target, not a repo). No hand-edits to
any shipped config.

### Same day, second session: Finding 014 fixed (George: option 2), then a new blocker found collecting the real distribution

**George picked option 2.** `SpotifyAdapter` now retries itself once the
outgoing renderer's release is confirmed, via `POST /player/resume` -
go-librespot's own local HTTP API, no Spotify account credentials needed
(unlike the test harness's Web API calls, which only work because this
project's own PKCE-authorized `spotify.local.env` exists). Implemented as
a new optional `Adapter.device_freed()` hook (`adapters/base.py`,
default no-op), called by `Supervisor.acquire()` after the outgoing
renderer's release and the incoming renderer's volume restore.
`SpotifyAdapter` is the only override. Unit-tested at the supervisor
call-site level (59 tests total, still no hardware needed for the policy
layer); the actual HTTP call is hardware-verified only, matching this
project's established convention for adapter network code. Full detail
in Finding 014's "Fixed and verified" addendum and ADR-0010's matching
amendment.

**Deployed live on `gexis`** (hot-patched three files into the running
venv, `systemctl restart gexis-core` - no rebuild) after explicit
confirmation, since editing a live systemd service's installed files with
`sudo` on real hardware is exactly the kind of action this project's
auto-mode classifier pauses for. Verified immediately: 5 of 5 real
LMS-to-Spotify handoffs succeeded (previously 0 of 4), gaps
895.5-1900.2ms.

**Moved to collecting the real ≥20-run distribution** criterion 8 needs.
LMS-to-Spotify: **done, 16 of 20 succeeded** -

| | |
|---|---|
| min | 899.7 ms |
| max | 2593.0 ms |
| mean | 1619.9 ms |
| median | 1827.8 ms |
| stdev | 484.5 ms |

(4 rounds skipped near the end, "lms never acquired PCM within 15s" -
turned out to be the same root cause as the blocker below, not a separate
issue.)

**Spotify-to-LMS: 0 of 11 attempted before the run was stopped** - but
this is **not** evidence of a genuine reverse-direction defect.
Diagnosed: `squeezelite.service` had gone into `failed` state
(`Start request repeated too quickly`, restart counter **24** - past the
raised-to-20 limit from Finding 013 §1) partway through the
LMS-to-Spotify leg, so every Spotify-to-LMS round failed simply because
there was no LMS renderer left to acquire anything, not because of
anything specific to that direction. Recovered
(`systemctl reset-failed && systemctl start squeezelite`, plus freeing
Spotify's own hold first via `/player/stop` so the restart wouldn't
immediately fail busy again) - all five units confirmed active,
`NRestarts=0`, before stopping for the session.

**This is Finding 013 §1 recurring, but with a materially sharper
trigger, recorded as an addendum to that finding.** The original
characterization was "legitimate adversarial arbitration activity" -
attack-test-style rapid racing. This session's rounds were evenly paced
(~6-8s apart, each settled before the next began), much closer to
ordinary repeated use than an attack, and it still tripped the limit.
`gexis-core`'s own log shows round 16 specifically: LMS still held the
device after the full 3s polite grace (every one of the 15 rounds before
it had freed within 3.1-3.2s) - escalated through `LmsAdapter`'s
always-SIGKILL `signal_stop` twice, finally freeing at 8.3s, by which
point squeezelite had already restarted and failed busy several times on
its own. Why round 16 specifically failed to free within the normal
window after 15 consecutive successes is **not established** - recovery
took priority over root-causing it this session.

**Blocks resuming criterion 8's Spotify-to-LMS leg** (and any repeat of
the LMS-to-Spotify leg past ~16 consecutive rounds) **until George
decides how to handle this** - raising the burst limit further is
possible but is explicitly a mitigation, not a cure, per Finding 013 §1's
own original text; the underlying race (SIGKILL firing while the device
may still be mid-release) is the more correct fix but wasn't chased
today. Not attempted again this session, deliberately, rather than risk
tripping the same failure repeatedly and needing another manual
recovery each time.

### Same day, third session: George picked "fix the race" - implemented, verified, criterion 8's same-rate LMS↔Spotify leg completed

**Root cause, found by tracing what happens *between* the arbitration
ladder's own checkpoints, not just at them:** SIGKILL (the 2026-09-07/08
fix for squeezelite exiting cleanly on SIGTERM and never returning) makes
`Restart=on-failure` fire correctly, but that automatic restart then runs
on systemd's own fixed `RestartSec=2` cadence, completely decoupled from
the arbitration ladder's own timing - squeezelite tests whether it can
open the ALSA device at every startup, and for as long as the device
stays legitimately busy it keeps failing and systemd keeps restarting it,
burning through the burst limit on a clock nothing in `gexis-core` was
watching or controlling.

**Fixed:** `LmsAdapter.signal_stop` now calls a new `stop_unit`
(`systemd.py`) - `systemctl stop`, not a raw kill signal - so nothing
restarts automatically at all once it's called. A new `device_freed`-
symmetric adapter hook, `restart_after_release` (`adapters/base.py`,
default no-op), brings squeezelite back explicitly instead, called by
`Supervisor.acquire()` as the very last step, after the incoming
renderer's own retry chance and volume restore - `LmsAdapter` is the only
override. **Residual risk named, not assumed away:** if that one explicit
restart also finds the device still busy, `Restart=on-failure` (still
configured, for genuine unrelated crashes) does still govern recovery
from that fresh failure - a much rarer combination than before, not
proven impossible. Full detail in ADR-0010's matching amendment and
Finding 013 §1's own addendum. 63 tests pass.

**Verified on hardware, deployed live (confirmed, then done) after the
same kind of explicit go-ahead as Finding 014's deploy:**
- The core guarantee directly confirmed: stopped squeezelite by hand
  while it held the device, watched it stay `inactive` for 9 seconds (far
  past `RestartSec=2`), no auto-restart - then a plain `systemctl start`
  brought it back cleanly.
- The named residual risk reproduced on purpose, not just theorized: a
  manual `systemctl start` issued while Spotify still held the device
  *did* trigger `Restart=on-failure` and climb `NRestarts` - freed
  immediately by stopping Spotify's own hold rather than let it climb
  toward the limit again.
- Through the real `Supervisor.acquire()` path (not manual testing): 15
  consecutive LMS-to-Spotify rounds, then 20 consecutive Spotify-to-LMS
  rounds - **zero restart-storm recurrences, all five units healthy
  throughout, `NRestarts` unchanged across both batches** (the
  kill-escalation path wasn't needed in either batch, consistent with
  escalation being rare rather than the fix being unexercised).

**Criterion 8's same-rate LMS↔Spotify distribution collected cleanly on
both legs as a direct result - written up in Finding 015:**

| Direction | n | min | max | mean | median | stdev |
|---|---|---|---|---|---|---|
| LMS→Spotify (combined, 3 batches across the session) | 36 | 895.5ms | 2593.0ms | 1631.5ms | 1827.8ms | 400.3ms |
| Spotify→LMS (one clean batch) | 20 | 4107.5ms | 4235.5ms | 4173.3ms | 4170.9ms | 33.2ms |

Both directions confirmed same-rate (44.1kHz both sides, read directly
from `/proc/asound/.../hw_params` and go-librespot's own `/status`, not
assumed). **A real, notable, unexplained asymmetry:** Spotify→LMS is both
~2.5x slower and ~12x more consistent (stdev) than LMS→Spotify - plausibly
LMS/squeezelite's own acquisition-side startup work dominating a
deterministic total, versus LMS→Spotify's spread being a visible
fingerprint of Finding 014's retry mechanism interacting with variable
release timing - neither root-caused, see Finding 015 for exactly what is
and isn't established.

**Criterion 9** (write the actual finding once real numbers exist) is
satisfied for this one pair/rate combination - cross-rate and
Bluetooth-involving pairs still need their own measurement. **Criterion
10** (UI transition screen - George's call) now has real numbers to
decide against for this pair, not yet decided.

**None of this session's three fixes (Finding 014, Finding 013 §1's
resolution, plus the harness/tooling from earlier) are in a rebuilt image
yet** - all deployed live via hot-patch only. Next rebuild should fold
all of it in before further hardware sessions rely on it surviving a
reflash.

### Same day: image rebuilt and reflashed, then both fixes above reverted after live regressions

**Rebuilt and reflashed** (`v0.2.1-28-ge916f86-dirty`, 846s/14m6s warm
build) - all today's fixes baked in for real, not hot-patched. Confirmed
on the fresh boot: all five units active, `pip show gexis-core` and a
grep of the installed `gexis_core` package both confirmed the new code
was actually there. A fresh reflash reset go-librespot's zeroconf
identity (expected, per Finding 005's own pattern) and BlueZ's pairing
state (expected) - Spotify re-paired with one phone-side tap; Bluetooth
needed three connection attempts before settling into reliably connecting
(George's own report) - not investigated further, noted as a data point
since it's stable afterward.

**Build filenames now carry the version too** (George asked, separately
from the fixes above) - `Makefile`'s `image:` target passes pi-gen's own
`IMG_SUFFIX` via `PIGEN_DOCKER_OPTS`'s `-e` flag, no `image/config` or
submodule edit needed. This build predates that change (built right
before it), so its own filename is still date-only - the *next* rebuild
is the first real test of it.

**A full library scan (60,974 tracks, LMS's own `songs` JSON-RPC query,
paginated) found zero non-44.1kHz content anywhere** - criterion 8's
cross-rate LMS↔Spotify leg has no existing content to test with. Not
resolved - George's call on whether to add dedicated test content or
defer this leg.

**Two serious live regressions found during continued use, both traced
to root cause and reverted the same day - full detail in Finding 014's
and Finding 013 §1's own follow-up sections, ADR-0010's matching
amendments, and a new standalone summary (`docs/findings/phase2c-issues-
overview.md`) written specifically to hand to a fresh session:**

1. **Finding 014's fix** (`SpotifyAdapter.device_freed()` calling
   go-librespot's local `/player/resume`) could get real audio playing
   without completing the Spotify Connect handshake that tells Spotify's
   own backend gexis is genuinely active - confirmed directly in
   `gexis-core`'s log (`will_play` with no following `device became
   active`). Symptom exactly as George reported: audio plays, the
   Spotify app shows "gexis disconnected," and "next" moves playback to
   the phone. Reverted to the inherited no-op - Mode A's original race
   (a lone LMS-to-Spotify attempt loses to LMS's release almost every
   time) is unresolved again.
2. **Finding 013 §1's fix** (`stop_unit`/`restart_after_release`)
   passed 35 clean scripted rounds, then recurred for real under
   continued live use with Bluetooth reconnecting several times -
   squeezelite hit the identical restart-storm failure again, tripping
   the burst limit. The residual risk that fix's own docs named
   ("not proven impossible, only made meaningfully rarer") turned out to
   matter. Reverted to plain `kill_unit(force=True)` +
   `Restart=on-failure` - the original, longer-tested (if imperfect)
   behaviour.

Both reverts: code changed, 63 tests still pass, deployed live on
`gexis` (hot-patch) to unblock George immediately, then **rebuilt again**
per George's explicit request so the reverted (safe) state is what's
actually flashed, not the regressed one. See "Next actions" below for
what a real fix for either would need to account for that this attempt
didn't.

### Ninth session, 2026-09-11: Finding 016 — the polite rung's grace period was a blind sleep, not a poll

**Diagnosed on the device with George**, debugging the restart storm
further, and found something upstream of it: `Supervisor.
_release_with_ladder`'s polite rung (`arbitration.py`) checked `_busy()`
once before `asyncio.sleep(ladder.polite_grace)` and once after, with
nothing in between. The `"freed within polite grace (%.1fs)"` log line
read as a per-renderer release measurement; it was actually measuring the
3.0s sleep itself. Evidence: seven consecutive hand-driven LMS releases on
the current build logged 3.1-3.2s six times running (the sleep plus
overhead) and 0.1s once (the pre-sleep check catching a device that was
already free before the ladder started) — against squeezelite's own
~700ms passive-release figure from an earlier session (ADR-0010's
2026-09-08 amendment), which that 3.1-3.2s cluster should never have been
that far from. Full detail, scope, and what this implies for Finding 015's
numbers in **Finding 016**.

**Why it mattered beyond the misleading log line:** every LMS takeover
was landing at 3.1-3.2s against the ladder's 3.0s `polite_grace`
ceiling — effectively no margin, and a plausible contributor to the
restart-storm fuel (`LmsAdapter.signal_stop` always sends `SIGKILL`
regardless of ladder rung, which fires `Restart=on-failure` on escalation)
under the Bluetooth-churn load pattern that broke Finding 013 §1's fix.

**Fixed:** the polite rung now polls `_busy()` every
`POLITE_POLL_INTERVAL` (0.1s) up to the same `polite_grace` ceiling,
returning as soon as the device reports free, instead of sleeping the
full grace blind. Ceiling, escalation semantics and the SIGTERM/SIGKILL
rungs are unchanged — same ladder, checked more than twice, not a
redesign. Shared code, so all three renderers get it. ADR-0010 amended
(sixth amendment). New unit test
(`test_polite_grace_polls_instead_of_sleeping_blind`,
`core/tests/test_arbitration.py`) verifies the poll-and-return-early
behaviour via recorded `asyncio.sleep` calls, not wall-clock timing — 64
tests total, all passing, still no hardware needed.

**Explicitly not touched, per George's order of work:** Finding 014's
LMS-to-Spotify first-attempt race and Finding 013 §1's explicit-restart
approach — both stay reverted; this change is evaluated on its own before
either of those is revisited.

**Not yet hardware-verified.** Per George's order of work: deploy to
`gexis`, re-run the Bluetooth-churn pattern that broke Finding 013 §1's
fix (LMS playing → Spotify → rapid Bluetooth connect/disconnect ×5-10 →
back to LMS, ×3, watching for escalation or restart-rate-limit errors —
a failure rate is part of the finding, not a reason to change behaviour
until it's clean), then re-collect the LMS release-timing distribution
before this goes into a `stage-gexis` rebuild. Expected: normal LMS
handoff drops from ~3.2s to ~0.7s.

### Tenth session, 2026-09-11: George's four blockers — two root-caused and closed, one fixed, one blocked on evidence

George reflashed (new build, new SSH host key) and reported four blockers
that cannot be deferred. Full detail, measurements and scope in **Finding
018**; summary:

**Important context for anything measured this session:** the reflashed
image **predates Finding 016's polling fix** (`POLITE_POLL_INTERVAL`
absent from the installed `arbitration.py`), so the blockers were all
observed with the old blind 3.0s polite-grace sleep still live.

1. **LMS elapsed time jumps ahead then back — LMS's own behaviour, not
   ours.** Reproduced with a plain LMS pause/resume and *no arbitration
   involved at all*: paused at 157.69, waited 30s, and the first reading
   on resume was 186.93 (= position + away time), correcting to 158.33
   within 0.3s. The server's stored position never drifts while paused.
   All we control is how long the wrong value stays visible — it lasts
   until squeezelite can actually start, i.e. until the outgoing renderer
   releases. Shortening the release shortens the symptom; nothing in
   gexis-player can remove it.
2. **Spotify position resets — Finding 014's Mode A race, now measured
   end-to-end, and all three levers are closed.** LMS releases in 1.44s
   (n=4, tight); go-librespot attempts its ALSA open ~1s after
   `will_play`; it loses by ~0.4s and the retry reloads at position 0.
   Tested and ruled out this session: `-C 0` (squeezelite then *never*
   releases — 4/4, reverted, `-C 1` confirmed restored); an earlier
   acquisition signal (traced `/events` — `will_play` is the only event
   before the failed open); and nudging LMS to retry (no effect —
   squeezelite already recovers in ~0.96s on its own). **Needs George's
   decision, not another unilateral attempt.**
3. **Bluetooth first connect after reboot — not root-caused, evidence
   doesn't exist yet.** Every static cause ruled out (ordering
   `After=bluealsa` present, rfkill clear, phone paired *and* trusted,
   both gexis BT units enabled), and on the one available boot the first
   connect actually *succeeded* at the profile level. `journalctl
   --list-boots` shows a single boot because the card was just flashed —
   but `/var/log/journal` exists and `Storage=auto`, so logs persist from
   here on and the next reboot's attempt is capturable.
4. **Spotify's volume range smaller than Bluetooth's — root-caused,
   fixed, verified.** `VolumeBridge`'s blanket 750ms echo window
   discarded *every* incoming volume event after one of our own writes,
   so a fast slider drag lost everything after the first value,
   including the one the user released on. Measured: fast ramp to
   100/100 left the DAC at 226/240 (7.0dB low), reproducibly; the same
   ramp 1.5s apart reached 240/240. Both dummy controls lost their echo
   windows in the 2026-09-08 `DummyMixerBridge` fix — whose docstring
   describes this identical bug — leaving Spotify the only renderer that
   couldn't reach full scale. Replaced with value-matched suppression
   (drop exactly one echo carrying the value we wrote; anything
   different is genuine). **Verified on hardware:** fast ramp now
   reaches 240/240 (3/3), and the ratchet-to-zero regression was checked
   explicitly — a deliberate `amixer sset DAC 200` held at 200 across 16
   readings over 8s.

**Deployed live on `gexis` (hot-patch, not an image):** the blocker 4
volume fix and Finding 016's polling fix. Backups at `/tmp/volume.py.bak`
and `/tmp/arbitration.py.bak` on the device. Box left with all units
active, `NRestarts=0` everywhere, volume at a sane -13.5dB.

### Design input from George, 2026-09-11/12 — LMS power as the arbitration mechanism

> **DECIDED, 2026-09-12. Now written up as
> [ADR-0027](docs/decisions/0027-lms-power-as-arbitration-mechanism.md)** —
> George chose "`pause` + `power 0`, restore the remembered state". Read the ADR
> for the decision and Finding 018 for the evidence. The input below is kept as
> the record of how the decision was reached, including his own reasoning and
> the two proposals of his that measurement refuted. **Still no implementation
> code** — the ADR is written, the code is not.

Recorded verbatim in substance so it isn't lost. Evidence behind it is
Finding 018's third pass.

George's rules:

1. **A deactivated device in LMS stays deactivated until the user
   activates it again.** No automatic activation that isn't visible to
   the user. (His own 3-4s auto-reactivation proposal is withdrawn —
   measured to evict Spotify, see Finding 018.)
2. **This kills LMS as the default/base renderer.** There must be a state
   where *no* renderer holds the device because all of them are off. UX
   implications to be handled when the interface is designed.
3. While another renderer holds the device, the squeezelite client is
   powered off.
4. **Powering on IS the acquisition, not pressing play.** For consistency
   with Bluetooth (A2DP connect) and Spotify (device selected), the
   activation is what takes the device; play is a separate user intention
   afterwards. Playback on takeover continues from wherever LMS was.
5. **Do not track who deactivated the device.** What matters is the
   device's state at any moment, not whether the user or the system
   caused it — the system's power-off is itself user-triggered (a
   takeover). We must not silently re-activate what the user turned off,
   which rule 1 already guarantees.
6. Crash handling: George unsure whether his other answers change this.
   (They do — see the feedback note below.)
7. Bare power-on counts as an acquisition; docs need amending to say so.
8. Asked for a fuller explanation of the Bluetooth side.

**Claude's feedback, given the same day:** rules 1 and 5 are mutually
consistent — provenance tracking is unnecessary *precisely because* rule 1
means we never auto-activate, so there is no user action to accidentally
undo. Rule 4 is better than the version Claude proposed: it removes the
restart-from-0 problem at its source (the user activates rather than
pressing play against a powered-off player), makes LMS's row in
ADR-0010's acquisition table uniform with the other two renderers, and
should retire both the 0.4s acquisition debounce and the spurious-reclaim
class of bug, since a stray server-side `mode: play` would no longer be an
acquisition signal at all. Rule 6 largely dissolves: once "off" is a
legitimate, user-restorable state rather than a broken one, a crash while
the player is off leaves a valid state. Rule 2 is the largest change —
it retires the base-slot premise ADR-0010 is built on, so this likely
wants its own numbered ADR rather than an amendment to that one.

**Refinement from George, same conversation:** on activation the player
should be in whatever transport state the user left it in — playing if
they left it playing, paused if they left it paused — and since "in most
cases the player is paused," we should not trigger a play.

**Measured consequence (Finding 018):** a *paused* LMS holds no ALSA
device at all (`-C 1` closes it), so a takeover from a paused player is
already clean — first open succeeds, `active` fires, 0.93s. Blocker 2 only
ever manifests when LMS is **playing** at the moment of takeover. So "most
cases are paused" describes the cases that were never broken; the broken
case is always the playing one, which George's own rule says must come
back playing. LMS preserves transport state across a power cycle natively,
so the rule needs no bookkeeping — the open decision is only whether the
resume comes from LMS's own restore (leaves the broken case broken, 0-5s)
or from us replaying one remembered bit (0.07-0.17s).

**Verified since (Finding 018):** the CometD `playerstatus` push *does*
carry `power`, and a change triggers a push in ~0.52s — but squeezelite
attempts its ALSA open 58ms after power-on, so we cannot act first, and a
lost attempt costs up to 5s on an untunable retry tick.

**George's decision, 2026-09-12:** `pause` + `power 0` on release, restore
the remembered transport state on return — i.e. we issue the `play`
ourselves in the case where the player was left playing, so that
squeezelite's first ALSA attempt lands on a device that is already free
(0.07-0.17s) instead of 460ms before it is (0-5s). Written up as ADR-0027.

**What implementing it touches, for whoever picks this up:**

- `adapters/lms.py` — acquisition moves from `mode -> play` to `power -> 1`
  (the 0.4s debounce and its confirming RPC go away with it); `release()`
  becomes record-state → `pause` → `power 0`; a new step restores the
  recorded state once the supervisor confirms the release.
- `arbitration.py` — `Supervisor._active` currently treats `None` as "LMS is
  current" (`active` property returns `BASE_RENDERER`). That has to become a
  real tri-state: nobody / lms / other. `_release_with_ladder` on an empty
  slot is a no-op.
- `core/tests/` — the base-slot assumptions are baked into
  `test_arbitration.py` (`test_base_slot_is_lms_by_default`,
  `test_takeover_returns_to_lms_not_a_stack`, and `build()`'s fixture).
- ADR-0010's kill ladder for LMS stops being reachable in normal operation;
  leave it in place as the escalation safety net, but it should effectively
  never fire.

**Both remaining open items DEFERRED by George, 2026-09-12** — not
blocking implementation: whether powering off mid-playback is audible at
the cut, and whether blocker 1's residual 0.3-1.6s elapsed flicker needs
the seek re-anchor (the seek removes it entirely but makes LMS re-request
the stream, with its own possible artefact). Revisit only if either proves
audible or annoying in real use.

**Also noticed, not acted on:** squeezelite's `ExecStart` now carries
`-O hw:gexislmsvol -V Master -C 1 -n gexis` — the `-O hw:gexislmsvol -V
Master` part reflects the per-renderer dummy-mixer volume work (Finding
008 §3 / ADR-0018's amendment) already landing in `ExecStart` as shipped.
Looks consistent with that fix, but George hasn't specifically tested the
volume-coupling item as closed on this exact build — worth confirming
separately, not assumed done here.


## Closed next-actions: ADR-0027 and Phase 2c criteria 7-10

0. **~~Implement ADR-0027~~ — DONE, Phase 2d CLOSED 2026-09-12.** Built,
   flashed (`v0.2.1-51-g89dca15-dirty`), and verified on the image: 84 unit
   tests, the installed core diffed file-by-file against the branch HEAD,
   13/13 end-to-end, plus George's listening pass. Branch
   `phase-2d-lms-power`, **not yet merged** — see the branch note below.
   Blocker 3 (Bluetooth first connect) root-caused the same day and
   **closed by decision: no change** (ADR-0024). What remains is criteria
   7-10, item 1 below.

   *Historical note on what this item used to say:*
   and it is what unblocks everything below it. See the design-input section
   above for exactly which files it touches, and Finding 018 for the
   measurements. Sequence George asked for throughout: change it on `gexis`
   first, he confirms by ear, then it goes into a `stage-gexis` rebuild.
   Two things need his ear specifically: whether powering off mid-playback
   clicks, and whether blocker 1's residual 0.3-1.6s elapsed flicker is
   acceptable without the seek re-anchor.

   **Phase plan already updated for it (2026-09-12, George's decisions):**
   `docs/DEVELOPMENT.md` gains sub-phase **2d** (criteria 3-4 reworked —
   2b was verified against wording ADR-0027 invalidates, so it is reopened
   under a new number rather than having its history rewritten); criteria
   7-10 are flagged for re-running since Finding 015's numbers predate the
   new mechanism; criterion 3 is rewritten and its empty-base-slot deferral
   **answered**; criterion 4's LMS half is demoted to history while
   Bluetooth's exception stays live; criterion 10 now expects a per-pair
   answer. **Phase 3** must publish "no renderer" and per-renderer
   availability. **Phase 4 gains criteria 6 and 7** — a first-class
   nobody-holds-the-device screen, and **LMS activation from our own UI**,
   which George placed in Phase 4 rather than Phase 6 because without it
   the only route back to LMS is the phone app. That gap between ADR-0027
   shipping and Phase 4 shipping is a knowingly accepted interim
   regression, recorded under Phase 2.

   **Do not re-derive the closed routes.** Finding 018 records, with numbers,
   why each of these is dead: `-C 0` (squeezelite never releases), `stop`
   instead of `pause` (slower and inconsistent), an earlier acquisition signal
   (`will_play` is the only event before the failed open), `/player/resume`
   and `/player/play` (both leave `active` unfired), killing squeezelite
   (restart storms, reverted twice), holding LMS paused until the device frees
   (freezes the wrong elapsed value on screen), and powering the player back on
   mid-session (evicts the renderer that just took over).

1. **~~Phase 2c, criteria 7-10~~ — DONE. PHASE 2 IS CLOSED, 2026-09-12.**
   All ten criteria met on the flashed image `v0.2.1-51-g89dca15-dirty`:
   - **Criterion 7** (Finding 019): 24/24 genuinely contended rounds, zero
     violations. The old attack test had silently stopped contending under
     ADR-0027 and would have reported a false pass.
   - **Criteria 8/9** (Finding 020): n=33 LMS→Spotify (median **224.6 ms**)
     and n=27 Spotify→LMS (median **335.2 ms**), against Finding 015's
     1827.8 ms and 4170.9 ms — 8.1x and 12.4x. Zero product-side failures
     across 72 attempted rounds. Finding 020 supersedes Finding 015.
   - **Criterion 10**: transition screen shown by default, skipped only for
     a pair measured under 1s. Today that exempts same-rate LMS↔Spotify and
     nothing else.

   **Five deferrals are listed in `docs/DEVELOPMENT.md` under the Phase 2
   closure block** — read them before treating Phase 2 as complete in every
   sense. The cross-rate half of criterion 8 is **unmet**, not
   met-with-caveats.

   **Next phase is 3** (core state daemon), whose criterion 1 now has to
   publish "no renderer holds the device" and per-renderer availability —
   see ADR-0027.

   *Superseded wording follows:* Every number in Finding 015 predates the mechanism 2d
   replaced, so they are all stale: the LMS→Spotify handoff is now 0.7-0.9s
   against that finding's 1827.8ms median, and criterion 10's
   transition-screen answer is likely per-pair rather than global
   (LMS↔Spotify is fast now; Bluetooth→LMS is still gated by Bluetooth's
   own 2.5-2.9s release, which 2d does not touch).

   **Branch, to decide before starting:** 7-10 have to be measured against
   2d's behaviour, so the work sits on top of `phase-2d-lms-power`. Cleanest
   is a 2c branch cut from *that*, with the whole line merged back to
   `phase-2-arbitration` once 2c closes — one merge rather than two
   overlapping ones. Note `phase-2c-takeover` still exists, moved back to
   the last pre-ADR-0027 commit, and contains the Findings 013-018 work.

   *Superseded wording:* **Re-measure after ADR-0027 lands** — Finding 015's numbers were taken
   against the old mechanism, and the 0.7s LMS→Spotify handoff seen while
   testing ADR-0027 is far better than that finding's 1827.8ms median.
   PR #6 already merged and `phase-2c-takeover` already branched (see this
   file's own Phase 2c section above) - criterion 7 is passing.
   **Blocked again, both same-day fixes reverted after live regressions -
   see the standalone `docs/findings/phase2c-issues-overview.md` for a
   self-contained brief.** Finding 015's same-rate LMS↔Spotify numbers
   were collected while both fixes were live and are informative about
   real timing, but don't reflect what's actually shipping now that both
   are reverted - don't treat them as a final answer for criterion 9/10
   until a real fix exists and is re-measured. What's left, in order:
   - **Finding 014's Mode A race (LMS-to-Spotify, first attempt almost
     always loses)** - unresolved again. Needs a fix that completes
     Spotify's own Connect handshake, not just gets audio flowing -
     `/player/resume` is confirmed unsafe. Unchecked: whether go-librespot
     exposes any other local endpoint that does this properly.
   - **Finding 013 §1's restart-storm** - unresolved again. A same-day fix
     survived 35 scripted rounds but not real, sustained use with
     Bluetooth churn - a next attempt needs to be tested against *that*,
     not just a clean batch. **Finding 016's polling fix (2026-09-11) is
     the next thing to hardware-verify against exactly that load
     pattern** before deciding whether the restart-storm fix itself needs
     revisiting - it targets one plausible source of the storm's fuel (no
     margin on the polite rung), not the storm mechanism directly, and
     George asked to see what the storm does with real margin restored
     before touching Finding 013 §1 or Finding 014 again.
   - **Cross-rate LMS↔Spotify** - blocked on content, not mechanism: a
     full library scan (60,974 tracks) found zero non-44.1kHz content.
     George's call - add dedicated test content, or defer this leg.
   - **Blocker 3 (Bluetooth first connect) is ROOT-CAUSED, 2026-09-12** -
     the adapter is discoverable for only 180s after boot (BlueZ's
     `DiscoverableTimeout` default, never overridden in `main.conf`, while
     `bluetooth-setup.sh`'s own comment claims persistent discoverability).
     A reflash wipes the bond, so re-pairing is needed, and re-pairing needs
     discoverability that lapsed hours earlier. **Fix is one line and the
     mechanism is confirmed, but the decision is George's** - it widens
     ADR-0024's accepted exposure from 3 minutes per boot to continuous.
     See ADR-0024's amendment and Finding 018's blocker 3 section.
     **Untested prediction worth one cheap check:** a plain *reboot* should
     NOT show this, because the bond survives in `/var/lib/bluetooth`. If a
     reboot does fail, the root cause above is wrong.
   - **Bluetooth-involving pairs** - not attempted this round; paused when
     the two blockers above surfaced. `bluetoothctl connect` reconnects
     the profile but not reliably the actual audio stream (a harness
     limitation, not a product defect) - manual taps needed for real
     contested rounds, and needed three attempts to first connect after
     this reflash (stable afterward, not investigated further).
   - **Criterion 9/10**: on hold until the two blockers above are
     resolved for real and re-measured - Finding 015's numbers exist but
     are provisional, see above.
   - **Image rebuilt twice this session** - once with both fixes
     (superseded), then again with both reverted (current). The version
     tag on whatever's flashed tells you which - check before trusting
     which behaviour is live.



---

# Sessions 12-14 (2026-09-14 to 2026-09-16) — Phase 4 built and closed

Moved verbatim from `HANDOFF.md` when Phase 4 closed. The narrative here is
history: 4c-4f and settings are in `main`, flashed and checked on hardware.

## Start here

**A new image is built and needs flashing before anything else:**
`image/deploy/2026-09-14-gexis-player-v0.2.1-110-gc49c0a0-dirty.img`

It carries the Finding 022 fix. On first boot the panel should come up on its
own showing `http://127.0.0.1:8090/` — no console getty. **`gexis` currently
has its panel hand-pointed at a third-party test URL** (`/etc/gexis/kiosk.env`,
original kept at `.orig`); the reflash reverts that, so a loopback page is the
expected result, not a regression.

**Then: a PR closing this work**, which George wants before the UI designs
arrive. Two things worth doing first:

- **A cold build.** Every build this session used `CONTINUE=1`, which reuses
  the previous rootfs. That is exactly how the stale `default.target` survived
  and got caught by an assertion. `make clean && make image` (~40 min) is the
  only way to prove the stage is correct from nothing, and the PR's whole claim
  is that it is.
- **`playlistcontrol cmd:load album_id:<id>`** — still unverified, still the
  load-bearing assumption of ADR-0030's typed-library half. Needs George
  present; running it starts music.

**Build wart to fix, not blocking:** the copy-out took **3h45m** for 4.5GB on
the last build (12m02s of actual build, 14212s total). `make fetch-deploy` does
the same copy per-file in 44s. `pi-gen` accepts a `DEPLOY_DIR` override
(`build.sh:191`), so bind-mounting the host's `image/deploy` into the container
and pointing `DEPLOY_DIR` at it would remove the 4.5GB stream entirely and
halve disk use. Designed, not implemented.


**Image built (2026-09-15, cold):**
`image/deploy/2026-09-15-gexis-player-v0.2.1-133-gb94c31c-dirty.img` — 4c–4f plus
provisioning of `TIMEZONE` and `IDLE_URL`, **no settings** (built from the main
tree while settings work stayed in a worktree). First cold attempt was killed by
Claude Code's memory guard; the resume failed in stage1 (`raspi-config` deps)
on a rootfs the kill had left mid-apt — removing the container again fixed it.
Flash, then `make provision DEVICE=/dev/sdX` before first boot. **A reflash
drops the hand-installed settings increments** until they are redeployed or
built in.

**Settings (ADR-0035) on branch `phase-4-settings`:** increment 1 (registry,
API, responsive screen) passed George's phone check; increment 2 (idle
timeout, idle URL, both drawer settings wired) **passed his check too —
Phase 4 criterion 5 met**, so every Phase 4 criterion is met or withdrawn. Number/text editors are minimal and undesigned — Claude Design to
draw them.

**Phase 4 steps 4c–4f all passed George's panel pass (2026-09-15)**,
hand-installed on `gexis` and **not yet in an image**: a reflash loses them,
plus the device-only `idle_url` and the Europe/Berlin time zone. PRs #10–#13
are stacked (4c → 4d → 4e → 4f); merge in order. **Phase 4 criterion 5 is the
one left** — the settings surface on a phone, which needs the settings HTTP
API (none exists) and a port of `Settings.dc.html`.

**4e (volume) is deployed on `gexis`** (2026-09-15, branch `phase-4e-volume`,
stacked on 4d): Controls drawer from the now playing volume button, slider over
−45…0 dB shown as slider position, mute restoring the prior level
(ADR-0034). Previous core at `/opt/gexis-core.4d-backup`. **Passed George's
panel pass**, plus two port deviations he asked for — see DEVELOPMENT.md,
"Deviations the port keeps across exports". Only reachable from now playing — Home has no volume button yet.

**4d (idle screen) is deployed on `gexis`** (2026-09-15, branch
`phase-4d-idle`, stacked on `phase-4c-now-playing` / PR #10): `GET /idle`
reports George's page embeddable; `idle_url` added to `/etc/gexis/core.toml`
(backup `core.toml.4c-backup`); core copied into the venv's site-packages
(pip cannot build on the device — no hatchling), previous core at
`/opt/gexis-core.4c-backup`. Device time zone set to Europe/Berlin by hand —
lost on reflash. **4d passed George's panel pass (2026-09-15)**, tested with a 10 s timeout via `?idle_seconds=10` in `kiosk.env`, since restored to 5 minutes.

**4c (now playing) is built and hand-installed on `gexis`** (2026-09-15):
`ui/src/screens/NowPlaying.svelte`, ported from `design/now-playing.html`,
fonts bundled via fontsource. Previous UI kept at `/opt/gexis-ui.4b-backup`.
Rendered in all six design states against a mock feed on the dev machine;
**not yet looked at on the panel** — George's hardware pass is next. With no
renderer the panel shows a "Nothing playing" placeholder (`data-unwired="home"`)
until Home is built. `design/` is **not committed**: it holds two
third-party photos (sample album art, artist photo) and this repo is public —
George to decide. Design package corrections from George: **no format badge
(sample rate/codec) anywhere** — open whether that includes the Peppy screen
(ADR-0019's codec rule); the design's drifting clock is the **fallback** for
the idle URL not loading (ADR-0033). Source pill now pulses while playing.
**Second design export (2026-09-15):** Paused is shown
only by the play control — label and artwork dimming removed from the locked
source, and from the port. `design/source/` is locked: build from it, never
edit it; run `design/verify.html` over HTTP after any package change (35 pass,
3 fail — the export references `./assets/`, which this package lacks). The
export's CSS also omits the pill pulse that the source has; the port follows
the source. **No sample rate or codec anywhere, Peppy screen included**
(George) — ADR-0019's codec rule to be amended in Phase 5.

**2026-09-15, thirteenth session:** image flashed and boots cleanly (George).
PR #9 opened for this branch. **Phase 4 criteria 6 and 7 withdrawn** — no
back-to-music screen, no activate control; 4e is now volume only. The
phone is the only way to start LMS until Phase 7. Awaiting designs: both
`.dc.html` files resent in full each iteration into `design/`, plus PNGs and
change notes for the area that changed. **When no renderer is connected the
panel shows the Home screen** (George, 2026-09-15), a design screen made for
that state and **distinct from the idle screen**. The idle screen (external
URL) takes over after 5 minutes without activity; when it is dismissed, Home
returns. This changes ADR-0019, where "nothing playing" belonged to the idle
screen directly — **needs ADR-0033 before implementation**; open points were
put to George.

No code changed in the twelfth session. It was build-environment repair and four
decisions. Nothing is half-finished, and the working tree is clean apart from
`image/pi-gen` (the Makefile deleting `stage2/EXPORT_IMAGE`, which is normal).

**Do these, in this order:**

0. **ADR-0032 (2026-09-15): the panel renders everything, a remote browser
   renders only settings.** Same page both ways; the phone shows a subset.
   George's inversion of a Claude Design "split by capability" proposal, and
   better than it — under the split some functions would have been phone-only,
   and the phone exists only while the LAN does. With the panel holding
   everything, nothing is phone-only and the device stays self-sufficient by
   construction. **Only the settings screen is responsive**; every other screen
   stays a fixed 1280x800 artboard. Settings becomes one imported component
   measuring its own mount width (720px breakpoint), so a setting added once
   appears on both. All inventory rows render for now, `[N]`/`[?]` included —
   mock stage, will iterate. Row types deliberately not defined yet; the
   settings HTTP API will be built to whatever vocabulary the design settles
   on. **No settings endpoints exist yet** — `settings.py` has the SQLite store
   from Phase 3 but nothing exposes it over HTTP. That is the next backend
   task once the design lands.

1. ~~**Flash and verify `04-ui` on hardware.**~~ **DONE 2026-09-14 — two
   defects found and fixed, see [Finding 022](docs/findings/022-kiosk-never-started-target-and-tty.md).**
   The panel showed a console getty: `firstrun.sh` reaches `raspi-config
   do_boot_behaviour B1`, which reset `default.target` away from
   `graphical.target`; and `getty@tty1` held the VT, so `labwc` exited 0 with
   an empty journal. Fixed by binding the unit to `multi-user.target` and
   adding `Conflicts=getty@tty1.service`. **Verified on `gexis` by an
   unattended reboot** — kiosk active, getty stopped, seat0/tty1, UI served,
   1280x800. Everything downstream of the trigger worked first time, so
   `04-ui` itself is sound. **Still to do: rebuild the image carrying the fix
   and reflash**; the fix is proven on a running device, not in an image.
   *Original text:* The image is built and waiting:
   `image/deploy/2026-09-13-gexis-player-v0.2.1-98-gfec5067-dirty.img` (raw,
   straight into Imager). labwc, the `PAMName=login` seat, 1280x800 and the
   Chromium kiosk flags have **never run** — all written from documentation.
   This is the outstanding half of Phase 4b and needs no designs.
   `journalctl -u gexis-kiosk` first if the panel is black; the unit is
   `Restart=no` on purpose so a failure stays visible.
2. **Verify `playlistcontrol cmd:load album_id:<id>`** against LMS with George
   present. It is the load-bearing assumption of ADR-0030's typed-library half
   and was deliberately not executed — running it starts music unannounced.
3. **Then wait on George's `.dc.html` artboards plus static PNGs** for 4c
   onward.

**Awaiting George's confirmation** (the settings-inventory rule in `CLAUDE.md`
requires his sign-off before anything is appended to ADR-0022's inventory):
ADR-0031 adds no new setting — *Device name* and *Wi-Fi configuration* are both
already `[R]` — but it raises two candidates that are **not** in the inventory
and have **not** been added:

- **Return to setup mode deliberately** `[N]` — a way to reopen the access
  point without waiting for the automatic re-entry condition. Adjacent to the
  deferred *Factory reset* item.
- **Access point security** `[?]` — whether the WPA2-vs-open choice is fixed in
  the build or exposed. ADR-0031 recommends fixed WPA2, i.e. not a setting.

**Unverified claims made this session, do not treat as tested:** AP mode has
never been raised on this hardware (only `WIFI-PROPERTIES.AP: yes` was read);
`libraries` returned `{}`, indistinguishable from an unknown command; only the
top of the `radios` subtree was walked; and whether a hostname change reaches
Spotify Connect and Bluetooth without a reboot is unknown.



## Phase 7 was re-decided (2026-09-14) — ADR-0030

George challenged ADR-0020: *"why did we select slimbrowse and not build
everything based on LMS capabilities so that we are in control of what we
display?"* The challenge was right, and ADR-0020 turned out never to have
written the typed-query alternative up as a considered option.

**The local library is now our own screens over typed queries** (`albums`,
`artists`, `genres`, `titles`, …) — measured against his LMS 9.1.1: 4554
albums, 7292 artists, 60974 titles, all with structured fields rather than a
server-formatted label.

**SlimBrowse survives only for radio, entered at `["radios","menu:radio"]`
rather than `home`.** That is an entry-point choice, not a filter: LMS's own
settings node, `My Apps`, global search and Radio Paradise are not filtered out
— they are never reachable. Podcasts is the one id excluded by name. Nine items
remain. Both areas share one visual language from the provided designs.

**Verify before building on it:** `playlistcontrol cmd:load album_id:<id>` is
the load-bearing assumption of the typed half and has **not** been executed —
doing so would have started music on George's system unannounced. ADR-0030's
"Unverified" section lists it and three others.

Knock-on: ADR-0020's cross-cutting rule now has **no live case for its second
branch** ("exists but cannot be operated here, show it and say where") — both
motivating examples are retired. The rule is kept as a principle; judge future
cases on the reasoning, not the retired rows.

Also settled this session: **ADR-0029**, text fields editable on every surface,
no on-screen keyboard, and a focused field with no keyboard attached does
nothing — a knowingly accepted exception to ADR-0014.

**Credentials now have a phase — ADR-0031, Phase 10.** First boot with no
network raises a setup access point (NetworkManager AP mode; verified available
on `gexis` 2026-09-14, NM 1.52.1, `WIFI-PROPERTIES.AP: yes`, but **never
exercised**). The setup page is served by `gexis-core`, and the typing happens
**on the user's phone** — which is why the panel still needs no keyboard and
why this closes ADR-0022's blocker without reopening ADR-0029. It collects
Wi-Fi credentials *and* the device name (ADR-0022's single name: mDNS, Spotify,
Bluetooth). `firstrun.sh` pre-seeding is unchanged and wins when present, so
the development workflow is untouched. **Pull Phase 10 forward the moment a
device goes to someone who did not build it.**



## Where things stand

**Phase 4 is starting, and five decisions were taken before any code**
(George, 2026-09-12), recorded in
[ADR-0028](docs/decisions/0028-ui-serving-and-command-channel.md) and
`docs/DEVELOPMENT.md`'s amended Phase 4 criteria:

1. **`gexis-core`'s own aiohttp app serves the UI**, same process and origin
   as `/state`. Not a separate nginx/lighttpd.
2. **Commands are REST POSTs**, not WebSocket messages. The socket stays
   publish-only. Decided chiefly because errors ("LMS unreachable") need
   somewhere to go, `/state`'s already-verified shape stays untouched, and
   `curl` is how this project actually debugs — a socket isn't curl-able.
3. **Volume is in Phase 4** (new criterion 8), displayed as a percentage of
   the hardware control. Not a transport control; transport proper stays
   Phase 6. Caveat recorded in the criterion: our percentage won't always
   match a phone's, Bluetooth especially (Findings 006/009/010). **Still
   open:** how the slider's *travel* maps onto a dB-linear scale, where
   raw-linear would cram every usable level into the top quarter.
4. **Criterion 6 reframed, not dropped.** George's objection was that a user
   doesn't need "why nobody holds the device" explained, because browse +
   tap-an-album already works via LMS's own auto-power-on. Correct — so the
   screen's job changed from explaining the state to offering the one action
   that gets back to music, and it is **expected to retire when Phase 7's
   browse lands**. It survives only because browse is three phases away and
   the activate control needs a host that isn't the user's own idle URL.
5. **Bluetooth's sample-rate field carries the codec** on now playing too
   (extending ADR-0019's Peppy-screen rule), so the codec must now be
   captured — new adapter work, but `MediaTransport1` already being watched
   makes it an extension rather than new plumbing.

Also George's correction, folded into criterion 3: **missing metadata is
often transient.** Bluetooth has no artwork, but artist/album/title are
enough for Phase 8's enrichment to find cover art and lyrics — so the
layout must reserve artwork space and not reflow when it arrives later
(ARCHITECTURE.md already required exactly this).

Build order agreed: **4a** model extensions (no UI) → **4b** serving and
kiosk → **4c** now playing → **4d** idle → **4e** back-to-music screen,
activate, volume → **4f** transition state. Table in `DEVELOPMENT.md`.

**4a is done** (194 unit tests, hand-installed and verified on `gexis`).
The payload now also carries `transport`, `codec`, `handoff`, `volume`
and `handoff_exempt_pairs`, and the command surface exists:

- `POST /volume {"percent": 55}` moved the real mixer to `132 [55%]
  [-54.00dB]`, with ALSA's own percent readout agreeing with ours.
- LMS deactivated from the server side published `active: null` with
  metadata blanked; `POST /renderer/lms/activate` then returned 200 and
  LMS came back — **the first `power 1` this project has ever sent**, and
  it deliberately fires no acquisition of its own, letting the existing
  CometD watch see the change so there is one acquisition path rather
  than two that can disagree.
- `409` for activating Spotify (declares no such control), `404` for an
  unknown renderer, `400` for a malformed volume body — all confirmed
  with `curl`, which is exactly why ADR-0028 chose REST.

**Not yet seen on real hardware: the handoff pair.** It is unit-tested,
including the case where the release ladder raises (cleared in a
`finally`, because a transition screen stuck on forever is the
unaccountable state ADR-0010 forbids) — but observing it live needs a
real takeover, which needs a phone. Note LMS↔Spotify is on the exempt
list anyway, so the visibly interesting case is a Bluetooth pair.

**Image rebuilt and verified, 2026-09-12** —
`2026-09-12-gexis-player-v0.2.1-88-g4cf667d-dirty` (34m54s, cold build
after a `make clean`). First image containing Phase 3, and the first
with the moved alsa pin: the manifest shows `libasound2t64` at
`1.2.14-1+rpt1+deb13u1` with the **`hi`** flag (held *and* installed),
and `libasound2-data` at the same version, so the dev/runtime mismatch
that existed in the failing run is gone. **It predates 4a** — the
version string names commit `4cf667d`, the pin fix; everything from
ADR-0028 onward has only been hand-installed.

**Phase 3 (core state daemon) is closed — all six criteria met.** Built and
hardware-verified on `gexis`, `phase-3-core-daemon`. Two real defects
found live during criterion 1's verification (Bluetooth's D-Bus interface
bug, the Spotify/Bluetooth relinquish() oversight) were fixed and
re-confirmed the same session — full detail further down this file.
Criterion 2 (adapters declaring capabilities, ADR-0013) followed
immediately after: `Capabilities` derived from the three built-ins'
actual, already-verified behaviour (audio connection, named acquisition
events, which skin fields each can supply), deliberately leaving
`controls` empty since no adapter can act on a user's command yet and
Phase 6 is where that becomes real. Published as a new field in the same
WebSocket payload; confirmed correct on `gexis`.

**Criterion 3 ("no special casing") raised a real scope fork, resolved by
George before any code:** ADR-0016 describes plugins as separate
processes with an IPC contract, which the three built-ins are not — a
full restructure into that model is a much bigger undertaking than
criterion 2 was. Found by grep first, not guessed: real, existing
renderer-name branching already in the codebase (`renderer_volume.py`'s
`MANAGED_RENDERERS` tuple, `volume.py`'s `if renderer == "spotify"`,
`__main__.py`'s by-name construction of two `DummyMixerBridge` instances
and one `VolumeBridge`). **George's call: remove that hardcoded
branching, keep the built-ins in-process** — the separate-process
question stays open for whenever Qobuz Connect (or another real plugin)
needs it. Fixed by extending `Capabilities` with `volume_managed`,
`volume_mechanism` (`DUMMY_MIXER`/`SOFTWARE_API`), and
`dummy_mixer_card`, so `__main__.py`'s wiring derives everything from
each adapter's own declaration. Verified on `gexis`: clean restart,
restore-on-acquire and the `DummyMixerBridge` mirror path both produced
the same values as before the refactor.

**Criterion 4 (moOde-compatible metadata file) researched from moOde's
own source before writing anything**, not assumed: `moode-player/moode`'s
`worker.php` (`updExtMetaFile()`) confirms `/var/local/www/
currentsong.txt` is plain `key=value` lines, atomically written (`.tmp` +
rename + `chmod 0666`) — not JSON, despite a forum thread and some UI
docs describing a JSON shape elsewhere in moOde's own stack. Its closest
analog to our architecture (the "external renderer active" branch — none
of our three sources is moOde's own local MPD library playback) writes
`file`/`artist`/`album`/`title`/`coverurl` plus `encoded`/`bitrate`/
`outrate`. **George's decision, presented with the exact gap named: only
the fields the model already has.** `encoded`/`bitrate` need codec/bit-
depth info nothing in this codebase tracks (only `sample_rate` in Hz);
`outrate` needs live ALSA hw_params, which nothing queries yet either.
Built `metadata_file.py`, wired as a plain `StateStore` subscriber
alongside `StateServer`, with its own change-dedup (moOde's own writer
compares before writing too — SD card wear). Renderer labels
("Squeezelite Active", "Spotify Active", "Bluetooth Active") are moOde's
own vocabulary verbatim. **Verified on `gexis`**: real file at the
expected path, `0666` permissions, correct live content against a
playing LMS track.

**Criterion 5 (SQLite config store) built as generic, currently-empty
infrastructure** - a key-value store (`settings.py`, JSON-encoded values,
one table so a future setting never needs a schema migration) for
ADR-0022's settings inventory, none of which has a UI to change it before
Phase 4 exists. Deliberately not migrating any existing `Config`/TOML
value (e.g. `boot_volume_steps`) into it - that would change where an
already-verified, hardware-tested value lives for no criterion-5 reason,
and stays a live option for whenever a real settings UI needs it.
Wired into `__main__.py` so the DB and schema are exercised for real on
the image. **Verified on `gexis`**: a value set before a service restart
read back correctly after one (`sqlite3` isn't on the image to inspect
the file directly - verified through `SettingsStore` itself instead).

**Criterion 6 (LMS track-change latency) measured and closed the same
session.** One script, run on `gexis` itself (not from a separate
machine, to avoid adding a network hop the real system doesn't have —
this project's own "wrong-host" lesson), alternating `playlist play`
between two distinct local library tracks so every round is an
unambiguous change, T0 at the JSON-RPC call and T1 at the first WebSocket
frame carrying the new track. **20/20 rounds, median 699.5 ms** (min
644.0, max 787.3 — tight, unimodal, no outliers). Recorded as
[Finding 021](docs/findings/021-criterion6-lms-track-change-latency.md).
No numeric bound for "bounded" exists anywhere in this project's own
records, so the finding reports the distribution as the record rather
than asserting a pass/fail line against a number nobody wrote down.

**PHASE 3 CLOSED, 2026-09-12.** All six criteria met on
`phase-3-core-daemon`, hand-installed and verified on `gexis` throughout
(not yet baked into a rebuilt image — see the hand-install note further
up this file). Two live defects found and fixed during verification
(Bluetooth's D-Bus interface bug; the Spotify/Bluetooth `relinquish()`
oversight), both re-confirmed. **Not yet done:** an actual image rebuild
containing this phase's code (everything so far has been the hand-install
loop over SSH), and merging `phase-3-core-daemon` toward `main` once
George decides it's ready. **Next: Phase 4** (UI shell, idle screen, now
playing — display-only, plus LMS activation).

Before writing any code for criterion 1, George was asked what "availability"
(criterion 1's per-renderer field, alongside "no renderer holds the
device") should actually mean for the UI, since Phase 3 itself ships no UI
and the answer only matters through what Phase 4 needs. **George's
decision: "backend reachable"** - not whether a renderer has a live
session - since only LMS ever gets an "activate" control from our own UI
(Phase 4); Spotify/Bluetooth availability only ever feeds a status line,
and richer session-awareness for them was deliberately not built ahead of
a criterion that would use it. Recorded in `model.py`'s module docstring.

Built this session, all unit-tested (no hardware) and passing (124 tests):

- **`core/src/gexis_core/model.py`** - `TrackMetadata` (ADR-0014's seven
  skin fields plus position/duration, `remaining_time` derived and clamped
  to never go negative) and `PlaybackState` (active renderer or nobody,
  per-renderer `available`, the active renderer's metadata or a blank
  placeholder when nobody holds the device).
- **`core/src/gexis_core/state.py`** - `StateStore`, the aggregator: the
  supervisor's `active` changes and each adapter's own metadata/
  availability reports come in here, and subscribers (the WebSocket
  server) are notified only when the combined, published state actually
  changes - a metadata push from a renderer that isn't active is recorded
  (so becoming active has something to show immediately) but does not
  broadcast.
- **`core/src/gexis_core/wsserver.py`** - `StateServer`, an `aiohttp.web`
  WebSocket endpoint at `/state` (no new dependency - aiohttp is already
  pinned). Push, not poll: a client gets the current snapshot on connect,
  then a fresh payload only when the state changes. Tested with a real
  `aiohttp` WebSocket client via `aiohttp.test_utils`, per Phase 3's own
  stated testing approach.
- **`arbitration.py`** gained `Supervisor(..., on_active_change=...)`,
  fired from `acquire`/`relinquish` after `_active` is already updated -
  this is what lets `state.py` reflect a takeover the instant it happens
  rather than on a poll.
- **Each adapter** (`lms.py`, `spotify.py`, `bluetooth.py`) gained
  `on_metadata_change`/`on_availability_change` hooks, matching the
  existing `on_volume_change` idiom rather than changing the abstract
  `Adapter` contract - that formalisation is criterion 2's job, not this
  one's. Field mappings sourced from each renderer's own docs, not
  assumed:
  - **LMS**: JSON-RPC `status` query, requesting `tags:aldcT` so pushed
    frames carry metadata, not just power. Per-song fields
    (title/artist/album/coverid/samplerate) live inside `playlist_loop[0]`
    in the JSON-RPC response, not at the top level - confirmed against
    community JSON-RPC examples (LMS-CLI.md itself only documents the raw
    telnet tagged-parameter format, which flattens differently). **Two
    things flagged as not yet hardware-verified**: the `playlist_loop`
    nesting itself, and tag `T`'s unit - LMS-CLI.md's own table says
    "samplerate, in KHz" but its own worked example returns a raw Hz value
    (44100) for 44.1kHz content: implemented as Hz, matching the doc's own
    example over its own prose, but not checked against `gexis`'s real LMS
    server.
  - **Spotify**: go-librespot's `/events` "metadata" and "seek" events, per
    API.md (fetched from the upstream repo, not assumed) - "seek" carries
    only position/duration, so it merges onto the last "metadata" event
    rather than reporting a mostly-blank update.
  - **Bluetooth**: BlueZ `MediaPlayer1`'s `Track` dict and `Position`
    property (org.bluez.MediaPlayer.rst), read once from the
    `ObjectManager` snapshot when the player appears and kept current via
    `PropertiesChanged`. No artwork or sample rate - matches ADR-0014's
    "Bluetooth supplies no artwork" expectation; the interface genuinely
    has no such fields, not an omission here. **Not yet hardware-verified**
    against a real phone connection - the `PropertiesChanged` handler's
    double-unwrap (a dict-valued D-Bus property nests one Variant level
    deeper than a scalar one) is inferred from dbus_next's documented
    behaviour, consistent with `bluetooth_trust.py`'s existing
    `.value`-unwrapping idiom, but not observed on a live signal yet.
- **`__main__.py`/`config.py`**: `StateStore`/`StateServer` wired in,
  `state_host`/`state_port` (default `0.0.0.0:8090`) added to `Config`.

**Update, same session: hand-installed on `gexis` and LMS metadata verified
live, on George's explicit instruction.** This resolves - for this
instance, not as a standing policy - the "develop-on-hardware workflow
inversion" question flagged above as discussed-but-undecided: George asked
directly for the code to be installed on `gexis` and checked against
`ws://gexis:8090/state`, rather than waiting for a full image rebuild.
Installed via `pip install --no-deps` from a rsynced copy of `core/` into
the existing `/opt/gexis-core/venv` (not yet baked into `stage-gexis` or a
rebuilt image - this is a hand-install for testing, same shape as the
config/systemd-file loop already documented, now extended to the Python
core for the first time). `gexis-core.service` restarted cleanly; journal
shows a clean startup, all three adapters reporting `available: true`,
`wsserver: listening on ws://0.0.0.0:8090/state`.

**Both flagged-unverified LMS mappings are now confirmed correct against
the real server:**
- `playlist_loop[0]` nesting - confirmed. A live query showed title/
  artist/album/coverid exactly where expected, and end-to-end through the
  WebSocket for a real local library track (Snow Patrol, "Eyes Open") -
  title, artist, album, artwork URL, position, duration, remaining_time
  all correct.
- Sample rate is Hz, not kHz - confirmed. `tracks` query on three library
  files all returned `"samplerate": "44100"` (a string, `int()` handles
  it fine) for 44.1kHz content - LMS-CLI.md's "in KHz" claim is simply
  wrong, as suspected from its own contradicting example.
- **New, incidental finding while testing:** the track playing at the
  time was a remote radio stream (`remote: 1`) - confirmed the `remote`
  branch's `current_title` fallback works correctly on live data
  ("Backstreet Boys - Anywhere for You"), and that remote items report no
  `samplerate` at all (not a bug - LMS has nothing to report for a stream
  it hasn't decoded). `remoteMeta` (a field not previously known about)
  duplicates title/artist/album/coverid for remote items - not used, since
  `playlist_loop`/`current_title` already covered it, but worth knowing it
  exists.

**Caused a live playback interruption while testing:** a `playlist play`
JSON-RPC call was issued directly against the real "gexis" LMS player to
get a local-file track queued for the sample-rate check, interrupting
whatever radio stream was playing at the time. Flagging plainly rather
than burying it - George's own player state was changed mid-test.

**Still not verified:** Spotify and Bluetooth metadata (both need a real
phone) and a genuinely external WebSocket client connection (all checks
above ran a client on `gexis` itself against `127.0.0.1:8090` or were
piped through SSH) - George's own next step, watching
`ws://gexis:8090/state` from his own machine while using the phone app.

**Bug found and fixed live, same session: the state WebSocket was
emitting a fresh payload roughly once a second regardless of real
activity.** George spotted it immediately watching the raw browser
console output. Cause: `_watch`'s CometD subscribe request used
`subscribe:1`, and LMS-CLI.md's own wording for that parameter is a
heartbeat interval in seconds ("the interval between automatic
generations in case nothing happened"), not an on/off flag - it was
already in the code before this session, harmless while the only thing
read from each push was `power`, but once metadata (including a ticking
`time` field) started flowing to the WebSocket, the heartbeat alone
produced a new payload every second independent of any genuine change.
Fixed: `subscribe:0`, which keeps push-on-real-change (power, volume,
track load) and drops only the unconditional resend - confirmed on
`gexis`, one message in an 8-second window with LMS playing, against one
every ~1s before. Also added metadata equality dedup to
`StateStore.set_metadata` on its own merits, though the `subscribe:0` fix
is what actually stopped this specific spam (a playing track's `time`
field genuinely differs on every real push, so dedup alone wouldn't have
silenced it).

**George then ran a real round of Bluetooth/Spotify/LMS testing against
the WebSocket and reported three findings - two real defects, one already-
known behaviour:**

1. **Bluetooth reported no metadata at all**, tried from Spotify and
   Plexamp on his phone. Root cause, confirmed by introspecting BlueZ
   directly on `gexis`: `MediaPlayer1`'s own proxy interface defines no
   signals of its own (empty `signals` list), so dbus_next generates no
   `on_properties_changed` for it - the journal showed
   `AttributeError("'ProxyInterface' object has no attribute
   'on_properties_changed'")` every single time a `MediaPlayer1` appeared.
   `PropertiesChanged` belongs to the generic
   `org.freedesktop.DBus.Properties` interface instead - matches
   `bluetooth_trust.py`'s own existing idiom, just for a signal instead of
   a method call. Fixed. Also extracted `on_interfaces_added`/
   `on_interfaces_removed` from closures into bound methods
   (`_handle_interfaces_added`/`_handle_interfaces_removed`) purely for
   testability - the closure shape is exactly how this bug shipped
   unnoticed, since nothing exercised it without real D-Bus. New fake-bus
   regression tests cover the actual `get_interface`/
   `on_properties_changed` call chain now.
2. **Stale data after disconnecting from a renderer, with nothing else
   taking over.** George: "I clearly disconnected from Spotify and was
   still seeing the old metadata... I think this was an oversight in the
   previous work." Confirmed by inspection, not just by his report:
   `on_release` was wired for LMS's own deactivation only -
   `SpotifyAdapter`/`BluetoothAdapter`'s own `run()` docstrings literally
   said "not wired up... out of ADR-0027's scope" verbatim in both files.
   Neither adapter ever told the supervisor "nobody holds it now" on a
   real disconnect, so `active` stayed pointed at whichever one was last
   used indefinitely. **George's call: this was an oversight, not a
   deliberate deferral - fix it.** Fixed both: `SpotifyAdapter` calls
   `on_release()` on go-librespot's own `"inactive"` event; `BluetoothAdapter`
   calls it when its `MediaPlayer1` disappears. Both call it
   unconditionally and safely - `Supervisor.relinquish()` already ignores
   a release from a renderer that isn't currently active, which is what
   makes the echo of our own takeover-driven release a no-op (the same
   mechanism LMS already relied on).
3. **Two consecutive metadata writes for the same song on an LMS
   takeover** - not a bug. The logs show exactly why:
   `lms: position was 0.0s, seeked back to the 35.5s it was released at`.
   LMS's own auto-power-on restarts the track from zero, and ADR-0027's
   resume logic then corrects it with a seek - two genuinely different
   real position values, both correctly published in quick succession.
   This is the same "residual elapsed flicker" ADR-0027's own Open section
   already names and defers ("issuing the `play` re-introduces LMS's
   stale-anchor jump for 0.3-1.6s before it corrects... decide after
   hearing the fix without it") - just newly visible through the WebSocket
   instead of only as an on-screen glitch. No change made; revisit only if
   that deferral itself gets revisited.

All three fixes deployed to `gexis` (same hand-install-over-SSH loop) and
confirmed starting cleanly. **George re-tested and confirmed both fixes
work**: Bluetooth now reports real metadata, and disconnecting from
Spotify/Bluetooth with nothing else taking over correctly returns `active`
to `null` with metadata blanked.

**Phase 3 criterion 1 is CLOSED, 2026-09-12** — see `docs/DEVELOPMENT.md`
for the full acceptance note. All three renderers' metadata, availability,
and "no renderer holds the device" verified on `gexis` against a real
WebSocket client, by George.

---

**Phase 0 is merged** (PR #1, into `main`). All seven acceptance criteria
passed, hardware-verified on `gexis`. Build cost is known: a full
`make image` is ~37-40 minutes on this dev machine under Docker + QEMU
emulation — rebuild-per-iteration is viable for Phase 2 onward, not just
in principle but measured.

**Phase 1 is absorbed into Phase 2** — decided and acted on, but the
`docs/DEVELOPMENT.md` change recording it is **PR #2, still open**, not
on `main` yet. The takeover gap has to be measured on the image, not a
hand-built machine; its three criteria are Phase 2 criteria 8-10.

**Phase 2a (renderer packaging, criteria 1-2) is done and closed** —
merged from `phase-2a-renderers` into `phase-2-arbitration`, its home
phase branch (neither has a PR open yet against `main`). squeezelite,
go-librespot and bluealsa-aplay are packaged
into `stage-gexis` as systemd units. Two hardware-found defects are fixed,
committed, and **reverified on hardware** on `gexis`: `pi` had no
sudo at all (shipped `/etc/sudoers.d/010_pi-nopasswd` directly — verified
empirically that stock Raspberry Pi OS Lite never ships it either, since
this image's `firstrun.sh` replaces the flow that would normally create
it; `sudo -n true` now succeeds on the flashed card), and go-librespot's
`ExecStart` had `-config_dir` (one dash; its CLI parses `-c` as a
distinct short flag, so this got parsed as `-c onfig_dir`) instead of
`--config_dir` (`go-librespot.service` now starts). Both blockers from
that hardware pass are closed. Also verified: all four units
(squeezelite, go-librespot, bluealsa, bluealsa-aplay) enabled and
active, squeezelite `NRestarts=0`; `speaker-test -D output` plays
audibly (criterion 4); `output.conf` has no `type plug`, no card index,
and has `ctl.output` (criterion 5); `libasound2t64` is
`1.2.14-1+rpt1` and held per `apt-mark showhold` (criterion 6);
squeezelite's `ExecStartPre` mixer check is present and passes.

**Phase 2's sub-phase mapping is confirmed as three-way** (2a criteria
1-2, 2b criteria 3-6, 2c criteria 7-10 — recorded in
`docs/DEVELOPMENT.md`). A four-way split was discussed and approved in
an earlier chat, but never written down anywhere, and by the time that
was noticed nobody had the record — it is **unrecoverable, not
withheld**. The three-way split is the version of record; if a fourth
sub-PR resurfaces from memory later, it does not override this — this
note exists so that isn't mistaken for a new discrepancy.

**Criterion 1 is now fully confirmed** (was partial). All three
renderers verified writing to `"output"`, each checked at its own
location, on a fresh boot (14:31:54) of a rebuilt-and-reflashed image:
squeezelite passes `-o output` in `ExecStart`; bluealsa-aplay has a
drop-in override at
`/etc/systemd/system/bluealsa-aplay.service.d/override.conf` that
clears the shipped `ExecStart` and sets `--pcm=output` — the packaged
default was `--pcm=default`, which would have played through whatever
`"default"` resolved to while the unit still looked healthy; go-librespot
has `audio_device: output` with `audio_backend: alsa` in
`/var/lib/go-librespot/config.yml` — not in the unit, which only passes
`--config_dir`, so this one is a two-place check (unit + config). Both
criteria 1 and 2 are met on the current build.

**The mixer-check journal-logging fix (`6ee6d6f`) is now verified on a
real boot**, not just an interactive shell: the success line appears in
`journalctl -u squeezelite -b`, attributed to
`squeezelite-mixer-check.sh[848]`, between systemd's `Starting` and
`Started`. This was the one outstanding piece of that commit — closed.

The sudoers fix's `visudo -cf` validation (`stage-gexis/01-firstboot/01-run.sh`)
was reviewed on a concern that it might skip validation if `visudo` is
absent on the pi-gen build host. Checked, not assumed: `on_chroot` (
`pi-gen/scripts/common:82-108`) runs the check via `capsh --chroot=...`
*inside the target rootfs*, not on the host, so host-side `visudo`
availability is irrelevant. That rootfs already has `sudo`/`visudo`
installed by `stage2/01-sys-tweaks/00-packages` (an earlier stage), and if
it somehow didn't, `capsh`'s non-zero exit would propagate through
`on_chroot`'s return code and the script's `exit 1` — fails closed, no
unvalidated sudoers file can ship. No host-side `sudo` package install
needed; none was made.

**Docker access on `C3PO` is resolved** — the `docker` group membership
picked up after George's terminal restart, and `make image` has since
built successfully (one retry needed: the first attempt failed at
`export-image`'s `losetup` step with `mknod: invalid minor device
number '/dev/loop0 (lost)'`, a transient loop-device race, not a code
issue — `make clean` to drop the leftover `pigen_work` container and
rerunning `make image` succeeded, 40m59s).

**`squeezelite-mixer-check.sh` no longer execs `amixer`** (`6ee6d6f`,
pushed to `phase-2a-renderers`). A successful check now logs a positive
line; the failure path dumps `amixer -D output scontrols` so a misnamed
control and an absent card are distinguishable. Previously a pass
produced no journal output at all, so a boot where the assertion ran and
a boot where it was never wired up looked identical in
`journalctl -u squeezelite -b`. Verified on the rebuilt image (see
criterion 1 note above).

**`go-librespot-config.yml`'s comment was fixed** (`210f7e7`): it said
the unit "passes `-config_dir`" (single dash) — the exact broken form
that cost a hardware round-trip earlier. No functional effect; it would
have misled whoever next debugged that file. The two occurrences in
`go-librespot.service` are correct and untouched (one of them quotes
the broken form deliberately, as part of explaining the fix).

**Branch divergence found and closed.** `make provision DEVICE=/dev/sdb`
failed with "No rule to make target 'provision'" — `HANDOFF.md`
documented the target, but the Makefile on `phase-2a-renderers` only
had `image:` and `clean:`. Cause: `e715344` ("Add make provision") is
on `main` via PR #3 (2026-09-05 20:36); the phase-branch line
(`phase1-absorbed-into-phase2` → `phase-2-arbitration` →
`phase-2a-renderers`) was cut before that and never took it back —
exactly two commits diverged (`e715344` and its merge `5e4be7d`), and
PRs #4/#5 are still open so haven't reached `main` either. Same shape as
the credential-exposure defect above, with a twist: PR #3's gitignore
rule *was* back-ported to the phase branches, but the rest of PR #3 (the
`provision` target, `provision.env.example`, the `image/README.md`
content) was not — the credential half got backported, the functional
half didn't. Resolved by merging `main` into `phase-2a-renderers`
(`514a6ff`) rather than cherry-picking, so the branches converge instead
of drifting further — auto-merged cleanly (`Makefile`,
`image/README.md`), no conflicts. `./test-gitignored-credentials.sh`
passes on the branch. Provisioning then ran and the flash booted with
SSH access.

**New concern, Phase 5, not tested — only inferred from the unit file:**
the shipped `bluealsa-aplay.service` runs `User=root` with
`PrivateTmp=true`, `ProtectSystem=strict`,
`DevicePolicy=closed` + `DeviceAllow=char-alsa rw`. `PrivateTmp` gives
the unit its own `/tmp` namespace; the peppyalsa FIFOs live at
`/tmp/peppymeter` and `/tmp/peppyspectrum`, so when Bluetooth is the
active renderer, its scope writes would land somewhere the
visualisation service can't see. This does *not* explain the meter-FIFO
finding below (that was `speaker-test` as `pi`, unaffected by this
unit's sandboxing) — it's a second, independent Phase 5 problem.

**`docs/DEVELOPMENT.md` on `main` is behind.** It doesn't yet show Phase
1's absorption, Phase 2's criteria 8-10, the tier-3-moves-to-`gexis`
change, or criterion 3's root-access amendment (a reachable SSH shell
with no sudo access is a Phase 0 gap found on hardware, same shape as the
provisioning-credentials gitignore defect below — criterion met literally,
intent unchecked). All of that exists on `phase1-absorbed-into-phase2`
(PR #2) and/or `phase-2a-renderers`. Read the branch, not just `main`, for
the current criteria.

**A live credential-exposure defect was found and fixed across every
affected branch.** `image/provision.local.env` (real SSH key, real Wi-Fi
password) was untracked and *not* gitignored on `phase-2a-renderers` and
three other branches — the ignore rule merged into `main` via PR #3, but
those branches were cut before that merge and never got it back. Fixed on
all affected branches directly. **PR #4** (open) adds a standing
regression test to `main`. **PR #5** (open) adds `docs/LESSONS.md`, naming
the general "verification ran against the wrong reality" pattern this and
two earlier incidents share.

**New defect found on `gexis`, not blocking Phase 2: the peppyalsa meter
FIFO doesn't write.** `/tmp/peppyspectrum` carries data during playback;
`/tmp/peppymeter` does not. Scope: single reader, single stream
(`speaker-test` sine 440 Hz, 48 kHz S16_LE), two runs, read as `pi`, ~8s
window opened before playback — not decisive on its own. Established:
the scope loads and attaches (`libpeppyalsa.so` symlink resolves,
spectrum FIFO writes, no scope-related errors in alsa-lib output);
`meter_show` controls console display only, not FIFO writing (set to 1,
ASCII level bars appear on the terminal and the FIFO stays silent, so
the meter path computes levels — only the FIFO write is missing); both
FIFOs exist as named pipes, `pi:audio`, created at boot (11:11), which
suggests something other than peppyalsa creates them. Unchecked
candidates, none eliminated: peppyalsa's open mode for the meter FIFO
vs. the spectrum FIFO; pre-existing FIFOs with unexpected ownership/mode
affecting behaviour; a meter-side option missing from `output.conf`
(the spectrum block has `spectrum_size`, `logarithmic_amplitude`,
`smoothing_factor`, `window`; the meter side has only `meter`,
`meter_max`, `meter_show`); `decay_ms 400` interacting with the write
path; a build variant with the meter FIFO write compiled out. Every
remaining candidate needs peppyalsa's source — stopped here because
further permutation on the box costs more than reading the code. This
is Phase 5 input, already on `docs/ARCHITECTURE.md`'s open-questions
list as "the peppyalsa FIFO byte format (blocks the visualisation
service)." Not written up as a finding yet — exists only here.

**First data on the FIFO format** (from the spectrum FIFO, which does
write): 64 bytes of one frame, fixed-width 4-byte groups, low byte
first (32-bit LE inferred from the pattern, not confirmed against
source). Values decoded 5, 16, 50, 62, 64, 56, 34, 0, 2, then zeros —
consistent with `spectrum_size 30` and `spectrum_max 100` in
`output.conf`; consistent is not confirmed.

`gexis`'s state as of this pass: the `meter_show 1` exploration was
reverted, config matches the shipped image again, no other hand-edits.

**Develop-on-hardware workflow inversion: discussed with George, no
decision yet.** Would change `docs/DEVELOPMENT.md`'s working contract,
so by its own stop-and-ask rules it wants an ADR before implementation.

**Build self-identification gap.** Nothing on the running system
identifies which build it is — checked `/boot/firmware/` and
`/etc/gexis*` only, no manifest, no version file, no marker (doesn't
establish absence everywhere, just that those are the two obvious
places). Criterion 7 says the manifest ships alongside the `.img`, i.e.
on `C3PO`. But `docs/DEVELOPMENT.md`'s tier-3 rule has the runner assert
its environment against "what the image build's own manifest recorded"
— and the runner is `gexis`, where the manifest isn't reachable. Needs
either the manifest shipped onto the image or a fetch path. **George's
call** whether that's a criterion 7 amendment.

**Method note, candidate `docs/LESSONS.md` instance:** a command run on
`C3PO` instead of `gexis` produced a false finding (`pcm.output` not
resolving), later retracted — the tell was `speaker-test` 1.2.16 on
`C3PO` vs. 1.2.14 on `gexis`. The wrong-host risk is structural to
pasting command blocks between machines, not a one-off slip — same
"verification ran against the wrong reality" shape PR #5 tracks.

**Phase 2b (arbitration core, criteria 3-6) is in progress on
`phase-2b-arbitration`**, branched from `phase-2-arbitration` after 2a
closed. ADR-0021 amended with a venv-packaging addendum: the Python core
builds into `/opt/gexis-core/venv` inside the pi-gen chroot, `dbus-next`
over `dbus-python` (pure Python, no build toolchain needed on the
image), exact-version pins (hash-pinning flagged as a follow-up, not
done). `core/` holds the supervisor (`Supervisor` + `TimeoutLadder`, base
slot always LMS, ADR-0010's policy, criterion 4's polite-stop → SIGTERM →
SIGKILL ladder via `systemctl kill`), fully unit-tested — 9 tests, no
hardware, all passing — plus adapters for LMS, Spotify and Bluetooth, a
volume bridge (criterion 5) and boot volume (criterion 6). Packaged into
`image/stage-gexis/03-core`; the Makefile now bind-mounts `core/` into
the pi-gen container as well as `stage-gexis`, so build-time `pip
install` runs against the same source tree the unit tests run against,
not a copy.

**A second "verification ran against the wrong reality" instance, caught
and corrected in the same session it was made:** the LMS-unreachable
claim two sections above was wrong. The original reachability check was
a bare GET to `/jsonrpc.js` with no body and a 5s timeout — LMS
apparently only handles POST there, so the GET just hung until the
timeout, which read as "unreachable." A real JSON-RPC POST succeeded
immediately, confirmed the "gexis" LMS player exists
(`e4:5f:01:58:89:07`, `192.168.178.188:9000`), and running the LMS
adapter's `run()` against it end-to-end — handshake, `/slim/subscribe`,
then a real `playlist play` triggered from the test itself — produced a
genuine CometD `mode -> play` push and fired `on_acquire()` within 4
seconds. First time the CometD subscription (previously the file's own
"unverified" flag) has been watched work at all. **Not independently
reconfirmed:** whether `release()`'s `pause` call takes effect within
any particular time bound — the JSON-RPC call returned success, but the
test moved on to clearing the playlist before checking mode again.
`adapters/lms.py`'s own comments now record this precisely rather than
carry a blanket "verified" claim forward. Add this as a second
`docs/LESSONS.md` instance alongside the `C3PO`/`gexis` one above — same
shape, different mechanism (wrong HTTP method instead of wrong host).

**Two decisions closed this session:** the boot volume placeholder
(`boot_volume_steps = 60`, i.e. −90dB on ADR-0018's scale — 0.5dB/step,
0=mute/−120dB, 240=0dB) is confirmed by George as the real safe level,
not a placeholder — code comments updated accordingly. LMS's
address needed its port spelled out (`192.168.178.188:9000`); the core's
config defaults to that address now (there is no sane localhost default
for a renderer that lives on a different machine, unlike go-librespot),
and `image/stage-gexis/03-core/files/core.toml` sets it explicitly too.

**The rebuild including the new `03-core` stage succeeded** (39m33s,
after two false starts: one from a bug in this session's own build-time
assertion — checked `venv/bin/python`, a relative symlink to
`venv/bin/python3`, itself an *absolute* symlink to `/usr/bin/python3`,
which only resolves once `${ROOTFS_DIR}` is the real root — fixed by
checking `venv/bin/pip` instead, a plain file; the other two attempts
were killed by `C3PO`'s own low-memory condition, unrelated to the build
itself, and succeeded once more memory was free). All commits pushed to
`origin/phase-2b-arbitration`.

**Reflashed and hardware-tested.** None of it is clean yet; do not treat
criteria 3-6 as met.

> **The dated session logs for Phases 2a-2d — every hardware round from
> 2026-09-06 to 2026-09-12, with what broke and how it was diagnosed — moved
> to [`docs/HANDOFF-ARCHIVE.md`](docs/HANDOFF-ARCHIVE.md) on 2026-09-14.**
> Verbatim, nothing edited. Look there for *why* something is the way it is;
> the rules those sessions produced are in `docs/LESSONS.md`,
> `docs/findings/`, and "Things that will bite if forgotten" below.



## Next actions, in order

**Immediate (2026-09-13, still open):** flash
`image/deploy/2026-09-13-gexis-player-v0.2.1-98-gfec5067-dirty.img` and verify
`04-ui` on hardware — labwc starting, the `PAMName=login` seat, 1280x800, the
Chromium kiosk flags, and the UI actually served by `gexis-core` under the
pinned Chromium rather than a remote Firefox. None of that has ever run. This
is the outstanding half of Phase 4b. Everything after it (4c onward) waits on
George's `.dc.html` artboards plus static PNG exports.

**Second (2026-09-14):** verify `playlistcontrol cmd:load album_id:<id>` with
George present — ADR-0030's typed-library half rests on it and it was
deliberately not executed, because running it starts music unannounced. See
"Start here" at the top of this file for the full list, including what is
awaiting George's sign-off.

> **Items 0 and 1 are done and archived** — ADR-0027 / Phase 2d, and Phase 2c
> criteria 7-10 (Phase 2 closed 2026-09-12). Both are in
> [`docs/HANDOFF-ARCHIVE.md`](docs/HANDOFF-ARCHIVE.md) with their full
> verification records. **Numbering is kept, not compacted**, so references to
> "item 3" elsewhere still resolve.

2. **Finding 013's four defects** - one fixed (squeezelite restart
   burst), one deferred by George's decision (the go-librespot retry
   storm - revisit on any real recurrence), two documented but not
   root-caused (the ~56s go-librespot backoff; go-librespot reporting
   itself playing while never opening the device) - the latter two would
   need reading go-librespot's own source, the way Finding 011 did for
   its acquisition signals, and weren't chased further this session.
3. **Fill the Finding 003 grid** on `rig`, not `gexis` — characterises the
   metering path, not the product image. 16 of 18 cells remain.
4. **Phase 5 (not blocking Phase 2c):** Finding 007's research is done
   and ADR-0025/0026 record the licence and integration-approach
   decisions. Still needed before vendoring: George's ruling on
   turntable/cassette handlers (ADR-0026 assumes meters+spectrum only
   until then), the labwc screen-ownership mechanism spike (ADR-0026
   flags this unverified), and a Pi-4 frame-rate measurement for
   Blocker 2 (Finding 007) — this last one is also the cleanest way to
   close the residual NEON doubt from the same finding.
5. **Two items deferred out of Phase 2b, not gone — pick up whenever
   they matter again, not urgent:**
   - Fixed output mode has no implementation at all in `gexis_core` —
     real, design-complete work (ADR-0018's table and "Settled
     consequences"), most naturally built once mode *selection* has a
     UI to live in (Phase 4+).
   - Bluetooth's SIGKILL-escalation path (device still held after a
     full ladder run, reproduced once 2026-09-08, not since) — worth a
     deliberate forced-escalation test if it's ever a live problem
     again; not chased further while polite stop keeps working.
   - LMS device-reclaim mystery (Finding 009/010 §4/5) — possibly
     related to the second squeezelite player "Moode"
     (192.168.178.131) seen on George's LMS server; still not confirmed
     or investigated further.
   - The LMS/Spotify boot-default-vs-mid-session fallback question and
     Bluetooth's `restore_volume_floor_db` number (Finding 011 §3/§4) —
     both need George to pick an actual value, not a mechanism fix.

**ADR-0010's sync-group-interaction item is moot in the good sense
now** — `-C 1` means squeezelite is never killed in normal operation,
so there's no sync-group loss to accept anymore. See the ADR's own
final amendment.

Decisions pending from George: confirming (or picking a different)
`restore_volume_floor_db` — currently a −40dB placeholder, and now
measured on hardware as genuinely too quiet for Bluetooth's
unmanaged-floor bump (Finding 011 §4), not just unreviewed; whether
`boot_volume_steps`'s -90dB fallback should keep applying to any
never-remembered LMS/Spotify acquisition mid-session, or only to true
cold boot (Finding 011 §3 — a mid-session first-use currently lands as
quiet as a fresh power-on, confirmed on hardware); which component
applies Bluetooth's software volume attenuation below ~96% (Finding
006, no owner yet); pinning down squeezelite's LMS-volume-to-hardware
mapping (Finding 008's B2 fix addresses the *cross-renderer bleed*
symptom this was originally raised under, but the underlying
mapping/curve question is separate and still open); the criterion 7
build-self-identification amendment; whether to act on the
develop-on-hardware workflow inversion (needs an ADR first if so);
turntable/cassette handlers for Phase 5 (ADR-0026); whether the LMS
device-reclaim mystery (Finding 009/010 §4/5) is related to the second
squeezelite player "Moode" (192.168.178.131) seen registered on
George's LMS server early in the 2026-09-08 session — flagged to
George, not yet confirmed or investigated further.

Not blocking, needed before their phases: the peppyalsa FIFO byte format
(blocks the visualisation service) and George supplying format icons for
LMS/Spotify/Bluetooth (Finding 007's follow-up notes — the bundled set
covers none of our three sources).

**Build speed — options 1 and 2 implemented and verified, 2026-09-08.**
`make image` ran ~40 minutes; George asked for ways to cut that (stability
still comes first — this doesn't reopen ADR-0001's pi-gen-over-rpi-image-gen
call, see its 2026-09-08 amendment). Five options were researched and
ranked; George asked to implement 1 and 2 and rebuild to see the effect.
Both are now live in the `Makefile` (see its own comment on the `image`
target for the full reasoning) and verified with two real, back-to-back
builds — not estimated:

| Build | What changed | Measured time |
|---|---|---|
| Baseline (2026-09-08, earlier session) | neither option | 39m11s |
| Cold build, option 2 only (`stage2/EXPORT_IMAGE` removed) | drops the unused "-lite" export | **32m01s** (predicted ~32m30s) |
| Warm build, both options (`CONTINUE=1` against the preserved container from the run above) | also skips stage0-2 | **11m33s** (predicted ceiling ~12m39s) |

Both measurements beat the prediction slightly. Confirmed correct, not
just fast: `stage0/prerun.sh` (the ~3.5-minute debootstrap) went from
Begin to End in the same second on the warm build — the rootfs is
reused wholesale — while `stage-gexis/03-core/00-run-chroot.sh` (the
`pip install` of `gexis-core`) still ran in full (30s) against the live
bind-mounted source, and only one `export-image` pass ran. The cache
skips the base OS layers, not our own code.

One wrinkle noticed, not a problem: `work/*/build.log` (mirrored to
`deploy/build.log`) *appends* across `CONTINUE=1` runs rather than
starting fresh, so grepping it for one run's stage timings after several
warm rebuilds will show more than one run's entries mixed together — use
the live `docker logs`/Makefile-reported wall time for a single run's
number, not this file, once several incremental builds have piled up.

**Consequence for the day-to-day workflow:** `make image` now leaves the
`pigen_work` container behind on success (`PRESERVE_CONTAINER=1`) instead
of self-cleaning — `make clean` is the only way left to force a truly
from-scratch build (a pi-gen submodule bump, a suspected caching bug, or
just wanting a clean-room result before a release). Its own comment in
the `Makefile` explains this.

**Not implemented, still open if the remaining ~11-12 minutes (mostly the
QEMU-emulated final export/compress and whatever base-OS work wasn't
cached) is ever worth chasing further:**

3. **Native arm64 build host** — removes the QEMU emulation tax entirely
   (the dominant remaining cost: QEMU user-mode emulation runs every
   `dpkg`/`apt` post-install script instruction-by-instruction). The
   single biggest possible further win, but changes the build environment
   away from the one ADR-0001/Findings 002-003 were measured on — not
   free of its own verification cost.
4. **Local apt caching** (`apt-cacher-ng` or similar) — smaller win here
   than usual: build logs show package *fetching* is already fast; the
   slow part is unpack/configure under emulation, not download. Cheap to
   add, helps most on a slow/flaky network day.
5. **Audit whether stage0/1/2 install anything this product doesn't
   need** — least certain, nothing checked yet, and cuts against
   ADR-0001's "less of the base is ours to maintain" reasoning. Last
   resort, not a first move.



---

# Session 14 close (2026-09-16) — superseded 'Start here' block, moved verbatim

Last updated: 2026-09-16 (fourteenth session — **Phase 4 closed: 4c-4f and
settings built, checked on hardware, merged, and flashed from an image built
from `main`**)

## Start here

**The device is running the current image.**
`image/deploy/2026-09-15-gexis-player-v0.2.1-146-ge89d8bb-dirty.img`, built
cold from `main` (`e89d8bb`), flashed and checked by George on 2026-09-16:
now playing, idle screen, volume and mute, handoff, and settings from a phone.
Provisioning carries the hostname, Wi-Fi, SSH key, time zone (Europe/Berlin)
and the idle URL, which is deliberately not in the repo.

**Phase 4 is closed** (2026-09-16). Criteria 1, 2, 3, 4, 5 and 8 met and
checked by George; 6 and 7 withdrawn. `docs/DEVELOPMENT.md` carries the
closure and what it does *not* claim — read that before assuming anything
about fixed output mode, text entry on the panel, or how much of the settings
inventory is actually wired.

**Open right now:**

- **PR #16** (`settings-seed`) — provisioning can seed settings so a reflash
  restores them. Hardware-checked briefly by George; **not merged**.
- **`playlistcontrol cmd:load album_id:<id>` is still unverified** and is the
  load-bearing assumption of ADR-0030's typed-library half. Needs George
  present: running it starts music.
- **For Claude Design:** number and text editing in settings is described but
  never drawn, so the port improvises both; the export's CSS drops the source
  pill's pulse; `design/README.md` still describes a format badge and the
  paused treatments that were removed.

**Next phase: 5 — visualisation service and the Peppy screen.** Seven
criteria plus the Peppy entry button, moved there from Phase 6 by George on
2026-09-15 as the phase's last step. Nothing in it is started. Two carried
decisions change what it must build: **no sample rate or codec anywhere,
Peppy screen included** (George, 2026-09-15 — ADR-0019's codec rule needs
amending in this phase), and ADR-0033's idle model, which renames that
record's "idle timeout while playing".


Last updated: 2026-09-15 (twelfth session — **04-ui fixed and verified on
hardware; ADR-0029 to 0032 decided; a new image is built and waiting to be
flashed**)



---

# Session 15 close (2026-09-17) — superseded 'Start here' block, moved verbatim

Last updated: 2026-09-16 (fifteenth session — **Phase 5 built: visualisation
service, skin corpus and validator, both engines in one process, rotation,
entry and exit, metadata layer; checked on the panel by George**)

## Start here

**The device runs the 2026-09-15 image plus hand-installed Phase 5 work.**
`image/deploy/2026-09-15-gexis-player-v0.2.1-146-ge89d8bb-dirty.img` is what
was flashed. On top of it, by hand and **not in that image**:

- the Phase 5 daemon code in `/opt/gexis-core/venv` (Peppy control, metadata
  file, settings seed);
- the driver, engines and stock skins in `/tmp/spike/gx`, started by hand —
  **gone on reboot**;
- the meter service, started by hand — also gone on reboot;
- packages `python3-pygame`, `python3-pil`, `wlrctl`, `grim` and
  `python3-pytest` (the last two test-only).

A new image carries all of it except the test-only packages
(`stage-gexis/05-peppy`, `03-core/files/gexis-meter.service`), and the
implicit-entry fix, which the device does **not** have. **Build it and reflash
before trusting anything above as a product.**

**Phase 5 status** — `docs/DEVELOPMENT.md` has each criterion's evidence:

- 1 visualisation service: built; levels verified live; **HTTP push
  untested**. Unit added 2026-09-16 — it had only ever run by hand.
- 2, 3 skins: Gelo5's 84 in `skins/` (config only; images fetched at build),
  validator gates `make image`.
- 4 no visible construction: measured, Finding 025.
- 5 rotation per track: built, Finding 027.
- 6 renderer change exits: **George checked**.
- 7 absent fields: our own metadata layer; **George checked** across all
  three renderers, including the layout fixes (text in its box, MM:SS in
  DSEG7, badges with names).
- 8 button and touch-to-hide: **George checked**. Implicit five-minute entry
  **failed on hardware** (every Spotify track end read as a skip), fixed and
  unit-tested, **not yet observed** — the first thing to check on the new
  image: play for six minutes without touching the panel.
- 9 no sample rate or codec: nothing renders it, ADR-0036.

**Follow-ups, not blocking:**

- `viz_timeout` is read by the daemon but not wired in the settings registry,
  so the phone cannot change it (ADR-0035 says wire it with its feature).
- The stock skins are Volumio-branded; Gelo5's are the image default.
- Titles too long for their box are cut with "…"; the wrapper scrolls them.
- Fonts: DejaVu for text; DSEG7 (OFL) for time. PeppyFont not vendored.
- George once saw the spectrum overlap remaining time on `dash-spectrum`;
  not reproduced in 24 rotations or a direct start.
- **Lesson candidate:** hand-started test processes multiplied because pid
  files captured the wrong pid; George saw overlapping skins. Stop by looking
  processes up, not by trusting a pid file.

**Issues to look at later (Phase 6 hardware rounds, 2026-09-16):**

- **Over Bluetooth, the Plexamp app reports pauses late or not at all** — about
  6 s from its own button, 4.5 s or never for a panel command. The Spotify app
  on the same phone reports in 0.2 s (Finding 028, addendum 2). A2DP's
  stream-idle signal comes 3 s after the report, so it cannot help. With
  Plexamp the panel's icon falls back after 8 s. Next step, with the speakers
  on: does Plexamp's audio stop at the tap?
- **LMS had player `gexis` on fixed volume (`digitalVolumeControl` 0), cause
  unknown.** George found it as "phone volume does nothing while the panel is
  muted, and LMS's volume bar is frozen". Measured 2026-09-16: with 0, LMS
  moves its own number but always sends full level, so no LMS volume change
  reaches the device, muted or not. Mute then became a trap, because the one
  change that ends it never arrived. Set back to 1 with George's OK; re-tested
  while playing: LMS volume reaches the DAC again, and a change while muted
  ends mute (ADR-0034). **George never touched it,** and nothing in this repo
  sets it; it worked on 2026-09-08 (Finding 008). **Check it after the next
  reflash and LMS restart.** Nothing warns when it is 0; a candidate for
  Phase 9.
- **Pausing LMS moved the DAC slightly** (dummy −47 → −50 dB, DAC 152 → 150)
  during the same test. Small, unexplained, not investigated.
- **After a `gexis-core` restart, a phone already connected is not active.**
  The Bluetooth adapter seeds metadata from a `MediaPlayer1` that is already
  present but never calls `on_acquire`. Spotify has the same effect. It only
  matters when the daemon restarts, not at boot.
- **LMS once reported a position about 5 s ahead on resume**, then corrected
  it at the next pause. Not reproduced on a second try; recheck with sound.

**Still open from earlier:** `playlistcontrol cmd:load album_id:<id>` is
unverified (ADR-0030); Claude Design owes drawn number/text editors and a
corrected `design/README.md`.

**Next phase: 6 — now playing, full**: transport controls only. The info
panels moved to Phase 8, and a control that cannot work right now is
disabled, never hidden (both George, 2026-09-16). The agreed plan is under
Phase 6 in `docs/DEVELOPMENT.md`. **Before any of it:** flash
`image/deploy/2026-09-16-gexis-player-v0.2.1-179-g67193d5-dirty.img` (built
from `main` after PR #17; contents verified as a file) and check the
five-minute Peppy entry on it.


# Session 16 close (2026-09-17) — superseded 'Start here' block, moved verbatim

Last updated: 2026-09-17 (sixteenth session, on R2D2 — **Phase 6 built on
`phase-6-plan`; its first image build on R2D2 failed at the loop device and
must be rerun before George's checks and the PR**)

## Start here

**The device runs the 2026-09-16 image (`v0.2.1-179-g67193d5`, Phase 5) plus
Phase 6 core and UI installed by hand.** There is **no Phase 6 image yet.**
**Next action: rerun `make image` on R2D2, verify the image with
`image/verify-image.sh`, hand it to George to flash and check, then the PR
from `phase-6-plan` to `main`.**

**Development moved to R2D2 on 2026-09-17** (see Machines).

**The first Phase 6 build on R2D2 failed (2026-09-17, 11:35-11:55, 1224 s).**
Every stage, including all of `stage-gexis`, finished; `export-image/prerun.sh`
then failed six times with `mknod: invalid minor device number '/dev/loop0
(lost)'`. No image came out (`image/deploy/` does not exist). Log:
`~/gexis-build.log`.

That is the failure `image/README.md` records under "Known issue (resolved)"
from C3PO's first build (2026-09-05), which blames the `loop` module not being
loaded before the build, fixed by `sudo modprobe -r loop && sudo modprobe loop`.
What was measured on R2D2 fits that record, but also a second explanation, and
**the rerun is what tells them apart:**

- R2D2 booted at 11:12; `/etc/modules-load.d/loop.conf` was written at 11:29,
  so it has not taken effect yet. The kernel logged `loop: module loaded` at
  11:54:42 — loaded by the build itself, at the loop step. (Fits the README.)
- This kernel has `CONFIG_BLK_DEV_LOOP_MIN_COUNT=0`: loading the module creates
  no `/dev/loopN` nodes. A `--privileged` container's `/dev` is (assumed, not
  checked) populated when the container starts, so a `/dev/loop0`
  created mid-build would never appear inside it — "(lost)". If that is the
  cause, autoloading at boot does **not** prevent it.
- `/dev/loop0` now exists on the host (created 11:54:42, nothing attached).

**So: do not reboot R2D2 and do not reload `loop` before the rerun** — both
remove `/dev/loop0`. If a plain rerun gets past `export-image`, the README's
root cause is incomplete: propose correcting it (and a durable fix, e.g.
pre-creating a loop node before the build) to George. If it fails the same
way, apply the README's fix — it needs `sudo`, so George runs it.

**Docker access:** the session that found this had no `docker` group in its
process (George is in the group; the process predated it) and `sudo` needs a
password. Check `id` shows `docker` before starting. Run the build detached,
as before, so the session's memory guard cannot kill it:
`nohup setsid bash -c "make image > ~/gexis-build.log 2>&1; echo BUILD-EXIT=\$? >> ~/gexis-build.log" >/dev/null 2>&1 </dev/null &`.
The submodule shows `m image/pi-gen` afterwards (`stage2/EXPORT_IMAGE` deleted
by the Makefile): expected, leave it.

**Verifying the image: `image/verify-image.sh image/deploy/<name>.img`** (new,
2026-09-17). Reads the root partition with `debugfs` at its offset (no root,
no loop device) and compares against the checkout: every unit, config and
Peppy file byte for byte; the six units enabled and `alsa-restore` masked;
`default.target` not written; venv `gexis_core` identical to `core/src`;
`/opt/gexis-ui` identical to `ui/dist`; Peppy engines, font, icons and both
skin corpora. Tested only against a synthetic ext4 image (every FAIL path and
the symlink/dump mechanics) — **its first real run is this image**; read its
output, don't just trust `RESULT`. Also check the version in the `.info`
manifest matches the commit built. The Phase 5 image's own check was never
written down step by step; this replaces it.


# Session 17 close (2026-09-17) — superseded 'Start here' block, moved verbatim

Last updated: 2026-09-17 (seventeenth session, on R2D2 — **the Phase 6 image
is built and verified as a file; George is flashing it**)

## Start here

**The Phase 6 image exists:**
`image/deploy/2026-09-17-gexis-player-v0.2.1-202-gf3674f3-dirty.img` (4.5 GB,
built from `phase-6-plan` at `f3674f3`; `-dirty` is only the pi-gen submodule's
deleted `stage2/EXPORT_IMAGE`). **Built in 467 s, `BUILD-EXIT=0`.**
`image/verify-image.sh` passed every check on its first real run, output read
line by line: 18 files byte-identical, six units enabled with the right link
targets, `alsa-restore` masked, `default.target` not written, venv
`gexis_core` = `core/src` (27 .py), `/opt/gexis-ui` = `ui/dist` (51 files),
Peppy engines, font, icon, 267 Gelo5 and 42 stock skin images; `viz_timeout`
not in the registry, daemon fallback 300 s. The script does not read the boot
partition; checked separately with `mtype`: `cmdline.txt` still has
`systemd.run=/boot/firstrun.sh`, `firstrun.sh` placeholders blank.

**When this session closed, George was about to flash it** (R2D2 rebooted
first). The device may still be on the 2026-09-16 image plus hand-installed
Phase 6 — ask, or check `/etc/gexis` timestamps.

**Next actions, in order:**

1. George flashes and runs `make provision DEVICE=/dev/sdX`, boots.
2. **Add C3PO's key to the device** (George, 2026-09-17: after first boot,
   not in `provision.sh`). `image/provision.local.env` now carries **R2D2's**
   key only (it had C3PO's, copied over with the file; both keys have the
   comment `desktop-to-dietpi` — tell them apart by fingerprint: R2D2
   `SHA256:UVfv…`, C3PO `SHA256:d/pT…`). C3PO's public key is saved at
   `~/.ssh/c3po_id_ed25519.pub`. Append it with
   `ssh pi@gexis.local 'cat >> ~/.ssh/authorized_keys' < ~/.ssh/c3po_id_ed25519.pub`
   and confirm both fingerprints with `ssh-keygen -lf ~/.ssh/authorized_keys`
   on the device. Repeat after every reflash. (A two-line `SSH_PUBKEY` would
   work in `firstrun.sh` — `imager_custom add_ssh_keys` echoes the value, one
   line per key — but `provision.sh`'s round-trip check greps one line and
   would refuse it; George chose not to change it.)
   `~/provision.local.env.bak-c3po-key` (holds the Wi-Fi password) can be
   deleted once George is happy.
3. Check LMS player `gexis` is on "adjust volume" (`digitalVolumeControl` 1).
4. George's checks below, then the PR from `phase-6-plan` to `main`.

**The loop-device question is still open — and this rerun did not settle
it.** The first R2D2 build (2026-09-17 11:35, log
`~/gexis-build-1-failed-loop.log`) failed at `export-image/prerun.sh` with
`mknod: invalid minor device number '/dev/loop0 (lost)'`. The rerun
(12:40, log `~/gexis-build.log`) attached `/dev/loop0` first time. The
previous handoff said a passing rerun would show `image/README.md`'s root
cause (module not loaded before the build) is incomplete — **that was wrong**:
the rerun started with the module loaded *and* `/dev/loop0` present, so both
explanations predicted a pass. What discriminates is **the first build after
R2D2's reboot**: `loop` autoloads from `/etc/modules-load.d/loop.conf`, but
with `CONFIG_BLK_DEV_LOOP_MIN_COUNT=0` no `/dev/loopN` exists. Before building,
record `lsmod | grep -w loop` and `ls /dev/loop*`. A pass means the README is
right; a `(lost)` failure means the missing node is the cause, and autoloading
does not prevent it — then propose to George correcting the README and a
durable fix (e.g. pre-creating a node before the build; needs `sudo`).

**Docker group:** the closing session's process predated George's `docker`
membership; the build ran via `newgrp docker` (no sudo), piping the detached
command into it. After the reboot `id` should show `docker` directly — check.
Run builds detached as before so the session's memory guard cannot kill them:
`nohup setsid bash -c "make image > ~/gexis-build.log 2>&1; echo BUILD-EXIT=\$? >> ~/gexis-build.log" >/dev/null 2>&1 </dev/null &`.
Move the previous log aside first. The submodule shows `m image/pi-gen`
afterwards: expected, leave it.

**Development moved to R2D2 on 2026-09-17** (see Machines).

**Checks for the flashed Phase 6 image:**

1. **Peppy screen:** it comes up after 5 minutes of playback with no touch.
   This was seen on the old image with a 1-minute test timeout; the timeout
   is back to the default.
2. **Transport on all three renderers:** play/pause (the icon flips on
   press), next and previous. On LMS radio, Next, Previous, Shuffle and
   Repeat are dimmed.
3. **Not yet checked anywhere: shuffle and repeat on Spotify and Bluetooth**
   (added 2026-09-17). Use the phone's Spotify app, then Bluetooth with the
   Spotify app, then Bluetooth with Plexamp. On Bluetooth, the buttons may be
   dimmed if the app exposes no shuffle or repeat.
4. **With the speakers on:** radio resuming after a pause; the dropout when
   LMS restarts a stream; the one-off LMS resume-position jump; whether
   Plexamp's audio stops at the tap.
5. **LMS volume:** check that player `gexis` is still on "adjust volume" after
   the reflash (see issues below).

**Phase 6** (DEVELOPMENT.md has the evidence): criteria 1 and 2 are built and
checked on the panel, except item 3 above. Criterion 3 (info panels) moved to
Phase 8; criterion 4 (the Peppy button) was done in Phase 5.
[ADR-0037](docs/decisions/0037-transport-commands.md) covers transport, with
two amendments by George: the play icon flips on press, and Spotify and
Bluetooth get shuffle and repeat.
[Finding 028](docs/findings/028-transport-commands-on-three-renderers.md) has
the measurements.

**Phases renumbered 2026-09-16:** 9 is settings wiring and UI polish (new);
10 is the plugin contract; 11 Plexamp and 12 Qobuz Connect (new); 13 is first
boot.

**Issues to look at later (Phase 6 hardware rounds, 2026-09-16):**

- **Over Bluetooth, the Plexamp app reports pauses late or not at all** — about
  6 s from its own button, 4.5 s or never for a panel command. The Spotify app
  on the same phone reports in 0.2 s (Finding 028, addendum 2). A2DP's
  stream-idle signal comes 3 s after the report, so it cannot help. With
  Plexamp the panel's icon falls back after 8 s. Next step, with the speakers
  on: does Plexamp's audio stop at the tap?
- **LMS had player `gexis` on fixed volume (`digitalVolumeControl` 0), cause
  unknown.** George found it as "phone volume does nothing while the panel is
  muted, and LMS's volume bar is frozen". Measured 2026-09-16: with 0, LMS
  moves its own number but always sends full level, so no LMS volume change
  reaches the device, muted or not. Mute then became a trap, because the one
  change that ends it never arrived. Set back to 1 with George's OK; re-tested
  while playing: LMS volume reaches the DAC again, and a change while muted
  ends mute (ADR-0034). **George never touched it,** and nothing in this repo
  sets it; it worked on 2026-09-08 (Finding 008). **Check it after the next
  reflash and LMS restart.** Nothing warns when it is 0; a candidate for
  Phase 9.
- **Pausing LMS moved the DAC slightly** (dummy −47 → −50 dB, DAC 152 → 150)
  during the same test. Small, unexplained, not investigated.
- **After a `gexis-core` restart, a phone already connected is not active.**
  The Bluetooth adapter seeds metadata from a `MediaPlayer1` that is already
  present but never calls `on_acquire`. Spotify has the same effect. It only
  matters when the daemon restarts, not at boot.
- **LMS once reported a position about 5 s ahead on resume**, then corrected
  it at the next pause. Not reproduced on a second try; recheck with sound.

**Follow-ups, not blocking:**

- `viz_timeout` is read by the daemon but not wired in the settings registry,
  so the phone cannot change it (ADR-0035 says wire it with its feature).
- The stock skins are Volumio-branded; Gelo5's are the image default.
- Titles too long for their box are cut with "…"; the wrapper scrolls them.
- Fonts: DejaVu for text; DSEG7 (OFL) for time. PeppyFont not vendored.
- George once saw the spectrum overlap remaining time on `dash-spectrum`;
  not reproduced in 24 rotations or a direct start.
- **Lesson candidate:** hand-started test processes multiplied because pid
  files captured the wrong pid; George saw overlapping skins. Stop by looking
  processes up, not by trusting a pid file.

**Still open from earlier:** `playlistcontrol cmd:load album_id:<id>` is
unverified (ADR-0030); Claude Design owes drawn number/text editors and a
corrected `design/README.md`.

**Next phase after the Phase 6 PR: 7 — library browse.**


# Session 18, Phase 6 close (2026-09-17) — superseded 'Start here' block, moved verbatim

Last updated: 2026-09-17 (eighteenth session, on R2D2 — **Phase 6 image
flashed and signed off by George; PR from `phase-6-plan` to `main` open**)

## Start here

**Phase 6 is closed pending the PR merge.** The device runs
`2026-09-17-gexis-player-v0.2.1-202-gf3674f3-dirty.img` (built from
`f3674f3`; `/etc/gexis` files dated 12:43–12:48, matching the build).
Provisioned with `make provision`; `firstrun.sh` consumed itself; no failed
units; all renderer, core, kiosk, meter and Peppy units running.

**Done on the device this session (checked by Claude):**

- C3PO's key appended; `ssh-keygen -lf ~/.ssh/authorized_keys` shows both,
  R2D2 `SHA256:UVfvJQXw…ci4` and C3PO `SHA256:d/pT3AST…tok`. **Repeat after
  every reflash** (`provision.local.env` carries R2D2's key only; George chose
  not to change `provision.sh`):
  `ssh pi@gexis.local 'cat >> ~/.ssh/authorized_keys' < ~/.ssh/c3po_id_ed25519.pub`.
- LMS player `gexis` (`88:a2:9e:79:e1:32`): `digitalVolumeControl` **1**
  after the reflash, read over JSON-RPC. LMS itself was not restarted, so the
  "after an LMS restart" half of that check was not made.
- Core tests on R2D2: 444 passed, 1 skipped (scratch venv, `core[test]`).

**George's hardware checks of the image: George called them done
(2026-09-17) and asked for the PR.** Results for the individual checks
(Peppy entry at 5 min, transport on three renderers, shuffle/repeat on
Spotify and Bluetooth, the speakers-on items) were not reported item by item
in the session, so none of them is recorded here as observed. If one matters
later, ask George rather than reading this as a pass.

**Next action:** George reviews and merges the Phase 6 PR. Then Phase 7 —
library browse, starting with the unverified
`playlistcontrol cmd:load album_id:<id>` (ADR-0030).

**The loop-device question is still open, and the discriminating state is
recorded.** Background: the first R2D2 build (2026-09-17 11:35, log
`~/gexis-build-1-failed-loop.log`) failed at `export-image/prerun.sh` with
`mknod: invalid minor device number '/dev/loop0 (lost)'`; the rerun (12:40,
`~/gexis-build.log`) passed but started with `/dev/loop0` already present, so
it discriminated nothing. **After R2D2's reboot, before any build (13:37,
up 8 min):** `lsmod | grep -w loop` → `loop 45056 0` (autoloaded from
`/etc/modules-load.d/loop.conf`); `ls -l /dev/loop*` → only
`/dev/loop-control`, **no `/dev/loopN`**. No build has run since. **The next
`make image` on R2D2 is the test**, provided R2D2 has not rebooted and nothing
has created a loop node in between — re-record both before building. A pass
means `image/README.md`'s root cause (module not loaded) is right; a `(lost)`
failure means the missing node is the cause and autoloading does not prevent
it — then propose to George correcting the README and a durable fix (e.g.
pre-creating a node before the build; needs `sudo`).

**Docker group:** after the reboot `id` shows `docker` (950) directly;
`newgrp` is no longer needed. Run builds detached so the session's memory
guard cannot kill them:
`nohup setsid bash -c "make image > ~/gexis-build.log 2>&1; echo BUILD-EXIT=\$? >> ~/gexis-build.log" >/dev/null 2>&1 </dev/null &`.
Move the previous log aside first. The submodule shows `m image/pi-gen`
afterwards: expected, leave it.

**Development moved to R2D2 on 2026-09-17** (see Machines).
`~/provision.local.env.bak-c3po-key` (holds the Wi-Fi password) can be
deleted once George is happy.

**Phase 6** (DEVELOPMENT.md has the evidence): criteria 1 and 2 built and
checked on the panel; criterion 3 (info panels) moved to Phase 8; criterion 4
(the Peppy button) was done in Phase 5.
[ADR-0037](docs/decisions/0037-transport-commands.md) covers transport, with
two amendments by George: the play icon flips on press, and Spotify and
Bluetooth get shuffle and repeat.
[Finding 028](docs/findings/028-transport-commands-on-three-renderers.md) has
the measurements.

**Phases renumbered 2026-09-16:** 9 is settings wiring and UI polish (new);
10 is the plugin contract; 11 Plexamp and 12 Qobuz Connect (new); 13 is first
boot.

**Issues to look at later (Phase 6 hardware rounds, 2026-09-16):**

- **Over Bluetooth, the Plexamp app reports pauses late or not at all** — about
  6 s from its own button, 4.5 s or never for a panel command. The Spotify app
  on the same phone reports in 0.2 s (Finding 028, addendum 2). A2DP's
  stream-idle signal comes 3 s after the report, so it cannot help. With
  Plexamp the panel's icon falls back after 8 s. Next step, with the speakers
  on: does Plexamp's audio stop at the tap?
- **LMS had player `gexis` on fixed volume (`digitalVolumeControl` 0), cause
  unknown.** George found it as "phone volume does nothing while the panel is
  muted, and LMS's volume bar is frozen". Measured 2026-09-16: with 0, LMS
  moves its own number but always sends full level, so no LMS volume change
  reaches the device, muted or not. Mute then became a trap, because the one
  change that ends it never arrived. Set back to 1 with George's OK; re-tested
  while playing: LMS volume reaches the DAC again, and a change while muted
  ends mute (ADR-0034). **George never touched it,** and nothing in this repo
  sets it; it worked on 2026-09-08 (Finding 008). **Checked after the 2026-09-17 reflash: 1.**
  Still unchecked after an LMS restart. Nothing warns when it is 0; a candidate for
  Phase 9.
- **Pausing LMS moved the DAC slightly** (dummy −47 → −50 dB, DAC 152 → 150)
  during the same test. Small, unexplained, not investigated.
- **After a `gexis-core` restart, a phone already connected is not active.**
  The Bluetooth adapter seeds metadata from a `MediaPlayer1` that is already
  present but never calls `on_acquire`. Spotify has the same effect. It only
  matters when the daemon restarts, not at boot.
- **LMS once reported a position about 5 s ahead on resume**, then corrected
  it at the next pause. Not reproduced on a second try; recheck with sound.

**Follow-ups, not blocking:**

- `viz_timeout` is read by the daemon but not wired in the settings registry,
  so the phone cannot change it (ADR-0035 says wire it with its feature).
- The stock skins are Volumio-branded; Gelo5's are the image default.
- Titles too long for their box are cut with "…"; the wrapper scrolls them.
- Fonts: DejaVu for text; DSEG7 (OFL) for time. PeppyFont not vendored.
- George once saw the spectrum overlap remaining time on `dash-spectrum`;
  not reproduced in 24 rotations or a direct start.
- **Lesson candidate:** hand-started test processes multiplied because pid
  files captured the wrong pid; George saw overlapping skins. Stop by looking
  processes up, not by trusting a pid file.

**Still open from earlier:** `playlistcontrol cmd:load album_id:<id>` is
unverified (ADR-0030); Claude Design owes drawn number/text editors and a
corrected `design/README.md`.

## Phase 7, step by step (moved 2026-09-18, nineteenth session)

Verbatim from `HANDOFF.md`'s "Start here" when Phase 7 closed. The
durable half is elsewhere: [ADR-0038](decisions/0038-library-and-radio-on-the-panel.md)
for the decisions, `docs/DEVELOPMENT.md` Phase 7 for the plan and what each
step settled, Findings 029-032 for the measurements.


**Phase 7 — library browse — is planned on branch `phase-7-plan`.** George
agreed the plan and six decisions on 2026-09-17; they are in
[ADR-0038](docs/decisions/0038-library-and-radio-on-the-panel.md) (status
**Proposed**) and in `docs/DEVELOPMENT.md` Phase 7 (criteria 1 and 6 amended,
10 and 11 added, the plan). In short: only the designed screens; row actions
play now, add to queue, add to playlist (**no create playlist** in Phase 7);
initials instead of artist photos and a discography-only artist page until
Phase 8; the queue rail is in; Radio Now Playing stays; five settings
appended to ADR-0022's inventory (George confirmed).

**Step 1 is done: [Finding 029](docs/findings/029-library-and-radio-against-lms.md).**
George's calls on it are in ADR-0038 (§1, §1a, §3): Album Artists; library
playlists only; LMS's filing and release types; add to any library playlist;
no playlist creation (George is asking Claude Design to remove it). ADR-0038
is still marked Proposed.

**Step 1a is done** (2026-09-17): a takeover restores LMS's old position
and play state only if `playlist_timestamp` is unchanged (George's rule A;
ADR-0027 amended, Finding 029 addendum). George checked both directions on
`gexis`. **Hand-installed on the device, not in an image:** `lms.py` copied
into `/opt/gexis-core/venv/lib/python3.13/site-packages/gexis_core/adapters/`,
previous core at `/opt/gexis-core.7-1a-backup`. A reflash loses it until the
Phase 7 image.

**Step 2 is done** (2026-09-17): a playing station shows the song as title,
its artist, the station as the album line, and the song's `artwork_url` or
"artwork pending" (ADR-0038 §8a). George checked on `gexis`; also
hand-installed (previous core, with step 1a, at `/opt/gexis-core.7-2-backup`).
George asked for radio artwork via enrichment: Phase 8 criterion 7.

**Step 3 is done** (2026-09-17): `core/src/gexis_core/library.py` and
`GET /library/…` reads, tested against made-up LMS replies (George's call).
Hand-installed on `gexis` too; previous core at `/opt/gexis-core.7-3-backup`.

**Step 4 is done** (2026-09-17, checked by George on the panel): Home is the
library root — five cards with live counts, the New Music strip, the mini
strip, the waiting services when no renderer is connected, and Settings from
its card. UI deployed by hand to `/opt/gexis-ui` (previous build at
`/opt/gexis-ui.7-4-backup`).

**Next actions: George's three findings from that check**, in his order:

- **4a: volume drops to 0 when LMS pauses. Done 2026-09-17, awaiting
  George's listen.** LMS fades the player out by moving the renderer's mixer
  control; the core mirrored that onto the DAC and published it
  ([Finding 031](docs/findings/031-lms-pause-fade-and-push-latency.md);
  ADR-0018 and ADR-0034 amended). Fixed by deciding only once the control has
  settled for 0.8 s, and only while the renderer is playing - two earlier
  attempts failed on hardware because the pause reaches the core 0.51 s after
  the fade. Measured after the fix: the DAC holds its level across a pause,
  the panel stays at 48%, and an LMS-app change still lands, 0.8 s later.
- **4b: press feedback. Done 2026-09-17, awaiting George's check.** Now
  playing's buttons, Settings' Back and the library's round buttons keep
  their resting fill and shrink to 0.95 on press; the mini strip shrinks to
  0.995 from its bottom edge. The design's grey press fill read as a flash,
  as it already had on play and the transport buttons.
- **4c: choppiness. Fixed by one backdrop for the whole panel** (George,
  2026-09-17: *"clear improvement"*). `ui/src/screens/PanelBackground.svelte`
  draws the weave and the artwork's bleed once; each screen keeps only its
  own veil, so exactly one screen is mounted at a time and the incoming one
  fades in (120 ms). Also in this step: artwork requested at the size it is
  drawn (200 px thumbs, 500 px covers), the strip's fade mask changed only
  when an edge gains or loses it, and the library's animation halved to
  140 ms. **The CPU governor was set to `performance` and reverted the same
  day** ([ADR-0039](docs/decisions/0039-cpu-governor-performance.md)): ~10 °C
  hotter (76.3 °C mean against 66.2) for no visible improvement. **Screen changes are not animated at all**
  (George, 2026-09-17): a fade of any kind showed the bare backdrop between
  two transparent screens and read as a blink - worse with the incoming-only
  fade than with the two-way one. The design's 260 ms slide-and-fade, the
  mini strip's 104 px slide and Settings' fade are all gone; the drawer, idle
  screen and handoff keep theirs. **The root's covers are loaded and decoded
  when the panel starts** (`ui/src/lib/library.js`), because without an
  animation the New Music tiles were visibly a beat behind the cards.
  **Horizontal scrolling:** no scroll handler at all - the edge fades come
  from two sentinels and an `IntersectionObserver`, the mask sits on a
  wrapper that does not scroll, and the scroller is `contain: content`.
  Reading `scrollLeft`/`scrollWidth` per frame forces a layout each time;
  **apply the same three to the artist grid and Browse in steps 6-7**, and
  virtualise there if that is not enough (917 artists, thousands of albums).
  George calls the strip *"95% there"*;
  [Finding 032](docs/findings/032-panel-frame-times-during-a-scroll.md)
  measured frame times on the panel and could not attribute the rest - two
  instruments answered a different question first, single-run comparisons
  misled, and the harness's own synthetic touches may cause the drops.
  **Revisit with the long lists, not before.**

**Lesson candidate (2026-09-17), for George:** headless Chromium on the
device was used to check the panel UI and answered a different question
twice — it did not reproduce the black-screen defect the panel showed, and
its screenshots silently stopped updating after any animated transition, so
a real defect first looked like a capture artefact. The panel is the only
renderer that answers "does the panel draw this".

**Step 5 is done** (2026-09-18, checked by George on the panel): the album
page and Play album, over `POST /library/action` (ADR-0038 §5). Track row
actions are step 7.

**A deployment defect found during that check, worth knowing about:** the
core served `index.html` with no cache directive, so restarting the kiosk
could bring back a *cached* page - the panel ran the previous bundle and
404'd the assets it named, and a deployed change was simply not there. Now
`Cache-Control: no-store` (assets are content-hashed and stay cacheable).
**If the panel ever seems not to have a change, check which bundle it has**
before believing the change did nothing.

**Step 6 is done** (2026-09-18): the artist grid with the `#`/A-Z jump rail
and the artist page with its discography. George's calls, now in ADR-0038
§1a: rail letters folded (`Ç` into C, `Í` into I, digits into `#`), and the
discography by year, newest first. He checked the navigation and found it
**slow** - see below.

**Step 7 is done** (2026-09-18): three-pane Browse with the row actions.
George's calls from that check, now in ADR-0038 §3: **Play means in order**
- the core turns LMS's shuffle off before a load, because with shuffle on a
freshly loaded album starts at a random track and an artist mid-album - and
album rows carry the year beside the title. Each pane also returns to the
top when its contents change. **Adding to a playlist is one LMS call per
track** (no bulk form): 87 tracks took 8 s after the core was changed to
keep one HTTP connection instead of opening one per track; the panel says
"Adding …" while it works.

**Steps 8 and 9 are done** (2026-09-18). Playlists: the library's playlists
with their counts, and a playlist's Play all, total and tracks. Radio:
`core/src/gexis_core/radio.py` walks the `radios` subtree and issues an
opaque handle per item, and the panel browses and plays by handle only
(ADR-0038 §5, §8) - checked against the live tree, where the root is the
nine items ADR-0030 predicted and **browsing plays nothing**, which is the
defect Finding 029 caused by following an inherited action.

**Step 10 is done** (2026-09-18, checked by George on the panel): the queue
rail on now playing, LMS only - the design's header with **Clear**, the
source row as the way to pick a playlist, rows that jump and remove, and the
count badge on the queue button. Shuffle all landed with it, beside Play all
on a playlist and on an artist page.

**Two defects found during that check, both fixed and both worth knowing:**

- **The queue could not grow.** It was read only by the seed status query at
  subscribe time, so every later change - which arrives as a CometD push -
  was never read. Two albums added, LMS holding 27 tracks, the panel still
  showing 1. The three tests over it all passed because they called
  `_report_queue_if_changed` themselves; nothing asserted the push loop does
  (`docs/LESSONS.md`). There is now a test that drives `_watch`.
- **The Peppy screen could not be dismissed by touch.** Whether it is up is
  held in memory, so a daemon started *while it is on screen* believes it is
  hidden - and `on_touch` only hides what it thinks is visible. The panel is
  then stranded behind the meter with no way back. A restart mid-session did
  it here; systemd would do the same after a crash on a device in a living
  room. `PeppyController.run()` now minimises once at startup so the two
  agree.

**Also worth not repeating:** the rail was first built from notes rather
than from `design/source/Now Playing.dc.html`, and lost the Clear button,
the source switcher and the count badge; and its own `button` reset was
missing, so every row drew the browser's default button chrome. **The styles
are scoped per component: each screen carries its own reset.**

**Next action: step 11 - the closing step.** Clear the `phase-7` markers,
update the docs, build the image (R2D2's loop-device test comes with it),
open the PR.

**Open, deferred by George: one investigation into lists,** once steps 6 and
7 have put real ones on the panel - not piecemeal fixes before that. What it
must cover, from his checks (2026-09-18): the New Music strip still scrolls
unevenly ([Finding 032](docs/findings/032-panel-frame-times-during-a-scroll.md)
says what is and is not established), and the artist grid is **slow to load,
slow to open and slow to scroll** - 917 artists come as one 98 KB read and
become 917 cards in a single pass, with `content-visibility` already tried
and removed because it broke the jump rail. Candidates to measure: rendering
only the rows on screen, lighter cards, and letter buckets from the core
rather than one list.

**George added the queue rail to it (2026-09-18):** with the rail built,
*everything* on the panel is "quite slow" in his words - so the
investigation is not only about long lists. One candidate is already
named rather than guessed: **the queue rail asks LMS for 500px covers and
draws them at 42px** (`ARTWORK_SIZE` in `adapters/lms.py` serves both now
playing's 500px well and every queue row). Artwork at the size drawn is what
the library reads already do - `ARTWORK_THUMB` exists for exactly this - and
oversized covers were part of what made the New Music strip scroll unevenly
(Finding 029 §5). Not changed yet: George deferred it to the one
investigation rather than fixing piecemeal.

---

## From HANDOFF.md, 2026-09-19 (was the nineteenth session's "Start here")

Moved verbatim when the twentieth session replaced it. Phase 8 and Phase 9
step 1 are finished; what follows is how they read while they were current.


## Start here

**Phase 8 — enrichment and lyrics — is done** (2026-09-18, branch
`phase-8-plan`). Now playing's Artist, Release and Lyrics tabs are filled,
synced lyrics follow the playhead on the Track tab, the artist page has its
About, Popular and Similar, Bluetooth and Spotify get cover art they were
never sent, and a radio stream gets artwork from the song rather than the
station. [ADR-0040](docs/decisions/0040-enrichment-providers.md) records the
providers and was twice amended by what the work measured.

**The idea to carry forward: "could not ask" is not "there is nothing
there."** MusicBrainz's search answered 503 for 4 of 9 tries, LRCLIB has a
busy-503 of its own, and LMS's plugin holds a socket for 75 s before
dropping it - which is also what an *absent* plugin does, in milliseconds.
Every one of those looks like an empty answer. Caching one would deny a
track its enrichment permanently; reading one as "no plugin here" turned
every artist photo off for ten minutes. The distinction is made in five
places now and is the phase's single most load-bearing idea.

**Two keys, both per-user settings George chose:** `listenbrainz_token` (its
popularity endpoint began demanding one mid-phase, having answered 200 the
same morning) and `fanart_key` for artist pictures. Nothing else needs one,
and with neither set the panel simply shows less.

**Fanart adds quality, not coverage** (measured on 14 random artists: 9 had
a picture from both sources, 5 from LMS only, **0 from fanart only**). It
goes first where it has one; LMS stays behind it. Its pictures go through
LMS's image proxy - 705 KB became 32.8 KB at 300 px.

**Parked by George: a background sweep for missing album art.** 155 of 4,567
albums have none. The same sweep for artist pictures was rejected on the
measurement above: 30-45 minutes of MusicBrainz's one-a-second allowance to
improve pictures that already exist.

**Phase 9 step 1 is done, and its question had a wrong premise.** "Why is a
playing panel never idle?" came from Finding 034's idle control, which was
measuring a queue rail left open by the run before it - the rail's blurred
scrim costs 71 % of the frames on its own. An idle panel is idle.

**What the chase found instead is worth more:
[ADR-0041](docs/decisions/0041-scrims-dim-but-do-not-blur.md) - scrims dim
but do not blur.** `backdrop-filter` costs 24.5 ms a frame in draw-and-submit
against a 16.7 ms budget, with the CPU idle: the compositor draws the
backdrop into its own texture and reads it back every frame, which is a
tile-based GPU's worst case
([Finding 037](docs/findings/037-why-a-blurred-scrim-costs-the-panel.md)).
Not the radius, not the area, and Vulkan is worse. **It is off the queue
rail and the volume drawer**, which George checked and kept; Settings and
the rail's source sheet are left for the sweep. **The rule for the design:
depth is affordable, live readback is not** - a static blurred image costs
almost nothing and the artwork backdrop stays exactly as it is.

**It does not reach the target on its own:** the rail goes from ~15 fps to
~36 against a 55 fps floor, and its own list is the rest - the same work the
artist grid needs.

**Next: Phase 9, in the order George agreed on 2026-09-18** - the idle
question first, then the UI sweep, then the performance work, then the
settings and the triage. The reason for that order is in
`docs/DEVELOPMENT.md`: the sweep is a judgement call, and a judgement made
on a panel that drops 71 % of its frames before anyone touches it cannot be
told from the floor it is standing on.

## From HANDOFF, 2026-09-19 (twentieth session) — the image that had never been booted

Superseded 2026-09-20: it was booted, four times on the 19th and once on the
20th. Finding 039 and Finding 041 record what that found. Moved here verbatim.

**The one thing waiting on hardware: an image with a boot animation that has
never been booted.** `2026-09-19-gexis-player-v0.2.1-287-ge59654c-dirty.img`.
George is flashing it to a *different* SD card, keeping the Phase 8 card as
the fallback — the right call, because the change touches the initramfs and
a wrong one does not reach a state where SSH can help.

**What to check on that first boot**, in order, because each answers a
different unknown in [ADR-0043](docs/decisions/0043-boot-animation-and-a-silent-boot.md):

1. **Does it boot at all?** The initramfs is rebuilt by
   `06-splash/02-run-chroot.sh`. If it does not, the fallback is the other
   card, not a fix on this one.
2. **Does the animation appear, and how early?** It should start a second or
   two after power, from the initramfs. Late (~4 s) means plymouth is
   starting after the root mount instead.
3. **Is there any text at all?** Six sources were quieted; any survivor is a
   defect and worth naming precisely.
4. **Is the handover clean?** The splash is held until the panel reports its
   first painted frame. A flash of black between animation and UI means the
   signal is not arriving.
5. **What did it cost?** `free -m` early on. Plymouth may hold all 100 frames
   in memory, ~400 MB if so. 36 of the 100 are exact duplicates, so there is
   cheap headroom if it matters.

**The failure that is worth remembering from this session.** The first build
of the splash stage failed on its *own assertion*: plymouth was not in the
initramfs. The rebuild had reported no error — Raspberry Pi OS ships
`update_initramfs=no`, so `update-initramfs` prints "Not updating initramfs."
and does nothing. Without that assertion the build would have succeeded and
produced a card whose animation starts late, which looks like a design choice
rather than a defect. Same shape as everything in `docs/LESSONS.md`.

**Also in this image, and not on the card George is looking at today:** the
Peppy source badge is now the mark alone (the renderer's name was the only
thing drawn outside the square each skin reserves, and on 7 of the 71 skins
"Bluetooth" left the screen), the album page's track rows are actionable, and
no `backdrop-filter` remains anywhere in the panel.

## Phase 9's design sweep — the state before 9a, archived 2026-09-20

Carried in HANDOFF.md until 9a through 9d were done. Kept verbatim: it is
what the sweep was planned against.

**The design drop is reviewed and nothing is built.**
[Finding 040](docs/findings/040-the-design-drop-and-what-it-changes.md) is the
survey, with George's corrections inline and authoritative; ADR-0044
(settings vocabulary), ADR-0045 (pairing confirmation) and ADR-0046 (fixed
output) are Proposed. `design/` in this repository is **still the previous
package** - the new one has not been landed, and landing it must preserve
`design/fonts/` and `IMPLEMENTED-DIFFERENTLY.md`, both of which the drop
reverts or does not know about.

**The next session's first job is a second comparison**: Claude Design is
adjusting the designs against the feedback in Finding 040's last two
sections, so the package on disk, the package they send back, and the
shipped UI all need diffing again. Finding 040 records how to do it - the
two `.dc.html` files carry 2,461 lines of diff and hold every screen except
Settings, and a skim of the prose misses nearly all of it.

**Three things in Finding 040 want a panel, not a repository:** whether Back
from a New Music album reaches the artist (the code says root, George says
artist), and the two reboot-dependent boot items below.

**Next, in the order George agreed:** the UI sweep (his, with
`design/IMPLEMENTED-DIFFERENTLY.md` in Claude Design's hands), then the
performance work against a baseline retaken *after* the sweep, then settings
and triage.

---

## From HANDOFF, 2026-09-22 (twenty-second session) — 9h before the picker arrived

Moved verbatim when the same day's second half finished 9h. The design
drop George was waiting on arrived, so the two things "waiting on his
designs" and the one 9h "still owed" are all answered below it.

## Start here

**Phase 9's design sweep is seven subphases in and the eighth is mostly
built.** Nine were planned (`docs/DEVELOPMENT.md`), volume last; **9a
through 9g are done, checked by George on the panel and committed**, and
**9h is built except the picker**.

**Two things wait on George's designs** (2026-09-22: *"Will provide soon the
designs"*):

- **The skin picker.** He is redrawing it — a list of skins, with the
  preview shown only when a row is tapped, because the drop's grid *"will
  put some strain on the rendering"*. **The daemon side is built and
  waiting**: `GET /skins` (name, kind, whether the corpus takes it) and
  `GET /skins/{name}/preview`.
- **The weather bar's other fields.** Open-Meteo returns them in the request
  the screen already makes — feels-like, humidity, wind with gusts and
  direction, cloud cover, pressure, sunrise and sunset, UV, chance of rain,
  daily wind maxima; 3.4 KB against the 748 B now fetched, no extra call.
  **The design's bar is full**, so anything added is a layout change.

**What 9h has landed:**

- **Three kinds of skin, not two** — 77 meters, 9 spectrum, 13 both, counted
  on the device. The old two options were *directories*, and `templates/` is
  not the meter corpus. The row is **Skins**: VU meters / Spectrum / VU
  meters + spectrum / Random.
- **[ADR-0050](docs/decisions/0050-skin-previews-are-the-skins-own-picture.md):
  a preview is the skin's own `screen.bgr`** — no render, no cache, no
  change detection, and **9h no longer needs an image build**.
- **The home strip, all three shapes**, after George corrected a finding
  that said two of them were impossible (`docs/LESSONS.md` case 14). They
  are `browselibrary` **sorts**, not fields or tags, and need no plugin.
- **`viz_stop` wired**, and `viz_timeout` moved from seconds to the minutes
  the design draws. Both read per tick.
- **`idle_clock`**, so the panel can be a picture frame (2026-09-22).

**What 9h still owes besides the picker: the visualiser does not honour the
Skins choice.** Our own `driver.py` loads one corpus directory and the kinds
cut across directories, so "Random" needs a composed directory of symlinks.
It is a change to the screen George watches, so it wants his eyes with music
playing.

## 2026-09-23 — Phase 9's 9i and 9j, as HANDOFF carried them

Moved here verbatim on 2026-09-24 when 9i and 9j were finished with,
per the rule in `CLAUDE.md`: HANDOFF is *current state*.

**Phase 9's design sweep is done bar the volume work.** **9a through 9h are
built, checked on the panel and committed.** What is left is now **two**
subphases, split on George's agreement (2026-09-22):

- **9i — the volume path. Built and on the device; the rows are not.**
  [ADR-0052](docs/decisions/0052-the-volume-path.md) on
  [Finding 045](docs/findings/045-the-volume-path-measured.md) decided it
  and all of it has landed: direct libasound writes (5.7 ms against 16.4), a
  **ramp** to each new target, the mirror rate-limited to one hardware write
  per 40 ms, `travel_curve` renamed to `Perceptual`, and
  `external_volume: true` so Spotify stops attenuating the stream on top of
  the DAC. Since then, three more things:
  - **The dummy controls now speak AVRCP's own 128 steps.** Bluetooth
    ratcheted: bluealsa's log shows 107 pushed to the phone and 108 coming
    back, 102 out and 101 back. AVRCP is 0–127 and the dummy was −50…100, so
    the two-way sync `--volume=mixer` makes was lossy by construction — a
    tap settles, a drag never does, and every drift is another AVRCP write
    on a channel that has to stumble once to start Finding 045 §10's retry
    storm. `mixer_volume_level_min=0 mixer_volume_level_max=127` on
    snd-dummy makes it exact; the 6.90 dB of top end that costs is taken
    back in `volume.py` as a constant shift (`DUMMY_DB_MIN = -38.1`).
    **Whether the storm is gone needs his phone and a drag.**
  - **`restore_ceiling` was built, objected to and withdrawn the same day.**
    It clamped the hardware on a restore and told nobody, so the first nudge
    of any slider released the whole 20 dB. George: *"We are taking away the
    decision from the user and creating what looks like an error because the
    sound jumps up or down with the first move of the volume."* **In its
    place `max_ceiling` is redefined as the top of every scale** — set it to
    −10 dB and the panel's 100%, LMS's 100 and a phone's 100 all mean −10 dB
    — applied as a *shift* on every position-to-dB map so every step keeps
    its size. ADR-0052 has an Amendment section; §1 and §3 are marked where
    they are contradicted rather than rewritten.
  - **[ADR-0053](docs/decisions/0053-the-panel-is-a-remote-control.md) is
    accepted and built** — *"Go"*, on
    [Finding 046](docs/findings/046-the-remote-control-path-measured.md)'s
    numbers. While a renderer holds the device the panel has no volume of
    its own: a position goes to that renderer's own control and the number
    shown is the renderer's own. LMS through the server's RPC (squeezelite
    carries nothing back from its control, and puts LMS's 0-100 through its
    own curve on the way in), Spotify through go-librespot's API, Bluetooth
    through its own control. Costs **+6 ms on Bluetooth, +10 on Spotify,
    +22–33 on LMS**.
    - **The idempotence test came first and found the fault rather than
      clearing it.** The direction the model uses is exact at every
      position on every scale; the opposite direction cannot be, because
      101 panel positions cannot name AVRCP's 128 values — 27 of them land
      somewhere else. So the invariant is **a renderer's own value is never
      sent back to it**, and `TestTheRemoteRoundTripDoesNotRatchet` pins the
      27 so nobody later closes the loop.
    - **Verified with the room silent**, using LMS's power-on acquisition
      rather than playback: LMS 25/70/45 published as 25/70/45, panel
      30/85/55 set LMS to 30/85/55, and with nothing active the panel still
      writes the DAC.
    - **The seam is measured and left to George** (Finding 046 §9): the
      panel's fallback window is −45…0 and the renderers span −38.1…0, so
      at release Bluetooth's 50% reads 58%. Moving the panel's window to
      −38.1 makes Bluetooth's two numbers identical everywhere and shrinks
      LMS's seam from 10 points to 1–6 — and changes what every percentage
      on the device means, so it is a question, not a change.

  - **[ADR-0054](docs/decisions/0054-one-curve-and-the-renderers-own-number.md)
    — one curve, ours, on each renderer's own number.** George's four
    findings on 2026-09-23, measured in
    [Finding 047](docs/findings/047-where-the-volume-actually-goes.md),
    had one cause: **nobody's volume curve was ours.** squeezelite derived
    its own from the dummy control's declared range, bluealsa applied its
    AVRCP curve, and we copied whatever dB came out. So a renderer's zero
    was −38 dB rather than silence and LMS's 0/5/10% were one value.
    - **The dummy control is a trigger now, not a scale.** Its write still
      says *when* in 0.1 ms; the number is read from the renderer (~13 ms).
    - **One curve: linear in dB over 60 dB, zero is silence.** 60 dB
      because that is librespot's `softvol` default and what George found
      works on the same DAC. Verified with the room silent: panel
      100/50/25/10/5/0% → 0.00/−30.00/−45.00/−54.00/−57.00 dB and silence,
      LMS reading the same number as the panel throughout.
    - **Finding 046 §9's seam is closed** — the panel uses the same curve,
      so the number no longer moves when a renderer lets go.
    - **Bluetooth's level left the ALSA mixer** (`--volume=none` plus
      `bluealsa_volume.py` on `org.bluealsa.PCM1`'s `Volume`). The mixer
      round trip was wrong one in three and pushed a stale value at the
      phone on every stream start, which is why a phone at maximum
      connected quiet.
    - **Acquisition asks a renderer where it is** rather than writing a
      remembered level under it.
    - **A regression caught during the work:** routing a panel change
      through the renderer took **560 ms** to reach the DAC. §6 writes the
      hardware at once — **72–96 ms**, no slower than before ADR-0053.

  - **George's pass on 2026-09-23: *"Works. Everything as expected all
    throughout."*** Three findings came out of it, all closed:
    - **Bluetooth did nothing at all** — the PCM filter said `Mode ==
      "sink"` where a client-read PCM's Mode is `"source"`, and the module
      logged nothing when it matched nothing, so a total failure looked
      like a phone not being connected ([LESSONS](docs/LESSONS.md) case 17).
    - **The 5%/4% steps are not ours.** The panel's own slider moves in 1%
      steps, measured; the coarseness is LMS's and Spotify's own apps.
    - **The taper is cubic**, not linear in dB. His remedy — a wider span —
      goes the wrong way, and the record carries the table that shows it.
    - **The volume drawer never closed.** A touch pinned it open and
      nothing un-pinned it, so a drag on the panel's own slider left it up
      until somebody tapped it away — and while pinned, no change from
      elsewhere could arm the timer either. It is now held open only while
      a finger is on it. Verified on the panel through CDP: held 5 s stays,
      4 s after lifting it is gone, and an external change opens and closes
      it at 3 s.

  **Recorded for the next step, on his instruction:** the registry's
  `travel_curve` row becomes **Volume curve**, offering **Cubic** and
  **Linear (dB)** — the two that now exist. **Recorded, not wired.**

  - **Four of the eight Audio rows are wired** (2026-09-23), each
    exercised through the API the panel and the phone use:
    **Volume curve** (Cubic / Linear (dB) — changing it moves the level
    under an untouched slider, −15.50 ↔ −30.00 dB at half travel);
    **Boot volume** (read by the boot unit, so it applies at the next boot,
    with `core.toml` as the fallback for any failure to read it);
    **Remember level per renderer** (read per acquisition; off means
    everyone starts from the boot level, and what is stored is kept);
    **Volume-managed renderers** (readonly, now reporting what the adapters
    declare). All four drop `[H]` in ADR-0022's inventory.

  - **Audio is fully wired** (2026-09-23), and half of it by deletion.
    George's four questions on the rows produced three removals and one
    change of unit:
    - **The per-renderer memory is gone** — `renderer_volume.py`,
      `volume.json`, `restore_volume_floor_db`, the `per_renderer_volume`
      row. *"Don't we ask each renderer the volume when they take over?"*
      We do: **12 acquisitions since ADR-0054 §5, 12 answers, 0
      fallbacks**, and the renderer's own memory is the real one. A
      renderer that does not answer is now left alone.
    - **The boot volume is gone** — the unit, the row and
      `config.boot_volume_steps`. Measured over two boots (Finding 047
      §10): the converter comes up at **−20 dB of its own accord**,
      nothing carries a level across a boot, and nothing plays before a
      renderer acquires. ADR-0018's "fixed safe level" is amended out;
      **the `alsa-restore` mask is the half that survives and is now
      load-bearing.**
    - **`restore_floor` and `boot_default_scope` are out of scope**, his
      call — `[?]` rows, decisions owed rather than behaviour missing.
    - **Maximum volume is a percentage.** *"if we say 80% then the max
      output can only be 80% of the max volume"* — measured: with no
      ceiling the panel at 80% gives −5.00 dB, and with the ceiling at 80%
      the panel at 100% gives −5.00 dB.
    - **Volume curve** is the one addition: Cubic (shipping) and Linear
      (dB), the two that exist.
  - **[ADR-0046](docs/decisions/0046-fixed-output-hides-the-slider.md) is
    built** — the oldest unbuilt decision in the project. The slider is
    *absent*, not disabled; both triggers carry a padlock; the drawer
    still opens onto its sentence; `state.fixed_output` is published
    rather than inferred; and the change waits for playback to stop.
    Verified on the device and on the panel over CDP. **Four of its Opens
    close on the same day's work**, and the one that stays is named: a
    phone's own slider still moves and now changes nothing.

  **9i and 9j are built**, and George has passed both on the device.

  **Three things closed on 2026-09-23 after his pass:**
  - ~~**Two skins render wrong and are no longer offered**~~ **Both are
    fixed and offered again, and the corpus is 99**
    ([Finding 050](docs/findings/050-two-skins-name-the-wrong-background.md),
    on George's *"Check all and don't just exclude, but try to fix
    them."*). `111G5_Teletronix S+M` named the **spectrum's blank panel**
    as its dial face — the same file `spectrum.txt` uses — so PeppyMeter
    drew a blank frame over the left dial and repainted under the needle
    out of the wrong picture: George's overlay and his trails, one cause.
    `107G5_Marantz S+M` had the identical defect and nobody had reported
    it. **Checked mechanically over both packs: those two are the only
    ones**, and the image now points each at its own `screen.bgr`, with a
    build check that refuses any skin that repeats it.
    `108G5_Kenwood Rev S+M` was never broken — −227° is a reverse dial,
    and the capture that condemned it was taken with nothing playing, so
    it was a held last frame. `skins.BROKEN` is empty.
    [Finding 048](docs/findings/048-two-skins-that-render-wrong.md) is
    marked superseded where it is wrong; LESSONS case 22 is why.
  - **The spectrum bars fit their frame**
    ([Finding 049](docs/findings/049-the-spectrum-draws-more-bars-than-it-has-room-for.md)),
    on George's *"the spectrum bars are actually falling slightly outside
    their designated area in the right"*. The engine draws one global
    `size` for every skin and **ignores each skin's own `steps`**, which
    ADR-0015 records. That number was 30 and **all 22 spectrum sections
    overflow at 30**; twelve overflow at their own declared count as well
    (`Kenwood Big` wants 30 bars in an 850px frame that holds 20). The
    driver now writes the skin's `steps`, clamped to what its own
    background PNG holds. **The pipe stays at 30 bands** — narrowing it
    would cost the ten skins drawn for thirty their resolution — the bar
    sprite is not resized, and no skin file is edited. Re-measured across
    all 22: none overflows.
  - **The visualisation's settings are written down** —
    [every key both programs read](docs/reference/peppy-visualisation-settings.md),
    in plain words, marked already-a-setting / fixed-by-the-build /
    candidate / not-applicable. **Nothing in it is proposed for ADR-0022's
    inventory**; that stays George's to ask for. The five worth having, in
    order, are at the end of it.
  - **Arbitration watches one card whatever the output is** — measured
    (Finding 048 §5): with the output on the headphone jack and something
    holding it, `device_busy()` answers `False`, so the release ladder
    would hand the device over while the outgoing renderer still had it.
    `alsa.CARD_ID` has been a constant since Phase 2; ADR-0055 is what
    made a second output reachable. **Not fixed** — it wants a decision on
    whether the card follows the output or arbitration is scoped to the
    DAC by definition.

  **Needs George, and nothing else will do:**
  - **Bluetooth, on the new path, with the amplifier turned down first.**
    Nothing has been through `bluealsa_volume.py` but unit tests. And the
    failure mode is *loud*: `--volume=none` means bluealsa no longer
    attenuates anything, so if the daemon does not apply the phone's level,
    the stream arrives at full scale.
  - Whether a phone's slider follows the panel's — the one leg of ADR-0053
    that is still inference.
  - Spotify's number path with a real session.
  - **How 60 dB sounds.** It is a measured starting point, not a measured
    answer; `RENDERER_DB_SPAN` in `volume.py` is one line.
  - Whether the 0.8 s `SETTLE_S` gate is still needed for LMS. It exists
    because LMS fades the control on pause — but the number now comes from
    the server, and LMS's *reported* volume may not move during a fade at
    all. If it does not, a change made in an LMS app would reach the DAC in
    ~15 ms instead of ~400. **Needs playback to test.**
- **9j — which output. Built 2026-09-23**
  ([ADR-0055](docs/decisions/0055-which-output-the-device-plays-to.md)).
  Four playback outputs, measured, and **two of them have no volume control
  at all** — so choosing one *is* ADR-0046's fixed output, which is why 9i
  and 9j were one conversation.

  | chosen | `output.conf` | control | `fixed_output` |
  | --- | --- | --- | --- |
  | HiFiBerry DAC+ HD | `hw:sndrpihifiberry` | `DAC` | false |
  | Headphones (3.5 mm) | `hw:Headphones` | `PCM` | false |
  | **HDMI 1** | `hw:vc4hdmi0` | **none** | **true** |

  - **Discovered, not written down.** There is no `dtoverlay=hifiberry-…`
    in `config.txt` — the HAT's EEPROM is read at boot — so the card name
    *and* its control's name belong to whatever board is fitted.
  - **All four are offered** and the empty socket says **`HDMI 2 — nothing
    connected`** (George: an absent option explains nothing). The suffix is
    display only, so plugging a cable in does not orphan a stored choice.
  - A switch rewrites `output.conf` and restarts the renderers **and the
    daemon** — which is how the new card's control name is picked up.
  - **A bug it found in itself, seconds after deploying:** "nothing stored"
    fell through to *the first output with a volume control*, which here is
    the Pi's own headphone jack (`aplay -l` lists card 4 before card 5), so
    a restart silently moved the device off the HAT. Nothing stored now
    means change nothing.

**The 2026-09-22 design drop is applied, all four parts of it.** George:
*"Please be thorough and check the designs I import — do not guess or
inferr."* The drop is vendored whole at `design/` and is the point of truth
for what it draws; **the panel stays the point of truth where the two
differ**, which the vendoring commit lists.

- **Now Playing's meta column grew** — tabs 19, title 54 at 1.06 clamped to
  two lines, artist 35, album 30, year 25 mono. **The Track tab's synced
  strip is three lines, not five**: 32px, the neighbours at 0.42, and a
  30%/70% mask on the window so they are ghosted rather than merely dimmer.
- **The idle screen has two forecast layouts**, `3 days` and `None`, and
  carries feels-like, wind, sunrise and sunset.
- **The visualisation picker is built** — a list of 380px with a preview
  pane beside it. Tapping a row previews; the 60px button writes.
- **`device_name` carries a warning**, and `warn` now has a second form: a
  string is about the row and is up the whole time the sheet is open. The
  drop's sentence says saving restarts the services and stops playback;
  [ADR-0048](docs/decisions/0048-how-the-device-name-reaches-four-services.md)
  applies the name at the next restart and stops nothing, so the row reads
  George's own line instead (ADR-0044 §2 records the deviation).

**George's five findings on the drop are in** (2026-09-22, after the first
pass): the renderer's mark stands alone at 32px with no word beside it; a
phone's taps no longer end the visualisation; the picker follows the corpus
and the fourth word is **All**, not Random; the `device_name` warning is his
sentence; and `idle_minmax` is gone, so the registry is 71 rows.

**The one that was not a design change:** *"Changing skin during playback
while being in visualization mode, stops showing the visualisation."* The
cause was the touch report. ADR-0036 counts a touch as attention and
attention takes the meter down — and the panel tells the daemon about
touches, because the daemon cannot see them. That report was wired to the
window rather than to the surface, so **a tap on a phone ended the
visualisation on a device in another room**. `/surface` already knew the
difference (ADR-0035 §6); the report is the panel's alone now.

**Both of those rulings came back the same day:** `skin` went into
ADR-0022's inventory as [N] (*"Record as N"*), and the Artist tab's name and
the Release tab's title follow the grown tokens (*"Grow both"*).

**9h is finished, and the last of it closed a hole that had been open since
9d.** `skin_corpus` and `skin_rotate` were in the registry with nothing
behind them — unwired, so a write was refused.
[ADR-0051](docs/decisions/0051-the-visualiser-reads-its-selection-from-a-file.md)
gives the renderer a file to read: `/run/gexis/visualisation.json`, written
by the daemon and polled in the driver's frame hook beside
`nowplaying.json`. No restart, no new channel.

**The corpus is every pack — 99 skins, 77 meters, 9 spectrum, 13 both.** The
engine reads one `meters.txt` (`gelo5/templates`, 71 skins and not one
spectrum), so two of the four corpus words would have offered nothing; the
driver loads all four template directories and swaps `base.path` around the
factory, as it already swaps `meter`. **It said 84 for a few hours** — the
stock pack was excluded on the grounds that the spectrum engine was pointed
at Gelo5's sections, which described one hardcoded line rather than the
device. George: *"there were 99 skins in total — why are you telling me now
that there are only 84?"* The engine follows the skin's pack now.

**And the visualiser was black when he tapped the button** — three faults in
a row, all introduced the same day, all fixed and this time **verified as
pixels**: the spectrum config ships root-owned while the unit runs as `pi`,
so the write that chooses a section killed `main()` after the display
existed and left a window with no loop behind it, owning every touch; a
spectrum-only skin with no engine draws nothing at all; and the engine's own
`meter = random` overwrote the chosen skin on the first frame.
`docs/LESSONS.md` case 15 is the reason it got that far: **a log line is the
process's account of itself, and on a screen only pixels are evidence.**
`grim` on the device takes the capture, and Claude can read the PNG.

**Two more he found after that, and only one of them was new.**

- **The needles shook, and had been shaking since Phase 5.** The engine's
  pipe drain reports *zero level* when a poll finds no new frame, and 47 of
  117 reads in five seconds found none while music played — each zero going
  into a four-deep smoothing buffer. The drain now holds the last frame,
  which is what our own `FifoSource` has always done with the same pipes.
  Measured before and after, frame by frame; the pre-9h driver paces the
  same, so nothing this week caused it.
- **The picker's preview was cropped on a laptop.** A 16:10 box at the full
  width of the pane, with the picture `cover`ed into it: on a wide, short
  window `max-height` beat `aspect-ratio` and the skin lost its edges. The
  picture keeps its own shape now, at four viewports checked.

**What 9h landed before that:**

- **Three kinds of skin, not two** — 77 meters, 9 spectrum, 13 both, counted
  on the device. The old two options were *directories*, and `templates/` is
  not the meter corpus. The row is **Skins**: VU meters / Spectrum / VU
  meters + spectrum / Random.
- **[ADR-0050](docs/decisions/0050-skin-previews-are-the-skins-own-picture.md):
  a preview is the skin's own `screen.bgr`** — no render, no cache, no
  change detection, and **9h needs no image build**.
- **The home strip, all three shapes**, after George corrected a finding
  that said two of them were impossible (`docs/LESSONS.md` case 14). They
  are `browselibrary` **sorts**, not fields or tags, and need no plugin.
- **`viz_stop` wired**, and `viz_timeout` moved from seconds to the minutes
  the design draws. Both read per tick.
- **`idle_clock`**, so the panel can be a picture frame (2026-09-22).

**The device is carrying deployed files, not a built image.** The daemon,
the panel and **`driver.py`** were rsynced to it for this work. The driver
is the new one: `image/stage-gexis/05-peppy/files/gexis-peppy-driver.py` is
what a build would install, and until that build the device and the image
differ.

**9g — the idle screen — is done.** Both providers chosen the way Finding
030 chose the enrichment ones ([Finding 043](docs/findings/043-the-idle-screens-two-providers.md)):
**Pixabay** on the pictures, **Open-Meteo** on George's answer to the
question that decided it — *a Gexis is not sold*, so a non-commercial free
tier is one this appliance may use.
[ADR-0047](docs/decisions/0047-the-idle-screen-gains-backgrounds-and-weather.md)
is **Accepted** and has one open question left, which is George's: whether
artist pictures should avoid the artist currently playing.

**What the panel shows now:** a drifting clock and date over one of four
backgrounds, a forecast bar across the bottom in three icon sets, and the
credits both providers require on one line along the bottom. Artist
pictures come from **fanart** with LMS behind them (six for six on George's
library); wallpapers come from Pixabay, random across the chosen categories;
on-device pictures come from an SMB share; and a picture that `cover` would
cost more than a quarter of is shown whole over a blurred copy of itself.

**One of the two things a build still owes: [ADR-0049](docs/decisions/0049-the-pictures-folder-is-a-share.md)'s
image stage has never been through one** (the other is the new `driver.py`,
above). samba is installed and the
share verified on the device — a picture written to it over SMB was drawn
on the panel — and the stage that bakes it is written with `testparm`
assertions that pass against that device. **The next rebuild is what proves
the stage**, and it is the first thing on this image that is neither ours
nor a renderer.

**Nine things the panel found that no test would have**, which is the
argument for the gate:

- **The design draws this screen and the first build did not look for it** —
  it is in `source/Now Playing.dc.html`, not a file of its own, and
  `screens.md` says so in its first paragraph.
  **[LESSONS](docs/LESSONS.md) case 13**, one day after case 12 and the same
  shape: a summary read in place of the source. The screen was rebuilt to the
  drawing.
- **A flat 4px contour reads grey at 21px** — 62% of the ink against the
  clock's 35%, measured over a controlled field. It tapers with the type now.
- **`object-fit: cover` keeps 35% of a portrait's height**, which is where
  the blurred-halo fit came from. The halo costs nothing: 16.8 ms a frame
  with it and without.
- A fixed scrim cannot keep a moving clock legible, and a radial gradient
  still opaque at its box's edge draws a rectangle over the picture.
- **Artist pictures were asked for at 300 px and drawn at 1280** — Finding
  035's defect upside down.
- **The geocoder does not take what the row asks for**: `Berlin, DE` — the
  design's own example — returns nothing from Open-Meteo, where `Berlin`
  returns five. The daemon splits the string now and ranks the answers.
- **An unreachable geocoder was reported as a place that does not exist**,
  which sends the user to fix a row that was already right.
- **Rotation was hidden for every background but Pixabay**, though the
  behaviour was common — the worst kind of gap: the feature works and
  nothing offers it.
- **Pictures in folders were invisible**, and the path guard that assumed one
  segment had to become one that resolves and checks containment.

**Known and deliberate:** an empty on-device folder shows the clock on black
with no explanation *on the idle screen* — the region blanks, never the
screen — and the settings row is where it says why.

**Two measured traps recorded there:** the Art Institute's IIIF image server
403s without an `AIC-User-Agent` header (with a browser User-Agent too — the
JSON API answers fine without it, so it fails only when an image is
fetched), and NASA's APOD carries a `copyright` field naming a photographer
on most days, so it is not the public-domain source it is assumed to be.

- **9a** — the decisions: ADR-0044, 0045, 0046 Accepted, ADR-0022 amended
  for the catalogue/surfaced split, ADR-0047 opened for the idle screen.
- **9b** — Now Playing: one header instead of two, the album year from LMS
  first, the source mark de-pilled, and the synced lyrics fixed after the
  panel check.
- **9c** — the Library sweep: Add to queue, the artist route out of a New
  Music album, radio as a tinted grid, genre pills, the About error branch.
- **9d** — the settings vocabulary and the Settings screen, **appended on
  George's instruction** to cover Wi-Fi and LMS discovery: see below.

**The diff it is all built on is
[Finding 042](docs/findings/042-the-device-against-the-new-design.md)**, and
its §9 records the five panel-check findings and what each turned out to be.
Ground truth is the device: `npm run build` on `ui/` reproduced
`/opt/gexis-ui`'s bundle byte-identically, settings came from live
`/settings`, state from a real `/state` frame, and the design's inventory
from evaluating its own `INV` literal rather than its prose — which matters,
because the two disagree.

**9d is the one to read about before touching Settings.** ADR-0044 now
carries **seven** mechanics, not six: `grouped` was counted as a fixture of
the drop's demo and is a mechanic. `visible` is computed in the registry and
published per row — the panel filters and does nothing else. A `list` with
`kind: "server"` stores a value and every other list does not. 54 rows became
56; 36 are surfaced.

**Where a list's items come from is answered for two of three.**
`core/src/gexis_core/wifi.py` (NetworkManager through `nmcli`, daemon is
root so there is no polkit agent) and `discovery.py` (UDP broadcast on 3483,
protocol verified against the real server — `IPAD` comes back absent, so the
address is the datagram's source). Generic routes `GET`/`POST
/settings/{key}/items`. **Bluetooth's trusted devices are still 9f's** and
that row opens on its own empty state.

**Two traps in `nmcli` that fail quietly**, both now tested: `-t` output
escapes colons inside values, so `split(":")` cuts a network called `2:1` in
half; and a saved connection is not named after its network — this image's is
`preconfigured` — so SSIDs are matched through `802-11-wireless.ssid`.

**What 9d taught about the plan itself.** George found four things on the
panel that no subphase owned. Two were scheduled nowhere at all (Wi-Fi, LMS
discovery); `handoff_duration` and `reboot` were design keys owed to nobody;
and `grouped` was a mechanic nobody had counted. **The list of design keys
the registry lacks is now written out in the test by its owing subphase** —
nine to 9g, four to 9h — so the next omission fails a test rather than
waiting to be found on hardware.

- **9e** — one `device_name`, written to all four and applied at the next
  restart ([ADR-0048](docs/decisions/0048-how-the-device-name-reaches-four-services.md)).
  Gate run end to end: renamed to `SofaPi`, rebooted, all four advertised
  it; renamed back, rebooted, all four followed.

**9e's gate found two defects no amount of reading would have**, and that is
the argument for having it:

- **BlueZ never read `main.conf`'s `Name =`.** Its `hostname` plugin
  overrides it — the vendor file says so two lines above the setting — and
  this image had been setting it since Phase 2. The build asserted its own
  `sed` had matched, which passed every time and meant nothing, because the
  hostname was the same string. `/etc/machine-info`'s `PRETTY_HOSTNAME` is
  the real mechanism. **[LESSONS](docs/LESSONS.md) case 9.**
- **A rename locked the panel out of its own browser.** Chromium's profile
  lock is `<hostname>-<pid>` and it refuses to start when that hostname is
  not the machine's — a two-button dialog on an appliance with no keyboard.
  `gexis-kiosk-start` clears the three Singleton entries before launching.

**And one in the deploy, worth knowing before the next one.** `rsync -a` put
the repository's `644` over the `755` the image installs, so Chromium never
started while `systemctl is-active gexis-kiosk` still said `active` — the
unit is labwc, and labwc was fine. **After any kiosk restart, check
`journalctl -u gexis-core | grep 'GET /assets/index-'`**, which cannot be
true unless Chromium started, loaded and reached the daemon, and names the
build on screen. The eight scripts installed `755` are executable in git
now. **[LESSONS](docs/LESSONS.md) case 10.**

**9f — Bluetooth pairing ([ADR-0045](docs/decisions/0045-bluetooth-pairing-confirmation.md))
— is built and on the device.** Our own `Agent1` replaced `bt-agent
--capability=NoInputNoOutput`, the request reaches the panel, accept and
reject work, and the countdown is the agent's rather than the panel's.
`bt_discoverable` is implemented for real, all three options, with
`DiscoverableTimeout=0` for Always — the "3 minutes" defect. `bt_trusted`
has its item list and `Forget`, which 9d left to it: it was the one `list`
with no source. Devices come from BlueZ's object tree, **paired only** (the
tree also carries everything the adapter has merely seen while
discoverable), and Forget is `Adapter1.RemoveDevice`, not `Trusted = false`
— clearing the flag leaves the bond and the phone reconnects.

**Checked on the panel, 2026-09-21** (George: *"Works fine"*): his Pixel is
paired and trusted, Settings › Sources › Trusted devices lists it with a
Forget, and the sheet opens instantly. **The reject and expiry paths have
not been driven since the freeze was fixed** — accept has, by the pair that
is on the device. Forgetting the phone from both ends is what sets up
driving them.

**Two panel defects found after that code was written, both fixed.** The
pairing frame froze — countdown still, Reject doing nothing — while every
server-side check passed, because an `$effect` read what it wrote and Svelte
stopped updating the whole tree ([LESSONS](docs/LESSONS.md) case 11); and a
failed answer left both buttons disabled, a `try/catch` with no `finally`.

**And the `bt_trusted` row read "None" with a phone paired** (George, on the
panel, 2026-09-21): the row's value is a count, the panel counted `row.items`
as the design does, and the design carries its items inline where ours were
fetched when the sheet opens — so the row could only ever read the empty
answer. **The row and the sheet are two surfaces, and the sheet working says
nothing about the row.**

**[ADR-0044](docs/decisions/0044-settings-row-vocabulary.md) §1 is amended
for what that turned out to be about: when a `list`'s items arrive.** George,
seeing the sheet still flash as it opened: *"Isn't the list static? It should
be instant."* It was not static — the sheet refetched on every open and began
in its searching state whatever the answer cost. Measured on the panel frame
by frame: **spinner from 27 ms to 36 ms, devices at 56 ms**, over a BlueZ read
of 22–29 ms. So:

- **`discover: true`** — LMS discovery (2.5 s) and a Wi-Fi scan (seconds) go
  looking when the sheet opens and say so while they look. `wifi` carries the
  flag now; it always searched and only the server row said so.
- **no `discover`** — `bt_trusted`'s items are one `GetManagedObjects`, so
  they arrive **with the row** in `/settings` and the sheet opens drawn, the
  refresh running behind it. The same read gives the row its count.

Re-measured after the change: **the searching block never enters the DOM at
all** (a MutationObserver over the whole body for 600 ms), and the Wi-Fi sheet
still shows its own, with its own words. The three kinds are `server`,
`network` and `device` now — the two-way branch had `device` falling through
to Wi-Fi's side of it, so the Bluetooth sheet said it was *"looking for
networks"* and *"sweeping every channel"*.

**Design Claude is owed the `device_name` restart warning text.** The note
shipped in 9e says the true thing plainly as a placeholder.

**Two settings rows still report behaviour the code does not have**, each
found by measuring rather than reading: `travel_curve` names a curve 34 dB
quieter at mid-travel than ADR-0034's slider, and `max_ceiling` is `None`,
so no ceiling is enforced. The third was `bt_discoverable`, which reported
"3 min after boot" that nothing chose (BlueZ's 180 s default reverting an
untimed `discoverable on`) — **9f implemented it**, and Always now sets
`DiscoverableTimeout=0`.

**`device_name` is refused** — `HTTP 409 "not wired yet"`. The four service
names agree only because each was set to the same literal at build time.
Nothing propagates. That is 9e.

**Finding 042 §8 says what it did not cover, and George closed the gap-hunt
on cost.** Now Playing and Settings were compared element by element; Library,
WaitingServices, Handoff and Idle were sampled, and sampling missed real
items — George named six in one breath. Two are confirmed in the finding;
three are unchecked and are expected to surface during 9c, where he judges
them on the panel. **The unused instrument:** the drop ships `verify.html`
(38 checks) and `geometry.json` (landmarks at 1280×800, 3 px tolerance) —
Now Playing only, cheap to run, not yet run.

**The boot-screen work from earlier in this session is done and paused.** The
still is on the device, the handover is 10 ms, two of three flashes are
accounted for and one is unexplained; a red-`swaybg` diagnostic is prepared
and not run. [Finding 041](docs/findings/041-the-ten-seconds-with-no-animation.md) §§8–10.

**Three build-side hazards found by the survey, none fixed:**
`49b79c6` changed `systemctl enable gexis-splash-backstop.service` → `.timer`
without a `disable` or an `rm`, and `01-run.sh` still installs the service
unit, so a warm build can keep the old symlink and quit the splash at
`multi-user.target`; `01-firstboot/files/firstrun.sh:67`'s
`sed -i 's| systemd.run.*||g'` is greedy and would strip **every** quieting
option and `splash` itself — inert today only because it targets a placeholder
path, so the obvious-looking fix is the one change that silently kills the
animation; and `02-run-chroot.sh` asserts nothing about the systemd wiring it
creates.

**ADR-0041 — scrims dim but do not blur** is the substantial result of step 1.
`backdrop-filter` costs 24.5 ms a frame in draw-and-submit against a 16.7 ms
budget with the CPU idle; the compositor reads the live screen back every
frame, which is a tile-based GPU's worst case
([Finding 037](docs/findings/037-why-a-blurred-scrim-costs-the-panel.md)). Not
the radius, not the area, and Vulkan is worse. **It does not reach the target
on its own:** the rail goes from ~15 fps to ~36 against a 55 fps floor.

**The build now caches its downloads** ([ADR-0042](docs/decisions/0042-a-local-cache-for-vendored-downloads.md)):
six artefacts, ~308 MB, content-addressed in `~/.cache/gexis-player/downloads`,
proven on the second build — zero bytes fetched. **It is explicitly not a
backup**: it protects this machine, not a fresh clone. A mirror we control is
deferred and is the only thing that answers George's actual question.

**Two pieces of Phase 9 groundwork are done and unused**, both off-device and
both waiting for the sweep:

- **The unwired-UI audit** (criterion 2). All 66 interactive elements traced.
  One real dead control, fixed then; **the latent trap it named was real and
  is now closed** — `confirmSheet()` had no path for a wired `action` row and
  `lib/settings.js` never sent `POST`, so the first action ever wired would
  have had a silently dead button. `reboot` was that first action, in 9d,
  and `runSetting` is the missing call. The audit predicted this exactly.
- **The settings wiring map** (criterion 1). Of 48 unwired rows: 14 are a read
  away, 19 need a branch, 4 need the feature built, 11 need a route or a
  sub-screen. `viz_timeout` is read by the daemon but missing from `wired`, so
  the phone cannot change a setting something actually consults.









**Phase 7a — panel responsiveness — is closed** (2026-09-18). Artwork at the
size drawn, an instrument that survives its own scrutiny, and a baseline:
[Finding 034](docs/findings/034-what-the-panel-presents.md). **The target is
three things** (George): under 2 % of frames dropped, no interaction below
55 fps, and his own go-ahead. Everything failed it when measured, which is
the point of having it. **The open question, now Phase 9 criterion 0: why is
a playing panel never idle?** 71 % of wanted frames dropped with nobody
touching it; PeppyMeter is already eliminated.

**Read Finding 034's six instrument faults before measuring anything here.**
Each produced a confident, plausible number: partial frames counted as
dropped (17.9 % on an untouched panel), fixed coordinates that scrolled
nothing (25-31 %), playback uncontrolled (57.7 % where the same control had
said 0.00 %), every frame counted twice (102 fps on a 60 Hz panel), a rail
measured with nothing below the current track to scroll, and thin runs
averaged in.

**Next: Phase 8 - enrichment and lyrics.** It needs an ADR choosing the
providers before any code;
[Finding 030](docs/findings/030-free-enrichment-providers.md) compares the
free ones and recommends a key-free combination without deciding it.

**Phase 7 — library browse — is merged (PR #19, 2026-09-18).** Every step
was built and checked by George on the panel; the last, the queue rail, on
2026-09-18. [ADR-0038](docs/decisions/0038-library-and-radio-on-the-panel.md)
is **Accepted**, `docs/DEVELOPMENT.md` Phase 7 records what each step
settled, and the step-by-step narrative is in
[the archive](docs/HANDOFF-ARCHIVE.md). What the panel has now: Home as the
library root with New Music, the album page, the artist grid and artist
page, three-pane Browse with row actions, playlists, radio, and the queue
rail with Clear and a playlist chooser. Play means in order; Shuffle all is
its own button.

**Open, deferred by George: one investigation into what makes the panel
slow.** It started as the lists (the New Music strip scrolls unevenly, the
artist grid is slow to load, open and scroll - 917 artists in one pass) and
George widened it after step 10: *with the rail built, everything is "quite
slow"*. [Finding 032](docs/findings/032-panel-frame-times-during-a-scroll.md)
says what is and is not established, and warns that the instruments lie
before they help. **One candidate is already named rather than guessed:**
the queue rail asks LMS for 500 px covers and draws them at 42 px
(`ARTWORK_SIZE` in `adapters/lms.py` serves both now playing's well and
every queue row), where the library reads already ask for the size drawn.
Candidates for the lists: rendering only what is on screen, lighter cards,
letter buckets from the core. `content-visibility: auto` was tried on the
artist grid and removed - off-screen groups are only estimated, so the jump
rail landed inside the previous letter.

**Two defects from the step 10 check are worth carrying forward as
patterns**, both fixed with a test that fails without the fix:

- **A queue that could never grow.** It was read only by the *seed* status
  query at subscribe time, and every later change arrives as a CometD push.
  All three tests over it passed, because each called the reader itself and
  none drove the push loop. *A test that exercises a function is not a test
  that anything calls it* (`docs/LESSONS.md`).
- **A Peppy screen that could not be dismissed by touch.** Whether it is up
  was known only in memory, so a daemon started *while it is on screen*
  believed it was hidden and ignored every touch, stranding the panel behind
  the meter. Any state held about something outside the process has to be
  reconciled at startup, not assumed.

**Test data on George's LMS:** playlist folder `/playlist` (George set it;
it triggered a full rescan that renumbered the library). Playlists
`gexis-test-album` (122541), `gexis-test-mixed` (122543),
`gexis-test-empty` (122544) — George removes them. Finding 029's raw replies
are at `~/gexis-findings/029-raw/` on R2D2, deliberately not in the repo
(library listing, playlist names, a TuneIn serial).

**Probing SlimBrowse can start playback.** A radio walk that followed
`base.actions.go` played a station for 45 s (Finding 029). Resolve the
command and refuse anything ending in `play` or `add` before sending.

**Corrected in this session, worth not repeating:** Claude raised "playing
from the library must power LMS on" as an open decision. It was not: LMS's
auto-power-on on play is recorded in ADR-0027 (hardware, 2026-09-12) and
Finding 019. The repo was not searched first — `docs/LESSONS.md` case 4's
corollary.

**Measured 2026-09-17 against George's LMS (read-only), now in ADR-0038:**
the `radios menu:radio` reply has no `id` on any item, so Podcasts is
excluded by its `["podcast","items"]` command; `cover_300x300` is a 173 KB
PNG where `cover_300x300_o.jpg` is a 25 KB JPEG (one album);
`ignoredarticles` is "The El La Los Las Le Les".

**Phase 8 research is recorded, ahead of time:**
[Finding 030](docs/findings/030-free-enrichment-providers.md) compares free
enrichment providers (George asked 2026-09-17). Nothing decided; the provider
choice needs an ADR when Phase 8 starts. George: API keys are a per-user
setting, so a key is not a blocker (ADR-0022 inventory row added).

**The Phase 8 image is built and verified as a file, not flashed:**
`image/deploy/2026-09-18-gexis-player-v0.2.1-272-g10fbb44-dirty.img`
(478 s, first attempt; `image/verify-image.sh` - all checks passed). **It
did not test the loop-device fix:** R2D2 had not rebooted, so the nodes
were still the ones `modprobe` made by hand (Finding 033). That test is
still a reboot followed by a build.

**The Phase 7 image:**
`image/deploy/2026-09-18-gexis-player-v0.2.1-232-g65d62e3-dirty.img`
(464 s; `image/verify-image.sh` - all checks passed, including the venv and
`/opt/gexis-ui` byte-identical to this checkout). **The device still runs the
Phase 6 image** (`2026-09-17-gexis-player-v0.2.1-202-gf3674f3-dirty.img`)
with Phase 7 hand-installed, so a reflash is what proves the image.

**The device** was flashed and provisioned 2026-09-17. Both SSH keys authorized. **After every reflash**
append C3PO's key (`provision.local.env` carries R2D2's only; George chose
not to change `provision.sh`):
`ssh pi@gexis.local 'cat >> ~/.ssh/authorized_keys' < ~/.ssh/c3po_id_ed25519.pub`,
then `ssh-keygen -lf ~/.ssh/authorized_keys` on the device shows R2D2
`SHA256:UVfvJQXw…ci4` and C3PO `SHA256:d/pT3AST…tok`.

**Phase 6 is merged** (PR #18, 2026-09-17). George called the image checks
done without item-by-item results, so none is recorded as observed
(`docs/DEVELOPMENT.md` Phase 6 status).

**The loop-device question is answered
([Finding 033](docs/findings/033-loop-device-before-a-build.md)).** The test
HANDOFF set up was run on 2026-09-18: the state before the build was the
module autoloaded (`loop 45056 0`) and **no `/dev/loopN`**, and the build
failed at `export-image/prerun.sh` with the same
`mknod: invalid minor device number '/dev/loop0 (lost)'` as ever, in 210 s.
So **the module being loaded is not what decides it - the missing device
node is**, and `image/README.md`'s recorded root cause was wrong (now
corrected there). The failed build leaves a `/dev/loop0` behind, which is
why every rerun passes. **No durable fix is chosen: it needs George, and
`sudo`.** Candidates, none tried: create a node before the build; load the
module with `max_loop=8` so udev makes `/dev/loop0-7` at boot; or put the
reload in the build script rather than in someone's memory. Until then the
first build after a reboot fails and the second passes.

**Docker group:** after the reboot `id` shows `docker` (950) directly;
`newgrp` is no longer needed. Run builds detached so the session's memory
guard cannot kill them:
`nohup setsid bash -c "make image > ~/gexis-build.log 2>&1; echo BUILD-EXIT=\$? >> ~/gexis-build.log" >/dev/null 2>&1 </dev/null &`.
Move the previous log aside first. The submodule shows `m image/pi-gen`
afterwards: expected, leave it.

**Development moved to R2D2 on 2026-09-17** (see Machines).
`~/provision.local.env.bak-c3po-key` (holds the Wi-Fi password) can be
deleted once George is happy.

**Phases renumbered 2026-09-16:** 9 is settings wiring and UI polish (new);
10 is the plugin contract; 11 Plexamp and 12 Qobuz Connect (new); 13 is first
boot.

**Issues to look at later (Phase 6 hardware rounds, 2026-09-16):**

- **Over Bluetooth, the Plexamp app reports pauses late or not at all** — about
  6 s from its own button, 4.5 s or never for a panel command. The Spotify app
  on the same phone reports in 0.2 s (Finding 028, addendum 2). A2DP's
  stream-idle signal comes 3 s after the report, so it cannot help. With
  Plexamp the panel's icon falls back after 8 s. Next step, with the speakers
  on: does Plexamp's audio stop at the tap?
- **LMS had player `gexis` on fixed volume (`digitalVolumeControl` 0), cause
  unknown.** George found it as "phone volume does nothing while the panel is
  muted, and LMS's volume bar is frozen". Measured 2026-09-16: with 0, LMS
  moves its own number but always sends full level, so no LMS volume change
  reaches the device, muted or not. Mute then became a trap, because the one
  change that ends it never arrived. Set back to 1 with George's OK; re-tested
  while playing: LMS volume reaches the DAC again, and a change while muted
  ends mute (ADR-0034). **George never touched it,** and nothing in this repo
  sets it; it worked on 2026-09-08 (Finding 008). **Checked after the 2026-09-17 reflash: 1.**
  Still unchecked after an LMS restart. Nothing warns when it is 0; a candidate for
  Phase 9.
- **Pausing LMS moved the DAC slightly** (dummy −47 → −50 dB, DAC 152 → 150)
  during the same test. Small, unexplained, not investigated.
- **After a `gexis-core` restart, a phone already connected is not active.**
  The Bluetooth adapter seeds metadata from a `MediaPlayer1` that is already
  present but never calls `on_acquire`. It only matters when the daemon
  restarts, not at boot. **Both halves are fixed** (2026-09-18):
  George saw the library's "waiting for a service" block over a playing
  Spotify track, because go-librespot announces acquisition with events and
  events are edges - nothing is emitted for a stream that was already
  running. The adapter now reads `/status` when it connects and acquires if
  something is playing, the same shape as the LMS adapter's "player already
  powered on at startup". Measured before the fix: 66 s from connect to the
  next `will_play`. **Bluetooth is the same shape and fixed the same way:**
  acquisition there is driven by `InterfacesAdded`, and a `MediaPlayer1`
  that was already present produces no such signal, so the startup scan now
  acquires when its `Status` is playing. Neither adapter acquires for a
  *paused* session: one left paused before the daemon started cannot be told
  from one somebody abandoned, and claiming it would take the device from
  whoever has it.
- **LMS once reported a position about 5 s ahead on resume**, then corrected
  it at the next pause. Not reproduced on a second try; recheck with sound.

**Follow-ups, not blocking:**

- `viz_timeout` is read by the daemon but not wired in the settings registry,
  so the phone cannot change it (ADR-0035 says wire it with its feature).
- The stock skins are Volumio-branded; Gelo5's are the image default.
- Titles too long for their box are cut with "…"; the wrapper scrolls them.
- Fonts: DejaVu for text; DSEG7 (OFL) for time. PeppyFont not vendored.
- George once saw the spectrum overlap remaining time on `dash-spectrum`;
  not reproduced in 24 rotations or a direct start.
- **Lesson candidate:** hand-started test processes multiplied because pid
  files captured the wrong pid; George saw overlapping skins. Stop by looking
  processes up, not by trusting a pid file.

**Still open from earlier:** Claude Design owes drawn number/text editors and a
corrected `design/README.md`.


## From HANDOFF, 2026-09-24 (twenty-third session) — the visualiser's four faults, 9k, and criterion 0 before it closed

# Handoff

Last updated: 2026-09-24 (twenty-third session, on R2D2 — **Phase 9: 9a
through 9j are done and passed on the device. The visualiser's four faults
are fixed and measured, its ballistics are three settings, and 9k — the
library's pictures from fanart — is built, with the portrait sweep run on
George's own library. Criterion 0 has the panel measured: the still screens
are at 0.00 %, and every scroll's cost is the background's two blurs. The
image predates all of it**)

## Start here

**Phase 9's volume work is done and passed.** 9i (the level) and 9j (which
output) were built, checked on the device by George and merged into the
branch; the narrative is in
[`docs/HANDOFF-ARCHIVE.md`](docs/HANDOFF-ARCHIVE.md) under 2026-09-23.
**Everything since is the visualiser and 9k.**

### What happened after his pass, and what it cost to find

**The visualisation had four faults, three of them one symptom.** George
kept reporting "the spectrum is flashing" and each fix was correct,
measured, and not the whole answer — [LESSONS](docs/LESSONS.md) cases 22–26
are the record of that, and case 25 is the one to read.

1. **The bars overflowed their frame**
   ([Finding 049](docs/findings/049-the-spectrum-draws-more-bars-than-it-has-room-for.md)).
   The engine draws one global bar count for every skin. **`steps` is not
   the bar count** — ADR-0015 said it was and it is the *vertical*
   quantisation — so the count is now what the artwork holds, `origin.x`
   mirrored on the right because the picture has a frame, **one number for
   the whole corpus** because the engine reads it once and the relay
   re-reads it.
2. **Two skins drew the spectrum's blank panel as their dial**
   ([Finding 050](docs/findings/050-two-skins-name-the-wrong-background.md)).
   `111G5_Teletronix S+M` and `107G5_Marantz S+M` named the wrong file. The
   image corrects both and a build check refuses any skin that repeats it.
   **`skins.BROKEN` is empty**; `108G5_Kenwood Rev S+M` was never broken.
3. **The pipe had no frames in it**
   ([Finding 052](docs/findings/052-the-spectrum-pipe-had-no-frames-in-it.md)).
   peppyalsa wrote the thirty bands as thirty separate writes, so a poll
   landing mid-frame spliced two frames together. **The image now patches
   peppyalsa to write each frame in one call.** Measured: 1 read in 239
   ended mid-frame before, 0 of 891 after.
4. **The meters follow the volume**
   ([ADR-0057](docs/decisions/0057-the-meters-follow-the-volume.md)), at a
   third of the dB — the volume's 60 dB onto a dial drawn for 20. The tap is
   upstream of the DAC, so the daemon publishes what it is cutting and the
   relay applies it.

**And [ADR-0058](docs/decisions/0058-the-visualisations-ballistics-are-settings.md):
three rows** under *Meters and spectrum tweaks* — spectrum smoothing 90%,
needle fall 400 ms, needle smoothing 240 ms — each note opening with the
value to come back to. **Those three defaults are where the tuning ended,
not where George has settled.**

**[Finding 053](docs/findings/053-fixed-output-crashed-the-daemon.md): fixed
output crashed the daemon.** Found by a check George asked for on a detail.
Deleting the per-renderer volume memory left one call behind, on the one
path only fixed output takes. Fixed and verified; the mode works.

### 9k — the library's pictures, built 2026-09-24

[ADR-0059](docs/decisions/0059-artist-portraits-in-the-list.md), on
[Finding 054](docs/findings/054-what-lms-knows-about-artist-identity.md).
**Two buttons in Settings → Enrichment**, fanart first with LMS as the
fallback, everything re-asked on every press, progress in George's own
words.

- **The portrait sweep is measured and done on his library: 917 of 917 in
  seven minutes, 525 found.** 759 distinct answers stored, 492 with a
  picture — so **about 43% keep LMS's photo**, which is fanart's coverage
  and not a fault. The grid will look mixed.
- **One walk serves both buttons.** fanart returns an artist's albums in the
  artist call, so a cover sweep makes no per-album request, and the
  release-group ids come from a 145 ms *lookup* rather than the search
  endpoint that 503s.
- **LMS cannot hold the MusicBrainz ids for us** (Finding 054 §10): no write
  path in its API, and the plugins in that space import tags rather than
  write them. A household that wants this shared tags its files with Picard.
- **Enrichment's four dead rows are wired** — the master toggle, lyrics and
  artwork each became a reason not to *ask* a provider; the confidence
  threshold is read on every ask and now gates the sweep too.

### Where it stands right now

- **The album-cover sweep was still running** when this was written — ~917
  artists at about 3 s each, so **45–50 minutes**, more than the 25–30 first
  estimated. Its number is in the settings row.
- **The image is a long way behind.** It predates all of the above.
- **Waiting on George:** whether the mixed look of the artist grid is
  acceptable. **The ballistics are closed** (George, 2026-09-25: the three
  settings are there for him to fine-tune, so the defaults need no verdict).
- **Criterion 0 is closed** with the screen opens below Phase 7a's floor
  ([ADR-0076](docs/decisions/0076-criterion-0-closes-with-the-opens-below-the-floor.md)),
  **to be revisited before Phase 13**.

### Criterion 0 — the panel measured, 2026-09-24

**Steps 1 and 2 are done: the still screens are at 0.00 %.** A pulsing badge
and a progress bar animated with `width` were what an untouched panel was
paying for (Findings 056 and 057); both are gone.

**Step 3, the scrolls, is answered — and it cost two retractions.**

- **[Finding 058](docs/findings/058-what-the-scrolls-are-not.md) withdraws
  two of Finding 055's numbers.** The instrument counted dropped frames the
  compositor had marked as not affecting smoothness, so **every figure it
  had ever printed was high by roughly a factor of two**; and
  `queue-rail-scroll` was measured on a sixteen-track queue that **moved
  0 px**, which makes the claim that ADR-0041 took the rail from 13.9 fps to
  50.0 unsupported. `albums-scroll` moved 191 px against the grid's 574.
  **Finding 055's table needs re-taking** — a corrected one is in 059.
- **The harness now refuses both mistakes**, swipes the same 170 px in every
  scene, and prints how far each run actually travelled.
- **[Finding 059](docs/findings/059-what-the-panel-pays-for-its-blur.md)
  names the cause: `filter: blur()` on `PanelBackground`.** A blur is
  re-evaluated over whatever area a frame damages, so the cost is the
  scroller's *area* and nothing about its contents — which is why Finding
  058's eight candidates were all negative. Suppress both blurs and the
  artist grid goes **25.6 fps / 33.81 % → 54.4 fps / 1.61 %**. The queue
  rail, which sits on an opaque plate that occludes the blur, does not move.
- **Layer promotion does not help and a smaller radius does not help**: a
  9 px blur costs nearly what 70 px costs. Only `filter: none` does.

**The fix that works, measured: hand the browser a small picture instead of
a filter.** The artwork URL carries its own size, so a 16 px cover stretched
over the panel *is* a blur, with no filter at all — **44.7 fps / 6.50 %** on
the artist grid, within 1 fps of removing the background altogether.

**This is a product decision, not a build task.** It changes the look twice:
`saturate(1.7)` is a filter too (keeping it costs ~2 fps), and the weave
loses its blur unless it is baked into an image — it is static, so baking
keeps it exactly. Nothing is implemented; **an ADR comes first, and George
has not yet ruled**.

**[Finding 060](docs/findings/060-the-queue-rails-own-cost.md): the rail's
own 17.9 % is two decorations.** Its plate's `box-shadow: -30px 0 80px` —
an 80 px blur, the same family again — and `.qrow__remove`, a 44 × 44 box
with a border and two rotated bars on every row. About eight frames each:
38.2 → 46.1 → **53.5 fps and 0.00 % dropped**, with artwork and text still
drawn. Measured in eight interleaved rounds after a block-by-block pass
drifted.

**[Finding 061](docs/findings/061-the-background-wants-a-layer-of-its-own.md):
the fix is one line and it is invisible.** `.bg { will-change: transform }`
takes the artist grid from **27.8 fps to 52.9**, as good as deleting the
background, and is pixel-identical — max difference 2 of 255, photographed
paused. **It also corrects Finding 059 and a report to George**: three of
059's rows used `[aria-hidden='true'] .bg`, which matches nothing, so
"layer promotion does nothing" was three more control runs.

**And `kNotOpaqueForTextAndLCDText` is confirmed.** With
`--disable-lcd-text` every scroll reads `SCROLL_COMPOSITOR_THREAD` and the
display draws **~58 frames a second** on both the grid and the rail. The
first reading of that flag was wrong: `PipelineReporter` under-counts a
scroll the compositor drives, said 11.7 fps, and George was told the cure
was worse than the disease. The harness now reports `drawn/s` beside it.
**The flag was tested and reverted; the device is back as it was.**

### Next

**Four decisions are with George**, with numbers and pictures: the one-line
background layer, the flag, the rail's shadow and the rail's remove button.
Nothing is implemented and each needs an ADR first.

**And the device has a hardware flag worth George's eye.** `vcgencmd
get_throttled` reads `0xd0000`: under-voltage, frequency capping and the
soft temperature limit have all *occurred* during this uptime — historical
bits, none current, at 74.5 °C and a full 1.8 GHz. Not a UI measurement,
but it is the kind of thing that makes measurements wander.

## From HANDOFF, 2026-09-25 (twenty-fourth session) — Phase 9 closing, all five criteria, as it carried them

# Handoff

Last updated: 2026-09-25 (twenty-fourth session, on R2D2 — **Phase 9 is
COMPLETE. All five criteria closed on George's own word, in one session:
criterion 0 on lived judgement with the opens below the floor, 1 with every
surfaced settings row acting, 2 with the check that was lying about two rows
fixed, 3 with his review's three findings, 4 with the handoff's own list
triaged. Next is Phase 10, the plugin contract.**)

## Start here

**Criterion 0 is closed** and
[ADR-0076](docs/decisions/0076-criterion-0-closes-with-the-opens-below-the-floor.md)
says so honestly: the scrolls reach 56.9–59.5 drawn/s at 0.00 % dropped, and
**the screen opens are 30–53 fps at 2.5–5.6 %, below Phase 7a's floor of 55
and 2 %** ([Finding 067](docs/findings/067-what-the-panel-presents-at-the-end-of-criterion-0.md)).
George closed it on lived use — *"the panel feels fast based on current
interaction"* — not on the numbers. **Revisit before Phase 13**, the setup
phase, when the panel stops being his.

**Phase 9 is complete**, and the five closures are recorded where they were
written — `docs/DEVELOPMENT.md`, each struck through with the closure above it
and the original text kept below.

- **0 — the panel meets Phase 7a's target.** Closed on lived judgement, not on
  the numbers: scrolls reach 56.9–59.5 drawn/s at 0.00 % dropped, **the opens
  are 30–53 and 2.5–5.6 % against a floor of 55 and 2 %**
  ([ADR-0076](docs/decisions/0076-criterion-0-closes-with-the-opens-below-the-floor.md)).
  **Revisit before Phase 13.**
- **1 — every ADR-0022 row wired or scoped out.** Checked against the running
  daemon: of 74 rows, no surfaced row is unwired and none carries a `?`.
- **2 — no unwired UI remains.** Four generated lists. It found one thing, and
  the thing was the check
  ([Finding 071](docs/findings/071-what-the-panel-shows-that-does-nothing.md)).
- **3 — the review pass with George.** Three issues, all fixed.
- **4 — the handoff's issues triaged.** Ten items
  ([Finding 074](docs/findings/074-the-handoffs-issues-triaged.md)).

### What was wired this session

Three commits, in this order, each verified on the hardware before the next:

1. **The device says which build it is.** `version` and `image_build` read
   `/etc/gexis/image.info`, which the image now writes — nothing on a running
   device could report it, because the `.info` beside the image is on the
   build host. A device flashed before that stage existed says `unknown`
   rather than showing an empty row.
2. **Three handoff rows** — `restore_transport`, `show_transition`,
   `handoff_duration` — read where they are used, so none needs a callback.
3. **Reclaim, and the two Bluetooth rows.** `reclaim_lms` takes the device
   back for LMS when a session ends, **off by default and opt-in by row**:
   ADR-0027 declines to do it, and the reclaims that were measured were
   spurious — a Spotify session ending because a phone locked would drag LMS
   back on. `bt_pairing` needed more than storing, because the capability is
   fixed when the BlueZ agent registers and `NoInputNoOutput` means BlueZ
   never asks at all — so a change unregisters and registers again.
   `bt_autotrust` was read per request already and simply was not settable.
   **ADR-0022's note for it was stale**: there is no
   `gexis-bluetooth-trust.service` in the image; the agent does the trusting.
4. **[ADR-0077](docs/decisions/0077-a-source-that-is-off-is-not-running.md):
   a source that is off is not running.** The last four rows — the three
   `Enabled` toggles and `headless`.
5. **The two orange dots**, both found by George reading the screen. The dot
   means a row's marks carry `?`, a decision still owed. `version` and
   `image_build` were still asking one that had been answered when they were
   wired; `version` says `unknown` correctly on this image, and `built` now
   falls back to `/etc/rpi-issue`, which pi-gen writes on every image, so it
   reads **2026-09-19**.
6. **[ADR-0078](docs/decisions/0078-the-transition-screen-waits-for-the-threshold.md):
   the transition screen waits for the threshold.** `handoff_threshold` showed
   `1` with no slider because a `number` row only draws one once it is wired —
   and it had stayed unwired because **nothing had ever read it**. It now means
   how long a takeover has to be in flight before the panel explains it; 0–3 s
   in 0.5 s steps, 0 being the old behaviour. Five runs on the panel
   ([Finding 069](docs/findings/069-the-transition-screen-against-the-threshold.md)).

### ADR-0077, because it is the one with teeth

Off means the renderer's unit is stopped **and disabled**, its adapter is not
watching, the state reports it unavailable, and arbitration refuses it. Three
things worth carrying forward:

- **Disabled, not just stopped.** A row whose effect ends at the next boot is
  a row that lies the second time you look at it.
- **A row only the panel honoured would not be a switch.** Spotify Connect is
  advertised on the network, squeezelite is a player in the LMS app, and a
  Bluetooth device is in a phone's settings screen. So Bluetooth off **powers
  the radio down** as well as stopping `bluealsa-aplay`, and disables the unit
  that unblocks rfkill at boot.
- **The gate is in the core, not the adapters.** ADR-0013 says the three
  defaults implement the public plugin contract; a plugin that read a settings
  row named after itself would put that row in the contract. The adapter's
  `run()` is wrapped instead. That also ends what would have been permanent
  noise — with go-librespot stopped, the Spotify watch retried every five
  seconds forever.

**`systemctl disable --now go-librespot.service` measured 7.0 s**, all of it
stopping the unit, so the call goes through `asyncio.to_thread`. Inline it was
seven seconds in which the daemon answered nothing. After: the row's own `PUT`
returns in 18 ms and the next request in 5 ms while the unit is still stopping.

**`headless` stops three units** — kiosk, visualiser, and the panel warm-up
that is pure boot cost with no kiosk to warm for. Turning it on from the panel
closes the panel; it is reversible from a phone, and only from a phone. 12 s
to the panel gone, 20 s to it back.

7. **[ADR-0079](docs/decisions/0079-with-lms-off-the-panel-is-two-screens.md):
   with LMS off, the panel is two screens.** George's answer to the question
   ADR-0077 left open — *"Library, browse and radio go with it."* Nothing
   playing is the waiting marks at 1.8× with a settings icon in the corner;
   something playing is Now Playing as the root, Home button become Settings,
   artist line inert, no mini strip. **The row decides it, not
   `availability.lms`**, which also goes false when the server is merely
   unreachable. Six states on the panel
   ([Finding 070](docs/findings/070-the-panel-with-lms-off.md)).

**Both dots are gone**, and no surfaced row carries a `?` any more.

**And building screen 7 found a bug in ADR-0077**: switching off the *active*
renderer left it active forever, because cancelling its watch is also how the
release event stops arriving. The panel showed a stopped Spotify's track,
artwork and progress bar indefinitely, while the same payload said the renderer
was unavailable. Fixed with one `relinquish`; [LESSONS](docs/LESSONS.md) 39 is
the part worth keeping.

## From HANDOFF, 2026-09-25 — how Phase 10 was planned, as it carried the plan

### How Phase 10 was planned, and what the plan got wrong

**Planned 2026-09-25 and reshaped by three of George's decisions**: themes
leave for Phase 14, the three default renderers **stay in the core process**,
and **Plexamp replaces Qobuz** as the contract's fourth-renderer proof, because
Qobuz needs a partnership and a private repository and that put the only proof
two phases out.

Keeping the defaults in place makes ADR-0013's claim — *"implemented against
the public plugin contract, not special-cased"* — untrue as written, so
[the record is amended](docs/decisions/0013-defaults-implement-public-contract.md):
they are the contract's **source**, not its consumers, and
`core/tests/test_contract_surface.py` pins the surface so the wire schema and
`Capabilities` cannot drift apart in silence.

**The order, and the reason for it:**

1. ~~**The Plexamp hardware check**~~ — **done 2026-09-25**
   ([Finding 077](docs/findings/077-plexamp-on-gexis.md)). Plexamp headless
   4.13.2 is installed and claimed on the device. **It can be a renderer**: a
   commanded stop works, it frees the ALSA device and keeps running, so
   ADR-0008's reversal is not triggered. Two things to carry into Phase 11 —
   the device is held for a deterministic **14 s** after the stop, so its
   `release_ladder` needs a longer polite grace than the default; and **the
   audio path does not work for the meters**, because it opens `hw:5,0`
   directly rather than `pcm.output`, in **S32_LE**, which is the format moOde
   measured as giving an all-zero peppyalsa FIFO.
2. ~~ADRs: the transport~~ — **done**, George took the recommendation:
   [ADR-0084](docs/decisions/0084-plugins-speak-json-lines-over-a-unix-socket.md),
   a Unix socket carrying JSON lines. The plugin channel can claim the audio
   device and lie about what is playing, which is not the class of thing
   ADR-0028 left open on the LAN.
3. ~~Draw the contract from `Adapter` and `Capabilities` as they are.~~ —
   **drafted**: [`docs/PLUGIN-CONTRACT.md`](docs/PLUGIN-CONTRACT.md), version
   1, **and deliberately not frozen**. It freezes after a non-renderer has
   been built against it, not before. `test_contract_surface.py` now checks
   the document against the objects as well as the objects against
   themselves, which is the drift guard ADR-0013's amendment promised.

   **The `kind` split is the part to attack**: `renderer` declares a unit, a
   release action and capabilities; `service` declares a unit and nothing
   else. If a Beszel agent cannot be said as a `hello` with
   `kind: "service"`, the contract is wrong.
4. **Discovery — the mass of the phase.** `"lms"` appears in **six core
   modules outside `adapters/`** and **ten UI files**, so "no core changes"
   means a manifest, a scanned directory, and settings rows and source artwork
   arriving from the plugin. The unsurfaced `plugins` row is where it lands.
5. ~~The **Beszel agent** against the draft, *before* freezing it.~~ —
   **built 2026-09-25**, and it did its job twice over: it found that a plugin
   could declare rows but nothing could switch it off (ADR-0086's amendment),
   and then that a plugin's settings could not reach a third-party binary at all
   (ADR-0088). Both were holes in the contract, found by the plugin written to
   look for them, which is what this criterion is for.

   **All four of the questions the record said were owed are answered.** The
   hub is George's. The agent listens on nothing. It costs 14 MB and under 1 %
   of a core. It ships in the image, defaulting off — George's call.

   ~~**What is left is the enrolment.**~~ **Done 2026-09-25** — George entered
   the token and the hub key through the settings screen: *"Added the keys into
   the plugin and can confirm it works."* The cost is measured
   ([Finding 080](docs/findings/080-the-agent-enrolled.md)) and **throttle state
   turned out not to be there at all**, which ADR-0087 now says instead of
   claiming otherwise.
6. **Freeze v1** — the last step, and it must stay last. This criterion's plugin
   has now amended the contract **twice**; freezing before it was built would
   have frozen a contract that its first real consumer broke.

**Settings rows are done** (2026-09-25), and a plugin's now reach a process
that cannot speak to us: see ADR-0088 above. A manifest's `settings` are merged
into the registry — a renderer's under a sub-heading in Sources, the shape the
three built-ins already have — with keys prefixed by the plugin's id so two
plugins shipping `enabled` cannot collide. Rows go through the registry's own
validation and a bad one is dropped with the reason logged rather than taking
the device down. A write reaches the plugin as `setting` under **its own** key;
the value is stored either way, and a plugin that was down is handed every
current value in its `welcome`. Proved on the device with a service plugin
written in `socket` and `json`.

**Still open inside discovery: arbitration does not carry plugins.** A
`renderer` that connects is welcomed and **idle**, and the log says so rather
than pretending otherwise. That is the last piece — an `Adapter` built around
a session and registered with the supervisor — and it is what Phase 11 needs
before Plexamp can be an external plugin.

**Read [Finding 075](docs/findings/075-what-moode-learned-about-plexamp.md)
before starting.** George's moOde project built a Plexamp route and **parked
it**: pause and app-dismissed are byte-identical at every observable endpoint.

**That phrase is narrower than it sounds, and the second export settles it.**
It was about the *HTTP endpoints*. Plexamp on `:32500` turns out to fit
ADR-0010's ladder without bending:

| our contract | Plexamp, per moOde |
|---|---|
| `release()` — the polite stop | the API stop at `:32500`. Frees the DAC, leaves Plexamp running |
| `signal_stop(force)` | kill the unit — which needs a restart, so it is rightly the second step |
| `on_release` | **TCP count to `:32500` reaching 0**, seconds after the app goes away |

So **Plexamp looks viable**, on someone else's machine, with two gaps neither
project has measured: the stop test's "before" read was empty, and nobody knows
what the TCP count does after an API stop — if our own `release()` drops it,
the adapter reads its own polite stop as a user disconnect.

The finding also carries two smaller things — our `output.conf` pins no sample
format, and peppyalsa gave moOde an all-zero meter FIFO for S32_LE.
