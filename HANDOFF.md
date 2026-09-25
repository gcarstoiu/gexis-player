# Handoff

Last updated: 2026-09-25 (twenty-fourth session, on R2D2 — **Phase 9 is
COMPLETE. All five criteria closed on George's own word, in one session:
criterion 0 on lived judgement with the opens below the floor, 1 with every
surfaced settings row acting, 2 with the check that was lying about two rows
fixed, 3 with his review's three findings, 4 with the handoff's own list
triaged. Next is Phase 10, the plugin contract.**)

## Start here

**Criterion 0 is closed** and
[ADR-0076](docs/decisions/0076-criterion-0-closes-with-the-opens-below-the-floor.md)
says so honestly: the scrolls reach 56.9–59.5 drawn/s at 0.00 % dropped, and
**the screen opens are 30–53 fps at 2.5–5.6 %, below Phase 7a's floor of 55
and 2 %** ([Finding 067](docs/findings/067-what-the-panel-presents-at-the-end-of-criterion-0.md)).
George closed it on lived use — *"the panel feels fast based on current
interaction"* — not on the numbers. **Revisit before Phase 13**, the setup
phase, when the panel stops being his.

**Phase 9 is complete**, and the five closures are recorded where they were
written — `docs/DEVELOPMENT.md`, each struck through with the closure above it
and the original text kept below.

- **0 — the panel meets Phase 7a's target.** Closed on lived judgement, not on
  the numbers: scrolls reach 56.9–59.5 drawn/s at 0.00 % dropped, **the opens
  are 30–53 and 2.5–5.6 % against a floor of 55 and 2 %**
  ([ADR-0076](docs/decisions/0076-criterion-0-closes-with-the-opens-below-the-floor.md)).
  **Revisit before Phase 13.**
- **1 — every ADR-0022 row wired or scoped out.** Checked against the running
  daemon: of 74 rows, no surfaced row is unwired and none carries a `?`.
- **2 — no unwired UI remains.** Four generated lists. It found one thing, and
  the thing was the check
  ([Finding 071](docs/findings/071-what-the-panel-shows-that-does-nothing.md)).
- **3 — the review pass with George.** Three issues, all fixed.
- **4 — the handoff's issues triaged.** Ten items
  ([Finding 074](docs/findings/074-the-handoffs-issues-triaged.md)).

### What was wired this session

Three commits, in this order, each verified on the hardware before the next:

1. **The device says which build it is.** `version` and `image_build` read
   `/etc/gexis/image.info`, which the image now writes — nothing on a running
   device could report it, because the `.info` beside the image is on the
   build host. A device flashed before that stage existed says `unknown`
   rather than showing an empty row.
2. **Three handoff rows** — `restore_transport`, `show_transition`,
   `handoff_duration` — read where they are used, so none needs a callback.
3. **Reclaim, and the two Bluetooth rows.** `reclaim_lms` takes the device
   back for LMS when a session ends, **off by default and opt-in by row**:
   ADR-0027 declines to do it, and the reclaims that were measured were
   spurious — a Spotify session ending because a phone locked would drag LMS
   back on. `bt_pairing` needed more than storing, because the capability is
   fixed when the BlueZ agent registers and `NoInputNoOutput` means BlueZ
   never asks at all — so a change unregisters and registers again.
   `bt_autotrust` was read per request already and simply was not settable.
   **ADR-0022's note for it was stale**: there is no
   `gexis-bluetooth-trust.service` in the image; the agent does the trusting.
4. **[ADR-0077](docs/decisions/0077-a-source-that-is-off-is-not-running.md):
   a source that is off is not running.** The last four rows — the three
   `Enabled` toggles and `headless`.
5. **The two orange dots**, both found by George reading the screen. The dot
   means a row's marks carry `?`, a decision still owed. `version` and
   `image_build` were still asking one that had been answered when they were
   wired; `version` says `unknown` correctly on this image, and `built` now
   falls back to `/etc/rpi-issue`, which pi-gen writes on every image, so it
   reads **2026-09-19**.
