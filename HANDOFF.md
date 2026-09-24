# Handoff

Last updated: 2026-09-24 (twenty-third session, on R2D2 — **Phase 9: 9a
through 9j are done and passed on the device. The visualiser's four faults
are fixed and measured, its ballistics are three settings, and 9k — the
library's pictures from fanart — is built, with the portrait sweep run on
George's own library. Criterion 0 has the panel measured: the still screens
are at 0.00 %, and every scroll's cost is the background's two blurs. The
image predates all of it**)

## Start here

**Phase 9's volume work is done and passed.** 9i (the level) and 9j (which
output) were built, checked on the device by George and merged into the
branch; the narrative is in
[`docs/HANDOFF-ARCHIVE.md`](docs/HANDOFF-ARCHIVE.md) under 2026-09-23.
**Everything since is the visualiser and 9k.**

### What happened after his pass, and what it cost to find

**The visualisation had four faults, three of them one symptom.** George
kept reporting "the spectrum is flashing" and each fix was correct,
measured, and not the whole answer — [LESSONS](docs/LESSONS.md) cases 22–26
are the record of that, and case 25 is the one to read.

1. **The bars overflowed their frame**
   ([Finding 049](docs/findings/049-the-spectrum-draws-more-bars-than-it-has-room-for.md)).
   The engine draws one global bar count for every skin. **`steps` is not
   the bar count** — ADR-0015 said it was and it is the *vertical*
   quantisation — so the count is now what the artwork holds, `origin.x`
   mirrored on the right because the picture has a frame, **one number for
   the whole corpus** because the engine reads it once and the relay
   re-reads it.
2. **Two skins drew the spectrum's blank panel as their dial**
   ([Finding 050](docs/findings/050-two-skins-name-the-wrong-background.md)).
   `111G5_Teletronix S+M` and `107G5_Marantz S+M` named the wrong file. The
   image corrects both and a build check refuses any skin that repeats it.
   **`skins.BROKEN` is empty**; `108G5_Kenwood Rev S+M` was never broken.
3. **The pipe had no frames in it**
   ([Finding 052](docs/findings/052-the-spectrum-pipe-had-no-frames-in-it.md)).
   peppyalsa wrote the thirty bands as thirty separate writes, so a poll
   landing mid-frame spliced two frames together. **The image now patches
   peppyalsa to write each frame in one call.** Measured: 1 read in 239
   ended mid-frame before, 0 of 891 after.
4. **The meters follow the volume**
   ([ADR-0057](docs/decisions/0057-the-meters-follow-the-volume.md)), at a
   third of the dB — the volume's 60 dB onto a dial drawn for 20. The tap is
   upstream of the DAC, so the daemon publishes what it is cutting and the
   relay applies it.

**And [ADR-0058](docs/decisions/0058-the-visualisations-ballistics-are-settings.md):
three rows** under *Meters and spectrum tweaks* — spectrum smoothing 90%,
needle fall 400 ms, needle smoothing 240 ms — each note opening with the
value to come back to. **Those three defaults are where the tuning ended,
not where George has settled.**

**[Finding 053](docs/findings/053-fixed-output-crashed-the-daemon.md): fixed
output crashed the daemon.** Found by a check George asked for on a detail.
Deleting the per-renderer volume memory left one call behind, on the one
path only fixed output takes. Fixed and verified; the mode works.

### 9k — the library's pictures, built 2026-09-24

[ADR-0059](docs/decisions/0059-artist-portraits-in-the-list.md), on
[Finding 054](docs/findings/054-what-lms-knows-about-artist-identity.md).
**Two buttons in Settings → Enrichment**, fanart first with LMS as the
fallback, everything re-asked on every press, progress in George's own
words.

- **The portrait sweep is measured and done on his library: 917 of 917 in
  seven minutes, 525 found.** 759 distinct answers stored, 492 with a
  picture — so **about 43% keep LMS's photo**, which is fanart's coverage
  and not a fault. The grid will look mixed.
- **One walk serves both buttons.** fanart returns an artist's albums in the
  artist call, so a cover sweep makes no per-album request, and the
  release-group ids come from a 145 ms *lookup* rather than the search
  endpoint that 503s.
