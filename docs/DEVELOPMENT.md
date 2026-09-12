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

### How changes land — George's rules, 2026-09-12

**One change at a time, each gated on George's own hardware regression
pass.** Stated for Phase 2c's criteria 7-10 and applying from there on:

- **Nothing ships without George running the regression test himself.**
  Claude's own automated verification is evidence to hand him, never a
  substitute for it. "Verified on `gexis`" by Claude is not the gate.
- **Land one change at a time, never a batch.** A batch "results in many
  possible breaking changes" — it makes a regression impossible to
  attribute, which is precisely how this project lost two days.

Not a new caution, a scar: Finding 014's `/player/resume` and Finding 013
§1's `stop_unit`/`restart_after_release` were both shipped and reverted
within a day, both passed scripted testing first, and both travelled
alongside other changes. ADR-0010 carries the reverts; `docs/LESSONS.md`
carries the pattern.

If a measurement turns up a defect part-way through a criterion, surface it
and let George choose whether to fix it now or after — do not fold the fix
into the change in flight.

### Branching

- One branch per phase: `phase-0-image`, `phase-2-arbitration`.
- Sub-PRs into the phase branch where a phase is large. Phase branch merges to
  `main` when its acceptance criteria pass.
- Commits are small and describe *why*, not *what*.

### Model split

Sonnet in Claude Code for implementation. Escalate to Opus after two failed
attempts, or immediately for anything that would become an ADR.

### Licence

gexis-player is GPL v3 (ADR-0025). Every source file we author carries
`# SPDX-License-Identifier: GPL-3.0-or-later` (or the equivalent comment
syntax) as its first line. Vendored third-party files keep whatever header
their upstream carries; do not add our SPDX line to a file we didn't write.

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

**Iteration loop, demonstrated for systemd units and config files only:**
edit on `gexis` over SSH, confirm the fix works there, then port the
change into `stage-gexis` and rebuild once. The rebuild makes the fix
real — part of the reproducible image — it is not how you find out
whether the fix works; that happens on `gexis` first. This loop is *not*
yet demonstrated for the Python core, which has never been iterated on
in the image. Do not assume it holds there until it has been.

The Python core first appears here, not in Phase 3: the arbitration
supervisor has to exist, in the image, for criteria 3-7 to be real and for
the takeover gap measurement (criteria 8-10, absorbed from Phase 1) to
characterise the product rather than a hand-built stand-in. This exercises
ADR-0021's venv packaging decision earlier than the phase order implied.

**Sub-phases**, one branch each off `phase-2-arbitration`, merged back to it
when their criteria pass:

- **2a — criteria 1-2.** Renderer packaging. **Done, verified on
  hardware.**
- **2b — criteria 3-6.** Arbitration core, timeout ladder, volume bridge,
  boot volume. The Python core lands here, plus ADR-0021's venv addendum.
  **Done, verified on hardware, 2026-09-10.** Criteria 3 and 6 hold
  cleanly. Criterion 4 (timeout ladder) and criterion 5's fixed-output
  half each carry one explicitly deferred item, George's decision,
  2026-09-10 — not oversights: Bluetooth's release ladder was found
  once (2026-09-08) to still hold the device after a full SIGKILL
  escalation, not specifically re-reproduced since (every Bluetooth
  release measured this phase succeeded via polite stop alone); and
  fixed output mode (mixer locked at 240, phone sliders inert) was
  never implemented in `gexis_core` — only variable mode is built and
  hardware-verified. See ADR-0010's "Open" section and ADR-0018's "To be
  recorded once resolved" for the full record of both.
- **2c — criteria 7-10.** Criterion 7 is an attack test across all
  renderers, not a feature, so it belongs with the takeover gap
  measurement rather than with 3-6. **Criteria 7-10 need re-running after
  2d** — every number in Finding 015 was measured against the release
  mechanism ADR-0027 replaces.
