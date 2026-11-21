# Finding 145 — The review of everything since 0.10.2, at 1.16.1: 55 defects, all fixed in 1.16.2

**Date:** 2026-11-10 (the review; fixes 2026-11-10 to 12; written up
2026-11-21). **For:** George's request (2026-11-10) for a multi-agent review
of everything since the last one, on a read-only worktree at `v1.16.1`,
nothing fixed before his go. The one before was
[Finding 125](125-the-review-since-0-10-1.md).

## Scope

- **Reviewed:** `v0.10.2` (2026-10-12) to `v1.16.1` (2026-11-10), Finding
  125's range included: about 62,000 lines added by the review's count;
  +60,421 / -5,700 in 320 files by `git diff --shortstat` over `core/src`,
  `core/updater`, `ui/src`, `image`, `packaging` and `.github`.
- **Method:** ten reviewer agents, one per area (the table below). Each read
  its area's code and diffs, ran its tests, and wrote a failing test or
  script per finding, kept outside the repository. Every finding then went
  to a second agent told to disprove it, often by running the code.
  Severities are the checkers'; they changed 6 of the 59 that stood.
- **Fixes:** after George's go (ADR-0178, 2026-11-10), on branches of one or
  two findings, each with a test that failed before the fix; merged one at a
  time into `review-fixes` with the full suite after each, then into `next`
  (`c89f6912`, 2026-11-12). 1.16.2 to Testing (serial 70, 2026-11-12);
  PR #100 merged by George on 2026-11-13.
- **Not covered:** nothing ran on a device or in a real browser: not
  Chromium's kiosk, browsers' local-network prompts, a live Lyrion server, or
  snapserver and CamillaDSP on a player (CamillaDSP only in `--check` mode,
  amd64). Not the Pi 5 or Compute Module paths, nor the plugin repositories'
  own code. The UI has no unit-test setup. Two plugin cases that follow from
  the unauthenticated LAN API (ADR-0022, ADR-0028) were left out on purpose.

## Results

**60 reported, 59 stand** (51 confirmed, 8 in part), 1 disproved. Four were
found twice (http-1 and security-2, multiroom-1 and security-3, security-4
and setup-2, plugins-1 and wiring-3), so **55 distinct**.

| Area | Reported | Confirmed | In part | Disproved |
|---|---|---|---|---|
| Audio stage | 6 | 6 | - | - |
| Multiroom and groups | 8 | 7 | 1 | - |
| Plugins and the catalogue | 5 | 4 | 1 | - |
| HTTP server and API | 5 | 3 | 2 | - |
| The core's wiring and state | 4 | 3 | 1 | - |
| Setup, network and screens | 8 | 8 | - | - |
| Updates and releases | 6 | 5 | 1 | - |
| UI: sound and remote | 3 | 3 | - | - |
| UI: screens and pages | 8 | 6 | 2 | - |
| Security | 7 | 6 | - | 1 |
| **Total** | **60** | **51** | **8** | **1** |

The one disproved (security-7) concerned older commits, which George
decided on 2026-10-19 to leave as they are.

| Severity (55 distinct) | Count | Meaning in the review |
|---|---|---|
| Critical | 2 | a break-in, lost data, or a player that cannot start without reflashing |
| High | 5 | a serious security hole, or a main feature broken for many |
| Medium | 23 | wrong in some situations, recoverable |
| Low | 25 | rare, minor or cosmetic, but real |

**Critical and high:**

| Finding | Fix |
|---|---|
| **Critical** (security-1): a crafted backup, restored over the network, made the root core overwrite a file of its choosing, enough to stop the player starting. | A restore brings back `core.toml`'s values and the device name, never the files (`c10a3049`). |
| **Critical** (wiring-1): a plugin whose settings rows the registry refuses stopped the core starting, on every boot. | Only plugins the registry took are wired (`26b8b4d6`); such a package is refused at upload (ADR-0178 decision 4). |
| **High** (http-1, security-2): no `Origin` or `Host` check, so any web page opened at home could reset, restart or turn up the player. | A browser drives it only from its own pages, named by an address, a name without dots, `localhost` or `.local` (decision 1). |
| **High** (multiroom-1, security-3): a forged group record's host could add lines to the Snapcast client's environment and run a program as `pi`, outside the plugin sandbox. | A member's host must be a name or an address (`bd1f64a6`). |
| **High** (security-4, setup-2): two minutes off its Wi-Fi, a player opened `gexis-setup`, whose password is published, to the whole API. | On a player already set up, the setup network only gives it a network, with a password of its own on the panel where a screen is in use (decision 2). |
| **High** (updates-1, in part): a process running as `pi` could swap a backup upload for a link and get the root core to give it a protected file. | The upload is handled through the one file opened, never by name (`482d3fdc`). |
| **High** (setup-1): a new Wi-Fi given through setup switched a set-up player's plugins off and asked *Make it yours* again. | Such a player is given a network, nothing more (`688428d0`). |

**Medium and low, the notable ones:**

- **Sound:** streams at 32 kHz or below, and 88.2/176.4 kHz on the
  USB-to-optical adapter, were silent with the equaliser or room correction
  on (now converted); the level after a room measurement could come back on
  the wrong scale, up to full scale; Done on *Nothing to correct* locked
  the player for 10 minutes.
- **Groups:** an ended group re-formed when a member that was off came back;
  adding a player to a group playing Lyrion paused everyone.
- **Plugins:** a removed Plexamp or Beszel came back on players carried over
  from before 1.13; the catalogue stopped being read past 16 KB; a package
  could carry one manifest for the check and another for the install; a
  plugin could give CamillaDSP orders (now confined, its control ports
  closed to plugins and, in a follow-up, to other services).
- **Core:** a broken character in a title froze every screen until the next
  track.
- **Screens:** choosing a TV deleted a DSI panel's start-up setting; a Home
  Assistant dashboard link could cover the screen for good (decision 3: such
  links do nothing).
- **Updates:** a GitHub failure while publishing could reset a channel's
  serial to 1 and stop its updates (a serial floor is now kept).

**Leftovers found while fixing:** nine, which George (2026-11-11) asked to
have dealt with. Four fixed with nothing seen changing, among them the music
services under accounts of their own (ADR-0179); four decided by George as
recommended (ADR-0178 decisions 5-8); one judged not a bug.

**Tests and release:** the core suite went from 3,144 passed (48 skipped)
on `next` before the first fix to 3,346 with the 55 fixes and 3,374 at
release. The seven UI-only fixes (ui-screens 1 and 3-8) have no test in the
repository: they were checked in Chromium against a mocked core, from
scratch files. The release build (run 43305560359) passed all 155
`verify-image.sh` checks. Two previews ran on sofapi for George's
regression pass. 1.16.2 also carried a group buffer of a second (ADR-0166,
amended 2026-11-12), not from the review. The fixes reached Stable with
1.16.4 (2026-11-15).

**Not confirmed here:** which checks needing other hardware (a group, the
USB-to-optical adapter, a 32 kHz stream, a DSI panel beside an HDMI panel)
ran on the previews; that each UI check failed before its fix is as recorded
then, not run again.

## What it means

- The second agent mattered: of 60 reports, 1 was disproved, 8 narrowed
  and 6 re-graded.
- It says nothing about what the reviewers could not reach: devices, real
  browsers, a live Lyrion, the plugin repositories.
- Two lessons came from the fixing, not the review: Lessons 94 (a suite
  green only on the machine it was written on) and 95 (a rule kept in a
  comment).
- Seven UI fixes have no test in the repository, so *Tests* would not catch
  them coming undone.
