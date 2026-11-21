# ADR-0182 — Upstream releases checked daily, and a patch release for one part

**Status:** **Accepted** 2026-11-15 (George: options 1 and 2 together, after
go-librespot's fix for the Android app sat unreleased; the fourth, upstream
builds as a standing rule, not chosen). Items marked *Claude's choice*
**confirmed by George 2026-11-21**, all six as written.
**Relates to:** [ADR-0100](0100-software-we-may-not-redistribute-is-fetched-on-the-device.md)
(we choose the version; `packaging/check-upstream.sh`),
[ADR-0173](0173-releases-built-on-github.md) (releases built on GitHub),
[ADR-0181](0181-go-librespot-from-upstreams-own-build-until-its-release.md)
(the case that raised it).

## Context

`packaging/check-upstream.sh` reads each maker's latest release and names the
pins that are behind, but it runs only before a release, and releases are cut
from `next`, which waits for George's regression pass of everything on it. A
fixed renderer could wait weeks for both.

## Decision

1. **A daily check on GitHub** (`.github/workflows/upstream.yml`, daily and
   on demand). It runs `check-upstream.sh`; for each part we package whose
   pin is behind (go-librespot, CamillaDSP, Beszel, …):
   - it makes a branch from `main`, `bump-<part>-<version>`, with the pin
     moved - version, address, sha256, and both lines in
     `packaging/inputs.tsv` (the binary and its source archive);
   - it opens a pull request into `main` named for the part and version,
     linking upstream's release notes, which notifies George;
   - it starts the tests and a preview build on that branch (*Claude's
     choice*: started by the workflow itself, since a push by its own token
     starts no other workflow).
   For what the player fetches on the device (ADR-0100: Plexamp, Roon Bridge)
   and anything without a simple pin, it opens an issue instead. One pull
   request or issue per part and version, never repeated. A pin waiting for
   a release (ADR-0181) counts as behind only once a release contains its
   commit.
2. **A patch release for one part, from `main`**, independent of `next`:
   the bump branch is the release branch. Preview on a test player (sofapi,
   or where the problem was seen), the part's checklist, one line of notes
   approved by George, tag `vX.Y.Z+1` on the branch, the usual build, signing
   and pull request, merged by George; then `main` into `next` and `docs`.
   Players fetch the changed part, the core (it carries the notes) and the
   release's own package; unchanged parts are not fetched again.
3. **Each part has its checklist** in `docs/tech/updates-and-releases.md`
   (*Claude's choice*). go-librespot's: a cast, volume from the phone and the
   panel, skip, another source taking over, a group, and the fault the
   release is for.

## Consequences

- From upstream's release to a preview on a player: about a day, plus
  George's go-ahead to install it (installing stays a session's step: the
  players are on the home network).
- `main` and `next` each gain a pin change at times; `next` takes it at the
  merge of `main`, as after every release.
- The workflow writes branches, opens pull requests and issues, and starts
  the two workflows, so it gets those permissions and no others; `main`'s
  ruleset still takes the change only through George's merge.

## Built (2026-11-15)

`.github/workflows/upstream.yml` runs `packaging/upstream-daily.sh` daily
(05:23 UTC) and on demand; `packaging/upstream-bump.py` moves a pin;
`check-upstream.sh` also lists what is behind for them (`UPSTREAM_TSV`). The
steps and the checklists are in `docs/tech/updates-and-releases.md`, *A
release of one part*. Checked against the real releases: CamillaDSP moved to
v4.1.3 and go-librespot to v0.10.5 gave the sums already recorded, byte for
byte; the whole run, against a local copy and a stand-in for `gh`, made the
branch, the commit, the mirror's two files, the pull request and the two
workflow starts, and the next runs repeated none of it.

*Claude's choices*, confirmed by George 2026-11-21:

- **Beszel gets an issue**, not a pull request: since ADR-0174 its pin is in
  `gcarstoiu/gexis-beszel`, which this repository's token cannot write.
- **Shairport Sync and NQPTP get an issue too** (added 2026-11-18, George:
  5.6.3 was out a week unseen): built here from a tag's commit (ADR-0167),
  their pin is a commit with its archive's and source tree's hashes, which
  the workflow does not compute; the issue lists what to move by hand.
- **The workflow puts the two files in the `inputs` mirror** itself, with
  the permission that pushes the branch, so the branch never names a file
  the mirror lacks.
- **CamillaDSP's binary checksum** in `image/verify-image.sh` moves with its
  pin (BUILD-TRAPS), or the release's image check would fail.
- **The tests are started by `workflow_dispatch`** (`tests.yml` gains it);
  the release notes' push later runs them as any push does.
- CamillaDSP's checklist.

**Needs George:** GitHub's *Allow GitHub Actions to create and approve pull
requests* (Settings → Actions → General) is off, so the workflow cannot open
its pull request until it is on. *Switched on by George 2026-11-18; read back
on 2026-11-21.* `main`'s ruleset asks for no approvals, so
the setting adds nothing to what an approval could do there.
