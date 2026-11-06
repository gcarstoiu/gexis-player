# Handoff

Last updated: 2026-11-06 (on R2D2).

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

**Testing: 1.14.0** (2026-11-06, serial 66): room correction for the bass
(Phase 29), with the kernel 6.18.60 and Mesa 26.2.6 from the Raspberry Pi
archive. Built by run 42261893617 (`verify-image.sh` all 151 checks passed,
as 1.13.0), signed on R2D2; the channel, each part, the notes and the history
read back good. Notes approved by George. **Release PR #96 for George to
merge**; do not push `next` until its checks have finished. The API page's
deploy timed out in GitHub Pages' queue and passed on a re-run.

**Stable: 1.13.0** (promoted by George 2026-11-06, serial 14; on Testing
since 2026-11-03, serial 65): Plexamp and Beszel from the catalogue (Phase
28), on 1.12.1 (releases built on GitHub). Read back with a good signature;
the image downloaded through README's link, its checksum and signature good.
README names 1.13.0 (reaches `main` with #96). The two measurements are
still owed (to-dos `ph22-measure`, `eq-measure`).

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

**In progress: Phase 29**, room correction for the bass, **on Testing
with 1.14.0** (2026-11-06, George; `ph-room-correction` merged into `next`,
worktree `~/projects/gexis-player-room-correction`). ADR-0175: cuts only, below 250 Hz, towards a
gentle rise below 80 Hz, in the equaliser's stage; three positions (George,
2026-11-05, over five; most of them decide a cut, not any one), 60 dB at the
seat, each speaker alone, a tap and a 3 s countdown at each, the check (Skip allowed)
waiting for the tap too, a 10-minute timeout; A/B a saved switch; the UMIK-1
only, **its 90° file given from the phone** (decision 4 changed 2026-11-05:
miniDSP has no API, its terms forbid automated tools, and the microphone
gives no serial over USB). Claude Design's design is `design/source/29`
(George kept its proposals and new copy). **Built and tested on mocks**:
`room_dsp` (numpy), `room_correction`, `room_run`, `room_mic`,
`room_control`, the stage's 16 cut slots, the routes, the screens
(`ui/src/screens/room/`), the manual, FAQ, technical guide, hardware page
and README; layouts checked with made-up data (`~/projects/scratch/ph29/harness`).
**On sofapi** (George's UMIK-1, a USB-C unit): George's first full run
(2026-11-05, five positions at 50 dB) gave the three decisions above, and
showed the output left at 100 % after a run - the level before kept as the
shown percentage (fixed: the DAC's own level, put back through the bridge;
read back from the DAC on sofapi after a cancel, a restart mid-run and the
next run, Lesson 93). Then (George, 2026-11-05): cuts as deep as the target
takes, stacked where one is not enough; both speakers swept together, shown
as a third tab, never cut; boosts stay out (decision 2). sofapi holds the
cuts recalculated from three of the first run's positions. **Not yet:** the
cuts read from CamillaDSP while music plays (only readable then), a full run
at three positions with both, the level against a meter, two sweeps'
agreement at 60 dB, the stage's cost, the A/B bit-exactness. **Copy to confirm** with George:
the lines the design has no state for (`design/IMPLEMENTED-DIFFERENTLY.md`,
Phase 29).

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

**The release key** moved to `~/projects/gexis-release-key` (George,
2026-10-24): every release command sets
`GEXIS_RELEASE_GNUPGHOME=~/projects/gexis-release-key`; the scripts default
to `~/.gnupg-gexis-release`, which no longer exists.

**The players** (2026-11-06): sofapi on Phase 29's last preview
(`gexis-core`, `gexis-player` and `gexis-ui` 1.13.0+git34 from `0f566c6b`),
Plexamp 0.5.1 and Beszel from the catalogue; `rpi-eeprom-update` reports a bootloader update
available, not applied (not looked into). Roon's extension enabled in
George's Roon; the other three last seen on 1.9.1 through their updaters
(2026-10-29). All four on Testing, which offers 1.14.0. sofapi and the bar
grouped; AirPlay on at sofapi and guestpi. Each has its own Lyrion server.

**The test venv imports the core from `~/projects/gexis-player-next`** (an
editable install): in another worktree run the suite with `PYTHONPATH=src`
from its `core/`, or it tests `next`'s code. **A preview is built on GitHub**
(`gh workflow run release.yml -f ref=<branch> -f kind=preview`, then `gh run
download <run> --name packages`): the whole set of one commit, which a preview
of core needs (the player meta-package pins it exactly).

**Deferred until a bug report** (George, 2026-10-21): a first start after a
screen change may miss full-screen (the HMTECH 10.1"; to-do
`first-start-fullscreen`).

**Release build output lives in `~/projects/gexis-release-out`**: link it to
`packaging/release/out` in the checkout `publish.sh` runs from (git-ignored;
remove the link after). Since ADR-0173 `reuse.py` reads the published
indexes, not these copies; George had the older releases' copies removed
(2026-11-04), 1.13.0's kept.

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

After Phase 29: 30 (room correction for the full range) and 31-33 in order,
each ADR first
(`docs/DEVELOPMENT.md`, the IDs there); MPD parked (ADR-0151). **Raspberry
Pi Imager** (ADR-0159, a task): Imager's own list stays open as it is
(George, 2026-10-24).

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-11-04, after 1.13.0.**

## Phases

Closed: 0-21 and 24-26 (13 with letters a-f). Phases are numbered
consecutively without letters, each with a stable ID (George, 2026-10-13).
On Stable with work open: 22 (multiroom), 23 (AirPlay 2, limited testing),
27 (releases built on GitHub; a card still to flash) and 28 (Plexamp and
Beszel to the catalogue), both with 1.13.0. 29 (room correction for the
bass) in progress, on Testing with 1.14.0; next 30, then 31-33; MPD parked. `docs/DEVELOPMENT.md`
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