- **2d — criteria 3-4, reworked for [ADR-0027](decisions/0027-lms-power-as-arbitration-mechanism.md).
  DONE, verified on the flashed image, 2026-09-12.** Closed on: 84 unit
  tests; the installed core diffed file-by-file against the branch HEAD so
  the image genuinely contains it (the previous image silently predated
  Finding 016 entirely, which is why this is checked rather than assumed);
  13/13 end-to-end checks run against the flashed build — Spotify's first
  ALSA open succeeds with `active` firing (0.89s), LMS returns on
  activation with playback and position restored (0.89s), deactivation
  leaves nobody holding the device; and George's own listening pass —
  takeovers correct, seek resumes at the right position, power-off silent,
  power-on a barely-audible click he judged not worth chasing. Session logs
  show no ladder escalation of any kind and zero go-librespot
  "resource busy" failures, the signature blocker 2 used to leave on every
  handoff.
  **Not covered by this closure:** criterion 4's Bluetooth exception is
  unchanged and still open (ADR-0010); criteria 7-10 still need re-running
  (2c); ADR-0027's own deferred items stand.
  New, 2026-09-12. LMS's player power becomes the arbitration mechanism:
  record the transport state, `pause`, then `power 0` on release;
  powering on is the acquisition; restore the recorded state on return;
  no permanent base slot. This is a **rework of already-accepted
  criteria, not new scope** — 2b's work was correct against the wording
  it was verified under, and that wording has since changed. Touches
  `adapters/lms.py`, `arbitration.py`'s base-slot assumption
  (`_active is None` currently means "LMS is current" and has to become a
  real nobody/lms/other tri-state), and the base-slot assumptions baked
  into `core/tests/test_arbitration.py`. Evidence: Finding 018.

  **Branch: `phase-2d-lms-power`, cut off `phase-2c-takeover` rather than
  off `phase-2-arbitration`** (George's call, 2026-09-12, to keep 2d's work
  separate). A deliberate deviation from the one-branch-off-the-phase-branch
  rule above, not drift: 2d's code modifies the same `arbitration.py` and
  `volume.py` that 2c's Finding 016 polling fix and blocker 4 volume fix had
  already changed, so branching off `phase-2-arbitration` would have produced
  a tree that was never built or tested in that configuration - this repo's
  recurring "verification ran against the wrong reality" failure. 2c's own
  branch was moved back to the last pre-ADR-0027 commit so the two do not
  overlap; it was local-only and unpushed, so nothing published was rewritten.

**Known interim regression, accepted deliberately (2026-09-12).** ADR-0027
makes takeovers clean but leaves LMS deactivated afterwards, and nothing
re-activates it silently. Until Phase 4's activation control ships
(criterion 7 there), **the only way back to LMS after a Spotify or
Bluetooth session is the LMS phone app.** For the phases in between, the
box is better at handing over and worse at coming back. George accepted
this knowingly — he uses the LMS app anyway — but it is the reason
activation was pulled into Phase 4 rather than left to Phase 6's
capability-driven transport controls.

**Acceptance**

1. squeezelite, go-librespot and bluealsa-aplay installed, each writing to
   `output`, each as a systemd unit.
2. `squeezelite -V DAC` asserted at startup; the unit refuses to start if the
   mixer control is absent or misnamed.
3. Arbitration: one renderer holds the device, or none. Acquisition on
   connection per ADR-0010's table **as amended by
   [ADR-0027](decisions/0027-lms-power-as-arbitration-mechanism.md)** —
   for LMS that is powering the player *on*, not pressing play. Takeover
   disconnects Connect-type renderers; for LMS it records the transport
   state, pauses, then powers the player off, and the player stays
   deactivated until the user activates it again.
   **Ships without ADR-0010's sync-group behaviour** — explicitly
   deferred, not unresolved; see ADR-0010's "Open" section.
   **Reworded 2026-09-12 (ADR-0027).** The previous wording said "base
   slot LMS, one active slot" and deferred empty-base-slot behaviour as
   undefined. There is no base slot now, and "no renderer holds the
   device" is a routine state rather than a deferred edge case — so that
   deferral is answered, not carried. Criterion 3 was verified against
   the old wording in 2b (2026-09-10); re-verification against this
   wording is 2d.