6. **[ADR-0078](docs/decisions/0078-the-transition-screen-waits-for-the-threshold.md):
   the transition screen waits for the threshold.** `handoff_threshold` showed
   `1` with no slider because a `number` row only draws one once it is wired —
   and it had stayed unwired because **nothing had ever read it**. It now means
   how long a takeover has to be in flight before the panel explains it; 0–3 s
   in 0.5 s steps, 0 being the old behaviour. Five runs on the panel
   ([Finding 069](docs/findings/069-the-transition-screen-against-the-threshold.md)).

### ADR-0077, because it is the one with teeth

Off means the renderer's unit is stopped **and disabled**, its adapter is not
watching, the state reports it unavailable, and arbitration refuses it. Three
things worth carrying forward:

- **Disabled, not just stopped.** A row whose effect ends at the next boot is
  a row that lies the second time you look at it.
- **A row only the panel honoured would not be a switch.** Spotify Connect is
  advertised on the network, squeezelite is a player in the LMS app, and a
  Bluetooth device is in a phone's settings screen. So Bluetooth off **powers
  the radio down** as well as stopping `bluealsa-aplay`, and disables the unit
  that unblocks rfkill at boot.
- **The gate is in the core, not the adapters.** ADR-0013 says the three
  defaults implement the public plugin contract; a plugin that read a settings
  row named after itself would put that row in the contract. The adapter's
  `run()` is wrapped instead. That also ends what would have been permanent
  noise — with go-librespot stopped, the Spotify watch retried every five
  seconds forever.

**`systemctl disable --now go-librespot.service` measured 7.0 s**, all of it
stopping the unit, so the call goes through `asyncio.to_thread`. Inline it was
seven seconds in which the daemon answered nothing. After: the row's own `PUT`
returns in 18 ms and the next request in 5 ms while the unit is still stopping.

**`headless` stops three units** — kiosk, visualiser, and the panel warm-up
that is pure boot cost with no kiosk to warm for. Turning it on from the panel
closes the panel; it is reversible from a phone, and only from a phone. 12 s
to the panel gone, 20 s to it back.

7. **[ADR-0079](docs/decisions/0079-with-lms-off-the-panel-is-two-screens.md):
   with LMS off, the panel is two screens.** George's answer to the question
   ADR-0077 left open — *"Library, browse and radio go with it."* Nothing
   playing is the waiting marks at 1.8× with a settings icon in the corner;
   something playing is Now Playing as the root, Home button become Settings,
   artist line inert, no mini strip. **The row decides it, not
   `availability.lms`**, which also goes false when the server is merely
   unreachable. Six states on the panel
   ([Finding 070](docs/findings/070-the-panel-with-lms-off.md)).

**Both dots are gone**, and no surfaced row carries a `?` any more.

**And building screen 7 found a bug in ADR-0077**: switching off the *active*
renderer left it active forever, because cancelling its watch is also how the
release event stops arriving. The panel showed a stopped Spotify's track,
artwork and progress bar indefinitely, while the same payload said the renderer
was unavailable. Fixed with one `relinquish`; [LESSONS](docs/LESSONS.md) 39 is
the part worth keeping.

### Where it stands right now

- **`gexis` runs the flashed image**, not an rsynced tree —
  `2026-09-25-gexis-player-v0.2.1-513-g8cbff39.img`, on a **new card**. The old
  one is kept intact and untouched, which is a better fallback than any
  archive. **Phase 9 holds on it**: no orange dots, no visible-and-unwired row,
  and `version` finally reports the build instead of `unknown`
  ([Finding 076](docs/findings/076-the-first-flash-since-the-settings-work.md)).
- **George's state was restored onto it** from the pre-flash copy: 41 settings,
  3,664 enrichment rows, the phone's pairing, and `idle_url`. Checked usable
  rather than merely present — 8 of 8 artist portraits served from the cache.
