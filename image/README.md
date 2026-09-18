# Image build

`make image` (from the repo root) builds a Raspberry Pi OS Lite 64-bit image
with the Gexis Player audio layer, via pi-gen's own Docker wrapper. Unmodified
pi-gen — everything project-specific lives in `image/stage-gexis/` and
`image/config`, bind-mounted in at build time.

**Retrying after a failed build:** `build-docker.sh` doesn't clean up its
container on failure. A retry without removing it first fails immediately
with `Container pigen_work already exists` — not a build problem, just
stale state:

```
docker rm -v pigen_work
```

## Host prerequisites (one-time, not part of `make image`)

These are host environment setup, same category as installing Docker itself.

1. **Docker.** `pacman -S docker`, then `sudo systemctl enable --now docker`
   and add your user to the `docker` group (`sudo usermod -aG docker $USER`,
   then re-login).

2. **binfmt_misc for aarch64.** `pacman -S qemu-user-static-binfmt`,
   `sudo systemctl enable --now systemd-binfmt`. This registers
   `qemu-aarch64-static` as the aarch64 interpreter so the container (itself
   x86_64) can run the aarch64 chroot pi-gen builds.

3. **A `qemu-aarch64` binary on `PATH`.** `build-docker.sh` checks for a
   binary literally named `qemu-aarch64` before it will run — a Debian
   package-naming assumption (Debian's `qemu-user-binfmt` installs that exact
   name). Arch's `qemu-user-static` package only installs
   `qemu-aarch64-static`. binfmt registration itself is unaffected (already
   correct after step 2) — this is purely `build-docker.sh`'s own precondition
   check being Debian-specific. Fix, no sudo required:

   ```
   mkdir -p ~/.local/bin
   ln -sf /usr/bin/qemu-aarch64-static ~/.local/bin/qemu-aarch64
   ```

   Make sure `~/.local/bin` is on `PATH`. This is *not* a pi-gen patch —
   `build-docker.sh` itself is untouched; this just satisfies its existing
   check with the binary Arch actually ships.

4. **The `loop` kernel module must be loaded: `sudo modprobe loop`.**
   Per-boot, not one-time — it doesn't persist across a reboot unless
   configured to autoload. Unlike the other prerequisites, a missing or
   broken loop driver doesn't fail loudly up front; it fails deep into
   `export-image` instead (see below). Checking this before a build is
   cheap; diagnosing it after the fact is not.

## Disk: why `make clean` is not the way to reclaim space

`PRESERVE_CONTAINER=1` keeps `pigen_work`'s two anonymous volumes between
builds. That is what makes a warm build ~12 minutes instead of ~40, and it is
also where space accumulates. Measured after two builds, 2026-09-13:

| | | |
|---|---|---|
| `work/*/stage{0,1,2,-gexis}/rootfs` | 8.4 GB | **the warm cache — never delete** |
| `work/*/export-image/*.img` | 8.3 GB | one raw image *per build*, leaked |
| `deploy/` | 2.2 GB | every build's output, re-copied to the host each run |

The `export-image` leak is ours, not pi-gen's. `export-image/prerun.sh`
deletes and recreates the image every run, but only the one named
`${IMG_FILENAME}${IMG_SUFFIX}.img` — and `IMG_SUFFIX` is the git-describe
version the root `Makefile` passes in, different on every build. So each
previous build's ~4.5GB image is orphaned forever. Stock pi-gen, which reuses
a date-based name, doesn't have this problem.

**`make prune`** removes both, and nothing else: it never touches the stage
rootfs trees, never removes the container, and leaves `image/deploy/` on the
host alone (that is the artefact you keep). `make image` runs it first. A
first run reclaimed 10,194 MB and the following build was 12m29s — still warm.

`make clean` is the opposite: `docker rm -v pigen_work` destroys the volumes
*including* the warm cache, forcing a ~40-minute cold build. It exists to
force a clean-room build, not to free disk. Reaching for it to clear a disk
warning is what silently cost the warm builds before `make prune` existed.

Note the two-partition trap this used to hide behind: Docker's data root
defaults to `/var/lib/docker`, on `/`, while `image/deploy/` is in the repo,
on `/home`. Deleting zips from `image/deploy/` frees the partition that
*wasn't* full. Docker's `data-root` was moved to `/home/docker` on 2026-09-13
so both now live on the same, larger partition.

## A build that dies during the copy-out

`build-docker.sh:154` ends every build with:

```
${DOCKER} cp "${CONTAINER_NAME}":/pi-gen/deploy - | tar -xf -
```

That streams the container's **entire** deploy directory to the host through a
pipe, on every build. Two consequences worth knowing:

