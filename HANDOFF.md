# Handoff

Last updated: 2026-10-07 (on R2D2).

**2026-10-07 (state now):** the user manual, FAQ and technical guide are
**approved and released into the repo** (George: *"you can go ahead and
publish"*): on `phase-13b`/`phase-13d`, pushed, linked from README's new
Documentation section; they reach `main` with the next release PR. The
library's size is out of every current file (13d5eed; George: history
stays as it is). On gexis: core/ui/player `0.9.2+git32.b8a250b`, system and
lyrion-server `+git174.13d5eed` - Wi-Fi details with George's lock and
chevron fixes, and sheets above the phone's mini player (a laptop's screen
hid Close; checked at 4 desktop and 2 phone sizes, no button covered).
**Next, in order:** (1) the update screen shows the notes of every release
between the installed one and the new one (George, 2026-10-07: *"the update
screen should show all until the current one"*) - an amendment to the
update ADR first; (2) ADR-0123 step 2, Cable (needs a cable in gexis);
(3) ADR-0124, software volume.

**0.9.2 released 2026-10-06 on Testing (serial 25), from `phase-13d`**
(tag v0.9.2 at 3225ec1): 13f's Lyrion menus behind Extended navigation,
Minimise (ADR-0122), the phone sheet in one row, the enrichment tile, the
on-the-go enrichment fixes, the update screen's end and progress. Image
`image/deploy/2026-10-06-gexis-player-v0.9.2.img` in the main checkout;
111 checks passed; check-upstream ok (Plexamp 4.13.2, Lyrion 9.1.1).
**PR #50 into `main` waits for George.** Phase 13d stays open (board
tests); 13f stays open (George's tries, the hidden-library hour).

**13f: Claude Design's look is built, Standard and Bar** (ADR-0118
accepted, A-J plus the handover notes and George's answers, 2026-10-06;
handover in `design/source/13f/`). Steps on `phase-13b`: 5ede1d5 (glyphs,
counts, letter index), 9e39b2f (standard screens), then fixes from
checking them against George's Lyrion - letter headers by Lyrion's
textkey, a rail jump that stays put, the search field's look, counts that
match what is shown (a last page counts the rows shown; J's entry is
Lyrion-counted), the 711 panel's album page and Album Artists card -
and **step 3, the bars** (4309aa4): LyrionLevel and LyrionSearch take
`bar`/`wide`; the letter-pair strip is one component, `bar/JumpStrip`,
shared with the bar Artists row (George: "consistent"); Play all and the
app logo in the head column; bar home gains My Music, Favourites, Apps
(196 x 300 sideways). **Album Artists** replaces Artists on both homes
(George, 2026-10-06). Standard checked at 711/800/853 and bars at 1280
and 1850 x 400, through the relay harness against George's Lyrion.
**Owed:** (1) done 2026-10-06 - `0.9.1+git42.ba6900a` installed on
gexis (George's go-ahead); Qobuz's context-menu albums now give `play`
tracks with add/next/play, and the album page checked on bar and
standard; (2) Play / Play next / Add never pressed on
George's system - his to try; (3) George's look at the bars, and note 7
(whether the strip reads as buttons) on a real bar.
Also on the 13d preview since 0.9.1: the update screen ends on the steps
until Done, install progress by package size, notes no longer cut
(ADR-0110 amended) - effective from the update after the one that
delivers them, so 0.9.2's notes must stay under 1,200 characters.

## Start here

**Work continues on `phase-13b` in the main checkout, and Phase 13d in its
own worktree, `~/projects/gexis-player-13d` (branch `phase-13d`). Releases
0.5.0 to 0.8.9 went to the testing channel (0.8.9 is serial 22,
2026-10-04).** `main` is merged through 0.8.8 (PR #46); **the 0.8.9 PR waits
for George to merge it** - he merges, Claude opens. Next: 13b's last screen
swaps (George), then testing 13d (its worktree), then **13f, Lyrion's own
menus** (added 2026-10-04, Finding 110; an ADR first). 0.8.8 was released
without a preview, at George's word: he tests the bars on releases, not
previews, and test releases keep their logs across restarts (Debug logs
default on for Testing). **George is testing the bars on 0.8.8**: the new
screen switched to before the panel starts (`gexis-screen-check.service`,
ADR-0109 amended again 2026-10-04) is not yet seen on hardware. **From 0.8.8, one PR per
release** (George, 2026-10-04): never push a release onto an open PR.
**Phases 13a, 13b, 13c and 13e are closed** (DEVELOPMENT.md; 13b on 2026-10-04).

| What | State |
|---|---|
| Lyrion server (ADR-0115, 19 decisions; Finding 109) | Shipped through 0.8.6. Measured on George's tens of thousands of files: scans 2 h 7 min (High) / 1 h 59 min (Normal), memory 1,876 / 1,191 MB, no audio gaps during a scan. Memory limit = the player's less 1 GB; Normal under 4 GB |
| Fetched software (ADR-0100 amended) | Pinned versions; `packaging/check-upstream.sh` before each release; a new pin is fetched by the update that brings it |
| Change logs (ADR-0116) | `release_notes.json` is the one source: the player's page, `CHANGELOG.md` on `main`, the signed notes |
| Screens (ADR-0109) | The 13.3" tested at 1920 x 1080 and recognised; a case listed once as its panel. **A new screen at start: a recognised one is switched to with Keep (amended 2026-10-04), any other asked about** - both swaps passed on George's panels, 2026-10-04. Crowd-sourced fingerprints postponed (recorded in the ADR). The 13.3"'s brief blackouts were its HDMI cable (LESSONS 56) |
| Skin picker (ADR-0050 amended) | 960 px previews made ahead for every installed pack |
| Released in 0.8.7 | The new-screen notice and its straight switch (29a3386, 88ee721, d91a4bc); a USB disk kept 7 days after unplugging (ADR-0115 decision 17, ddf088f); setup's copy fixes from the review (963857d-034fb33); genre pills kept to two rows on the artist page (7cd3e1b); skin packs fetched from the channel's release when the player's own is unpublished, a stale pack failure no longer shown, failures in words (efd329d); Finding 109's playback test; 13a/13c/13e closed |

**`gexis` right now (2026-10-06, evening):** the 13d preview with
`phase-13b` merged - core, player and ui `0.9.1+git60.4f0662e`, Extended
navigation on, kiosk.env back to its original (debug port off, checksum
2fecdd6d...). Check playback before any restart.

**After 0.9.2 (2026-10-06, night), on `phase-13b`:**
- Updater: apt-listchanges off (the install bar's 16 s at 0), DpkgShare's
  rate re-measured (3.5 MB/s), the bar held full before the tick
  (ADR-0110 amended); **Check for updates now runs a check-only unit**
  (`gexis-update-checknow.service`) - it had started the nightly unit,
  which installs on Automatic. Phone: Settings' lists end clear of the
  sheet (22 px, measured on every page). On gexis as preview
  `0.9.2+git5` except the check-only unit (committed after).
- **Panel speed: Finding 112, fixed.** The slower opens were the hidden
  visualiser drawing (57 % of a core while playing). George chose option 1:
  ADR-0019 amended - hidden, it does not draw (`/run/gexis/visualiser-shown`).
  Now 6 % hidden, shown in 0.3 s with a finished frame; every open at or
  below 29 September (1-3 % dropped). On gexis as preview core/player
  `0.9.2+git13.c8d3e83`, gexis-system `0.8.9+git160.0be27be`. `panel-frames.py`
  now ignores the hidden library and measures all 16 interactions.
- **ADR-0123 / ADR-0124 accepted 2026-10-07** (rows in ADR-0022), built one
  step at a time: **step 1, Wi-Fi details - built, on gexis**, then George's
  two findings fixed (one chevron; the lock alone at the line's end, open
  where the password is known, both the same 13 x 15): ui/player
  `0.9.2+git28`, core `0.9.2+git25` (restarted) on gexis; checked on the
  panel and on phones 412 and 360 px wide. docs-drafts and the manual page updated.
  **Next: step 2, Cable** (manual address, 60 s keep) - gexis has `eth0` but no
  cable plugged; **step 3, software volume** (`meter -> softvol -> card`;
  verify passthrough at 100 % and the HDMI placement).
- **Docs (drafts) - HELD until George gives the go-ahead** (2026-10-06:
  "Do not release them until I give the go ahead"): `docs/manual/`,
  `docs/FAQ.md`, `docs/tech/` live ONLY on the local branch `docs-drafts`
  (commit 74fc7f9), taken off `phase-13b` so no release carries them.
  Manual and FAQ published privately for his comments (watched);
  `docs/HARDWARE.md` updated and published as a commentable doc.
  The tech-docs pass listed where ADRs and `docs/ARCHITECTURE.md` disagree
  with the code (ADR-0105 §4, 0106 item 2, 0107's table, 0108's main text,
  0110, 0113, 0040 §1, 0031/0104 on setup; stale docstrings in volume.py,
  remote_volume.py, adapters/base.py, NowPlaying.svelte; vite dev proxy
  missing routes) - **to be reconciled, not yet done.**
- Plexamp 0.4.0 was already released and pinned (shipped in 0.9.2).

**Second round of George's findings (2026-10-06), built and on gexis:**
- One-tap search also for Qobuz's and Spotty's "Search" folders (opened
  straight to the field, their kept searches skipped - decision E).
- Phone sheet (ADR-0101 amended): one row of icons, open or closed; Now
  playing a toggle (`panel.now` reported; `minimise` ask added).
- Choppiness, measured with a fake phone on the real relay
  (scratchpad tools): (a) the core's event loop stalls the touchpad relay
  while it parses big Lyrion answers - ~135 ms in every ~170 for 2 s while
  All Artists' letter index (2.7 MB) was built; letter indexes now kept by
  list for 30 min; (b) bunches are spread on the panel: moves 60 % per
  frame, scrolls half per frame in whole pixels (ADR-0121 §3 amended); the
  browser's own smooth scroll was tried and measured worse (slow start,
  then 150-190 px jumps), reverted. **Still open:** a 104 ms main-thread
  hitch when the Album Artists grid draws its next rows (page work, not
  input); gexis's Wi-Fi power saving is on (not yet measured as a cause -
  a decision for George once measured); **item 4 ("redrawn more often")
  not reproduced** - the idle home paints nothing in 8 s; asked George
  what he sees and when.
- Enrichment: Lyrion Client's three rows are one tile, `sweep_all`
  (ADR-0022 inventory, ADR-0059 amended), last run kept in enrichment.db.
- On-the-go enrichment (traced by a subagent, claims checked): late covers
  now reach the screen (daemon looks ~90 s, panel 60 s), one fetch per
  track/provider and one search per artist at a time, providers search
  with the raw artist; 86 stored 'nobody' identities purged on gexis
  (logged), nobodies now expire after a week. Then (same evening, George: "Do this too"): queries as a catalogue
  holds the names (lead artist, trimmed album, bare title; live-checked:
  two traced Bluetooth tracks now get covers), covers asked only when the
  renderer sent none and first, album/artist answers cached without the
  duration, confidence stored with cached answers. **Kept as designed:**
  the per-provider 15-min backoff (a per-track one was weighed and refused:
  a down provider would be asked for every track).

**George's findings of 2026-10-06, all built and on gexis:** Qobuz's
unstreamable "* " albums open as album pages (tracks Not available, a
note in place of Play album); a library album gets lengths and a Release
block from the library; rail/strip drawn while the letter index is pending
(Albums, Genres and a genre's artists no longer jump); pointer: a tap
clears the ring, the queue button rings, sideways scroll shape, moves
applied once a frame (**choppiness not confirmed fixed** - his hands);
touchpad socket reopens when the phone's page returns; the phone's
Home/Now playing/Lyrics row moved between pad and volume; a whole
labelled field counts as a text field, search openers announce text entry
and the field takes focus as it opens (**the one-tap keyboard is untried
on a phone**). **ADR-0122 accepted and built**: Minimise (chevron, top
left over the art) shows the library as left; Home stays. **Owed:** the
hidden library's behaviour on the Pi over an hour (ADR-0122,
Consequences); George's look at the chevron.

**Next, in order:**
0. **Fixes after 0.9.0, on gexis, unreleased** (George's findings,
   2026-10-05): an update stops whoever is playing (4f1684d); the starting
   volume holds 3 s after Spotify takes over (e10b93e); Starting volume
   beside Spotify's switch (1ef73a8); the panel's post-update notes scroll
   and wait for Continue (1f5cd5f). The phone's notes scrolled in every
   test - George sends a screenshot next time.
0. **ADR-0121, the phone as touchpad and keyboard: built and on gexis**
   (1c46f74, a56430d, 6181168; after George's first try, a8130c9 speed
   150-400 %, 88f389d the choppy start, 78356e2 a bigger pad and a touch
   outside closes the sheet). Three of its four measurements done and in
   the ADR (31 ms round trip; taps drive the panel after two fixes; the
   kiosk 16-23 % of one core while moving). **Owed: the keyboard on George's
   Android** - he found no text field; Settings' text rows (e.g. Pexels API
   key, empty) have one. **No system cursor on the panel** since fd106a5 + 5b4042c
   (a blank labwc cursor theme in gexis-system; on gexis, checked by grim
   -c). **Gestures and pointer styles built and on gexis**
   (George took every recommendation, 2026-10-05; ADR-0121 §2-3 amended,
   Pointer style in ADR-0022): two fingers scroll (7ea1f87), pinch zooms
   1-3x and zooms out when the phone leaves; Dot and Arrow from Claude
   Design's *Cursors* handoff (`Gexis_DAC_Player_3.zip`), Dot first.
   Checked through a local relay, not on George's phone; the zoom's cost
   on the Pi is not measured. **George's second try** (2026-10-05): TheAudioDB key,
   Pexels API key and Pointer style had never accepted writes - not in
   `__main__`'s wired table; fixed, and a test now catches it (42c7236).
   The drawer holds while the pointer is on it, rings only on icon buttons
   and follow the screen (d84fb94), scroll lines on the pad (80ff8bc).
   **Home / Now playing / Lyrics in the phone's sheet** (ADR-0101
   amended; N1 not behind the touchpad, N2 greyed while nothing plays;
   55d6c1e): checked on gexis's panel (standard layout) - Lyrics, Lyrics
   off, Home, Now playing, each screenshotted, toggle state reported back.
   **The bar layout's lyrics switch is not tried on hardware.**
