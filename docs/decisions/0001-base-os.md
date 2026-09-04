# ADR-0001 — Base OS

**Status:** Accepted
**Date:** 2026-09-04
**Note:** This record was drafted in conversation long before the repository
existed and left open, blocked on a single question. It is written here for the
first time. See `docs/decisions/README.md` for the numbering gap.

## Context

The candidates were **Raspberry Pi OS Lite (64-bit)** and **DietPi**, with
Armbian considered and dropped.

The record sat open for one reason: whether DietPi offers a reproducible,
CI-drivable image build comparable to Volumio's `build.sh` or moOde's pi-gen
wrapper. ADR-0021 made that a hard requirement rather than a preference.

Since the question was first raised, several other records have changed the
criteria. They are listed below because they narrow the decision considerably.

## The blocking question, answered

**DietPi does not offer a supported image-build pipeline for third parties.**

DietPi has two tools:

- **`dietpi-installer`** — converts an existing Debian system into a DietPi
  system. The installer's own comments describe its expectation as a running
  Debian 12 or later, ideally minimal, "Raspberry Pi OS Lite-ish".
- **`dietpi-build`** — used internally to produce DietPi's own images.

On `dietpi-build`, a DietPi maintainer states plainly in a project discussion
that there is no documentation for the feature because it is not intended for
public usage, that people normally use the install script to build their own
image rather than the build script, and that they are not sure the build script
works outside GitHub because they use it for their own GitHub Actions.

The same thread records that Ubuntu hosts are unsupported, and that the script
assumes an arm64 host is not cross-building — the reporter's build produced an
image with no kernel and no device tree until they moved to an amd64 VM.

So the supported third-party route is the **installer applied to a base image**.
That is a conversion step, not a build pipeline. It can be automated, but it
inherits an image somebody else built, which is the opposite of what ADR-0021
requires.

## Decision

**Raspberry Pi OS Lite, 64-bit.**

## Why the other criteria all point the same way

**DietPi on a Pi is a conversion of Raspberry Pi OS Lite anyway.** It keeps the
Raspberry Pi apt repositories and kernel — the installer pulls
`raspi-utils-core`, `raspberrypi-sys-mods` and `raspberrypi-archive-keyring` —
and DietPi's own project material describes them as maintaining userland,
software catalogue and minimal images rather than kernels. Choosing DietPi would
mean adding a conversion layer on top of the thing we would otherwise use
directly.

**ADR-0021 chose `firstrun.sh` for first-boot provisioning.** That is the
Raspberry Pi OS mechanism. DietPi has its own equivalent in `dietpi.txt` and a
first-boot FAT partition, which is capable but different, and we would be
building against their convention instead of the platform's.

**ADR-0021 chose in-place `apt` updates and pinned `alsa-lib`.** Findings 002
and 003 characterise the metering path against `libasound2t64 1.2.14-1+rpt1`
specifically — the stock Raspberry Pi package. Building on the distribution that
ships it keeps the tested version and the shipped version the same thing.

**labwc is the Raspberry Pi OS default Wayland compositor**, since October 2024.
The UI is Chromium in kiosk mode under labwc. On DietPi that stack is assembled
by hand.

**Phase 1 was measured on Raspberry Pi OS Lite.** Findings 002 and 003 were
taken on this exact base. Choosing it means those results describe the product
rather than a rig.

**Footprint is not a criterion.** One published comparison reports DietPi using
38% less RAM (109 MiB against 176 MiB) and 77% less disk (953 MB against 4.1 GB)
than Raspberry Pi OS Lite, five minutes after boot on a Pi 4. That is a real
difference and it is explicitly not a design driver here: the standing principle
is to spend the hardware on responsiveness, and roughly 67 MiB is negligible on
a 4 GB board that will run Chromium.

## What DietPi offered that we lose

Stated honestly, because these were the reasons it was a candidate:

- **`dietpi-software`** — optimised installs for Squeezelite, Shairport Sync,
  Snapcast and similar. We are not using distribution glue for renderers; all
  three Pi audio distributions converge on the same underlying components, and
  ADR-0013 requires our own adapters regardless.
- **`dietpi.txt` automation** — genuine first-boot automation. `firstrun.sh`
  covers our needs and is the platform convention.
- **A smaller base** — see above.

There is also a licence consideration: DietPi's scripts are GPLv2, and building
on their provisioning layer would raise derivative-work questions for a public
repository. Not decisive, but it does not argue for them either.

## Build tool

Two candidates, both from Raspberry Pi:

- **pi-gen** — the tool used to build Raspberry Pi OS itself. moOde wraps it,
  which is a working precedent for exactly our use case.
- **rpi-image-gen** — newer, YAML-configured, and described by its authors as
  under active development.

**Recommendation: pi-gen**, on the grounds that it is proven for this purpose and
has a precedent in the same product category. `rpi-image-gen` is worth revisiting
once it settles; the decision is not load-bearing enough to gamble on a tool
under active development.

This is a sub-decision and is revisitable without reopening the base OS choice.

## Consequences

- Findings 002 and 003 apply to the product directly, not by inference.
- The apt repositories, kernel and `firstrun.sh` mechanism are all the platform's
  defaults, so less of the base is ours to maintain.
- We inherit Raspberry Pi's release cadence and their decisions about what a
  "Lite" image contains, including `dtparam=audio=on`, which is why the DAC
  enumerates at card index 3 (Finding 002) and why ADR-0009 forbids index
  references.
- No conversion layer.

## Unverified

- Whether `pi-gen` builds cleanly on the CachyOS dev machine, or needs a Debian
  container. moOde's wrapper presumably addresses this.
- Whether `rpi-image-gen` would be materially better, since it has not been
  evaluated.
- Whether anything in a stock Lite image needs removing rather than merely
  configuring. Nothing found so far, but the image has not been audited.
