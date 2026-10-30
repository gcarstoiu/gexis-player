# Handoff

Last updated: 2026-10-30 (on R2D2).

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

**Current release: 1.9.1 on Testing, 1.7.0 on Stable** (2026-10-29:
Testing serial 60 read back with a good signature; Stable serial 11). 1.9.1
carries the two multiroom changes previewed on 2026-10-28: another group
shown and joined whole, and a source leads once it plays. PR #89 merged by
George (2026-10-29). Image `image/deploy/2026-10-29-gexis-player-v1.9.1.img`
(149 checks passed); build output `~/projects/gexis-release-out/r1.9.1`. A
release worktree needs its pi-gen submodule initialised before `make
image`.
**Before the next Stable promotion, remind George** (his request,
2026-10-28; to-do `ph22-eq-check`): a group heard in sync with the
equaliser on at one player only. 1.8.0 plays such a player about 46 ms late
(lesson 85); the fix, `c913bdc6`, is in 1.9.0 and 1.9.1 (not yet heard).
**Stable waits for the catalogue's release** (George, 2026-10-29): the
promotion comes after it, heard then, in one session with the two
measurements (to-dos `ph22-measure`, `eq-measure`).
**R2D2's `/` fills up**: Docker's containerd store keeps images on `/`, not
in `/home/docker`, and pi-gen rebuilds its 1.16 GB build image on every
image build, about 1.7 GB at a build's peak; check `df -h /` before one
(4.1 GB free on 2026-10-29, after the clean-up).
**Now: Phase 24, the plugin catalogue** (`ph-plugin-catalogue`), brought
forward with themes (25) before room correction (now 26 and 27), which still
cannot be auditioned (George, 2026-10-29).
[ADR-0168](docs/decisions/0168-a-plugin-catalogue.md) accepted the same day
(George's seven answers, each as recommended; no setting). Plan step 1
done: `gcarstoiu/gexis-plugins` public, GPL-3.0-or-later (local copy
`~/projects/gexis-plugins`; ADR-0168, *Built*); its main has a ruleset
(pull requests, the listing check required; the admin merges a tools change
past it). Steps 2 and 3, the core and the screens, built on
`ph-plugin-catalogue` (worktree
`~/projects/gexis-player-ph-plugin-catalogue`), checked from mocked data
(`~/projects/scratch/ph24`: `run.sh` with `catalogue_layout.py` and
`shots.py`), not yet on a player. George confirmed or changed their choices
the same evening (ADR-0168, *Confirmed and changed*): the notice before a
first install only, and a restore all in one go - both built. **The
catalogue key exists** (ADR-0168, *The catalogue key*): R2D2 keeps the
subkey in `~/projects/gexis-catalogue-key`; the master and revocation
certificate wait in `~/projects/gexis-catalogue-key-for-george` until
George has them, then that folder is deleted. **Step 4 done** (2026-10-30;
ADR-0168, *The first listing on a test player*): the samples
(`gcarstoiu/gexis-sample-plugins`, local copy
`~/projects/gexis-sample-plugins`) installed, updated, restored, withdrawn
and blocked on sofapi; `gexis-plugins` #1-#9 merged; **serial 4 published**
(both samples withdrawn; `tools/publish.sh`,
`GEXIS_CATALOGUE_GNUPGHOME=~/projects/gexis-catalogue-key`). The signature
is now `catalogue-<serial>.json.sig` (George, after GitHub's cache paired a
catalogue with the previous signature). The ADR's three measurements done.
Next: step 5, the public documents (manual, FAQ, README); then step 6,
George's tests on a preview and release 1.10.0. The samples left `tools/`
for that repository. The wiki Roadmap shows the new order (pushed
2026-10-29 with George's OK).
**Found in step 3, fixed apart**: on a phone the confirm, its progress card
and the update dialog sat half off the screen (since 1.7.0); branch
`fix-remote-dialogs` (worktree `~/projects/gexis-player-fix-remote-dialogs`),
merged into the phase branch, into `next` after George's test. **sofapi
runs the phase's preview** (`1.9.1+git26.81918c4` core and player,
`1.9.1+git25.1b14a2e` UI; files in `~/gexis-pc`), which carries the fix:
George's phone test of the dialogs can be done there.
**`fix-vite`** (worktree `~/projects/gexis-player-fix-vite`): Vite 8.3.3
for three Dependabot alerts on its development server (George); the built
UI compared with 8.3.0's, the same mocked screens pixel for pixel; into
`next` with the next release.

**Phase 23, AirPlay 2** (`ph-airplay`), in 1.9.0 and 1.9.1 on Testing,
marked *Limited testing* (no Apple device yet).
[ADR-0167](docs/decisions/0167-airplay-2-as-a-plugin.md) accepted; the
adapter is `gcarstoiu/gexis-airplay` (local copy `~/projects/gexis-airplay`).
**Open:** the test with an Apple device (to-do `ph23-test`), then T1-T9 to
George and the tag removed.

**Phase 22, multiroom for every source**, in 1.8.0 to 1.9.1 on Testing;
[ADR-0166](docs/decisions/0166-multiroom-for-every-source.md) all confirmed
by George (D7 amended 2026-10-28: a player with the equaliser on plays
earlier by CamillaDSP's hold, fixed in 1.9.0, not yet heard; decision 11 and
the lead taken only on play, in 1.9.1). **Open:** the
check by ear before the next Stable promotion (above); the measurement
session (at 192 kHz the bar lost sync over Wi-Fi; a card's own delay, USB or
optical, is measured there too); the Home Assistant integration's join and
unjoin (its `multiroom` branch, `9744bb3`), released after the player's;
back and forth between Lyrion-app grouping and the player's. The tests and
the build's story are in the archive (2026-10-28).

**The release key** moved to `~/projects/gexis-release-key` (George,
2026-10-24): every release command sets
`GEXIS_RELEASE_GNUPGHOME=~/projects/gexis-release-key`; the scripts default
to `~/.gnupg-gexis-release`, which no longer exists.

**The players** (2026-10-29): all four on 1.9.1 through their updaters, on
Testing (sofapi moved from Stable to Testing for it, George), dpkg clean;
sofapi since 2026-10-30 on the phase's preview (above), no catalogue
plugins installed, DevTools off; `~/gexis-pd` removed. sofapi and the bar grouped;
AirPlay on at sofapi and guestpi. Each has its own Lyrion server. The old
preview folders are gone (of those named, only `gexis-lead` and `gexis-pj`
were still there, on sofapi and the bar).

**The test venv imports the core from `~/projects/gexis-player-next`** (an
editable install): in another worktree run the suite with `PYTHONPATH=src`
from its `core/`, or it tests `next`'s code. **A preview of core needs the
player meta-package too** (it pins core exactly): `packaging/build.sh` with
every component and `player`, after copying the unchanged UI and system
packages from the release's build output (`repos/ours-*`).

**Deferred until a bug report** (George, 2026-10-21): a first start after a
screen change may miss full-screen (the HMTECH 10.1"; to-do
`first-start-fullscreen`).

**Release build output lives in `~/projects/gexis-release-out`**: in each
release worktree, `ln -s` it to `packaging/release/out` before `build.sh`
(excluded in `.git/info/exclude`). `reuse.py` reuses a published file only
against a local copy, so losing that folder means re-uploading every OS file.

**Open:**
- **Not checked:** iOS's handling of `interactive-widget` (the mini player
  on the phone's keyboard); Android's is.
- **The visualiser made cheaper, the rest left** (Finding 134; George,
  2026-10-22: stop here): the needle and spectrum skins are unchanged - the
  present itself and the vendored engines' drawing (to-do `viz-cheaper`).
- **Glass** (foonerd's Rust PeppyMeter, Finding 133): George, 2026-10-22,
  *"Glass is too young now"* - **remind him at the beginning of 2027** and
  measure it again (to-do `glass-revisit-2027`).

**The Home Assistant integration** (Phase 19, closed 2026-10-25):
`gcarstoiu/gexis-player-homeassistant` at 0.5.0 (2026-10-27: the card as the
phone remote, the equaliser's switch and setting, seeking, Fixed mute, the
app's registration fix; local copy
`~/projects/gexis-player-homeassistant`, tests on `~/projects/ha-venv`; a
Home Assistant 2026.10.3 in Docker, `~/projects/scratch/ha-test`). **HACS's
default list**: hacs/default#12691 (from George's fork `gcarstoiu/default`),
every automated check passed; it waits for HACS's maintainers - do not ask
them for a review (their template).

**Phases 20 and 21 closed 2026-10-27** (the archive has their state). Left
from Phase 20: the measurement through a card (to-do `eq-measure`, at a time
George picks).

Then 25-30 in order, each ADR first (`docs/DEVELOPMENT.md`, the IDs
there); MPD parked (ADR-0151). **Raspberry Pi Imager** (ADR-0159, a task):
Imager's own list stays open as it is (George, 2026-10-24).

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-10-29, after 1.9.1** (/home 220 -> 234 GB free, / 3.0 -> 4.1 GB).

## Phases

Closed: 0-21 (13 with letters a-f). Phases are numbered consecutively
without letters, each with a stable ID (George, 2026-10-13); 20 (the
equaliser) and 21 (the phone remote) closed 2026-10-27 with 1.7.0; 22
(multiroom) and 23 (AirPlay 2, limited testing) on Testing; 24 (the plugin
catalogue) being planned, then 25 (themes), 26-27 (room correction), 28-30;
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
