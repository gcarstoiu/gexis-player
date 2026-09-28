# Handoff

Last updated: 2026-09-28 (twenty-ninth session, on R2D2).

## Start here

> **First thing, before anything else: remind George to run these two, then
> check the repository is gone (`gh repo list gcarstoiu`).** He asked for the
> reminder on 2026-09-28. The code, both tags and both releases are in the
> local archive (bundle verified, tarballs match GitHub's sizes); see
> `docs/SESSIONS.local.md`. Deleting cannot be undone, so George runs it:
>
> ```
> ! gh auth refresh -h github.com -s delete_repo
> ! gh repo delete gcarstoiu/gexis-<the withdrawn plugin's repo> --yes
> ```
>
> The repository's name is in `docs/SESSIONS.local.md` (this file is public).

**Phase 13 (first-boot setup, ADR-0031, ADR-0104) is built through step 3 on
`phase-13`, PR #37, and every step was run on gexis with George.** The image
for step 4 is built and verified:
`image/deploy/2026-09-28-gexis-player-v0.2.1-746-g14b1a95.img`, sha256
`989cdb17…7bed`, 81 `verify-image.sh` checks, the setup modules and the UI
bundle identical to the branch, no `/var/lib/gexis`, no saved Wi-Fi, no `wlan`
rfkill state. **George flashes it on a second card** (gexis's own card stays).

**Step 4's card: Option A (George, 2026-09-28).** Only Claude's SSH key goes
on it, **by hand** into the card's `firstrun.sh` (`SSH_PUBKEY=`, from
`image/provision.local.env`) - no Wi-Fi, name or time zone. `make provision`
cannot do that: it writes every field of its env file. The card is left in
R2D2 after flashing; **identify it with `lsblk` and tell George which device
before writing anything.** SSH on is the one way the card is not blank; setup
still sees a new device (no saved Wi-Fi), and the Wi-Fi country stays unset.
Without the key nothing could be read afterwards: not criterion 4's name, not
the country.

**Owed before PR #37 merges (George, 2026-09-28: "Before"): Phase 9
criterion 0's revisit.** Phase 9 closed with the panel's screen *opens* below
the floor on George's judgement (30-53 fps and 2.5-5.6 % dropped against 55 and
2 %; ADR-0076, Finding 067), and DEVELOPMENT.md says to revisit it *before
Phase 13 is implemented*, because setup is where the panel becomes a
stranger's. **It was missed when Phase 13 started** - Phase 13's own section was
read, not the obligation Phase 9 attached to it. The measured lever is the home
screen's teardown, ~190 ms of a ~280 ms transition.

**Decision owed (George, no hurry):** make `outputs.resolve`'s fallback prefer
a HAT over the Pi's own outputs. Today a card whose DAC is not the
`sndrpihifiberry` the shipped `output.conf` names falls back to the first output
with a volume control, likely the headphone jack; setup's Output step lists the
DAC but starts on the jack. George asked whether a HiFiBerry/IQaudIO DAC+ would
be recognised: listed by its own name if its EEPROM identifies it, read from
the code, never tried.

Step 4 is next: an image from `phase-13` on a card flashed with nothing pre-seeded (the
new-device path: setup network after 15 s, the "Set up gexis" hero, the name
reaching all four places, the Wi-Fi country on a card that never had one).

| Step | Commits | On gexis |
|---|---|---|
| 1. The core decides on setup, holds the setup network, retries every 5 min | 931e4d8 | open in 3.9 s; a phone on it left alone; home Wi-Fi back 3.6 s after the scan |
| 2. The panel shows the way in: network, password, two QR codes | 44dd4de | George joined and opened the page from both codes |
| 3. The phone's setup page; the core keeps the answers and applies them | cfa30d0 | wrong password refused in 14 s, setup back 0.7 s later with the reason, page resumed on Network; right password joined in 10 s |
| After George's review | b0e403c, 8de9e51, 4280626, 96337ff, da803f6 | Continue on Network goes to Review after a failed join; `clock_format` setting (Settings and setup); compact Display tiles; the panel's hero with a large icon (photographed: open, joining, failed); the reason from NM's `Error:` line, not its hint |

