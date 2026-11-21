# Handoff

Last updated: 2026-11-21 (on R2D2).

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

**Testing: 1.18.1** (2026-11-21, serial 75; PR #109 merged by George,
bringing in #108): Spotify keeps playing on the lead through a group change
(ADR-0183, A; a join's pause 1.77 s on sofapi, accepted by George) and
go-librespot 0.10.7 in place of ADR-0181's development build - Spotify only
(George, 2026-11-21: the room fixes wait for Phase 37's release). 1.18.0
(2026-11-18, serial 74) brought Phase 32, the bass from both speakers
together, the Wi-Fi rescan fix and Shairport Sync 5.6.3. **Stable: 1.18.1**
(serial 18, promoted 2026-11-21 at George's word; both channels read back
with a good signature, `releases/latest` is r1.18.1 with its signed image).
George found the bass from both speakers and a Spotify group good by ear;
the play from an Apple device (Shairport Sync 5.6.3 and Phase 23's test) was
closed by George without being done, so AirPlay stays marked *Limited
testing* until one is. The plugin catalogue (serial
9) lists gexis-plexamp 0.6.0 (lowest release 1.18.0) and gexis-beszel
0.21.2-1.

**Phase 37, room measurement reworked** (`ph-room-measurement`;
[ADR-0187](docs/decisions/0187-room-measurement-reworked-setup-check-five-positions-timing-mark.md)
accepted 2026-11-20): a setup check, five positions around the head (placed
by eye), a timing mark on every sweep; the head's weight and finer bass
detail kept only if the data shows them better. **First step, on sofapi**:
the research build `ph37-research` (af7d1134, never released: five
positions, each sweep's deconvolved response kept in
`/var/lib/gexis/room-research/`, never a recording), installed 2026-11-20
14:29 at George's word, with his consent to keep the responses and copy them
(about 30 MB) to `~/projects/scratch/ph37/`; both copies deleted after the
analysis. **Waiting: George's run at five positions** (the speaker cables
back the right way if still swapped from 19 Nov). **Do not update sofapi to
1.18.1 before it**: that replaces the research build (its *Updates* is not
Automatic, so the night only checks). Then `~/projects/scratch/ph37/check/analyse.py
<run>.json` (`PYTHONPATH=<worktree>/core/src`): C5 and D5 judged on the
check's re-placed positions, the ringing (C6), the joint over-cut (C7), the
level readings (C2); a finding; the run's logs for ADR-0185 C4 and C8.

**Room work held for Phase 37's release** (George, 2026-11-21):
`fix-room-grouped-after-undo` (f175b600: the room asks for a group, not its
chain) and `fix-room-screens` (c2059ac6, ADR-0185 D4), not yet seen live; `room-checks` (0aee0318, ADR-0185
D1-D3, amended by ADR-0187: D1's check moves into the setup check);
`room-chart` (ADR-0186; D4's edits uncommitted in its worktree, on hold; its
full-Both preview, run 44606811416, never to be installed).
`preview-1.18.1-room` holds them all. `upstream-shairport-nqptp` (Shairport
Sync and NQPTP watched) was on the 1.18.1 preview, not released: it goes
with the next release PR.

**ADR-0182 in `main`**: `.github/workflows/upstream.yml` runs
`packaging/upstream-daily.sh` daily (a bump branch for a part packaged here,
an issue otherwise). *Allow GitHub Actions to create and approve pull
requests* on since 2026-11-18 (George). **Owed by George:** the ADR's
*Claude's choices*.

**The plugin catalogue** (Phase 24, closed 2026-10-31):
`gcarstoiu/gexis-plugins` (local `~/projects/gexis-plugins`; `tools/publish.sh`
with `GEXIS_CATALOGUE_GNUPGHOME=~/projects/gexis-catalogue-key`), serial 9
(2026-11-18): TV remote 0.1.1, Plexamp 0.6.0, Beszel and its hub 0.21.2-1;
its pull requests are George's to merge, or Claude's at his word (#18). The catalogue key's master and revocation
certificate wait in `~/projects/gexis-catalogue-key-for-george` until George
has them. Not yet seen on a player: the visualiser back after a real drop of
the TV's output; the store on a bar; setup writing a plugin record; Remove
with *Keep* off (ADR-0147, ADR-0169). George closed the phone test of the
dialogs and the 31 October fixes unchecked (2026-11-21; both in every release
since 1.10.0). The mocked-screen checks
(`~/projects/scratch/dpad`, `ph24`, `ph26/sources`, `ph26/blog`) build from
`~/projects/gexis-player-next` unless `WT` names another worktree.

**Roon** (Phase 26, closed): `gcarstoiu/gexis-roon` (local
`~/projects/gexis-roon`) 0.2.1, pinned in `packaging/roon/pins.sh`. **Left
open** (ADR-0172, *Built*): Roon took the output back eight seconds after
Lyrion took it, the cause not established (0.2.1 logs the pause's answer
and the loopback's states); not measured: bit-perfect, rates above 44.1 kHz,
a group, the plugin off and on, Roon Bridge's own update.

**Phases 22, 23, 27 to 31 and 35 closed 2026-11-16** (George, with 1.17.0
on Stable): what each left is in its *Closed* paragraph in
`docs/DEVELOPMENT.md` and on the to-do list; the list as it stood is in the
archive (2026-11-21).

**The Home Assistant integration's 0.7.0** (released 2026-11-16 at George's
word): internet radio, join and unjoin, the card's group. **Seen by George
in his Home Assistant 2026-11-21: all good.**

**Open, small:** a preview's download still holds the skin packs (1.1 of
1.2 GB) though `release.yml` excludes them; `gen_personalise.py` out of step since Phase 23;
the mocked Settings → Display showed two *Screen port* rows
(`screen_port`, `screen_port_info`), not yet looked at on a player.

**The players** (2026-11-21): **sofapi** on Phase 37's research build (core,
player and UI 1.18.0+git22.af7d113, which carries all of the 1.18.1 preview;
go-librespot 0.10.7-4, Shairport Sync 5.6.3-1), room correction on, a USB
isolator on its DAC's cable, in no group since the group test of 21 Nov. **shelvespi** on
1.18.0. **guestpi** and **bedroompi** not read since 18 Nov. All on Testing,
which offers 1.18.1. AirPlay on at guestpi only; sofapi's Plexamp library
lent, its Beszel agent 0.21.2-1. Each has its own Lyrion server. Lyrion
stops on a player that leaves its sync (Lyrion's own).

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
0.7.0 (local `~/projects/gexis-player-homeassistant`, tests on
`~/projects/ha-venv`). **HACS's default list**: hacs/default#12691 waits for
HACS's maintainers - do not ask them for a review (their template).

**BedroomPi and GuestPi cannot reach each other** (2026-11-14): the mesh,
not the player - each is on a different access point and nothing sent
straight between them arrives. Each lists the other through ShelvesPi
(*Can't group from here*, ADR-0136 item 5). Probes in
`~/projects/scratch/ph31/dbg/`.

Phases and their IDs: `docs/DEVELOPMENT.md`. MPD parked (ADR-0151). **Raspberry
Pi Imager** (ADR-0159, a task): Imager's own list stays open as it is
(George, 2026-10-24).

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-11-21, after 1.18.1**: `spotify-group-change` removed (its worktree,
here and on GitHub; GitHub removed `release-1.18.1` and
`bump-go-librespot-0.10.7` itself); HANDOFF brought to the current state, the
finished blocks moved verbatim to the archive; then, at George's word,
`bump-go-librespot-0.10.6` and `preview-1.18.1` deleted. Still owed: `docs/LESSONS.md` (5,272 words) cut back.

## Phases

Closed: 0-31 and 35 (13 with letters a-f); 22, 23, 27-31 and 35 on
2026-11-16 (George, with 1.17.0 on Stable), what each left above. Phases are
numbered consecutively without letters, each with a stable ID (George,
2026-10-13). **In progress: 37**, room measurement
reworked (above). **32** (the library answers for itself) closed 2026-11-21
(George, with 1.18.1 on Stable); left: ADR-0184's amendment (timed lyrics
first) on `fix-lyrics-timed-first` (43de3d8b; 3,608 core tests pass),
previewed on sofapi after George's room run, which keeps the research build
until then. Then 33 (Lyrion's own menus: the look), 36 (Glass,
a finding first); MPD parked. 34 (room correction in time) closed
2026-11-21 without being built (George, on Finding 155). `docs/DEVELOPMENT.md` holds each phase's
acceptance criteria.

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
