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

**Current release: 1.6.0, on Stable** (2026-10-25; Testing serial 56,
Stable serial 10). PR #84 merged by George the same day; `main` merged into
`docs` and `next`, `release-1.6.0` and its worktree gone, the routine
clean-up run. Image `image/deploy/2026-10-25-gexis-player-v1.6.0.img`; build
output in `~/projects/gexis-release-out/r1.6.0`. The release's detail is in
the archive (2026-10-25, 1.6.0).

**1.7.0 on Testing, not promoted** (2026-10-27; George: both phases for
testing, Stable later; the notes, shortened at his word, approved by him).
Phases 20 and 21 merged into `next` (2c63fa87; core suite 2751 passed, 48
skipped; the UI builds); tag `v1.7.0` on the notes commit `81dd559d`. Image
`image/deploy/2026-10-27-gexis-player-v1.7.0.img`, built from the tag in
`~/projects/gexis-player-r170` (944 s; `verify-image.sh` 129 checks passed;
the skins check clean); parts `ours-db936235e357`, `rpi-668ab304bc41`
(Chromium 156, new), `skins-67e037cab00f`, `debian-2e90e264cb7d`; build
output `~/projects/gexis-release-out/r1.7.0`. Testing serial 57 read back,
good signature; Stable still 1.6.0, serial 10. gexis-core and gexis-player
`1.7.0`, gexis-ui `1.6.0+git74.913b105` (the preview's build). sofapi has
the release's core and player (core restarted 18:00, no warnings). **R2D2's
`/` was full** (80 MB): Docker's containerd store keeps images there, not
in `/home/docker`, and pi-gen rebuilds its 1.16 GB build image every time;
the first image build failed on it. George chose removing the two
Squeezelite test images; with the dangling images pruned, 1.9 GB free after
the build. **Next:** the release PR (George merges), then `main` into `docs`
and `next`, `release-1.7.0` and the worktree removed, the routine clean-up.

**The release key** moved to `~/projects/gexis-release-key` (George,
2026-10-24): every release command sets
`GEXIS_RELEASE_GNUPGHOME=~/projects/gexis-release-key`; the scripts default
to `~/.gnupg-gexis-release`, which no longer exists.

**The players** (2026-10-25; all four idle and clean at the clean-up):
sofapi 1.6.0; ShelvesPi 1.5.0; bedroompi `preview-1023` as last recorded.
sofapi since 2026-10-27: core and player 1.7.0, ui `1.6.0+git74.913b105`.

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
`gcarstoiu/gexis-player-homeassistant` at 0.4.1 (local copy
`~/projects/gexis-player-homeassistant`, tests on `~/projects/ha-venv`; a
Home Assistant 2026.10.3 in Docker, `~/projects/scratch/ha-test`). **HACS's
default list**: hacs/default#12691 (from George's fork `gcarstoiu/default`),
every automated check passed; it waits for HACS's maintainers - do not ask
them for a review (their template).

**Phase 20, the equaliser, on sofapi as a preview** (2026-10-26).
George, 2026-10-25: the three settings confirmed (ADR-0022), the design
handed over (`design/source/20`, look 3a), implement with the decisions left
to Claude recorded and shown to him, measure through a card after. Branch
`ph-equaliser` in `~/projects/gexis-player-ph-equaliser`, pushed:
go-librespot 0.10.5 and Beszel 0.21.1 (for this preview); the core
(`equaliser.py`, `eq_engine.py`, `eq_control.py`, `outputs.render(eq=True)`,
the routes, `equaliser` on `/state`, the Settings row); `gexis-camilladsp`
4.1.3 and `gexis-equaliser.service`, `snd-aloop` at boot; the UI
(`ui/src/screens/eq/`, the drawer, the bar's tray, the phone's mini
player); the documents. **George's try, 2026-10-26:** C1-C16 confirmed; D3
amended - the volume gives the lowering back, with the gentler top
(`volume.GiveBack`, only between the level and the control; the engine
gives it back on the quiet side of a change); no visualiser with the
equaliser on - Spotify's float, which the meter's 16-bit view cannot read
(Finding 138, *The meter and float*; lesson 82), mended by `output` taking
integers only; C17 (the note's wording) and C18 (a change is a short dip)
confirmed the same day. Core suite 2738 passed, 48 skipped; the note checked
from mocked data on every surface (`~/projects/scratch/eq-m2`:
`note_shots.py`, with eq-m1's `eq_layout.py`; the silent meter test
`meter_test.sh`). **On sofapi since 2026-10-26 10:50**, the equaliser off
as George left it: core `1.6.0+git18.09b35e4`, ui `1.6.0+git19.f3c8a9f`,
player `1.6.0+git20.8b3b945` (dry run first: 3 upgraded, nothing removed;
core and kiosk restarted, the panel on `index-0Jj3Qt9V.js`); system
`1.6.0+git13.6186a94`, camilladsp `4.1.3-1`, go-librespot `0.10.5-2`,
Beszel `0.21.1` from the first preview. **Not yet on the device:** the
give-back and the integer-only `output` with the equaliser on (switching it
on is George's setting to change: ask, or read back after he does). **Next:**
the measurement through sofapi's card (it plays through the amplifier: at a
time George picks), with the give-back's checks (ADR-0162 *Not yet done*);
the manual's drawer picture retaken with the demo library.

**Phase 21, the phone remote, being built** (2026-10-26; George: while he
tries Phase 20, two phases open). Branch `ph-phone-controls` in
`~/projects/gexis-player-ph-phone-controls`, from `ph-equaliser` with `next`
merged in. The design `design/source/21` (on `docs`; its Settings copy is
the repository's, as the bundle's had LAN addresses, and the bundle's
shared README was older than ours, so only its Phase 21 parts were taken).
[ADR-0164](docs/decisions/0164-the-phone-remote.md) accepted: George's
answers (both pads as drawn, the touchpad sending steps, so the pointer
leaves the phone; touch sizes as drawn; repeat cycles; the Home Assistant
card follows); Claude's C1-C14 for his confirmation (C12: Pointer speed and
style retired, ADR-0022, only once he confirms). **Built the same day**
(ADR-0164, *Built*), pushed: core suite 2745 passed, 48 skipped; checked from
mocked data against the design (`~/projects/scratch/ph21`: `remote_layout.py`
in `gexis-layout-core:1`, its `demo` flag for the manual's pictures from
the demo library; `remote_shots.py`, `variant_shot.py`, `typing_shot.py`
with `fake_panel.py`, in `gexis-layout:1`, on a `gexis-layout` network).
**On sofapi as a preview since 2026-10-26 21:19** (George asked for it;
sofapi idle; dry run first: 3 upgraded, nothing removed): core
`1.6.0+git50.18da13b`, ui `1.6.0+git49.b740c16`, player
`1.6.0+git50.18da13b` - Phase 20's too, the branch being built on it; the
other packages as Phase 20's preview left them (copied from its
`packaging/out` for the player's pins). Core and kiosk restarted, the panel
on `index-BhU4fWJL.js`, `/tmp/pv` removed. **George, the same evening:
Claude Design got the remote wrong.** **The second design came on
2026-10-27** (`Phone Remote v3`, imported on `docs`; v2 deleted, the
Settings copy still the repository's): the Trackpad drives the panel's
pointer again (ADR-0121's gestures, nothing drawn on the phone), the D-pad
the ring, no typing sheet, no shuffle or repeat on the phone, Fixed volume
as the panel's locked row with mute. ADR-0164 revised; George's answers the
same day: mute with Fixed volume where the output has a control
([ADR-0165](docs/decisions/0165-mute-with-fixed-output.md), the panel's
fixed rows too), the touch area giving way on phones under 780 px before
the page scrolls, the strips following the finger. Claude's C1-C13 for his
confirmation (C12 now keeps Pointer speed and style: nothing for ADR-0022);
**all confirmed by George the same day**.
**Rebuilt the same day** (ADR-0164, *Built (2026-10-27)*), pushed: core
suite 2751 passed, 48 skipped; checked from mocked data against the board
(`~/projects/scratch/ph21`: `run2.sh` / `batch2.sh` with `remote_shots2.py`
and `fake_panel2.py`, `run_manual2.sh` for the manual's pictures from the
demo library). **On sofapi as a preview since 2026-10-27 12:44** (sofapi
stopped; dry run first: 3 upgraded, nothing removed): core
`1.6.0+git60.3c5147e`, ui `1.6.0+git62.8367bb5`, player
`1.6.0+git63.6990a1d`; core and kiosk restarted, the panel on
`index-BfuMrj2Q.js`, no errors in the core's journal, `/tmp/pv` removed. The
first build's three debs are in `~/projects/scratch/ph21/first-build-debs`.
**George's findings the same day** (the EQ sheet to close with a swipe down;
Settings to show the remote's background) fixed on `ph-phone-controls`
(105f9bf4 UI, 48d64a91 docs and the manual's Settings picture), checked from
mocked data (`remote_shots2.py` modes `settings`, `swipe`; a `brightart`
flag for the contrast check), pushed; **on sofapi since 14:22** (stopped;
dry run: 2 upgraded, nothing removed): ui `1.6.0+git67.105f9bf`, player
`1.6.0+git68.48d64a9`, core unchanged; core and kiosk restarted, the panel on
`index-Bx9oVtwP.js`, no warnings, `/tmp/pv` removed; the rebuild's ui and
player debs in `~/projects/scratch/ph21/second-build-debs`. **George's next
two findings, the same afternoon**, his answers asked: the remote fills a
phone up to 480 px wide (C10 amended; his phone's browser is 427 px, and
the 412 px column left 7 px strips no dimming reached), and the touch area's
buttons (OK included) and both switches take the quick actions' ground
(the remote's `--remote-control-*` tokens dropped). 5c8235b9 UI, 6dcdeb93
docs (the four phone pictures retaken); checked from mocked data at 427,
412 and 800 wide (`remote_shots2.py` mode `edges`). **On sofapi since
14:57** while it played (George agreed; no restarts, the UI served from
disk): ui `1.6.0+git69.5c8235b`, player `1.6.0+git70.6dcdeb9`; the previous
pair in `~/projects/scratch/ph21/findings1-debs`. **George, the same
afternoon**: Settings' grey text over a bright cover kept as it is; the
wiki's Roadmap (Phase 21 under Now) pushed with his OK; **the EQ sheet's
switch without the box round it** (9fbbebf5, the manual's EQ picture
retaken; checked from mocked data at 427 and 360, `remote_shots2.py` mode
`eqpower`). **On sofapi since 15:55** (stopped; dry run: 2 upgraded,
nothing removed; no restarts): ui and player `1.6.0+git71.9fbbebf`; the
previous pair in `~/projects/scratch/ph21/findings2-debs`. Asked: whether
the panel's volume drawer, whose switch has the same box (Phase 20's
`EqQuick`), follows. **Then Settings, all of it, on the modals' solid grey**
(George; asked, the whole screen while it shows): `flat` on `Settings` and
`Equaliser`, a `--bg-panel` layer in `PhoneRemote` (0f1783cf, the manual's
Settings picture retaken; checked from mocked data at 427 and 800,
`remote_shots2.py` mode `flat`). **On sofapi since 16:15** (stopped; dry
run: 2 upgraded, nothing removed; no restarts): ui and player
`1.6.0+git72.0f1783c`; the previous pair in
`~/projects/scratch/ph21/findings3-debs`. **George's answers then**: the
panel's volume drawer loses its switch's box too (e5d09001 on
`ph-equaliser`, merged into `ph-phone-controls`; checked from mocked data,
the drawer Variable and Fixed, the bar's tray unchanged); a Settings
chooser's dimming stays below the top bar. **On sofapi since 16:37** (stopped;
dry run: 2 upgraded, nothing removed; the kiosk restarted for the panel,
no warnings): ui `1.6.0+git74.913b105`, player `1.6.0+git89.7f1b297`; the
previous pair in `~/projects/scratch/ph21/findings4-debs`. **The flaky
backup test fixed** on `fix-backup-test` (81415912: the upload test
compares the bytes it wrote; on Python 3.13, CI's, `gzip.compress` stamps
the second, so two calls a second apart differ; reproduced in
`python:3.13-slim` with a ticking clock, the old test failing and the new
passing), checks passed, merged into `next` (28c3f319) and `next` into
`ph-phone-controls`; its worktree `~/projects/gexis-player-fix-backup-test`
stays until the branch reaches `main` (ROUTINE-CLEANUP).
Rolling sofapi back to Phase 20's preview (core git18, ui git19, player
git20, in `ph-equaliser`'s `packaging/out`) only if George asks. Next:
George's look on sofapi, then the Home Assistant card (and its media player
reading `fixed_mute`).

Then 22-30 in order, each ADR first (`docs/DEVELOPMENT.md`, the IDs
there); MPD parked (ADR-0151). **Raspberry Pi Imager** (ADR-0159, a task):
Imager's own list stays open as it is (George, 2026-10-24).

The shared to-do list (an artifact with a `todos` collection; its address is
in Claude's memory, not here) holds the open items with their detail.

**Routine clean-up** (`docs/ROUTINE-CLEANUP.md`, George 2026-10-12): after
every merged release PR, otherwise weekly on Sunday evening. **Last run:
2026-10-25, after 1.6.0** (/home 224 -> 237 GB free).

## Phases

Closed: 0-19 (13 with letters a-f). Phases are numbered consecutively
without letters, each with a stable ID (George, 2026-10-13); 20 and 21
(the phone remote, `ph-phone-controls`, added by George on 2026-10-26) in
progress, 22-30 to come, MPD parked. `docs/DEVELOPMENT.md` holds each phase's acceptance criteria.

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
