# Handoff

Last updated: 2026-10-12 (on R2D2).

## Start here

Branches: **`phase-13b`** in the main checkout holds the documents and shared
work; **`phase-13d`** in `~/projects/gexis-player-13d` is the release branch,
and `phase-13b` is merged into it after each docs change. A release is built
from a worktree made at its tag, then removed. History: `docs/HANDOFF-ARCHIVE.md`
(search it; never read it whole).

**Current release: 0.10.2 on Testing** (2026-10-12; tag `v0.10.2`, release
`r0.10.2`, serial 36, PR #61 merged; image `image/deploy/2026-10-12-gexis-player-v0.10.2.img`,
the only one kept). It holds the final code review's fixes (Finding 119: 77
confirmed, all addressed) and George's twelve answers to its questions
(ADR-0139 no sudo in the image, ADR-0140 software level before the
renderers, and ten others - see the PR and Finding 119). Suite 2,255.

**Devices.** sofapi (Waveshare 10.1"; its Lyrion queue is George's - do not
clear it) and the bar (ShelvesPi, 11.9") run `phase-13d` previews
(0.10.1+git122), which 0.10.2 supersedes. guestpi offline. **Cards flashed
from now on have no passwordless sudo: provision test cards with
`DEV_SUDO="yes"`** (ADR-0139).

**Owed by George**
- Confirm the new [H] values for ADR-0022's inventory: `SETUP_ACTIVE_S`
  600 s, `KEEP_AUTOMATIC` 3, the cache's 2 GiB free / 10 % / hourly, the
  30-day photo re-ask, the 20 s / 120 s / 15 min request limits.
- Tests on 0.10.1-0.10.2: volume type changes (g04, g05), Plexamp's slider in
  Fixed (g22), the Space topic, a freshly flashed card without a restore
  (g24), setup over a network cable (g26), a USB DAC at its highest rate
  (g10), Phase 13f's look (g25).
- Decide the version (g27, 1.0.0 suggested) and allow Claude's device tests on
  the bar (g29: headphone jack, switches, the boot step in Software, a reset,
  a cut-short update).
- The bar's Plexamp needs a new claim token; the bar on its own supply, then
  Claude reads `vcgencmd get_throttled` again.

**Run on the bar 2026-10-12 and right** (Finding 119): the headphone jack
(0 % and Mute silent), levels carried across output and volume-type changes,
the boot step in Software. **Not run yet:** a cut-short update and a factory
reset (both need George), setup over Ethernet (g26).

**Next: the first public release** (George, 2026-10-12). It waits for
guestpi (Phase 13d's two tests). Then: promote to Stable with the image file
(c16; the installation guide's download works from then), README's "first
Stable release is next", Raspberry Pi Imager - the image file and *Use
custom* at the release, our own Imager repository and the community
application after (g14). **After it:** Phase 13g (the player in Home
Assistant), themes (14), a sound bar on optical (14a), the library answering
for itself (15) - each ADR first. HDMI audio on the second port: to revisit.

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-10-12** (~102 GB freed; start-of-session reading ~30,500 -> ~9,500 words).

## Phases

Closed: 0-12, 13, 13a, 13b, 13c, 13e (`docs/DEVELOPMENT.md` holds each phase's
acceptance criteria; the archive holds the order as it was argued). Open:
**13d** DACs we have not tested - closes after guestpi's two tests (Plexamp
through the IQaudio Pi-DAC PRO; a chosen board that is not fitted taken
back); **13f** Lyrion's own menus - closes on George's look; **13g** the player
in Home Assistant - after the release; **14** themes - settle first what a
theme is if plugins are processes (ADR-0016); **14a** a sound bar on optical
(a maximum sample rate per output); **15** the library answers for itself
(Plex server metadata first, internet providers as fallback; Finding 086).

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

**On the players**
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
