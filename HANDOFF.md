# Handoff

Last updated: 2026-10-18 (on R2D2).

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

**Current release: 1.0.6, on Stable** (2026-10-17; Stable serial 4, Testing
serial 48, signatures verified through the API and the public URL; image
`image/deploy/2026-10-17-gexis-player-v1.0.6.img`, 123 checks, the public
download byte for byte the checked image; built in 16 minutes, the skin
packs reused): *Add a backup* in Settings → Restore (ADR-0083 amended
2026-10-17), the backup fixes, the Settings header wrap. PR #74 merged by
George; post-merge steps and the routine clean-up done.

**Phase 14 (`ph-first-use`) is built on its own branch, not merged**
(worktree `~/projects/gexis-player-14`, branch `ph-first-use` off
`next` (then `phase-13d`), pushed). **Reworked 2026-10-18 after George found it did not
follow the designs**: first use (part 1 setup and part 2 *Make it yours*) is
now one page, `FirstUsePage.svelte`, **generated** from Claude Design's
`design/source/14-first-use` by `tools/design/gen_personalise.py`. The markup
and styles are converted mechanically, the prototype's logic is kept
verbatim, and 40 asserted replacements call the core. Change the design, then
generate again; never restyle the `.svelte` by hand. Every screen was checked
side by side with the prototype. ADR-0149's decisions were revised (25,
including the two kept against the design: Output and the rename/second
player on a restore, George 2026-10-08). **sofapi runs it** (core `1.0.6+git87`, UI and player `+git88`; part 2 opens from Settings → System →
Personalise). Added 2026-10-18 at George's request: a Touchpad step in
part 2 (before the visualiser; preview with the pointer moving) and the
volume type under part 1's Output (`GET /setup/outputs`; ADR-0149 26-27). Then: Getting ready shows the
opening flow animation with the chosen sources and a status badge, and the
core keeps the Lyrion servers found (`discovery.Known`; the list answered in
3 ms on sofapi, was 2.8 s; ADR-0149 28-29). After George's part 2 test: Getting
ready names every stage of a download from the live component status (the
pack already in on sofapi had sat at 0 % for 30 s), and *Personalise* is at
the top of Display (ADR-0149 30-31).

**Tested, or nothing** (on `next`, merged into `ph-first-use`; George,
2026-10-18): every list of screens, boards and outputs shows *Tested* (here,
or reported working by owners) or no mark; a reported problem is a line
under the model; an output's name no longer carries its state (settings
migration 10 rewrote sofapi's stored output). ADR-0126, 0117 and 0109
amended; HARDWARE.md's table regenerated.

**The waiting screen's sources** (on `next`, 2026-10-18; George: reuse the
library's waiting footer without its bar): `WaitingServices` in a `bare`
form, the pulsing marks straight on the picture, and no hint line or
*Hint on the waiting screen* setting (migration 11); manual pictures retaken through the demo
front (scratchpad `holddemo.py`, ports 8097/8098, `lmsoff.flag`,
`DEMO_NAME`). Plexamp is one screen in part 2, its sign-in read from the
plugin (ADR-0149 32-34). Should list: DSI screens, weather on the waiting
screen. Since George's notes of 2026-10-18: part 2 is owed only until
the first boot after setup (`personalise.at_start`), a restore is pinned by
a test never to owe it, and the visualiser tweaks show only what the skin
type draws (on `next`, merged into `ph-first-use`). After George's full run
on a fresh card (2026-10-18): part 2's panel screen first, *Do it later* =
Spotify and Bluetooth, the core restarts once settled when part 2 sets a
Lyrion server, the output recommendation, Headless apart, the standby picker
(ADR-0149 35-41); on `next`: the setup password is `gexis-setup` always, a
show-password eye, plain HTTP stays and is explained, no text selection on
the panel, BlueZ's "Not Provided" is no title. *Personalise* is in ADR-0022 (George, 2026-10-18). Waiting
for George: his test of part 2, then part 1 on sofapi after *Reset to
factory settings* (his choice, instead of a fresh card), then the PR.

