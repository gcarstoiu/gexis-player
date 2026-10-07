# ADR-0110 — The update experience: release numbers, one modal, playback stops on consent, the panel locked

**Status:** **Accepted** — George, 2026-10-01, after the first update from
GitHub that he ran himself (867 → 871 on `sofa-pi`). His five findings, then
his answers to six questions (each quoted at **Decided**).
**Phase:** 13c ([DEVELOPMENT.md](../DEVELOPMENT.md)).
**Amends:**
- [ADR-0105](0105-updates-over-the-network.md) §4 step 4: *wait until nothing
  is playing*.
- §6: *what the user sees*.
- [ADR-0022](0022-settings.md)'s rows *Release · Check now · Update now*.

**Builds on:** [ADR-0108](0108-how-a-release-is-published-and-found.md) (the
channel names a release; each release carries signed notes).

## Context

The mechanism worked: the update was checked, downloaded, backed up, installed
and verified, and the services restarted. The experience did not.
- **The release names** read `0.2.1+git871.c73ea29`.
- ***Check now* and *Update now*** were separate rows, and they said nothing
  while they worked.
- **Nothing showed progress** or what would come next.
- **The silence wait looked like a bug.** The updater waited for 20 s of
  silence even with nothing playing, because 20 s of silence is what it waits
  for.
- **The panel stayed usable** while its software was being replaced.

## Decided

### 1. A release has a number: `0.2.4`, `0.3.0`

- **The last number** goes up for fixes; **the middle one** for new features.
- **I propose the number with the release's notes, and George approves both**
  together. **Decided** (*"Agreed"*).
- **Testing and Stable share numbers.** A release keeps its number when it is
  promoted.
- **The number is a git tag** `v0.2.4` on the commit the release is built
  from. `gexis-player`'s version is then exactly `0.2.4`.
- **Ordering is preserved.** Debian orders `0.2.1+git871…` before `0.2.4`, so
  every device updates.
- **The other packages are unaffected.** They keep the versions their own
  inputs give.
- **Where the long form shows:**
  - The long form (`git871…`) stays only on the *Image build* row, for
    support.
  - Everywhere else the user sees the number.
  - A device on a build without a number shows the part before `+`.

### 2. The Release tile holds the buttons

- ***Check now* and *Update now* stop being rows.** The *Release* row becomes
  a tile: the installed number, its state, and one button.