**Testing on gexis (no Ethernet):** a file `/run/gexis-setup-trial` with
`retry=<s>`, then restart `gexis-core`: the core opens the setup network over
the working Wi-Fi, and its own retry gives the Wi-Fi back once no phone is on.
Arm a transient guard timer as well (`image/tools/ap-trial.sh` shows the
shape). Screenshots during a trial: `systemd-run --uid=pi --on-active=N` with
`XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 grim`. **A trial that
finishes setup leaves a profile named after the network and `setup-done`;
remove both** (done after each run today).

**Not tested yet:** the new-device path and its hero; a rename (restarts the
device); changed time zone, output or Headless through setup; hidden and open
networks; Ethernet; the page on an iPhone. The phone page was seen by George
only, not photographed.

### Branches and PRs

| Branch | State | What is on it |
|---|---|---|
| `main` | 66d931e | Everything to PR #36: Phase 12/12b, the phone mini player and grim (PR #35), Debug logs (PR #36, ADR-0103) |
| `phase-13` | ahead of `main`, pushed | ADR-0031 amended; ADR-0104; Finding 099; `ap-trial.sh`; Phase 13 steps 1-3 and George's review (above); ADR-0022 rows: Run setup again [N], thresholds [H], Wi-Fi country [H], clock format [N] |

### gexis

- Flashed 2026-09-28 with `image/deploy/2026-09-28-gexis-player-v0.2.1-730-g66d931e.img`
  (sha256 `942d8582…eb79`, 80 `verify-image.sh` checks pass), provisioned, and
  George's backup restored. **Restore, then download worked**: Plexamp was
  fetched at boot in 31 s and runs. Not yet checked: that it came back signed
  in, and Remove on Plexamp.
- Runs `phase-13`'s core and UI **installed by hand** (not in an image), and
  `ap-trial.sh`. On its Wi-Fi it behaves as before: setup not needed. Its
  setup password is `naccw4n2` (in `/var/lib/gexis/setup-password`).
  `python3-pytest` is not reinstalled yet.
- The core's tests run on R2D2 from a venv: `python3 -m venv <dir>` and
  `pip install -e 'core[test]'` (none existed this session).
- It holds a saved connection "Pixel 10 Pro Network" from the restore - one of
  the configured networks ADR-0031's 5-minute retry would look for.

### Decided, not started

- **Phase 13a, plugins you install and update** (George, 2026-09-28: a phase
  set before themes). Criteria in DEVELOPMENT.md. Its ADR comes first.
- **Settings as an installed app: not now** (ADR-0102). The HTTPS routes are
  kept there for later.

### Open, none blocking

- **LMS's power-on reaches the core 1.45-1.5 s after the press** - LMS's own
  status-push filter, now most of what is left of Finding 091's gap. A plain
  CometD subscription or the CLI's `listen` would be immediate (ADR-0095, *Not in
  this record*). **George, 2026-09-28: recorded, no action; he will watch for it
  in normal use.**
- **Bluetooth "Not provided", once**, 2026-09-26 22:08: `MediaPlayer1` appeared and
  no track information ever followed. George could not reproduce it the next
  morning and suspects the phone's battery saver. Not explained.
- **A paused Spotify is not an acquisition after a core restart**, and a later
  resume sends no `active` - so the core does not know Spotify took the device.
  Needs a restart during a pause to happen. Seen, not fixed. **George,
  2026-09-28: recorded, no action; he will watch for it in normal use.**
- **The Restore row reads "4 paired"** (seen 2026-09-28): a list row's count is
  labelled "paired", Bluetooth's word, for backups too. Cosmetic, not fixed.
- **A phone that opens `/` posts `/panel/painted`** (seen in Finding 099's
  trial). That call ends the boot animation (ADR-0043 §3), so a phone opening
  the page during boot would drop the splash before the panel draws. Read
  from the code, not seen happen.
- Everything older that is still open is in the archive's 2026-09-27 block:
  the Squeeze Plex Hub route (decision 2), the timeline-poll lead, cross-rate
  gaps, Plex lyrics.

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
13a plugins you install and update       decided 2026-09-28 (George): a phase
                                            before themes. Upload a plugin from a
                                            phone or computer, run it sandboxed,
                                            Remove it; updates from versions we
                                            have tested. ADR first
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