- **LMS cannot hold the MusicBrainz ids for us** (Finding 054 §10): no write
  path in its API, and the plugins in that space import tags rather than
  write them. A household that wants this shared tags its files with Picard.
- **Enrichment's four dead rows are wired** — the master toggle, lyrics and
  artwork each became a reason not to *ask* a provider; the confidence
  threshold is read on every ask and now gates the sweep too.

### Where it stands right now

- **The album-cover sweep was still running** when this was written — ~917
  artists at about 3 s each, so **45–50 minutes**, more than the 25–30 first
  estimated. Its number is in the settings row.
- **The image is a long way behind.** It predates all of the above.
- **Waiting on George:** the three ballistics defaults, whether the
  mixed look of the artist grid is acceptable, and **the background's blur**
  (below).

### Criterion 0 — the panel measured, 2026-09-24

**Steps 1 and 2 are done: the still screens are at 0.00 %.** A pulsing badge
and a progress bar animated with `width` were what an untouched panel was
paying for (Findings 056 and 057); both are gone.

**Step 3, the scrolls, is answered — and it cost two retractions.**

- **[Finding 058](docs/findings/058-what-the-scrolls-are-not.md) withdraws
  two of Finding 055's numbers.** The instrument counted dropped frames the
  compositor had marked as not affecting smoothness, so **every figure it
  had ever printed was high by roughly a factor of two**; and
  `queue-rail-scroll` was measured on a sixteen-track queue that **moved
  0 px**, which makes the claim that ADR-0041 took the rail from 13.9 fps to
  50.0 unsupported. `albums-scroll` moved 191 px against the grid's 574.
  **Finding 055's table needs re-taking** — a corrected one is in 059.
- **The harness now refuses both mistakes**, swipes the same 170 px in every
  scene, and prints how far each run actually travelled.
- **[Finding 059](docs/findings/059-what-the-panel-pays-for-its-blur.md)
  names the cause: `filter: blur()` on `PanelBackground`.** A blur is
  re-evaluated over whatever area a frame damages, so the cost is the
  scroller's *area* and nothing about its contents — which is why Finding
  058's eight candidates were all negative. Suppress both blurs and the
  artist grid goes **25.6 fps / 33.81 % → 54.4 fps / 1.61 %**. The queue
  rail, which sits on an opaque plate that occludes the blur, does not move.
- **Layer promotion does not help and a smaller radius does not help**: a
  9 px blur costs nearly what 70 px costs. Only `filter: none` does.

**The fix that works, measured: hand the browser a small picture instead of
a filter.** The artwork URL carries its own size, so a 16 px cover stretched
over the panel *is* a blur, with no filter at all — **44.7 fps / 6.50 %** on
the artist grid, within 1 fps of removing the background altogether.

**This is a product decision, not a build task.** It changes the look twice:
`saturate(1.7)` is a filter too (keeping it costs ~2 fps), and the weave
loses its blur unless it is baked into an image — it is static, so baking
keeps it exactly. Nothing is implemented; **an ADR comes first, and George
has not yet ruled**.

### Next

Criterion 0 step 3's remainder: **the queue rail's own 17.9 %**, which is
immune to the background and is a separate question, and **why every list
scrolls on the main thread at all** — Finding 032 blamed its own synthesised
touches for that, and with real touches it is still true, so that caveat is
resolved in the other direction.


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
8  enrichment + lyrics                    <- next. Additive only, cannot break
                                            playback.
                                            Needs an ADR choosing the providers
                                            first (Finding 030)
9  settings wiring + UI polish            <- next. Every ADR-0022 row wired or
                                            scoped out; criterion 0 is the
                                            panel reaching Phase 7a's target
10 plugin contract + themes               Qobuz is the fourth-renderer test;
                                            a Beszel agent is the test that
                                            the contract carries a non-renderer
                                            (George, 2026-09-18)
11 Plexamp as a renderer                  starts with the hardware check: does it
                                            release the device? (ADR-0008's
                                            reversal condition)
12 Qobuz Connect as a renderer            the plugin that proves 10
13 first boot without a network           setup access point; pull forward the
                                            moment a non-developer gets a device
                                            (ADR-0031)
```

Phases 9-13 were renumbered on 2026-09-16 (George). `docs/DEVELOPMENT.md`
holds each phase's acceptance criteria; this list is only the order.

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
