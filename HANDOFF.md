# Handoff

Last updated: 2026-10-22 (on R2D2).

## Start here

Branches (renamed 2026-10-18, George: Phase 13d was over and the names read
as open phases): **`docs`** in the main checkout holds the documents and
shared work (was `phase-13b`); **`next`** in `~/projects/gexis-player-next` is
the release branch, what the next release is built from (was `phase-13d`),
and `docs` is merged into it after each docs change. A phase's work has its
own branch (`ph-first-use`) and is merged into `next` once George's tests
pass. A release is built
from a worktree made at its tag, then removed.

**GitHub checks every push** (2026-10-18): `.github/workflows/tests.yml` runs
*Core tests* (Python 3.13) and *UI build*; `main`'s ruleset requires both and
a pull request; merged branches are deleted by GitHub; Dependabot alerts are
on (security alerts only, no version-bump PRs). On GitHub the visualiser's
tests run too (pygame's fonts work on 3.13): 2546 pass, against 2500 here.
*Releases built on GitHub* is a Should on the Roadmap (signing stays local;
a trial build first, for the disk).

**The public roadmap is the GitHub wiki's *Roadmap* page** (2026-10-18; its own
repository, `gexis-player.wiki.git`): Now, Next (the next two phases), Later,
and the ideas as Must / Should / Could. It follows `docs/DEVELOPMENT.md`'s
phases; change it when a phase opens, closes or moves, and show George first. History: `docs/HANDOFF-ARCHIVE.md`
(search it; never read it whole).

**Current release: 1.4.0, on Testing** (2026-10-22; Testing serial 54, its
signature good from the release key, read back with `gh release download
channels`; Stable unchanged at serial 8, 1.3.1). Tag `v1.4.0` on the
release-notes commit `527c3bd0`; `next` and `release-1.4.0` pushed there.
Image `image/deploy/2026-10-22-gexis-player-v1.4.0.img` (`verify-image.sh`
123/123 from the release worktree, 978 skins clean); parts
`ours-488ab973183a`, `skins-67e037cab00f`, `rpi-222df5468eaa`,
`debian-ddaba64c92a5`; build output in `~/.local/share/gexis-release-out/r1.4.0`.
Packages: gexis-core and gexis-player `1.4.0`, gexis-system
`1.3.1+git60.4f8ea32`, gexis-ui `1.3.1+git64.be7558c`; the skin packs are
1.3.0's published files (`1.2.0+git33.96b8a42`, copied, not rebuilt - a
rebuilt archive differs in bytes from the published one with the same files).
What it carries: Phase 18's Home Assistant dashboard (ADR-0156) with the
phone's touchpad and typing over it (ADR-0157), the phone's mini player
redesigned, a track's own artist on album pages, the visualiser cheaper on
turntables and tapes (Finding 134), and the fixes - the visualiser surviving
a screen change, no black frame on opening, over the dashboard when asked
for, a show refused in standby starting nothing, meters after software
volume (Finding 135), the spectrum box after a skin change (Finding 136),
dimmed bar controls, rows without a flash, the mini player on the phone's
keyboard, no password-save offer. `CHANGELOG.md` on `next` has the notes as
George approved them. CI: *Tests* passed on `release-1.4.0`, `next` and the
tag; the tag's *API description* run was still in progress at hand-off.

**PR #81 (`release-1.4.0` → `main`) waits for George's merge** - never
Claude's. Once he has merged it (`docs/tech/updates-and-releases.md` §4,
step 5, then `docs/ROUTINE-CLEANUP.md`):
- merge `origin/main` into `docs` and into `next`, push both;
- delete the merged branches on GitHub and locally: `release-1.4.0`,
  `album-track-artist`, `bar-controls-dimmed`, `meter-before-softvol`,
  `peppy-cheaper`, `peppy-quiet-repaint`, `peppy-refused-no-restart`,
  `peppy-survive-resize`, `ph-ha-dashboard`, `phone-sheet`, `preview-1021`,
  `spectrum-box-follows`, `tap-no-flash` (all are in `next`; check with
  `git merge-base --is-ancestor <b> origin/main` first);
- remove their worktrees (`~/projects/gexis-player-{artist,barctl,cheaper,
  dash,meter,preview,refused,repaint,resize,sheet,spectrum,tap}`) and the
  release worktree `~/projects/gexis-player-r140`;
- the routine clean-up; tick `rel-1-4-0` on the to-do list; mark Phase 18
  in the phases doc and the wiki Roadmap as George decides (show him first).
- Promotion to Stable is George's call, later; the README's "current
  release" line changes only then.