- **PR #26** is open with everything: https://github.com/gcarstoiu/gexis-player/pull/26
- **[ADR-0083](docs/decisions/0083-a-backup-leaves-the-device.md) is rsynced on
  top, not in the image.** Backup, the share and a restore round trip are all
  verified on the hardware; the image *stage* that installs the share has not
  run. **The next build is what proves it** - and until then a flash still
  needs the hand copy above.
- **The album-cover sweep has not been re-run** since the raw-name and
  collaboration fixes. 82 newly placed artists would now find release groups.
  George's low-cover report turned out to be the Bluetooth path (ADR-0080), so
  this is still owed and still unmeasured.

### Next — Phase 10, the plugin contract

**Planned 2026-09-25 and reshaped by three of George's decisions**: themes
leave for Phase 14, the three default renderers **stay in the core process**,
and **Plexamp replaces Qobuz** as the contract's fourth-renderer proof, because
Qobuz needs a partnership and a private repository and that put the only proof
two phases out.

Keeping the defaults in place makes ADR-0013's claim — *"implemented against
the public plugin contract, not special-cased"* — untrue as written, so
[the record is amended](docs/decisions/0013-defaults-implement-public-contract.md):
they are the contract's **source**, not its consumers, and
`core/tests/test_contract_surface.py` pins the surface so the wire schema and
`Capabilities` cannot drift apart in silence.

**The order, and the reason for it:**

1. ~~**The Plexamp hardware check**~~ — **done 2026-09-25**
   ([Finding 077](docs/findings/077-plexamp-on-gexis.md)). Plexamp headless
   4.13.2 is installed and claimed on the device. **It can be a renderer**: a
   commanded stop works, it frees the ALSA device and keeps running, so
   ADR-0008's reversal is not triggered. Two things to carry into Phase 11 —
   the device is held for a deterministic **14 s** after the stop, so its
   `release_ladder` needs a longer polite grace than the default; and **the
   audio path does not work for the meters**, because it opens `hw:5,0`
   directly rather than `pcm.output`, in **S32_LE**, which is the format moOde
   measured as giving an all-zero peppyalsa FIFO.
2. ~~ADRs: the transport~~ — **done**, George took the recommendation:
   [ADR-0084](docs/decisions/0084-plugins-speak-json-lines-over-a-unix-socket.md),
   a Unix socket carrying JSON lines. The plugin channel can claim the audio
   device and lie about what is playing, which is not the class of thing
   ADR-0028 left open on the LAN.
3. ~~Draw the contract from `Adapter` and `Capabilities` as they are.~~ —
   **drafted**: [`docs/PLUGIN-CONTRACT.md`](docs/PLUGIN-CONTRACT.md), version
   1, **and deliberately not frozen**. It freezes after a non-renderer has
   been built against it, not before. `test_contract_surface.py` now checks
   the document against the objects as well as the objects against
   themselves, which is the drift guard ADR-0013's amendment promised.

   **The `kind` split is the part to attack**: `renderer` declares a unit, a
   release action and capabilities; `service` declares a unit and nothing
   else. If a Beszel agent cannot be said as a `hello` with
   `kind: "service"`, the contract is wrong.
4. **Discovery — the mass of the phase.** `"lms"` appears in **six core
   modules outside `adapters/`** and **ten UI files**, so "no core changes"
   means a manifest, a scanned directory, and settings rows and source artwork
   arriving from the plugin. The unsurfaced `plugins` row is where it lands.
5. The **Beszel agent** against the draft, *before* freezing it — it is the
   test that the contract carries something with no metadata, no transport and
   no claim on the audio device. **The machinery it needs is built**: a
   service connects over the socket, is welcomed, and appears in the payload
   as `kind: "service"` with no accent, status or mark — checked on the device
   with a throwaway manifest. What is left is the agent itself and the
   question of where its hub lives.