**Release build output lives in `~/.local/share/gexis-release-out`**: in each
release worktree, `ln -s` it to `packaging/release/out` before `build.sh`
(excluded in `.git/info/exclude`). `reuse.py` reuses a published file only
against a local copy, so losing that folder means re-uploading every OS file.

**The blog** (George's WordPress, tag `sound`): eleven articles in
`~/projects/gexis-blog/`, pushed as drafts by George (2026-10-15; article 05
now mentions *Add a backup*, bundle rebuilt 2026-10-17, for George to re-push);
`schedule_wp.py` schedules nine, daily at 18:00 from 2026-10-16 - whether he
ran it is not recorded. The theme (`gcarstoiu/gexis-wp-theme` 1.0.3, pushed)
mirrors FAQ, Install, Hardware, Manual and Release notes from `main`.

Suite 2,493 passed, 47 skipped (2026-10-16), with the venv in
`~/.local/share/gexis-venv` (never under `/tmp`: LESSONS 74).

**Devices.** sofapi (Waveshare 10.1", SMSL USB DAC; a test machine), the bar
(ShelvesPi, 11.9"), guestpi (IQaudIO Pi-DAC PRO, 13.3"), bedroompi (a
separate card; off the network on 2026-10-16 evening). sofapi and ShelvesPi
run previews from the release branch (equal in content to 1.0.5); guestpi and bedroompi are
offered 1.0.5 on Stable. **Cards flashed now have no passwordless sudo:
provision test cards with `DEV_SUDO="yes"`** (ADR-0139).

**Owed by George** (the shared to-do list has the detail)
- On a card flashed from the 0.12.0 image: setup without a restore (g24),
  setup over a network cable (g26).
- The screen on the bar's second HDMI port (g35).
- The spectrum on sofapi's panel after the change (Finding 122).
- On sofapi: the meters falling with the volume, and *Needles follow the
  volume* and *Gain* (ADR-0146).

**Not run on a device yet:** the outline cut by the real mini strip (a
stand-in bar only, headless); the headphone jack taking over from a
switched-off HDMI device (ADR-0141 D5, fixed in 1.0.2).

**Next: George's test of Phase 14 on sofapi** (above): part 2, then part 1
after a factory reset, then a PR for `ph-first-use`. Still open from the release:
Raspberry Pi Imager, the image file and *Use custom* (g14). **After it**, in order
(`docs/DEVELOPMENT.md`, "Phases after the first public release"; refer to them
by ID): **15** MPD for real 5.1/7.1 (`ph-mpd`), **16** room correction with a
USB microphone (`ph-room-correction`), **17** the player in Home Assistant
(`ph-home-assistant`), **18** themes (`ph-themes`), **19** a sound bar on
optical (`ph-optical`), **20** the library answers for itself (`ph-library`),
**21** Lyrion's own menus' look (`ph-lyrion-menus`) - each ADR first.

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-10-17, after 1.0.6's PR (#74)** (/home 225 -> 238 GB free).

## Phases

Closed: 0-12, 13, 13a, 13b, 13c, 13d (2026-10-12, Finding 114's addendum),
13e, 13f (2026-10-12: shipped behind *Extended navigation*; its look is
`ph-lyrion-menus`) (`docs/DEVELOPMENT.md` holds each phase's acceptance criteria; the archive
holds the order as it was argued). **From 2026-10-13 phases are numbered
consecutively without letters, each with a stable ID** (George); the open ones
are 14-21. **Phase 14 is `ph-first-use`** (George, 2026-10-15): setup split into
a device part and a personal part, before MPD (now 15); ADR-0149 proposed, its
open points owed by George, then Claude Design.

## Machines

| Name | What it is |
|---|---|
| R2D2 | Dev machine. CachyOS, **fish shell** (use `bash -c` for loops). Docker `data-root` `/home/docker`. Claude builds here; George flashes. |
| sofapi, the bar (ShelvesPi), guestpi | Test players, Pi 4. Reached by SSH key as `pi`; host keys kept in the session's scratchpad. |
| rig | Pi 4 reference for Findings 002-004. Not a test target. |
| LMS server | George's Lyrion server, for manual tests. CI must never depend on it. |

## Things that will bite

The full list, with how each was found, is in the archive (2026-10-12 block).

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
