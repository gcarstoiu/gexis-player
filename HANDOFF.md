# Handoff

Last updated: 2026-10-25 (on R2D2).

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

**Current release: 1.5.0, on Stable** (promoted 2026-10-25 at George's word:
Stable serial 9, Testing serial 55 since 2026-10-24, both signatures good
from the release key, read back with `gh release download channels`; the
public `gexis-player.img.xz` passes its checksum and signature and
decompresses to the checked image; r1.5.0 is GitHub's latest). Tag `v1.5.0` on the
release-notes commit `bfb0f647`; `next` and `release-1.5.0` pushed there.
Image `image/deploy/2026-10-24-gexis-player-v1.5.0.img` (`verify-image.sh`
123/123, 978 skins clean); parts `ours-17e046a32cf3`, `skins-67e037cab00f`,
`rpi-dea26bfd5ea8`, `debian-612079c6b5f1`; build output in
`~/projects/gexis-release-out/r1.5.0`. gexis-core and gexis-player `1.5.0`,
gexis-ui `1.4.0+git88.eaca532`, gexis-system `1.4.0+git29.d93d43f`.
What it carries: Phase 17's DSI screens, Phase 19's player side (`id`,
`screen`), the bar fixes (the tray's buttons on the first tap, settings
sheets that fit, pictures tried again, the tray staying open), the Lyrion
server and bar wallpaper fixes. **PR #82 was merged by George**
(2026-10-25); `main` is merged into `docs` and `next`, `release-1.5.0` and its
worktree are gone, and the routine clean-up ran. **PR #83** (README: 1.5.0
is the current release; branch `readme-1.5.0`, worktree
`~/projects/gexis-player-readme`) waits for George; the same line is on
`docs` and `next`.

**The release key** moved to `~/projects/gexis-release-key` (George,
2026-10-24): every release command sets
`GEXIS_RELEASE_GNUPGHOME=~/projects/gexis-release-key`; the scripts default
to `~/.gnupg-gexis-release`, which no longer exists.

**The players** (2026-10-25): ShelvesPi runs 1.5.0 (the four bar fixes
checked there by George, all fine, 2026-10-25; no debug drop-in or DevTools
port left), sofapi the
Phase 19 preview (core and player `1.4.0+git49.c4af394`, ui
`1.4.0+git24.e505054`), bedroompi `preview-1023` (core and player
`1.4.0+git45.561e337`, ui `1.4.0+git36.b8793e5`, system
`1.4.0+git29.d93d43f`); all of it is in 1.5.0, a newer version.

**The test venv imports the core from `~/projects/gexis-player-next`** (an
editable install): in another worktree run the suite with `PYTHONPATH=src`
from its `core/`, or it tests `next`'s code. **A preview of core needs the
player meta-package too** (it pins core exactly): `packaging/build.sh` with
every component and `player`, after copying the unchanged UI and system
packages from the release's build output (`repos/ours-*`).

**Deferred until a bug report** (George, 2026-10-21; from 1.3.1): the HMTECH 10.1" came up at 800x480 on the first start
after the boot that switched to it (Chromium stored 1004x580 in a 1024x600
work area: not full-screen), then full-screen on two restarts in a row. A
first start after a screen change may still miss full-screen. The 10.1" was
checked by its EDID in the tests, not again on the device under the new
standby.

**Release build output lives in `~/projects/gexis-release-out`**: in each
release worktree, `ln -s` it to `packaging/release/out` before `build.sh`
(excluded in `.git/info/exclude`). `reuse.py` reuses a published file only
against a local copy, so losing that folder means re-uploading every OS file.

**Not an issue** (George, 2026-10-20): Squeezelite joining whichever Lyrion
server answers first after a restart (Finding 130 point 6). GitHub reported
6 Dependabot alerts on `main` (all `vite`, the UI's build tool, not on the
player), raised 20-21 Oct.

**Open:**
- **`screen-name-tile`** (from `next`, worktree
  `~/projects/gexis-player-screen-name`, 2026-10-25): Settings' *Attached
  screen* tile showed the stored `Maker/Model` and broke mid-word (a DSI
  panel read "Raspberry Pi/Touch Display or compati / ble" on a phone, in
  1.5.0); now maker and model, wrapping between words. Checked with mocked
  data at the phone's, panel's and bar's size; waits for George's preview.
- **Not checked:** iOS's handling of `interactive-widget` (the mini player
  on the phone's keyboard); Android's is.
- **The visualiser made cheaper, the rest left** (Finding 134; George,
  2026-10-22: stop here): the needle and spectrum skins are unchanged - the
  present itself and the vendored engines' drawing (to-do `viz-cheaper`).
