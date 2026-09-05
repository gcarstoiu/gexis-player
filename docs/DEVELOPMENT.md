# Development

## Working contract

**George** sets requirements, acceptance criteria, trade-offs and UX. Reviews
PRs. Decides anything that would become an ADR.

**Claude** implements, tests, and opens PRs. Does not commit to `main`.

### When Claude must stop and ask

- The work requires a decision not covered by an ADR or by acceptance criteria.
- An ADR turns out to be wrong, unimplementable, or in conflict with another.
- A measurement contradicts a finding.
- The acceptance criteria for a phase cannot be met as written.

In all four cases: stop, describe the problem, propose options. Do not decide
and continue.

### Branching

- One branch per phase: `phase-0-image`, `phase-2-arbitration`.
- Sub-PRs into the phase branch where a phase is large. Phase branch merges to
  `main` when its acceptance criteria pass.
- Commits are small and describe *why*, not *what*.

### Model split

Sonnet in Claude Code for implementation. Escalate to Opus after two failed
attempts, or immediately for anything that would become an ADR.

---

## Phases

Ordered by risk retirement. Audio arbitration cannot be retrofitted; screens
can. A phase is done when every criterion is demonstrable, not when the code
looks finished.

### Phase 0 — Reproducible image that makes a sound

**Acceptance**

1. `make image` on a clean checkout produces a bootable `.img` with no manual
   steps.
2. The build records every package version it pinned, in a file committed with
   the artefact.
3. Flashing the image, adding Wi-Fi credentials to the boot partition, and
   booting yields a machine reachable over SSH by key.
4. `aplay -D output <testfile>` plays audibly. Card referenced by name.
5. `/etc/alsa/conf.d/output.conf` contains no `type plug` and no card index.
6. `libasound2t64` is `1.2.14-1+rpt1` and held.
7. Every build records the exact package set it produced, as a manifest
   alongside the `.img`. Rebuilds are not guaranteed to produce an
   identical set.

### Phase 1 — Takeover gap

**Acceptance**

1. Time from stop of renderer A to first sample of renderer B, measured
   same-rate and cross-rate, reported as a distribution over at least 20 runs.
2. Result recorded as a finding with scope stated.
3. ADR-0010 amended to say whether handoff needs a transition screen.

### Phase 2 — Audio layer and arbitration

No UI. Verified from logs and CLI.

**Acceptance**

1. squeezelite, go-librespot and bluealsa-aplay installed, each writing to
   `output`, each as a systemd unit.
2. `squeezelite -V DAC` asserted at startup; the unit refuses to start if the
   mixer control is absent or misnamed.
3. Arbitration: base slot LMS, one active slot. Acquisition on connection per
   ADR-0010's table. Takeover disconnects Connect-type renderers and pauses LMS.
4. Timeout ladder on release: polite stop → SIGTERM → SIGKILL, each step logged.
5. Volume bridge: phone-app volume moves the hardware mixer in variable mode and
   does nothing in fixed mode.
6. Boot volume is the configured safe level, not restored.
7. No renderer can be made to play while another holds the device.

### Phase 3 — Core state daemon

Still no UI. Tested with a WebSocket client.

**Acceptance**

1. Normalised playback model published over WebSocket: the seven skin fields
   plus position and duration.
2. Adapters for LMS (CometD), Spotify (go-librespot API) and Bluetooth (BlueZ
   D-Bus), each declaring capabilities and acquisition/release behaviour.
3. Adapters implement the public plugin contract — no special casing.
4. Metadata file written in moOde-compatible format.
5. SQLite config store; settings survive a service restart.
6. Track change on LMS appears on the WebSocket within a bounded time, measured
   and recorded.

### Phase 4 — UI shell, idle screen, display-only now playing

**Acceptance**

1. Chromium kiosk under labwc at 1280x800, starting on boot, never restarting.
2. Idle screen loads the configured URL, with a built-in fallback for
   unreachable and unconfigured.
3. Now playing shows metadata for all three renderers. No transport controls
   yet.
4. Handoff state visible during takeover.
5. Same page served to a remote browser and renders correctly.

### Phase 5 — Visualisation service and Peppy screen

**Acceptance**

1. Service reads both peppyalsa FIFOs and publishes on WebSocket, PeppyMeter
   HTTP, and FIFO passthrough.
2. Skin renderer parses all 84 skins; unknown keys or `meter.type` values fail
   the build.
3. `spectrum.name` resolves by name; `meter.visible = False` honoured.
4. Entry from now playing shows no construction — measured, not asserted.
5. Skin rotates per track, with the next track's skin composited ahead of time.
6. Renderer change exits to now playing; idle timeout returns.
7. Absent fields do not render their layer.

### Phase 6 — Now playing, full

**Acceptance**

1. Transport controls rendered from adapter capability declarations.
2. Controls that would not work are hidden or non-editable per the cross-cutting
   rule, never dead.
3. Artist and track info panels.
4. Peppy screen entry button.

### Phase 7 — Library browse

**Acceptance**

1. Full SlimBrowse: My Music, Radio, plugin menus.
2. `base.actions` / `itemsParams` dispatch implemented.
3. `nextWindow` precedence and in-place refresh correct.
4. Pagination on lists of thousands.
5. Actions map to controls through the lookup table; unknown actions in a
   context menu.
6. Text-input items shown but not editable on the panel; editable remotely.

### Phase 8 — Enrichment and lyrics

Purely additive. Cannot break playback.

**Acceptance**

1. Single shared token bucket; MusicBrainz never exceeds one request per second.
2. Real User-Agent. Persistent cache including negative results.
3. Never overwrites renderer-supplied text.
4. Confidence threshold; below it, nothing shown.
5. Now playing renders before enrichment returns, every time.

### Phase 9 — Plugin contract and themes

**Acceptance**

1. Contract documented and versioned.
2. A fourth renderer built against it, in a separate repository, with no changes
   to the core.
3. Theme engine.

---

## Test tiers

| Tier | Runs | Scope |
|---|---|---|
| 0 — static | pre-commit | lint, format, type checks |
| 1 — unit | every commit | state daemon, adapters, skin parser |
| 2 — container ALSA | every commit | arbitration via `snd-aloop`, no hardware |
| 3 — hardware in the loop | self-hosted runner on `rig` | real DAC, real mixer |
| 4 — skin corpus | every commit | parse all 84 skins, fail on unknown constructs |

Boundary and architecture tests are non-deferrable. Coverage floors and lint
ceilings can be added later.

### Two rules for tier 3

**The runner asserts its environment before every job.** `alsa-lib` version,
checksum of `output.conf`, no process holding the ALSA device, expected packages
at expected versions. On failure the job stops with "environment dirty" rather
than running tests. `rig` is both the scratch machine and the runner, so a
half-finished experiment must produce a clear message rather than a confusing
test failure.

**Any test using `snd-aloop` runs its condition at least 20 times and reports
the distribution.** A single run has roughly a 30% chance of a spurious failure
(Finding 004). Single-verdict tests on this rig are not trustworthy.
