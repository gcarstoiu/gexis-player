# ADR-0182 — Upstream releases checked daily, and a patch release for one part

**Status:** **Accepted** 2026-11-15 (George: options 1 and 2 together, after
go-librespot's fix for the Android app sat unreleased; the fourth, upstream
builds as a standing rule, not chosen). Items marked *Claude's choice* are
for George to confirm.
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
