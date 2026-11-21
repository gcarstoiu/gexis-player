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

**Testing and Stable: 1.18.1** (Testing serial 75, Stable serial 18,
promoted 2026-11-21 at George's word; both read back with a good signature).
AirPlay stays *Limited testing* (no Apple device's play; closed by George).
Plugin catalogue serial 9 (gexis-plexamp 0.6.0, gexis-beszel 0.21.2-1).

**Waiting for the next release** (branches from `next`, pushed, no
worktree): `fix-lyrics-timed-first` (ADR-0184 items 7-10; preview on sofapi
after George's room run), `fix-first-use-tag` (AirPlay's tag over its name
at 390 px), `upstream-shairport-nqptp`, and Phase 37's room work below. The
integration's `fix-card-narrow` (the transport under the cover at 345 px and
under) is for a 0.7.1 at George's word.

**Phase 37, room measurement reworked** (`ph-room-measurement`;
[ADR-0187](docs/decisions/0187-room-measurement-reworked-setup-check-five-positions-timing-mark.md)
accepted 2026-11-20): a setup check, five positions around the head (placed
by eye), a timing mark on every sweep; the head's weight and finer bass
detail kept only if the data shows them better. **First step, on sofapi**:
the research build `ph37-research` (af7d1134, never released), installed
2026-11-20 at George's word; it keeps each sweep's deconvolved response in
`/var/lib/gexis/room-research/` (never a recording), copied with George's
consent to `~/projects/scratch/ph37/`, both copies deleted after the
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
requests* on since 2026-11-18 (George). The ADR's *Claude's choices*
confirmed by George 2026-11-21.

**The plugin catalogue**: `gcarstoiu/gexis-plugins` (local
`~/projects/gexis-plugins`; `tools/publish.sh` with
`GEXIS_CATALOGUE_GNUPGHOME=~/projects/gexis-catalogue-key`), serial 9; its
pull requests are George's to merge, or Claude's at his word. The key's
master and revocation certificate wait in
`~/projects/gexis-catalogue-key-for-george` until George has them. The
mocked-screen checks (`~/projects/scratch/dpad`, `ph24`, `ph26/sources`)
build from `~/projects/gexis-player-next` unless `WT` names a worktree.

**Roon** (Phase 26, closed): `gcarstoiu/gexis-roon` (local
`~/projects/gexis-roon`) 0.2.1, pinned in `packaging/roon/pins.sh`. **Left
open** (ADR-0172, *Built*): Roon took the output back eight seconds after
Lyrion took it, the cause not established (0.2.1 logs the pause's answer
and the loopback's states); not measured: bit-perfect, rates above 44.1 kHz,
a group, the plugin off and on, Roon Bridge's own update.

**Open, small:** a preview's download still holds the skin packs (1.1 of
1.2 GB) though `release.yml` excludes them; `tools/design/gen_personalise.py`
out of step since Phase 23 (retire it or bring it in step: ADR-0149's, for
George).

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

**The Home Assistant integration**: `gcarstoiu/gexis-player-homeassistant`
0.7.0, seen by George 2026-11-21 (local `~/projects/gexis-player-homeassistant`, tests on
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
2026-11-21, after 1.18.1**; the same evening at George's word: LESSONS.md
cut to 4,948 words (eight rules shortened, their cases already in the
archive), HANDOFF trimmed, seven clean worktrees removed (`ph37` and
`roomchart` kept).

## Phases

**In progress: 37**, room measurement reworked (above). Then 33 (Lyrion's
own menus: the look) and 36 (Glass, a finding first); MPD parked. Closed:
0-32, 34 and 35 - 32 on 2026-11-21 with 1.18.1 on Stable, 34 the same day
without being built (Finding 155). Each phase has a stable ID; what a closed
phase left is in its *Closed* paragraph in `docs/DEVELOPMENT.md` and on the
to-do list.

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
