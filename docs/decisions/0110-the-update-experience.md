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
