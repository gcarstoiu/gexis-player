# ADR-0116 — Change logs in Settings

**Status:** **Accepted** — George, 2026-10-03.
**Builds on:** [ADR-0110](0110-the-update-experience.md) (the Software update
tile and its notes), [ADR-0108](0108-how-a-release-is-published-and-found.md) (releases
and their signed notes).

## Context

The Software update tile shows the waiting release's notes, and went on
showing them after the update was installed. George, 2026-10-03: *"It's good
to show the one for an update coming the way we do. Once the update is done
though there is no point in [showing] it there anymore. What I suggest is to
have another tile in settings called change logs which displays the last 10.
If user wants more he is pointed to the git page where we have them all."*

Each release's notes are approved by George, signed, and published with the
release (`notes`, a clearsigned file, and the page's text). Nothing on the
player kept them once the next update was found.

## Decided (George, 2026-10-03)

1. **The Software update tile shows notes only while an update waits.** Once
   it is installed, the tile says it is up to date and no more.
2. **A Change logs row** under Updates opens a page with the notes of the
   last 10 releases, newest first.
3. **Older ones are on GitHub**, and the page says where.

## Technical

4. **The notes live in the repository**, in
   `core/src/gexis_core/release_notes.json` (version → date and notes), which
   the player ships. A release's notes are added there, as approved, before
   it is tagged; `publish.sh` takes them from there and refuses a release
   that has none. One text: what the player shows, what GitHub shows and
   what is signed cannot drift apart.
5. **Backfilled from what was published**: the twelve player releases from
   0.3.0 to 0.8.3, each from its signed `notes` file, every signature checked
   against the release key (2026-10-03, all good), dated by the day the
   release was published. Older notes read as they were written - prose
   before 0.4.0's sections - because they are the record.
6. **The page is the Legal and Credits page** (a `document` row), its
   sections a release each, drawn with the same notes component as the
   update. Read from the player's own file: it works offline, and shows the
   releases up to the one installed.

### Settled the same day (George)

7. **Older ones are in `CHANGELOG.md`** (*"B"*, of two: A was GitHub's
   releases page, where each player release sits among three or four
   *Part* entries - the shared apt parts, ADR-0108 - that its search does
   not filter out, tried 2026-10-03). It is generated from the same file,
   checked current by a test, and the page points at it on `main`. **Each
   release is merged into `main`** so that page is current.
