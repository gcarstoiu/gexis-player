# Handoff

Last updated: 2026-09-17 (eighteenth session, on R2D2 — **Phase 6 merged
(PR #18); Phase 7 planned, ADR-0038 written and awaiting George's read**)

## Start here

**Phase 7 — library browse — is planned on branch `phase-7-plan`.** George
agreed the plan and six decisions on 2026-09-17; they are in
[ADR-0038](docs/decisions/0038-library-and-radio-on-the-panel.md) (status
**Proposed**) and in `docs/DEVELOPMENT.md` Phase 7 (criteria 1 and 6 amended,
10 and 11 added, the plan). In short: only the designed screens; row actions
play now, add to queue, add to playlist (**no create playlist** in Phase 7);
initials instead of artist photos and a discography-only artist page until
Phase 8; the queue rail is in; Radio Now Playing stays; five settings
appended to ADR-0022's inventory (George confirmed).

**Step 1 is done: [Finding 029](docs/findings/029-library-and-radio-against-lms.md).**
George's calls on it are in ADR-0038 (§1, §1a, §3): Album Artists; library
playlists only; LMS's filing and release types; add to any library playlist;
no playlist creation (George is asking Claude Design to remove it). ADR-0038
is still marked Proposed.

**Step 1a is done** (2026-09-17): a takeover restores LMS's old position
and play state only if `playlist_timestamp` is unchanged (George's rule A;
ADR-0027 amended, Finding 029 addendum). George checked both directions on
`gexis`. **Hand-installed on the device, not in an image:** `lms.py` copied
into `/opt/gexis-core/venv/lib/python3.13/site-packages/gexis_core/adapters/`,
previous core at `/opt/gexis-core.7-1a-backup`. A reflash loses it until the
Phase 7 image.

**Step 2 is done** (2026-09-17): a playing station shows the song as title,
its artist, the station as the album line, and the song's `artwork_url` or
"artwork pending" (ADR-0038 §8a). George checked on `gexis`; also
hand-installed (previous core, with step 1a, at `/opt/gexis-core.7-2-backup`).
George asked for radio artwork via enrichment: Phase 8 criterion 7.

**Step 3 is done** (2026-09-17): `core/src/gexis_core/library.py` and
`GET /library/…` reads, tested against made-up LMS replies (George's call).
Hand-installed on `gexis` too; previous core at `/opt/gexis-core.7-3-backup`.

**Step 4 is done** (2026-09-17, checked by George on the panel): Home is the
library root — five cards with live counts, the New Music strip, the mini
strip, the waiting services when no renderer is connected, and Settings from
its card. UI deployed by hand to `/opt/gexis-ui` (previous build at
`/opt/gexis-ui.7-4-backup`).

**Next actions: George's three findings from that check**, in his order:

- **4a: volume drops to 0 when LMS pauses. Done 2026-09-17, awaiting
  George's listen.** LMS fades the player out by moving the renderer's mixer
  control; the core mirrored that onto the DAC and published it
  ([Finding 031](docs/findings/031-lms-pause-fade-and-push-latency.md);
  ADR-0018 and ADR-0034 amended). Fixed by deciding only once the control has
  settled for 0.8 s, and only while the renderer is playing - two earlier
  attempts failed on hardware because the pause reaches the core 0.51 s after
  the fade. Measured after the fix: the DAC holds its level across a pause,
  the panel stays at 48%, and an LMS-app change still lands, 0.8 s later.
- **4b: press feedback. Done 2026-09-17, awaiting George's check.** Now
  playing's buttons, Settings' Back and the library's round buttons keep
  their resting fill and shrink to 0.95 on press; the mini strip shrinks to
  0.995 from its bottom edge. The design's grey press fill read as a flash,
  as it already had on play and the transport buttons.
- **4c: choppiness. Fixed by one backdrop for the whole panel** (George,
  2026-09-17: *"clear improvement"*). `ui/src/screens/PanelBackground.svelte`
  draws the weave and the artwork's bleed once; each screen keeps only its
  own veil, so exactly one screen is mounted at a time and the incoming one
  fades in (120 ms). Also in this step: artwork requested at the size it is
  drawn (200 px thumbs, 500 px covers), the strip's fade mask changed only
  when an edge gains or loses it, and the library's animation halved to
  140 ms. **The CPU governor was set to `performance` and reverted the same
  day** ([ADR-0039](docs/decisions/0039-cpu-governor-performance.md)): ~10 °C
  hotter (76.3 °C mean against 66.2) for no visible improvement. **Left for
  George's next look:** a fraction-of-a-second blink between now playing and
  Home, which the two-way fade caused by showing the bare backdrop between
  the screens; the outgoing screen now leaves at once instead.

**Lesson candidate (2026-09-17), for George:** headless Chromium on the
device was used to check the panel UI and answered a different question
twice — it did not reproduce the black-screen defect the panel showed, and
its screenshots silently stopped updating after any animated transition, so
a real defect first looked like a capture artefact. The panel is the only
renderer that answers "does the panel draw this".

**Test data on George's LMS:** playlist folder `/playlist` (George set it;
it triggered a full rescan that renumbered the library). Playlists
`gexis-test-album` (122541), `gexis-test-mixed` (122543),
`gexis-test-empty` (122544) — George removes them. Finding 029's raw replies
are at `~/gexis-findings/029-raw/` on R2D2, deliberately not in the repo
(library listing, playlist names, a TuneIn serial).

**Probing SlimBrowse can start playback.** A radio walk that followed
`base.actions.go` played a station for 45 s (Finding 029). Resolve the
command and refuse anything ending in `play` or `add` before sending.

**Corrected in this session, worth not repeating:** Claude raised "playing
from the library must power LMS on" as an open decision. It was not: LMS's
auto-power-on on play is recorded in ADR-0027 (hardware, 2026-09-12) and
Finding 019. The repo was not searched first — `docs/LESSONS.md` case 4's
corollary.

**Measured 2026-09-17 against George's LMS (read-only), now in ADR-0038:**
the `radios menu:radio` reply has no `id` on any item, so Podcasts is
excluded by its `["podcast","items"]` command; `cover_300x300` is a 173 KB
PNG where `cover_300x300_o.jpg` is a 25 KB JPEG (one album);
`ignoredarticles` is "The El La Los Las Le Les".

**Phase 8 research is recorded, ahead of time:**
[Finding 030](docs/findings/030-free-enrichment-providers.md) compares free
enrichment providers (George asked 2026-09-17). Nothing decided; the provider
choice needs an ADR when Phase 8 starts. George: API keys are a per-user
setting, so a key is not a blocker (ADR-0022 inventory row added).

**The device** runs the Phase 6 image
(`2026-09-17-gexis-player-v0.2.1-202-gf3674f3-dirty.img`), flashed and
provisioned 2026-09-17. Both SSH keys authorized. **After every reflash**
append C3PO's key (`provision.local.env` carries R2D2's only; George chose
not to change `provision.sh`):
`ssh pi@gexis.local 'cat >> ~/.ssh/authorized_keys' < ~/.ssh/c3po_id_ed25519.pub`,
then `ssh-keygen -lf ~/.ssh/authorized_keys` on the device shows R2D2
`SHA256:UVfvJQXw…ci4` and C3PO `SHA256:d/pT3AST…tok`.

**Phase 6 is merged** (PR #18, 2026-09-17). George called the image checks
done without item-by-item results, so none is recorded as observed
(`docs/DEVELOPMENT.md` Phase 6 status).

**The loop-device question is still open, and the discriminating state is
recorded.** Background: the first R2D2 build (2026-09-17 11:35, log
`~/gexis-build-1-failed-loop.log`) failed at `export-image/prerun.sh` with
`mknod: invalid minor device number '/dev/loop0 (lost)'`; the rerun (12:40,
`~/gexis-build.log`) passed but started with `/dev/loop0` already present, so
it discriminated nothing. **After R2D2's reboot, before any build (13:37,
up 8 min):** `lsmod | grep -w loop` → `loop 45056 0` (autoloaded from
`/etc/modules-load.d/loop.conf`); `ls -l /dev/loop*` → only
`/dev/loop-control`, **no `/dev/loopN`**. No build has run since. **The next
`make image` on R2D2 is the test**, provided R2D2 has not rebooted and nothing
has created a loop node in between — re-record both before building. A pass
means `image/README.md`'s root cause (module not loaded) is right; a `(lost)`
failure means the missing node is the cause and autoloading does not prevent
it — then propose to George correcting the README and a durable fix (e.g.
pre-creating a node before the build; needs `sudo`).

**Docker group:** after the reboot `id` shows `docker` (950) directly;
`newgrp` is no longer needed. Run builds detached so the session's memory
guard cannot kill them:
`nohup setsid bash -c "make image > ~/gexis-build.log 2>&1; echo BUILD-EXIT=\$? >> ~/gexis-build.log" >/dev/null 2>&1 </dev/null &`.
Move the previous log aside first. The submodule shows `m image/pi-gen`
afterwards: expected, leave it.

**Development moved to R2D2 on 2026-09-17** (see Machines).
`~/provision.local.env.bak-c3po-key` (holds the Wi-Fi password) can be
deleted once George is happy.

**Phases renumbered 2026-09-16:** 9 is settings wiring and UI polish (new);
10 is the plugin contract; 11 Plexamp and 12 Qobuz Connect (new); 13 is first
boot.

**Issues to look at later (Phase 6 hardware rounds, 2026-09-16):**

- **Over Bluetooth, the Plexamp app reports pauses late or not at all** — about
  6 s from its own button, 4.5 s or never for a panel command. The Spotify app
  on the same phone reports in 0.2 s (Finding 028, addendum 2). A2DP's
  stream-idle signal comes 3 s after the report, so it cannot help. With
  Plexamp the panel's icon falls back after 8 s. Next step, with the speakers
  on: does Plexamp's audio stop at the tap?
- **LMS had player `gexis` on fixed volume (`digitalVolumeControl` 0), cause
  unknown.** George found it as "phone volume does nothing while the panel is
  muted, and LMS's volume bar is frozen". Measured 2026-09-16: with 0, LMS
  moves its own number but always sends full level, so no LMS volume change
  reaches the device, muted or not. Mute then became a trap, because the one
  change that ends it never arrived. Set back to 1 with George's OK; re-tested
  while playing: LMS volume reaches the DAC again, and a change while muted
  ends mute (ADR-0034). **George never touched it,** and nothing in this repo
  sets it; it worked on 2026-09-08 (Finding 008). **Checked after the 2026-09-17 reflash: 1.**
  Still unchecked after an LMS restart. Nothing warns when it is 0; a candidate for
  Phase 9.
- **Pausing LMS moved the DAC slightly** (dummy −47 → −50 dB, DAC 152 → 150)
  during the same test. Small, unexplained, not investigated.
- **After a `gexis-core` restart, a phone already connected is not active.**
  The Bluetooth adapter seeds metadata from a `MediaPlayer1` that is already
  present but never calls `on_acquire`. Spotify has the same effect. It only
  matters when the daemon restarts, not at boot.
- **LMS once reported a position about 5 s ahead on resume**, then corrected
  it at the next pause. Not reproduced on a second try; recheck with sound.

**Follow-ups, not blocking:**

- `viz_timeout` is read by the daemon but not wired in the settings registry,
  so the phone cannot change it (ADR-0035 says wire it with its feature).
- The stock skins are Volumio-branded; Gelo5's are the image default.
- Titles too long for their box are cut with "…"; the wrapper scrolls them.
- Fonts: DejaVu for text; DSEG7 (OFL) for time. PeppyFont not vendored.
- George once saw the spectrum overlap remaining time on `dash-spectrum`;
  not reproduced in 24 rotations or a direct start.
- **Lesson candidate:** hand-started test processes multiplied because pid
  files captured the wrong pid; George saw overlapping skins. Stop by looking
  processes up, not by trusting a pid file.

**Still open from earlier:** Claude Design owes drawn number/text editors and a
corrected `design/README.md`.

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
0  reproducible image                     ✓ merged — pi-gen, ADR-0021
1  measurements                           absorbed into 2 — needs 2's own renderers
2  audio layer + arbitration              ← in progress: renderers packaged and
                                             hardware-verified (criteria 1,2,4,5,6);
                                             Python core arrives here for 3-7; takeover gap
3  core state daemon                      no UI; test with a WebSocket client
4  UI shell + idle + display-only nowplay
5  visualisation service + Peppy screen   capability-blind, proves the model
6  now playing, full                      capability-driven controls
7  library browse                         typed queries + our screens; SlimBrowse
                                            for radio only (ADR-0030)
8  enrichment + lyrics                    additive only, cannot break playback
9  plugin contract hardening + themes     Qobuz is the fourth-renderer test
10 first boot without a network           setup access point; pull forward the
                                            moment a non-developer gets a device
                                            (ADR-0031)
```

## Things that will bite if forgotten

- **A reflashed card only has R2D2's SSH key.** `make provision` writes the
  one key in `image/provision.local.env`; C3PO's
  (`~/.ssh/c3po_id_ed25519.pub`) is appended by hand after first boot
  (George, 2026-09-17). Both keys are commented `desktop-to-dietpi`; compare
  fingerprints, not comments.

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
