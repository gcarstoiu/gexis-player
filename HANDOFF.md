# Handoff

Last updated: 2026-10-12 (on R2D2).

## Start here

Branches: **`phase-13b`** in the main checkout holds the documents and shared
work; **`phase-13d`** in `~/projects/gexis-player-13d` is the release branch,
and `phase-13b` is merged into it after each docs change. A release is built
from a worktree made at its tag, then removed. History: `docs/HANDOFF-ARCHIVE.md`
(search it; never read it whole).

**Current release: 0.11.0 on Testing** (2026-10-12; tag `v0.11.0`, release
`r0.11.0`, serial 37, PR #62 merged; image
`image/deploy/2026-10-12-gexis-player-v0.11.0.img`). USB DACs and native DSD
(ADR-0143/0144, Finding 120), the screen on either HDMI port (ADR-0109
amended), the player announcing for its plugins (ADR-0142), plugin versions,
Phase 13d closed. After the tag on `phase-13d`: setup keeps the screen it
applied (the bar's lingering "provisional"). Suite 2,322.

**Devices.** sofapi (Waveshare 10.1"; a test machine - its Lyrion queue may
be lost, George 2026-10-12; an SMSL USB DAC on it), the bar (ShelvesPi,
11.9") and guestpi (IQaudIO Pi-DAC PRO, 13.3") all run `phase-13d` previews
of 2026-10-12 (core `+git52` to `+git76`; sofapi carries the newest, with the
USB DAC and DSD work). **Cards flashed
from now on have no passwordless sudo: provision test cards with
`DEV_SUDO="yes"`** (ADR-0139).

**Owed by George** (the shared to-do list has the detail)
- On a card flashed from the 0.11.0 image: setup without a restore (g24),
  setup over a network cable (g26), an update cut short and a factory reset
  (g34).
- The screen on the bar's second HDMI port (g35).
- ADR-0141, picture and sound on different HDMI ports: six decisions, the
  first being before or after 1.0 (g36).
- Then: 1.0.0 cut from this code as the first Stable release.
- Optional: Lyrion sync (g09), the bar's own supply (g12), a DSD file from the
  library (g38).

**Not run on a device yet:** a screen on HDMI-A-2; a fresh card from 0.11.0;
setup over Ethernet; a cut-short update; a factory reset.

**Next: 1.0.0, the first public release**, once George's tests pass: the
notes, promote to Stable with the image file (c16; the installation guide's
download works from then), README's *Download and install* section, Raspberry
Pi Imager - the image file and *Use custom*, our own Imager repository and the
community application after (g14). **After it**, in order (`docs/DEVELOPMENT.md`, "Phases after the first
public release"; refer to them by ID): **14** MPD for real 5.1/7.1
(`ph-mpd`), **15** the player in Home Assistant (`ph-home-assistant`), **16**
themes (`ph-themes`), **17** a sound bar on optical (`ph-optical`), **18** the
library answers for itself (`ph-library`), **19** Lyrion's own menus' look
(`ph-lyrion-menus`) - each ADR first.

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-10-12 evening, after 0.11.0** (the first: ~102 GB and ~30,500 -> ~9,500
words in the morning).

## Phases

Closed: 0-12, 13, 13a, 13b, 13c, 13d (2026-10-12, Finding 114's addendum),
13e, 13f (2026-10-12: shipped behind *Extended navigation*; its look is
`ph-lyrion-menus`) (`docs/DEVELOPMENT.md` holds each phase's acceptance criteria; the archive
holds the order as it was argued). **From 2026-10-13 phases are numbered
consecutively without letters, each with a stable ID** (George); the open ones
are 14-19, listed under *Next*.

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
- **Run `verify-image.sh` from the release worktree**: from `phase-13b` it
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
