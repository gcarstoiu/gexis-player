# ADR-0021 — Deployment as a flashable image

**Status:** Accepted (Q1 distribution channel, Q3 archive snapshot pinning deferred; see below)
**Date:** 2026-09-04
**Blocked by:** ADR-0022 handed this record the first-boot provisioning problem
**Overlaps:** ADR-0001 (base OS, still open)

## Context

Delivery is a flashable image, decided during the architecture discussion. We
own the whole system, which is what makes the bit-perfect claim provable rather
than conditional on what a user did to their own OS.

That decision left three things unaddressed, and ADR-0022 added a fourth.

## Why image, not package

- **The ALSA chain must be exactly as specified.** ADR-0009 makes `output` a
  single point of audit. A package installed onto an arbitrary system inherits
  whatever the user has done to their ALSA configuration, and the bit-perfect
  claim becomes conditional.
- **Held and pinned versions.** Finding 001 showed moOde holding `libasound2t64`
  at a patched version. We do not need that patch, but we do need to know which
  alsa-lib we shipped when someone reports a metering fault.
- **The renderer set is fixed and known.** Arbitration assumes exactly the
  renderers we installed.

Cost: users cannot add our player to an existing Pi that is doing something
else. Accepted.

---

## The first-boot problem, and what the research found

ADR-0022 made text entry remote-browser only. Wi-Fi credentials are text, and
without Wi-Fi there is no remote browser.

The obvious answer — "users flash with Raspberry Pi Imager and enter Wi-Fi in
the customisation dialogue" — **does not work for a custom image file.**
Raspberry Pi state that <cite index="4-1">customisation of custom image files was never truly supported, was possible only by means of a defect, and that the defect was dangerous because Imager had no way of knowing whether the customisation was appropriate for the image</cite>. Users of Imager 2.x report the
customisation step greyed out and skipped when a custom OS is selected.

There is, however, a supported route. Imager reads an online OS manifest, and
each entry carries an `init_format` metadata item telling Imager what style of
customisation the image supports:

| `init_format` | Mechanism |
|---|---|
| `none` | no customisation; the default when omitted |
| `systemd` | `firstrun.sh` style |
| `cloudinit` | standard cloud-init, as used by Ubuntu Server images |
| `cloudinit-rpi` | enhanced cloud-init with Raspberry Pi options |

`cloudinit-rpi` additionally exposes Raspberry Pi-specific options such as
enabling SPI or I2C, but requires the image to carry the `cc_raspberry_pi`
cloud-init module and a `raspi-config-vendor` package adapted for the
distribution.

An image can reach users through Imager in two ways: a **self-hosted repository**
consumed with `rpi-imager --repo <url>`, of which a community-driven example
exists, or by **applying to appear in Imager's community categories** alongside
official images.

**This makes the blocker solvable without inventing anything**, but it means the
distribution channel and the first-boot mechanism are one decision, not two.

---

## Resolved

### Updates are in-place package updates

**No reflashing.** Version 1.1 reaches a 1.0 user over the network, `apt`-style,
from a repository we host. Reflash and A/B partitioning were both rejected.

*Rationale:* reflash means a user rebuilds their device for a bug fix and loses
settings, pairings and network configuration. A/B partitioning is the robust
appliance answer but costs partition complexity and roughly double the system
storage for a problem we do not yet have.

#### This changes what the image guarantees

The argument for shipping an image was that we own the whole system, which is
what makes the bit-perfect claim provable. **With in-place updates the image is
the starting point, not the guarantee.** A running device drifts from any image
we ever shipped.

The claim therefore has to be maintained by the update mechanism rather than by
the image alone:

- **`alsa-lib` is pinned and held.** Findings 002 and 003 establish the metering
  path's behaviour against `1.2.14-1+rpt1` specifically. An unattended upgrade
  pulling a different alsa-lib could change metering or transparency silently.

  Note the inversion from moOde: they hold `libasound2t64` because it carries
  their patch (Finding 001). We would hold it because we have tested against a
  known version and have not tested against the next one.

- **The `output` device definition is a packaged file with a known checksum.**
  ADR-0009 made it a single point of audit; updates must not modify it silently,
  and a locally modified copy should be detectable.

- **The build records what it pinned**, so a fault reported against a running
  device can be traced to a package set.