0. **Idle backgrounds checked** (George: "always the same" animals,
   2026-10-05; ADR-0047 §2e, W1-W3 as recommended): the pool was one page
   of 50 at a change a minute (52 pictures drawn 230 times in an
   afternoon). Now 200 a page, the page turning daily through three, no
   repeat until the page is spent (online and on-device), kept on disk in
   `/var/lib/gexis-core/wallpapers/state.json` - checked on gexis: 200
   animals, a restart did not ask Pixabay again (8da8fc7). Artist pictures
   pick among an artist's fanart backgrounds (3172c48). A face-placed
   picture failed its request - numpy floats - fixed (b8eb10c). **Not
   done**: a library over 1000 artists uses its first 1000 only; bars
   find 0-12 wide pictures per 200 (Animals none). Drags (queue order, list scrolling) are
   out by decision D. Not measured during playback.
0. **ADR-0120, bar backgrounds** (accepted 2026-10-05): step 1 (placement)
   and step 2 (TheAudioDB for
   backgrounds and the Enrichment updates, its key row) built and live on
   gexis; the shared key's album list holds one album per artist, so covers
   are asked per album. Step 3 (Pexels, the rename to *Pixabay API key*,
   the bar's source order measured) built and live too, **untried against
   Pexels itself**: it issues no new keys for now (George), so the row is
   empty.
   a Pexels key for step 3.
1. **Phase 13d** (ADR-0117, accepted 2026-10-04): built in the worktree,
   six commits, not on hardware. George tests later: the DAC2 HD unchanged
   (preview from `phase-13d`), the IQaudio DAC+ chosen under *Sound card
   board*, and the take-back with a board that is not fitted. **Tests in a
   worktree:** the scratchpad venv imports the main checkout's
   `gexis_core`; run them with `PYTHONPATH=src`.
2. **The copy review** (George, 2026-10-03): one page per area, built from the
   code, with screenshots, for him to comment on. **Setup** ("Setup Copy")
   and **Settings** ("Settings Copy", 2026-10-05) are done, every comment
   fixed on `phase-13b` (6061e10-15e7d56): shorter Audio texts, Fixed output
   hides the three volume rows, the artwork updates moved back to Enrichment
   under *Lyrion Client* (reversing 2026-09-25 at his request), counts in
   what a list holds, errors in words, "player" where the text means the
   player and "device" only for the hardware (his call). **The intermediate
   screens are the third page, not started.** Comments do not reach the
   session by themselves: watch the artifact and read its threads.
3. **ADR-0119, Plexamp claimed from Settings** - accepted and built,
   **live on gexis as a preview** (2026-10-05): the contract's new `row`
   event (47190f8), the row's *Claimed* / *Claim again* and links in notes
   (48d0718), `plexamp-run` (ab56c0c), and **gexis-plexamp 0.4.0, committed
   in its own repository (784242c), not pushed or released** - on gexis its
   files were laid over the 0.3.0 package by hand. A release needs a
   gexis-plexamp 0.4.0 release and its pin moved. *Claim again* on George's
   real player worked (2026-10-05, his token): a new Plex player, Plexamp's own
   settings started again; it plays through the DAC and the meters (George). The test player `gexis-claimtest` is his to remove from
   his Plex account.
4. **Phase 13d, DACs**: ADR-0117 accepted, built in its worktree, being
   tested on `gexis` (merged up with `phase-13b` for the preview).
5. **docs/HARDWARE.md** is a draft; what it lacks is listed at its end.

**Working rules learned this session** (also in memory): a change is seen on
George's player before a release is cut, installed as the **whole set of one
commit, `gexis-player` with it, reading every removal apt reports**
(LESSONS 55), and the core restarted and checked by behaviour only the new
code has (LESSONS 54). A setting read for a worker thread is read on the
core's own thread first (SQLite; it bit twice).

**How a release is made** (each step proven 2026-10-02): run
`packaging/check-upstream.sh` - a pin behind its maker is tried on George's
player first, then moved (ADR-0100, amended 2026-10-03); George sees every
change live on his player before any release; George approves the notes (impersonal, New / Fixed / Good to know, no restart promises -
publish.sh refuses them); add them, with the day, to
`core/src/gexis_core/release_notes.json`, regenerate `CHANGELOG.md` (`cd core
&& python -m gexis_core.changelog ../CHANGELOG.md`; a test checks it) and
commit (ADR-0116: publish.sh takes them from the tagged commit's file, and
the player shows them under Change logs); tag `vX.Y.Z` locally; `make image` (never commit while it
packages - a `.dirty` build); `image/verify-image.sh` on the image;
`packaging/release/build.sh <img>`; `packaging/release/publish.sh rX.Y.Z
--channel testing`; push the tag; then push the branch and open **one**
pull request into `main` for the release - **George merges it** (2026-10-03; ADR-0116 decision 7: Change logs
points at `main`'s `CHANGELOG.md`, so it is current once he has). `packaging/release/out` is a symlink into the
`gexis-player-13a` worktree, excluded in `.git/info/exclude`. Never edit a
script while it runs (LESSONS 51).

**Provisioning a card:** do it, don't hand it to George - `udisksctl mount`
needs no password where `sudo mount` does. A card meant to test setup gets
the SSH key only, since a saved Wi-Fi skips setup.

### Branches and PRs

| Branch | State | What is on it |
|---|---|---|
| `main` | Merged through 0.8.9 (PR #47) | Every release to date |
| `phase-13b` | 13b, closed; records since 0.8.9 not yet in a PR | Goes to `main` with the next release's PR |
| `phase-13d` | Worktree `~/projects/gexis-player-13d`; ADR-0117 and its build, with `phase-13b` merged in | Merged into the release branch once George's tests pass |
| tags | `v0.1.0`-`v0.8.9` all pushed (2026-10-04) | - |
| `design-13b` | Claude Design's 2026-09-30 handoff | Reference only |

### Devices

- **A card flashed 2026-10-02 with `2026-10-02-gexis-player-v0.5.0.img`**
  (97 `verify-image.sh` checks), SSH key only, set up by George from the
  phone and his backup restored: *"everything seems in place"*. His finding
  there - Keep asked at boot while he was at the phone - is what the 13b
  amendment above answers.
- **sofa-pi** (192.168.178.131) took every update 852 -> 0.3.3 by George's
  own hand; whether it is on 0.4.0 or 0.5.0 now was not checked this session.
- The core's tests run on R2D2 from a venv (`python3 -m venv <dir>`,
  `pip install -e 'core[test]'`); add pygame to run the render tests too.

### Decided, not started

- **Hardware requirements, minimum and recommended** - **started as
  `docs/HARDWARE.md`** (George, 2026-10-03), the Lyrion server its own
  optional section; what is not yet in it is listed at its end
  (ADR-0111 decision 12):
  card space for the skins, and the Pi's load at 1920 x 1080. **And the
  Lyrion server** (George, 2026-10-03: *"record the results for hardware
  recommendations"*; Finding 109): memory by library size - about 27 KB a
  file while scanning, 1,876 MB for tens of thousands of files, the player itself needing
  about 1 GB beside it, so no server on a 1 GB Pi (ADR-0115 decision 18);
  card space - 151 MB of library and 670 MB of artwork cache for those files;
  time - 2 h 7 min for a first scan over the network, 26 min to check.
- **go-librespot 0.9.0 -> 0.10.2** (George, 2026-09-30: *"After 13c"*) -
  the first real update of a component through a release.
- **New users start from an image** (ADR-0105 amended): promoting to stable
  attaches the signed image; a Raspberry Pi Imager listing with the first
  public release, which waits on 13a, 13b and 13c.
- **Before the first public release** (George's to-do list, 2026-10-03):
  - **Remove the `pi` user's passwordless `sudo`** (George: *"The removal of
    sudo should go to first release to-dos"*; ADR-0107 decision 3 left it to
    then). Development images keep it - Claude's SSH work on `gexis` uses it -
    so the release image is where it goes.
- **Settings as an installed app: not now** (ADR-0102).

### Open, none blocking

- **PeppyMeter's redraw area for a meter away from the corner** is offset by
  `meter.y`; letterboxing adds 40 px to it. Whether the driver's partial
  updates show it as smearing is unchecked (skin-packs report, 2026-10-01).
- **An image without skins starts `gexis-peppy`, which exits 1** ("no
  skins") until a pack arrives and the core restarts it. Harmless; one
  failed unit in the journal.
- **Choosing a screen restarts the player even when nothing visible
  changes** - out of the 2026-10-02 amendment's scope.
- **LMS's power-on reaches the core 1.45-1.5 s after the press** (George,
  2026-09-28: recorded, no action).
- **Bluetooth "Not provided", once**, 2026-09-26; not reproduced.
- **The Restore row reads "4 paired"** - Bluetooth's word for backups too.
- **A phone that opens `/` posts `/panel/painted`**, read from the code.
- Older open items are in the archive's 2026-09-27 and 2026-10-02 blocks.

## Build environment (2026-09-13) — read this before the next build

No Phase 4 work happened this session. What changed is the build host, and it
matters because **Claude runs every build** (George, 2026-09-13), which makes
one failure mode routine rather than incidental.

**1. Docker's `data-root` moved to `/home/docker`.** It was `/var/lib/docker`,
on `/` — 62G with 9.1G free — while `image/deploy/` is in the repo on `/home`
(396G). The low-disk warnings were always about `/`; deleting zips from
`image/deploy/` frees the partition that *wasn't* full. Moved with
`rsync -aHAX --numeric-ids` (overlay2 needs hardlinks, xattrs and numeric
ids); `/` went 9.1G → 26G free. The old tree is gone. Roll back by removing
`/etc/docker/daemon.json` if this ever needs undoing.

**2. `make prune` (new), run automatically by `make image`.** Two things
accumulated in the preserved volumes, neither a cache: `work/*/export-image/`
leaked one raw ~4.5GB image *per build* (pi-gen's `prerun.sh` deletes only
`${IMG_FILENAME}${IMG_SUFFIX}.img`, and our `IMG_SUFFIX` is the git-describe
version, different every build — the leak is ours, not pi-gen's), and
`deploy/` kept every build's output, which `build-docker.sh` re-streams to the
host each run. First run reclaimed **10,194 MB**; volumes 18.89GB → 8.20GB.

**This is what to reach for instead of `make clean`.** `clean` does
`docker rm -v pigen_work`, which destroys the volumes *including* the ~8.4GB
of stage rootfs trees that make a build warm. "Clear the disk warning" and
"lose the warm build" were the same command. `clean` still exists, for forcing
a genuinely cold build.

**3. `DEPLOY_COMPRESSION=none`** — `image/deploy/` now holds a raw
`<date>-gexis-player-<version>.img`, no `image_` prefix, no zip. Settled the
open call `image/README.md` had carried since 2026-09-05, and the deciding
reason is the division of labour: **Claude builds, George flashes** (George,
2026-09-13), and a raw `.img` goes straight into Raspberry Pi Imager. Costs
4.5GB against 1.28GB zipped; `mtools` inspection and `bmaptool` support come
along with it. **Do not re-propose compression to make the copy-out cheaper**
— that optimises the build host at the cost of the one manual step in the
loop. `make prune` and `make fetch-deploy` handle both halves of the cost.

**4. `make fetch-deploy` (new) — expect to need it.** `build-docker.sh:154`
ends every build with `docker cp …/deploy - | tar -xf -`, streaming the whole
directory through a pipe. Under host memory pressure **that** is the step that
dies, with the build itself already complete. Observed twice on 2026-09-13,
both times leaving a valid image in the volume.

Two traps here, both of which cost time this session:

- **There is no kernel OOM record.** The kill comes from the process
  supervising the build, so `journalctl | grep oom-kill` finds nothing and
  proves nothing. A correct diagnosis was retracted on exactly that
  non-evidence before the failure was reproduced live.
- **A fallback inside `make image` cannot work.** The signal reaches make
  (`make: *** [Makefile:127: image] Terminated`), so no recipe is left
  running. Recovery must be a separate invocation — hence the target.

`make fetch-deploy` copies per-file (no tar pipe; 44s for 4.5GB), skips
anything already present at the right size, and appends the manifest
annotation `image` would have. Verified: recovered image byte-identical,
manifest reporting the true 749s.

**5. The build bind-mounts the live working tree — do not edit `core/` while one
runs.** `PIGEN_DOCKER_OPTS` mounts `core`, `ui/dist`, `skins` and
`stage-gexis` **read-only into the container, not copies**, and each stage reads
them when it runs. An edit landing between two stages produces an image that is
half one commit and half another, **and the `.info` still reports the git-describe
version it started with**, so the artefact would name a commit whose contents it
does not have.

Nearly hit on 2026-09-25: `03-core` finished at container 17:22:06 and the first
edit of that session's next piece of work landed 25 seconds later on the host
clock. **The clocks are not the same** — the container runs two hours behind —
so the arithmetic proved nothing. What settled it was looking:

```
docker exec pigen_work_cont sh -c 'ls /pi-gen/work/*/stage-gexis/rootfs/opt/gexis-core/venv/lib/python3*/site-packages/gexis_core/adapters/'
```

The new module was absent, so the image held exactly the merged commit. **Check
that way, not by comparing timestamps**, and prefer starting a build from a
clean tree you then leave alone.

**Current warm-build baseline: 12m29s** (cold ~40m), 2026-09-13, with prune
and no compression. Latest artefact:
`image/deploy/2026-09-13-gexis-player-v0.2.1-98-gfec5067-dirty.img` —
**built and verified as a file, not yet flashed.** `04-ui` (labwc, the
`PAMName=login` seat, 1280x800, the Chromium flags) is still written entirely
from documentation and has never been run on hardware.

Commits: `3c13bd1` (prune), `987e84f` (raw .img), plus the `fetch-deploy`
commit, on `phase-3-core-daemon`.

## Machines

| Name | What it is | Notes |
|---|---|---|
| `R2D2` | **dev machine from 2026-09-17** | CachyOS, 12 cores, 31 GB RAM, **fish shell**. `192.168.178.134`. Replaced C3PO because builds kept being killed for low memory. Set up per `image/README.md`'s host prerequisites: Docker with `data-root` `/home/docker`, qemu-user-static-binfmt, `~/.local/bin/qemu-aarch64`, loop autoloaded via `/etc/modules-load.d/loop.conf`. Repo at `~/projects/gexis-player`, both `*.local.env` files and Claude's project memory copied from C3PO, its key authorized on `gexis`. UI builds, 444 core tests pass. |
| `C3PO` | former dev machine | CachyOS, 8 cores, 14 GB, **fish shell** — no heredocs. Hand it script files to run with `bash`, not pasted multi-line commands. Retired for builds 2026-09-17 (out of memory). |
| `rig` | Raspberry Pi 4, 4 GB | Raspberry Pi OS Lite 64-bit, Trixie. **Reference machine** — holds the environment Findings 002-004 were measured against. Not the build/test target. |
| `gexis` | Raspberry Pi 4 | Flashed from this project's own `make image` output. User `pi`. Reachable as `pi@gexis.local` by SSH key. **The image-built target** — Phase 2 onward is built and measured here. |
| SD card 2 | moOde | Reference install. Read-only recon source. Do not modify. |
| LMS server | `192.168.178.188` | For manual testing (arbitration base slot, etc). **CI gets a containerised throwaway instead — CI must not depend on this server being up.** |

**Provisioning a freshly flashed card:** `make provision DEVICE=/dev/sdX`
fills in `firstrun.sh`'s SSH key / Wi-Fi / hostname from
`image/provision.local.env` (gitignored, copy `image/provision.env.example`
to create it) and clears the card's stale SSH host key. See
`image/README.md`.

**Builds are versioned, starting 2026-09-07** (George: "can we start
giving release numbers to the builds"). `git describe --tags --always
--dirty` at build time, appended to the `.info` manifest as "Image
version: vX.Y.Z" — same place peppyalsa's commit and go-librespot's
version already live, not a new mechanism. First tag: `v0.1.0`
(annotated, on `phase-2b-arbitration`). No bump convention decided yet
(when to cut `v0.2.0` vs. just moving the tag) — tag manually before a
build worth naming, for now.

**Filenames carry the version too, starting 2026-09-11** (George asked).
The `.info`-only note above is now out of date on this point - the
plumbing concern it named (threading the version through pi-gen's own
two-pass `image/config` sourcing, which would need git access *inside*
the container that isn't there) turned out to have a simpler answer:
pi-gen already exposes `IMG_SUFFIX`, appended to every export-image
filename with no default of its own unless a stage sets one (none of
ours do), so the `Makefile`'s `image:` target now passes
`-e IMG_SUFFIX=-$(IMAGE_VERSION)` via `PIGEN_DOCKER_OPTS` - no
`image/config` change, no submodule edit. Confirmed the env var reaches
the container intact via a standalone `docker run -e` test (a plain host
environment variable does not cross that boundary on its own - `docker
run` only forwards what's explicitly passed) and confirmed the resulting
filename shape by simulating `build.sh`'s own variable-resolution lines
directly. The `image:` target's own manifest-lookup glob was widened
(`*-gexis-player.info` → `*-gexis-player*.info`) to still find the
now-longer filename - the exact class of thing that broke silently once
already (the multi-manifest annotation bug, Phase 2c's prerequisites) -
check this first if a future build's manifest looks unannotated again.

**First real `make image` run found it didn't work at all - the
filenames came out exactly as before, no version suffix.** Root cause:
`image/stage-gexis/EXPORT_IMAGE` (this project's own file, not the pinned
submodule - the mechanism that triggers pi-gen's export-image stage at
all, adapted from upstream's stage4/5 convention) unconditionally set
`IMG_SUFFIX=""` at its own top, sourced by `build.sh` right before the
export stage runs - silently clobbering whatever the Makefile had passed
in via the container's environment, every single build, before this was
noticed. The annotated `.info` manifest's own version line still worked
(a separate, host-side mechanism, unaffected) - only the filenames
themselves were wrong. Missed originally because the isolated
verification checked the env-var-passing mechanism and simulated
`build.sh`'s own variable-resolution lines directly, but never checked
whether anything sourced *after* those lines could still overwrite the
result - `EXPORT_IMAGE` files are exactly that, and this project's own
copy of the pattern wasn't audited. Fixed (`IMG_SUFFIX="${IMG_SUFFIX:-}"`,
preserves rather than clobbers), confirmed by the same isolated-simulation
method as before (sourcing the actual fixed file with `IMG_SUFFIX`
pre-set, exactly as the container would have it). **A second `make
image` run is what actually proves this** - the one that produced today's
reverted, currently-flashed image predates this fix.

## Phase order

```
0  reproducible image                     * merged - pi-gen, ADR-0021
1  measurements                           absorbed into 2 - needs 2's own renderers
2  audio layer + arbitration              * merged
3  core state daemon                      * merged
4  UI shell + idle + display-only nowplay * merged
5  visualisation service + Peppy screen   * merged
6  now playing, full                      * merged (PR #18)
7  library browse                         * merged (PR #19) - typed queries +
                                            our screens; SlimBrowse for radio
7a panel responsiveness                   * done - artwork at the size drawn,
                                            an instrument that survives its
                                            own scrutiny, and a baseline
                                            (Finding 034). Reaching the target
                                            is Phase 9 criterion 0
8  enrichment + lyrics                  * done 2026-09-18, checked by George
                                            on the panel. ADR-0040, twice
                                            amended by what the work measured
9  settings wiring + UI polish          * COMPLETE 2026-09-25 - all five
                                            criteria closed. 0 carries a
                                            revisit before 13
10 plugin contract                      * COMPLETE 2026-09-25 - criterion 3
                                            done, criterion 1 documented and
                                            versioned. Criterion 2 and the
                                            freeze go to 11, because 2 is the
                                            freeze's evidence. Themes left it
                                            for 14 and the defaults stayed in
                                            the core process, both George's;
                                            the Beszel agent was the test that
                                            it carries a non-renderer, and it
                                            amended the contract twice
11 Plexamp as a renderer, as a plugin   * COMPLETE 2026-09-25 - all six
                                            criteria, and Phase 10's criterion
                                            2 with them. ALSO the proof
                                            for 10. Its
                                            hardware check is pulled forward
                                            into 10 - Finding 075 says moOde
                                            built a Plexamp route and parked it.
                                            **Four defects closed 2026-09-26
                                            after George used it** (ADR-0091,
                                            ADR-0092): the 14 s handback, the
                                            phone still showing it connected,
                                            `activate` implemented but never
                                            declared, and - the one that matters
                                            - it could not take the device from
                                            a renderer that was holding it AT
                                            ALL. Criterion 2's *"takeover gaps
                                            measured against the other
                                            renderers"* was closed on Finding
                                            085, which turns out to have
                                            measured an LMS that had already let
                                            go; the criterion is better
                                            satisfied now than when it was
                                            signed off, and that record is
                                            corrected rather than left to read
                                            as if it had been right
12 plugins fetch their software on the  * COMPLETE 2026-09-28 (PR #34 merged)
   device; 12b Legal and Credits            Plexamp fetched from Plex, status /
                                            progress / Retry / Remove in its row;
                                            Legal and Credits approved
13 first boot without a network           setup access point; pull forward the
                                            moment a non-developer gets a device
                                            (ADR-0031)
13a plugins you install and update       CLOSED 2026-10-03. Decided 2026-09-28 (George): a phase
                                            before themes. Upload a plugin from a
                                            phone or computer, run it sandboxed,
                                            Remove it; updates from versions we
                                            have tested. ADR first
13b other screens                        * BUILT on phase-13b; hardware tests
                                            and the PR to go. Added 2026-09-28
                                            (George): 800x480 to
                                            1920x1080, bars 1280x400 and 1480x320
                                            (landscape); two layout families;
                                            skins per resolution; recognise the
                                            screen in setup. Finding 100. ADR
                                            first; designs from Claude Design
13c updates over the network             * CLOSED 2026-10-03; MERGED (PR #42); 13a merged (PR #41).
                                            Added 2026-09-28 (George: "Agreed to
                                            do before"). **The first public release
                                            image waits on 13a, 13b and 13c**
                                            (George, 2026-09-29). ADR-0021's in-place
                                            apt updates, never built: our parts as
                                            .debs, a signed repository, OS updates
                                            as they come or a tested snapshot
                                            (decide), backup before each update.
                                            ADR first
13d DACs we have not tested             decided 2026-10-01 (George): after 13b,
                                            from Volumio's list; the DAC2 HD and
                                            IQaudio DAC+ first. ADR first
13e server plugins                       CLOSED 2026-10-03. Decided 2026-10-02 (George): after 13d,
                                            before the first public release. Lyrion
                                            server and Beszel hub, shipped in our
                                            releases; music first, scan impact
                                            measured. Pi-hole and AdGuard deferred.
                                            ADR first
14 themes                                 cut out of 10. ADR-0016 calls themes
                                            plugins and plugins processes; a
                                            theme has no process - settle that
                                            first
15 the library answers for itself         moved here 2026-09-26 (George): "the
                                            entire discussion and in between
                                            phase for enrichment via Plex server
                                            gets [moved] to its own phase at the
                                            end of the phase queue after themes".
                                            Was 11a, inserted on
                                            2026-09-25. Leverage the Plex
                                            server's own metadata; internet
                                            providers stay as fallbacks, not
                                            removed. Measured first:
                                            Finding 086, which is what it has
                                            instead of a plan
```

Phases 9-13 were renumbered on 2026-09-16 (George). `docs/DEVELOPMENT.md`
holds each phase's acceptance criteria; this list is only the order.

## Things that will bite if forgotten

- **The 13.3" panel's setup jams gexis's Wi-Fi** (measured 2026-10-05,
  0.9.0 preview, 5 GHz channel 36, signal -62 to -66 dBm either way): with
  the panel connected, 20-37 % of pings to the router lost, 80-1,260 ms
  average, link 6.5-27 Mb/s; unplugged, 0 % lost, 7 ms, 290-390 Mb/s. It
  shows as stuttering playback and Settings that fail to load on the phone.
  Wi-Fi power saving is not the cause (off was worse). **Swapped for the
  10.1" 1280x800, the same day: 0 % lost, 7-10 ms to the Lyrion server,
  290-325 Mb/s** - so it is the 13.3" FHD's setup (the panel, its supply or
  its cable; not split further). A network cable to the Pi avoids it.

- **Restarting `gexis-core` does not reload the panel.** `ui/dist` rsynced to
  `/opt/gexis-ui` reaches Chromium only on a page load, so a probe run after a
  daemon restart measures the *old* bundle faithfully and reports that the
  change does not work. **Port 9222 is not open on the image** (checked
  2026-09-26), so reload with `systemctl restart gexis-kiosk` and confirm the
  panel fetched the new bundle: `journalctl -u gexis-core | grep 'GET
  /assets/index-'` names it by hash. [LESSONS](docs/LESSONS.md) 10 and 38.

- **A flash wipes everything the device learned - back up first, from
  Settings.** *Back up now* (ADR-0083) writes an archive to the Backups share:
  both databases, `core.toml` and `device-name.env`, BlueZ's pairings, the
  Spotify pairing (go-librespot's `state.json` only - its `config.yml` is the
  image's), the Beszel fingerprint and **Plexamp's claim**
  (`~/.local/share/Plexamp`). **Copy it off the device** before flashing, and
  keep it **outside the repository** - `core.toml` carries `idle_url`, a
  per-display identifier that must never be committed.

  **After a flash:** copy the archive back into the share, *Restore* it, and let
  it reboot. Startup brings every unit in line with its switch (ADR-0077 as
  amended), so Plexamp and Beszel come back running and claimed - measured
  2026-09-26 with the units disabled as a fresh image ships them. Then:
  **re-pair the phone** only if the pairing was not in the archive, and
  **append C3PO's SSH key** (below). The sweeps are not needed: `enrichment.db`
  comes back with everything else.

  **Archives from before 2026-09-26 still restore.** They hold all of
  `/var/lib/go-librespot`; the restore takes `state.json` and skips the rest
  rather than refusing the archive.

  **Restoring wholesale carries dead keys** - `per_renderer_volume`,
  `boot_volume`, `idle_brightness`, `handoff_threshold`. Harmless:
  `Settings.value` reads the registry, not the store.

- **The journal is in RAM.** A reboot - including the one a restore does -
  destroys every log since boot. On 2026-09-26 that cost the logs of a bug
  George had just reproduced. Capture before rebooting (`ssh ... journalctl -f >
  file`); whether to make it persistent is a decision still owed.

- **Only squeezelite may use `output_wait`** (ADR-0095 as amended). Two renderers
  waiting for the DAC at once deadlocked the core for 68 s: the kernel hands a
  freed device to whichever waiter it wakes first, not the one arbitration chose.
  Do not move go-librespot, Plexamp or bluealsa onto it without answering that.

- **Plexamp restores its queue on every start** - `plexamp-start-idle` exists
  because a restored *paused* queue opens the DAC with nobody asking. Anything
  that restarts Plexamp outside `plexamp.service` (running `node js/index.js` by
  hand, as the claim does) bypasses it.

- **A plugin's mark is cached for a day**, which is safe only because its URL
  carries the file's hash (`Plugin.mark_url`). Anything that serves a picture
  under a fixed URL with a long `max-age` will be shown stale after it changes.

- **A reflashed card only has R2D2's SSH key.** `make provision` writes the
  one key in `image/provision.local.env`; C3PO's
  (`~/.ssh/c3po_id_ed25519.pub`) is appended by hand after first boot
  (George, 2026-09-17). Both keys are commented `desktop-to-dietpi`; compare
  fingerprints, not comments.

- **Deleting a stage does not delete what it installed** (LESSONS 45).
  `stage-gexis` reuses its rootfs across warm builds, so files from a removed
  stage stay in every image until its work directory is cleared:
  `docker run --rm --volumes-from pigen_work debian:trixie rm -rf
  /pi-gen/work/gexis-player/stage-gexis`. Stages 0-2 stay warm.
- **Never `docker start pigen_work`.** It re-runs pi-gen's entrypoint and
  starts a build — done accidentally on 2026-09-13 while inspecting the
  volumes, killed ~90s into stage0 (no damage: `lists/partial` and
  `dpkg/updates` were empty, `dpkg/status` untouched). To read the volumes,
  use a throwaway container, which is what `make prune` does:
  `docker run --rm --volumes-from pigen_work pi-gen:latest sh -c '…'`.
  Note the real build never starts `pigen_work` either — when it exists,
  `build-docker.sh` runs `pigen_work_cont` with `--rm --volumes-from`, so
  `pigen_work` is only a volume holder and its exit status is irrelevant.
- **`work/*/build.log` accumulates across `CONTINUE=1` runs.** Its first
  timestamp is not this build's start. Anything deriving a duration from it
  must take the *last* `Begin /pi-gen/stage0` to the *last* `Build finished`
  — a first cut of `fetch-deploy`'s annotation reported 4186s for a 749s
  build by spanning two runs.
- **An interrupted `docker cp … | tar -xf -` rewrites `deploy/`
  alphabetically** and can truncate a *previous* build's artefact, not just
  the current one. Cost a good image on 2026-09-12 (583MB of a real 1.05GB).
  `make prune` shrinks the blast radius by keeping only the current build in
  the volume; it does not remove it. Check sizes before trusting a
  `deploy/` file that a killed build touched.
- **Never reference an ALSA card by index.** 3 on `rig`, 2 on moOde, 1 on
  `gexis` — same DAC model, three different indices (Finding 005). Use
  `hw:sndrpihifiberry`.
- **`ctl.output`, not just `pcm.output`, in `output.conf`.** Mixer access
  (`squeezelite -V DAC`) resolves through the control interface, not the
  PCM slave chain — ADR-0009 was itself incomplete on this until Phase 2a.
- **`squeezelite -V <control>` does not fail on a bad mixer name** —
  confirmed from its source. It logs and silently falls back to software
  volume. `squeezelite.service`'s `ExecStartPre` is the actual assertion.
  As of 2026-09-08 (B2) the target is `hw:gexislmsvol`'s `Master`, a
  private `snd-dummy` control, not the real `DAC` — same risk, different
  target; the check was updated to match, don't let it drift back.
- **`alsactl monitor <card>` needs the `hw:` prefix** — `alsactl monitor
  gexislmsvol` fails with `Invalid CTL`, `alsactl monitor
  hw:gexislmsvol` works. Not documented in `alsactl(1)`'s own SYNOPSIS.
  Found 2026-09-08 wiring up `DummyMixerBridge`.
- **`amixer sget`'s value line format differs by control** — a control
  with distinct playback/capture volumes prints `Front Left: Playback
  216 [...]`; one without (e.g. a `snd-dummy` card's `Master`) prints
  `Front Left: 30 [...]` — no "Playback" word. `volume.py`'s `get_raw()`
  parses both now; a regex written against only the real DAC's format
  will silently return `None` for a dummy control.
- **gexis-player is GPL v3 (ADR-0025, 2026-09-08).** Every file we
  author under `core/src/gexis_core/` carries `# SPDX-License-Identifier:
  GPL-3.0-or-later` as its first line — see `docs/DEVELOPMENT.md`'s
  "Licence" section. Don't add it to a vendored third-party file.
- **A `.gitignore` fix on one branch does not protect other branches**
  working off the same tree. Run `./test-gitignored-credentials.sh` on
  whatever branch you're on if you're not sure.
- **`type plug` must not appear in the `output` chain.**
- **`alsa-lib` is pinned at `1.2.14-1+rpt1+deb13u1`** (moved from
  `1.2.14-1+rpt1`, 2026-09-12, George's decision — see ADR-0021's amended
  pin bullet). Findings 002/003 measured the older version; they are left
  as the measurements they were, not rewritten. **The failure mode to
  recognise:** a pinned version can vanish from the archive index and
  then `make image` fails outright at `stage-gexis/00-alsa` with
  `E: Version '...' for 'libasound2t64' was not found`. That is the pin
  working as intended (a hard stop, not silent drift) — check
  `archive.raspberrypi.com/debian`'s own `binary-arm64` `Packages` index
  for what is actually available before touching anything, rather than
  trusting apt's "however the following packages replace it" list, which
  names armhf and `-data` packages and reads like a restructure when it
  is only a point release. ADR-0021's deferred Q3 (snapshot-pinning the
  archive) is the standing fix and is still deferred.
- **`docs/DEVELOPMENT.md` on `main` is stale** — see above.
- **Adding a user to the `docker` group needs a new login session**, not
  just relaunching Claude Code — a shell spawned before the change keeps
  its old group list until it's re-created (new terminal / re-login).
  Check with `id` before assuming `docker` commands will work.
- **A failed `make image` leaves `pigen_work` behind even after
  `make clean`** if `clean` ran before the failing attempt rather than
  after it — `clean`'s `docker rm -v pigen_work` only removes what
  exists *at the time it runs*. Run `make clean` again after any failure,
  right before retrying.
- **An interrupted `make image` can leave a *previous* image truncated in
  `image/deploy/`, looking exactly like a valid one.** Found 2026-09-13.
  The build itself finished (15m18s, warm) and was killed by `C3PO`'s own
  low-memory condition during the final `docker cp ... | tar -xf -` that
  copies results out. That copy rewrites everything in `deploy/`
  alphabetically, so it had already overwritten the previous day's `.zip`
  and got part-way: 583 MB where the real file was 1.05 GB. Nothing says
  so — the filename and timestamp look normal, and flashing it would fail
  in some interesting way much later.
  **Recovery needs no rebuild.** `PRESERVE_CONTAINER=1` means the finished
  artefacts are still in the container: `docker cp
  pigen_work:/pi-gen/deploy/. <somewhere>` retrieves them from a *stopped*
  container (`docker exec` will not work on one). Check the recovered
  sizes against `unzip -t` before trusting either file.
- **Two images in `deploy/` is ~2.3 GB and the disk is 62 GB.** With the
  pi-gen container and its volumes also resident, 85% used is a normal
  post-build state. `make clean` reclaims the container's share; the
  images themselves are only removed by hand.
- **Don't assume `C3PO`'s tooling is on the image.** `xxd`, `bc`,
  `telnet`, `nc` aren't there (Lite base doesn't have them) — `od`,
  `curl`, `ss`, `fuser` are. Reach LMS's CLI (port 9090) via bash's
  `/dev/tcp` instead of `telnet`/`nc`. More broadly, never paste command
  blocks across machines without checking which host a shell is actually
  attached to first (see the method note above).
- **`systemctl is-active` does not mean "working."** squeezelite reported
  active while go-librespot held the ALSA device out from under it,
  retrying every 5s with no way to see that from unit status alone —
  found on hardware, 2026-09-06. Check the actual symptom (audio, or in
  this case `fuser` on the PCM node), not just unit state.
- **A commanded pause does not make squeezelite release faster than its
  `-C` idle timeout** — measured ~8.5s from an LMS CLI pause to the ALSA
  device actually freeing, 2026-09-06. Arbitration cannot get a fast
  release out of squeezelite through LMS's own pause command; see the
  hardware session above for what this means for criterion 4.
- **go-librespot's `server.port` and `zeroconf_port` are ephemeral if
  left unset** — measured differing across a single `systemctl restart`.
  `server.port` is now pinned (`config.yml`); `zeroconf_port` is left
  random on purpose, since nothing on this device needs to address it by
  a fixed port and it must stay reachable from off-device (the phone
  app) regardless of which port it lands on.
- **`$EDITOR` is unset on `C3PO`.** `git merge` without `--no-edit` stops
  waiting for `vi`, which isn't installed. Use `git commit --no-edit` (or
  set an explicit editor) rather than let it hang.
- **Bluetooth is rfkill soft-blocked by default on this image** —
  nothing in the unattended boot clears it (that's normally
  `raspi-config`'s interactive country-code step). `rfkill list` and
  `/sys/class/rfkill/*/soft` show it directly; `hciconfig hci0 up`'s
  error message names it explicitly. Don't trust `bluetoothd`'s own
  "Failed to set mode: Failed (0x03)" to self-diagnose this — it's the
  same underlying block, several layers removed. `rfkill` itself is on
  the image already (`/usr/sbin/rfkill`, needs `sudo` and isn't on a
  non-root `PATH` by default) — it was never actually missing, just not
  found by an unqualified `which rfkill`.
- **A stock `alsa-restore.service` fights any "boot volume is fixed,
  never restored" requirement.** It's enabled by default on Raspberry
  Pi OS Lite and does exactly the opposite. Mask it, don't just order
  your own unit to run after it and hope you win the race.
- **A lossy bidirectional bridge over two different scales needs echo
  suppression on *both* directions, and a single write can produce more
  than one incoming event.** A boolean "skip the next one" flag missed
  both — see the volume bridge fix above for the measured consequence
  (a real ratchet to zero) and the fix (a shared time-window, not a
  one-shot flag).
- **`bluetoothctl discoverable on` does NOT mean persistently
  discoverable.** BlueZ's `DiscoverableTimeout` defaults to 180s and
  silently reverts the adapter afterwards; `Pairable` has no such default
  and does persist, so the two behave differently despite being set the
  same way two lines apart. Cost us blocker 3 and 1h36m of a live debug
  session. Read `bluetoothctl show` back after setting it, rather than
  trusting "Changing discoverable on succeeded".
- **Build filenames now carry the version (2026-09-11)** — the
  `Makefile`'s `image:` target manifest-lookup glob is
  `*-gexis-player*.info`, not `*-gexis-player.info` — if a future edit
  narrows it back, the annotation step will silently stop finding the
  manifest again, the same shape as the multi-manifest bug this project
  already hit once (Phase 2c's prerequisites, `ls -t | head -1`).

## Working agreement

George is product manager: requirements, acceptance criteria, trade-offs, UX.
Claude handles implementation, tooling, tests, commits. Does not commit to
`main` — opens PRs.

Every architectural decision becomes a numbered ADR before implementation.
Findings state their scope: what was tested, under what conditions, what was
not. `docs/LESSONS.md` (PR #5) tracks recurring verification-methodology
failures, kept distinct from findings and ADRs.