- **Up to date or never checked:** the button is *Check for updates*.
- **An update is waiting** (found by the nightly check in Manual mode):
  - the tile reads *0.2.5 available*;
  - its button is *Update…*;
  - it opens the same modal at the *available* step. **Decided** (*"Yes -
    agree"*).

### 3. One modal, from the check to the end

1. ***Checking…*** while the device asks its channel.
2. **The answer:**
   - ***Up to date (0.2.4)***, which closes; or
   - ***0.2.5 is available***, with its notes (*What's new*) and an
     **Update** button.
3. **If anything is playing,** a warning before anything starts: *Playback
   stops during the update.* **Continue** or **Cancel**. Cancel is the last
   way out (§5).
4. **The steps, all listed from the start, each marked as it is done:**
   1. Download, with **a progress bar**;
   2. Back up;
   3. Stop playback;
   4. Install;
   5. Restart the player;
   6. Check.
5. ***Updated to 0.2.5***, or ***Did not update - back on 0.2.4***, with the
   reason.

The modal is the same on the phone and in the panel's Settings.
- **Closing it on the phone** leaves the update running. Settings shows it
  again when reopened.
- **The phone loses its connection** while the player restarts, and the modal
  says so.

### 4. Playback stops on consent, not by waiting

- **An update the user starts does not wait for silence.**
  - With something playing, the warning in §3 asks first.
  - Continue pauses or disconnects every source, and the update proceeds at
    once.
- **Afterwards nothing resumes:** everything is paused or disconnected.
  **Decided** (*"No - everything is paused or disconnected"*).
- **At night (Automatic), nobody can be asked.**
  - The check runs between **03:00 and 04:00**.
  - **It starts only if nothing is playing.** If something is, it does not
    wait: it tries again the next night. **Decided** (*"Agreed - make it at
    night somewhere around 3 or 4"*).

### 5. Started is finished

- **Once the user presses Update (or Continue), there is no cancel.**
  **Decided** (*"Once upgrade is triggered by the user, it needs to finish.
  No cancelation as a decission was made."*).
- **Finishing includes going back.** If the install or its check fails, the
  device returns to the release it had (ADR-0105 §4 step 6). The modal and
  the panel end on that outcome.

### 6. The panel is locked while it updates

From the moment the update starts until it has finished or gone back, the
panel shows one full-screen message and takes no input:
- *Updating to 0.2.5*;
- the steps, as in §3, with the download's bar;
- *Don't switch off.*

The core restarts in the middle of it. While it reconnects, the panel keeps
the message, then reloads on the new version: no normal screen shows in
between. A reboot, when one is needed, shows *Restarting the device* until
the boot splash.

### 7. Who designs it

**Built from our design system** (tokens, the existing sheet, row and button
styles), not sent to Claude Design. **Decided** (*"You build it based on our
design system"*).

### §2 amended, 2026-10-01 — Release and Software update are two rows

George, after seeing the tile: *"the release field becomes read-only and it
only shows the current release running on the panel; the check for updates
button is added to another tile"*. He confirmed it, the name and the
channel shown on Release together (*"i confirm the 4 entries from above"*).
- **Release** is read-only: the number this device runs and the channel it
  follows, `0.3.1 · Testing`.
- **Software update** is the tile:
  - what the updater last found and when (*Up to date · checked today
    03:12*, or *0.3.2 available*);
  - the waiting release's notes;
  - the button.

**Testing and Stable share one number** (George asked, 2026-10-01). The
build tested on Testing is the one Stable gets, so a separate *beta* number
would need a second build. The channel on Release, and GitHub's *Pre-release*
mark, say which one a release is on.

### Restarts are not in the notes (2026-10-01)

0.3.2's notes said *"No reboot"*, and `sofa-pi` rebooted. Its first
`gexis-system` update put back a boot option that Raspberry Pi's first boot
strips from every device: every `systemd.*` option in `cmdline.txt`.
- **Whether an update restarts the device depends on the device,** so the
  notes cannot promise it either way. **Decided (George: "Let's go for A"):**
  the notes leave it out.
- **The modal says it before the update starts:** *"Installing stops
  playback. The player restarts, and the device too if the system needs
  it."*
- **`publish.sh` refuses notes that say it.**
- **The option itself moved** to `/etc/systemd/system.conf.d/`
  (`ShowStatus=no`), where nothing strips it and no reboot is needed.

### The end is the steps, all done, until dismissed (2026-10-05)

George, after updating gexis to 0.9.1: *"the user needs to see that all
checkmarks got green. I would rather keep the user in the installation
screen which he would need to dismiss, rather than showing the changelog
which he has seen already at the beginning of the process."* So a finished
update - on the panel's lock and in the phone's modal - shows **Updated to
x.y.z with the six steps ticked**, and a **Done** button; the notes are not
shown again. The panel's lock waits for Done; a panel nobody watches lets
go after ten minutes, so it does not stay locked for the night.

And *"More granularity is needed"*: the install step's bar stood at 0 % for
35 s and jumped to 42 %. It counted dpkg's actions, and a release changes
four packages, one of them about 70 MB. The bar now weighs each package by
its size and moves on with the time a package takes, never past the end of
the action dpkg is on.

The notes themselves were cut at 1,200 characters by the updater - 0.9.0's
and 0.9.1's mid-word on the phone - and are kept whole since.

## What changes underneath

- **The updater:**
  - **Reports progress.** `status.json` gains `steps` (each pending, active,
    done or failed) and the download's `progress` (0-1), read from apt's
    `Status-Fd`.
  - **Takes `--now`** for an update the user started: no silence wait. The
    core has already stopped playback.
  - **Skips the night run** when anything is playing, instead of waiting.
- **The timer** runs at 03:00 with up to an hour's random delay
  (`RandomizedDelaySec=1h`, 90 min before).
- **The core:**
  - **Publishes `update`** in `/state` (state, step, progress, release)
    while an install runs. It reads `status.json` when it starts, so the
    message survives its own restart.
  - **Gains `POST /updates/install`**, which pauses or disconnects every
    source, then starts the install.
- **Settings:** the `update_check` and `update_install` rows go. Their actions
  remain as routes the tile and the modal use. A settings migration removes
  the keys (ADR-0105 §5).
- **Publishing:** `publish.sh` refuses a release whose `gexis-player` version
  is not a plain `x.y.z`.

## Not in this record

- Notifications outside Settings (*an update is waiting* on the panel's home
  screen). ADR-0105 §6 says the panel and phone say so. That is not built yet,
  and this record does not change it.
- A/B partitions (ADR-0105 §4: decided against for now).

## Amended 2026-10-06: the install bar's dead start

George, on 0.9.1 -> 0.9.2: *"it still stayed quite a while on 0 and then
when it reached around 70%, the text under the checkmarks changed to
Restarting player and all the checkboxes were green."* From gexis's
`dpkg.log` and the updater's journal: dpkg began 16 s after the install
step did, because apt first ran `apt-listchanges` over every package (8.8 s
for gexis-core's 75 MB alone; 0.27 s with no frontend). The updater now runs
apt with `APT_LISTCHANGES_FRONTEND=none`. DpkgShare's rate is re-measured
from the same log (gexis-core unpacked in 13 s, configured in 6: 3.5 MB/s,
not 1.5), and the bar is shown full for a second before the step is
ticked. Like every updater change, it applies from the update after the
one that delivers it.

## Amended 2026-10-07: the notes of every release being skipped

George: *"the update screen should show all until the current one."* A
device several releases behind went straight to the newest (ADR-0105) and
was shown only that release's notes; what the skipped ones changed was in
*Change logs* only after installing.

1. **Each release publishes its history beside its notes:** `r<tag>/history`,
   every release's notes from that tag's `release_notes.json` (ADR-0116),
   clearsigned by the release key like the notes (ADR-0108).
2. **The updater reads the waiting release's history** and keeps every
   release newer than the installed one, up to the waiting one, newest
   first, each with its number, date and notes. A history that is missing
   or does not verify falls back to the waiting release's notes alone, as
   before. Kept whole up to 40,000 characters (about twenty releases); past
   that, the oldest are left out and a line says how many, with *Change logs*
   and GitHub named for them.
3. **Shown as one block per release** in the modal and on the Software update
   tile: the release's number and date as its heading, its notes under it.
   One release waiting reads as it does today.
4. Like every updater change, **it applies from the update after the one that
   delivers it**: the updater that reads the notes is the installed one.

## Amended 2026-10-07 (brought into line with the code)

- **"What changes underneath", `--now`:** the updater has no `--now` flag.
  `gexis-update install` never waits for silence; only `gexis-update
  scheduled`, the night run, looks at whether anything is playing
  (`core/updater/gexis-update`).
- **"What changes underneath", `POST /updates/install`:** there is no such
  route. The modal's button runs the `update_install` settings action, which
  starts `gexis-update-install.service` (`core/src/gexis_core/__main__.py`).
  The core does not stop playback first: the updater stops every source
  itself at its *Stop playback* step (`stop_playback`, the core's
  `/renderers/park?stop=all`), after the download and the backup, so music
  plays on through those two.
- **"What changes underneath", Settings:** the `update_check` and
  `update_install` rows were not removed. They remain in the registry as
  unsurfaced actions (`"surfaced": false`), which the modal runs; no
  migration removed their keys.
- **§3 step 2, *Up to date (0.2.4)*:** the answer reads *Up to date*, with
  the release named in its text ("This player has 0.2.4, the newest
  release."), and it waits for **OK** rather than closing
  (`ui/src/screens/UpdateModal.svelte`).
- **"The end is the steps" (2026-10-05), notes "kept whole":** each
  release's notes are kept up to 8,000 characters (`NOTES_MAX`), far above
  any so far; the history as a whole up to 40,000.

**Not built (2026-10-07) - to be built before the first public release** (George, 2026-10-07: *"Build them."*):

- **§5's "returns to the release it had" holds only when the install or its
  `verify` fails.** A core that does not answer after the restart is
  reported as failed and the device stays on the new release; nothing goes
  back (ADR-0105, amended the same day).
- **§6's *Restarting the device* is likely not what a reboot shows.**
  Inferred from the code, not seen on a device: the updater ticks the
  restart and check steps and reports *done* before calling the reboot, so
  the panel's lock shows *Restarting the device* only for the moment the
  restart step is active, then the finished screen (*Updated to …*, Done)
  until the boot (`ui/src/screens/UpdateScreen.svelte`,
  `core/updater/gexis-update`).
