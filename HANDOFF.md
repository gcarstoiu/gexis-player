# Handoff

Last updated: 2026-09-12 (eleventh session — **PHASE 3 STARTED**)

## Where things stand

**Phase 3 (core state daemon) started, criterion 1's first slice built on
`phase-3-core-daemon`, not yet hardware-verified or pushed for George's own
pass.** Before writing any code, George was asked what "availability"
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

**Not done yet, deliberately** - this is one slice, not the whole
criterion's hardware verification, per the standing "land one change at a
time" rule: no reflash, no real WebSocket client against the live daemon,
no confirmation of the two flagged-unverified mappings above. Next: George
reviews/tests this slice (a WebSocket client against a running
`gexis-core`, once pushed and, ideally, exercised on `gexis`) before
criterion 2 (capability declarations) starts.

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

**Reflashed and hardware-tested — see the session below for what was
found.** None of it is clean yet; do not treat criteria 3-6 as met.

---

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

## Machines

| Name | What it is | Notes |
|---|---|---|
| `C3PO` | dev machine | CachyOS, **fish shell** — no heredocs. Hand it script files to run with `bash`, not pasted multi-line commands. |
| `rig` | Raspberry Pi 4, 4 GB | Raspberry Pi OS Lite 64-bit, Trixie. **Reference machine** — holds the environment Findings 002-004 were measured against. Not the build/test target. |
| `gexis` | Raspberry Pi 4 | Flashed from this project's own `make image` output. User `pi`. Reachable as `pi@gexis.local` by SSH key. **The image-built target** — Phase 2 onward is built and measured here. |
| SD card 2 | moOde | Reference install. Read-only recon source. Do not modify. |
| LMS server | `192.168.178.188` | For manual testing (arbitration base slot, etc). **CI gets a containerised throwaway instead — CI must not depend on this server being up.** |

**Provisioning a freshly flashed card:** `make provision DEVICE=/dev/sdX`
fills in `firstrun.sh`'s SSH key / Wi-Fi / hostname from
`image/provision.local.env` (gitignored, copy `image/provision.env.example`
to create it) and clears the card's stale SSH host key. See
`image/README.md`.

