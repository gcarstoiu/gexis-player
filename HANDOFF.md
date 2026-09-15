# Handoff

Last updated: 2026-09-15 (twelfth session — **04-ui fixed and verified on
hardware; ADR-0029 to 0032 decided; a new image is built and waiting to be
flashed**)

## Start here

**A new image is built and needs flashing before anything else:**
`image/deploy/2026-09-14-gexis-player-v0.2.1-110-gc49c0a0-dirty.img`

It carries the Finding 022 fix. On first boot the panel should come up on its
own showing `http://127.0.0.1:8090/` — no console getty. **`gexis` currently
has its panel hand-pointed at a third-party test URL** (`/etc/gexis/kiosk.env`,
original kept at `.orig`); the reflash reverts that, so a loopback page is the
expected result, not a regression.

**Then: a PR closing this work**, which George wants before the UI designs
arrive. Two things worth doing first:

- **A cold build.** Every build this session used `CONTINUE=1`, which reuses
  the previous rootfs. That is exactly how the stale `default.target` survived
  and got caught by an assertion. `make clean && make image` (~40 min) is the
  only way to prove the stage is correct from nothing, and the PR's whole claim
  is that it is.
- **`playlistcontrol cmd:load album_id:<id>`** — still unverified, still the
  load-bearing assumption of ADR-0030's typed-library half. Needs George
  present; running it starts music.

**Build wart to fix, not blocking:** the copy-out took **3h45m** for 4.5GB on
the last build (12m02s of actual build, 14212s total). `make fetch-deploy` does
the same copy per-file in 44s. `pi-gen` accepts a `DEPLOY_DIR` override
(`build.sh:191`), so bind-mounting the host's `image/deploy` into the container
and pointing `DEPLOY_DIR` at it would remove the 4.5GB stream entirely and
halve disk use. Designed, not implemented.


