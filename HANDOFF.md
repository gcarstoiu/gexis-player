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

**A full rebuild including the new `03-core` stage is in flight** on
`C3PO` to confirm the whole thing actually packages and boots — not yet
reflashed or hardware-verified end-to-end. `phase-2b-arbitration` is not
yet pushed to `origin`.

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

## Next actions, in order

1. **Phase 2 criteria 3-7**: arbitration (base/active slot, ADR-0010),
   timeout ladder on release, volume bridge, boot volume. This is where
   the Python core first appears — in the image, via `stage-gexis`, not
   Phase 3. Criteria 1, 2, 4, 5, 6 are now met; this picks up where they
   left off.
2. **Write up the peppyalsa meter FIFO finding** (see above) with its
   stated scope.
3. Criteria 8-10 (takeover gap measurement) once 3-7 hold on real
   hardware — needs LMS (George has one; CI gets a containerised
   throwaway) and, for the Spotify leg, the registered Spotify API app
   (transfer-playback confirmed available to new apps — see
   `docs/ARCHITECTURE.md`'s open-questions list).
4. **Fill the Finding 003 grid** on `rig`, not `gexis` — characterises the
   metering path, not the product image. 16 of 18 cells remain.

Decisions pending from George: the criterion 7 build-self-identification
amendment (above), and whether to act on the develop-on-hardware
workflow inversion (above, needs an ADR first if so).

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
- **Don't assume `C3PO`'s tooling is on the image.** `xxd` isn't there
  (ships with vim; Lite base doesn't have it) — use `od`. More broadly,
  never paste command blocks across machines without checking which host
  a shell is actually attached to first (see the method note above).
- **`$EDITOR` is unset on `C3PO`.** `git merge` without `--no-edit` stops
  waiting for `vi`, which isn't installed. Use `git commit --no-edit` (or
  set an explicit editor) rather than let it hang.

## Working agreement

George is product manager: requirements, acceptance criteria, trade-offs, UX.
Claude handles implementation, tooling, tests, commits. Does not commit to
`main` — opens PRs.

Every architectural decision becomes a numbered ADR before implementation.
Findings state their scope: what was tested, under what conditions, what was
not. `docs/LESSONS.md` (PR #5) tracks recurring verification-methodology
failures, kept distinct from findings and ADRs.
