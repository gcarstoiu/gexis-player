# Handoff

Last updated: 2026-10-19 (on R2D2).

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

**Current release: 1.3.0, on Stable** (2026-10-20; Stable serial 7,
Testing serial 52, both signatures good from the release key, read back from
GitHub; the public `gexis-player.img.xz` decompresses to the checked image).
Image `image/deploy/2026-10-20-gexis-player-v1.3.0.img`, 123 checks, and all
978 skins through the new whole-pack check (`make check-skins`, run by `make
image`); parts `ours-c886989caba4`, `skins-c272f4628d09` (new),
`rpi-7325dbec7a52`, `debian-5d5dc927ef03`. It carries Phase 16 (optical,
ADR-0155), the moon at night (ADR-0153), four more icon sets (ADR-0154), the
Static fix (Finding 129), the visualiser repaint (Finding 131) and aiohttp
3.14.4. **PR #79** was merged by George; post-merge steps and the clean-up are done
(the four feature branches and worktrees removed; the wiki Roadmap pushed
with George's OK: Now 17 DSI, Next 18 room correction and 19 Home
Assistant). The three aiohttp
alerts close when Dependabot rescans `main` (it holds 3.14.4).
GitHub Pages builds the API page from the `v1.3.0` tag.

**Release build output lives in `~/.local/share/gexis-release-out`**: in each
release worktree, `ln -s` it to `packaging/release/out` before `build.sh`
(excluded in `.git/info/exclude`). `reuse.py` reuses a published file only
against a local copy, so losing that folder means re-uploading every OS file.

**In `next`, for the next release** (2026-10-20): the idle countdown re-arms
whenever the idle screen goes away (sofapi was off its idle screen 12:30-20:22
after the visualiser took it down), and standby wakes on a tap read from the kernel while the
output is off, and reads the real screen at start (ADR-0135 amended:
ShelvesPi's bar stayed dark all day - its taps had no output to land on, and
the update's restart forgot the standby). Powering the display down with
`wlopm` was tried and dropped (3 s back); the bar's ~3 s is its own screen
resyncing (switching takes 0.05 s) - George: "Keep it as is". ShelvesPi runs
`1.3.0+git11` (both fixes; `wlopm` removed again), sofapi `1.3.0+git6` (the
idle fix). Branches `idle-rearm`, `standby-power` (superseded) and
`standby-touch` merged into `next`, to delete after the release.

**Open, sofapi's new 7" (HMTECH, 800x480, EDID "HCT"/"HDMI"), 2026-10-20
evening:** with the kiosk's `--force-device-scale-factor=0.625` Chromium draws
the page at 500x300, centred, inside a full-screen window (measured with grim:
not a start-up race, not the Sony's second output, not a missed full-screen;
without the scale it fills but the layout is cut). ShelvesPi at 0.8 fills.
No 800x480 screen had run on hardware before. Its touch does not show on USB
at all (only the optical adapter). The list's "HMTECH 7" HDMI Monitor" is the
non-touch model. **Not recorded as tested** until it works.

**Open:** Squeezelite joins whichever Lyrion server answers first after a
restart (Finding 130 point 6); George's look at the moon before sunrise. sofapi
and ShelvesPi run previews (above).

**Next: Phase 17, DSI screens** (`ph-dsi`; George names his screen when it
starts), next. Then, in order (`docs/DEVELOPMENT.md`;
refer to them by ID): **18** room correction
(`ph-room-correction`), **19** Home Assistant (`ph-home-assistant`), **20**
themes (`ph-themes`), **21** the library answers for itself (`ph-library`),
**22** Lyrion's own menus' look (`ph-lyrion-menus`); MPD is parked
(`ph-mpd`, ADR-0151). Each ADR first. Still open from 1.0.0: Raspberry Pi
Imager, the image file and *Use custom* (g14).

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-10-20, after 1.3.0** (/home 226 -> 232 GB free).

## Phases

Closed: 0-15 (13 with letters a-f; Phase 15, the public API, on
2026-10-19 with 1.2.0). Phases are numbered consecutively without letters,
each with a stable ID (George, 2026-10-13); the open ones are 16-22, with
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