**4c (now playing) is built and hand-installed on `gexis`** (2026-09-15):
`ui/src/screens/NowPlaying.svelte`, ported from `design/now-playing.html`,
fonts bundled via fontsource. Previous UI kept at `/opt/gexis-ui.4b-backup`.
Rendered in all six design states against a mock feed on the dev machine;
**not yet looked at on the panel** — George's hardware pass is next. With no
renderer the panel shows a "Nothing playing" placeholder (`data-unwired="home"`)
until Home is built. `design/` is **not committed**: it holds two
third-party photos (sample album art, artist photo) and this repo is public —
George to decide. Design package corrections from George: **no format badge
(sample rate/codec) anywhere** — open whether that includes the Peppy screen
(ADR-0019's codec rule); the design's drifting clock is the **fallback** for
the idle URL not loading (ADR-0033). Source pill now pulses while playing.
**Open:** George reported the Paused label and the artwork dimming as not in
the design, but `design/source/Now Playing.dc.html` has both (`stateLabel`,
`pausedVeil: playing ? 0 : 0.55`) — asked him to confirm removal.

**2026-09-15, thirteenth session:** image flashed and boots cleanly (George).
PR #9 opened for this branch. **Phase 4 criteria 6 and 7 withdrawn** — no
back-to-music screen, no activate control; 4e is now volume only. The
phone is the only way to start LMS until Phase 7. Awaiting designs: both
`.dc.html` files resent in full each iteration into `design/`, plus PNGs and
change notes for the area that changed. **When no renderer is connected the
panel shows the Home screen** (George, 2026-09-15), a design screen made for
that state and **distinct from the idle screen**. The idle screen (external
URL) takes over after 5 minutes without activity; when it is dismissed, Home
returns. This changes ADR-0019, where "nothing playing" belonged to the idle
screen directly — **needs ADR-0033 before implementation**; open points were
put to George.

No code changed in the twelfth session. It was build-environment repair and four
decisions. Nothing is half-finished, and the working tree is clean apart from
`image/pi-gen` (the Makefile deleting `stage2/EXPORT_IMAGE`, which is normal).

**Do these, in this order:**

0. **ADR-0032 (2026-09-15): the panel renders everything, a remote browser
   renders only settings.** Same page both ways; the phone shows a subset.
   George's inversion of a Claude Design "split by capability" proposal, and
   better than it — under the split some functions would have been phone-only,
   and the phone exists only while the LAN does. With the panel holding
   everything, nothing is phone-only and the device stays self-sufficient by
   construction. **Only the settings screen is responsive**; every other screen
   stays a fixed 1280x800 artboard. Settings becomes one imported component
   measuring its own mount width (720px breakpoint), so a setting added once
   appears on both. All inventory rows render for now, `[N]`/`[?]` included —
   mock stage, will iterate. Row types deliberately not defined yet; the
   settings HTTP API will be built to whatever vocabulary the design settles
   on. **No settings endpoints exist yet** — `settings.py` has the SQLite store
   from Phase 3 but nothing exposes it over HTTP. That is the next backend
   task once the design lands.

1. ~~**Flash and verify `04-ui` on hardware.**~~ **DONE 2026-09-14 — two
   defects found and fixed, see [Finding 022](docs/findings/022-kiosk-never-started-target-and-tty.md).**
   The panel showed a console getty: `firstrun.sh` reaches `raspi-config
   do_boot_behaviour B1`, which reset `default.target` away from
   `graphical.target`; and `getty@tty1` held the VT, so `labwc` exited 0 with
   an empty journal. Fixed by binding the unit to `multi-user.target` and
   adding `Conflicts=getty@tty1.service`. **Verified on `gexis` by an
   unattended reboot** — kiosk active, getty stopped, seat0/tty1, UI served,
   1280x800. Everything downstream of the trigger worked first time, so
   `04-ui` itself is sound. **Still to do: rebuild the image carrying the fix
   and reflash**; the fix is proven on a running device, not in an image.
   *Original text:* The image is built and waiting:
   `image/deploy/2026-09-13-gexis-player-v0.2.1-98-gfec5067-dirty.img` (raw,
   straight into Imager). labwc, the `PAMName=login` seat, 1280x800 and the
   Chromium kiosk flags have **never run** — all written from documentation.
   This is the outstanding half of Phase 4b and needs no designs.
   `journalctl -u gexis-kiosk` first if the panel is black; the unit is
   `Restart=no` on purpose so a failure stays visible.
2. **Verify `playlistcontrol cmd:load album_id:<id>`** against LMS with George
   present. It is the load-bearing assumption of ADR-0030's typed-library half
   and was deliberately not executed — running it starts music unannounced.
3. **Then wait on George's `.dc.html` artboards plus static PNGs** for 4c
   onward.

**Awaiting George's confirmation** (the settings-inventory rule in `CLAUDE.md`
requires his sign-off before anything is appended to ADR-0022's inventory):
ADR-0031 adds no new setting — *Device name* and *Wi-Fi configuration* are both
already `[R]` — but it raises two candidates that are **not** in the inventory
and have **not** been added:

- **Return to setup mode deliberately** `[N]` — a way to reopen the access
  point without waiting for the automatic re-entry condition. Adjacent to the
  deferred *Factory reset* item.
- **Access point security** `[?]` — whether the WPA2-vs-open choice is fixed in
  the build or exposed. ADR-0031 recommends fixed WPA2, i.e. not a setting.

**Unverified claims made this session, do not treat as tested:** AP mode has
never been raised on this hardware (only `WIFI-PROPERTIES.AP: yes` was read);
`libraries` returned `{}`, indistinguishable from an unknown command; only the
top of the `radios` subtree was walked; and whether a hostname change reaches
Spotify Connect and Bluetooth without a reboot is unknown.

## Phase 7 was re-decided (2026-09-14) — ADR-0030

George challenged ADR-0020: *"why did we select slimbrowse and not build
everything based on LMS capabilities so that we are in control of what we
display?"* The challenge was right, and ADR-0020 turned out never to have
written the typed-query alternative up as a considered option.

**The local library is now our own screens over typed queries** (`albums`,
`artists`, `genres`, `titles`, …) — measured against his LMS 9.1.1: 4554
albums, 7292 artists, 60974 titles, all with structured fields rather than a
server-formatted label.

**SlimBrowse survives only for radio, entered at `["radios","menu:radio"]`
rather than `home`.** That is an entry-point choice, not a filter: LMS's own
settings node, `My Apps`, global search and Radio Paradise are not filtered out
— they are never reachable. Podcasts is the one id excluded by name. Nine items
remain. Both areas share one visual language from the provided designs.

**Verify before building on it:** `playlistcontrol cmd:load album_id:<id>` is
the load-bearing assumption of the typed half and has **not** been executed —
doing so would have started music on George's system unannounced. ADR-0030's
"Unverified" section lists it and three others.

Knock-on: ADR-0020's cross-cutting rule now has **no live case for its second
branch** ("exists but cannot be operated here, show it and say where") — both
motivating examples are retired. The rule is kept as a principle; judge future
cases on the reasoning, not the retired rows.

Also settled this session: **ADR-0029**, text fields editable on every surface,
no on-screen keyboard, and a focused field with no keyboard attached does
nothing — a knowingly accepted exception to ADR-0014.

**Credentials now have a phase — ADR-0031, Phase 10.** First boot with no
network raises a setup access point (NetworkManager AP mode; verified available
on `gexis` 2026-09-14, NM 1.52.1, `WIFI-PROPERTIES.AP: yes`, but **never
exercised**). The setup page is served by `gexis-core`, and the typing happens
**on the user's phone** — which is why the panel still needs no keyboard and
why this closes ADR-0022's blocker without reopening ADR-0029. It collects
Wi-Fi credentials *and* the device name (ADR-0022's single name: mDNS, Spotify,
Bluetooth). `firstrun.sh` pre-seeding is unchanged and wins when present, so
the development workflow is untouched. **Pull Phase 10 forward the moment a
device goes to someone who did not build it.**

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

## Where things stand

**Phase 4 is starting, and five decisions were taken before any code**
(George, 2026-09-12), recorded in
[ADR-0028](docs/decisions/0028-ui-serving-and-command-channel.md) and
`docs/DEVELOPMENT.md`'s amended Phase 4 criteria:

1. **`gexis-core`'s own aiohttp app serves the UI**, same process and origin
   as `/state`. Not a separate nginx/lighttpd.
2. **Commands are REST POSTs**, not WebSocket messages. The socket stays
   publish-only. Decided chiefly because errors ("LMS unreachable") need
   somewhere to go, `/state`'s already-verified shape stays untouched, and
   `curl` is how this project actually debugs — a socket isn't curl-able.
3. **Volume is in Phase 4** (new criterion 8), displayed as a percentage of
   the hardware control. Not a transport control; transport proper stays
   Phase 6. Caveat recorded in the criterion: our percentage won't always
   match a phone's, Bluetooth especially (Findings 006/009/010). **Still
   open:** how the slider's *travel* maps onto a dB-linear scale, where
   raw-linear would cram every usable level into the top quarter.
4. **Criterion 6 reframed, not dropped.** George's objection was that a user
   doesn't need "why nobody holds the device" explained, because browse +
   tap-an-album already works via LMS's own auto-power-on. Correct — so the
   screen's job changed from explaining the state to offering the one action
   that gets back to music, and it is **expected to retire when Phase 7's
   browse lands**. It survives only because browse is three phases away and
   the activate control needs a host that isn't the user's own idle URL.
5. **Bluetooth's sample-rate field carries the codec** on now playing too
   (extending ADR-0019's Peppy-screen rule), so the codec must now be
   captured — new adapter work, but `MediaTransport1` already being watched
   makes it an extension rather than new plumbing.

Also George's correction, folded into criterion 3: **missing metadata is
often transient.** Bluetooth has no artwork, but artist/album/title are
enough for Phase 8's enrichment to find cover art and lyrics — so the
layout must reserve artwork space and not reflow when it arrives later
(ARCHITECTURE.md already required exactly this).

Build order agreed: **4a** model extensions (no UI) → **4b** serving and
kiosk → **4c** now playing → **4d** idle → **4e** back-to-music screen,
activate, volume → **4f** transition state. Table in `DEVELOPMENT.md`.

**4a is done** (194 unit tests, hand-installed and verified on `gexis`).
The payload now also carries `transport`, `codec`, `handoff`, `volume`
and `handoff_exempt_pairs`, and the command surface exists:

- `POST /volume {"percent": 55}` moved the real mixer to `132 [55%]
  [-54.00dB]`, with ALSA's own percent readout agreeing with ours.
- LMS deactivated from the server side published `active: null` with
  metadata blanked; `POST /renderer/lms/activate` then returned 200 and
  LMS came back — **the first `power 1` this project has ever sent**, and
  it deliberately fires no acquisition of its own, letting the existing
  CometD watch see the change so there is one acquisition path rather
  than two that can disagree.
- `409` for activating Spotify (declares no such control), `404` for an
  unknown renderer, `400` for a malformed volume body — all confirmed
  with `curl`, which is exactly why ADR-0028 chose REST.

**Not yet seen on real hardware: the handoff pair.** It is unit-tested,
including the case where the release ladder raises (cleared in a
`finally`, because a transition screen stuck on forever is the
unaccountable state ADR-0010 forbids) — but observing it live needs a
real takeover, which needs a phone. Note LMS↔Spotify is on the exempt
list anyway, so the visibly interesting case is a Bluetooth pair.

**Image rebuilt and verified, 2026-09-12** —
`2026-09-12-gexis-player-v0.2.1-88-g4cf667d-dirty` (34m54s, cold build
after a `make clean`). First image containing Phase 3, and the first
with the moved alsa pin: the manifest shows `libasound2t64` at
`1.2.14-1+rpt1+deb13u1` with the **`hi`** flag (held *and* installed),
and `libasound2-data` at the same version, so the dev/runtime mismatch
that existed in the failing run is gone. **It predates 4a** — the
version string names commit `4cf667d`, the pin fix; everything from
ADR-0028 onward has only been hand-installed.

**Phase 3 (core state daemon) is closed — all six criteria met.** Built and
hardware-verified on `gexis`, `phase-3-core-daemon`. Two real defects
found live during criterion 1's verification (Bluetooth's D-Bus interface
bug, the Spotify/Bluetooth relinquish() oversight) were fixed and
re-confirmed the same session — full detail further down this file.
Criterion 2 (adapters declaring capabilities, ADR-0013) followed
immediately after: `Capabilities` derived from the three built-ins'
actual, already-verified behaviour (audio connection, named acquisition
events, which skin fields each can supply), deliberately leaving
`controls` empty since no adapter can act on a user's command yet and
Phase 6 is where that becomes real. Published as a new field in the same
WebSocket payload; confirmed correct on `gexis`.

**Criterion 3 ("no special casing") raised a real scope fork, resolved by
George before any code:** ADR-0016 describes plugins as separate
processes with an IPC contract, which the three built-ins are not — a
full restructure into that model is a much bigger undertaking than
criterion 2 was. Found by grep first, not guessed: real, existing
renderer-name branching already in the codebase (`renderer_volume.py`'s
`MANAGED_RENDERERS` tuple, `volume.py`'s `if renderer == "spotify"`,
`__main__.py`'s by-name construction of two `DummyMixerBridge` instances
and one `VolumeBridge`). **George's call: remove that hardcoded
branching, keep the built-ins in-process** — the separate-process
question stays open for whenever Qobuz Connect (or another real plugin)
needs it. Fixed by extending `Capabilities` with `volume_managed`,
`volume_mechanism` (`DUMMY_MIXER`/`SOFTWARE_API`), and
`dummy_mixer_card`, so `__main__.py`'s wiring derives everything from
each adapter's own declaration. Verified on `gexis`: clean restart,
restore-on-acquire and the `DummyMixerBridge` mirror path both produced
the same values as before the refactor.

**Criterion 4 (moOde-compatible metadata file) researched from moOde's
own source before writing anything**, not assumed: `moode-player/moode`'s
`worker.php` (`updExtMetaFile()`) confirms `/var/local/www/
currentsong.txt` is plain `key=value` lines, atomically written (`.tmp` +
rename + `chmod 0666`) — not JSON, despite a forum thread and some UI
docs describing a JSON shape elsewhere in moOde's own stack. Its closest
analog to our architecture (the "external renderer active" branch — none
of our three sources is moOde's own local MPD library playback) writes
`file`/`artist`/`album`/`title`/`coverurl` plus `encoded`/`bitrate`/
`outrate`. **George's decision, presented with the exact gap named: only
the fields the model already has.** `encoded`/`bitrate` need codec/bit-
depth info nothing in this codebase tracks (only `sample_rate` in Hz);
`outrate` needs live ALSA hw_params, which nothing queries yet either.
Built `metadata_file.py`, wired as a plain `StateStore` subscriber
alongside `StateServer`, with its own change-dedup (moOde's own writer
compares before writing too — SD card wear). Renderer labels
("Squeezelite Active", "Spotify Active", "Bluetooth Active") are moOde's
own vocabulary verbatim. **Verified on `gexis`**: real file at the
expected path, `0666` permissions, correct live content against a
playing LMS track.

**Criterion 5 (SQLite config store) built as generic, currently-empty
infrastructure** - a key-value store (`settings.py`, JSON-encoded values,
one table so a future setting never needs a schema migration) for
ADR-0022's settings inventory, none of which has a UI to change it before
Phase 4 exists. Deliberately not migrating any existing `Config`/TOML
value (e.g. `boot_volume_steps`) into it - that would change where an
already-verified, hardware-tested value lives for no criterion-5 reason,
and stays a live option for whenever a real settings UI needs it.
Wired into `__main__.py` so the DB and schema are exercised for real on
the image. **Verified on `gexis`**: a value set before a service restart
read back correctly after one (`sqlite3` isn't on the image to inspect
the file directly - verified through `SettingsStore` itself instead).

**Criterion 6 (LMS track-change latency) measured and closed the same
session.** One script, run on `gexis` itself (not from a separate
machine, to avoid adding a network hop the real system doesn't have —
this project's own "wrong-host" lesson), alternating `playlist play`
between two distinct local library tracks so every round is an
unambiguous change, T0 at the JSON-RPC call and T1 at the first WebSocket
frame carrying the new track. **20/20 rounds, median 699.5 ms** (min
644.0, max 787.3 — tight, unimodal, no outliers). Recorded as
[Finding 021](docs/findings/021-criterion6-lms-track-change-latency.md).
No numeric bound for "bounded" exists anywhere in this project's own
records, so the finding reports the distribution as the record rather
than asserting a pass/fail line against a number nobody wrote down.

**PHASE 3 CLOSED, 2026-09-12.** All six criteria met on
`phase-3-core-daemon`, hand-installed and verified on `gexis` throughout
(not yet baked into a rebuilt image — see the hand-install note further
up this file). Two live defects found and fixed during verification
(Bluetooth's D-Bus interface bug; the Spotify/Bluetooth `relinquish()`
oversight), both re-confirmed. **Not yet done:** an actual image rebuild
containing this phase's code (everything so far has been the hand-install
loop over SSH), and merging `phase-3-core-daemon` toward `main` once
George decides it's ready. **Next: Phase 4** (UI shell, idle screen, now
playing — display-only, plus LMS activation).

Before writing any code for criterion 1, George was asked what "availability"
(criterion 1's per-renderer field, alongside "no renderer holds the
device") should actually mean for the UI, since Phase 3 itself ships no UI
and the answer only matters through what Phase 4 needs. **George's
decision: "backend reachable"** - not whether a renderer has a live
session - since only LMS ever gets an "activate" control from our own UI
(Phase 4); Spotify/Bluetooth availability only ever feeds a status line,
and richer session-awareness for them was deliberately not built ahead of
a criterion that would use it. Recorded in `model.py`'s module docstring.

Built this session, all unit-tested (no hardware) and passing (124 tests):

- **`core/src/gexis_core/model.py`** - `TrackMetadata` (ADR-0014's seven
  skin fields plus position/duration, `remaining_time` derived and clamped
  to never go negative) and `PlaybackState` (active renderer or nobody,
  per-renderer `available`, the active renderer's metadata or a blank
  placeholder when nobody holds the device).
- **`core/src/gexis_core/state.py`** - `StateStore`, the aggregator: the
  supervisor's `active` changes and each adapter's own metadata/
  availability reports come in here, and subscribers (the WebSocket
  server) are notified only when the combined, published state actually
  changes - a metadata push from a renderer that isn't active is recorded
  (so becoming active has something to show immediately) but does not
  broadcast.
- **`core/src/gexis_core/wsserver.py`** - `StateServer`, an `aiohttp.web`
  WebSocket endpoint at `/state` (no new dependency - aiohttp is already
  pinned). Push, not poll: a client gets the current snapshot on connect,
  then a fresh payload only when the state changes. Tested with a real
  `aiohttp` WebSocket client via `aiohttp.test_utils`, per Phase 3's own
  stated testing approach.
- **`arbitration.py`** gained `Supervisor(..., on_active_change=...)`,
  fired from `acquire`/`relinquish` after `_active` is already updated -
  this is what lets `state.py` reflect a takeover the instant it happens
  rather than on a poll.
- **Each adapter** (`lms.py`, `spotify.py`, `bluetooth.py`) gained
  `on_metadata_change`/`on_availability_change` hooks, matching the
  existing `on_volume_change` idiom rather than changing the abstract
  `Adapter` contract - that formalisation is criterion 2's job, not this
  one's. Field mappings sourced from each renderer's own docs, not
  assumed:
  - **LMS**: JSON-RPC `status` query, requesting `tags:aldcT` so pushed
    frames carry metadata, not just power. Per-song fields
    (title/artist/album/coverid/samplerate) live inside `playlist_loop[0]`
    in the JSON-RPC response, not at the top level - confirmed against
    community JSON-RPC examples (LMS-CLI.md itself only documents the raw
    telnet tagged-parameter format, which flattens differently). **Two
    things flagged as not yet hardware-verified**: the `playlist_loop`
    nesting itself, and tag `T`'s unit - LMS-CLI.md's own table says
    "samplerate, in KHz" but its own worked example returns a raw Hz value
    (44100) for 44.1kHz content: implemented as Hz, matching the doc's own
    example over its own prose, but not checked against `gexis`'s real LMS
    server.
  - **Spotify**: go-librespot's `/events` "metadata" and "seek" events, per
    API.md (fetched from the upstream repo, not assumed) - "seek" carries
    only position/duration, so it merges onto the last "metadata" event
    rather than reporting a mostly-blank update.
  - **Bluetooth**: BlueZ `MediaPlayer1`'s `Track` dict and `Position`
    property (org.bluez.MediaPlayer.rst), read once from the
    `ObjectManager` snapshot when the player appears and kept current via
    `PropertiesChanged`. No artwork or sample rate - matches ADR-0014's
    "Bluetooth supplies no artwork" expectation; the interface genuinely
    has no such fields, not an omission here. **Not yet hardware-verified**
    against a real phone connection - the `PropertiesChanged` handler's
    double-unwrap (a dict-valued D-Bus property nests one Variant level
    deeper than a scalar one) is inferred from dbus_next's documented
    behaviour, consistent with `bluetooth_trust.py`'s existing
    `.value`-unwrapping idiom, but not observed on a live signal yet.
- **`__main__.py`/`config.py`**: `StateStore`/`StateServer` wired in,
  `state_host`/`state_port` (default `0.0.0.0:8090`) added to `Config`.

**Update, same session: hand-installed on `gexis` and LMS metadata verified
live, on George's explicit instruction.** This resolves - for this
instance, not as a standing policy - the "develop-on-hardware workflow
inversion" question flagged above as discussed-but-undecided: George asked
directly for the code to be installed on `gexis` and checked against
`ws://gexis:8090/state`, rather than waiting for a full image rebuild.
Installed via `pip install --no-deps` from a rsynced copy of `core/` into
the existing `/opt/gexis-core/venv` (not yet baked into `stage-gexis` or a
rebuilt image - this is a hand-install for testing, same shape as the
config/systemd-file loop already documented, now extended to the Python
core for the first time). `gexis-core.service` restarted cleanly; journal
shows a clean startup, all three adapters reporting `available: true`,
`wsserver: listening on ws://0.0.0.0:8090/state`.

**Both flagged-unverified LMS mappings are now confirmed correct against
the real server:**
- `playlist_loop[0]` nesting - confirmed. A live query showed title/
  artist/album/coverid exactly where expected, and end-to-end through the
  WebSocket for a real local library track (Snow Patrol, "Eyes Open") -
  title, artist, album, artwork URL, position, duration, remaining_time
  all correct.
- Sample rate is Hz, not kHz - confirmed. `tracks` query on three library
  files all returned `"samplerate": "44100"` (a string, `int()` handles
  it fine) for 44.1kHz content - LMS-CLI.md's "in KHz" claim is simply
  wrong, as suspected from its own contradicting example.
- **New, incidental finding while testing:** the track playing at the
  time was a remote radio stream (`remote: 1`) - confirmed the `remote`
  branch's `current_title` fallback works correctly on live data
  ("Backstreet Boys - Anywhere for You"), and that remote items report no
  `samplerate` at all (not a bug - LMS has nothing to report for a stream
  it hasn't decoded). `remoteMeta` (a field not previously known about)
  duplicates title/artist/album/coverid for remote items - not used, since
  `playlist_loop`/`current_title` already covered it, but worth knowing it
  exists.

**Caused a live playback interruption while testing:** a `playlist play`
JSON-RPC call was issued directly against the real "gexis" LMS player to
get a local-file track queued for the sample-rate check, interrupting
whatever radio stream was playing at the time. Flagging plainly rather
than burying it - George's own player state was changed mid-test.

**Still not verified:** Spotify and Bluetooth metadata (both need a real
phone) and a genuinely external WebSocket client connection (all checks
above ran a client on `gexis` itself against `127.0.0.1:8090` or were
piped through SSH) - George's own next step, watching
`ws://gexis:8090/state` from his own machine while using the phone app.

**Bug found and fixed live, same session: the state WebSocket was
emitting a fresh payload roughly once a second regardless of real
activity.** George spotted it immediately watching the raw browser
console output. Cause: `_watch`'s CometD subscribe request used
`subscribe:1`, and LMS-CLI.md's own wording for that parameter is a
heartbeat interval in seconds ("the interval between automatic
generations in case nothing happened"), not an on/off flag - it was
already in the code before this session, harmless while the only thing
read from each push was `power`, but once metadata (including a ticking
`time` field) started flowing to the WebSocket, the heartbeat alone
produced a new payload every second independent of any genuine change.
Fixed: `subscribe:0`, which keeps push-on-real-change (power, volume,
track load) and drops only the unconditional resend - confirmed on
`gexis`, one message in an 8-second window with LMS playing, against one
every ~1s before. Also added metadata equality dedup to
`StateStore.set_metadata` on its own merits, though the `subscribe:0` fix
is what actually stopped this specific spam (a playing track's `time`
field genuinely differs on every real push, so dedup alone wouldn't have
silenced it).

**George then ran a real round of Bluetooth/Spotify/LMS testing against
the WebSocket and reported three findings - two real defects, one already-
known behaviour:**

1. **Bluetooth reported no metadata at all**, tried from Spotify and
   Plexamp on his phone. Root cause, confirmed by introspecting BlueZ
   directly on `gexis`: `MediaPlayer1`'s own proxy interface defines no
   signals of its own (empty `signals` list), so dbus_next generates no
   `on_properties_changed` for it - the journal showed
   `AttributeError("'ProxyInterface' object has no attribute
   'on_properties_changed'")` every single time a `MediaPlayer1` appeared.
   `PropertiesChanged` belongs to the generic
   `org.freedesktop.DBus.Properties` interface instead - matches
   `bluetooth_trust.py`'s own existing idiom, just for a signal instead of
   a method call. Fixed. Also extracted `on_interfaces_added`/
   `on_interfaces_removed` from closures into bound methods
   (`_handle_interfaces_added`/`_handle_interfaces_removed`) purely for
   testability - the closure shape is exactly how this bug shipped
   unnoticed, since nothing exercised it without real D-Bus. New fake-bus
   regression tests cover the actual `get_interface`/
   `on_properties_changed` call chain now.
2. **Stale data after disconnecting from a renderer, with nothing else
   taking over.** George: "I clearly disconnected from Spotify and was
   still seeing the old metadata... I think this was an oversight in the
   previous work." Confirmed by inspection, not just by his report:
   `on_release` was wired for LMS's own deactivation only -
   `SpotifyAdapter`/`BluetoothAdapter`'s own `run()` docstrings literally
   said "not wired up... out of ADR-0027's scope" verbatim in both files.
   Neither adapter ever told the supervisor "nobody holds it now" on a
   real disconnect, so `active` stayed pointed at whichever one was last
   used indefinitely. **George's call: this was an oversight, not a
   deliberate deferral - fix it.** Fixed both: `SpotifyAdapter` calls
   `on_release()` on go-librespot's own `"inactive"` event; `BluetoothAdapter`
   calls it when its `MediaPlayer1` disappears. Both call it
   unconditionally and safely - `Supervisor.relinquish()` already ignores
   a release from a renderer that isn't currently active, which is what
   makes the echo of our own takeover-driven release a no-op (the same
   mechanism LMS already relied on).
3. **Two consecutive metadata writes for the same song on an LMS
   takeover** - not a bug. The logs show exactly why:
   `lms: position was 0.0s, seeked back to the 35.5s it was released at`.
   LMS's own auto-power-on restarts the track from zero, and ADR-0027's
   resume logic then corrects it with a seek - two genuinely different
   real position values, both correctly published in quick succession.
   This is the same "residual elapsed flicker" ADR-0027's own Open section
   already names and defers ("issuing the `play` re-introduces LMS's
   stale-anchor jump for 0.3-1.6s before it corrects... decide after
   hearing the fix without it") - just newly visible through the WebSocket
   instead of only as an on-screen glitch. No change made; revisit only if
   that deferral itself gets revisited.

All three fixes deployed to `gexis` (same hand-install-over-SSH loop) and
confirmed starting cleanly. **George re-tested and confirmed both fixes
work**: Bluetooth now reports real metadata, and disconnecting from
Spotify/Bluetooth with nothing else taking over correctly returns `active`
to `null` with metadata blanked.

**Phase 3 criterion 1 is CLOSED, 2026-09-12** — see `docs/DEVELOPMENT.md`
for the full acceptance note. All three renderers' metadata, availability,
and "no renderer holds the device" verified on `gexis` against a real
WebSocket client, by George.

---

**Phase 0 is merged** (PR #1, into `main`). All seven acceptance criteria
passed, hardware-verified on `gexis`. Build cost is known: a full
`make image` is ~37-40 minutes on this dev machine under Docker + QEMU
emulation — rebuild-per-iteration is viable for Phase 2 onward, not just
in principle but measured.

**Phase 1 is absorbed into Phase 2** — decided and acted on, but the
`docs/DEVELOPMENT.md` change recording it is **PR #2, still open**, not
on `main` yet. The takeover gap has to be measured on the image, not a
hand-built machine; its three criteria are Phase 2 criteria 8-10.

**Phase 2a (renderer packaging, criteria 1-2) is done and closed** —
merged from `phase-2a-renderers` into `phase-2-arbitration`, its home
phase branch (neither has a PR open yet against `main`). squeezelite,
go-librespot and bluealsa-aplay are packaged
into `stage-gexis` as systemd units. Two hardware-found defects are fixed,
committed, and **reverified on hardware** on `gexis`: `pi` had no
sudo at all (shipped `/etc/sudoers.d/010_pi-nopasswd` directly — verified
empirically that stock Raspberry Pi OS Lite never ships it either, since
this image's `firstrun.sh` replaces the flow that would normally create
it; `sudo -n true` now succeeds on the flashed card), and go-librespot's
`ExecStart` had `-config_dir` (one dash; its CLI parses `-c` as a
distinct short flag, so this got parsed as `-c onfig_dir`) instead of
`--config_dir` (`go-librespot.service` now starts). Both blockers from
that hardware pass are closed. Also verified: all four units
(squeezelite, go-librespot, bluealsa, bluealsa-aplay) enabled and
active, squeezelite `NRestarts=0`; `speaker-test -D output` plays
audibly (criterion 4); `output.conf` has no `type plug`, no card index,
and has `ctl.output` (criterion 5); `libasound2t64` is
`1.2.14-1+rpt1` and held per `apt-mark showhold` (criterion 6);
squeezelite's `ExecStartPre` mixer check is present and passes.

**Phase 2's sub-phase mapping is confirmed as three-way** (2a criteria
1-2, 2b criteria 3-6, 2c criteria 7-10 — recorded in
`docs/DEVELOPMENT.md`). A four-way split was discussed and approved in
an earlier chat, but never written down anywhere, and by the time that
was noticed nobody had the record — it is **unrecoverable, not
withheld**. The three-way split is the version of record; if a fourth
sub-PR resurfaces from memory later, it does not override this — this
note exists so that isn't mistaken for a new discrepancy.

**Criterion 1 is now fully confirmed** (was partial). All three
renderers verified writing to `"output"`, each checked at its own
location, on a fresh boot (14:31:54) of a rebuilt-and-reflashed image:
squeezelite passes `-o output` in `ExecStart`; bluealsa-aplay has a
drop-in override at
`/etc/systemd/system/bluealsa-aplay.service.d/override.conf` that
clears the shipped `ExecStart` and sets `--pcm=output` — the packaged
default was `--pcm=default`, which would have played through whatever
`"default"` resolved to while the unit still looked healthy; go-librespot
has `audio_device: output` with `audio_backend: alsa` in
`/var/lib/go-librespot/config.yml` — not in the unit, which only passes
`--config_dir`, so this one is a two-place check (unit + config). Both
criteria 1 and 2 are met on the current build.

**The mixer-check journal-logging fix (`6ee6d6f`) is now verified on a
real boot**, not just an interactive shell: the success line appears in
`journalctl -u squeezelite -b`, attributed to
`squeezelite-mixer-check.sh[848]`, between systemd's `Starting` and
`Started`. This was the one outstanding piece of that commit — closed.

The sudoers fix's `visudo -cf` validation (`stage-gexis/01-firstboot/01-run.sh`)
was reviewed on a concern that it might skip validation if `visudo` is
absent on the pi-gen build host. Checked, not assumed: `on_chroot` (
`pi-gen/scripts/common:82-108`) runs the check via `capsh --chroot=...`
*inside the target rootfs*, not on the host, so host-side `visudo`
availability is irrelevant. That rootfs already has `sudo`/`visudo`
installed by `stage2/01-sys-tweaks/00-packages` (an earlier stage), and if
it somehow didn't, `capsh`'s non-zero exit would propagate through
`on_chroot`'s return code and the script's `exit 1` — fails closed, no
unvalidated sudoers file can ship. No host-side `sudo` package install
needed; none was made.

**Docker access on `C3PO` is resolved** — the `docker` group membership
picked up after George's terminal restart, and `make image` has since
built successfully (one retry needed: the first attempt failed at
`export-image`'s `losetup` step with `mknod: invalid minor device
number '/dev/loop0 (lost)'`, a transient loop-device race, not a code
issue — `make clean` to drop the leftover `pigen_work` container and
rerunning `make image` succeeded, 40m59s).

**`squeezelite-mixer-check.sh` no longer execs `amixer`** (`6ee6d6f`,
pushed to `phase-2a-renderers`). A successful check now logs a positive
line; the failure path dumps `amixer -D output scontrols` so a misnamed
control and an absent card are distinguishable. Previously a pass
produced no journal output at all, so a boot where the assertion ran and
a boot where it was never wired up looked identical in
`journalctl -u squeezelite -b`. Verified on the rebuilt image (see
criterion 1 note above).

**`go-librespot-config.yml`'s comment was fixed** (`210f7e7`): it said
the unit "passes `-config_dir`" (single dash) — the exact broken form
that cost a hardware round-trip earlier. No functional effect; it would
have misled whoever next debugged that file. The two occurrences in
`go-librespot.service` are correct and untouched (one of them quotes
the broken form deliberately, as part of explaining the fix).

**Branch divergence found and closed.** `make provision DEVICE=/dev/sdb`
failed with "No rule to make target 'provision'" — `HANDOFF.md`
documented the target, but the Makefile on `phase-2a-renderers` only
had `image:` and `clean:`. Cause: `e715344` ("Add make provision") is
on `main` via PR #3 (2026-09-05 20:36); the phase-branch line
(`phase1-absorbed-into-phase2` → `phase-2-arbitration` →
`phase-2a-renderers`) was cut before that and never took it back —
exactly two commits diverged (`e715344` and its merge `5e4be7d`), and
PRs #4/#5 are still open so haven't reached `main` either. Same shape as
the credential-exposure defect above, with a twist: PR #3's gitignore
rule *was* back-ported to the phase branches, but the rest of PR #3 (the
`provision` target, `provision.env.example`, the `image/README.md`
content) was not — the credential half got backported, the functional
half didn't. Resolved by merging `main` into `phase-2a-renderers`
(`514a6ff`) rather than cherry-picking, so the branches converge instead
of drifting further — auto-merged cleanly (`Makefile`,
`image/README.md`), no conflicts. `./test-gitignored-credentials.sh`
passes on the branch. Provisioning then ran and the flash booted with
SSH access.

**New concern, Phase 5, not tested — only inferred from the unit file:**
the shipped `bluealsa-aplay.service` runs `User=root` with
`PrivateTmp=true`, `ProtectSystem=strict`,
`DevicePolicy=closed` + `DeviceAllow=char-alsa rw`. `PrivateTmp` gives
the unit its own `/tmp` namespace; the peppyalsa FIFOs live at
`/tmp/peppymeter` and `/tmp/peppyspectrum`, so when Bluetooth is the
active renderer, its scope writes would land somewhere the
visualisation service can't see. This does *not* explain the meter-FIFO
finding below (that was `speaker-test` as `pi`, unaffected by this
unit's sandboxing) — it's a second, independent Phase 5 problem.

**`docs/DEVELOPMENT.md` on `main` is behind.** It doesn't yet show Phase
1's absorption, Phase 2's criteria 8-10, the tier-3-moves-to-`gexis`
change, or criterion 3's root-access amendment (a reachable SSH shell
with no sudo access is a Phase 0 gap found on hardware, same shape as the
provisioning-credentials gitignore defect below — criterion met literally,
intent unchecked). All of that exists on `phase1-absorbed-into-phase2`
(PR #2) and/or `phase-2a-renderers`. Read the branch, not just `main`, for
the current criteria.

**A live credential-exposure defect was found and fixed across every
affected branch.** `image/provision.local.env` (real SSH key, real Wi-Fi
password) was untracked and *not* gitignored on `phase-2a-renderers` and
three other branches — the ignore rule merged into `main` via PR #3, but
those branches were cut before that merge and never got it back. Fixed on
all affected branches directly. **PR #4** (open) adds a standing
regression test to `main`. **PR #5** (open) adds `docs/LESSONS.md`, naming
the general "verification ran against the wrong reality" pattern this and
two earlier incidents share.

**New defect found on `gexis`, not blocking Phase 2: the peppyalsa meter
FIFO doesn't write.** `/tmp/peppyspectrum` carries data during playback;
`/tmp/peppymeter` does not. Scope: single reader, single stream
(`speaker-test` sine 440 Hz, 48 kHz S16_LE), two runs, read as `pi`, ~8s
window opened before playback — not decisive on its own. Established:
the scope loads and attaches (`libpeppyalsa.so` symlink resolves,
spectrum FIFO writes, no scope-related errors in alsa-lib output);
`meter_show` controls console display only, not FIFO writing (set to 1,
ASCII level bars appear on the terminal and the FIFO stays silent, so
the meter path computes levels — only the FIFO write is missing); both
FIFOs exist as named pipes, `pi:audio`, created at boot (11:11), which
suggests something other than peppyalsa creates them. Unchecked
candidates, none eliminated: peppyalsa's open mode for the meter FIFO
vs. the spectrum FIFO; pre-existing FIFOs with unexpected ownership/mode
affecting behaviour; a meter-side option missing from `output.conf`
(the spectrum block has `spectrum_size`, `logarithmic_amplitude`,
`smoothing_factor`, `window`; the meter side has only `meter`,
`meter_max`, `meter_show`); `decay_ms 400` interacting with the write
path; a build variant with the meter FIFO write compiled out. Every
remaining candidate needs peppyalsa's source — stopped here because
further permutation on the box costs more than reading the code. This
is Phase 5 input, already on `docs/ARCHITECTURE.md`'s open-questions
list as "the peppyalsa FIFO byte format (blocks the visualisation
service)." Not written up as a finding yet — exists only here.

**First data on the FIFO format** (from the spectrum FIFO, which does
write): 64 bytes of one frame, fixed-width 4-byte groups, low byte
first (32-bit LE inferred from the pattern, not confirmed against
source). Values decoded 5, 16, 50, 62, 64, 56, 34, 0, 2, then zeros —
consistent with `spectrum_size 30` and `spectrum_max 100` in
`output.conf`; consistent is not confirmed.

`gexis`'s state as of this pass: the `meter_show 1` exploration was
reverted, config matches the shipped image again, no other hand-edits.

**Develop-on-hardware workflow inversion: discussed with George, no
decision yet.** Would change `docs/DEVELOPMENT.md`'s working contract,
so by its own stop-and-ask rules it wants an ADR before implementation.

**Build self-identification gap.** Nothing on the running system
identifies which build it is — checked `/boot/firmware/` and
`/etc/gexis*` only, no manifest, no version file, no marker (doesn't
establish absence everywhere, just that those are the two obvious
places). Criterion 7 says the manifest ships alongside the `.img`, i.e.
on `C3PO`. But `docs/DEVELOPMENT.md`'s tier-3 rule has the runner assert
its environment against "what the image build's own manifest recorded"
— and the runner is `gexis`, where the manifest isn't reachable. Needs
either the manifest shipped onto the image or a fetch path. **George's
call** whether that's a criterion 7 amendment.

**Method note, candidate `docs/LESSONS.md` instance:** a command run on
`C3PO` instead of `gexis` produced a false finding (`pcm.output` not
resolving), later retracted — the tell was `speaker-test` 1.2.16 on
`C3PO` vs. 1.2.14 on `gexis`. The wrong-host risk is structural to
pasting command blocks between machines, not a one-off slip — same
"verification ran against the wrong reality" shape PR #5 tracks.

**Phase 2b (arbitration core, criteria 3-6) is in progress on
`phase-2b-arbitration`**, branched from `phase-2-arbitration` after 2a
closed. ADR-0021 amended with a venv-packaging addendum: the Python core
builds into `/opt/gexis-core/venv` inside the pi-gen chroot, `dbus-next`
over `dbus-python` (pure Python, no build toolchain needed on the
image), exact-version pins (hash-pinning flagged as a follow-up, not
done). `core/` holds the supervisor (`Supervisor` + `TimeoutLadder`, base
slot always LMS, ADR-0010's policy, criterion 4's polite-stop → SIGTERM →
SIGKILL ladder via `systemctl kill`), fully unit-tested — 9 tests, no
hardware, all passing — plus adapters for LMS, Spotify and Bluetooth, a
volume bridge (criterion 5) and boot volume (criterion 6). Packaged into
`image/stage-gexis/03-core`; the Makefile now bind-mounts `core/` into
the pi-gen container as well as `stage-gexis`, so build-time `pip
install` runs against the same source tree the unit tests run against,
not a copy.

**A second "verification ran against the wrong reality" instance, caught
and corrected in the same session it was made:** the LMS-unreachable
claim two sections above was wrong. The original reachability check was
a bare GET to `/jsonrpc.js` with no body and a 5s timeout — LMS
apparently only handles POST there, so the GET just hung until the
timeout, which read as "unreachable." A real JSON-RPC POST succeeded
immediately, confirmed the "gexis" LMS player exists
(`e4:5f:01:58:89:07`, `192.168.178.188:9000`), and running the LMS
adapter's `run()` against it end-to-end — handshake, `/slim/subscribe`,
then a real `playlist play` triggered from the test itself — produced a
genuine CometD `mode -> play` push and fired `on_acquire()` within 4
seconds. First time the CometD subscription (previously the file's own
"unverified" flag) has been watched work at all. **Not independently
reconfirmed:** whether `release()`'s `pause` call takes effect within
any particular time bound — the JSON-RPC call returned success, but the
test moved on to clearing the playlist before checking mode again.
`adapters/lms.py`'s own comments now record this precisely rather than
carry a blanket "verified" claim forward. Add this as a second
`docs/LESSONS.md` instance alongside the `C3PO`/`gexis` one above — same
shape, different mechanism (wrong HTTP method instead of wrong host).

**Two decisions closed this session:** the boot volume placeholder
(`boot_volume_steps = 60`, i.e. −90dB on ADR-0018's scale — 0.5dB/step,
0=mute/−120dB, 240=0dB) is confirmed by George as the real safe level,
not a placeholder — code comments updated accordingly. LMS's
address needed its port spelled out (`192.168.178.188:9000`); the core's
config defaults to that address now (there is no sane localhost default
for a renderer that lives on a different machine, unlike go-librespot),
and `image/stage-gexis/03-core/files/core.toml` sets it explicitly too.

**The rebuild including the new `03-core` stage succeeded** (39m33s,
after two false starts: one from a bug in this session's own build-time
assertion — checked `venv/bin/python`, a relative symlink to
`venv/bin/python3`, itself an *absolute* symlink to `/usr/bin/python3`,
which only resolves once `${ROOTFS_DIR}` is the real root — fixed by
checking `venv/bin/pip` instead, a plain file; the other two attempts
were killed by `C3PO`'s own low-memory condition, unrelated to the build
itself, and succeeded once more memory was free). All commits pushed to
`origin/phase-2b-arbitration`.

**Reflashed and hardware-tested.** None of it is clean yet; do not treat
criteria 3-6 as met.

> **The dated session logs for Phases 2a-2d — every hardware round from
> 2026-09-06 to 2026-09-12, with what broke and how it was diagnosed — moved
> to [`docs/HANDOFF-ARCHIVE.md`](docs/HANDOFF-ARCHIVE.md) on 2026-09-14.**
> Verbatim, nothing edited. Look there for *why* something is the way it is;
> the rules those sessions produced are in `docs/LESSONS.md`,
> `docs/findings/`, and "Things that will bite if forgotten" below.

## Machines

| Name | What it is | Notes |
|---|---|---|
| `C3PO` | dev machine | CachyOS, **fish shell** — no heredocs. Hand it script files to run with `bash`, not pasted multi-line commands. |
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

## Next actions, in order

**Immediate (2026-09-13, still open):** flash
`image/deploy/2026-09-13-gexis-player-v0.2.1-98-gfec5067-dirty.img` and verify
`04-ui` on hardware — labwc starting, the `PAMName=login` seat, 1280x800, the
Chromium kiosk flags, and the UI actually served by `gexis-core` under the
pinned Chromium rather than a remote Firefox. None of that has ever run. This
is the outstanding half of Phase 4b. Everything after it (4c onward) waits on
George's `.dc.html` artboards plus static PNG exports.

**Second (2026-09-14):** verify `playlistcontrol cmd:load album_id:<id>` with
George present — ADR-0030's typed-library half rests on it and it was
deliberately not executed, because running it starts music unannounced. See
"Start here" at the top of this file for the full list, including what is
awaiting George's sign-off.

> **Items 0 and 1 are done and archived** — ADR-0027 / Phase 2d, and Phase 2c
> criteria 7-10 (Phase 2 closed 2026-09-12). Both are in
> [`docs/HANDOFF-ARCHIVE.md`](docs/HANDOFF-ARCHIVE.md) with their full
> verification records. **Numbering is kept, not compacted**, so references to
> "item 3" elsewhere still resolve.

2. **Finding 013's four defects** - one fixed (squeezelite restart
   burst), one deferred by George's decision (the go-librespot retry
   storm - revisit on any real recurrence), two documented but not
   root-caused (the ~56s go-librespot backoff; go-librespot reporting
   itself playing while never opening the device) - the latter two would
   need reading go-librespot's own source, the way Finding 011 did for
   its acquisition signals, and weren't chased further this session.
3. **Fill the Finding 003 grid** on `rig`, not `gexis` — characterises the
   metering path, not the product image. 16 of 18 cells remain.
4. **Phase 5 (not blocking Phase 2c):** Finding 007's research is done
   and ADR-0025/0026 record the licence and integration-approach
   decisions. Still needed before vendoring: George's ruling on
   turntable/cassette handlers (ADR-0026 assumes meters+spectrum only
   until then), the labwc screen-ownership mechanism spike (ADR-0026
   flags this unverified), and a Pi-4 frame-rate measurement for
   Blocker 2 (Finding 007) — this last one is also the cleanest way to
   close the residual NEON doubt from the same finding.
5. **Two items deferred out of Phase 2b, not gone — pick up whenever
   they matter again, not urgent:**
   - Fixed output mode has no implementation at all in `gexis_core` —
     real, design-complete work (ADR-0018's table and "Settled
     consequences"), most naturally built once mode *selection* has a
     UI to live in (Phase 4+).
   - Bluetooth's SIGKILL-escalation path (device still held after a
     full ladder run, reproduced once 2026-09-08, not since) — worth a
     deliberate forced-escalation test if it's ever a live problem
     again; not chased further while polite stop keeps working.
   - LMS device-reclaim mystery (Finding 009/010 §4/5) — possibly
     related to the second squeezelite player "Moode"
     (192.168.178.131) seen on George's LMS server; still not confirmed
     or investigated further.
   - The LMS/Spotify boot-default-vs-mid-session fallback question and
     Bluetooth's `restore_volume_floor_db` number (Finding 011 §3/§4) —
     both need George to pick an actual value, not a mechanism fix.

**ADR-0010's sync-group-interaction item is moot in the good sense
now** — `-C 1` means squeezelite is never killed in normal operation,
so there's no sync-group loss to accept anymore. See the ADR's own
final amendment.

Decisions pending from George: confirming (or picking a different)
`restore_volume_floor_db` — currently a −40dB placeholder, and now
measured on hardware as genuinely too quiet for Bluetooth's
unmanaged-floor bump (Finding 011 §4), not just unreviewed; whether
`boot_volume_steps`'s -90dB fallback should keep applying to any
never-remembered LMS/Spotify acquisition mid-session, or only to true
cold boot (Finding 011 §3 — a mid-session first-use currently lands as
quiet as a fresh power-on, confirmed on hardware); which component
applies Bluetooth's software volume attenuation below ~96% (Finding
006, no owner yet); pinning down squeezelite's LMS-volume-to-hardware
mapping (Finding 008's B2 fix addresses the *cross-renderer bleed*
symptom this was originally raised under, but the underlying
mapping/curve question is separate and still open); the criterion 7
build-self-identification amendment; whether to act on the
develop-on-hardware workflow inversion (needs an ADR first if so);
turntable/cassette handlers for Phase 5 (ADR-0026); whether the LMS
device-reclaim mystery (Finding 009/010 §4/5) is related to the second
squeezelite player "Moode" (192.168.178.131) seen registered on
George's LMS server early in the 2026-09-08 session — flagged to
George, not yet confirmed or investigated further.

Not blocking, needed before their phases: the peppyalsa FIFO byte format
(blocks the visualisation service) and George supplying format icons for
LMS/Spotify/Bluetooth (Finding 007's follow-up notes — the bundled set
covers none of our three sources).

**Build speed — options 1 and 2 implemented and verified, 2026-09-08.**
`make image` ran ~40 minutes; George asked for ways to cut that (stability
still comes first — this doesn't reopen ADR-0001's pi-gen-over-rpi-image-gen
call, see its 2026-09-08 amendment). Five options were researched and
ranked; George asked to implement 1 and 2 and rebuild to see the effect.
Both are now live in the `Makefile` (see its own comment on the `image`
target for the full reasoning) and verified with two real, back-to-back
builds — not estimated:

| Build | What changed | Measured time |
|---|---|---|
| Baseline (2026-09-08, earlier session) | neither option | 39m11s |
| Cold build, option 2 only (`stage2/EXPORT_IMAGE` removed) | drops the unused "-lite" export | **32m01s** (predicted ~32m30s) |
| Warm build, both options (`CONTINUE=1` against the preserved container from the run above) | also skips stage0-2 | **11m33s** (predicted ceiling ~12m39s) |

Both measurements beat the prediction slightly. Confirmed correct, not
just fast: `stage0/prerun.sh` (the ~3.5-minute debootstrap) went from
Begin to End in the same second on the warm build — the rootfs is
reused wholesale — while `stage-gexis/03-core/00-run-chroot.sh` (the
`pip install` of `gexis-core`) still ran in full (30s) against the live
bind-mounted source, and only one `export-image` pass ran. The cache
skips the base OS layers, not our own code.

One wrinkle noticed, not a problem: `work/*/build.log` (mirrored to
`deploy/build.log`) *appends* across `CONTINUE=1` runs rather than
starting fresh, so grepping it for one run's stage timings after several
warm rebuilds will show more than one run's entries mixed together — use
the live `docker logs`/Makefile-reported wall time for a single run's
number, not this file, once several incremental builds have piled up.

**Consequence for the day-to-day workflow:** `make image` now leaves the
`pigen_work` container behind on success (`PRESERVE_CONTAINER=1`) instead
of self-cleaning — `make clean` is the only way left to force a truly
from-scratch build (a pi-gen submodule bump, a suspected caching bug, or
just wanting a clean-room result before a release). Its own comment in
the `Makefile` explains this.

**Not implemented, still open if the remaining ~11-12 minutes (mostly the
QEMU-emulated final export/compress and whatever base-OS work wasn't
cached) is ever worth chasing further:**

3. **Native arm64 build host** — removes the QEMU emulation tax entirely
   (the dominant remaining cost: QEMU user-mode emulation runs every
   `dpkg`/`apt` post-install script instruction-by-instruction). The
   single biggest possible further win, but changes the build environment
   away from the one ADR-0001/Findings 002-003 were measured on — not
   free of its own verification cost.
4. **Local apt caching** (`apt-cacher-ng` or similar) — smaller win here
   than usual: build logs show package *fetching* is already fast; the
   slow part is unpack/configure under emulation, not download. Cheap to
   add, helps most on a slow/flaky network day.
5. **Audit whether stage0/1/2 install anything this product doesn't
   need** — least certain, nothing checked yet, and cuts against
   ADR-0001's "less of the base is ours to maintain" reasoning. Last
   resort, not a first move.

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
