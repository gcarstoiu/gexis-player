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

## What `make image` produces

`image/deploy/` will contain **two** images:

- `<date>-gexis-player-lite.img` — bare Raspberry Pi OS Lite, no
  customisation. A side effect of `stage2/EXPORT_IMAGE` being unconditional,
  unmodified pi-gen. Harmless; ignore it.
- `<date>-gexis-player.img` — **this is the actual deliverable.** Built from
  `stage-gexis` on top of stage2: pins and holds `libasound2t64` at
  `1.2.14-1+rpt1`, builds peppyalsa from source, and installs
  `/etc/alsa/conf.d/output.conf`.

Each `.img` gets a matching `.info` file (from pi-gen's own
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

## Known issue: loop device setup in export-image (unresolved)

First build attempt (2026-09-05, this host) reached `export-image/prerun.sh`
and failed there — everything before it, including all of stage-gexis,
succeeded. `pi-gen/scripts/common`'s `ensure_next_loopdev()` calls `losetup -f`
to get the next free loop device, then extracts its minor number with a sed
pattern anchored on trailing digits. On this host `losetup -f` returned
`/dev/loop0 (lost)` instead of a plain path, the sed pattern didn't match
(no trailing digits), and the unmodified string got passed to `mknod`:

```
mknod: invalid minor device number '/dev/loop0 (lost)'
```

pi-gen retries this 5 times (`build.sh`'s own retry loop) and hard-fails when
they all reproduce identically. `/dev/loop0` appeared on the host itself at
the same timestamp, created by the container's own `mknod` — device nodes
for loop devices aren't container-namespaced (they're a shared kernel
subsystem), so a container run can reach out and touch host loop-device
state this way.

Not root-caused. Not a Debian-vs-Arch package-naming issue like the
qemu-aarch64 one above — this looks like a losetup/kernel-state interaction,
possibly specific to this kernel (`7.2.2-1-cachyos`) or to how this Docker
setup handles loop devices in a `--privileged` container. Nothing in
`export-image/` was touched to work around it.

## Testing a build

Flash `<date>-gexis-player.img`. Wi-Fi credentials and SSH enablement are
**not** baked into the image (ADR-0021) — add them to the boot partition by
hand after flashing, before first boot. `george@rig.local` is the test
target.

```
aplay -D output <testfile>   # card referenced by name, no `type plug`, no index
```
