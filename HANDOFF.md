# Handoff

Last updated: 2026-09-26 (twenty-sixth session, on R2D2 — **Phase 11 stays
complete and the contract stays frozen at v1. Two decisions were taken and built
today. ADR-0091: a takeover from Plexamp costs 0.9 s where it cost fourteen
seconds. ADR-0092: Plexamp can now take the device from a renderer that is
holding it, which it could never do — 0.55 s, from never. **George confirmed both
from his phone: *"Seems to work."*** Phase 11 stays closed, and the next phase is
12 - Qobuz - because George moved the Plex-metadata work to the end of the
queue.**)

## Start here

**[ADR-0091](docs/decisions/0091-a-plugin-renderer-is-taken-off-the-device.md) is
built and measured** ([Finding 089](docs/findings/089-the-takeover-after-adr-0091.md)).
Five commits, all landed separately so each can be reviewed on its own:

| | where | what |
|---|---|---|
| 1 | `arbitration.py` | the `sigterm_grace` and `sigkill_grace` rungs **poll** instead of sleeping blind — [Finding 016](docs/findings/016-polite-grace-blind-sleep.md)'s fix, which had only ever been applied to the polite rung |
| 2 | `adapters/plugin.py` | `PluginAdapter.signal_stop` always sends **SIGKILL** — a SIGTERM death is not a failure to systemd, so `Restart=on-failure` never fires and the renderer would not come back |
| 3 | `gexis-plexamp` | `polite_grace` **16.0 → 0.5** |
| 4 | `arbitration.py` | the ladder logs the **rung**, not a signal it no longer chooses |
| 5 | `plexamp.service` | `Wants=` moved to `[Unit]`, `StartLimitBurst` 5 → 20, `RestartSec` 5 → 1, and two `verify-image.sh` checks |

### Then ADR-0092, which George found by using it

He reported *"Cannot takeover with plexamp. The plexamp mobile app fails to
playback"* — and it was not ADR-0091. **Plexamp could not take the device from a
renderer that was holding it at all**, reproduced against LMS as well as Spotify.
The circle: Plexamp must open the ALSA device to start playing, and the plugin's
only evidence of an acquisition *was* playback starting.
[Finding 085](docs/findings/085-the-takeover-gaps-and-the-controls.md)'s
*"LMS → Plexamp, 0.2 s, five times"* was measured against an LMS that had already
let go, so this had never been tested.

[ADR-0092](docs/decisions/0092-a-play-queue-is-an-acquisition.md): a `playQueueID`
the plugin has not seen is the deliberate act, the refused timeline carries
everything needed to ask again, and `device_freed` — the hook ADR-0089 already had
for this — issues the play once the device is free. **No contract change.**
Measured at **0.55 s** from the controller's request to Plexamp holding a playing
LMS's device. Two commits in `gexis-plexamp`, none in the core.

**George has tried it from his phone** — *"Seems to work."* — which is the path
none of the measurements could reach.

### The image: built and verified, 2026-09-26

**`2026-09-26-gexis-player-v0.2.1-608-gd29ee48.img`**, 4.8 GiB, 700 s, manifest
annotated. `image/verify-image.sh` — **all checks passed**, including the four
that are new today:

```
ok   plexamp.service pulls the plugin in, from [Unit] where it counts
ok   the plugin tree is not nested
ok   the plugin in the image is the release it pins (a816fc5e7670)
ok   plexamp.service has the restart headroom a killed renderer needs
```

**The first attempt at this build was thrown away**, and it is the reason two of
those checks exist. `cp -a SRC DEST` copies *into* `DEST` when `DEST` exists, and
builds here run `CONTINUE=1` over a preserved rootfs — so the warm rebuild left
v0.2.0 in place and hid v0.2.1 at `src/gexis_plexamp/gexis_plexamp/`, which
`PYTHONPATH` does not import. The stage reported success in a second and the
verifier passed, because the file it looked for existed. Found by reading the
rootfs rather than the exit status; stopped at `export-image`, so no artefact
escaped.

