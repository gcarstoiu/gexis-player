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
   booting yields a machine reachable over SSH by key, **with root
   available to that session** (passwordless sudo for `pi`) — a shell
   that cannot become root cannot be administered. Amended 2026-09-05:
   the original wording asked only for a reachable shell and got exactly
   that — `pi` locked, password-less, no sudoers grant, unreachable to
   itself as root. Found on hardware, not by re-reading this criterion.
   The provisioning-credentials gitignore defect had the same shape: a
   rule that was correct exactly where it was checked and absent
   everywhere it wasn't stated to matter. Both times the criterion (or
   the check) was satisfied precisely and literally, and that was the
   problem.
4. `aplay -D output <testfile>` plays audibly. Card referenced by name.
5. `/etc/alsa/conf.d/output.conf` contains no `type plug` and no card index.
6. `libasound2t64` is `1.2.14-1+rpt1` and held.
7. Every build records the exact package set it produced, as a manifest
   alongside the `.img`. Rebuilds are not guaranteed to produce an
   identical set.

### Phase 1 — Takeover gap

**Absorbed into Phase 2.** The takeover gap has to be measured on the image,
not a hand-built machine — measuring it on `rig` would characterise `rig`,
not the product. The renderers it needs (squeezelite, go-librespot) are
Phase 2 deliverables, so a standalone Phase 1 cannot run before Phase 2
exists to run it on. Its three criteria are now Phase 2 criteria 8-10. This
heading is kept, unnumbered content, so the later phase numbers do not
shift.

### Phase 2 — Audio layer and arbitration

No UI. Verified from logs and CLI.

All deliverables ship in the image, via `stage-gexis`. Hand-installing on
`gexis` is acceptable for exploration mid-phase, but nothing in this phase
is done until it is in the build.

The Python core first appears here, not in Phase 3: the arbitration
supervisor has to exist, in the image, for criteria 3-7 to be real and for
the takeover gap measurement (criteria 8-10, absorbed from Phase 1) to
characterise the product rather than a hand-built stand-in. This exercises
ADR-0021's venv packaging decision earlier than the phase order implied.

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
8. Takeover gap: time from stop of renderer A to first sample of renderer B,
   measured same-rate and cross-rate, reported as a distribution over at
   least 20 runs.
9. Result recorded as a finding with scope stated.
10. ADR-0010 amended to say whether handoff needs a transition screen.

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
| 3 — hardware in the loop | self-hosted runner on `gexis` | real DAC, real mixer |
| 4 — skin corpus | every commit | parse all 84 skins, fail on unknown constructs |

Boundary and architecture tests are non-deferrable. Coverage floors and lint
ceilings can be added later.

### Two rules for tier 3

**The runner asserts its environment before every job.** `alsa-lib` version,
checksum of `output.conf`, no process holding the ALSA device, expected
packages at expected versions, matching what the image build's own manifest
recorded. On failure the job stops with "environment dirty" rather than
running tests. `gexis` is the runner — image-built, not hand-built — but
Phase 2's own preamble permits hand-installing on it for exploration, so a
not-yet-rolled-back experiment or a process left holding the device must
still produce a clear message rather than a confusing test failure. `rig` is
no longer the runner; it stays a reference machine (Findings 002-004) and a
scratch machine for exactly this kind of hand-installed exploration.

**Any test using `snd-aloop` runs its condition at least 20 times and reports
the distribution.** A single run has roughly a 30% chance of a spurious
failure (Finding 004, measured on `rig`). Single-verdict tests are not
trustworthy regardless of which machine runs them.
