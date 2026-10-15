# Handoff

Last updated: 2026-10-15 (on R2D2).

## Start here

Branches: **`phase-13b`** in the main checkout holds the documents and shared
work; **`phase-13d`** in `~/projects/gexis-player-13d` is the release branch,
and `phase-13b` is merged into it after each docs change. A release is built
from a worktree made at its tag, then removed. History: `docs/HANDOFF-ARCHIVE.md`
(search it; never read it whole).

**Current release: 1.0.1, the first Stable release** (2026-10-15; tag
`v1.0.1`, release `r1.0.1`; Testing serial 43, Stable serial 1, signatures
checked; image `image/deploy/2026-10-14-gexis-player-v1.0.1.img`, 121 checks;
the public download verified). PR #69 merged by George; both branches carry
it, the release worktree and branch are removed.

**1.0.0 was promoted and pulled back the same night** (Finding 126): on the
11.9" bar the setup network could not be joined. 1.0.1's setup network takes
channel 1, 6 or 11, farthest from the screens' pixel-clock multiples
(ADR-0031 amended). **Settled 2026-10-15** (Finding 126, three test rounds,
three research reviews): the cause is the HDMI signal - changing only the
bar's clock (59.4 -> 35.5 MHz) brought channel 6 back; kiosk, CPU load,
Bluetooth and power saving made no difference; nothing radio-related changed
in our software or the OS since 0.9.1. Why it worked before: **open** - the
adapter swapped on 2026-10-14 at 19:25 was the suspect, but a cable in its
place fails the same way (10:13 run); what else changed physically is not on
record. The pixel-clock rule ignores neighbours:
on sofapi at 6-7 m only channel 6 was usable (channel 1 crowded).
**Decided (George, 2026-10-15):** keep the rule and add the rotation - the
next channel every 2 min until a phone joins, the join step counting down
(ADR-0031 amended; 5335250f on `phase-13d`, not released). On bedroompi
since 10:54 for George to try; the 2 minutes proposed for ADR-0022 as [H],
not appended.
The bar's test card (`bedroompi.local`, in ShelvesPi's Pi) still runs 1.0.0
with the fix hand-copied - reflash it from the 1.0.1 image.

**Fixed on `phase-13d`, not released:** the stand-in watcher (ADR-0141 D5)
failed every 3 s in 1.0.0/1.0.1 - a settings read from a worker thread - so
the jack never stood in (a539d16d, LESSONS 73); once working, a missing
output was reported every 3 s (a816c24d, now once). On sofapi since
2026-10-15 09:47: no errors; the switch itself not yet tried with a receiver.

Suite 2,485 passed, 47 skipped (2026-10-15).

**Devices.** sofapi (Waveshare 10.1"; a test machine - its Lyrion queue may
be lost, George 2026-10-12; an SMSL USB DAC on it), the bar (ShelvesPi,
11.9") and guestpi (IQaudIO Pi-DAC PRO, 13.3") as read 2026-10-13:
sofapi runs a `phase-13d` preview (core and player `1.0.1+git23`, UI
`0.15.0+git44`, 2026-10-15); the bar runs release 0.14.0; guestpi as read
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
2026-10-15, after 1.0.1's PR (#69)** (/home 224 -> 242 GB free; start-of-session
reading ~4,800 words).

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