- Under host memory pressure this is the step that gets killed — observed
  twice, 2026-09-13, both times with the build itself already complete
  (`Build finished` in the log, image intact in the volume). There is no
  kernel OOM record for it; the kills came from the supervising process, so
  searching `journalctl` for `oom-kill` finds nothing and proves nothing.
- An interrupted `tar -xf` rewrites `deploy/` alphabetically and can leave a
  *previous* build's artefact truncated. `make prune` reduces the blast radius
  by keeping only the current build in the volume, but does not remove it.

If it dies there, **the build is not lost** — it has already finished and the
artefacts are in the volume. Recover them with:

```
make fetch-deploy
```

It copies one file at a time, avoiding the tar pipe entirely (measured: 44s
for a 4.5GB image), then appends the manifest annotation the `image` target
would have — that step runs *after* the copy, so a killed copy-out skips it
too. Re-running is cheap and safe: anything already present at the right size
is skipped, and the annotation stays a single block.

This has to be its own target rather than a fallback inside `image`, because
the kill signals make itself (`make: *** [image] Terminated`) — by the time
the copy has failed there is no recipe left running to recover from it.

Verified 2026-09-13: recovered image byte-identical to the one copied out by
hand, manifest reporting the true 749s build.

Never `docker start pigen_work` to inspect the volumes: that re-runs pi-gen's
entrypoint and starts a build. Read them through a throwaway container
instead, which is what `make prune` does:

```
docker run --rm --volumes-from pigen_work pi-gen:latest sh -c 'ls -la /pi-gen/deploy'
```

## What `make image` produces

`image/deploy/` will contain **one** image, `<date>-gexis-player-<version>.img`
— **the deliverable.** Built from `stage-gexis` on top of stage2: pins and
holds `libasound2t64`, builds peppyalsa from source, installs
`/etc/alsa/conf.d/output.conf`, wires up first-boot provisioning, and installs
squeezelite, go-librespot, bluealsa-aplay, gexis-core and the kiosk UI.

The second `-lite` image is gone: the root `Makefile` removes
`stage2/EXPORT_IMAGE` before each build, because that checkpoint export costs
a full loop-device/zerofree/compress cycle (measured 6m41s) for an artefact
nobody consumes.

A raw `.img`, not a zip — `DEPLOY_COMPRESSION=none`, set in `image/config`
2026-09-13; that file carries the reasoning. What settled the previously-open
call, in order of weight:

- **Who does what.** Claude builds, George flashes (George, 2026-09-13). A raw
  `.img` drops straight into Raspberry Pi Imager with no extraction step. The
  build host's convenience does not get to add a step to the one part of this
  loop a human actually performs.
- **Inspection.** `mtools` reads the boot partition straight out of the `.img`
  (see below); with a zip that needed a 4.5GB `unzip` first.
- **`bmaptool`**, which pi-gen already emits a `.bmap` for, can skip
  unallocated blocks only when handed the image itself.
- **Build time.** Barely moves. A measured pair of warm builds on the same
  tree: `05-finalise` 8m07s with zip, 7m23s without — the step is dominated by
  zerofree and unmount, not compression.
- **Cost, and it is real.** 4.5GB raw against 1.28GB zipped, measured on the
  2026-09-13 builds. That lands on `image/deploy/` *and* on the container's
  deploy volume, and `build-docker.sh` streams the whole volume to the host on
  every build (see "A build that dies during the copy-out", below).

Both halves of that cost are handled rather than paid: `make prune` bounds the
disk side, `make fetch-deploy` recovers the streaming side when it is killed.
Re-compressing to make Claude's copy-out cheaper would be optimising the wrong
end of the loop, so don't.

Each image gets a matching `.info` file (from pi-gen's own
`export-image/05-finalise` step) containing the exact `dpkg -l` package list
at build time — the manifest required by Phase 0 acceptance criterion 2/7.
peppyalsa and go-librespot aren't apt packages, so pi-gen's manifest doesn't
cover them: the root `Makefile` appends peppyalsa's pinned commit (read out
of `stage-gexis/00-alsa/01-run-chroot.sh`) and go-librespot's pinned release
tag (read out of `stage-gexis/02-renderers/01-run.sh`) — one source of truth
each, not duplicated into the Makefile — plus the total wall-clock build
time, after the build completes. Post-processing on the host, not a pi-gen
change.

Rebuilding is not guaranteed to reproduce the same package set — see
`docs/DEVELOPMENT.md` criterion 7 and ADR-0021.

## Known issue: loop device setup in export-image

