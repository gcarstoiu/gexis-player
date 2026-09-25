# ADR-0083 — A backup leaves the device

**Status:** Accepted
**Date:** 2026-09-25
**Relates to:** [ADR-0049](0049-the-pictures-folder-is-a-share.md) (the share
this amends), [ADR-0028](0028-ui-serving-and-command-channel.md) (the LAN is
unauthenticated by decision), [ADR-0035](0035-settings-api.md) /
[ADR-0044](0044-settings-row-vocabulary.md) (action and list rows),
ADR-0022's inventory (`backup`)

## Context

`backup` has been an inventoried, unsurfaced, unwired row since ADR-0022. On
2026-09-25 that cost something real: George reflashed the card, and both
databases — `settings.db` with 41 stored rows including three API keys, and
`enrichment.db` with 3,664 enrichment rows and 7,061 notes — live on it. The
copy that saved them was taken by hand over SSH, and only because the card
turned out not to have been overwritten yet.

George: *"Wire it for both actions — backup and restore."*

**The question this record answers is not how to make an archive. It is where
the archive goes.** A backup written to the device does not survive the event
it exists for: the card being reflashed, or dying.

## Decision

**The archive is written into an SMB share of its own, and restoring reads
from the same share.**

- A new `[backups]` share at `/var/lib/gexis-core/backups`, guest-writable,
  alongside `[pictures]`.
- **`backup`** is an `action` row: pressing it writes
  `gexis-<name>-<timestamp>.tgz` and says which.
- **`restore`** is a `list` row: its items are the archives in that directory,
  newest first. Choosing one restores it, behind a confirm, and **reboots**.

**What is in it:** `settings.db`, `enrichment.db`, `/etc/gexis/core.toml`,
`/etc/gexis/device-name.env` and BlueZ's `/var/lib/bluetooth`. That is
everything the 2026-09-25 hand copy took, because that copy was assembled by
asking what a flash destroys.

## Rationale

### Why a share rather than a download

A browser download reaches the phone and not the panel: Chromium in kiosk mode
has nowhere to put a file and nothing to open it with. That would be a row
that works on one surface and quietly does nothing on the other, which is
[ADR-0020](0020-library-browse-tree.md)'s defect exactly.

A share reaches **every** machine on the network without either surface being
involved, and restoring is dropping a file back. It is also what ADR-0049
already chose the last time the question was *"how does a file get on and off
this appliance"*.

### Amending ADR-0049's "one hole in the box"

ADR-0049's config file says it plainly, and it was right to:

> **One directory and nothing else.** Not the home directory, not
> `/var/lib/gexis-core` — which holds the settings database, the enrichment
> cache and the downloaded wallpaper cache — and not a parent of either. A
> share is a hole in a box and should be the size of what goes through it.

**This is a second hole, and it is the size of what goes through it.** Not
`/var/lib/gexis-core`, which is what that sentence refuses — a sibling
directory that holds nothing but archives somebody asked for. The rule was
never "one share"; it was "no share wider than its purpose".

### The archives contain secrets, and that is not a new exposure

`settings.db` holds the fanart.tv key, the ListenBrainz token and the
Pixabay key; `core.toml` holds `idle_url`, which carries a per-display
identifier. On a guest-writable share, anyone on the LAN can read them.

**They can already.** Checked 2026-09-25: `GET /settings` returns every one of
those values in plaintext to anyone who can reach port 8090. `secret: true` is
a property of the *input field*, not of the payload. ADR-0028 chose an
unauthenticated LAN and ADR-0049 reasoned from it — *"a password here, with
that door open, would be a lock on the window beside it"* — and the same
argument carries here unchanged.

**It is stated rather than assumed**, because a file is easier to copy than an
HTTP endpoint is to notice, and because if ADR-0028 is ever revisited this
share is one of the things that has to be revisited with it.

### Restore reboots

A restore replaces the settings store under a running daemon, the enrichment
cache under a running sweep, and BlueZ's pairings under a running adapter.
Re-reading all of that live is a third mechanism to get wrong, for a button
somebody presses roughly once. **Rebooting is the honest simple answer**, and
the row says so before it acts.

### Rejected: restore from an upload

Considered because it needs no share. Rejected for the same reason as the
download: it is a phone-only affordance on a two-surface device, and it needs
a multipart endpoint and a file picker that the panel cannot show.

### Rejected: writing backups into `[pictures]`

Considered because the share exists. Rejected because that share is *for*
pictures, the idle screen reads everything in it as an image, and an archive
dropped there would be a broken wallpaper.

## Consequences

- **The device gains a second guest-writable share.** Named, scoped and
  stated above.
- **A restore reboots the device**, including when it is playing.
- **An archive is portable between devices**, which is not designed for and
  not prevented: it carries a device name and an LMS address, so restoring one
  device's archive onto another moves both.
- The `backup` row leaves `surfaced: false` behind. `restore` is new, and is
  the second row of the pair rather than a second mechanism.

## What this does not settle

- **Automatic backups.** Everything here is somebody pressing a button.
  ADR-0022's inventory has an `updates` row that is a natural home for a
  scheduled one, and nothing here builds it.
- **Whether a restore should be able to take a subset** — settings without
  the enrichment cache, say. One archive, all of it, until somebody wants
  otherwise.
