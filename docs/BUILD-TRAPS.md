# Traps when building and releasing

Moved from `HANDOFF.md` verbatim on 2026-10-29 (George), so that HANDOFF
stays current state. **Read before any package build, image build or
release.** How each was found is in `docs/HANDOFF-ARCHIVE.md` (2026-10-12
block) and `docs/LESSONS.md`. The steps themselves are in
`docs/tech/updates-and-releases.md` §4.

**Since 1.12.1 releases are built on GitHub** (ADR-0173): `release.yml` on the
tag, then `publish.sh --sign rX --channel testing` on R2D2. The *Building*
traps below are a local build's, kept for when GitHub is unavailable.

**On GitHub**
- **Parse a workflow before pushing it** (2026-11-02): a `: ` inside a
  one-line `run:` is YAML's key separator, and GitHub rejected the whole
  file with no job started. `~/projects/ha-venv/bin/python` has PyYAML:
  `yaml.safe_load(open(".github/workflows/release.yml"))`.
- **Signing on R2D2** needs `GEXIS_RELEASE_GNUPGHOME=~/projects/gexis-release-key`,
  `TMPDIR` in `~/projects/scratch/` (promotion downloads the 1.1 GB image), and
  `packaging/release/out` linked to `~/projects/gexis-release-out` in the
  checkout it runs from (git-ignored; remove the link after). It refuses a
  file without an attestation from `release.yml` at the tag.
- **A download the build needs is listed in `packaging/inputs.tsv`** with its
  licence, or the release run fails; `packaging/inputs.sh publish` (with
  `GEXIS_BUILD_CACHE` set) puts it in the mirror.
- **`workflow_dispatch` needs the workflow on `main`**: previews by hand work
  only once a release PR has brought `release.yml` there.

- **The release tag goes on the release-notes commit, nothing after it**
  (1.4.0, 2026-10-22): a package's version is the last commit that touched it,
  and the notes are core's last change - a documents fix committed after them
  and tagged built core as `1.3.1+git67`. A fix found after the notes goes in
  *before* them (reorder the unpushed commits), then the tag.
- **A cancelled run blocks the release PR** (1.5.0, 2026-10-24; again 1.12.0,
  2026-11-02, from the HANDOFF commit merged into `next`): pushing `next`
  again cancels the run on the release commit, and `main`'s ruleset counts a
  cancelled *Core tests* as failed, though the PR's own run passed. **Push
  `next` again only once the release PR's checks have finished**; if a run
  was cancelled, re-run it (`gh run rerun <id>`).

**Building**
- **Clear space with `make prune`, never `make clean`**: `clean` destroys the
  warm pi-gen stages (~9 GB; a cold build is ~40 min against ~15).
- **Never `docker start pigen_work`** - it starts a build. Read its volumes
  with a throwaway `docker run --rm --volumes-from pigen_work ...`.
- **Do not edit `core/`, `ui/dist`, `skins` or `stage-gexis` while an image
  builds**: they are bind-mounted live, and the `.info` would name a commit
  the image does not hold.
- **If the copy-out dies after a finished build, `make fetch-deploy`**
  recovers the image; an interrupted copy can truncate an older file in
  `deploy/` - check sizes.
- **Deleting a stage does not delete what it installed** until
  `stage-gexis`'s work directory is cleared (LESSONS 45).
- **A pinned package can vanish from the archive** (`alsa-lib`, ADR-0021):
  `make image` then stops at `00-alsa`; read the archive's own `Packages`
  index before changing anything.
- **Package versions take 7 hex characters** (`build.sh --abbrev=7`); a
  history rewrite after previews makes dpkg see a downgrade - put a preview
  device back with `apt-get install --allow-downgrades`, dry run first.

**Releasing**
- **Run `verify-image.sh` from the release worktree** (local): from the main
  checkout it compares against code the release does not carry (0.11.0: five
  false fails). With `GEXIS_BUILD_CACHE` unset it skips the Plexamp check
  (1.12.0's 160 checks against 161); GitHub always has the cache.
- **A skin pack whose version did not change ships the published file**
  (1.4.0): a rebuilt archive with the same files differs in bytes, and the
  repository refuses one version with two contents. Automatic since
  ADR-0173: the workflow takes the last release's packs into the build cache
  (`published.py last`), and `build.sh` replaces a rebuilt one by the
  published file (`published.py prefer`).
- **GitHub caches `channels/<name>` for minutes after a publish**: verify the
  new file with `gh release download channels`, not the public URL.