**Corrected 2026-09-18 — read this before the section below, which is kept
for its symptoms and its history.** The root cause named there, *"the `loop`
kernel module was not loaded"*, is **wrong**. R2D2 now autoloads the module
at boot, and the first build after a reboot failed identically with the
module loaded (`loop 45056 0`, use count 0). What decides it is whether a
**`/dev/loopN` node exists**: with only `/dev/loop-control` present,
`losetup -f` answers `/dev/loop0 (lost)` - the kernel knows loop0 is free,
but nothing can reach it. The failed build leaves a `/dev/loop0` behind,
which is why the *rerun* always passes, and why reloading the module worked:
it makes udev create the nodes.
[Finding 033](../docs/findings/033-loop-device-before-a-build.md) has the
recorded before-and-after state. **No durable fix is chosen yet** (it needs
George and `sudo`); until one is, expect the first build after a reboot to
fail in 210 s and the second to pass.


First build attempt (2026-09-05, this host) reached `export-image/prerun.sh`
and failed there — everything before it, including all of stage-gexis,
succeeded. A second attempt, after the fix below, completed end to end in
36m43s. `pi-gen/scripts/common`'s `ensure_next_loopdev()` calls `losetup -f`
to get the next free loop device, then extracts its minor number with a sed
pattern anchored on trailing digits. `losetup -f` returned `/dev/loop0 (lost)`
instead of a plain path, the sed pattern didn't match (no trailing digits),
and the unmodified string got passed to `mknod`:

```
mknod: invalid minor device number '/dev/loop0 (lost)'
```

