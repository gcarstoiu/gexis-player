# ADR-0107 — Our parts as Debian packages

**Status:** **Accepted** — George, 2026-09-30: *"agree with all 3
decisions"* (below, each marked **Decided**).
**Phase:** 13c step 1 ([DEVELOPMENT.md](../DEVELOPMENT.md)).
**Builds on:** [ADR-0105](0105-updates-over-the-network.md) §1 (*"Our parts
become Debian packages, and the image is built from them"*), which named five
packages and left the rest to this record.

## Context

ADR-0105 §1's table - `gexis-core`, `gexis-ui`, `gexis-system`, `gexis-skins`,
`gexis-player` - was written before anyone listed what the image stages
actually put on the card. The list (2026-09-30, every script in
`image/stage-gexis/` read, 1,600 lines) found what the table does not cover:

- **Seven third-party components with no home**: peppyalsa (compiled from
  source, patched), go-librespot and beszel-agent (downloaded arm64 binaries),
  the PeppyMeter and PeppySpectrum engines, the DSEG font, and the Plexamp
  adapter from `gexis-plexamp`.
- **Ten edits to files other packages own**: `cmdline.txt` four times (first
  boot, `cgroup_enable=memory`, `console=tty3`, the quiet-boot options),
  `config.txt` (`disable_splash`), `/etc/samba/smb.conf` (an include), a whole
  `/etc/machine-info`, the Plymouth default theme, the initramfs rebuild, the
  `gexis-plugins` group and the `beszel` user, and `apt-mark hold` on alsa-lib.
- **Seven files the player rewrites at runtime** that a package would
  overwrite on upgrade: `device-name.env`, `machine-info`, `hostname`/`hosts`,
  go-librespot's `config.yml`, `output.conf`, the spectrum engine's
  `config.txt`, the journald drop-in.
- **About eleven programs in `/usr/local`** and **every unit in
  `/etc/systemd/system`** - places a package must not install into.
- **Build inputs not pinned**: the core's Python environment pins its two
  direct dependencies, not the rest, and fetches its build backend from PyPI;
  peppyalsa is pinned by commit and cloned without a checksum.
- **Generated at build time and wrong after an update**: `/etc/gexis/image.info`
  (the version the panel shows) and `packages.txt`.

## Proposed

### The packages

| Package | Arch | What it carries |
|---|---|---|
| `gexis-core` | arm64 | the core in its own Python environment at `/opt/gexis-core/venv` (built at that path), its units, built-in plugin manifests |
| `gexis-ui` | all | the built pages |
| `gexis-system` | all | our units, ALSA files, scripts, splash, Samba and Avahi files, kiosk, the Peppy driver and its configs; the edits to other packages' files, made by its scripts |
| `gexis-skins` | all | stock, Gelo5 and animated skins, letterboxed at package build |
| `gexis-peppyalsa` | arm64 | the patched peppyalsa library |
| `gexis-peppy-engines` | all | PeppyMeter, PeppySpectrum, the DSEG font |
| `gexis-go-librespot` | arm64 | go-librespot, as upstream built it |
| `gexis-beszel-agent` | arm64 | beszel-agent, as upstream built it |
| `gexis-plexamp` | all | our Plexamp adapter (Plexamp itself stays fetched on the device, ADR-0100) |
| `gexis-player` | all | depends on **exact** versions of all of the above and of alsa-lib: **the release** |

**One package per third-party component**, versioned by that component's own
version (`gexis-go-librespot 0.9.0-1`), so updating one is updating one
package - which is what ADR-0106's *our plugins update with the release*
needs.

### Built in a container, reproducibly

`make packages` builds every `.deb` in an **arm64 Debian trixie container**
(`arm64v8/debian:trixie` under qemu, working on R2D2 as of 2026-09-30), so
nothing depends on the host's Python or `dpkg`. `make image` then installs the
packages from a local directory. The core's environment is built from a
**lock file with hashes** (every dependency, transitive included, and the
build backend), so the same commit gives the same environment.

### Files the player rewrites: shipped as defaults, placed once

Each ships under `/usr/share/gexis/defaults/` and `gexis-system`'s install
script copies it into place **only if it is not there**. An update never
touches a user's name, output choice or Spotify sign-in.

### Edits to other packages' files: made by our scripts, idempotently

Each edit becomes a small function in `gexis-system`'s install script that
checks before it changes anything, so running it again changes nothing, and a
release can change an edit. An edit to `cmdline.txt` or `config.txt` takes
effect only at boot; **the updater restarts the device when one changed**
(ADR-0105 §4 said *"only when the kernel or firmware changed"*: add *or the
boot configuration*). The first-boot `systemd.run=` entry stays an image-only
edit: it belongs to one card, not to a release.

### The version the device reports

From the installed `gexis-player` package, not a build stamp. `image.info`
keeps only the image's build date; `packages.txt` is generated after every
install, not frozen at build.

## Decided (George, 2026-09-30)

1. **Move our programs and units to where packages belong** -
   `/usr/lib/gexis/`, `/usr/bin/`, `/lib/systemd/system/` - out of
   `/usr/local` and `/etc/systemd/system`. **Decided: yes, now.** Nothing
   of a user's lives in those paths; `/etc/systemd/system` is where a user's
   own overrides belong, and a package that owns files there fights them.
   `verify-image.sh` and the core's references move with them, checked by the
   image build. The cost is one careful step, before there are devices in the
   field whose paths would have to be migrated.
2. **`core.toml` ships without an LMS address.** Today every image points at
   `192.168.178.188:9000`, George's server, as its default. First-boot setup
   already asks (*find / address / off*, ADR-0104), and the `lms_server`
   setting overrides the file. **Decided: ship none**; a device with no
   answer has LMS off until setup gives it one. George's own card keeps its
   address through setup or a restore.
3. **`pi` may use `sudo` without a password**
   (`/etc/sudoers.d/010_pi-nopasswd`). Convenient for development over SSH;
   on a device in someone's home it means anything that gets a shell as `pi`
   owns the device. **Decided: kept in development images, decided
   before the first public release** - a release-blocking item in
   DEVELOPMENT.md, not part of this step.

## Not in this record

- Where the repository lives (ADR-0105, amended 2026-09-30: George's
  decision owed).
- Signing (ADR-0105 §2) and the updater (§4) - later steps of 13c.

## Versions for components pinned by commit (settled 2026-09-30)

peppyalsa and the Peppy engines are pinned by commit, and a version made of
the commit ID does not sort by age. They carry the commit's date instead
(George: *"technical choice"*): `0.44+git20260726.7dcb0c5-1` (upstream's
own 0.44, then the date) and
`0.1+meter20260724.ee2de28+spectrum20251228.c8be00d-1`. Both sort above the
first builds' `0.0.0+git…`. peppyalsa's build checks the date against its
clone; the engines' tarballs carry none, so their dates sit beside their pins
and move with them.

## Unverified

- The core's environment built under qemu at `/opt/gexis-core/venv` and
  installed from a `.deb` into the image behaves as the one built in the
  image's chroot does today (same Python 3.13, same wheels) - the first thing
  step 1 checks.
- How long a full package build takes under qemu.
