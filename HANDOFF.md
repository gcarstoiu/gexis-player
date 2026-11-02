# Handoff

Last updated: 2026-11-02 (on R2D2).

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

**Stable and Testing: 1.12.0** (2026-11-02; Testing serial 63, Stable
serial 13, promoted by George the same day; each read back with a good
signature): Phase 26, Roon, with three fixes (the visualiser's tap and the
updater's stop sending the panel token, ADR-0170 *Two callers missed*; the
row of sources under the library narrowed to fit), built on 1.11.0 (themes,
Phase 25, Testing serial 62; left a pre-release, as 1.9.1 was). Notes
approved by George; PRs #91 and #92 merged by George (2026-11-02). Image
`image/deploy/2026-11-02-gexis-player-v1.12.0.img` (160 checks passed);
build output `~/projects/gexis-release-out/r1.12.0`. The two measurements
are still owed (to-dos `ph22-measure`, `eq-measure`).

**R2D2's `/` fills up**: Docker's
containerd store keeps images on `/`, not in `/home/docker`, and pi-gen
rebuilds its 1.16 GB build image on every image build, about 1.7 GB at a
build's peak; check `df -h /` before one (4.6 GB free on 2026-11-02, after
the clean-up).

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

**Phases 25 (themes) and 26 (Roon) closed 2026-11-02** (George: satisfied
with Roon, nothing more measured; one release with everything). Roon's
plugin is `gcarstoiu/gexis-roon` (local `~/projects/gexis-roon`), 0.2.1
released with its asset and pinned in `packaging/roon/pins.sh`; Roon's
extension through Debian's `python3-roonapi`. **Left open** (ADR-0172,
*Built*): Roon took the output back eight seconds after Lyrion took it, the
cause not established (0.2.1 logs the pause's answer and the loopback's
states); not measured: bit-perfect, rates above 44.1 kHz, a group, the
plugin off and on, Roon Bridge's own update. sofapi runs preview packages
from `ph-roon` (in `~/gexis-pc`) and has the reboot marker set; the next
update reboots it once. **Next:** Phase 27, releases built on GitHub
(`ph-github-builds`, added by George 2026-11-02; ADR-0173 accepted, decisions
1-3), on its branch and worktree `~/projects/gexis-player-github-builds`. The
trial passed (Finding 140: v1.12.0 built on GitHub in 27 minutes, its OS
packages identical to r1.12.0's); next, the `inputs` mirror, then the release
workflow; then 28, room
correction for the bass. **Open, small:** `gen_personalise.py` out of step since Phase 23;
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

**The release key** moved to `~/projects/gexis-release-key` (George,
2026-10-24): every release command sets
`GEXIS_RELEASE_GNUPGHOME=~/projects/gexis-release-key`; the scripts default
to `~/.gnupg-gexis-release`, which no longer exists.

**The players** (2026-11-02): sofapi on preview packages from `ph-roon`
(core and system `1.11.0+git13.f93d3d2`, UI `1.11.0+git1.f946515`, Roon
0.2.1, in `~/gexis-pc`), its reboot marker set, Roon's extension enabled in
George's Roon; the other three last seen on 1.9.1 through their updaters
(2026-10-29). All four on Testing, which offers 1.12.0. sofapi and the bar
grouped; AirPlay on at sofapi and guestpi. Each has its own Lyrion server.

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

**The Home Assistant integration**: `gcarstoiu/gexis-player-homeassistant`
0.5.0 (local `~/projects/gexis-player-homeassistant`, tests on
`~/projects/ha-venv`). **HACS's default list**: hacs/default#12691 waits for
HACS's maintainers - do not ask them for a review (their template).

**Phases 20 and 21 closed 2026-10-27** (the archive has their state). Left
from Phase 20: the measurement through a card (to-do `eq-measure`, at a time
George picks).

Next, Phase 27 (releases built on GitHub, ADR-0173 accepted), then 28 (room
correction for the bass) and 29-32 in order, each ADR first
(`docs/DEVELOPMENT.md`, the IDs there); MPD parked (ADR-0151). **Raspberry
Pi Imager** (ADR-0159, a task): Imager's own list stays open as it is
(George, 2026-10-24).

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-11-02, after 1.12.0** (/home 214 -> 232 GB free, / 3.6 -> 4.6 GB).

## Phases

Closed: 0-21 and 24-26 (13 with letters a-f). Phases are numbered
consecutively without letters, each with a stable ID (George, 2026-10-13);
20 (the equaliser) and 21 (the phone remote) closed 2026-10-27 with 1.7.0,
24 (the plugin catalogue) 2026-10-31 with 1.10.0, 25 (themes) and 26
(Roon) 2026-11-02 with 1.11.0 and 1.12.0; 22 (multiroom) and 23 (AirPlay 2,
limited testing) on Stable with work open; next 27 (releases built on
GitHub), 28-29 (room correction), 30-32; MPD parked. `docs/DEVELOPMENT.md`
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