**Builds are versioned, starting 2026-09-07** (George: "can we start
giving release numbers to the builds"). `git describe --tags --always
--dirty` at build time, appended to the `.info` manifest as "Image
version: vX.Y.Z" — same place peppyalsa's commit and go-librespot's
version already live, not a new mechanism. First tag: `v0.1.0`
(annotated, on `phase-2b-arbitration`). No bump convention decided yet
(when to cut `v0.2.0` vs. just moving the tag) — tag manually before a
build worth naming, for now.

**Filenames carry the version too, starting 2026-09-11** (George asked).
The `.info`-only note above is now out of date on this point - the
plumbing concern it named (threading the version through pi-gen's own
two-pass `image/config` sourcing, which would need git access *inside*
the container that isn't there) turned out to have a simpler answer:
pi-gen already exposes `IMG_SUFFIX`, appended to every export-image
filename with no default of its own unless a stage sets one (none of
ours do), so the `Makefile`'s `image:` target now passes
`-e IMG_SUFFIX=-$(IMAGE_VERSION)` via `PIGEN_DOCKER_OPTS` - no
`image/config` change, no submodule edit. Confirmed the env var reaches
the container intact via a standalone `docker run -e` test (a plain host
environment variable does not cross that boundary on its own - `docker
run` only forwards what's explicitly passed) and confirmed the resulting
filename shape by simulating `build.sh`'s own variable-resolution lines
directly. The `image:` target's own manifest-lookup glob was widened
(`*-gexis-player.info` → `*-gexis-player*.info`) to still find the
now-longer filename - the exact class of thing that broke silently once
already (the multi-manifest annotation bug, Phase 2c's prerequisites) -
check this first if a future build's manifest looks unannotated again.

**First real `make image` run found it didn't work at all - the
filenames came out exactly as before, no version suffix.** Root cause:
`image/stage-gexis/EXPORT_IMAGE` (this project's own file, not the pinned
submodule - the mechanism that triggers pi-gen's export-image stage at
all, adapted from upstream's stage4/5 convention) unconditionally set
`IMG_SUFFIX=""` at its own top, sourced by `build.sh` right before the
export stage runs - silently clobbering whatever the Makefile had passed
in via the container's environment, every single build, before this was
noticed. The annotated `.info` manifest's own version line still worked
(a separate, host-side mechanism, unaffected) - only the filenames
themselves were wrong. Missed originally because the isolated
verification checked the env-var-passing mechanism and simulated
`build.sh`'s own variable-resolution lines directly, but never checked
whether anything sourced *after* those lines could still overwrite the
result - `EXPORT_IMAGE` files are exactly that, and this project's own
copy of the pattern wasn't audited. Fixed (`IMG_SUFFIX="${IMG_SUFFIX:-}"`,
preserves rather than clobbers), confirmed by the same isolated-simulation
method as before (sourcing the actual fixed file with `IMG_SUFFIX`
pre-set, exactly as the container would have it). **A second `make
image` run is what actually proves this** - the one that produced today's
reverted, currently-flashed image predates this fix.

## Next actions, in order

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

## Phase order

```
0  reproducible image                     ✓ merged — pi-gen, ADR-0021
1  measurements                           absorbed into 2 — needs 2's own renderers
2  audio layer + arbitration              ← in progress: renderers packaged and
                                             hardware-verified (criteria 1,2,4,5,6);
                                             Python core arrives here for 3-7; takeover gap
3  core state daemon                      no UI; test with a WebSocket client
4  UI shell + idle + display-only nowplay
5  visualisation service + Peppy screen   capability-blind, proves the model
6  now playing, full                      capability-driven controls
7  library browse                         full SlimBrowse
8  enrichment + lyrics                    additive only, cannot break playback
9  plugin contract hardening + themes     Qobuz is the fourth-renderer test
```

## Things that will bite if forgotten

- **Never reference an ALSA card by index.** 3 on `rig`, 2 on moOde, 1 on
  `gexis` — same DAC model, three different indices (Finding 005). Use
  `hw:sndrpihifiberry`.
- **`ctl.output`, not just `pcm.output`, in `output.conf`.** Mixer access
  (`squeezelite -V DAC`) resolves through the control interface, not the
  PCM slave chain — ADR-0009 was itself incomplete on this until Phase 2a.
- **`squeezelite -V <control>` does not fail on a bad mixer name** —
  confirmed from its source. It logs and silently falls back to software
  volume. `squeezelite.service`'s `ExecStartPre` is the actual assertion.
  As of 2026-09-08 (B2) the target is `hw:gexislmsvol`'s `Master`, a
  private `snd-dummy` control, not the real `DAC` — same risk, different
  target; the check was updated to match, don't let it drift back.
- **`alsactl monitor <card>` needs the `hw:` prefix** — `alsactl monitor
  gexislmsvol` fails with `Invalid CTL`, `alsactl monitor
  hw:gexislmsvol` works. Not documented in `alsactl(1)`'s own SYNOPSIS.
  Found 2026-09-08 wiring up `DummyMixerBridge`.
- **`amixer sget`'s value line format differs by control** — a control
  with distinct playback/capture volumes prints `Front Left: Playback
  216 [...]`; one without (e.g. a `snd-dummy` card's `Master`) prints
  `Front Left: 30 [...]` — no "Playback" word. `volume.py`'s `get_raw()`
  parses both now; a regex written against only the real DAC's format
  will silently return `None` for a dummy control.
- **gexis-player is GPL v3 (ADR-0025, 2026-09-08).** Every file we
  author under `core/src/gexis_core/` carries `# SPDX-License-Identifier:
  GPL-3.0-or-later` as its first line — see `docs/DEVELOPMENT.md`'s
  "Licence" section. Don't add it to a vendored third-party file.
- **A `.gitignore` fix on one branch does not protect other branches**
  working off the same tree. Run `./test-gitignored-credentials.sh` on
  whatever branch you're on if you're not sure.
- **`type plug` must not appear in the `output` chain.**
- **`alsa-lib` is pinned at `1.2.14-1+rpt1`.** Findings 002/003.
- **`docs/DEVELOPMENT.md` on `main` is stale** — see above.
- **Adding a user to the `docker` group needs a new login session**, not
  just relaunching Claude Code — a shell spawned before the change keeps
  its old group list until it's re-created (new terminal / re-login).
  Check with `id` before assuming `docker` commands will work.
- **A failed `make image` leaves `pigen_work` behind even after
  `make clean`** if `clean` ran before the failing attempt rather than
  after it — `clean`'s `docker rm -v pigen_work` only removes what
  exists *at the time it runs*. Run `make clean` again after any failure,
  right before retrying.
- **Don't assume `C3PO`'s tooling is on the image.** `xxd`, `bc`,
  `telnet`, `nc` aren't there (Lite base doesn't have them) — `od`,
  `curl`, `ss`, `fuser` are. Reach LMS's CLI (port 9090) via bash's
  `/dev/tcp` instead of `telnet`/`nc`. More broadly, never paste command
  blocks across machines without checking which host a shell is actually
  attached to first (see the method note above).
- **`systemctl is-active` does not mean "working."** squeezelite reported
  active while go-librespot held the ALSA device out from under it,
  retrying every 5s with no way to see that from unit status alone —
  found on hardware, 2026-09-06. Check the actual symptom (audio, or in
  this case `fuser` on the PCM node), not just unit state.
- **A commanded pause does not make squeezelite release faster than its
  `-C` idle timeout** — measured ~8.5s from an LMS CLI pause to the ALSA
  device actually freeing, 2026-09-06. Arbitration cannot get a fast
  release out of squeezelite through LMS's own pause command; see the
  hardware session above for what this means for criterion 4.
- **go-librespot's `server.port` and `zeroconf_port` are ephemeral if
  left unset** — measured differing across a single `systemctl restart`.
  `server.port` is now pinned (`config.yml`); `zeroconf_port` is left
  random on purpose, since nothing on this device needs to address it by
  a fixed port and it must stay reachable from off-device (the phone
  app) regardless of which port it lands on.
- **`$EDITOR` is unset on `C3PO`.** `git merge` without `--no-edit` stops
  waiting for `vi`, which isn't installed. Use `git commit --no-edit` (or
  set an explicit editor) rather than let it hang.
- **Bluetooth is rfkill soft-blocked by default on this image** —
  nothing in the unattended boot clears it (that's normally
  `raspi-config`'s interactive country-code step). `rfkill list` and
  `/sys/class/rfkill/*/soft` show it directly; `hciconfig hci0 up`'s
  error message names it explicitly. Don't trust `bluetoothd`'s own
  "Failed to set mode: Failed (0x03)" to self-diagnose this — it's the
  same underlying block, several layers removed. `rfkill` itself is on
  the image already (`/usr/sbin/rfkill`, needs `sudo` and isn't on a
  non-root `PATH` by default) — it was never actually missing, just not
  found by an unqualified `which rfkill`.
- **A stock `alsa-restore.service` fights any "boot volume is fixed,
  never restored" requirement.** It's enabled by default on Raspberry
  Pi OS Lite and does exactly the opposite. Mask it, don't just order
  your own unit to run after it and hope you win the race.
- **A lossy bidirectional bridge over two different scales needs echo
  suppression on *both* directions, and a single write can produce more
  than one incoming event.** A boolean "skip the next one" flag missed
  both — see the volume bridge fix above for the measured consequence
  (a real ratchet to zero) and the fix (a shared time-window, not a
  one-shot flag).
- **`bluetoothctl discoverable on` does NOT mean persistently
  discoverable.** BlueZ's `DiscoverableTimeout` defaults to 180s and
  silently reverts the adapter afterwards; `Pairable` has no such default
  and does persist, so the two behave differently despite being set the
  same way two lines apart. Cost us blocker 3 and 1h36m of a live debug
  session. Read `bluetoothctl show` back after setting it, rather than
  trusting "Changing discoverable on succeeded".
- **Build filenames now carry the version (2026-09-11)** — the
  `Makefile`'s `image:` target manifest-lookup glob is
  `*-gexis-player*.info`, not `*-gexis-player.info` — if a future edit
  narrows it back, the annotation step will silently stop finding the
  manifest again, the same shape as the multi-manifest bug this project
  already hit once (Phase 2c's prerequisites, `ls -t | head -1`).

## Working agreement

George is product manager: requirements, acceptance criteria, trade-offs, UX.
Claude handles implementation, tooling, tests, commits. Does not commit to
`main` — opens PRs.

Every architectural decision becomes a numbered ADR before implementation.
Findings state their scope: what was tested, under what conditions, what was
not. `docs/LESSONS.md` (PR #5) tracks recurring verification-methodology
failures, kept distinct from findings and ADRs.
