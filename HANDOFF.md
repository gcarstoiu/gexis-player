# Handoff

Last updated: 2026-11-18 (on R2D2).

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

**Testing: 1.18.0** (2026-11-18, serial 74; PR #107 merged by George):
Phase 32 (information from the Plex library first, ADR-0184), room
correction's bass from both speakers together (ADR-0175's amendment,
Finding 151), a group's gaps over Wi-Fi fixed (Finding 154: the core's
Wi-Fi-name read let nmcli rescan every ~43 s), Shairport Sync 5.6.3.
**Stable: 1.17.0** (serial 17). The plugin catalogue (serial 9) lists
gexis-plexamp 0.6.0 (lowest release 1.18.0) and gexis-beszel 0.21.2-1.
**Owed by George on 1.18.0:** Plex's lyrics seen on screen; his listening
to the bass from both speakers; his ear in a Spotify group (after the fix
the gaps could not be reproduced: the access point had moved shelvespi to
another, where a scan costs no audio); a play from an Apple device
(Shairport Sync 5.6.3, with `ph23-test`). Then Stable at his word.

**Next: 1.18.1** (George, 2026-11-18): go-librespot 0.10.7 (the daily job's
`bump-go-librespot-0.10.7`; 0.10.6 contains ADR-0181's commit, so our
development build goes) and **ADR-0183, accepted** (A: Spotify on the lead
paused, the chain rewritten under it, resumed; `spotify-group-change`
3759f835, `rechain.keep_spotify_playing`, 3,605 core tests pass), with
`upstream-shairport-nqptp` (Shairport Sync and NQPTP watched). All three on
`preview-1.18.1` (from `next`; the inputs list's conflict resolved to
Shairport 5.6.3 and go-librespot 0.10.7), preview run 44408717854, **on
sofapi since 2026-11-18 23:16** (George's go-ahead; core 1.18.0+git6, player
git13, go-librespot 0.10.7-4; idle, core clean, the group kept). Then George with his phone: go-librespot's checklist
(`docs/tech/updates-and-releases.md`) and ADR-0183's (a join and a leave
under Spotify on the lead: the music back, the phone keeps the player and
the position, the gap timed; the phone's Pause and Next still reach the
player; the follower in time; the equaliser on at the lead). GitHub Actions
may now open and approve pull requests (George, 2026-11-18; read back).

**ADR-0182 in `main`**: `.github/workflows/upstream.yml` runs
`packaging/upstream-daily.sh` daily (a bump branch for a part packaged here,
an issue otherwise). *Allow GitHub Actions to create and approve pull
requests* on since 2026-11-18 (George). **Owed by George:** the ADR's
*Claude's choices*.

**Spotify on the lead through a group change** (George, 2026-11-15: it
should keep playing): a group change stops go-librespot, which ends the
cast. [ADR-0183](docs/decisions/0183-spotify-keeps-playing-on-the-lead-through-a-group-change.md)
**proposed**: pause it, rewrite, resume (go-librespot reopens its device on
resume with the ALSA configuration read afresh); not built until George
accepts it.