**Still nothing booted.** The artefact is checked as a file, which
`docs/LESSONS.md` case 5 is explicit is not the same thing.

### Shipped: v0.2.1 is published and the stage pins it

`gcarstoiu/gexis-plexamp` **v0.2.1** is released, and
`image/stage-gexis/08-plexamp/01-run.sh` pins
`a816fc5e7670766a38288207a5add56ecf4d6df061e907011b9d5e799128553c`. **The pin was
verified against the published asset**, not assumed: downloaded after release and
compared, and separately `git archive --format=tar.gz --prefix=gexis-plexamp/` at
v0.2.0 was shown to reproduce *that* release byte-identically, so the command is
the release process rather than a guess at it.

Seeding the build cache to stand in for an unpublished asset was considered and
rejected on the way: `fetch-cached.sh`'s own comment says *"A build that has never
seen the cache has to work, or the cache becomes a hidden build dependency."*

### What it costs and what it bought

| | before | after |
|---|---|---|
| takeover, by the ladder's own clock | 12.6–14.2 s | **0.9 s** |
| device freed after the signal | — | **143 ms** |
| player answering again | never went away | **4.04 s** |
| six back-to-back takeovers | — | **nothing failed**, one restart each |

**The fifth commit is the one to read.** `Wants=gexis-plexamp.service` had sat
under `[Service]` since the stage was written, where systemd's answer is *"Unknown
key 'Wants' in section [Service], ignoring"* — so ADR-0090's *"one switch controls
the pair"* had never actually worked, and nothing noticed until a release ladder
started stopping the player for real. `verify-image.sh` now checks it **by
position**, because the key being present was never the part that was wrong.

**One claim was corrected the same day it was written.** ADR-0091 said the stale
"connected" clears because plex.tv's `presence` flips within ≤10.5 s. That was
measured on a unit that *stayed stopped*; with `Restart=on-failure` the player is
back in about a second and `presence` never flips — correctly, since a player you
cannot see is one you cannot cast back to. What changes is that the PMS session is
gone and the player reports `state="stopped"`.

### Why, in one paragraph

Plexamp gives the device back in ~14 s where LMS takes 0.4 s.
[Finding 088](docs/findings/088-making-plexamp-behave-like-the-other-renderers.md)
decomposed it: the stop is immediate (`BASS: Stopped in 0 ms`), output is
suspended at +3 s, and **the open PCM is held in `SETUP` for a further ~11 s**.
That is squeezelite's own behaviour — which is why `squeezelite.service` carries
`-C 1` — except that Plexamp exposes no `-C`, and **no runtime lever inside it
releases the device**: `audioDeviceUuid` re-initialises BASS and plays on,
`setSinksForSource` needs a mesh, `remoteControl` is not settable over HTTP at
all. The second complaint, the phone still showing the player as connected after
LMS takes over, has the **same single cause and it is ours**: the polite rung
polls for the whole of `polite_grace` and returns `POLITE` the moment the device
frees, so the rung always wins and the player is left running, registered and
claimed.

### The measurement that licences the design

| signal, `systemctl kill -s` | what systemd does |
|---|---|
| **SIGTERM** | unit `inactive`, `ExecMainStatus=15`, `Result=success`, `NRestarts=0` — **it does not come back** |
| **SIGKILL** | back by itself at t+0.6 s, `NRestarts=1`, plugin unit with it |

`pcm` stayed `closed` throughout both, and after a full restart: **Plexamp opens
the ALSA device when it plays, not when it starts.** That sentence is what makes
this safe. [Finding 013 §1](docs/findings/013-phase2c-attack-test-and-spotify-reliability-defects.md)'s
restart storm — shipped and reverted twice — needed a renderer that grabs the
device the moment it is back, and `LmsAdapter` carries the warning *"before
proposing a third."* **This is not a third attempt**: there is no restart hook,
`Restart=on-failure` is the only path back, and the storm's precondition is
absent by measurement.

### The four symptoms, and which of them are actually fixable