- **Glass** (foonerd's Rust PeppyMeter, Finding 133): George, 2026-10-22,
  *"Glass is too young now"* - **remind him at the beginning of 2027** and
  measure it again (to-do `glass-revisit-2027`).
- George's look at the moon before sunrise.

**In progress: Phase 19, the player in Home Assistant** (`ph-home-assistant`,
started 2026-10-24, ADR-0160). In 1.5.0: `id` and `screen` on
`/player/status` and the documents. The integration
`gcarstoiu/gexis-player-homeassistant` 0.1.0 is released (2026-10-24; local
copy `~/projects/gexis-player-homeassistant`, tests on `~/projects/ha-venv`).
Criteria 2-4 hold against a Home Assistant 2026.10.3 in Docker
(`~/projects/scratch/ha-test`, container `gexis-ha-test`, stopped; ADR-0160
*Measured*, Finding 137). **Criterion 1 seen 2026-10-25** on George's own
Home Assistant: every player found by itself, the controls working. **His
findings that day widen the phase** (criteria 5-7, ADR-0160): the source
shown and not chosen, and *Home*, *Now playing* and *Lyrics* buttons - in
the integration's 0.2.0 (released 2026-10-25), the documents on
`ph-home-assistant`; a D-pad for the panel and
a dashboard card of our own (switcher, D-pad, quick actions; George's
design in Claude Design), each with an ADR first: ADR-0161 (the D-pad)
accepted 2026-10-25 (George; its focus look comes from the design, and
nothing is built before it arrives, George the same day). HACS's default
list (our icon in HACS's store): not before Phase 19 is finished (George,
2026-10-25). The
brief for Claude Design is `design/briefs/19-ha-card-and-dpad-focus.md`, and
`design/IMPLEMENTED-DIFFERENTLY.md` was brought up to date for it. George
settled its three open points the same day: Settings stays on a bar
(ADR-0109 amended); the attribution line and a bar's two-step *Attached
screen* stay as built. George handed the brief to Claude Design
(2026-10-25); the card's look (Home Assistant's theme or the player's) is
settled in the design. **0.2.0 on George's Home Assistant** (2026-10-25):
HACS offered no update and a forced re-download brought no new entities
until *Update information* and a restart; then the three buttons showed.
On the Docker Home Assistant (2026.10.3) 0.2.0 adds them to an entry made
under 0.1.0 and serves `brand/icon.png` (local brand images since 2026.3).
HACS's own list shows the placeholder: the public brands site has no gexis
image. The branch and worktree
stay until the phase closes.

Then, in order (`docs/DEVELOPMENT.md`; refer
to them by ID): **20** a simple equaliser (`ph-equaliser`, added
2026-10-25: presets and a manual setup in CamillaDSP, the filter stage room
correction then reuses), **21** room correction for the bass
(`ph-room-correction`), **22** room correction for the full range
(`ph-room-correction-full`), **23** themes (`ph-themes`), **24** the
library answers for itself (`ph-library`), **25** Lyrion's own menus' look
(`ph-lyrion-menus`); MPD is parked (`ph-mpd`, ADR-0151). Each ADR first. **Raspberry Pi Imager**
(ADR-0159, a task, not a phase): the install guide is corrected; our own
Imager list and Imager's settings not now; Imager's own list stays open, as
it is, with no further changes for now (George, 2026-10-24).

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-10-25, after 1.5.0** (/home 223 -> 230 GB free).

## Phases

Closed: 0-18 (13 with letters a-f; Phase 15, the public API, on
2026-10-19 with 1.2.0; Phase 16, optical, with 1.3.0; Phase 18, the Home
Assistant dashboard, with 1.4.0; Phase 17, DSI screens, for 1.5.0). Phases are numbered consecutively without letters,
each with a stable ID (George, 2026-10-13); the open ones are 19-25, with
MPD parked. `docs/DEVELOPMENT.md` holds each phase's acceptance criteria.

## Machines

| Name | What it is |
|---|---|
| R2D2 | Dev machine. CachyOS, **fish shell** (use `bash -c` for loops). Docker `data-root` `/home/docker`. Claude builds here; George flashes. |
| sofapi, the bar (ShelvesPi), guestpi, bedroompi | Test players, Pi 4 (bedroompi: the Waveshare 10.1" DSI-TOUCH-A, Phase 17). Reached by SSH key as `pi`; host keys in `~/projects/scratch/known_hosts`. |
| rig | Pi 4 reference for Findings 002-004. Not a test target. |
| LMS server | George's Lyrion server, for manual tests. CI must never depend on it. |

## Things that will bite

The full list, with how each was found, is in the archive (2026-10-12 block).

- **The release tag goes on the release-notes commit, nothing after it**
  (1.4.0, 2026-10-22): a package's version is the last commit that touched it,
  and the notes are core's last change - a documents fix committed after them
  and tagged built core as `1.3.1+git67`. A fix found after the notes goes in
  *before* them (reorder the unpushed commits), then the tag.
- **A cancelled run blocks the release PR** (1.5.0, 2026-10-24): pushing
  `next` again cancels the run on the release commit, and `main`'s ruleset
  counts a cancelled *Core tests* as failed, though the PR's own run passed.
  Re-run it (`gh run rerun <id>`), or push `next` once.

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
