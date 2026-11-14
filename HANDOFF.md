# Handoff

Last updated: 2026-11-14 (on R2D2).

## Start here

Branches: **`docs`** in the main checkout holds the documents and shared
work; **`next`** in `~/projects/gexis-player-next` is the release branch, and
`docs` is merged into it after each docs change. A phase's work has its own
branch (`ph-…`), merged into `next` once George's tests pass. A release is
built from a worktree made at its tag, then removed.

**GitHub checks every push**: *Core tests* (Python 3.13) and *UI build*;
`main`'s ruleset requires both and a pull request; merged branches are
deleted by GitHub; Dependabot sends security alerts only.

**The public roadmap is the GitHub wiki's *Roadmap* page** (2026-10-18; its own
repository, `gexis-player.wiki.git`): Now, Next (the next two phases), Later,
and the ideas as Must / Should / Could. It follows `docs/DEVELOPMENT.md`'s
phases; change it when a phase opens, closes or moves, and show George first. History: `docs/HANDOFF-ARCHIVE.md`
(search it; never read it whole).

**Stable: 1.16.1** (2026-11-10; serial 15): room correction's Full range marked *Limited testing* (George),
on 1.16.0 (room correction for the full range, Phase 30), with 1.14.0 (Phase
29) and 1.15.0 (Phase 35) - Stable came from 1.13.0. Built by run
42864483931 (`verify-image.sh` all 151 checks passed); signed on R2D2; both
channels read back with a good signature; `releases/latest` is r1.16.1 and
its image (1.1 GB) downloads through README's link, matching its checksum
and signature. Notes approved by George; PRs #98 and #99 merged by George
(README names 1.16.1). `v1.16.0` is
a lightweight tag (the others annotated); `build.sh` reads tags with
`--tags`, so its versions are right.

**Testing: 1.16.2** (2026-11-12, serial 70; Stable stays 1.16.1): the 55
fixes from the review of 1.16.1 (the four users see: ADR-0178) and a
group's buffer of a second (ADR-0166 amended). Built by run 43305560359
(`verify-image.sh` all 155 checks passed), signed on R2D2, read back with a
good signature; notes approved and PR #100 merged by George. **Owed after
the merge:** `main` into `docs` and `next` and the routine clean-up; Finding
145; then the worktrees (`gexis-player-fixes`, `gexis-player-fixes-b`,
`gexis-fix-*`, `gexis-review`, `gexis-review-fixes`,
`gexis-release-1.16.2`) and the local `fix-*` branches removed.
`publish.sh` keeps a serial floor in `out/serials/`.

**The plugin catalogue** (Phase 24, closed 2026-10-31):
`gcarstoiu/gexis-plugins` (local `~/projects/gexis-plugins`; `tools/publish.sh`
with `GEXIS_CATALOGUE_GNUPGHOME=~/projects/gexis-catalogue-key`), serial 5,
TV remote 0.1.1 listed. The catalogue key's master and revocation
certificate wait in `~/projects/gexis-catalogue-key-for-george` until George
has them. Not yet seen on a player: the visualiser back after a real drop of
the TV's output; the store on a bar; setup writing a plugin record; Remove
with *Keep* off (ADR-0147, ADR-0169); George's phone test of the dialogs
(to-do `fix-remote-dialogs-test`). The mocked-screen checks
(`~/projects/scratch/dpad`, `ph24`, `ph26/sources`, `ph26/blog`) build from
`~/projects/gexis-player-next` unless `WT` names another worktree.