#### Infrastructure this requires

An apt repository, signed, hosted, and maintained. That is real infrastructure
and it did not exist as a requirement before this decision. Not specified here.

### Configuration survives updates on the root filesystem

Follows from in-place updates: `apt` does not delete application data, so
settings, pairings and network configuration persist without a separate
partition.

- **SQLite settings store**, Bluetooth pairings, Wi-Fi configuration and
  `alsactl` state all live under conventional system paths.
- **No separate data partition.** It would solve a problem reflashing would have
  created, and we are not reflashing.

#### The root filesystem is read-write

Read-only root is the usual appliance choice on SD cards and was considered.
**In-place `apt` updates require a writable root**, and an overlay that is
remounted for every update is complexity without a matching benefit here.

Accepted cost: SD card wear and corruption risk on unclean power loss are not
mitigated at the filesystem level. Consistent with the standing principle that
flash wear is not a design driver.

### First boot is provisioned before first boot

For the first release, network credentials are placed on the boot partition
before the card is booted — either by Raspberry Pi Imager, or by editing the
boot partition directly.

This settles **Q2**: the image supports the **`systemd` / `firstrun.sh`**
mechanism rather than cloud-init.

*Rationale:* the same file works whether written by Imager or by hand. A user
editing the boot partition manually and a user going through Imager's
customisation dialogue produce the same artefact, so there is one path to build
and test rather than two. `cloudinit-rpi` would additionally require the
`cc_raspberry_pi` module and a vendored `raspi-config` package for our
distribution, which is more work for options we do not need.

#### Consequence: manual editing is the guaranteed path

Per the research above, Imager will not offer customisation for a custom image
file unless the image is listed in an OS manifest. So until that exists, **the
documented first-boot procedure is editing the boot partition**, and Imager
customisation is an improvement layered on later rather than the assumed route.

The documentation must therefore carry an explicit, correct procedure for this.
It is the first thing every user does, and getting it wrong means a device that
never appears on the network.

### Setup hotspot is a Could

An access point on first boot with a setup interface, so the user configures
Wi-Fi from a phone with no card editing at all, is the right long-term answer
and is **Could tier**. Not in the first release.

When it is built it does not replace the boot-partition path, which remains the
recovery route when the configured network is unavailable.

## Deferred

### Q1 — distribution channel

Three routes exist and the choice does not block anything now:

- **Plain `.img` download** — simplest, no customisation dialogue.
- **Self-hosted Imager repository** via `rpi-imager --repo <url>` — gives a
  customisation dialogue, but the flag is a barrier for non-technical users.
- **Application to Imager's community categories** — best experience by a
  distance, but a review process we do not control or schedule.

The last is the outcome to aim at and cannot be a dependency for a first
release. Revisit when there is something to distribute.

### Q3 — archive snapshot pinning

Not adopted. Raspberry Pi's and Debian's apt archives are live, so a rebuild
from the same commit at a later date can resolve different transitive package
versions even though our own pinned commit is unchanged (see Reproducibility,
below). Pinning the build to a dated snapshot mirror would make a rebuild
identical over time, at the cost of standing snapshot infrastructure.

No concrete need has appeared yet. Revisit if reproducing an old build's exact
package set is ever actually required — e.g. bisecting a regression against a
specific shipped archive state — rather than building it speculatively.

## Reproducibility

Whatever is chosen, the build must be CI-drivable and must record exactly what
it produced: every build writes a manifest of resolved package versions
alongside the `.img`, so a fault reported against a shipped image can be
traced to a package set.

**Rebuilding is not guaranteed to reproduce that same set.** In-place `apt`
updates (above) mean a running device diverges from its image after its first
update anyway — reproducing an image tells us what shipped, not what a given
device is currently running. The manifest exists to answer "what did we ship,"
not to pin the archive in time. The one package that must not drift silently,
`libasound2t64`, is pinned and held for that specific reason (Findings
002/003), independent of whether the rest of the build is reproducible.

Snapshot-pinning the apt archive (so a rebuild months later resolves
identically) was considered and deferred — see Q3 below — rather than built
into Phase 0 speculatively.

This is the same requirement that blocks ADR-0001: whether DietPi supports a
build pipeline comparable to Volumio's `build.sh` or moOde's pi-gen wrapper.

