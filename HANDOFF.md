# Handoff

Last updated: 2026-11-01 (on R2D2).

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

**Current release: 1.10.0 on Testing and Stable** (2026-10-31: Testing
serial 61, Stable serial 12, each read back with a good signature; the image
downloaded through the README's link, its checksum matching). PR #90 merged
by George (2026-11-01). 1.10.0 carries Phase 24 (the plugin catalogue, one
store for every plugin, plugins that ask for more), the fixes from George's
two tests on 2026-10-31, the phone dialogs' fix and Vite 8.3.3. Image
`image/deploy/2026-10-31-gexis-player-v1.10.0.img` (152 checks passed);
build output `~/projects/gexis-release-out/r1.10.0`. Stable was promoted
without the two measurements (George; to-dos `ph22-measure`, `eq-measure`).
**R2D2's `/` fills up**: Docker's containerd store keeps images on `/`, not
in `/home/docker`, and pi-gen rebuilds its 1.16 GB build image on every
image build, about 1.7 GB at a build's peak; check `df -h /` before one
(4.7 GB free on 2026-11-01, after the clean-up).

**Phase 24, the plugin catalogue, closed 2026-10-31** with 1.10.0
(`docs/DEVELOPMENT.md`; its story is in the archive). The catalogue is
`gcarstoiu/gexis-plugins` (local copy `~/projects/gexis-plugins`; published
with `tools/publish.sh` and
`GEXIS_CATALOGUE_GNUPGHOME=~/projects/gexis-catalogue-key`), at serial 5:
TV remote (HDMI-CEC) 0.1.1 listed (#12), its source public at
`gcarstoiu/gexis-tv-remote` (local copy `~/projects/gexis-tv-remote`;
ADR-0170, *Published and listed*); the samples
(`gcarstoiu/gexis-sample-plugins`) withdrawn. The catalogue key's master
and revocation certificate still wait in
`~/projects/gexis-catalogue-key-for-george` until George has them, then
that folder is deleted. **Not yet seen on a player:** the visualiser's
window put back after a real drop of the TV's output (ADR-0147, *Amended
2026-10-31*); the store on a bar; a new player's setup writing its plugin
record, and Remove with *Keep* off for one of ours (ADR-0169). George's
phone test of the dialogs is still owed (to-do `fix-remote-dialogs-test`).
The mocked-screen checks (`~/projects/scratch/dpad`, `~/projects/scratch/ph24`)
build from `~/projects/gexis-player-next` unless `WT` names another worktree.

**Now: Phase 25, themes** (`ph-themes`, worktree
`~/projects/gexis-player-themes`, pushed up to the ADR; local since), started
2026-11-01. [ADR-0171](docs/decisions/0171-themes.md) accepted (George: six
themes built in, one per player, the row in Display with Deep Teal the
default). **Built, not yet on a player**: the design's rule as
`ui/src/lib/themeRule.js`, `ui/scripts/themes.mjs` writing `themes.css`
(checked against the design by the build); today's colours and corners
through tokens - Deep Teal pixel-identical on 101 mocked screens (panel at
the 10", 7" and TV sizes, bar, phone); the monos from fontsource; a core test
against new literals. The harness: `~/projects/scratch/ph25/` (`run.sh`,
`capture.py`, `compare.py`; `THEME`, `COVER`, `EQ` for the mocked core; do
not edit `run.sh` while a capture runs). The equaliser stays as the rule
gives it on the light themes, and the idle screen keeps today's look
(George, 2026-11-01). **Open**: a preview on
sofapi, after George's OK; `gen_personalise.py` out of step since Phase 23
(the first-use page's header says so).

**Also now: Phase 26, Roon** (`ph-roon`, worktree
`~/projects/gexis-player-roon`), started 2026-11-01 (George).
[ADR-0172](docs/decisions/0172-roon.md) accepted: Roon Bridge as a plugin
(fetched on switch-on, Roon's own updates, a user of its own), through a
third `snd-aloop` card into `pcm.output`, Now Playing by Roon's extension API.
Roon over AirPlay already plays since 1.10.0 (classic AirPlay; Roon's
*Compatibility mode*; FAQ on `fix-roon-airplay`).

**Phase 23, AirPlay 2** (`ph-airplay`), in every release since 1.9.0 and on
Stable with 1.10.0, marked *Limited testing* (no Apple device yet).
[ADR-0167](docs/decisions/0167-airplay-2-as-a-plugin.md) accepted; the
adapter is `gcarstoiu/gexis-airplay` (local copy `~/projects/gexis-airplay`).
**Open:** the test with an Apple device (to-do `ph23-test`), then T1-T9 to
George and the tag removed.

**Phase 22, multiroom for every source**, in every release since 1.8.0 and
on Stable with 1.10.0;
[ADR-0166](docs/decisions/0166-multiroom-for-every-source.md) all confirmed
by George; he found the group in sync before the promotion (2026-10-31).
**Open:** the measurement session (at 192 kHz the bar lost sync over Wi-Fi;
a card's own delay, USB or optical, is measured there too); the Home
Assistant integration's join and unjoin (its `multiroom` branch,
`9744bb3`), released after the player's; back and forth between Lyrion-app
grouping and the player's. The tests and the build's story are in the
archive (2026-10-28).

**The release key** moved to `~/projects/gexis-release-key` (George,
2026-10-24): every release command sets
`GEXIS_RELEASE_GNUPGHOME=~/projects/gexis-release-key`; the scripts default
to `~/.gnupg-gexis-release`, which no longer exists.

**The players** (2026-11-01): sofapi on the themes preview (core
`1.10.0+git9.da56e56`, UI and player `1.10.0+git12.a36666b`, from
`ph-themes`: the idle screen keeping today's look, George) with
`tv-remote` 0.1.1, DevTools off, its preview packages in `~/gexis-pc`; the
other three on 1.9.1 through their updaters (2026-10-29); all four on
Testing, where 1.10.0 is offered. sofapi and the bar grouped; AirPlay on at
sofapi and guestpi. Each has its own Lyrion server.

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

After themes, Roon (26), then 27-31 in order, each ADR first
(`docs/DEVELOPMENT.md`, the IDs there); MPD parked (ADR-0151). **Raspberry
Pi Imager** (ADR-0159, a task): Imager's own list stays open as it is
(George, 2026-10-24).

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-11-01, after 1.10.0** (/home 218 -> 233 GB free, / 3.7 -> 4.7 GB).

## Phases

Closed: 0-21 and 24 (13 with letters a-f). Phases are numbered
consecutively without letters, each with a stable ID (George, 2026-10-13);
20 (the equaliser) and 21 (the phone remote) closed 2026-10-27 with 1.7.0,
24 (the plugin catalogue) 2026-10-31 with 1.10.0; 22 (multiroom) and 23
(AirPlay 2, limited testing) on Stable with work open; 25 (themes) in
progress, then 26 (Roon), 27-28 (room correction), 29-31; MPD parked. `docs/DEVELOPMENT.md`
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