pi-gen retries this 5 times (`build.sh`'s own retry loop) and hard-fails when
they all reproduce identically.

**Root cause, confirmed with `sudo losetup -f` directly on the host:** the
`loop` kernel module was not loaded before the container's first access to
`/dev/loop-control`. `losetup -f` can see via `/dev/loop-control` that loop0
is free, but the `mknod` pi-gen's own container ran against it produced a
device node that udev never properly backed — losetup can see the kernel
state but can't resolve a working path to it, hence "(lost)". This is stable,
reproducible state, not a race: `sudo losetup -f` as root, well after the
module had ostensibly been loaded, still returned the same "(lost)" result
until the driver was reloaded.

**Fix:** `sudo modprobe -r loop && sudo modprobe loop`. This makes the driver
and udev recreate the device nodes from scratch. **Do not `rm` the device
node** — that discards the evidence and doesn't fix the underlying state;
reload the module instead. This is a Docker/CachyOS loop-device
interaction, not a pi-gen defect — nothing in `export-image/` was touched.

**Not a symptom, ignore it:** `losetup -f` as an unprivileged user always
fails on Arch with `Permission denied` (`/dev/loop-control` is root-only).
Any diagnosis of loop-device issues here must use `sudo`, or the result is
meaningless.

## First boot: the boot-partition edit

Nothing on this image is pre-provisioned — no default password, no cloud-init,
no baked-in Wi-Fi. The **only** first-boot mechanism is `firstrun.sh`, wired
in via `cmdline.txt`'s `systemd.run=` (ADR-0021). It runs once, very early in
boot, then deletes itself and its `cmdline.txt` entry.

After flashing (`<date>-gexis-player-<version>.img` — Imager, Etcher and
`bmaptool` all take the raw image directly), the boot partition's
`firstrun.sh` needs five values filled in, and takes two optional ones:

```sh
SSH_PUBKEY="ssh-ed25519 AAAA... you@host"   # required — no other remote access exists
WIFI_SSID="your-network"                     # leave blank for Ethernet-only
WIFI_PASS="your-password"
WIFI_COUNTRY="GB"                            # ISO 3166-1 alpha-2
HOSTNAME=""                                  # optional
TIMEZONE="Europe/Berlin"                     # optional
IDLE_URL=""                                  # optional; the idle screen page
SETTINGS=""                                  # optional; settings to start from, as JSON
```

`SETTINGS` is JSON keyed by the settings screen's own keys, e.g.
`{"idle_timeout": 10, "drawer_autohide": 5}`. First boot writes it to
`/etc/gexis/settings-seed.json`, and the daemon treats those values as
defaults — so a reflash restores them, and anything changed later from the
phone still wins. `make provision` refuses invalid JSON; the daemon logs and
ignores an unknown key or an out-of-range value.

**`make provision DEVICE=/dev/sdX`** does this — the SSH key is a long
single line, and a hand-edit that truncates it costs a reflash to discover.
One-time setup, then every reflash after:

```
cp image/provision.env.example image/provision.local.env   # once
$EDITOR image/provision.local.env                            # fill in real values
make provision DEVICE=/dev/sdX                                # every card
```

`image/provision.local.env` is gitignored — real credentials never reach the
repo. `DEVICE` is the whole card (e.g. `/dev/sdb`), never guessed: writing to
the wrong block device is destructive, so the tool refuses to run without it
and refuses if the device looks like the machine's own disk. It also refuses
to write anything if `SSH_PUBKEY` is empty — a card provisioned with a blank
key boots unreachable, which is the exact failure Phase 0 hit — and verifies
every substitution actually landed (by having a shell parse the written line
back out and comparing, not just checking that the edit command didn't
error) before declaring the card ready.

It finishes by running `ssh-keygen -R <hostname>` and
`ssh-keygen -R <hostname>.local` for you. **This is not a workaround for
anything broken** — every reflash generates a fresh SSH host key at first
boot, so reconnecting to the same hostname after a reflash normally fails
with `REMOTE HOST IDENTIFICATION HAS CHANGED` until the stale entry is
cleared by hand. `ssh-keygen -R` matches the exact string given, which is
why both the bare hostname and the `.local` form are cleared separately.

Save, eject, boot. `firstrun.sh` calls the same platform helpers Raspberry Pi
Imager's own customisation dialogue calls
(`/usr/lib/raspberrypi-sys-mods/imager_custom`, `/usr/lib/userconf-pi/userconf`)
— confirmed against their current source, not assumed. Wi-Fi goes through
NetworkManager (`imager_custom set_wlan` → `nmcli`); a `wpa_supplicant.conf`
dropped on the boot partition does **nothing** on current Raspberry Pi OS —
confirmed dead since the Bookworm NetworkManager switch
([raspberrypi/bookworm-feedback#72](https://github.com/raspberrypi/bookworm-feedback/issues/72)).

The default user stays `pi`, password-locked (SSH key only — `enable_ssh -k`
disables password auth). To change the username, edit `firstrun.sh`'s
`userconf` call directly rather than adding a variable for it; that's a rarer
edit and not worth a placeholder.

`stage-gexis/01-firstboot`'s build step **fails the build** if `firstrun.sh`
is missing, `cmdline.txt` doesn't invoke it, or a stale cloud-init template
made it onto the boot partition — this class of defect (Phase 0's first
build shipped with *no* working first-boot path at all, caught only by
hand-inspecting a flashed card) should never again reach `deploy/`.

Verifying the boot partition doesn't require hardware — `mtools` reads it
straight out of the deployed `.img`, with no extraction step since
`DEPLOY_COMPRESSION=none` (2026-09-13):

```
IMG=image/deploy/<date>-gexis-player-<version>.img
OFFSET=$(( $(fdisk -l "$IMG" | awk '/FAT32/{for(i=1;i<=NF;i++) if($i ~ /^[0-9]+$/){print $i; exit}}') * 512 ))
mdir -i "${IMG}@@${OFFSET}" -/
mcopy -i "${IMG}@@${OFFSET}" ::cmdline.txt -
```

The `awk` takes the first all-numeric field on the FAT32 row (the start
sector) rather than a fixed column number: `fdisk` only emits the `Boot`
column when some partition carries the flag, which shifts every column after
it.

## Renderers (Phase 2a)

`stage-gexis/02-renderers` installs squeezelite, go-librespot and
bluealsa-aplay, each as a systemd unit writing to `output`.

- **squeezelite** — `apt install squeezelite` (Debian trixie, arm64,
  confirmed via packages.debian.org — not assumed). Not held: no Finding
  ties us to an exact version the way `libasound2t64` is. `-V DAC`'s mixer
  resolution needed `output.conf`'s new `ctl.output` block (see below) —
  without it, squeezelite doesn't fail, it silently reverts to software
  volume (confirmed by reading `output_alsa.c`, ADR-0018's exact warning).
  `squeezelite.service`'s `ExecStartPre` runs `amixer -D output sget DAC`
  first, so a broken mixer control fails the unit instead of playing
  silently-wrong audio. `-C 10` (closes the ALSA device after 10s idle,
  which is what actually frees it for takeover, per ADR-0010's
  implementation note) is a **provisional value** — real tuning is
  criteria 8-10's job once there's a real takeover-gap distribution to
  tune against.
- **go-librespot** — no Debian package (confirmed empty search). Pinned
  the same way peppyalsa is: an exact release tag and a checksum verified
  independently, not just trusted from the API
  (`stage-gexis/02-renderers/01-run.sh`). Downloaded and verified on the
  host, not in the qemu-emulated chroot — no reason to pay emulation cost
  for a plain HTTPS GET and a `sha256sum`. `zeroconf_backend: avahi`
  (shares the image's already-running `avahi-daemon` rather than standing
  up a second mDNS responder). Config lives under systemd's
  `StateDirectory=` (`/var/lib/go-librespot`, passed via `-config_dir`),
  not `~/.config` — see "First hardware pass" below for why that matters.
- **bluealsa / bluealsa-aplay** — `bluez-alsa-utils` (Debian trixie, arm64)
  already ships and auto-enables both units
  (`WantedBy=bluetooth.target`). We override two things via systemd
  drop-ins, per upstream's own documented customisation path, not
  replacement units: `bluealsa-aplay`'s `ExecStart` to point `--pcm` at
  `output` instead of its shipped default of `default`, and `bluealsa`'s
  `ExecStart` to drop the `a2dp-source` profile its shipped default
  advertises unasked (confirmed running as `-p a2dp-source -p a2dp-sink`
  on hardware — not something we'd set deliberately; only `a2dp-sink` is
  a requirement, and fewer advertised profiles is less for a phone to
  negotiate wrongly).

**`output.conf` gained a `ctl.output` block.** ADR-0009's indirection had
only ever been exercised for playback (`pcm.output`) before Phase 2's
renderers arrived — nothing had needed the mixer-control half of it yet.
squeezelite's `-V <name>` resolves against a ctl device matching the PCM
name it was given, not through the PCM's slave chain, so `-o output -V DAC`
needed `ctl.output` to exist. Completing ADR-0009's own stated indirection,
not a new decision.

### First hardware pass (2026-09-05, `gexis`)

squeezelite, bluealsa and bluealsa-aplay came up healthy first try — the
`ExecStartPre` mixer guard ran and passed, confirming `ctl.output`
resolves on real hardware, not just in theory.

go-librespot crash-looped — 114 restarts in 25 minutes, no backoff limit,
burying `failed creating config directory: mkdir
/home/pi/.config/go-librespot: permission denied` in noise. Root cause:
`install -D` (see `01-run.sh`) creates intermediate directories owned by
whoever runs it — root, in the build container — regardless of `-o`/`-g`
on the target file, so `/home/pi/.config` ended up root-owned. `/home/pi`
was also the wrong place on principle: a system service's state shouldn't
live under a user account's home directory at all. Fixed by moving to
`StateDirectory=go-librespot` (systemd creates and re-chowns
`/var/lib/go-librespot` to `User=`/`Group=` on every start — self-healing
against exactly this class of ownership mistake) and adding
`StartLimitIntervalSec=`/`StartLimitBurst=` to both renderer units so a
misconfigured service gives up and stays failed instead of spinning
forever.

### Second hardware pass (2026-09-05, `gexis`)

Two more found on this pass, both build-time fixes since neither is
fixable once a card is already running:

**`pi` had no way to become root at all** — `sudo -n true` failed with
"a password is required", and there's no other path: the account is
locked and password-less by design (SSH-key-only, see `userconf pi ""`
above). Verified, not assumed, that stock Raspberry Pi OS Lite normally
grants this via `/etc/sudoers.d/010_pi-nopasswd`, created by the
interactive first-boot wizard this image never triggers — checked both
this image's rootfs and the bare, unmodified `-lite` artefact directly
(`dd` + `debugfs`); neither ships the file. Not something this stage
removed; never there in the first place. `stage-gexis/01-firstboot/01-run.sh`
now ships it directly, and asserts what actually matters for sudo to
honour it — mode `440` exactly, and `visudo -cf` syntax-valid — because
sudo silently ignores a sudoers.d file with the wrong permissions or a
syntax error rather than erroring, which is exactly the failure mode this
gap already took the shape of once.

**go-librespot's `--config_dir` was `-config_dir`** — a single dash. Its
own CLI parses `-c` as a distinct short flag for config overrides
(`field=value`, documented in its own README), POSIX-style, not Go's
stdlib `flag` package (which treats `-x` and `--x` identically). A single
dash reads as `-c` consuming `onfig_dir` as its argument — exactly the
observed `invalid config override format: onfig_dir` crash. The
`config.yml` content itself was already correct.

Not yet reverified on hardware.

## Testing a build

`pi@gexis.local` is the test target — `gexis` is the image-built machine,
not the hand-built `rig` (see `HANDOFF.md`).

```
aplay -D output <testfile>   # card referenced by name, no `type plug`, no index
```

Not yet done as of the 2026-09-05 build: flashing and hardware verification
(Phase 0 criteria 3–5). The build itself is confirmed good (criteria 1, 2, 6,
amended 7), and the boot partition is confirmed correct by direct inspection
(criterion 3's mechanism) — but nothing has actually booted on real hardware
yet.
