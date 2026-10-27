# Handoff

Last updated: 2026-10-27 (on R2D2).

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

**Current release: 1.7.0, on Stable** (promoted 2026-10-27 at George's
word: Stable serial 11, Testing serial 57, both read back with good
signatures; r1.7.0 is GitHub's latest; the public `gexis-player.img.xz`
through `releases/latest/download` passes its checksum and signature and
decompresses to the checked image). 1.7.0 carries Phases 20 and 21 (the
equaliser, the phone remote, mute with Fixed volume); PR #85 merged by George
the same day. README's current release: PR #86, merged by George the same day; `main`
merged into `docs` and `next`, its branch and worktree gone. Image
`image/deploy/2026-10-27-gexis-player-v1.7.0.img`; build output
`~/projects/gexis-release-out/r1.7.0`. The release's detail is in the
archive (2026-10-27, 1.7.0).
**R2D2's `/` fills up**: Docker's containerd store keeps images on `/`, not
in `/home/docker`, and pi-gen rebuilds its 1.16 GB build image on every
image build; check `df -h /` before one (1.9 GB free after 1.7.0's).
**Now: Phase 22, multiroom for every source** (`ph-multiroom`, started
2026-10-27; George moved multiroom, then AirPlay 2, before room correction,
which cannot be tried yet: 22-25 are now multiroom, AirPlay 2, room
correction for the bass, for the full range).
[ADR-0166](docs/decisions/0166-multiroom-for-every-source.md) proposed the
same day from George's nine answers (one group, Lyrion's sync for Lyrion,
Snapcast for every other source and plugin; the shortest delay; the source's
rate); Claude's C1-C6 for his confirmation; the wiki Roadmap shows the new
order (pushed with his OK). **Next:** his word on the ADR,
then the design brief for the grouping (Claude Design), then the build.
The wiki Roadmap shows Phases 20 and 21 done and the Harmony Hub ideas
(pushed 2026-10-27 with his OK).

**The release key** moved to `~/projects/gexis-release-key` (George,
2026-10-24): every release command sets
`GEXIS_RELEASE_GNUPGHOME=~/projects/gexis-release-key`; the scripts default
to `~/.gnupg-gexis-release`, which no longer exists.

**The players**: sofapi core 1.7.0, ui and player `1.7.0+git5.5596698`
(2026-10-27); ShelvesPi 1.5.0; bedroompi `preview-1023` as last recorded.

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

**Phases 20 (the equaliser) and 21 (the phone remote) closed 2026-10-27**
(George, with 1.7.0's promotion; `docs/DEVELOPMENT.md` has what each
criterion rests on). `ph-equaliser` is gone (in `main`). The remote's laptop
background (5596698e) was merged into `next` after 1.7.0 (222edb08), so
`ph-phone-controls` and its worktree stay until the next release takes it to
`main` (ROUTINE-CLEANUP). Left from Phase 20: the measurement through a card
(to-do `eq-measure`, at a time George picks). Mocked-data checks:
`~/projects/scratch/ph21` (`run2.sh`, `remote_shots2.py`, `run_manual2.sh`)
and `~/projects/scratch/hacard` (`run.sh`, the card).

Then 22-30 in order, each ADR first (`docs/DEVELOPMENT.md`, the IDs
there); MPD parked (ADR-0151). **Raspberry Pi Imager** (ADR-0159, a task):
Imager's own list stays open as it is (George, 2026-10-24).

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-10-27, after 1.7.0** (/home 220 -> 235 GB free).

## Phases

Closed: 0-21 (13 with letters a-f). Phases are numbered consecutively
without letters, each with a stable ID (George, 2026-10-13); 20 (the
equaliser) and 21 (the phone remote) closed 2026-10-27 with 1.7.0; 22
(multiroom) in progress, 23-30 to come, MPD parked. `docs/DEVELOPMENT.md` holds each phase's acceptance criteria.

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
