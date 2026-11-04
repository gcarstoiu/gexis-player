# ADR-0173 — Releases built on GitHub

**Status:** **Built** 2026-11-03, in 1.12.1 (Testing serial 64). **Accepted**
2026-11-02 (George: decisions 1-3), Phase 27 (`ph-github-builds`); the trial
passed the same day
([Finding 140](../findings/140-a-release-built-on-github-the-trial.md)). George
asked for it on 2026-11-02, before room correction, as building releases on
R2D2 has become troublesome. It was a *Should* idea since 2026-10-18: the
packages and the image built on GitHub's ARM machines from the release tag,
signing kept local, a trial build first. The rest is Claude's proposal.
**Builds on:** [ADR-0042](0042-a-local-cache-for-vendored-downloads.md),
[ADR-0105](0105-updates-over-the-network.md),
[ADR-0107](0107-our-parts-as-debian-packages.md),
[ADR-0108](0108-how-a-release-is-published-and-found.md).

## Context

**Today everything is built on R2D2**, an x86_64 machine, with each ARM step
emulated by qemu:
- the ~20 packages, one arm64 Debian container each (`packaging/build.sh`;
  squeezelite, shairport-sync, nqptp and peppyalsa compiled from source);
- the UI on the host (ADR-0023);
- the image by pi-gen in Docker, privileged, reusing a container whose
  volumes hold the base OS stages (8.4 GB, `image/README.md`): about 15
  minutes warm, 40 cold (`BUILD-TRAPS.md`; 1.12.0's took 940 s);
- the release (`packaging/release/build.sh`): the OS packages fetched and
  checked against their signed indexes, the four parts signed with the
  release subkey, then uploaded by `publish.sh`.

**What only R2D2 has**:
- that warm container;
- the download cache (ADR-0042, 171 files, 2.1 GB): the only copy if an
  upstream removes a pinned file;
- the packages cache: skin packs and wallpapers, about an hour each to
  rebuild under emulation (`packaging/build.sh`);
- every earlier release in `gexis-release-out`. `fetch-tested-set.py` takes
  from it the OS versions the Raspberry Pi archive no longer keeps, and
  `reuse.py` trusts a published file only against a local copy;
- the signing subkey (ADR-0105 decision 1);
- the tested image in `image/deploy`, which `--promote` compresses.

**What has gone wrong building here**, each recorded:
- R2D2's `/` filling up: Docker keeps images on `/`, and pi-gen rebuilds its
  1.16 GB build image every build (HANDOFF; 3.6 GB free before 2026-11-02's
  clean-up, which removed 9.9 GB of pi-gen leftovers and 1.1 GB of images);
- a copy-out killed by memory pressure (`make fetch-deploy`);
- no edits while an image builds, because of live bind mounts;
- `make clean` destroying the warm stages;
- a pinned package vanishing from the archive (alsa-lib);
- a rebuilt skin pack refused because its bytes differed (1.4.0);
- the release worktree, the image's path and `verify-image.sh`'s checkout
  having to line up by hand (0.11.0, 1.1.0).

The traps are in `docs/BUILD-TRAPS.md`.

**GitHub's machines** (sources below, read 2026-11-02):
- **arm64 runners are free for public repositories** (generally available
  since 2025-08-07): `ubuntu-24.04-arm`, 4 vCPU, 16 GB RAM, 14 GB of disk
  guaranteed free. More is usually there: 49 GB on an arm64 runner after a
  clean-up (2025-11), 16-19 GB on x64 as it comes. arm64 runners had no
  second disk at `/mnt`.
- **A job may run 6 hours.** Twenty jobs at once on the free plan.
- **A release file may be up to 2 GiB**, with 1,000 per release and no limit
  on the total: the image's `.xz` (1.1 GB) fits, the raw image (5.2 GB) does
  not.
- **Workflow artifacts** are kept up to 90 days. Whether the free plan's
  500 MB of storage applies to public repositories is not stated, so
  nothing large is passed as an artifact.
- **The build cache** is 10 GB per repository, each entry evicted after 7
  days unused.
- **pi-gen on GitHub**: RPi-Distro's own CI is GitLab. `usimd/pi-gen-action`
  runs it on `ubuntu-24.04-arm`. Building arm64 trixie under qemu on x64
  runners has failed since about February 2026 (its issue #179, open); its
  users moved to the arm64 runners. No measured build time was found.
- **Build attestations** are available to public repositories:
  `gh attestation verify` shows which repository, workflow and commit built
  a file of a given digest.
- **Environments with a required reviewer** are on the free plan for public
  repositories.
- **Actions have been hijacked through their tags**: tj-actions/changed-files
  in March 2025, trivy-action in March 2026. Pinning each action to a commit
  is GitHub's own advice.

## Proposed (Claude)

1. **GitHub builds the release from its tag.** One workflow,
   `.github/workflows/release.yml`, runs when a `v*` tag is pushed (the tag
   already goes on the release-notes commit), and by hand for a trial. On
   GitHub's arm64 machines, natively, without qemu, it:
   - builds the packages;
   - builds the UI and the image;
   - runs `verify-image.sh` from the same checkout;
   - builds the four parts, unsigned.

   It calls the same `make` targets and scripts as R2D2. Every image starts
   from a clean machine: no warm stages, no caches that only one machine
   has. It is **one job**, so nothing large passes between jobs as an
   artifact. Its runner is pinned (`ubuntu-24.04-arm`), not `-latest`.
2. **Signing stays on R2D2** (ADR-0105 decision 1; the idea of 2026-10-18).
   The workflow uploads the packages and indexes into each part. A part is
   named by its content, so an unchanged part is not uploaded again. It also
   uploads the image's `.xz` and its checksum to the release's page. Devices
   accept nothing that is unsigned, so nothing the workflow uploads is
   installed until R2D2 signs it. A Testing release's page offers the image
   unsigned until it is promoted. The README's link reads only the Latest
   release, which is Stable's.

   `publish.sh` then:
   - downloads only what it signs: each part's `Release`, `parts`, notes and
     history, a few kilobytes;
   - checks GitHub's build attestation, which shows the files came from this
     repository's workflow at that tag;
   - checks every hash;
   - signs, and uploads the signatures and the channel file.

   At promotion it downloads the image's `.xz` from the release (1.1 GB,
   about three minutes on 2026-11-02), checks it against the attestation,
   signs it as today, and uploads the 228-byte signature. The key never
   leaves R2D2, and no GitHub secret holds it.
3. **What only R2D2 had, kept on GitHub**:
   - **The downloads** (ADR-0042's deferred mirror): a pre-release `inputs`
     holding each pinned download under its sha256, read by the workflow
     before the upstream. It is filled once from R2D2's cache, current pins
     only, after a check that each may be redistributed. Software that may
     not be redistributed is fetched on the device
     ([ADR-0100](0100-software-we-may-not-redistribute-is-fetched-on-the-device.md))
     and is never in it.
   - **Earlier releases**: the published parts themselves, each file checked
     against its part's signed index. `reuse.py` and `fetch-tested-set.py`
     read GitHub instead of `gexis-release-out`.
   - **Skin packs and wallpapers**: taken from the last release's part when
     their version did not change (1.4.0's trap, now automatic), and built
     natively when it did.
4. **Build logs stay with the release.** The release page links the run, and
   the image's `.info` (its package list and pins) is attached.
5. **Hardened like any workflow that writes**:
   - actions pinned by commit;
   - read-only permissions, except for the one job that uploads;
   - no secret beyond GitHub's own token;
   - runs grouped per tag and never cancelled, which is the cancelled-run
     trap;
   - provenance attestations for the packages, indexes and the image.
6. **Nothing changes on a device**: the parts, channels, serials, notes,
   history and numbers stay as in ADR-0108, ADR-0110 and ADR-0116. A
   release built on GitHub cannot be told from one built on R2D2.
7. **A trial first**: v1.12.0 built on GitHub by hand and compared with the
   r1.12.0 built here. The OS packages and their versions must match, or
   each difference must be explained. `verify-image.sh` must pass, and the
   time and disk are recorded as a Finding. If the image does not fit, the
   fallbacks are in *If the trial fails*.

### Decisions for George

- **Decision 1, previews too.** The phase branch's packages are built by
  the same workflow, run by hand, and kept as an artifact for a few days.
  Ours weighed 76 MB in 1.12.0. *Corrected 2026-11-03:* that was 1.12.0's
  new packages; a preview downloads the whole set, 133 MB without the skin
  packs (1.12.1), 1.2 GB with them. R2D2 downloads them (`gh run download`)
  and installs them on a test player over SSH, as today. R2D2 then needs no
  Docker builds at all. *Recommended.* The alternative is releases only,
  with previews still built here.
- **Decision 2, the mirror in public.** The `inputs` pre-release hosts other
  projects' source archives and files under our repository, as ADR-0042
  allowed and deferred for want of a host. *Recommended*: only files whose
  licence allows it, listed with their licences. The alternative is GitHub's
  build cache. It is not public, but each entry is evicted after a week
  unused, so it is no mirror.
- **Decision 3, R2D2's build machinery afterwards.** Once the first release
  built on GitHub is out, remove from R2D2 (measured 2026-11-02):
  - the warm pi-gen container and its work volume, 8.9 GB;
  - the build images, 2.9 GB: pi-gen's 1.16 GB, the deb builder's 1.23 GB,
    Debian's arm64 base and the skin check.

  The images sit on `/`, which had 4.6 GB free. The scripts keep working for
  a local build from cold. *Recommended.* The alternative is to keep them
  warm as a fallback.

## Decided (George)

- **Decision 1, previews too** (2026-11-02), as proposed: a branch's
  packages are built by the workflow on request, downloaded to R2D2 and
  installed on a test player over SSH, over previews built on R2D2.
- **Decision 2, the mirror in public** (2026-11-02), as proposed: an
  `inputs` pre-release on gexis-player holds each pinned download under its
  sha256 and is read before the upstream. It is filled from R2D2's cache with
  the current pins only, each file's licence checked and listed. Chosen over
  GitHub's build cache and over the upstreams alone. ADR-0042's deferred
  mirror is built here.

  Then, with the list of 146 files seen first (2026-11-02):
  - the source archives of the two GPL binaries we redistribute
    (go-librespot, CamillaDSP) join it, as GPL-3.0 asks of whoever passes a
    binary on;
  - the four packages built from a git clone by commit (squeezelite,
    peppyalsa, nqptp, shairport-sync) build from GitHub's archive of that
    commit, through the cache and so the mirror. Their Debian revisions rise,
    so the next release carries new versions of the four.

  `packaging/inputs.tsv` lists every file with its licence; a release build
  fails on a download it does not list. The workflow fills its empty cache
  from the mirror before it builds, so `fetch-cached.sh` is unchanged: it is
  an input of the skin packs, and editing it would give each pack a new
  version for every player to download again.
- **Decision 3, R2D2's build machinery removed afterwards** (2026-11-02), as
  proposed: once the first release built on GitHub is out and verified,
  the warm pi-gen container, its work volume and the build images go. A
  local build stays possible, from cold. Chosen over keeping them warm as a
  fallback.

## The trial (2026-11-02)

v1.12.0, built on `ubuntu-24.04-arm` by its own `make packages` and `make
image`, with nothing cached ([Finding 140](../findings/140-a-release-built-on-github-the-trial.md)):
- the job took 27 minutes: packages 644 s, image 427 s (pi-gen 311 s, against
  940 s warm on R2D2), `xz` 333 s;
- the build's peak was 33 GB above the start, on a runner with 107 GB free;
- the image's 1,037 OS packages and versions are r1.12.0's;
- 18 of our packages are byte-identical to the published ones; the five
  skin packs differ in bytes at the same version, as on R2D2 since 1.4.0;
- `verify-image.sh` passed all 161 checks.

None of the fallbacks below is needed.

## If the trial fails

- **The disk** (14 GB guaranteed; pi-gen's work area was 8.8 GB, the image
  5.2 GB): remove the runner's preinstalled toolchains (15-30 GB by reports),
  and delete each stage's leftovers as the build goes. If it still does not
  fit, the image is built in two jobs: the OS stages, then ours, the first
  kept as a release file under 2 GiB.
- **The time**: a cold build once per release is acceptable within the
  6-hour job.
- **pi-gen itself** (privileged Docker, loop devices): pi-gen without
  Docker, directly on the runner (it has root), as its README allows.
- **Not a fallback**: x64 runners with qemu, broken for arm64 trixie since
  about February 2026, and larger runners, which are paid.

## Not in this phase

- Signing on GitHub, by an environment secret behind an approval. It would
  make GitHub part of every device's trust; ADR-0105 placed that on R2D2
  alone.
- Building for other boards: the Pi 5 stays where the ideas list puts it.
- The plugin repositories (`gexis-roon`, `gexis-airplay`, …) building their
  own tarballs; they remain releases cut by hand.

## Built (2026-11-03)

On `ph-github-builds`, released in 1.12.1:

- **`.github/workflows/release.yml`**: on a tag, *Packages and image* (read
  access only) and *Upload, unsigned* (the one job that may write, which
  attests); by hand, *kind: preview* or *release*. Actions pinned by commit,
  the runner pinned to `ubuntu-24.04-arm`.
- **The `inputs` mirror** (`packaging/inputs.tsv`, `packaging/inputs.sh`): 152
  files, 2.12 GB, uploaded from R2D2's cache; the workflow fills its cache
  from it and fails on an unlisted download.
- **Sources from archives** (`packaging/fetch-source.sh`): squeezelite -3,
  peppyalsa -6, nqptp -2, shairport-sync -2.
- **Earlier releases from GitHub** (`packaging/release/published.py`): every
  published part's index proven by the release key; `reuse.py`,
  `fetch-tested-set.py` and the skin packs read from it.
- **Signing apart** (`packaging/release/sign.sh`; `publish.sh --upload` on
  GitHub, `--sign` on R2D2, which checks each file's attestation first).

1.12.1 (run 41609042614): built in about 18 minutes and uploaded in 1.5,
then signed on R2D2 from four `Release` files, four `Packages` and the parts
list. Read back: Testing serial 64, every signature good, each part's
`InRelease` listing its own `Packages`. sofapi updated itself to it. A
preview by hand (`workflow_dispatch` from `main`, `next`'s packages) took
about 5 minutes; its artifact was 1.2 GB with the skin packs, which previews
now leave out. One OS package moved with the image:
`rpi-eeprom` 28.36-1, published by Raspberry Pi overnight. **Not yet seen:** a
card flashed from its image.

## Settings (ADR-0022)

None: nothing on a device changes.

## Measured before it is called done

- The trial: v1.12.0 on GitHub, its OS packages and versions against
  r1.12.0's, `verify-image.sh` passing, time and disk recorded. *Done
  2026-11-02, Finding 140.*
- A release built on GitHub from its tag, signed and published to Testing
  from R2D2 with nothing built there; the channel file read back with a good
  signature.
- A test player on Testing updating to it, and a card flashed from its image
  that sets up.
- With decision 1: a preview from the workflow installed on a test player.

## Sources

Read 2026-11-02.

- Runners: [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners);
  [arm64 for public repositories, GA](https://github.blog/changelog/2025-08-07-arm64-hosted-runners-for-public-repositories-are-now-generally-available/);
  free disk seen: [runner-images#14405](https://github.com/actions/runner-images/issues/14405),
  [getsentry/self-hosted#4046](https://github.com/getsentry/self-hosted/pull/4046);
  `ubuntu-latest` moving to 26.04: [runner-images#14748](https://github.com/actions/runner-images/issues/14748).
- Limits: [Actions limits](https://docs.github.com/en/actions/reference/limits);
  [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions);
  [dependency caching](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching);
  [about releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).
- pi-gen: [RPi-Distro/pi-gen](https://github.com/RPi-Distro/pi-gen);
  [usimd/pi-gen-action](https://github.com/usimd/pi-gen-action),
  [its issue #179](https://github.com/usimd/pi-gen-action/issues/179).
- Security: [secure use of Actions](https://docs.github.com/en/actions/reference/security/secure-use);
  [artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations);
  [environments and required reviewers](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments);
  tj-actions/changed-files: [GHSA-mrrh-fwg8-r2c3](https://github.com/advisories/GHSA-mrrh-fwg8-r2c3).