**Both players run the preview `preview-1021`** (since 2026-10-22 13:10):
gexis-ui and gexis-player `1.3.1+git64`, gexis-system `git60`, gexis-core
`git62` - the same code as 1.4.0 except core's version string. They move to
1.4.0 by the update.

**Deferred until a bug report** (George, 2026-10-21; from 1.3.1): the HMTECH 10.1" came up at 800x480 on the first start
after the boot that switched to it (Chromium stored 1004x580 in a 1024x600
work area: not full-screen), then full-screen on two restarts in a row. A
first start after a screen change may still miss full-screen. The 10.1" was
checked by its EDID in the tests, not again on the device under the new
standby.

**Release build output lives in `~/.local/share/gexis-release-out`**: in each
release worktree, `ln -s` it to `packaging/release/out` before `build.sh`
(excluded in `.git/info/exclude`). `reuse.py` reuses a published file only
against a local copy, so losing that folder means re-uploading every OS file.

**Not an issue** (George, 2026-10-20): Squeezelite joining whichever Lyrion
server answers first after a restart (Finding 130 point 6). GitHub reported
6 Dependabot alerts on `main` (all `vite`, the UI's build tool, not on the
player), raised 20-21 Oct.

**Open:**
- **The visualiser button on the bar sometimes does nothing** (George, 21
  and 22 Oct; not in 1.4.0's notes). Not the tray's 2 s self-hide (George
  tapped at once); a tap whose finger moves about 12 px gives no click in
  Chromium (reproduced headless), not yet caught on George's finger: the
  three recorded taps all worked. ShelvesPi's kiosk runs with a local
  DevTools port 9222 and a touch recorder in the page (`window.__rec`) until
  the next reboot (`/run/systemd/system/gexis-kiosk.service.d/zz-debug.conf`).
  Read the recorder when it fails again, then remove the drop-in and restart
  the kiosk (check nobody is using the bar first). `tools/panel-touch.py`'s
  coordinates are wrong on the 1480x320 bar - inject with CDP
  `Input.dispatchTouchEvent` instead.
- **Not yet tried with a real Home Assistant**: the dashboard was checked
  with George's own dashboard on sofapi (put back after) and with a
  throwaway one on R2D2 (`docker rm -f gexis-test-ha` when done); the phone
  typing with a stand-in login only, not George's. The schedule and standby
  over the dashboard are not tried on a device. iOS's handling of
  `interactive-widget` (the mini player on the keyboard) is not checked;
  Android's is.
- **The visualiser made cheaper, the rest left** (Finding 134; George,
  2026-10-22: stop here): the needle and spectrum skins are unchanged - the
  present itself and the vendored engines' drawing (to-do `viz-cheaper`).
- **Glass** (foonerd's Rust PeppyMeter, Finding 133): George, 2026-10-22,
  *"Glass is too young now"* - **remind him at the beginning of 2027** and
  measure it again (to-do `glass-revisit-2027`).
- George's look at the moon before sunrise.

**Phase 18, a Home Assistant dashboard on the screen** (`ph-ha-dashboard`,
ADR-0156) is built and in 1.4.0 on Testing; it is not closed in
`docs/DEVELOPMENT.md` - **a decision for George**: close it with 1.4.0, or
after a test with his real Home Assistant. **Next:** Phase 17, DSI screens
(`ph-dsi`), which waits for George to name his screen. Then, in order (`docs/DEVELOPMENT.md`; refer
to them by ID): **19** room correction for the bass (`ph-room-correction`),
**20** room correction for the full range (`ph-room-correction-full`), **21**
Home Assistant (`ph-home-assistant`), **22** themes (`ph-themes`), **23** the
library answers for itself (`ph-library`), **24** Lyrion's own menus' look
(`ph-lyrion-menus`); MPD is parked (`ph-mpd`, ADR-0151). Each ADR first. Still open from 1.0.0: Raspberry Pi
Imager, the image file and *Use custom* (g14).

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-10-21, after 1.3.1** (/home 227 -> 232 GB free); due again once PR #81 is merged.

## Phases

Closed: 0-16 (13 with letters a-f; Phase 15, the public API, on
2026-10-19 with 1.2.0; Phase 16, optical, with 1.3.0). Phases are numbered consecutively without letters,
each with a stable ID (George, 2026-10-13); the open ones are 17-24, with
MPD parked. `docs/DEVELOPMENT.md` holds each phase's acceptance criteria.

## Machines

| Name | What it is |
|---|---|
| R2D2 | Dev machine. CachyOS, **fish shell** (use `bash -c` for loops). Docker `data-root` `/home/docker`. Claude builds here; George flashes. |
| sofapi, the bar (ShelvesPi), guestpi | Test players, Pi 4. Reached by SSH key as `pi`; host keys kept in the session's scratchpad. |
| rig | Pi 4 reference for Findings 002-004. Not a test target. |
| LMS server | George's Lyrion server, for manual tests. CI must never depend on it. |

## Things that will bite

The full list, with how each was found, is in the archive (2026-10-12 block).

- **The release tag goes on the release-notes commit, nothing after it**
  (1.4.0, 2026-10-22): a package's version is the last commit that touched it,
  and the notes are core's last change - a documents fix committed after them
  and tagged built core as `1.3.1+git67`. A fix found after the notes goes in
  *before* them (reorder the unpushed commits), then the tag.

**Building**
- **Clear space with `make prune`, never `make clean`**: `clean` destroys the
  warm pi-gen stages (~9 GB; a cold build is ~40 min against ~15).
- **Never `docker start pigen_work`** - it starts a build. Read its volumes
  with a throwaway `docker run --rm --volumes-from pigen_work ...`.
- **Do not edit `core/`, `ui/dist`, `skins` or `stage-gexis` while an image
  builds**: they are bind-mounted live, and the `.info` would name a commit
  the image does not hold.
- **If the copy-out dies after a finished build, `make fetch-deploy`**
  recovers the image; an interrupted copy can truncate an older file in
  `deploy/` - check sizes.
- **Deleting a stage does not delete what it installed** until
  `stage-gexis`'s work directory is cleared (LESSONS 45).
- **A pinned package can vanish from the archive** (`alsa-lib`, ADR-0021):
  `make image` then stops at `00-alsa`; read the archive's own `Packages`
  index before changing anything.
- **Package versions take 7 hex characters** (`build.sh --abbrev=7`); a
  history rewrite after previews makes dpkg see a downgrade - put a preview
  device back with `apt-get install --allow-downgrades`, dry run first.

**Releasing**
- **Run `verify-image.sh` from the release worktree**: from the main checkout it
  compares against code the release does not carry (0.11.0: five false fails).
- **A skin pack whose version did not change ships the published file**
  (1.4.0): a rebuilt archive with the same files differs in bytes, and the
  repository refuses one version with two contents. Copy the published debs
  from the release that built them (for 1.4.0, `out/r1.3.0/repos/skins-*/`)
  into the release's `packaging/out` before `publish.sh`.
- **GitHub caches `channels/<name>` for minutes after a publish**: verify the
  new file with `gh release download channels`, not the public URL.

**On the players**
- **DSD silence is the byte `0x69`**, not zero; never play `/dev/urandom` or
  zeros as DSD - at Fixed it reaches the amplifier at full scale.
- **Uploaded plugins run as systemd dynamic users, which the system bus
  refuses** on our image: what a plugin needs from the system goes through
  the core (`announce`, ADR-0142).
- **Dry-run every install** (`apt-get -s`) and read the removals: a lone UI
  package removes `gexis-player`; build the player meta-package with the rest.
- **Restarting `gexis-core` does not reload the panel**: restart
  `gexis-kiosk`, and confirm the new bundle by hash in the core's log
  (LESSONS 10, 38, 66).
- **A flash wipes what the device learned: back up from Settings first** and
  keep the archive outside the repository (`core.toml` can carry a
  per-display `idle_url`).
- **The journal is in RAM unless *Debug logs* is on** (ADR-0103): a reboot,
  including a restore's, loses the logs - capture first.
- **Never reference an ALSA card by index**; use `hw:sndrpihifiberry`.
  `ctl.output` as well as `pcm.output` in `output.conf`; no `type plug` in the
  `output` chain.
- **Only Squeezelite may use `output_wait`** (ADR-0095): two waiters
  deadlocked the core.
- **`systemctl is-active` does not mean working**: check the symptom (audio,
  `fuser` on the PCM node).
- **Plexamp restores its queue on every start** - anything that starts it
  outside `plexamp.service` bypasses `plexamp-start-idle`.
- **BlueZ's `discoverable on` lapses after 180 s** unless the timeout is set;
  read `bluetoothctl show` back.
- **amixer's value line differs by control** (`Playback` word or not; mono
  controls print `Mono:`); `get_raw()` parses all three.
- **The 13.3" panel's setup jams the Pi's Wi-Fi** (2026-10-05); use a cable
  with it.

**In the repository**
- Every file we author under `core/src/gexis_core/` starts with
  `# SPDX-License-Identifier: GPL-3.0-or-later` (ADR-0025).
- No LAN addresses, MAC addresses, network names, `claude.ai` links or
  session ids in any committed file or commit message.

## Working agreement

As in `CLAUDE.md`: George is product manager, Claude implements; ADR before
architecture; findings state their scope; George merges every PR into `main`.
