# ADR-0168 — A plugin catalogue

**Status:** **Accepted** 2026-10-29 (George: the seven questions as
recommended, and no setting). Phase 24 (`ph-plugin-catalogue`), brought
forward that day before room correction (George). What a user and an author
see and may do is George's (*Decided*); the technical shape is Claude's
proposal, confirmed or changed by the phase's measurements. Builds on
[ADR-0106](0106-plugins-you-install-and-update.md) (uploaded plugins: the
checks, the folder, the sandbox, the notice),
[ADR-0108](0108-how-a-release-is-published-and-found.md) (a signed file a
device trusts, with a serial that only increases) and
[ADR-0086](0086-a-plugin-declares-itself-in-a-manifest.md) (the manifest).
It amends ADR-0106's *Not in this record*.

## Context

- **A plugin reaches a player in two ways today** (ADR-0106): ours as
  packages in each release; anyone else's as a `.tar.gz` that a user uploads
  from a phone or computer, checked by `uploads.check` and run under the
  sandbox's unit. An author can reach users only by handing them the file.
  ADR-0106 left a catalogue out: we do not list or vouch for other people's
  plugins.
- **What the player has for this already**: the checks an upload passes
  (manifest, id, paths, sizes, aarch64; `core/src/gexis_core/uploads.py`),
  the install with one step back, the sandbox units, the download row's
  progress and Retry, and gpgv with a signed file whose serial only
  increases (the channel files).
