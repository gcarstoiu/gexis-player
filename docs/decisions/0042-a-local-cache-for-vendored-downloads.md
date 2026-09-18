# ADR-0042 — A local cache for the build's vendored downloads

**Status:** Accepted — George, 2026-09-19 ("let's do 1 for now")
**Date:** 2026-09-19
**Raised by:** George, on being told the image build re-downloads everything:
*"What if the resources are not there anymore? Shouldn't we have a backup as
well just in case?"*
**Relates to:** [ADR-0021](0021-deployment-flashable-image.md) (the flashable
image, whose Q3 — snapshot-pinning the apt archive — is the same question
asked of Debian rather than of GitHub)

## Context

Five third-party artefacts are fetched on every image build, verified by
sha256 and then thrown away: `05-peppy/01-run.sh` deletes its `mktemp -d` on
exit, and `02-renderers/01-run.sh` does the same.

| artefact | source | size |
|---|---|---|
| Gelo5's 84 skins | a release asset on `project-owner/PeppyMeter.doc` | 143 MB |
| PeppyMeter, PeppySpectrum, peppy_screensaver | `codeload.github.com`, three pinned commits on `foonerd/*` | small |
| DSEG7 Classic | `keshikan/DSEG` v0.46 | small |
| go-librespot | `devgianlu/go-librespot` v0.9.0 | ~10 MB |

**A sha256 protects integrity, not availability.** Every one of those pins
guarantees that what arrives is what we expected and guarantees nothing about
it arriving at all.

**The skins are the exposed one.** They are a release asset on a
*documentation* repository, uploaded once in March 2024, holding a pack a
community member posted on the Volumio forum. Nothing about that is a
distribution channel with an obligation to keep existing, and the corpus
cannot be reconstructed: [ADR-0015](0015-skin-renderer-peppymeter-format.md)
is written against those 84 skins by name. Everything else is either a
project's own release or a git object.

**This failure mode is not hypothetical here.** A build already broke on
moving upstream state on 2026-09-12, when a held pin met a moving archive.

## Decision

**The build reads a content-addressed local cache before it reaches the
network, and fills it on a miss.**

- **Keyed by sha256, not by name or URL.** The cache file *is* its checksum,
  so a hit is self-verifying and a changed pin is a different file rather
  than a stale one. There is no invalidation rule to get wrong.
- **On the host, outside the repository.**
  `${GEXIS_BUILD_CACHE:-$HOME/.cache/gexis-player/downloads}`, bind-mounted
  read-write into pi-gen's container. Outside the repo so `git clean` cannot
  delete 150 MB, and so a working tree stays small.
- **Optional, never load-bearing.** If the mount is absent the build fetches
  exactly as it does today. A build that has never seen the cache must still
  work, or the cache becomes a hidden build dependency.
- **The checksum is still verified after a cache hit**, not just after a
  download. A cache is a place a corrupted file could live.

## What this does and does not buy

**Does:** removes ~150 MB from every rebuild; makes a rebuild possible with
no network at all; and means an upstream that disappears tomorrow does not
stop the machines that have already built once.

**Does not: this is not the backup George asked for.** It protects the
machine holding the cache. A fresh clone on a new machine, or this one after
a disk loss, is exactly as exposed as before. **Option 2 — a mirror we
control — remains unbuilt and remains the only thing that actually answers
"what if it is not there any more".** It was deferred on 2026-09-19 because
it needs somewhere to host 150 MB, which is a decision this record does not
make.

Re-hosting is permitted when we come to it: `PeppyMeter.doc` and `PeppyMeter`
are GPL-3.0, as is this project ([ADR-0025](0025-project-licence-gplv3.md)). The
caveat already in `skins/README.md` stands — the forum post itself states no
terms, and that GPL-3.0 is the hosting repository's rather than Gelo5's own
statement.

## Alternatives considered

- **Vendor the skins into the repository** — 143 MB in a public repo, via
  git-lfs or a release rather than the tree itself. Rejected for now as the
  heaviest option, and it answers the same question a mirror would.
- **A pi-gen build-container volume instead of a host directory** — the
  container is already reused between builds (`PRESERVE_CONTAINER=1`), so a
  cache could live there. Rejected: `make clean` removes that container, and
  a cache that disappears with a routine cleanup is not a cache.
- **Cache by URL rather than by content** — needs an invalidation rule, and
  gets it wrong precisely when a pin changes, which is the moment it matters.
