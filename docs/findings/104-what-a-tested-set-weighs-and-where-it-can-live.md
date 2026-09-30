# Finding 104 — What a tested set weighs, and where it can live

**Date:** 2026-09-30
**Question:** [ADR-0105](../decisions/0105-updates-over-the-network.md)
decision 3 chose a **tested set** - every operating-system package a release
was tested with, kept downloadable by us - *"measured in a prototype first"*.
How large is it, where do its packages come from, do the archives keep old
versions, and can the hosting ADR-0105 named hold it?

**Scope:** the package set installed on `sofa-pi` (the second card; image
755-era, packages installed 2026-09-29), read with `dpkg-query` and
python-apt. The live archives' `binary-arm64` indexes fetched 2026-09-30 (Debian
`trixie` main, contrib, non-free, non-free-firmware, `trixie-updates`,
`trixie-security`; Raspberry Pi `trixie` main). GitHub's limits as documented
on 2026-09-30, not tested. **Not measured:** how fast the set moves over weeks
(one day of drift only), the packages our own build adds on top once they are
packaged (13c step 1), any upload or download through GitHub.

## The set

| From | Packages | Package files |
|---|---|---|
| Raspberry Pi archive | 140 | **497 MB** |
| Debian | 884 | 371 MB |
| Debian security | 3 | 12 MB |
| **Total** | **1,027** (784 arm64, 243 `all`) | **880 MB** |

**The Raspberry Pi part is small in count and large in size**: Chromium 122 MB
and `chromium-common` 43 MB, two kernels at 32 MB each (`-v8` and `-2712`, the
Pi 5's), firmware (`firmware-atheros` 38 MB, `firmware-mediatek` 26 MB),
`mesa-vulkan-drivers` 33 MB. Some of it is weight a Pi 4 player does not need;
not pruned here.

## Do the archives keep old versions?

- **Every installed version is in a live archive today** (0 of 1,027 missing).
- **The Raspberry Pi archive indexes one version per package** (1,471 names,
  none listed twice). A new version replaces the old one in the index at once.
- **Its pool keeps the files**: `pool/main/a/alsa-lib/` still holds 1.1.8
  through 1.2.14, both `1.2.14-1+rpt1` and `+deb13u1`. So what happened on
  2026-09-12 (ADR-0021's amendment) was the index dropping `1.2.14-1+rpt1`, not
  the file: apt cannot install a version its index does not list, and a
  download by direct link still works. How long the pool keeps files is not
  documented; alsa-lib's go back to Debian 10.
- **Debian has `snapshot.debian.org`** (answers); **Raspberry Pi has no
  equivalent** (`snapshot.raspberrypi.com` does not resolve).

## How fast it moves

One day after installation: 7 packages newer, all Debian security (OpenSSL,
PCRE2, Node.js), 16 MB. One day is not a rate; the image built on 2026-09-30
gives a second point.

## Where it can live (GitHub's documented limits)

| | GitHub Pages | GitHub Releases |
|---|---|---|
| Total | **1 GB** per site | no limit on a release's total, nor bandwidth |
| Per file | git's 100 MB (Pages publishes a repository) | under 2 GiB |
| Count | - | 1,000 files per release |

- **Pages cannot hold it.** One set is 880 MB of the 1 GB; the second release
  does not fit, and Chromium's 122 MB file exceeds git's per-file limit.
- **Releases can**, within their documented limits, but **1,027 packages
  exceed one release's 1,000 files**: a set spans two releases, or the Debian
  part is served another way.
- Serving an apt repository from Releases (a flat repository whose files sit
  at `releases/download/<tag>/`, behind GitHub's redirect to its storage) is
  **not tried**.

## What it bears on

- ADR-0105's hosting candidate (Pages) is out for the OS set; the record is
  amended to say so, and the hosting is a decision for George.
- The Debian half can be pinned **without copying** by pointing the device at
  a `snapshot.debian.org` date; the Raspberry Pi half has to be copied.