4. Timeout ladder on release: polite stop → SIGTERM → SIGKILL, each step
   logged, applying uniformly to every renderer as written.

   **LMS no longer reaches this ladder in normal operation, as of
   2026-09-12 ([ADR-0027](decisions/0027-lms-power-as-arbitration-mechanism.md)).**
   Powering the player off frees the ALSA device in 0.06-0.11s (measured,
   n=4, Finding 018) against 1.44s for a commanded pause, so the polite
   rung succeeds every time and escalation is unreachable short of a
   genuine fault. The ladder stays in place as the escalation safety net
   and still applies in full to Spotify and Bluetooth. Everything in the
   next paragraph is now **history** — kept because it is the reasoning a
   later reader would otherwise re-derive, and because the SIGKILL-not-
   SIGTERM point remains true of squeezelite if the ladder is ever
   genuinely reached.

   **History, not current behaviour:** LMS went through two reverted attempts
   (2026-09-06, 2026-09-07) at routing around squeezelite's `-C` idle
   timer — skip the polite rung and SIGTERM immediately, then SIGKILL
   unconditionally — before landing on the actual fix, 2026-09-08:
   `squeezelite.service` runs `-C 1`, which measured ~700ms to release
   against a commanded pause (no audible artefacts), comfortably inside
   the default 3s polite grace. LMS's ladder *timing* needs no exception
   anymore. Its escalation *signal* still does, permanently: squeezelite
   exits cleanly on SIGTERM (systemd never counts that as a failure), so
   `LmsAdapter.signal_stop` always sends SIGKILL regardless of which
   rung called it — confirmed necessary twice, including a live
   reproduction from the ladder's own genuine escalation after `-C 1`
   shipped (a real takeover still needed the full ladder once). See
   ADR-0010's amended implementation note for the full history.

   **Bluetooth is a live, unresolved exception as of 2026-09-08:** the
   full ladder ran against `bluealsa-aplay.service` — polite stop
   (disconnect), SIGTERM, SIGKILL — and the device was still held after
   SIGKILL. Not fixed; see ADR-0010's "Open" section for the two
   candidate causes (a too-fast unit restart racing the check; the
   process holding the PCM open even after its IO worker exits on
   disconnect) and why the fix likely isn't "kill it more reliably."
5. Volume bridge: phone-app volume moves the hardware mixer in variable mode and
   does nothing in fixed mode.
6. Boot volume is the configured safe level, not restored.
7. No renderer can be made to play while another holds the device.
8. Takeover gap: time from stop of renderer A to first sample of renderer B,
   measured same-rate and cross-rate, reported as a distribution over at
   least 20 runs.
9. Result recorded as a finding with scope stated.
10. ADR-0010 **and ADR-0027** amended to say whether handoff needs a
    transition screen. **Note the answer is now likely per-pair, not
    global:** LMS↔Spotify handoffs measured 0.07-0.7s under ADR-0027,
    while Bluetooth→LMS is still gated by Bluetooth's own 2.5-2.9s
    release, which ADR-0027 does not touch.

### Phase 3 — Core state daemon

Still no UI. Tested with a WebSocket client.

**Acceptance**

1. Normalised playback model published over WebSocket: the seven skin fields
   plus position and duration. **The model must also express "no renderer
   holds the device" and each renderer's availability**
   ([ADR-0027](decisions/0027-lms-power-as-arbitration-mechanism.md),
   2026-09-12) — the old model could always name a current renderer,
   because LMS was permanently the base. It no longer can, and the UI
   cannot offer to activate LMS unless the model says LMS is
   deactivated.
2. Adapters for LMS (CometD), Spotify (go-librespot API) and Bluetooth (BlueZ
   D-Bus), each declaring capabilities and acquisition/release behaviour.
3. Adapters implement the public plugin contract — no special casing.
4. Metadata file written in moOde-compatible format.
5. SQLite config store; settings survive a service restart.
6. Track change on LMS appears on the WebSocket within a bounded time, measured
   and recorded.

### Phase 4 — UI shell, idle screen, now playing (display-only, plus LMS activation)

**Acceptance**

1. Chromium kiosk under labwc at 1280x800, starting on boot, never restarting.
2. Idle screen loads the configured URL, with a built-in fallback for
   unreachable and unconfigured.
3. Now playing shows metadata for all three renderers. No transport controls
   yet.
4. Handoff state visible during takeover.
5. Same page served to a remote browser and renders correctly.
6. **"No renderer holds the device" is a first-class screen state, and the
   user can tell why.** New, 2026-09-12
   ([ADR-0027](decisions/0027-lms-power-as-arbitration-mechanism.md)).
   Distinct from criterion 2's idle screen, which meant "LMS is current
   but not playing" — under ADR-0027 nobody need hold the device at all,
   routinely. ADR-0010's accountability rule applies directly: a user
   who finds LMS deactivated after a Spotify session must be able to
   account for it.
7. **The user can activate LMS from this UI.** New, 2026-09-12, George's
   decision that it belongs in Phase 4 rather than waiting for Phase 6's
   capability-driven transport controls. This is the one control this
   phase is not display-only about, and deliberately so:
   ADR-0027 leaves LMS deactivated after every takeover and never
   re-activates it silently, so **without this control the only route back
   to LMS is the LMS phone app** — unacceptable on an appliance with its
   own screen. Until it ships, that phone-app dependency is a known,
   accepted interim regression; see the note under Phase 2.

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