**Roon** (Phase 26, closed): `gcarstoiu/gexis-roon` (local
`~/projects/gexis-roon`) 0.2.1, pinned in `packaging/roon/pins.sh`. **Left
open** (ADR-0172, *Built*): Roon took the output back eight seconds after
Lyrion took it, the cause not established (0.2.1 logs the pause's answer
and the loopback's states); not measured: bit-perfect, rates above 44.1 kHz,
a group, the plugin off and on, Roon Bridge's own update.

**Phase 27** (releases built on GitHub, ADR-0173) is in 1.12.1, on Stable
with 1.13.0. **Left:** a
card flashed from 1.12.1's image (criterion 4: the card below), then R2D2's
pi-gen container (8.9 GB) and build images (2.9 GB) removed (decision 3).

**Phase 28** (Plexamp and Beszel from the catalogue, ADR-0174) is on Stable
with 1.13.0:
`gcarstoiu/gexis-beszel` 0.21.1-1 and `gcarstoiu/gexis-plexamp` 0.5.1
(gexis-plugins #13-#17, merged by George), catalogue serial 8; sofapi runs
the branch's last preview (`~/preview-ph28d`) with both carried over.
**Owed:** Plexamp played once on 0.5.1 (its engine's cache now
through a link) and George's look at the Plugins page, on sofapi; a card
from `image/deploy/2026-11-03-gexis-player-v1.12.1.img.xz` (also Phase 27's)
set up without Plexamp or Beszel, then updated to 1.13.0 (nothing
installed, *Add plugins* lists them), then reset to factory settings for
first use offering Plexamp from the catalogue. **Not built:** ADR-0174's
"found while reading" setup fix - part 2 switches ours on without adding
them to the Plugins page's list (`plugin_store.ADDED`).

**Phase 29** (room correction for the bass, ADR-0175) **on Stable with
1.16.1**. **Not yet:** the cuts read from CamillaDSP while music plays, the
level against a meter, two sweeps' agreement at 60 dB, the stage's cost,
the A/B bit-exactness. **Copy to confirm** with George: the lines the design
has no state for (`design/IMPLEMENTED-DIFFERENTLY.md`, Phases 29 and 30).

**Open, small:** a preview's download still holds the skin packs (1.1 of
1.2 GB) though `release.yml` excludes them; `gen_personalise.py` out of step since Phase 23;
the mocked Settings → Display showed two *Screen port* rows
(`screen_port`, `screen_port_info`), not yet looked at on a player.

**Phase 23, AirPlay 2** (`ph-airplay`), in every release since 1.9.0 and on
Stable with 1.10.0, marked *Limited testing* (no Apple device yet).
[ADR-0167](docs/decisions/0167-airplay-2-as-a-plugin.md) accepted; the
adapter is `gcarstoiu/gexis-airplay` (local copy `~/projects/gexis-airplay`).
**Open:** the test with an Apple device (to-do `ph23-test`), then T1-T9 to
George and the tag removed.

**Phase 22, multiroom for every source**, on Stable with 1.10.0
([ADR-0166](docs/decisions/0166-multiroom-for-every-source.md)). **Open:**
the measurement session (at 192 kHz the bar lost sync over Wi-Fi); the Home
Assistant integration's join and unjoin (its `multiroom` branch, `9744bb3`),
released after the player's; Lyrion-app grouping back and forth with the
player's.

**The players** (2026-11-10): sofapi on the preview of 1.16.0's code
(`~/preview-ph30b`; its 10 Nov measurement reads as bass-only), *Pages from
Home Assistant* on, Plexamp 0.5.1 and Beszel from the catalogue;
`rpi-eeprom-update` reports a bootloader update available, not applied (not
looked into). Roon's extension enabled in George's Roon; the other three last
seen on 1.9.1 through their updaters (2026-10-29). All four on Testing, which
offers 1.16.1. sofapi and the bar grouped; AirPlay on at sofapi and guestpi.
Each has its own Lyrion server.

**The test venv imports the core from `~/projects/gexis-player-next`** (an
editable install): in another worktree run the suite with `PYTHONPATH=src`
from its `core/`, or it tests `next`'s code. **A preview is built on GitHub**
(`gh workflow run release.yml -f ref=<branch> -f kind=preview`, then `gh run
download <run> --name packages`): the whole set of one commit, which a preview
of core needs (the player meta-package pins it exactly).

**Deferred until a bug report** (George, 2026-10-21): a first start after a
screen change may miss full-screen (the HMTECH 10.1"; to-do
`first-start-fullscreen`).

**Open:**
- **Not checked:** iOS's handling of `interactive-widget` (the mini player
  on the phone's keyboard); Android's is.
- **The visualiser made cheaper, the rest left** (Finding 134; George,
  2026-10-22: stop here): the needle and spectrum skins are unchanged - the
  present itself and the vendored engines' drawing (to-do `viz-cheaper`).
- **Glass** (foonerd's Rust PeppyMeter, Finding 133) is **Phase 36**
  (`ph-glass`, George 2026-11-13): a finding first (Glass as released, a
  fork of ours, or our own engine), then an ADR. The PeppyMeter,
  PeppySpectrum and peppy_screensaver forks we pin were archived on
  2026-10-04; every pinned download from foonerd's repositories still matched
  its checksum on 2026-11-13 (130).

**The Home Assistant integration**: `gcarstoiu/gexis-player-homeassistant`
0.6.0 (local `~/projects/gexis-player-homeassistant`, tests on
`~/projects/ha-venv`). **HACS's default list**: hacs/default#12691 waits for
HACS's maintainers - do not ask them for a review (their template).

**Phase 30** (room correction for the full range, ADR-0177, Finding 144)
**on Stable with 1.16.1**, Full range marked *Limited testing* (George).
**Now:** George's run at the full range on sofapi. **Owed:** the stage's cost
at 44.1/96/192 kHz; acceptance 2 as a finding from a run checked at Full
range. Layouts are checked with made-up data in
`~/projects/scratch/ph30/harness` (`WT` names the worktree). Phase 34 next
for room correction, research first; whether more positions help is checked
there (George).

**Phase 31** (internet radio without Lyrion, `ph-radio`) **started
2026-11-13**: ADR-0180 accepted; settings in ADR-0022. **mpv measured
2026-11-13** (Finding 146): confirmed. **The core built 2026-11-14** on
`ph-radio` (worktree `~/projects/gexis-player-radio`; what the build settled
is in ADR-0180's *The core, built*): directory, favourites, mpv as
`gexis-radio.service`, `/stations` routes, logos through the player,
settings, packaging. **The design arrived 2026-11-14** (`design/source/31/`;
its PNGs and per-artboard markup in `~/projects/scratch/ph31/design`);
George's answers in ADR-0180 (as drawn; an added station keeps playing;
logos through the player; six limits in ADR-0022). **The screens built
2026-11-14** on `ph-radio` (CI green at 439ac897): the panel, the bars, the
phone, Settings and first use, each checked against its artboards with
invented stations (`~/projects/scratch/ph31/harness`, `WT` names the
worktree; the screenshots in its `out/`). **Next:** the public documents'
Radio sections; the Home Assistant integration (favourites as sources, the
media browser, the card's Radio view, C01–C06), released after the
player's; a preview on a player not in a group (sofapi's `output` feeds the
group's loopback): the rate at the card, the stage, 32 kHz, CPU, an hour. **Done 2026-11-14**
([Finding 147](docs/findings/147-internet-radio-through-the-real-chain.md)):
sofapi ungrouped, the preview of 439ac89 installed (mpv with it), measured,
grouped again with the bar; the preview **stays installed on sofapi** for
George's regression pass (`~/preview-ph31`, the packages only). Acceptance 7
waits on George (4.8-7.0 % of a core through the real chain).

**Phase 35** (a page from Home Assistant, ADR-0176 as amended) **on Stable
with 1.16.1**, with the integration's 0.6.0. **Not yet on a player:** the
heat take-down, a USB keyboard's key, one page replacing another, the switch
turned off while a page is up; acceptance 4 (192 kHz with room correction).

**A multi-agent review** of everything since 0.10.2 runs on a read-only
worktree at v1.16.1 (`~/projects/gexis-review`, George 2026-11-10): ten
reviewers, each finding checked by an independent refuter, then explained to
George by severity; **fixes only after his go**. Remove the worktree when it
is done.

Phases and their IDs: `docs/DEVELOPMENT.md`. MPD parked (ADR-0151). **Raspberry
Pi Imager** (ADR-0159, a task): Imager's own list stays open as it is
(George, 2026-10-24).

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-11-10, after 1.16.1.**

## Phases

Closed: 0-21 and 24-26 (13 with letters a-f). Phases are numbered
consecutively without letters, each with a stable ID (George, 2026-10-13).
On Stable with work open: 22 (multiroom), 23 (AirPlay 2, limited testing),
27 (releases built on GitHub; a card still to flash) and 28 (Plexamp and
Beszel to the catalogue), both with 1.13.0. 29 (room correction for the
bass), 30 (the full range) and 35 (a page from Home Assistant) on Stable with
1.16.1, work open. **31 started 2026-11-13** (internet radio, ADR-0180
accepted); then 32-34 and 36 (Glass, added 2026-11-13); MPD parked. `docs/DEVELOPMENT.md`
holds each phase's acceptance criteria.

## Machines

| Name | What it is |
|---|---|
| R2D2 | Dev machine. CachyOS, **fish shell** (use `bash -c` for loops). Docker `data-root` `/home/docker`. Claude builds here; George flashes. |
| sofapi, the bar (ShelvesPi), guestpi, bedroompi | Test players, Pi 4 (bedroompi: the Waveshare 10.1" DSI-TOUCH-A, Phase 17). Reached by SSH key as `pi`; host keys in `~/projects/scratch/known_hosts`. |
| rig | Pi 4 reference for Findings 002-004. Not a test target. |
| LMS server | George's Lyrion server, for manual tests. CI must never depend on it. |

## Things that will bite

The full list, with how each was found, is in the archive (2026-10-12 block).

- **Building or releasing: read `docs/BUILD-TRAPS.md` first** (moved
  there from here, 2026-10-29).

**On the players**
- **DSD silence is the byte `0x69`**, not zero; never play `/dev/urandom` or
  zeros as DSD - at Fixed it reaches the amplifier at full scale.
- **Uploaded plugins run as systemd dynamic users, which the system bus
  refuses** on our image: what a plugin needs from the system goes through
  the core (`announce`, ADR-0142).
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
- **Plexamp restores its queue on every start** - anything that starts it
  outside `plexamp.service` bypasses `plexamp-start-idle` (from ADR-0174:
  outside its plugin, which clears it first).
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
