# Finding 105 — An update, and a going back, on the device

**Date:** 2026-09-30
**Question:** Does `gexis-update` (ADR-0105 §4, ADR-0108) move a device from
one release to the next through its channel, and put the release before back
when an install fails?
**Scope:** `sofa-pi` (the second card, restored as `gexis`), flashed with image
833 - the first built from packages - with `gexis-update` and the release key
installed by hand (833 predates the updater). Two releases built locally with
`packaging/release/build.sh` from images 833 and 849, **served from R2D2**
through an SSH tunnel in the layout GitHub serves them (`<tag>/`,
`<tag>-debian/`, `channels/testing`), testing channel only. Nothing on
GitHub. **Not tested:** a release on GitHub (only the one-package
`repo-test-1`, installed on the device and deleted), a reboot-triggering
update (none of these changed a kernel or the boot files), an update started
from the Updates screen, Automatic, stable.

## 833 → 849

The third run did it, in 26 s from start: check (the channel verified by
`gpgv`, 849 waiting), download, a backup (`gexis-gexis-20260930-183402.tgz`),
20 s of silence, install under `systemd-inhibit`, verify, restart.

- **Only what changed moved**: `gexis-player`, `gexis-core`, peppyalsa and the
  engines (their new date-based versions accepted over `0.0.0+git…`). The
  176 MB skins, the UI, the system files and every OS package stayed - the
  tested set was the same.
- alsa-lib stayed at its pin (held); `dpkg --audit` clean; no failed unit; the
  core answered; the daily check timer came on with the update.

The first two runs failed and went back - each the updater's own bug, fixed
and committed (80647a8):
1. apt's error was reported as `systemd-inhibit`'s (*"apt-get failed with exit
   status 100"*); apt's output is now kept and its `E:` lines quoted.
2. The release going in and the one kept for going back shared one apt index;
   fetching the second replaced the first's, and the install found *"Version
   '0.2.1+git849…' for 'gexis-player' was not found"*. Each release now has its
   own view.

The restart list also named `gexis-update-install` (the unit the updater
runs as) and `gexis-park` (whose stop pauses LMS); both are now excluded.

## A broken release, and going back

A release `0.2.1+git850.broken` - 849 with `gexis-player`'s install script
made to fail - on testing, serial 2:

- The install failed at `gexis-player`'s configure; the message quoted dpkg.
- The updater pinned 849, reinstalled it from the cache it had filled before
  installing, and reported *"Back on 0.2.1+git849.dfeaae7"*.
- After: `gexis-player` and `gexis-core` at 849, installed (`ii`); `dpkg
  --audit` clean; no failed unit; the core answered.
- The channel's serial stayed at 1: a failed release is not remembered as
  seen.

## What it bears on

- ADR-0105 §4's set works without A/B for a failed package install.
- **Open for Automatic (13c step 5):** because a failed release's serial is not
  kept, a nightly Automatic run would try the same broken release every night -
  back up, install, go back. It should remember a release that failed and not
  try it again until the channel names another.
- The test harness mistake (a wait that matched *"install failed"* inside the
  going-back line and took its snapshot mid-rollback) is the check's, not the
  updater's; the final state was read after the run ended.
