# Handoff

Last updated: 2026-10-21 (on R2D2).

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

**Current release: 1.3.1, on Stable** (2026-10-21; Stable serial 8,
Testing serial 53, both signatures good from the release key, read back from
GitHub; the public `gexis-player.img.xz` decompresses to the checked image).
Image `image/deploy/2026-10-20-gexis-player-v1.3.1.img`, 123 checks, 978
skins clean; parts `ours-2a97557a07d1`, `skins-67e037cab00f`,
`rpi-7325dbec7a52`, `debian-256b0ff5ed7a`. A fix release: the idle countdown
re-arms after the visualiser, standby wakes on a tap read from the kernel and
reads the real screen at start (ADR-0135 amended), the kiosk forgets
Chromium's stored window at every start, and the HMTECH 7" and 10.1" (both
without touch) are tested. A screen's few seconds back from standby are the
screen's own (the bar ~3 s; George: "Keep it as is"), in the release notes and
the FAQ. **PR #80** was merged by George; post-merge steps and the clean-up are
done. sofapi runs `1.3.0+git16`, ShelvesPi `1.3.0+git11` - previews of what
1.3.1 carries; they move to 1.3.1 by the update. GitHub reports 6 Dependabot
alerts on `main` (2 high, 4 moderate), all `vite` (the UI's build tool, not
on the player; fixed in 8.3.3), raised 20-21 Oct.

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

**Not an issue** (George, 2026-10-20): Squeezelite joining whichever Lyrion server answers first after a restart (Finding 130 point 6). **Open:** George's look at the moon before sunrise. sofapi
and ShelvesPi run previews of 1.3.1's fixes.

**In flight (2026-10-21), each on its own branch, none merged into `next`
yet:**
- `tap-no-flash` (rows: a tap shows only the selection), `peppy-quiet-repaint`
  (the repaint after a show painted out of sight; check-skins holds the level,
  978 pixel-exact; the skin packs' check left out of their version, with a
  floor at `96b8a42`), `album-track-artist` (a track's own artist when not the
  album's). All three together on **ShelvesPi as one preview**
  (`preview-1021`, `1.3.1+git11.8d12629`), George testing.
- `ph-ha-dashboard` (Phase 18): core, panel, buttons, schedule, docs,
  Finding 132; on **sofapi** (`1.3.1+git12.96d8129`), shown and its failure
  message checked by screenshot with a framable page. Not yet tried: the
  phone's and the tray's buttons, the schedule, standby over it, a real Home
  Assistant dashboard (George has no address yet; he declined changes to his
  Home Assistant - the player changes nothing there, ADR-0156 decision 8).
  A throwaway Home Assistant runs on R2D2 (`docker rm -f gexis-test-ha` when
  done).
- **Open: the visualiser button on ShelvesPi refused several taps** (George,
  21 Oct morning: nothing happened). The page received the taps (`/touch`)
  but sent no `/peppy/show`; cause not found by reading. Next: reproduce with
  injected taps (`tools/panel-touch.py`) once George is off the bar. The bar's
  touch controller also dropped off USB at 07:56 and 08:15 (about 1 s each).

**Next: Phase 18, a Home Assistant dashboard on the screen**
(`ph-ha-dashboard`, ADR-0156, added 2026-10-21; George: *"let's build
afterwards"*) - built ahead of Phase 17, DSI screens (`ph-dsi`), which waits
for George to name his screen. Then, in order (`docs/DEVELOPMENT.md`; refer
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
2026-10-21, after 1.3.1** (/home 227 -> 232 GB free).

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
