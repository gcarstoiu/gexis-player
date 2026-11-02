# Finding 140 — A release built on GitHub: the trial

**Date:** 2026-11-02. **For:** Phase 27 (`ph-github-builds`), ADR-0173's
trial: does v1.12.0 build on GitHub's arm64 runner as R2D2 built it, and
what does it cost in time and disk?

## Scope

- **One run** of `.github/workflows/release.yml` on `ph-github-builds`
  (run 41502983922): `ubuntu-24.04-arm`, aarch64, 4 cores, 15 GiB RAM,
  Docker 28.0.4. The tag `v1.12.0` was checked out with its history and
  pi-gen's submodule. Its own `make packages` and `make image` ran,
  unchanged, natively with no qemu.
- **Nothing cached**: the downloads (ADR-0042) and the skin packs came from
  upstream. Node 24 came from `actions/setup-node`.
- **Compared with r1.12.0 as R2D2 built it:**
  - the image's package list (pi-gen's `.info`);
  - every package's SHA-256 against the release parts' signed indexes;
  - `verify-image.sh` on both images.
- **Not done**: the release's parts, signing or publishing; booting the
  image; a second run, to see how much the time and disk vary between
  runners.

## Results

| Step | Time |
|---|---|
| Packages (`make packages`, all 24, skin packs included) | 644 s |
| Image (`make image`: pi-gen's image built, stages 0-2 and ours) | 427 s, of which pi-gen 311 s |
| `verify-image.sh` | 1 s |
| `xz -T0 -6` of the image | 333 s |
| The whole job | 27 min |

R2D2, for comparison, under qemu:
- the image took 940 s warm (`.info` of r1.12.0) and about 40 min cold
  (`BUILD-TRAPS.md`);
- a skin pack took about an hour to rebuild (`packaging/build.sh`).

**Disk:** the runner had a 145 GB root with 107 GB free as it came, 122 GB
after removing preinstalled toolchains. The build's peak was 56.2 GB used,
33 GB above the 23 GB before it started. GitHub promises only 14 GB free.

**What was built:**
- **The image's OS packages** are identical to r1.12.0's: 1,037 each, the
  same names, versions and architectures.
- **18 of our packages are byte-identical** to the files r1.12.0 published.
- **The five skin packs** have r1.12.0's versions (`1.2.0+git33.96b8a42`)
  but different bytes. The same happens on R2D2 itself: `BUILD-TRAPS.md`
  has recorded since 1.4.0 that a rebuilt pack differs in bytes, and the
  release reuses the published file. Whether the files inside are the same
  was not compared.
- **`gexis-skins`** (the old pack) was built and, as on R2D2, belongs to
  neither the image nor the release (ADR-0111).
- **`verify-image.sh` passed all 161 checks** on GitHub's image. On R2D2's
  1.12.0 image it passes the same 161, but only with `GEXIS_BUILD_CACHE`
  set. Without it, the check of the Plexamp plugin against its pinned
  release is skipped: 160 was recorded for 1.12.0.
- **The image's `.xz`** was 1,107,015,592 bytes, against 1,110,437,508 for
  R2D2's 1.12.0. The images are not byte-identical; that was not expected,
  and they were not compared beyond the checks above.

## What it changes

- **ADR-0173 goes ahead as proposed.** The trial's three fallbacks are not
  needed: no two-job split, no pi-gen without Docker, no x64 runner.
- **A cold build on GitHub is faster than a warm one on R2D2**: 311 s
  against 940 s for pi-gen, 27 minutes for the whole job.
- **Skin packs are reused from the last release** when their version did not
  change, as the ADR proposes. A pack rebuilt elsewhere is a new file under
  an old version, which the repository refuses (1.4.0).
- **Freeing the runner's disk** took 41 s and was not needed on this
  runner. It stays, since only 14 GB is promised.
- **`verify-image.sh` always has the download cache on GitHub**, so the
  Plexamp check always runs there.

## The whole chain, unsigned (2026-11-02, later)

**Scope:** run 41525285578 on `ph-github-builds` (commit 52b77c0): the
branch built as a release, with the `inputs` mirror, the published parts
read from GitHub, the four packages built from source archives, and the
release's parts built unsigned (`build.sh --unsigned`). Nothing uploaded;
the parts compared with r1.12.0's.

| Step | Time |
|---|---|
| The mirror into the empty cache (152 files, 2.12 GB) | 59 s |
| The 123 published parts' indexes, each proven by the release key, and the published skin packs and wallpapers | 79 s |
| Packages | 179 s |
| Image | 420 s |
| The parts, unsigned, and the image's `xz` | 376 s |
| The whole job | about 19 min |

- **Every download came from the mirror**: nothing from upstream, and none
  the list lacks.
- **The skin packs and wallpapers were the published files**, not rebuilt:
  the packages took 179 s against 644 s in the trial.
- **The tested set**: 1,020 packages (136 Raspberry Pi, 884 Debian), all
  already on GitHub, none to upload.
- **The parts**:
  - **skins** came out as r1.12.0's own part, `skins-67e037cab00f`;
  - **ours** has 18 packages, 13 already published. The 5 new ones are the
    four from source archives and the branch's `gexis-player`;
  - **rpi and Debian** got new names with no new package. Their indexes
    are r1.12.0's apart from `Filename` lines:
    - Debian, 3 lines: a file r1.12.0's part held itself is now referred
      to in that part;
    - Raspberry Pi, 31 lines: the same for 4 files, and 27 now taken from
      another published part holding the same file, which R2D2's method,
      limited to parts built there, could not use.
- **nqptp and shairport-sync from archives** still report 1.2.9 and 5.6.2.
  Without `.git` they take the version from `configure.ac` instead of `git
  describe`, which gave the same at their tags. The bytes differ from the
  `-1` builds.
- **`verify-image.sh`** passed every check; the disk's peak was 58.1 GB.
