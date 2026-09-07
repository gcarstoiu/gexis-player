# Handoff

Last updated: 2026-09-06

## Where things stand

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
(annotated, on `phase-2b-arbitration`). Filenames are unchanged — still
date-stamped (`image/config`'s `IMG_NAME`), not version-stamped;
threading the version through pi-gen's own two-pass config sourcing was
more plumbing than this needed given the manifest already carries it.
No bump convention decided yet (when to cut `v0.2.0` vs. just moving
the tag) — tag manually before a build worth naming, for now.

## Next actions, in order

1. **Rebuild and reflash `gexis`**, to pick up everything since the last
   flash: the `-C 1` revert (squeezelite release), the Bluetooth
   volume-memory bug fix, the `bluealsa-aplay` mixer-args fix, and the
   new auto-trust service. Nothing from this session is hardware-
   verified on a rebuilt image yet.
2. **On the reflashed image, in order:**
   - A real end-to-end Bluetooth pairing and playback test — trust,
     mixer, and volume all changed this session; none re-verified
     together yet.
   - Confirm LMS takeover releases in ~700ms with no artefacts, matches
     the `-C 1` measurement across more than one run.
   - Recheck George's original issue 3 (position reset on switch) —
     expected to resolve with LMS no longer killed, not yet confirmed.
   - Re-run the LMS-app-volume-buttons scenario against Spotify (the
     false-acquisition fix from two sessions ago still isn't
     independently reconfirmed — LMS's `/jsonrpc.js` POST endpoint was
     down when that was investigated).
3. **Bluetooth's release ladder — needs its own investigation, not a
   guess.** Two candidate causes recorded (ADR-0010's "Open" section):
   a too-fast unit restart racing the ladder's check, or
   `bluealsa-aplay` holding the PCM open past its own IO worker exiting
   on disconnect. Likely needs the same shape of fix LMS got — make the
   renderer's own release path actually work, rather than lean harder
   on killing the process.
4. **Re-test Finding 006** (Bluetooth volume partly software below
   ~96%) against the mixer-args fix — plausible but unconfirmed that
   fixing `--mixer-device`/`--mixer-name` also fixes or changes this.
5. **Phase 2b, criteria 3-6**, once 1-4 hold: the supervisor, adapters
   and volume bridge are written and unit-tested (`core/`), but no live
   takeover has actually been exercised end-to-end and left working —
   every hardware session so far has found and fixed a defect in the
   attempt.
6. **Write up the peppyalsa meter FIFO finding** (see above) with its
   stated scope.
7. Criteria 7-10 (the attack test and takeover gap measurement) once 5
   holds on real hardware — needs LMS (have one; CI gets a containerised
   throwaway) and, for the Spotify leg, the registered Spotify API app
   (transfer-playback confirmed available to new apps — see
   `docs/ARCHITECTURE.md`'s open-questions list).
8. **Fill the Finding 003 grid** on `rig`, not `gexis` — characterises the
   metering path, not the product image. 16 of 18 cells remain.

**ADR-0010's sync-group-interaction item is moot in the good sense
now** — `-C 1` means squeezelite is never killed in normal operation,
so there's no sync-group loss to accept anymore. See the ADR's own
final amendment.

Decisions pending from George: confirming (or picking a different)
`restore_volume_floor_db` — currently a −40dB placeholder, not
reviewed; which component applies Bluetooth's software volume
attenuation below ~96% (Finding 006, no owner yet, possibly connected
to this session's mixer-args fix); pinning down squeezelite's
LMS-volume-to-hardware mapping (no owner yet); the criterion 7
build-self-identification amendment; whether to act on the
develop-on-hardware workflow inversion (needs an ADR first if so).

The LMS-play-starts-Spotify observation was attempted-and-not-reproduced
in an earlier session (see hardware session above) and did not recur in
this one either — not blocking further work.

Not blocking, needed before their phases: skin asset conventions (needle
pivot, `distance`, icon set — blocks the skin renderer) and the peppyalsa
FIFO byte format (blocks the visualisation service).

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
- **`squeezelite -V DAC` does not fail on a bad mixer name** — confirmed
  from its source. It logs and silently falls back to software volume.
  `squeezelite.service`'s `ExecStartPre` is the actual assertion.
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

## Working agreement

George is product manager: requirements, acceptance criteria, trade-offs, UX.
Claude handles implementation, tooling, tests, commits. Does not commit to
`main` — opens PRs.

Every architectural decision becomes a numbered ADR before implementation.
Findings state their scope: what was tested, under what conditions, what was
not. `docs/LESSONS.md` (PR #5) tracks recurring verification-methodology
failures, kept distinct from findings and ADRs.
