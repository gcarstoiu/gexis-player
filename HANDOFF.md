# Handoff

Last updated: 2026-11-24 (on R2D2).

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

**Testing and Stable: 1.18.2** (2026-11-21; Testing serial 76, Stable
serial 19, both read back with a good signature; released without a preview
at George's word): timed lyrics first (ADR-0184 items 7-10), the room's two
held fixes (`fix-room-grouped-after-undo`, `fix-room-screens`), first use's
AirPlay tag, the upstream watch of Shairport Sync and NQPTP. Squeezelite is
-4 (BUILD-TRAPS; `packaging/revisions.json` with it). PR #110 merged by
George 2026-11-21; `main` into `docs` and `next`. AirPlay stays *Limited
testing*. The
integration's **0.7.1** (the card's transport under the cover at 345 px and
under) released 2026-11-21 as Latest. Plugin catalogue serial 9.

**Phase 37, room measurement reworked** (`ph-room-measurement`, worktree
`~/projects/gexis-player-room`;
[ADR-0187](docs/decisions/0187-room-measurement-reworked-setup-check-five-positions-timing-mark.md)
accepted 2026-11-20): a setup check, five positions around the head, a
timing mark on every sweep. **George's two runs of 2026-11-23** on the
research builds: [Finding 158](docs/findings/158-room-measurement-five-positions-on-sofapi.md)
(the head at half the weight and the finer bass detail kept) and
[Finding 159](docs/findings/159-room-measurement-timing-marks-on-sofapi.md)
(D3's heights, 52 dB: D4 proven in the bass, both confirmed; from 2 kHz the
pair played reads 1-3 dB under the added, unexplained; above the bass the
check names places 3-5 worse, corrections following the microphone's
place; the level reading moved 0.9 dB with the head placed again). **George
decided the together sweeps go** (2026-11-23), built: both added from each
speaker's sweeps by their marks, the check's head playing a pair and
logging the gap (`sets` in the run's state, the phone's rows following;
`ph-room-measurement` e5799dc4); the start screen says about 20 minutes
(George, the same day).
Both runs' responses deleted here and on sofapi; the text results stay in
`~/projects/scratch/ph37/run/` (scripts in `check/`, `d4/`).
**The branch** = `next` + `room-checks` + `room-chart` + five positions +
the new design + George's notes (the distance step lit, the check's *of
4*, the chart's *Each position* switch, drawing C) + the timing mark and
the distance step's lead + the together sweeps gone; the manual, technical
guide and API updated; the manual's room picture still to be retaken.
**Decided from mock-ups and built the same day** (George; mock-ups in
`~/projects/scratch/ph37/variants/sheet/`): each speaker's tab the speaker
alone in the bass too, with a line in the legend (ADR-0186 D4-D5; `room-chart`
f4fcdd37 merged, 99652be9), and **the speaker check** as its own step 3 of 5
- whistles at the head for distance, wiring and level, left and right at 2,
a list with *Check again* / *Measure*, a swap or crossed wire waiting for
*Check again*, the louder speaker turned down by a CamillaDSP `Gain`
(ADR-0187 D1-D2, C1-C2, as built; ca235a95; ADR-0022 [H] for both, confirmed).
Tested in the made-up room only.
**Decided from a canvas of mock-ups and built the same evening** (George:
A, B, B): **the speakers aligned on their own**
([ADR-0188](docs/decisions/0188-speakers-aligned-on-their-own.md): a
*Speakers* card with its own switch, its delay and level heard with room
correction on or off, *Check the speakers* running the check alone - *Keep*,
or after a measurement it leaves behind *Keep and measure* - and an amber
note on room correction's card until measured again); **the ringing** as a
small card after the check and **a card per dip** on the correction
(ADR-0187 D7-D8; C6, C7 and C9 computed and logged); `ph-room-measurement`
d71d7110. The canvas (private, George's) also holds the panel's and the bar's
screens for the switch (ADR-0188 C6), not built until George has seen them.
**George's answers (2026-11-24):** the dips' wording as built; ADR-0022's
four entries appended; the panel and bar to be built as drawn; the preview
installed. **sofapi** runs it (core, player and UI 1.18.2+git30.d71d711,
run 45262635911, installed 2026-11-24 06:43 at George's word, the core
restarted): its measurement's 0.23 ms delay came across as the speakers'
alignment, switched on; no level stored (`right_db` none).
**The panel and the bar built as drawn** (2026-11-24, 3d65d70e: the two
switches named side by side, the stale note in the last measurement's card,
*Measure or check, from your phone*); its preview builds on GitHub, not
installed. **Next:** George tries the speaker check and a run on the preview; the manual's room picture retaken; Phase 37's acceptance 5.
**Before Phase 37 closes** (George, 2026-11-21; acceptance 5): the level at
the seat against a meter, and the equaliser's and multiroom's measurements
through the amplifiers - George present for each.

**Room work held for Phase 37's release** (George, 2026-11-21; the two
finished fixes went out in 1.18.2): `room-checks` (0aee0318, ADR-0185
D1-D3, amended by ADR-0187: D1's check moves into the setup check);
`room-chart` (ADR-0186; D4's edits uncommitted in its worktree, on hold; its
full-Both preview, run 44606811416, never to be installed).

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
1.2 GB) though `release.yml` excludes them.

**sofapi runs hot** (2026-11-21): 78 °C with no page; a Home Assistant page with one camera was closed for the heat twice (Finding 157). ADR-0176 P8 kept as it is; George is bringing the temperature down.

**The players** (2026-11-24): **sofapi** on Phase 37's preview
(core 1.18.2+git30.d71d711, 1.18.2 with Phase 37's branch;
go-librespot 0.10.7-4, Shairport Sync 5.6.3-1), room correction on, a USB
isolator on its DAC's cable, in no group since the group test of 21 Nov. On 23 Nov its DAC fell
silent after the install while sofapi showed the stream running; a USB
replug brought it back (Lesson 98, cause open). That DAC's own PCM filter
was *Filter off* through the 23 Nov measurements, which plays it quieter;
George set *Sharp roll-off* on 24 Nov. **shelvespi** on
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
2026-11-21, after 1.18.2** (#110): the five merged branches and
`release-1.18.2` deleted here and on GitHub; the 1.12.1 card image (1.1 GB)
and 1.16 GB of dangling images removed; the ADR index complete, ADR-0182,
0184 and 0185 brought to 1.18.2; the repository scan clean. Earlier the same
day: LESSONS.md cut to 4,948 words, HANDOFF trimmed, seven worktrees and
R2D2's pi-gen machinery (about 9 GB) removed.

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