- **Two catalogues others run**, read 2026-10-29:
  - *Lyrion's plugin repository*: each entry has its version, download URL,
    checksum (`sha`) and the server versions it suits (`minTarget`,
    `maxTarget`). The central `extensions.xml` is rebuilt every few hours
    from each author's own repository file, listed once in `include.json`:
    a new version reaches users when its author publishes it, without
    anyone reading that version
    ([LMS-Community/lms-plugin-repository](https://github.com/LMS-Community/lms-plugin-repository)).
  - *HACS* (Home Assistant): a repository enters the default list by a pull
    request to `hacs/default`, merged only once automated checks pass (a
    full GitHub release, a licence GitHub recognises, HACS's own validation)
    ([hacs.xyz](https://hacs.xyz/docs/publish/include/)).
- **A release asset on GitHub can be deleted and uploaded again under the
  same name**, so a URL alone does not say which bytes were read; a checksum
  does.

## Proposed (Claude)

### The catalogue is a repository on GitHub

1. **`gcarstoiu/gexis-plugins`, public**, apart from the player's
   repository so that authors' pull requests never touch the player's. One
   file per plugin, `plugins/<id>.json`, written by its author: id, name,
   summary, kind, author, source (a public repository), licence (SPDX), and
   its versions - each with an https download URL (a release asset of the
   source repository), the archive's sha256 and size, the contract version
   and the lowest player release it needs.
2. **Listed by a pull request, checked before anyone reads it** (GitHub
   Actions): the file's schema; the archive at the URL matches its sha256
   and size; the player's own `uploads.check` accepts it - run from the
   player's code at a pinned commit, so that a listed plugin is one an
   upload would accept; the id is free and not one of ours; a listed
   version is only ever added, never changed.
3. **Then read by a person** (decision 2): the source at the version's tag
   against its summary, what it asks of the sandbox, and a name that does
   not pass for ours or for someone else's product.
4. **Published signed.** After a merge, `publish.sh`, run locally as a
   release is, writes `catalogue.json` from the plugin files with a serial
   that only increases, signs it with **the catalogue key**, and uploads it
   with its signature to the repository's permanent release `index`. The
   catalogue key is its own, not the release key: it signs a list of other
   people's plugins, and a leak of it could not sign an update of the
   player.

### On the player

5. **The core reads the catalogue** from that fixed URL with the nightly
   update check and when *More plugins* opens; verifies it with gpgv against
   the catalogue key the core package carries; refuses a lower serial; and
   keeps the last good one. Offline, it shows the last one it had, with its
   date. GitHub sees the player's address, as for the update check; nothing
   else is sent.
6. **Settings → Plugins → More plugins** lists what suits this player - its
   contract, its release, aarch64 - each with its mark, name, summary,
   author, licence, source and the manifest's tag if it has one.
7. **Install** shows a notice (decision 6), downloads with the download row's
   progress and Retry, checks the size and sha256, and hands the archive to
   `uploads.install`: the same checks, folder and sandbox as an upload. The
   plugin's row says *from the catalogue* instead of *uploaded*; it arrives
   off, and installing restarts the core, as an upload does (ADR-0106,
   decided).
8. **Updates**: a newer listed version shows on the plugin's row (decision 4);
   the previous version stays for one step back. Only listed versions are
   offered, so a player never installs bytes nobody read (decision 3).
9. **Withdrawn and blocked** (decision 5): the catalogue can withdraw a version
   or a plugin, with a reason. *Withdrawn*: not offered, and marked on the
   row of a player that has it. *Blocked*: also switched off on every player
   that has it, with the reason - for a plugin found to do harm.
10. **Backups** as ADR-0106 decided for an upload (settings and data, not
    the package); after a restore, a plugin from the catalogue is installed
    from it again - its version if still listed, else the newest - instead
    of *needs uploading again*.
11. **Ours stay with the release** (ADR-0106 decision 4, unchanged):
    Plexamp's adapter, AirPlay, Beszel and the Lyrion server are not in the
    catalogue.

### The first listing

12. **The sample plugins** (`tools/sample-plugin`, `tools/sample-renderer`)
    in a repository of their own, listed first and taken through the whole
    path: pull request, checks, reading, signing, install from the panel and
    from the phone, an update to a second version, withdrawn, blocked, and a
    restore.

## Decided (George, 2026-10-29)

Asked one at a time; each answered as Claude recommended.

1. **Other authors' plugins are listed** once they pass the checks and a
   person's reading. Listed means checked, not made or vouched for by Gexis
   Player. This lifts ADR-0106's "we do not list other people's plugins".
2. **George merges a listing**, on a review note Claude writes on each pull
   request, as with release PRs.
3. **Every version is read**: each is its own pull request, pinned by its
   checksum, and a player installs only listed versions. Not Lyrion's way
   (read once, later versions unread).
4. **An update is a tap on the plugin's row**; nothing updates by itself in
   this phase.
5. **Two levels when a plugin is pulled**: *withdrawn* is no longer offered
   and is marked on the row of a player that has it, which keeps running it;
   *blocked*, for a plugin found to do harm, is also switched off on every
   player that has it, with the reason.
6. **The notice before installing**: "This plugin is not part of Gexis
   Player. It was checked before it was listed, and is installed and run at
   your own risk and responsibility."
7. **On the phone, the panel and the bars, built from the Plugins page's own
   rows** (a row per plugin, the download row, the switch), without a design
   round.

## Built: the repository (plan step 1, 2026-10-29)

`gcarstoiu/gexis-plugins` is public (George, the same day), under
GPL-3.0-or-later as the player (George). It holds `tools/catalogue.py` (an
entry's form, the index), `tools/check.py` (the pull request's check: each
new version downloaded, its size and sha256 compared, the player's own
`uploads.check` run on it from the commit in `tools/player-ref`),
`tools/publish.sh` (signed, read back; `--dry-run` signs into `out/` only)
and the authors' guide as its README. The check runs on
`pull_request_target`, so the tools are main's and the pull request's files
are read as data only. Shown: the tools' 19 tests against the player's
upload check, on R2D2 and on GitHub; a dry run signed and verified with a
throwaway key, and a changed file failed its signature. **The catalogue key
waits for George** (asked the same day: not yet); until it exists nothing
is published. Not yet run: the check on a real pull request (plan step 4).

## Built: the player's side (plan step 2, 2026-10-29)

On `ph-plugin-catalogue`: `core/src/gexis_core/plugin_catalogue.py` and
`GET /plugins/catalogue` (`?refresh=1`), `POST /plugins/catalogue/install`.
Proposals 5-10 as written, with these settled in building:
- **A version's age is its place in the list**, newest last; the
  catalogue's check refuses a new version put before a listed one.
- **A plugin uploaded here under a listed id** shows as *uploaded* and is
  not replaced from the catalogue; an upload over a catalogue plugin makes
  it an upload.
- **Blocked during a run**: switched off at once, and the core restarted
  once so the row says why; its switch refuses to turn it on.
- **After a restore**, one plugin a start is installed again, since each
  install restarts the core.
- **The key**: the core package carries `gexis-catalogue.gpg` only once
  `packaging/keys/gexis-catalogue.asc` exists; without it there is no
  catalogue on the player.
Shown: 19 tests (a real key, gpgv as on the device; the network faked),
two of them seen to fail with the serial check or the checksum check
removed; the suite, 2,837 passed. **Not yet run on a player**, nor the
start-up wiring in `__main__.py` (the blocked switch-off before uploaded
plugins start, the refused switch), which no unit test reaches.

## Settings (ADR-0022)

None. A switch to hide *More plugins* was offered and declined (George,
2026-10-29): it is always there. With decision 4, no update setting either.

## Measured before it is called done

- Reading and verifying the catalogue on a Pi 4 - time and memory - with
  twenty synthetic entries.
- The sample listed end to end, as in 12, on a test player.
- An archive that differs from its sha256, a catalogue with a lower serial,
  one with a bad signature: each refused, nothing installed.

## Unverified

- That `uploads.check` runs in GitHub Actions from the player's code alone:
  it imports `gexis_core.plugins` and the standard library (read from the
  source, not tried).

## Not decided here

- Paid plugins, ratings, download counts, comments: none planned.
- Our own plugins updated through the catalogue, apart from releases.
- Authors' own signatures (ADR-0106: a signature says who built it; the
  checksum pins what was read).
- Architectures other than aarch64.