**The plugin catalogue** (Phase 24, closed 2026-10-31):
`gcarstoiu/gexis-plugins` (local `~/projects/gexis-plugins`; `tools/publish.sh`
with `GEXIS_CATALOGUE_GNUPGHOME=~/projects/gexis-catalogue-key`), serial 9
(2026-11-18): TV remote 0.1.1, Plexamp 0.6.0, Beszel and its hub 0.21.2-1;
its pull requests are George's to merge, or Claude's at his word (#18). The catalogue key's master and revocation
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

**Phases 22, 23, 27 to 31 and 35 closed 2026-11-16** (George, with 1.17.0
on Stable). Each one's *Closed* paragraph in `docs/DEVELOPMENT.md` says what
was left, and the to-do list carries it; their full notes are in the archive
(2026-11-16).
- **22, multiroom**: the measurement session (at 192 kHz the bar lost sync
  over Wi-Fi); Lyrion-app grouping back and forth with the player's.
- **23, AirPlay 2** (*Limited testing*): the test with an Apple device
  (to-do `ph23-test`), then T1-T9 to George and the mark removed.
- **27 and 28**: a card flashed from
  `image/deploy/2026-11-03-gexis-player-v1.12.1.img.xz`, set up without
  Plexamp or Beszel, updated, then reset for first use offering Plexamp; then
  R2D2's pi-gen container (8.9 GB) and build images (2.9 GB) removed.
  Plexamp played once on 0.5.1 and George's look at the Plugins page, on
  sofapi. ADR-0174's setup fix (`plugin_store.ADDED`) not built.
- **29, the bass**: not measured - the cuts read from CamillaDSP while music
  plays, the level against a meter, two sweeps' agreement at 60 dB, the
  stage's cost, the A/B bit-exactness. Heard thin by George (Finding 151);
  the cuts now designed from both speakers together, in 1.18.0. Owed:
  George's listening, the bass rise judged by ear.
- **A hum with the touch cable in** (sofapi, 2026-11-17): causes, tests and
  remedies in `docs/HARDWARE.md`; George's tests come first.
- **30, the full range** (*Limited testing*): George's run at Full range on
  sofapi; the stage's cost at 44.1/96/192 kHz; acceptance 2 as a finding.
  Phase 34 next for room correction, research first.
- **31, internet radio**: the follower's Stop on a follower running 1.17.0
  (to-do `ph31-regression-fixes`). `core/tests/test_main_order.py` reads
  `main()` for a name used before it is assigned (LESSONS 19).
- **35, a page from Home Assistant**: not yet on a player - the heat
  take-down, a USB keyboard's key, one page replacing another, the switch
  turned off while a page is up; acceptance 4 (192 kHz with room
  correction).

**The Home Assistant integration's 0.7.0** (released 2026-11-16 at George's
word): internet radio, join and unjoin, the card's group. **Not yet seen in a
real Home Assistant** (mocked entities only, `~/projects/scratch/ha-0.7.0/card`):
acceptance 8, join and unjoin, the card's group.

**Open, small:** a preview's download still holds the skin packs (1.1 of
1.2 GB) though `release.yml` excludes them; `gen_personalise.py` out of step since Phase 23;
the mocked Settings → Display showed two *Screen port* rows
(`screen_port`, `screen_port_info`), not yet looked at on a player.

**The players** (2026-11-18): **sofapi** and **guestpi** on 1.18.0's code
before its tag (core 1.17.0+git87, player git90, UI git86, system git22,
Shairport Sync 5.6.3-1; run 44391293146); **shelvespi** on 1.17.0 with the
Wi-Fi fix (core and player git65, run 44365618347); **bedroompi** on 1.17.0.
All on Testing, which offers 1.18.0. sofapi leads a group with shelvespi;
room correction on at sofapi, its Plexamp library lent, its Beszel agent
0.21.2-1 (uploaded); AirPlay on at guestpi only. Each has its own Lyrion
server. Lyrion stops on a player that leaves its sync (Lyrion's own).

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
2026-11-18, after 1.18.0**: five merged worktrees and six branches removed
(here and on GitHub); HANDOFF 3,232 words to about 1,950, the finished
blocks moved verbatim to the archive; ADR-0175's and ADR-0184's index rows
brought up to date; the repository scan clean, except that the home
network's name was not checked (reading it on a player was refused). Still
owed: `docs/LESSONS.md` (5,272 words) cut back; the start-of-session set is
about 9,500 words.

## Phases

Closed: 0-31 and 35 (13 with letters a-f); 22, 23, 27-31 and 35 on
2026-11-16 (George, with 1.17.0 on Stable), what each left above. Phases are
numbered consecutively without letters, each with a stable ID (George,
2026-10-13). **In progress: 32**, the library answers for itself
(`ph-library`, George 2026-11-16): ADR-0184's four steps (covers; the
artist, popular tracks and both sweeps; MusicBrainz ids; lyrics behind
LRCLIB's) in 1.18.0 on Testing, with gexis-plexamp 0.6.0; Findings 149,
150, 152 and 153, measured on George's library with his consent (counts
and timings only, no names, track listings or screenshots). Left: George
seeing Plex's lyrics on screen; the phase closes at his word.
Then 33 (Lyrion's own menus: the look), 34 (room correction in time,
research first), 36 (Glass, a finding first); MPD parked. `docs/DEVELOPMENT.md` holds each phase's
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