| | status |
|---|---|
| 14 s takeover | **fixed and measured: 0.9 s** (Finding 089) |
| phone still shows it connected after LMS takes over | **the cause is fixed** - the player is no longer left running and claimed. But `presence` does *not* flip (the restart beats the timeout); what changes is that the session is gone and the player reports stopped. **Whether the phone's chrome follows is unobserved** |
| panel waits for renderers until playback starts | **not fixable.** Nothing reaches the player when a controller selects it; ADR-0027 already says acquisition is deliberate |
| panel does not follow a phone disconnect | **not fixable, and not a defect.** A disconnect does not even stop playback, so the panel showing Plexamp as active is correct |
| *(found while testing)* could not take the device from a renderer holding it | **fixed and measured: 0.55 s**, from never (ADR-0092) |

The two "not fixable" rows are established across five places — the player's HTTP
routes, its timeline subscriber list, the PMS client table, the PMS session, and
pubsub — and corroborated by an independent implementation of the player side,
whose own source says *"Plexamp clients do not subscribe nor send wait=1."*
**Nobody needs to sweep this again.**

### The one lead still open

`/player/timeline/poll` is logged **zero** times by Plexamp, for any address,
including our own plugin which polls it every second. So the log shows commands
and not polls, and it cannot say whether the phone polls the timeline while it is
attached. **If it does, a sustained absence of polls is a real presence signal**
and the fourth row above stops being impossible. Answering it needs one
`tcpdump` on `:32500` while George's phone is attached — a minute of his time,
not a session's.

### Decision 2 is still George's, and independent of this one

The **Squeeze Plex Hub** route reaches the same DAC bit-identically
(`S32_LE 192000Hz 2ch` both ways, LMS handed the original `file.flac` from the
PMS, no transcode) and hands the device back in 1.0 s. It already advertises this
device's own squeezelite as a Plex target over GDM — it has been in George's
player list all along. The cost is that Plexamp's playback engine is replaced by
LMS's and Phase 11's plugin becomes a metadata shim. **Not rejected, not
started**, and ADR-0091 does not pre-empt it.

### Still open, and none of it blocking

- **Cross-rate takeover gaps.** Blocked since Phase 9, unchanged: a
  60,974-track scan found **zero** non-44.1 kHz files.
- **Gaps against Spotify and Bluetooth.** Neither can be made to take the device
  on request — they answer 409 to `activate`, correctly — so measuring them needs
  a phone.
- **Claiming** from the `claim_token` row. The row exists and the plugin accepts
  it; Plexamp's own setup still does the claiming. Not a Phase 11 criterion.
- **The Plex-metadata work is now phase 15**, last in the queue, after themes -
  George moved it there on 2026-09-26. It was 11a, sitting immediately next. It is
  drafted and not started, and still needs an ADR for where the Plex credential
  lives. [Finding 086](docs/findings/086-what-the-plex-server-could-answer.md) is
  the measurement it would be built on.
- **Plex lyrics.** `/library/streams/<id>` 404s for every one of 40 `lrc` streams
  sampled, unexplained.
- **A boot.** The image carries everything; **nothing built from it has been
  run.**
- **Everything is pushed.** `gexis-plexamp` `main` is pushed and released as
  **v0.2.1**, and `gexis-plexamp` has nothing outstanding.
