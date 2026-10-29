# ADR-0168 — A plugin catalogue

**Status:** **Proposed** 2026-10-29, for Phase 24 (`ph-plugin-catalogue`),
brought forward that day before room correction (George). What a user and
an author see and may do is George's to decide (*Owed*, seven questions);
the technical shape is Claude's proposal. Builds on
[ADR-0106](0106-plugins-you-install-and-update.md) (uploaded plugins: the
checks, the folder, the sandbox, the notice),
[ADR-0108](0108-how-a-release-is-published-and-found.md) (a signed file a
device trusts, with a serial that only increases) and
[ADR-0086](0086-a-plugin-declares-itself-in-a-manifest.md) (the manifest).
Once accepted it amends ADR-0106's *Not in this record*.

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
3. **Then read by a person** (Owed 2): the source at the version's tag
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
7. **Install** shows a notice (Owed 6), downloads with the download row's
   progress and Retry, checks the size and sha256, and hands the archive to
   `uploads.install`: the same checks, folder and sandbox as an upload. The
   plugin's row says *from the catalogue* instead of *uploaded*; it arrives
   off, and installing restarts the core, as an upload does (ADR-0106,
   decided).
8. **Updates**: a newer listed version shows on the plugin's row (Owed 4);
   the previous version stays for one step back. Only listed versions are
   offered, so a player never installs bytes nobody read (if Owed 3 is
   *every version*).
9. **Withdrawn and blocked** (Owed 5): the catalogue can withdraw a version
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

## Owed (George)

1. **Other authors' plugins listed.** The catalogue lists plugins by other
   authors once they pass the checks and a person's reading; listed means
   checked, not made or vouched for. This lifts ADR-0106's "we do not list
   other people's plugins". *Recommended: yes - it is what the phase is
   for.*
2. **Who merges a listing.** *Recommended: George, on a review note Claude
   writes on each pull request*, as with release PRs. Or Claude merges once
   the checks pass and the reading finds nothing, and tells George.
3. **Every version read, or the plugin once.** *Recommended: every version*:
   a player installs only listed versions, pinned by checksum, as ADR-0106
   decided for ours. Or Lyrion's way: read once when listed, then each
   version its author publishes reaches users unread - quicker for authors,
   and a plugin can change after it was read.
4. **Updates: a tap, or automatic.** *Recommended: a tap on the plugin's row
   in this phase*; automatic, following *Updates: Automatic*, later if
   wanted.
5. **A withdrawn plugin on a player that has it.** *Recommended: the two
   levels in 9* - withdrawn marks it, blocked also switches it off.
6. **The notice before installing from the catalogue.** The upload's notice
   is George's own wording. *Proposed:* "This plugin is not part of Gexis
   Player. It was checked before it was listed, and is installed and run at
   your own risk and responsibility."
7. **Where, and how it looks.** *Recommended: on the panel and the bars as
   well as the phone* (installing needs no file picker), *built from the
   Plugins page's own rows* - a row per plugin, the download row, the switch
   - without a design round; or a brief for Claude Design first.

## Settings (ADR-0022), to propose for the inventory

Not appended until George confirms:
- **[N] More plugins shown** (`plugins.catalogue`, on): off hides the
  catalogue for an owner who wants only what ships.
- **[?] Updates for catalogue plugins** (Manual / Automatic): only if Owed 4
  chooses automatic.

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
