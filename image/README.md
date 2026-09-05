# Image build

`make image` (from the repo root) builds a Raspberry Pi OS Lite 64-bit image
with the Gexis Player audio layer, via pi-gen's own Docker wrapper. Unmodified
pi-gen — everything project-specific lives in `image/stage-gexis/` and
`image/config`, bind-mounted in at build time.

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

## What `make image` produces

`image/deploy/` will contain artefacts for **two** images (confirmed by a
successful build, 2026-09-05, 36m43s wall-clock):

- `image_<date>-gexis-player-lite.zip` — bare Raspberry Pi OS Lite, no
  customisation. A side effect of `stage2/EXPORT_IMAGE` being unconditional,
  unmodified pi-gen. Harmless; ignore it.
- `image_<date>-gexis-player.zip` — **this is the actual deliverable.** Built
  from `stage-gexis` on top of stage2: pins and holds `libasound2t64` at
  `1.2.14-1+rpt1`, builds peppyalsa from source, and installs
  `/etc/alsa/conf.d/output.conf`.

Each is a zip containing one file, `<date>-gexis-player[-lite].img` — pi-gen's
default `DEPLOY_COMPRESSION=zip`, not overridden in `image/config`. Both
Raspberry Pi Imager and balenaEtcher flash directly from the zip without
extracting it, so this doesn't reintroduce a manual step for criterion 1.
Whether we want a literal `.img` in `deploy/` instead (set
`DEPLOY_COMPRESSION=none` in `image/config`) is an open call — the zip form
is roughly a third the size (a real 2026-09-05 build: 836 MB zipped vs.
2.9 GB raw).

Each image gets a matching `.info` file (from pi-gen's own
`export-image/05-finalise` step) containing the exact `dpkg -l` package list
at build time — the manifest required by Phase 0 acceptance criterion 2/7.
peppyalsa isn't an apt package, so pi-gen's manifest doesn't cover it: the
root `Makefile` appends its pinned upstream commit
(`7dcb0c5e783e0c86315a0f655684613affd3e9d2`, read out of
`stage-gexis/00-alsa/01-run-chroot.sh` so there's one source of truth) and
the total wall-clock build time to the `.info` file after the build
completes — post-processing on the host, not a pi-gen change.

Rebuilding is not guaranteed to reproduce the same package set — see
`docs/DEVELOPMENT.md` criterion 7 and ADR-0021.

## Known issue (resolved): loop device setup in export-image

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

After flashing (`image_<date>-gexis-player.zip`, direct — Imager and Etcher
both accept the zip), the boot partition's `firstrun.sh` needs five values
filled in:

```sh
SSH_PUBKEY="ssh-ed25519 AAAA... you@host"   # required — no other remote access exists
WIFI_SSID="your-network"                     # leave blank for Ethernet-only
WIFI_PASS="your-password"
WIFI_COUNTRY="GB"                            # ISO 3166-1 alpha-2
HOSTNAME=""                                  # optional
```

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
straight out of the `.img` inside the zip:

```
unzip -p image_<date>-gexis-player.zip > /tmp/gexis.img
OFFSET=$(( $(fdisk -l /tmp/gexis.img | awk '/FAT32/{print $3}') * 512 ))
mdir -i "/tmp/gexis.img@@${OFFSET}" -/
mcopy -i "/tmp/gexis.img@@${OFFSET}" ::cmdline.txt -
```

## Testing a build

`george@rig.local` is the test target.

```
aplay -D output <testfile>   # card referenced by name, no `type plug`, no index
```

Not yet done as of the 2026-09-05 build: flashing and hardware verification
(Phase 0 criteria 3–5). The build itself is confirmed good (criteria 1, 2, 6,
amended 7), and the boot partition is confirmed correct by direct inspection
(criterion 3's mechanism) — but nothing has actually booted on real hardware
yet.