Two candidate tools, both from Raspberry Pi:

- **pi-gen** — used to build Raspberry Pi OS itself, and wrapped by moOde.
- **rpi-image-gen** — a newer tool for creating custom images, configured with
  YAML and described by its authors as under active development.

Neither has been evaluated. That evaluation belongs with ADR-0001.

## Out of scope

- Whether the image supports Pi models other than the 4. Out of scope by
  requirement.
- Factory reset. Implied by Q4 but not specified anywhere.

## Unverified

- Whether Imager's community listing process has requirements we would fail.
- Whether `rpi-image-gen` is stable enough to depend on, given its authors
  describe it as under active development.
- Reports exist of Imager 2.0.3 and 2.0.6 applying only some customisations even
  for official images. If accurate, first-boot provisioning through Imager is
  less reliable than it appears and a fallback matters more.

## Update, 2026-09-05: `init_format` has moved on upstream

Confirmed against `raspberrypi/rpi-imager`'s own
[`doc/os_customisation_formats.md`](https://github.com/raspberrypi/rpi-imager/blob/main/doc/os_customisation_formats.md)
while implementing Phase 0's first-boot fix: Raspberry Pi's own official
Trixie images have already moved past `init_format: systemd` (this record's
choice) to `cloudinit-rpi`, and their newest images again to a single
`rpi-preseed.toml` file with no `cmdline.txt` entry at all.

Not a reversal — `systemd`/`firstrun.sh` is still a supported `init_format`
value, we are not consuming Raspberry Pi's own OS-list manifest (that's Q1,
still deferred), and the record's stated rationale (one file, hand-edited or
Imager-written, one path to test) still holds for our own image. Recorded
because the platform keeps moving under this decision, and the next person
to touch first-boot provisioning should know that before assuming `systemd`
is still current upstream practice.

## Addendum, 2026-09-06: the Python core is packaged in a venv, not apt

Phase 2b needs to actually build and ship the core daemon (ADR-0017), which
raises the packaging question this record left implicit.

**Decision:** a Python venv, created at build time inside the pi-gen chroot,
at `/opt/gexis-core/venv`. `stage-gexis/03-core` runs `python3 -m venv`
against the target's own system Python (no separate interpreter shipped —
consistent with "pin the interpreter... version" above, since the venv
inherits whichever CPython `stage2` installed) and then `pip install` from a
pinned `requirements.txt` (exact versions; see Unverified below) plus the
core package itself, built from `core/`'s `pyproject.toml`. Systemd units
invoke `/opt/gexis-core/venv/bin/python -m gexis_core` directly — no
activation script, no PATH dependency, same pattern as pointing a unit at
`/usr/local/bin/go-librespot`.

**Why not apt.** None of the core's dependencies (`aiohttp`, `dbus-next`) are
needed at pinned exact versions that Debian's archive happens to carry, and
packaging our own `.deb` for a fast-moving in-tree daemon is more
infrastructure than a venv for no benefit `pip install -e` doesn't already
give at this stage. Same reasoning ADR-0017 already applied to the language
choice, extended to how it's installed. Revisit if the core ever needs a
dependency with a compiled extension absent from piwheels (the arm64 wheel
mirror `pip` already resolves against here) — that would make the venv
build-time cost real instead of the wheel-download-only cost it is now.

**Why `dbus-next`, not `dbus-python`.** `dbus-python` binds libdbus and needs
a C toolchain plus dev headers at install time — the image doesn't carry a
build toolchain in the shipped rootfs, and adding one for a single Python
binding is a cost with no other use. `dbus-next` is pure Python, asyncio-native
(the core is asyncio throughout, per its adapter design), and installs from a
prebuilt wheel. Confirmed available on piwheels for this target
(`arm64`/`cp313`) before choosing it, not assumed.

**Unverified:** `requirements.txt` pins exact versions (`==`) but not hashes.
`pip install --require-hashes` is the stronger guarantee and matches the
pin-and-verify discipline used for peppyalsa (commit) and go-librespot
(checksum) — not done yet because it adds a maintenance step (regenerating
hashes on every dependency bump) that hasn't been weighed against the
benefit. Revisit before this ships past Phase 2b.
