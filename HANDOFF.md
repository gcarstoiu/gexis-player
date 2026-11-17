# Handoff

Last updated: 2026-11-16 (on R2D2).

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

**Testing and Stable: 1.17.0** (2026-11-16; Testing serial 73, Stable
serial 17): internet radio (Phase 31), after George's regression pass and his
look at the touchpad fix on sofapi; release run 43842724641, `verify-image.sh`
all checks passed; PR #104 merged by George. Promoted the same day at his
word: both channels read back with a good signature, `releases/latest` is
r1.17.0 (its checksum matches, its signature is there, the image 1.15 GB).
**PR #105 for George**: README's *Download and install* still names 1.16.4 on
`main`. After its merge: `main` into `docs` and `next`, `readme-1.17.0`
deleted.

**go-librespot is upstream's build of `775ba5883`** (ADR-0181), kept in the
`inputs` mirror with its source; `packaging/check-upstream.sh` reports it
waiting until a release contains the commit, which then replaces it by the
usual route. **ADR-0182 in `main`** (PR #103, merged by George 2026-11-16): `.github/workflows/upstream.yml` runs
`packaging/upstream-daily.sh` daily (a bump branch, its PR, tests and a
preview; an issue for what is not pinned here), `packaging/upstream-bump.py`
moves a pin, the steps and checklists in `docs/tech/updates-and-releases.md`.
**Owed by George:** *Allow GitHub Actions to create and approve pull
requests* is off, so its first PR would fail; the ADR's *Claude's choices*.
Its first run will open an issue for Beszel (0.21.1, 0.21.2 is out).

**Spotify on the lead through a group change** (George, 2026-11-15: it
should keep playing): a group change stops go-librespot, which ends the
cast. [ADR-0183](docs/decisions/0183-spotify-keeps-playing-on-the-lead-through-a-group-change.md)
**proposed**: pause it, rewrite, resume (go-librespot reopens its device on
resume with the ALSA configuration read afresh); not built until George
accepts it.

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
  stage's cost, the A/B bit-exactness. **George heard it thin (2026-11-17,
  [Finding 151](docs/findings/151-room-correction-thins-the-voice-range.md)):**
  each speaker cut alone took 5.5-10 dB from what is heard together at
  80-190 Hz; cuts designed from the *Both* sweeps would not (predicted).
  George chose those (ADR-0175's amendment, with the research behind it),
  and a kept measurement redesigned at start. Built on `room-both`
  (f471bc63); its preview, with Phase 32's, from `preview-library-room`,
  on sofapi since 2026-11-17 (core and player 1.17.0+git47.faf38e6, UI
  git42.f471bc6): its measurement redesigned at start, six cuts the same
  on both, *Not checked*. Owed: George's listening, the bass rise judged by
  ear.
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

**The Home Assistant integration's 0.7.0 released 2026-11-16** (George:
released before Phase 32, the card's group built now; then released at his
word without his look from HACS): internet radio (the favourites as
sources, the directory in the media browser, `gexis.radio_favourite`, the
card's Radio view), join and unjoin, and the card's group as the phone's
(ADR-0163 C8-C14; `gexis.set_group_volume`, `gexis.mute_group`). `main`
fast-forwarded to `019fe0f`, tagged and released (*Latest*); the pre-release
0.7.0b1 and the branches `radio`, `multiroom`, `release-0.7.0` deleted.
**Not yet seen in a real Home Assistant:** acceptance 8 (favourites from the
sources and the card; the media browser's browsing and search), join and
unjoin, the card's group - checked from mocked entities only
(`~/projects/scratch/ha-0.7.0/card`, `run.sh`). Harnesses:
`~/projects/scratch/ph31/card`, `ph31/harness`, `ph30/harness` (`WT` names
the worktree).

**Open, small:** a preview's download still holds the skin packs (1.1 of
1.2 GB) though `release.yml` excludes them; `gen_personalise.py` out of step since Phase 23;
the mocked Settings → Display showed two *Screen port* rows
(`screen_port`, `screen_port_info`), not yet looked at on a player.

**The players** (2026-11-16): **sofapi** on the preview of `next` at
b8a76991 (run 43838072189: gexis-core and gexis-player 1.16.4+git33,
gexis-ui and gexis-system 1.16.4+git31.9fdd26e), installed idle, core
restarted and up. The other three on the preview branch
`preview-radio-mdns` (deleted 2026-11-16, merged) at 8897a71e (1.16.4 and
`ph-radio`; gexis-core and gexis-player 1.16.4+git31, go-librespot
775ba58-4; run 43725073814), installed idle, cores restarted. All four on
Testing, which now offers 1.17.0 (not yet installed on any); room correction
on at sofapi; each has its own Lyrion
server. Lyrion stops on a player that leaves its sync (Lyrion's own); the
screen now keeps Lyrion as the source.

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

**BedroomPi and GuestPi cannot reach each other** (2026-11-14, George asked
why GuestPi was missing from BedroomPi's menu): the home network, not the
player. Each is on a different access point of the mesh; nothing sent from
one straight to the other arrives, over IPv4 or IPv6, before and after
BedroomPi's reboot, while multicast does - so each hears the other announced,
its status request times out. Every other pair answers. A group with only
those two would fail the same way. **Now each lists the other through
ShelvesPi** (ADR-0136 item 5, George chose it: *Can't group from here*, no
Join), seen on the players. On those two a list opening waits 2 s, up to 4 s
behind a background look, for the fresh answer; the kept list shows
meanwhile. Masked probes in
`~/projects/scratch/ph31/dbg/` (`reach.py`, `link.py`, `seen.py`).

Phases and their IDs: `docs/DEVELOPMENT.md`. MPD parked (ADR-0151). **Raspberry
Pi Imager** (ADR-0159, a task): Imager's own list stays open as it is
(George, 2026-10-24).

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-11-16, after 1.17.0**: the closed phases' notes moved to the archive
(HANDOFF 2,633 words to about 2,000). Still owed: `docs/LESSONS.md` (5,183
words) cut back; the start-of-session set is about 9,400 words.

## Phases

Closed: 0-31 and 35 (13 with letters a-f); 22, 23, 27-31 and 35 on
2026-11-16 (George, with 1.17.0 on Stable), what each left above. Phases are
numbered consecutively without letters, each with a stable ID (George,
2026-10-13). **In progress: 32**, the library answers for itself
(`ph-library`, George 2026-11-16, after the integration's 0.7.0):
[ADR-0184](docs/decisions/0184-plex-information-through-plexamps-claim.md)
**accepted** for acceptance 1 (George, 2026-11-16): Plexamp's claim lent by
the plugin through a new contract event, held in memory only; backups as
Plexamp's claim; its local server; Plex only where Plexamp is installed and
claimed; *Information from Plex* (on) beside Plexamp in Sources, in ADR-0022.
George agreed (2026-11-16) to the measurements on his library (acceptance
3-5): counts and timings only, no names, track listings or screenshots. U1 read from Plexamp 4.13.2's code
(`~/projects/scratch/ph32/plexamp-4.13.2`): `server:identifier` and
`@Plexamp:resources` (each server's connections and own token) in its
settings store. **Built 2026-11-16, covers first, not yet on a player:**
gexis-plexamp 0.6.0 on its branch `library` (lends the library from
Plexamp's files; the *Information from Plex* row in its manifest; 122 tests)
and the core on `ph-library` (worktree `~/projects/gexis-player-ph-library`):
the contract's `library` event, added within version 1; `plex.py` (held in
memory, one album index, the `plex-release` provider first, covers through
`/plex/cover/<key>/<stamp>`); the row greyed until the plugin reports a
claim; the visualiser asks the core for a cover named by its path (AirPlay's
too). 3,549 core tests pass. ADR-0184 *As built*. **On sofapi since 2026-11-17** (George's
go-ahead): the core, system and player packages of `ph-library`
(`1.17.0+git22.f0bee53`), and plugin 0.6.0 put in by the core's own
installer, its origin left as the catalogue's (0.5.1 kept as the previous
version); the library lent and taken, the row on and not greyed.
[Finding 149](docs/findings/149-plex-covers-as-built.md), counts only: 3,539
of LMS's 4,823 albums matched by name, a cover in 54-81 ms, 2 s for a host
that does not answer, no token or address in the logs. **Second step built 2026-11-17** (George: the
cover sweep asks Plex first; go on with artist pictures and biographies; he
expected popular tracks there too, and they are - sorted by `ratingCount`,
as Plexamp's DJ asks): ADR-0184's second step, `ph-library` 60796813 -
`plex-artist` (biography, picture, similar, popular) first in the chain and
on the artist page, ahead of LMS's own plugin; both sweep buttons ask Plex
first, stored apart (`plex-artist`, `plex-album` notes) so fanart's stay
behind it. 3,565 core tests pass. **On sofapi since 2026-11-17** (George's
go-ahead): core and player `1.17.0+git31.6079681` (preview run
44025601946), the sweep run once.
[Finding 150](docs/findings/150-plex-artists-and-sweep-as-built.md), counts
only: Plex's picture and biography on the page of every artist it holds by
name, *Popular* rows for 12 of 13 of them; 1,177 of 1,719 matches by the
lead artist only; after the sweep, Plex's picture on 556 of 948 artists and
169 of 270 sampled covers. George confirmed both calls of the second step
(Plex ahead of LMS's plugin; the portraits sweep too). **Owed:** his answer
on a collaboration's page, put back to him (the internet sources already
give the lead artist's biography there, so Plex-only would change nothing
but the label; ADR-0184); a Plex
picture on now-playing seen live; then MusicBrainz-id matching, lyrics
(acceptance 6) and 7's decisions. The catalogue lists 0.6.0 with the release that carries it, by
its `player` field.
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