6. Freeze v1. Criterion 2 closes in Phase 11.

**Still open inside discovery:** a plugin's **settings rows** merged into the
registry, and writes reaching it over the socket. And **arbitration does not
carry plugins yet** — a `renderer` that connects is welcomed and idle, and the
log says so rather than pretending otherwise. Both are adapter-shaped work:
an `Adapter` built around a session and registered with the supervisor.

**Read [Finding 075](docs/findings/075-what-moode-learned-about-plexamp.md)
before starting.** George's moOde project built a Plexamp route and **parked
it**: pause and app-dismissed are byte-identical at every observable endpoint.

**That phrase is narrower than it sounds, and the second export settles it.**
It was about the *HTTP endpoints*. Plexamp on `:32500` turns out to fit
ADR-0010's ladder without bending:

| our contract | Plexamp, per moOde |
|---|---|
| `release()` — the polite stop | the API stop at `:32500`. Frees the DAC, leaves Plexamp running |
| `signal_stop(force)` | kill the unit — which needs a restart, so it is rightly the second step |
| `on_release` | **TCP count to `:32500` reaching 0**, seconds after the app goes away |

So **Plexamp looks viable**, on someone else's machine, with two gaps neither
project has measured: the stop test's "before" read was empty, and nobody knows
what the TCP count does after an API stop — if our own `release()` drops it,
the adapter reads its own polite stop as a user disconnect.

The finding also carries two smaller things — our `output.conf` pins no sample
format, and peppyalsa gave moOde an all-zero meter FIFO for S32_LE.

**Three decisions are open and labelled in the ADRs**, none blocking:

- **Is 1.8× the right scale for the waiting screen?** A judgement, not a
  measurement: two services come to 680 px of the width and about 300 px of the
  height. George asked for *"not the entire height and width of the screen"*
  and this is the reading of it.
- **Should turning `headless` on hand tty1 back to a getty?** Today the screen
  goes blank until the next boot, which then reaches a login prompt normally
  (the kiosk's `Conflicts=getty@tty1` stops the getty and systemd does not
  start it again). Measured on the device.
- **Should `handoff_exempt_pairs` survive?** With a working threshold it
  changes no outcome — both its pairs are far under any value the bar offers.
  It stays because it is measured evidence and because removing published
  state is Phase 4 criterion 4's business (ADR-0078).

**And the device has a hardware flag worth George's eye.** `vcgencmd
get_throttled` read `0xd0000` last session: under-voltage, frequency capping
and the soft temperature limit have all *occurred* during that uptime —
historical bits, none current, at 74.5 °C and a full 1.8 GHz. Not a UI
measurement, but it is the kind of thing that makes measurements wander.

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
8  enrichment + lyrics                  * done 2026-09-18, checked by George
                                            on the panel. ADR-0040, twice
                                            amended by what the work measured
9  settings wiring + UI polish          * COMPLETE 2026-09-25 - all five
                                            criteria closed. 0 carries a
                                            revisit before 13
10 plugin contract                        <- next. Themes left it for 14, and
                                            the defaults stay in the core
                                            process (George, 2026-09-25), so
                                            ADR-0013 is amended: they are the
                                            contract's source, not its
                                            consumers. A Beszel agent is the
                                            test that it carries a non-renderer
11 Plexamp as a renderer                  now ALSO the fourth-renderer proof
                                            for 10, replacing Qobuz. Its
                                            hardware check is pulled forward
                                            into 10 - Finding 075 says moOde
                                            built a Plexamp route and parked it
12 Qobuz Connect as a renderer            a second plugin against a contract
                                            already proved; keeps the private
                                            repository out of the critical path
13 first boot without a network           setup access point; pull forward the
                                            moment a non-developer gets a device
                                            (ADR-0031)
14 themes                                 cut out of 10. ADR-0016 calls themes
                                            plugins and plugins processes; a
                                            theme has no process - settle that
                                            first
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
