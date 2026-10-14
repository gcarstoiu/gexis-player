# Handoff

Last updated: 2026-10-14 (on R2D2).

## Start here

Branches: **`phase-13b`** in the main checkout holds the documents and shared
work; **`phase-13d`** in `~/projects/gexis-player-13d` is the release branch,
and `phase-13b` is merged into it after each docs change. A release is built
from a worktree made at its tag, then removed. History: `docs/HANDOFF-ARCHIVE.md`
(search it; never read it whole).

**Current release: 0.14.0 on Testing** (2026-10-13; tag `v0.14.0`, release
`r0.14.0`, serial 40; PR #65 merged 2026-10-14, post-merge steps and the
routine clean-up done; image `image/deploy/2026-10-13-gexis-player-v0.14.0.img`,
121 checks passed). One Screen
tile; a TV as the screen at 1080p (ADR-0147 amended twice after George's TV
tests); standby keeps a sound port on; the update backup survives a vanishing
file. 0.13.0 (PR #64) merged and its post-merge steps done. The bar is on
0.14.0: **the second power cut passed** (2026-10-14, Finding 123
addendum) - cut mid-install, finished by itself at the next start.

**Since 0.14.0, on `phase-13d` and installed on sofapi only** (George's
fixes of 2026-10-14, all for the next release; its notes need his approval):
Attached screen and Screen port as two tiles again, the Screen port tile
listing what is on each port; the home strip scrolls by touchpad; the
outline follows every pressable in its own shape, cut to the part that
shows, none round a row with its actions revealed, the dot small inside it;
similar-artist tags, the artist's name and the release title open their
pages; the touchpad pings (2 s, fresh socket after 5 s) and probes at the
first touch after a quiet spell; Wi-Fi power saving off on a player; the
sheet swipes open and closed; artist photos kept across a Lyrion rescan
(revalidated by name - the first rescan after the update still drops them
once); later the same day: the outline cut only by what covers an element, a
touchpad tap over the visualiser only dismisses it, the TV's mode kept after
it is turned off and on, artists and *Play playlist* on app playlists, a
stream's own artwork in the queue, Popular reveals, teal selection, tab
underline, search opens on its field, and **Text size** (ADR-0148). **George
checked them on sofapi (g46, done 2026-10-14).** **Players are not
updated to a release by Claude** (George, 2026-10-13).

**From the power-cut test, in 0.13.0:** George's power cut on the bar (g34,
Finding 123) found the updater could not recover - its note for the boot was
an empty file (never synced), and every check said "current". Fixed: the
note is synced, a cut-short install is finished with no note (at boot and at
every check), only half-installed packages are reinstalled, the whole release
completed after. The bar recovered with the fixed code (run from a copy) and
is on the complete 0.12.0 set. Also: *Could not check for updates* says why
in words. **Not proved:** a second real cut with the fixed updater
installed - done 2026-10-14, passed. LESSONS 70.

Suite 2,386 passed, 47 skipped (2026-10-14).

**Devices.** sofapi (Waveshare 10.1"; a test machine - its Lyrion queue may
be lost, George 2026-10-12; an SMSL USB DAC on it), the bar (ShelvesPi,
11.9") and guestpi (IQaudIO Pi-DAC PRO, 13.3") as read 2026-10-13:
sofapi runs a `phase-13d` preview (core `0.14.0+git20`, UI and player
`+git28`, 2026-10-14); the bar runs release 0.14.0; guestpi as read
2026-10-13, core `0.10.2+git63`. **Cards flashed
from now on have no passwordless sudo: provision test cards with
`DEV_SUDO="yes"`** (ADR-0139).

**Owed by George** (the shared to-do list has the detail)
- On a card flashed from the 0.12.0 image: setup without a restore (g24),
  setup over a network cable (g26).
- The screen on the bar's second HDMI port (g35).
- The spectrum on sofapi's panel after the change (Finding 122): whether the
  bars now look right.
- On sofapi: the meters falling with the volume, and *Visualiser tweaks* →
  *Needles follow the volume* and *Gain* (ADR-0146).
- Then: 1.0.0 cut from this code as the first Stable release.
- Done 2026-10-14: the fixes since 0.14.0 on sofapi (g46); Lyrion synced playback (7e/g09, passed); the bar's supply
  (g12: the undervoltage was the USB extension cord, 0x0 plugged in
  directly).

**Not run on a device yet:** a screen on the bar's HDMI-A-2; a fresh card
from 0.12.0; setup over Ethernet; the outline cut by the real mini strip (a
stand-in bar only, headless).

**Next: 1.0.0, the first public release**, once George's tests pass: the
notes, promote to Stable with the image file (c16; the installation guide's
download works from then), README's *Download and install* section, Raspberry
Pi Imager - the image file and *Use custom*, our own Imager repository and the
community application after (g14). **After it**, in order (`docs/DEVELOPMENT.md`, "Phases after the first
public release"; refer to them by ID): **14** MPD for real 5.1/7.1
(`ph-mpd`), **15** room correction with a USB microphone (`ph-room-correction`),
**16** the player in Home Assistant (`ph-home-assistant`), **17** themes
(`ph-themes`), **18** a sound bar on optical (`ph-optical`), **19** the library
answers for itself (`ph-library`), **20** Lyrion's own menus' look
(`ph-lyrion-menus`) - each ADR first.

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-10-14, after 0.14.0's PR** (the first: ~102 GB and ~30,500 -> ~9,500
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