- **Nothing outstanding.** PRs [#28](https://github.com/gcarstoiu/gexis-player/pull/28),
  [#29](https://github.com/gcarstoiu/gexis-player/pull/29) and
  [#30](https://github.com/gcarstoiu/gexis-player/pull/30) are all merged, R2D2 is
  **on `main` at the #30 merge**, the tree is clean, and
  `phase-11-plexamp-plugin` is fully merged and can be deleted whenever somebody
  wants to. `gexis-plexamp` `main` is pushed and released as **v0.2.1**.
- **Three PRs for one session**, because each merge landed while work continued on
  the same branch. Worth avoiding next time by branching again after a merge
  rather than pushing onto a branch whose PR has already gone in.

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
                                            for 10, replacing Qobuz. Its
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
12 Qobuz Connect as a renderer            <- next. a second plugin against a
                                            contract already proved; keeps the
                                            private repository out of the
                                            critical path
13 first boot without a network           setup access point; pull forward the
                                            moment a non-developer gets a device
                                            (ADR-0031)
14 themes                                 cut out of 10. ADR-0016 calls themes
                                            plugins and plugins processes; a
                                            theme has no process - settle that
                                            first
15 the library answers for itself         moved here 2026-09-26 (George): "the
                                            entire discussion and in between
                                            phase for enrichment via Plex server
                                            gets [moved] to its own phase at the
                                            end of the phase queue after themes".
                                            Was 11a, inserted before Qobuz on
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

- **Restarting `gexis-core` does not reload the panel.** `ui/dist` rsynced to
  `/opt/gexis-ui` reaches Chromium only on a page load, so a probe run after a
  daemon restart measures the *old* bundle faithfully and reports that the
  change does not work. `Page.navigate` to the same URL over CDP on 9222.
  [LESSONS](docs/LESSONS.md) 38, and it cost a wrong result on 2026-09-25.

- **A flash wipes everything the device learned.** Both databases live on the
  card — `/var/lib/gexis-core/settings.db` and `enrichment.db` — as do BlueZ's
  pairings. **ADR-0022's `backup` row is inventoried and unwired**, so nothing
  on the device exports either. **A manual copy was taken 2026-09-25**, and it
  is the shape to repeat before every flash:

  ```
  ssh pi@gexis.local 'sudo tar -czf /tmp/gexis-state.tgz -C / \
      var/lib/gexis-core/settings.db var/lib/gexis-core/enrichment.db \
      etc/gexis/core.toml etc/gexis/device-name.env
    sudo tar -czf /tmp/gexis-bt.tgz -C / var/lib/bluetooth
    sudo chown pi /tmp/gexis-*.tgz'
  scp pi@gexis.local:/tmp/gexis-{state,bt}.tgz <somewhere outside this repo>
  ```

  **Outside the repository, always.** `core.toml` carries `idle_url`, a
  per-display identifier that must never be committed. The 2026-09-25 copy is
  in `~/gexis-backups/2026-09-25-pre-flash/`: 41 stored settings including all
  three secrets, 3,664 enrichment rows, 7,061 notes, and the phone's pairing.

  **After a flash, in this order:**

  1. **The two keys and the token**, which have no default and nothing can
     guess: `fanart_key` (without it, portraits come from LMS only),
     `wallpaper_key` (Pixabay, ADR-0047), `listenbrainz_token`.
  2. **`idle_url`** — deliberately *not* in the image's `core.toml` because it
     carries a per-display identifier and this repository is public. Until it
     is set, the idle screen falls back to the built-in clock.
  3. **`weather_location`**, **`timezone`**, **`device_name`** if not `gexis`.
  4. **Re-pair the phone.** BlueZ's store went with the card.
  5. **Run both sweeps** — artist portraits and album covers. `enrichment.db`
     held every one and it is gone, so the library starts with LMS's pictures
     and nothing else. Roughly seven minutes and 45–50 minutes respectively,
     measured 2026-09-24.
  6. **Append C3PO's SSH key** — see below.

  **What survives without being touched:** `lms_server`, baked into the
  image's `core.toml`, and any row George never moved off its default.
  **That is fewer than it looks.** The 2026-09-25 backup shows
  `spectrum_smoothing` at **62** against a registry default of 90 — so
  ADR-0058's ballistics are *not* all at their defaults, and an earlier note
  here claiming they were was wrong. `meter_fall` (400 ms) and
  `meter_smoothing` (240 ms) do match.

  **Restoring wholesale carries dead keys.** That DB still holds
  `per_renderer_volume` and `boot_volume`, rows deleted on 2026-09-23 with the
  machinery behind them, and `idle_brightness`, which the registry now calls
  `background_brightness`. Harmless — `Settings.value` reads the registry, not
  the store — but a restore is not a reason to stop reading what it contains.

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
