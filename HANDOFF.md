# Handoff

Last updated: 2026-10-28 (on R2D2).

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

**Current release: 1.9.0 on Testing, 1.7.0 on Stable** (2026-10-28:
Testing serial 59 read back with a good signature; Stable serial 11). 1.9.0
carries Phase 23 (AirPlay 2, marked *Limited testing*) and the group-latency
fix; **PR #88 (`release-1.9.0` into `main`) open, for George to merge** - do
not push `next` while its checks run. Release worktree
`~/projects/gexis-player-r190`; image
`image/deploy/2026-10-28-gexis-player-v1.9.0.img` (149 checks passed); build
output `~/projects/gexis-release-out/r1.9.0`. 1.8.0's story is in the
archive (2026-10-28). A release worktree needs its pi-gen submodule
initialised before `make image`.
**Before the next Stable promotion, remind George** (his request,
2026-10-28; to-do `ph22-eq-check`): a group heard in sync with the
equaliser on at one player only. 1.8.0 plays such a player about 46 ms late
(lesson 85); the fix, `c913bdc6`, is in 1.9.0 (not yet heard): promote 1.9.0,
not 1.8.0, once it is heard. On sofapi the fixed core is installed
(`1.8.0+git18.66947eb`) and not yet running: restart `gexis-core` there
before the check, once nobody is playing.
**R2D2's `/` fills up**: Docker's containerd store keeps images on `/`, not
in `/home/docker`, and pi-gen rebuilds its 1.16 GB build image on every
image build; check `df -h /` before one (1.9 GB free after 1.8.0's, 213 MB at its lowest while pi-gen rebuilt).
**Now: Phase 23, AirPlay 2** (`ph-airplay`, closed as a branch) - in 1.9.0
on Testing, marked *Limited testing*: released before it is tried, no Apple
device yet (George, 2026-10-28). [ADR-0167](docs/decisions/0167-airplay-2-as-a-plugin.md)
accepted. Shairport Sync 5.6.2 and NQPTP 1.2.9 are built by us
(`packaging/shairport-sync`, `packaging/nqptp`); the adapter is
`gcarstoiu/gexis-airplay` (local copy `~/projects/gexis-airplay`). **Open:**
the test with an Apple device (to-do `ph23-test`), then T1-T9 to George and
the tag removed. The build's story is in the archive (2026-10-28, evening).

**Phase 22, multiroom for every source**, in 1.8.0 and 1.9.0 on Testing;
[ADR-0166](docs/decisions/0166-multiroom-for-every-source.md) all confirmed
by George (D7 amended 2026-10-28: a player with the equaliser on plays
earlier by CamillaDSP's hold, fixed in 1.9.0, not yet heard). **Open:** the
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

**The players** (2026-10-28, evening): sofapi and guestpi on Phase 23's
preview builds - guestpi the last (`1.8.0+git19.14fd6b9`, the same content
as 1.9.0), sofapi with a newer core installed but not yet running (restart
it before the group check, once nobody plays); AirPlay switched on on both.
The bar and bedroompi on Phase 22's preview 13 (1.8.0's packages). Each has
its own Lyrion server. Bring them to 1.9.0 through the updater (Testing).

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
- George's look at the moon before sunrise.

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

Then 23-30 in order, each ADR first (`docs/DEVELOPMENT.md`, the IDs
there); MPD parked (ADR-0151). **Raspberry Pi Imager** (ADR-0159, a task):
Imager's own list stays open as it is (George, 2026-10-24).

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-10-28, after 1.9.0** (/home 220 -> 234 GB free, / 826 MB -> 1.9 GB).

## Phases

Closed: 0-21 (13 with letters a-f). Phases are numbered consecutively
without letters, each with a stable ID (George, 2026-10-13); 20 (the
equaliser) and 21 (the phone remote) closed 2026-10-27 with 1.7.0; 22
(multiroom) and 23 (AirPlay 2, limited testing) on Testing, 24-30 to come, MPD parked. `docs/DEVELOPMENT.md` holds each phase's acceptance criteria.

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
