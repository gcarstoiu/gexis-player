# Finding 123 — An update cut short by pulling the power, on the bar

**Date:** 2026-10-13. **Run by:** George (g34: *"Just did the power cut
test. Check shelvespi"*).

## Scope

- **Device:** the bar (ShelvesPi, Pi 4), gexis-player 0.10.2+git65, its
  updater byte-identical to the one in v0.12.0
  (sha256 `7eb60abe…`). Update channel switched to Testing for the test.
- **What George did:** *Update now* to 0.12.0 (Testing, serial 38), and pulled
  the power once it was installing.
- **Read afterwards:** dpkg's state, the updater's files in
  `/var/lib/gexis/updates`, this boot's journal (the bar keeps none across
  boots), the apt log.
- **Not tested:** a second power cut with the fixed updater installed - it
  ships in the next release, and only an update from it can be cut again.
  Power cuts at other moments (download, backup, restart).

## What the power cut left

- dpkg: `gexis-core` half installed (`reinstreq`), `gexis-player` and
  `gexis-system` unpacked but not configured, triggers pending; dpkg's
  journal not empty.
- **`pending-check.json` - the note the updater writes before dpkg starts,
  so the boot knows an install was running - was an empty file**, dated
  13:50:08, before the cut. It was written beside and renamed, but never
  synced: the rename reached the card and the contents did not.
- `apt.log` carried a block of null bytes where the install's output had been.

## What the updater did with it

1. **At boot, `postboot` read the empty note, failed to parse it, and did
   nothing** - no log line.
2. **A check four minutes later said "0.12.0 is testing's release"**:
   `check` compares `gexis-player`'s version, and dpkg already listed the
   unpacked 0.12.0. Nothing would have repaired the bar; the next update
   would never be offered.

## The fix, and the bar recovered with it

On `phase-13d` after 0.12.0 (the updater, `core/updater/gexis-update`):

- **The note is synced** - the file, then its folder - before dpkg starts.
- **An install dpkg says was cut short is finished with no note**: at boot
  when the note is missing or unreadable, and at the start of every check
  (not while dpkg's lock is held). The release is the `gexis-player` dpkg
  unpacked; it is finished from that release's own repositories, the rest of
  the release installed, checked, and the device restarted for the boot to
  check it.
- **Only the packages dpkg says must be installed again are reinstalled**,
  then dpkg configures the rest. The first run on the bar asked apt to
  reinstall all three listed packages and apt stopped with "Internal Error,
  No file name for gexis-system:arm64"; `gexis-player` and `gexis-system`
  only waited for `gexis-core`.
- **The rest of the release is installed after the repair.** The first
  successful repair left four OS packages the install had not reached at
  their old versions (`ntfs-3g`, `libntfs-3g89t64`, `librsvg2-common`,
  `librsvg2-2`), which every later check would have called current.

The fixed updater, run on the bar from a copy (the installed one untouched)
with `check`:

| Run | Result |
|---|---|
| 1 (reinstall everything listed) | dpkg finished what it could; apt's internal error; stopped with the cut-short message, no restart |
| 2 (reinstall only `gexis-core`) | dpkg clean, 0.12.0 verified, note written, restart; the boot's `postboot`: "done: 0.12.0 installed (reboot)" |
| 3 (the release's remaining steps) | the four OS packages upgraded; a dry run of the release's upgrade: 0 to change; `dpkg --audit` clean |

After it: gexis-player, gexis-core 0.12.0; the core, the meter service, the
panel and Squeezelite active. Tests: 2,352 passed.

## Addendum 2026-10-14: the second power cut, with the fixed updater installed

The bar on 0.13.0 (the fixed updater, installed by an ordinary update the
evening before); George started *Update now* to 0.14.0 at 08:14 and pulled
the power once it was installing.

- **The cut came mid-install:** at the next start dpkg was interrupted with
  gexis-core, gexis-player, gexis-system and gexis-ui unfinished.
- **The note survived** (synced to the card): `postboot` read it at 08:15:29
  and logged *"finishing the install that was cut short"*.
- **Finished by itself, nobody touching it:** `dpkg --configure -a` (exit 1,
  gexis-core half installed), only gexis-core reinstalled, `dpkg --configure
  -a` clean, the release's `dist-upgrade` and `install gexis-player=0.14.0`,
  verified, the core answering - *"done: 0.14.0 installed"* at 08:19:07, one
  start, about four minutes.
- **The whole release:** a dry run of 0.14.0's upgrade afterwards: 0 to
  change; `dpkg --audit` clean; the core, the panel, the meters and
  Squeezelite active.

**Not tested:** a cut at other moments (the download, the backup, the
restart); the case with no note at all (the updater's own fallback,
`finish_cut_short` at a check, proved only on the bar's state of 2026-10-13
by hand). The bar still reports undervoltage (`0x50005`, the extension cord).
