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

### The settings inventory is kept current as work happens

**George's rule, 2026-09-13.** Implementing anything that comes — or might
come — with a setting means proposing it for
[ADR-0022](decisions/0022-settings.md)'s inventory, and appending it **only
after George confirms**. He is PM; the inventory is his list, so a row is
proposed, never silently added.

*Why the rule exists:* that inventory went stale once already. Assembled
2026-09-04, by 2026-09-13 it had missed Phases 2-4, ADRs 0024-0028 and
every volume finding — 16 items where there should have been about fifty,
with two whole groups (arbitration, and system/maintenance) absent
entirely. Nobody decided to leave them out; nothing prompted anyone to
write them down while the work was happening, so they had to be
reconstructed from the records afterwards, which loses the reasoning that
was live at the time.

It also protects a real hazard. Several rows are placeholders nobody ever
confirmed — `restore_volume_floor_db` at −40 dB is the clearest — and a
settings screen built on a list nobody kept current would ship those
placeholders as though they were choices.

*What counts as a trigger:* a hardcoded constant, a new value in `Config`
or `core.toml`, a behaviour with a plausible second choice, or anything
that would differ per installation. Mark the proposed row the way that
record does: **[R]** recorded / **[H]** hardcoded today / **[N]** genuinely
new suggestion / **[?]** a decision George still owes — and add any **[?]**
to the waiting-on list at the end of the inventory.

### UI work: imported whole, wired progressively, checked against a picture

**George's decisions, 2026-09-13.** From Phase 4 the UI is built from
complete designs rather than per-phase mockups: **import the whole design,
render it, and wire the backend to whatever phase we are actually at.** The
alternative — hiding unwired parts — would have made Claude decide what each
screen looks like with elements removed, which is design work landing in the
wrong hands.

Three things keep that honest:

1. **Unwired UI is marked in code**, with one convention, so "what is still a
   shell" is a generated list rather than something remembered. **The
   convention (2026-09-15): a `data-unwired="<step or phase>"` attribute** on
   the element — `4e`, `phase-6`, `home` — listed with
   `grep -rn data-unwired ui/src`. It doubles as
   the wiring backlog for Phases 6 and 8.
2. **Removal is continuous.** The phase that wires a control clears its marker
   as part of that work — it is editing those components regardless. Phase 9
   criterion 2 is only the backstop for whatever slipped through; a one-off
   audit there would be the largest-possible-batch change at the point of
   least appetite for churn.
3. **Accuracy is checked against a picture, not a description.** For each
   screen, screenshot the running UI **from the device's own Chromium at
   1280x800** and compare it to the design's exported PNG. The device's
   browser is the only authoritative render (ADR-0023 pins it) and it catches
   what a dev-machine render hides: self-hosted fonts, DPI, real panel
   colour. The comparison is what stops "is this accurate?" becoming an
   exchange of opinions.

Design deliverables are therefore: the artboard HTML/CSS, **static PNG
exports per state**, tokens as CSS custom properties, component boundaries,
and phase labels on elements. The exports are committed to the repo as
reference-only, never built, so a later redesign is a diff rather than a
re-derivation.

**How an export lands (2026-09-15).** Claude Design cannot write to the repo;
George copies each export into `design/`. So history is kept by commit:

1. The previous export is already committed, so nothing is lost by
   overwriting it. **Replace the folder's contents wholesale** (delete, then
   paste) so a file the new export dropped shows up as a deletion.
2. Claude commits the export **on its own, before any port work**
   (`Design export: <what changed>`), then reads `git diff HEAD~1 -- design/`
   to see what actually changed rather than what the export says changed.
3. `design/source/` is locked — built from, never edited. Run
   `design/verify.html` over HTTP after any change to the package.

**Deviations the port keeps across exports.** Claude Design does not know
about these, so a new export will not contain them. Re-apply them when
porting, until the design takes them in.
**[design/IMPLEMENTED-DIFFERENTLY.md](../design/IMPLEMENTED-DIFFERENTLY.md)
collects all of them for Claude Design** - the list below plus everything
decided since, sorted by whether it was hardware, a UX call or scope
(written for the Phase 9 sweep, 2026-09-18):

- **Volume glyph (2026-09-15, George).** The now playing volume button draws
  the drawer's 30px glyph (`ui/src/lib/VolumeIcon.svelte`), not the design's
  26px one, whose three arcs merge at full volume.
- **Drawer opens on a change from elsewhere (2026-09-15, George).** A
  phone's volume change opens the drawer, which closes 3 s after the last
  change. The panel's own changes and a takeover's restored level do not
  open it.
- **Press feedback shrinks, it does not fill (2026-09-16/17, George).** The
  design's grey press fill read as a flash on the play button, then on
  prev/next/shuffle/repeat, then on now playing's Home, Settings' Back and
  the mini strip. Those keep their resting fill and shrink instead.
- **The library and Settings are mounted only while open (2026-09-17).** The
  design leaves both in the page at opacity 0; on the panel the closed
  library then covered now playing in black.
- **Mini strip volume glyph (2026-09-17).** The strip draws the drawer's
  30px glyph, for the same reason as now playing's button above, not the
  design's 24px one.
- **New Music artist names at 0.60 alpha (2026-09-17).** The design uses
  0.55, under its own 4.5:1 floor for 15px text (`design/tokens.css`).
- **Card counts are singular where they should be (2026-09-17):**
  "1 playlist", not the design's "1 playlists".
- **Settings inventory (2026-09-15).** `idle_grace` is not a row — ADR-0033
  merged it into `idle_timeout` (5 min); `travel_curve` is decided (ADR-0034,
  marks `RH`); `drawer_on_external` and `drawer_autohide` are added under
  Display › Panel. The daemon's `settings_registry.json` is authoritative.

### Branching

- One branch per phase: `phase-0-image`, `phase-2-arbitration`.
- Sub-PRs into the phase branch where a phase is large. Phase branch merges to
  `main` when its acceptance criteria pass.
- Commits are small and describe *why*, not *what*.

### The build's downloads are cached locally

`make image` vendors five third-party artefacts — Gelo5's skins (143 MB),
the two Peppy engines and the screensaver templates, the DSEG font, and
go-librespot. Each is pinned by sha256 and, since
[ADR-0042](decisions/0042-a-local-cache-for-vendored-downloads.md), read from
a content-addressed cache before the network.

- The cache lives at `$HOME/.cache/gexis-player/downloads`, or wherever
  `GEXIS_BUILD_CACHE` points, and is bind-mounted into pi-gen's container.
- Entries are named by their checksum, so a hit verifies itself and a changed
  pin is a different file rather than a stale one.
- **It is optional.** Delete it and the next build refetches. A build with no
  cache mounted behaves exactly as it did before.

**It is not a backup.** It protects the machine holding it, not a fresh
clone. A mirror we control is the thing that would, and is deferred.

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

**Extended 2026-09-15:** Phase 4 criteria 6 and 7 were withdrawn (George —
starting playback from the phone re-activates LMS, so nothing is stranded).
This regression is now accepted **until Phase 7's library browse**, not
Phase 4.

**PHASE 2 CLOSED, 2026-09-12.** All ten criteria met, with five items
carried out explicitly deferred rather than silently unmet. Sub-phases
2a/2b/2c/2d all closed; the whole phase was verified on the flashed image
`v0.2.1-51-g89dca15-dirty`, not on hand-installed builds.

**What is deferred, and therefore what this closure does NOT claim:**

| deferred | criterion | why |
|---|---|---|
| Bluetooth's release ladder still does not free the device | 4 | Found 2026-09-08, never re-reproduced since the busy-check fix; George's decision 2026-09-10 to defer. ADR-0010 "Open". |
| Fixed output mode is unimplemented | 5 | Only variable mode is built and verified. ADR-0018. Most naturally built once mode selection has a UI (Phase 4+). |
| Criterion 7 unproven for Bluetooth pairs | 7 | Not scriptable — contested rounds need a human tapping a phone each time. |
| Cross-rate takeover gap unmeasured | 8, 9 | A 60,974-track library scan found zero non-44.1kHz files. Needs test content sourced first. **This half of criterion 8 is unmet, not met-with-caveats.** |
| Bluetooth takeover gap unmeasured | 8, 9, 10 | Same scriptability limit. Bluetooth pairs therefore show the transition screen by default. |

Also carried forward, decided rather than open: Bluetooth discoverability
stays at BlueZ's 3-minute default (ADR-0024), so re-pairing after a reflash
must happen within three minutes of boot.

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
   **MET for LMS↔Spotify, 2026-09-12** — 24/24 genuinely contended rounds,
   zero violations, with no ladder escalation and `NRestarts=0` throughout
   (Finding 019). **Unproven for any Bluetooth-involving pair**, deferred
   with criterion 8's Bluetooth leg for the same reason. Note the previous
   attack test had silently stopped contending at all under ADR-0027's
   acquisition model and would have reported a false pass — see the finding.
8. Takeover gap: time from stop of renderer A to first sample of renderer B,
   measured same-rate and cross-rate, reported as a distribution over at
   least 20 runs.
   **MET for the same-rate LMS↔Spotify pair, 2026-09-12** — n=33
   (LMS→Spotify, median 224.6 ms) and n=27 (Spotify→LMS, median 335.2 ms),
   both clearing the ≥20 requirement, against Finding 015's 1827.8 ms and
   4170.9 ms on the old mechanism. Zero product-side failures across 72
   attempted rounds. See Finding 020.

   **Narrowed by George's decision, 2026-09-12, to the same-rate
   LMS↔Spotify pair only.** Two legs are deferred, both for reasons of
   what can actually be measured rather than of effort:
   - **Cross-rate: no content exists to test with.** A full library scan
     (60,974 tracks, LMS's own `songs` JSON-RPC query, paginated) found
     **zero non-44.1kHz tracks**. Testing this leg would mean sourcing and
     adding dedicated test content first. Deferred, not skipped — the
     criterion's cross-rate half is unmet and stays unmet.
   - **Bluetooth-involving pairs: not scriptable.** `bluetoothctl connect`
     reconnects the A2DP profile but not reliably the audio stream, so
     contested Bluetooth rounds need a human tapping a phone for every
     run — which a ≥20-run distribution makes impractical. A harness
     limitation, not a product defect. Bluetooth's own release is also
     still 2.5-2.9s and untouched by ADR-0027, so its numbers would
     characterise a path with a known open defect (ADR-0010's Bluetooth
     release item).

   **What this means for criterion 9/10:** they can be satisfied for the
   same-rate LMS↔Spotify pair and for nothing else. Criterion 10's
   transition-screen answer is therefore a per-pair answer with two pairs
   unmeasured — say so rather than generalising from the one that was.
9. Result recorded as a finding with scope stated.
   **MET, 2026-09-12 — [Finding 020](findings/020-criterion8-takeover-gap-adr0027.md)**,
   which supersedes Finding 015's numbers entirely (those were measured
   against the mechanism ADR-0027 replaced). Scope stated there: same-rate
   LMS↔Spotify only, activation route only, cross-rate and Bluetooth
   deferred and explicitly unmet.
10. ADR-0010 **and ADR-0027** amended to say whether handoff needs a
    transition screen. **MET, 2026-09-12 — George's decision: the screen
    exists and is shown by DEFAULT, skipped only for a pair measured below
    1 second.** Evidence-gated rather than a fixed list: a pair earns its
    exemption by being measured and loses it if a later measurement moves
    it back above. Today that exempts same-rate LMS↔Spotify (224.6 /
    335.2 ms) and exempts nothing else — Bluetooth pairs and cross-rate are
    unmeasured and therefore show it. Recorded in ADR-0010's "Handoff
    transition screen" section; ADR-0027 cross-references it.
    **Consequence:** the transition state is a real Phase 4 requirement,
    and the renderer pair must be known at render time to decide whether to
    show it. **Note the answer is now likely per-pair, not
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

   **MET, 2026-09-12** — `model.py`/`state.py`/`wsserver.py` built and
   hardware-verified on `gexis` (hand-installed into the running
   `gexis-core.service` over SSH, George's explicit call for this
   testing round — see HANDOFF.md for why that's noted as a one-off
   rather than a standing workflow decision). "Availability" means
   "backend reachable", George's decision: only LMS ever gets an
   activate control from our own UI (Phase 4), so that's the only thing
   the field needs to gate or explain; Spotify/Bluetooth availability is
   a status line, not a button. All three renderers confirmed by George
   against a live WebSocket client: LMS metadata verified end-to-end
   against real library tracks and a live radio stream (title, artist,
   album, artwork, sample rate, position, duration, and the
   `current_title` remote-stream fallback all correct); Spotify's
   metadata and its "went inactive" release both confirmed; Bluetooth's
   metadata confirmed after a same-session fix (see below). "No renderer
   holds the device" confirmed reachable from all three renderers, not
   just LMS's own deactivation.

   Two real defects found and fixed live during this verification, both
   recorded in full in HANDOFF.md: Bluetooth reported no metadata at all
   (BlueZ's `MediaPlayer1` proxy has no `on_properties_changed` of its
   own — the signal belongs to `org.freedesktop.DBus.Properties`
   instead) and Spotify/Bluetooth disconnects never told the supervisor
   "nobody holds it now" (`on_release` was wired for LMS's deactivation
   only — an oversight in the original ADR-0027 work, George's call, not
   a deliberate deferral). Both fixed and re-confirmed on hardware.
2. Adapters for LMS (CometD), Spotify (go-librespot API) and Bluetooth (BlueZ
   D-Bus), each declaring capabilities and acquisition/release behaviour.

   **MET, 2026-09-12** — `Capabilities` (`adapters/base.py`), ADR-0013's
   contract fields derived from the three built-ins' actual behaviour:
   audio connection (ADR-0009, "output" for all three today), the named
   acquisition events each adapter treats as a takeover, and which of
   ADR-0014's seven skin fields each renderer can ever supply (artwork/
   sample rate — Bluetooth has neither, confirmed live against a real
   phone this session). `release_action` is not duplicated here; it
   already exists on `Adapter` and is used directly by `arbitration.py`.
   `controls` (transport commands accepted from outside) is declared but
   left honestly empty on all three — no adapter exposes a way to send a
   user's command yet, Phase 4 has no transport controls beyond LMS
   activation, and Phase 6 is where that becomes real. Published as a new
   `capabilities` field in the state WebSocket payload alongside
   criterion 1's fields; confirmed correct on `gexis`.
3. Adapters implement the public plugin contract — no special casing.

   **MET, 2026-09-12, scoped by George's explicit decision.** Two
   readings were possible: removing renderer-name branching from the
   core's own wiring code (in-process, extending criterion 2's
   Capabilities), or actually restructuring the three built-ins into
   separate OS processes per
   [ADR-0016](decisions/0016-plugins-as-separate-processes.md)'s IPC
   model. George chose the former — the built-ins stay in-process Python
   classes; ADR-0016's separate-process architecture is not attempted
   here and remains open for whenever a real second plugin (Qobuz
   Connect) needs it.

   Found by grep, not hypothetical: `renderer_volume.py` hardcoded
   `MANAGED_RENDERERS = ("lms", "spotify")`, `volume.py` branched on
   `if renderer == "spotify"`, and `__main__.py` constructed two
   `DummyMixerBridge` instances and one `VolumeBridge` by naming
   "lms"/"bluetooth"/"spotify" directly. Fixed by extending
   `Capabilities` with the volume side of the contract —
   `volume_managed`, `volume_mechanism` (`DUMMY_MIXER` or
   `SOFTWARE_API` — two genuinely different mechanisms, not an arbitrary
   split), `dummy_mixer_card` — so `__main__.py`'s wiring derives both
   the managed-renderer set and which bridge each renderer needs from
   its own adapter, rather than naming any renderer by hand.
   `DummyMixerBridge` itself needed no changes — it was already generic;
   all the special-casing was in what constructed it. Verified on
   `gexis`: a clean restart, and both `restore_volume`'s write-on-acquire
   and the `DummyMixerBridge` mirror path (a live LMS volume nudge)
   produced the same values as before the refactor — no behavioural
   change, only where the renderer-specific facts live.
4. Metadata file written in moOde-compatible format.

   **MET, 2026-09-12.** `metadata_file.py` writes `/var/local/www/
   currentsong.txt` in moOde's own key=value format - sourced directly
   from `moode-player/moode`'s `worker.php` (`updExtMetaFile()`), not
   assumed: plain `key=value` lines (not JSON, despite some forum/UI
   docs describing that shape elsewhere in moOde's stack), atomic write
   via a `.tmp` file, rename, then `chmod 0666`. **Scoped by George's
   decision to only the fields the model already has** — `file`,
   `artist`, `album`, `title`, `coverurl` — leaving out `encoded`/
   `bitrate`/`outrate` (moOde's closest analog, its "external renderer
   active" branch, needs codec/bit-depth data and live ALSA hw_params
   this codebase doesn't track) rather than faking them. Renderer labels
   ("Squeezelite Active", "Spotify Active", "Bluetooth Active") are
   moOde's own vocabulary verbatim. Verified on `gexis`: real file,
   correct permissions, correct content against a live LMS track.
5. SQLite config store; settings survive a service restart.

   **MET, 2026-09-12.** `settings.py`'s `SettingsStore` - generic
   key-value persistence, JSON-encoded values in one table so a future
   setting never needs a schema migration, only a new key. Holds no real
   setting yet: none of ADR-0022's inventory (output mode, boot volume,
   device name, Bluetooth trusted devices, ...) has a UI to change it
   before Phase 4 exists - building the storage mechanism ahead of what
   will use it, same pattern as criteria 1-4. Distinct from `config.py`'s
   `Config` (deployment-time TOML, edited by hand over SSH) - this is
   runtime state. Wired into `__main__.py` so the DB and schema are
   exercised for real on the image. Verified on `gexis`: a value set
   before a service restart reads back correctly after one.
6. Track change on LMS appears on the WebSocket within a bounded time, measured
   and recorded.

   **MET, 2026-09-12 — [Finding 021](findings/021-criterion6-lms-track-change-latency.md).**
   20/20 rounds, n=20, median **699.5 ms** (min 644.0, max 787.3) —
   tight, unimodal, no outliers. Measured on `gexis` itself (T0 issuing
   `playlist play` to the real LMS server, T1 the first WebSocket frame
   carrying the new track's metadata), alternating between two distinct
   local library tracks so every round is an unambiguous change. **No
   numeric bound was specified anywhere in this project's records for
   what "bounded" means** — the finding reports the measured
   distribution as the record rather than asserting a pass/fail line
   against a number that was never written down. Scope: one pass, one
   session, both tracks 44.1 kHz (the library has no other content to
   test with), LMS already active throughout (this is a mid-session
   track change, not an acquisition — Findings 018/020 cover that
   separately).

**PHASE 3 CLOSED, 2026-09-12.** All six criteria met. See HANDOFF.md for
the full session record, including two live defects found and fixed
during verification (Bluetooth's D-Bus interface bug; the Spotify/
Bluetooth `relinquish()` oversight) and the scope decisions George made
along the way (availability semantics, criterion 3's in-process fix
over ADR-0016's separate-process model, criterion 4/5's minimal scope).

### Phase 4 — UI shell, idle screen, now playing (display-only, plus LMS activation)

**Acceptance**

1. Chromium kiosk under labwc at 1280x800, starting on boot, never restarting.
2. Idle screen loads the configured URL, with a built-in fallback for
   unreachable and unconfigured.
3. Now playing shows metadata for all three renderers. No transport controls
   yet. **Volume is not a transport control and is in scope — see criterion 8**
   (George's decision, 2026-09-12); transport proper (play/pause/next/previous/
   seek) stays Phase 6.

   **Now playing shows no sample rate and no codec — dropped in the design
   (George, 2026-09-15).** The paragraph below is withdrawn for now playing.
   ADR-0019's codec rule for the *Peppy screen* is untouched, and the `codec`
   field built in 4a stays in the payload for it. *Withdrawn text follows.*

   **Bluetooth's sample-rate field carries the codec, not a rate**
   (George's decision, 2026-09-12, extending [ADR-0019](decisions/0019-peppy-screen-lifecycle.md)'s
   rule for the Peppy screen to now playing as well — "the decode rate is the
   codec's, not the source's"). This needs new adapter work: no codec is
   captured anywhere today. BlueZ's `MediaTransport1` carries it and that
   object is already watched (it is one of the two Bluetooth acquisition
   signals), so it is an extension of existing code rather than new plumbing.

   **Missing metadata may be filled in later and the layout must not move**
   (George, 2026-09-12). Bluetooth supplies no artwork, but artist/album/title
   are enough for the Phase 8 enrichment service to find cover art and lyrics,
   so "absent" is transient, not permanent. ARCHITECTURE.md already states the
   requirement this creates: "Text appears immediately; art and bio arrive
   later. Reserve artwork space so late arrival does not reflow."
   [ADR-0012](decisions/0012-enrichment-additive-only.md) means no
   "possibly wrong" treatment is needed — enrichment never overwrites
   renderer-supplied text and shows nothing below its confidence threshold.
4. Handoff state visible during takeover. **Sharpened 2026-09-12 by
   criterion 10's answer: the transition state is shown by DEFAULT and
   skipped only for a renderer pair measured under 1 second** (ADR-0010,
   "Handoff transition screen"). Two consequences this phase has to build
   for, neither of which the original one-line criterion implied:
   - **The renderer pair must be known at render time**, not just "a
     handoff is happening" — the decision to show or skip depends on which
     pair it is.
   - **The exempt list is data, not a constant.** A pair earns exemption by
     being measured and loses it if a later measurement moves it back above
     the threshold. Today only same-rate LMS↔Spotify is exempt; every
     Bluetooth pair and anything cross-rate shows the screen.
5. Same page served to a remote browser and renders correctly. **Clarified
   2026-09-15 by [ADR-0032](decisions/0032-one-page-two-surfaces.md):** still
   the same page, and still required to render correctly — but on a remote
   browser "correctly" means the **settings surface** laid out for phone
   width, not the panel interface shrunk. The panel renders everything;
   a remote browser renders only settings. Only the settings screen is
   responsive; every other screen stays at the fixed 1280x800 artboard.
   **Increment 1 built 2026-09-15** per
   [ADR-0035](decisions/0035-settings-api.md): the daemon's settings registry
   (every inventory row, none wired), `GET /settings`, `PUT`/`POST
   /settings/{key}`, `GET /surface`, `settings_revision` in `/state`, and
   `Settings.dc.html` ported as the responsive component. A remote browser gets
   only settings. Two design deviations: `idle_grace` merged into
   `idle_timeout` (ADR-0033), and the two volume-drawer rows added. **Passed George's phone
   check 2026-09-15.**
   **Increment 2 built 2026-09-15:** idle timeout, idle URL (editable from the
   phone; clearing returns to `core.toml`), and both volume-drawer settings
   wired, reaching the panel live. **Passed George's phone check 2026-09-15.
   Criterion 5 met.**
6. **WITHDRAWN 2026-09-15, together with criterion 7** (George: *"there is no
   need for this. As soon as I start playing from my phone, LMS activates so
   there is no risk of getting stuck"*). ADR-0027 measured that auto-power-on,
   so nothing is stranded. **Consequence, accepted knowingly:** until Phase 7's
   library browse, the panel alone cannot start LMS after a takeover — the
   phone is the only route. The regression this pair existed to close (the
   note under Phase 2) is now accepted until Phase 7 rather than Phase 4. What
   the panel shows when nothing holds the device is a design question, not
   an acceptance criterion. The backend half built in 4a — `POST
   /renderer/lms/activate` and LMS's `activate` control — stays; it is
   unused by the UI, not wrong. Numbering is kept so older references still
   resolve. *Original text follows.*

   **When no renderer holds the device, the screen offers the action that
   gets back to music.** Reframed 2026-09-12 by George, replacing the
   original wording ("...and the user can tell why").

   *What changed and why.* The original criterion, added the same day from
   [ADR-0027](decisions/0027-lms-power-as-arbitration-mechanism.md), leaned
   on ADR-0010's accountability rule: a user finding LMS deactivated after
   a Spotify session must be able to account for it. George's objection:
   the user does not actually need that explained, because the obvious
   next action already works — Phase 7's library browse, tap an album, and
   LMS's own auto-power-on starts it (documented and measured in ADR-0027's
   Open section: deactivated at 24.4s, a plain `play` came back at 2.3s;
   the lost position does not matter when starting something new).

   *Why the screen survives anyway, with a different job.* Library browse
   is Phase 7, three phases out. Until it lands, this state needs something
   on screen and criterion 7's activate control needs a home — and the idle
   screen is a poor host for it, being a user-configured external page we
   do not own (criterion 2). So this is a deliberately minimal screen whose
   purpose is to offer the one action, not to explain the state, **and it
   is expected to be retired when Phase 7's browse screen can take over
   that job.**
7. **WITHDRAWN 2026-09-15 — see criterion 6.** *Original text follows.*

   **The user can activate LMS from this UI.** New, 2026-09-12, George's
   decision that it belongs in Phase 4 rather than waiting for Phase 6's
   capability-driven transport controls. This is the one control this
   phase is not display-only about, and deliberately so:
   ADR-0027 leaves LMS deactivated after every takeover and never
   re-activates it silently, so **without this control the only route back
   to LMS is the LMS phone app** — unacceptable on an appliance with its
   own screen. Until it ships, that phone-app dependency is a known,
   accepted interim regression; see the note under Phase 2.
8. **Volume is displayed and adjustable from this UI.** New, 2026-09-12,
   George's decision. Not a transport control (criterion 3), and the only
   other thing this phase is not display-only about.

   **Amended 2026-09-15 by [ADR-0034](decisions/0034-panel-volume-travel-and-mute.md):**
   the slider travels −45…0 dB, the number shown is slider position (not
   the hardware percentage), and mute is added, restoring the prior level.
   *Original text follows.*

   **Displayed as a percentage of the hardware control** (George's
   decision) — the shared ALSA DAC, ADR-0018's 240 steps of 0.5 dB. That
   is the one level every renderer genuinely shares; LMS and Spotify each
   apply their own curve above it (Findings 009/010) and Bluetooth is
   deliberately unmanaged below ~96% (Finding 006), so **our percentage
   will not always match what a phone shows, Bluetooth especially.** Said
   here rather than discovered.

   Why it belongs in this phase and not Phase 6: the mechanism is already
   built and hardware-verified (`VolumeBridge`/`DummyMixerBridge`,
   per-renderer memory, hardened across Findings 006/008/009/010/011), the
   write path rides criterion 7's command channel
   ([ADR-0028](decisions/0028-ui-serving-and-command-channel.md)) with no
   new transport, and leaving it out would repeat exactly what criterion 7
   exists to fix — a panel that shows the track but leaves the phone as the
   only way to change anything.

   **Open, to settle when the control itself is built:** the *slider's*
   mapping. The hardware scale is dB-linear, so a raw-linear slider puts
   every usable level in the top quarter of its travel (raw 60 of 240 is
   −90 dB — Finding 011 measured that as inaudible). Displaying the raw
   percentage is George's decision and settled; how the control's travel
   maps onto it is not, and is the same class of problem Findings 009/010
   solved for LMS and Spotify.

**How Phase 4 is being built** (2026-09-12, agreed with George — one
increment at a time, each gated on his own hardware pass as usual):

| step | covers | note |
|---|---|---|
| **4a** | model extensions | no UI; transport state, handoff pair, command channel + LMS `power 1`, volume level, Bluetooth codec. Unit-testable and verifiable over the existing WebSocket. |
| **4b** | criteria 1, 5 | static serving (ADR-0028), `stage-gexis/04-ui`, labwc + Chromium kiosk, the Node build step ADR-0023 named as its cost |
| **4c** | criterion 3 | now playing. **Built 2026-09-15** from `design/now-playing.html`; all six design states rendered against a mock `/state` in headless Chromium (Brave) on the dev machine, installed on `gexis`. Checked on the panel by George. **Passed George's panel pass 2026-09-15.** |
| **4d** | criterion 2 | idle screen and its fallback. **Built 2026-09-15:** `GET /idle` probes `idle_url` (from `/etc/gexis/core.toml`) for reachability and framing headers; the UI embeds the page in a sandboxed iframe or shows the design's drifting clock. Timer per ADR-0033, hardcoded 5 minutes. Deployed on `gexis`; **passed George's panel pass 2026-09-15**. George's URL was given 2026-09-15 and is deliberately **not in this public repository** — it carries a per-display identifier. It sends no `X-Frame-Options`/CSP header and its HTML has no frame-busting (checked 2026-09-15); its scripts were not checked, so embedding is unproven until it renders on the panel. |
| **4e** | criterion 8 | volume. *Was criteria 6, 7, 8 until 2026-09-15; the back-to-music screen and activate control were withdrawn.* **Built 2026-09-15** per [ADR-0034](decisions/0034-panel-volume-travel-and-mute.md): the design's Controls drawer, slider over −45…0 dB shown as slider position, mute (`POST /volume/mute`) restoring the prior level. Exercised end to end against the real `StateServer` with a fake mixer in headless Chromium. **Passed George's panel pass 2026-09-15.** |
| **4f** | criterion 4 | transition state, with the exempt-pair list as published data rather than a constant in the UI. **Built 2026-09-15:** the design's "Handing off" overlay, shown from the published handoff's start until it ends (not the design canvas's fixed 2.7 s), held at least 1.4 s — one note cycle — so it never flashes; exempt pairs from `handoff_exempt_pairs` skip it. **Passed George's panel pass 2026-09-15.** |

**PHASE 4 CLOSED, 2026-09-16.** Criteria 1, 2, 3, 4, 5 and 8 met; 6 and 7
withdrawn (George, 2026-09-15). Every step was checked by George on the panel
or his phone as it landed, and the whole phase was then flashed from an image
built from `main` (`2026-09-15-gexis-player-v0.2.1-146-ge89d8bb-dirty.img`)
and checked again — not left on hand-installed builds.

**What is deferred, and therefore what this closure does NOT claim:**

| deferred | criterion | why |
|---|---|---|
| Settings cannot be reached from the panel | 5 | The design reaches settings from the library root, which is Phase 7. George declined a temporary entry (2026-09-15). The phone is the settings surface until then. |
| Almost every settings row is unwired | 5 | ADR-0035 wires a setting with the feature that reads it. Four are wired: idle timeout, idle URL, and the two volume-drawer rows. The rest render and refuse writes. |
| Text rows cannot be typed into on the panel | 5 | ADR-0029: no on-screen keyboard; the panel's route is a USB keyboard, and the design draws no field. On a phone they are a native input. |
| Number and text editors are not designed | 5 | `design/settings.md` describes them, `Settings.dc.html` does not draw them. The port improvises both in the design's language, pending Claude Design. |
| Fixed output mode is still unimplemented | 8 | ADR-0018, carried from Phase 2. The design hides the volume control entirely in that mode; nothing implements the mode itself. |
| Mute does not reach a renderer's own app | 8 | ADR-0034 records it: panel writes go through the bridge's echo suppression, deliberately. |
| Home is a placeholder | — | ADR-0033's no-renderer screen is the library root, Phase 7. Today it is a "Nothing playing" line marked unwired. |
| Sample rate and codec are displayed nowhere | 3 | George, 2026-09-15. The fields are still published; ADR-0019's Peppy-screen codec rule is to be amended in Phase 5. |

### Phase 5 — Visualisation service and Peppy screen

**Acceptance**

**Installed by `stage-gexis/05-peppy` since 2026-09-16:** both engines pinned
by commit and checksum, both skin corpora (`stock`, 15 skins; `gelo5`, 84),
pygame, `wlrctl`, a launcher and a unit wanted by `multi-user.target`. The
stage compares the fetched pack's config files against the ones `make skins`
validates, so the gate covers what ships. Verified inside
`2026-09-16-...-162-g64ee703`; **not yet flashed**.

1. Service reads both peppyalsa FIFOs and publishes on WebSocket, PeppyMeter
   HTTP, and FIFO passthrough. **Built 2026-09-16** — `meters.py`,
   `meter_service.py`, its own process (ADR-0011, frame formats from
   [Finding 024](findings/024-peppyalsa-fifo-frame-formats.md)). Verified on
   `gexis` with music playing: levels reached our WebSocket, and stock
   PeppyMeter rendered from our passthrough pipe rather than peppyalsa's.
   Unit `gexis-meter.service` (stage `03-core`) added 2026-09-16; until then
   the service had only been started by hand. **Not yet:** the HTTP push
   transport is untested (needs a PeppyMeter web server).
2. Skin renderer parses all 84 skins; unknown keys or `meter.type` values fail
   the build. **Built 2026-09-16** — `skins.py`, run by `make skins` before
   every image build and by the unit tests against the real corpus in
   `skins/`. Per Finding 007 §4 and ADR-0015 this is an additive build-time
   gate: the vendored PeppyMeter cannot fail on a bad key at parse time.
   Key sets are the corpus's own, per meter type.
3. `spectrum.name` resolves by name; `meter.visible = False` honoured.
   **Built 2026-09-16**, with the corpus: 13 links all resolve, reversing the
   spectrum list changes nothing, renaming the sections fails the build.
4. Entry from now playing shows no construction — measured, not asserted.
   **Measured 2026-09-16, [Finding 025](findings/025-peppy-entry-has-no-visible-construction.md):**
   10 rounds, the first observation after the raise always showed the finished
   screen, and its background region was byte-identical to the settled frame.
   Mechanism: `wlrctl toplevel minimize/focus` over labwc's
   `wlr-foreign-toplevel-management`. The unit, the Gelo5 images and the button
   followed (stage `05-peppy`, criterion 8).
5. Skin rotates per track, with the next track's skin composited ahead of
   time. **Built 2026-09-16**, in the driver: random without repeats until the
   corpus is exhausted, driven by track changes read from the metadata file
   the core already writes. The next skin's meter is built right after a
   switch, so a track change loads no images. Three simulated changes gave
   three skins and the spectrum kept animating across them
   ([Finding 027](findings/027-one-process-for-meters-and-spectrum.md)).
6. Renderer change exits to now playing; the unattended-playback timeout
   returns (ADR-0036 renamed it — it is not ADR-0033's idle timer).
   **Built 2026-09-16:** the daemon owns show/hide (`peppy.py`), driving labwc
   through `wlrctl`; the UI reports touches (`POST /touch`) because a touch
   lands in whichever window owns the screen. Show, hide and touch verified on
   the panel. **George checked the renderer-change path on the panel**
   (2026-09-16): a takeover takes the screen back to now playing.
7. Absent fields do not render their layer. **Built 2026-09-16:** neither
   vendored engine draws metadata, so the driver has its own layer
   (`gexis_peppy_render.py`) over the skins' geometry — title, artist, album,
   remaining time, artwork, and the renderer's badge from the UI's own icons.
   A field with nothing behind it is not drawn and its area stays the skin's
   background; sample rate never renders (ADR-0036). Artwork is drawn before
   text, because some skins place text over it (`dash-spectrum`). 17 tests on
   the device. **George checked metadata on the panel across all three
   renderers**, and found text behind the artwork on `dash-spectrum`, text
   running over artwork, and remaining time out of line. Fixed by following
   the layout rules the skins were designed for (Volumio's wrapper): text
   centred in its box beside the artwork, remaining time `MM:SS` in DSEG7,
   badges with the renderer's name. **George checked the fixes** (2026-09-16).
   Not reproduced: the spectrum once overlapping remaining time on
   `dash-spectrum`.
8. **Peppy screen entry button** on now playing, as the phase's last step.
   Moved here from Phase 6 criterion 4 (George, 2026-09-15): criterion 4
   above already measures entry from now playing, and the button is already
   rendered, marked `data-unwired="phase-5"`.
   **Built 2026-09-16:** the button raises the screen, and a touch on it
   hides it — the driver reports touches, since they land in the meter window
   and PeppyMeter's loop discards them. **Both checked on the panel by
   George.** The five-minute implicit entry **failed its first observation**
   (2026-09-16: eight minutes of Spotify playback, no touch, never raised).
   Cause: Spotify reports position only on events, so every natural track end
   read as a skip and restarted the five minutes. Fixed by advancing the last
   reported position while playing, as the UI's progress bar does; paused time
   no longer counts either. **Unit-tested; not yet observed on hardware.**
   **Entry is also implicit after five minutes of unattended playback**
   ([ADR-0036](decisions/0036-peppy-entry-and-no-rate-or-codec.md), George
   2026-09-16): touch, a forced track change and a renderer change restart the
   five minutes; a volume change does not.
9. **No sample rate and no codec render anywhere, this screen included**
   (George). A skin carrying that field simply does not draw it, which is
   criterion 7's existing rule rather than an exception. ADR-0019's
   "Bluetooth shows the codec" is withdrawn.

### Phase 6 — Now playing, full

**Status 2026-09-17: built, imaged and closed.** Everything is on branch
`phase-6-plan`. The image (`v0.2.1-202-gf3674f3`) was built on R2D2 on the
second attempt (the first failed at `export-image`, see HANDOFF), verified with
`image/verify-image.sh`, flashed, and George called his checks of it done and
asked for the PR. Individual results of those checks, including shuffle and
repeat on Spotify and Bluetooth and the speakers-on items below, were not
reported item by item, so they are not recorded as observed.

**Acceptance**

1. Transport controls rendered from adapter capability declarations.
   **Built** ([ADR-0037](decisions/0037-transport-commands.md)):
   `POST /transport/{command}` to the active renderer; the panel renders each
   button from the renderer's `controls`. **George checked on the panel:**
   play/pause, next and previous on all three renderers, and LMS shuffle and
   repeat both ways. **Not yet checked:** shuffle and repeat on Spotify and
   Bluetooth, added 2026-09-17 at George's request over the design's LMS-only
   rule.
2. Controls that would not work are hidden or non-editable per the cross-cutting
   rule, never dead. **Sharpened by George, 2026-09-16:** a control the
   renderer has is **visible at all times**; when it cannot work *right now*
   (next at the end of a queue or playlist) it is **disabled, not hidden**.
   Measured case: Next and Previous on an LMS radio station; an LMS playlist
   wraps, so it has no end (Finding 028).
   Hiding is only for a control the renderer does not have at all.
   **Built:** `/state` publishes `controls.available`. On LMS, a one-item
   playlist disables Next, Previous and Shuffle, and a live stream disables
   Repeat. On Bluetooth, Shuffle and Repeat are disabled while the phone's
   app exposes no such property. **George checked the LMS radio case.**
3. ~~Artist and track info panels.~~ **Moved to Phase 8 criterion 6** (George,
   2026-09-16): their content (biography, tags, similar artists, label,
   release notes) comes from enrichment, which no renderer supplies. The
   design already places the Artist, Release and Lyrics tabs in Phase 8.
4. ~~Peppy screen entry button.~~ **Moved to Phase 5 criterion 8** (George,
   2026-09-15).

**Plan, agreed with George 2026-09-16** — one increment at a time, each
checked on the panel before the next:

0. **ADR-0037:** one command route, to the active renderer only; capability
   in two layers, what a renderer can ever do (static, as today) and what it
   can do now (live); controls show the renderer's reported state, never an
   optimistic one.
1. **Hardware finding, no product code:** every command on every renderer.
   **Done 2026-09-16, [Finding 028](findings/028-transport-commands-on-three-renderers.md):**
   everything works on all three; LMS previous is `button jump_rew`; Next and
   Previous are disabled only for an LMS one-item playlist (radio). Speakers
   were off — audible checks at PR validation.
   LMS play/pause/next/previous/shuffle/repeat and whether each change is
   reported back, previous mid-track, radio streams. Spotify through
   go-librespot, including **Finding 014's risk** that its resume bypasses
   the Connect handshake. Bluetooth AVRCP on George's phone.
2. **Play/pause** end to end, all three renderers. **Done; George checked.**
   The position defect below is fixed (go-librespot's `/status` is read on
   every transport event; measured correct across pauses). **George's
   amendment:** the icon flips on press and reverts after 8 s without
   confirmation, because Bluetooth reported pauses 4.5 s late — later traced
   to the Plexamp app (Finding 028 addenda). **Includes a defect found
   in step 1** (2026-09-16, recorded at George's request): for Spotify the
   core's `metadata.position` stays at the value from the start of the track
   through pause and resume — go-librespot's `/status` had 35 s, 41 s and
   49 s while the core published 0.0 — because the adapter takes a position
   only from `metadata` and `seek` events. The UI's progress bar re-anchors
   when play/pause changes, so a pause very likely sends it back to 0:00.
   Unconfirmed on the panel; play/pause is not done until the bar is right
   after a pause.
3. **Previous and next.** **Done; George checked all three** (Bluetooth
   re-measured with the Spotify and Plexamp apps).
4. **Disabled when inoperable** — each "cannot work now" case from step 1
   becomes a rule and a test. **Done; George checked on LMS radio.**
5. **LMS shuffle and repeat** (three states), read back from the server.
   **Done; George checked both ways.** Extended 2026-09-17 to Spotify and
   Bluetooth (not yet checked). The repeat lag George saw in the Lyrion app is
   the app's; Squeezer is prompt (Finding 028, addendum 3).
6. Clear the `phase-6` unwired markers; DEVELOPMENT, HANDOFF, PR, image.
   **Markers cleared; docs updated; image built and verified 2026-09-17 on the
   second attempt (the first failed at the loop device, see HANDOFF); flashed;
   George called the image checks done; PR opened.**

**Deferred to George's check of the image, with the speakers on:** radio
resuming after a pause (resume or jump to live?), the dropout when LMS
restarts a stream, the one-off LMS resume-position jump, and whether the
Plexamp app's audio stops at the tap.

### Phase 7 — Library browse

**Status 2026-09-18: every step done; ADR-0038 accepted. What is left of the
phase is the image build and the PR.**
Branch `phase-7-plan`. Criteria 1 and 6 amended, 10 and 11 added, by
[ADR-0038](decisions/0038-library-and-radio-on-the-panel.md) (George's
decisions, 2026-09-17).

**Rewritten 2026-09-14 by [ADR-0030](decisions/0030-library-typed-radio-slimbrowse.md).**
The previous criteria were sized for "Full SlimBrowse: My Music, Radio, plugin
menus" and are recorded below. Phase 7 is now materially smaller: the library
is our own screens over typed queries, and the generic browser handles one
subtree of nine items.

**Acceptance**

1. **Library screens over typed queries**, not SlimBrowse. **Amended
   2026-09-17 (George): only what is designed** — the library root with the
   New Music strip, three-pane Browse, the artist grid, the artist page
   (discography only until Phase 8; initials, not photos), the album page, and
   Playlists (LMS library playlists only, not a plugin's). "Artists" is Album
   Artists; filing and discography grouping are LMS's own. Row actions: play
   now, add to queue, add to any library playlist; **creating playlists is
   not supported** (George, 2026-09-17). ADR-0030's other lists (All Artists,
   Composers, Genres, Years, Compilations, Songs, Music Folder) are out of
   scope. Counts and commands are in ADR-0030; screens in ADR-0038.
2. **Playback from a typed id works** — `playlistcontrol cmd:load
   album_id:<id>` and its track/artist equivalents. **Verify first:** ADR-0030
   records this as the load-bearing assumption of the typed half and it has
   *not* been executed against a real player.
3. **Pagination on lists of thousands.** Evidence updated 2026-09-17
   (Finding 029): Songs is out of scope and all 916 album artists arrive in
   one 98 KB request in 23 ms; the long lists that remain are albums (4,567),
   Radio Now Playing (950) and Local Radio stations (194).
4. **Artwork** via `artwork_track_id` → `/music/<id>/cover`.
5. **Radio browses via SlimBrowse rooted at `["radios","menu:radio"]`**, never
   at `home`. `base.actions` / `itemsParams` dispatch, `nextWindow` precedence
   and in-place refresh are still required — but only for this subtree.
6. **Podcasts excluded by its command `["podcast","items"]`** (amended
   2026-09-17: the reply carries no `opmlpodcast` id, ADR-0038 §8); Radio
   Now Playing stays (George); Radio Paradise and the rest of
   `My Apps` are unreachable by construction, not filtered.
7. **Text-input items dropped wherever they appear** — mechanically, from an
   `input` block or `__TAGGEDINPUT__` / `__INPUT__` in the action params. One
   case today (Search TuneIn); the rule stays general because the subtree is
   plugin-driven.
8. **Library and Radio are separate areas sharing one visual language** —
   server-supplied radio items render into our own components, per the
   provided designs.
9. **A radio stream's title comes from the stream's own metadata.** Found
   2026-09-16 during Phase 6's hardware round, on a TuneIn station: LMS sends
   `current_title` as a single space and the real names in `remoteMeta`
   (`title` "#1 Hit Radio", `artist` "KissFM  Live!"). The core publishes the
   blank, so the panel shows no title. George: fix in Phase 7.
   **Second shape, 2026-09-17 (Finding 029):** a station can put its own name
   in `current_title` while `remoteMeta` carries the song; and the published
   artwork is LMS's grey placeholder, while `remoteMeta.artwork_url` has the
   song's art (George saw the placeholder on the panel).
   **Decided 2026-09-17 (George), ADR-0038 §8a:** the song is the title, its
   artist the artist, the station the album line; artwork is the song's
   `artwork_url`, otherwise "artwork pending", not LMS's placeholder.
10. **Queue rail on now playing** (LMS only), with the design's empty state
    offering a playlist chooser. Added 2026-09-17 (George).
11. **Home and the mini strip:** Home is the library root, reached from
    `active: null` (ADR-0033) and from now playing's Home button; the mini
    strip on every other screen, with play/pause through ADR-0037's route.
    Added 2026-09-17 with the plan.

**Plan, agreed with George 2026-09-17** — one increment at a time, each
checked on the panel before the next:

0. **ADR-0038:** designed screens only; row actions; initials and a
   discography-only artist page; queue rail; routes, paging, RAM cache,
   radio handles; artwork direct as `cover_WxH_o.jpg`; Podcasts by command.
   ADR-0022 inventory rows appended. **Written; awaiting George's read.**
1. **Hardware finding (029), no product code.** **Done 2026-09-17,
   [Finding 029](findings/029-library-and-radio-against-lms.md).** Read-only: page costs,
   `textkey` folding, release types, track durations, the radio tree four
   levels down, `remoteMeta`, which artist list the design's "Artists" is,
   rescan over CometD. **With George present** (plays music): `load` by
   album, artist, track and playlist; add to queue; add to playlist; the
   queue read back; `load` on a powered-off LMS while Spotify plays.
1a. **Resume only unchanged content** (added 2026-09-17, George agreed):
    a takeover restores the recorded position and play state only if LMS
    still holds the same content. Finding 029 defect A: a fresh load after a
    Spotify session was seeked to the radio's old 192.6 s. Live on the
    current image for any LMS app, so fixed before any Phase 7 code. First
    measure whether `playlist_timestamp` changes only on a load (not on
    pause, track change or add); otherwise compare track and queue length.
    Checked by repeating Finding 029's test 5, and the same-content resume
    from Finding 018.
    **Done 2026-09-17; George checked both on `gexis` (hand-installed).**
    Rule A (George): restore only if `playlist_timestamp` is unchanged; an
    edit while away loses the position. ADR-0027 amended; Finding 029
    addendum.
2. **Radio title and artwork from `remoteMeta`** (criterion 9). **Done 2026-09-17;
   George checked on `gexis` (hand-installed):** TuneIn "Paradiso Berlin" showed
   title "CRAZY", artist "SEAL", album line "Paradiso Berlin", and the song's
   cover (a 427 KB PNG proxied from Last.fm). A station with no song was not
   tried on hardware; tests only.
3. **Library reads in the core**, tested against replies recorded in step 1.
   **Done 2026-09-17.** Tested against **made-up** LMS replies in Finding
   029's shapes (George: no library data in the public repo).
   `core/src/gexis_core/library.py`; `GET /library/counts`, `/new`,
   `/artists`, `/artists/{id}/albums`, `/albums/{id}`, `/playlists`,
   `/playlists/{id}`. Checked by Claude on `gexis` (hand-installed): every
   route 35–90 ms against George's LMS; no panel to check until step 4.
4. **Home as the library root**, the New Music strip, the mini strip, Back
   and Home navigation, now playing's Home button. **Done 2026-09-17;
   George checked on the panel.** `Library.svelte`, `MiniStrip.svelte`,
   `WaitingServices.svelte`, `SourceMark.svelte`, and the shared
   `playhead`/`playToggle` modules now playing uses too. The header's Back
   and Home are built but only reachable from step 5 on. **Defect found and
   fixed during the check:** closed as an opacity-0 layer, the library kept
   covering now playing in black on the panel (not reproducible in headless
   Chromium on the device, with or without GPU flags); the library and
   Settings are now mounted only while open, as the idle screen already was.
   George's three findings from the check are steps 4a-4c.
4a. **LMS's pause fade must not move the DAC** (George's finding from the
    step 4 check). **Done 2026-09-17**, awaiting George's listen: a dummy
    control's change is decided once it has settled for 0.8 s and applied
    only while its renderer is playing. ADR-0018 amended;
    [Finding 031](findings/031-lms-pause-fade-and-push-latency.md) has the
    measurements and the two attempts that failed first.
4b. **Press feedback shrinks instead of flashing** on the mini strip,
    Settings' Back and now playing's Home (George, 2026-09-17), as the
    transport buttons already do. **Done 2026-09-17**, awaiting George's
    check: those controls keep their resting fill and scale to 0.95; the
    strip scales to 0.995 from its bottom edge.
4c. **Panel smoothness**, in George's order. **First two done 2026-09-17**,
    awaiting George's check: New Music covers are requested at 200 px for
    their 176 px cards (and now playing's at 500 px, where the unsized
    original could be 358 KB), and the strip's fade mask now changes only
    when an edge gains or loses its fade, not on every scroll frame. **The
    third is not done:** one shared blurred background behind every screen
    would mean only one screen is mounted at a time, which changes how they
    cross-fade, so it waits until George says the first two are not enough.
    **Neither helped visibly (George, 2026-09-17).** What did: **one backdrop
    for the whole panel** (`PanelBackground.svelte`), with each screen drawing
    only its own veil - *"clear improvement"*. **Deviation:** exactly one
    screen is mounted at a time and the incoming one fades in over 120 ms,
    where the design layers the library over now playing; transparent screens
    cannot overlap without showing both. **A screen change is no longer animated at all**
    (George, 2026-09-17): over a shared backdrop the screens are transparent,
    so every version of a fade - two-way, then incoming-only - showed the
    bare backdrop between them as a blink. The design's 260 ms slide-and-fade
    is not used; the backdrop stays put, so the swap is the whole effect.
    **Nothing runs per scroll frame:** the edge fades come from two
    sentinels watched by an `IntersectionObserver`, not a scroll handler
    reading `scrollLeft`/`scrollWidth` (which lays the strip out again every
    frame); the mask sits on a wrapper that does not scroll; the scroller
    carries `contain: content`. **The same three apply to every long list in
    steps 6 and 7.** George: *"95% there"*.
    [Finding 032](findings/032-panel-frame-times-during-a-scroll.md) measured
    the rest on the panel and could **not** attribute it: 5-9 % of scrolling
    frames drop, but the run-to-run spread is wider than any difference
    between the mask, the covers, the backdrop or containment, and the
    harness's synthetic touches may cause the stutter themselves. Revisit
    with the long lists. **The root's data and its covers load when the panel
    starts, not when Home opens** (George, 2026-09-17: the tiles arrived visibly after the
    cards): `lib/library.js` reads the counts and New Music, waits for the
    covers to decode, and publishes both together; opening Home reads what
    is already there and refreshes quietly behind it. The CPU governor was set to `performance` in the same
    round and **reverted** once the backdrop fixed it
    ([ADR-0039](decisions/0039-cpu-governor-performance.md)).
5. **Album page and Play all. Done 2026-09-18; George checked on the
   panel.** `POST /library/action` (ADR-0038 §5) and the album page ported
   from the design: 264 px cover, title, artist and year, the track list
   with durations, and Play album. Track row actions stay for step 7.
   **A defect found during the check:** the core served `index.html` with no
   cache directive, so the kiosk restarted onto the *previous* bundle and
   404'd its assets - a deployed change simply was not there, and the tiles
   looked dead because in that build they were. It is now `no-store`.
   **Open, deferred by George: one investigation into lists**, once steps 6
   and 7 have put real ones on the panel. What it has to cover, from his
   checks: scrolling the New Music strip (Finding 032 says what is and is
   not established), and the artist grid being slow to load, slow to open
   and slow to scroll - 917 artists arrive as one 98 KB read and become 917
   cards in one pass. Candidates to measure then: rendering only the rows on
   screen, lighter cards, and letting the core hand over letter buckets
   rather than one list. **Widened by George after step 10 (2026-09-18):**
   with the queue rail built, everything on the panel is "quite slow", so
   this is not only about long lists. One candidate is already named rather
   than guessed: the rail asks LMS for 500 px covers and draws them at 42 px
   (`ARTWORK_SIZE` serves both now playing's well and every queue row),
   where the library reads already request artwork at the size drawn.
6. **Artist grid with the jump rail, then the artist page. Done 2026-09-18;
   George checked the navigation on the panel.** Rail letters folded, the
   discography newest first (both his calls, ADR-0038 §1a); initials instead
   of photos and no Phase 8 blocks (§2). **`content-visibility: auto` on the
   letter groups was tried and removed:** with off-screen groups only
   estimated, the rail landed inside the previous letter and correcting over
   later frames did not converge. **George, 2026-09-18: loading the artists,
   opening the grid and scrolling it are all slow** - added to the deferred
   lists investigation below rather than fixed piecemeal.
7. **Three-pane Browse** with row actions. **Done 2026-09-18; George
   checked the navigation on the panel.** Artist, that artist's albums
   (newest first, year beside the title at his request) and the album's
   tracks, with play now / add to queue / add to any library playlist
   revealed on the active row, and the design's sheet at its pick step for
   the playlist. **Three things came out of his check:** Play now turns
   LMS's shuffle off first (§3 - with shuffle on, a load starts at a random
   track), each pane returns to the top when its contents change, and the
   core keeps one HTTP connection rather than opening one per track when
   adding to a playlist (87 tracks, 8 s; LMS has no bulk form).
8. **Playlists. Done 2026-09-18.** The library's playlists with their track
   counts, each with the row actions; a playlist opens to Play all, its
   total, and its tracks. **Shuffle all is not drawn** - the design has it
   beside Play all, it is not built, and ADR-0020's rule is not to render a
   control that does nothing. **George asked for it (2026-09-18) and it
   landed with step 10:** the same load with LMS's shuffle turned on instead
   of off, beside Play all here and on the artist page.
9. **Radio. Done 2026-09-18.** `radio.py` walks the subtree and issues a
   handle per item; the panel browses and plays by handle only (ADR-0038
   §5, §8). Checked against the live tree: the root is the nine items
   ADR-0030 predicted, with Podcasts and Search TuneIn dropped; a folder
   opens and a station plays, and **browsing the tree played nothing** -
   the defect Finding 029 caused. 13 tests, against replies shaped like the
   ones that finding recorded.
10. **Queue rail. Done 2026-09-18; George checked it on the panel.** LMS
    only. The core publishes the queue on `/state`, re-reading it from LMS
    only when `playlist_timestamp` or the current index moves (Finding 029,
    step 1a); the rail draws the design's header with **Clear**, the source
    row that both names the playlist a queue came from and is the way to
    pick another, rows that jump and remove by position, and the count badge
    on the queue button. **Two defects came out of the check, both of a kind
    worth naming:** the queue was read only by the *seed* status query, so it
    could never grow - two albums added, LMS holding 27 tracks, the panel
    still showing 1 - and all three tests over it passed because each called
    the reader itself and none drove the push loop
    (`docs/LESSONS.md`); and the Peppy screen **could not be dismissed by
    touch** after a daemon restart, because whether it is up is held in
    memory and `on_touch` only hides what it believes is visible, which
    strands the panel behind the meter. Each fix has a test that fails
    without it. **George, 2026-09-18: with the rail built, everything on the
    panel is "quite slow"** - added to the lists investigation below, which
    is therefore no longer only about long lists.
11. Clear the `phase-7` markers; DEVELOPMENT, HANDOFF, image (also R2D2's
    loop-device test, HANDOFF), PR.

*Superseded criteria, kept for history:* (1) Full SlimBrowse: My Music, Radio,
plugin menus. (2) `base.actions` / `itemsParams` dispatch implemented.
(3) `nextWindow` precedence and in-place refresh correct. (4) Pagination on
lists of thousands. (5) Actions map to controls through the lookup table;
unknown actions in a context menu. (6) Text-input items shown but not editable
on the panel; editable remotely — itself already amended 2026-09-13 by
[ADR-0029](decisions/0029-text-entry-on-every-surface.md), and now moot: no
text input is rendered at all.

### Phase 7a — Panel responsiveness

**Added 2026-09-18 (George), and closed the same day.** Inserted between 7
and 8 rather than folded into Phase 9's polish slot, because Phase 8 puts
more on the panel and attribution is already the hard part: Finding 032
could not separate the causes it had. Nothing renumbers.

**Closed with criterion 4 unmet, deliberately.** Steps 1-3 are done: the
artwork ladder landed and George checked it, and the panel now has an
instrument and a baseline ([Finding 034](findings/034-what-the-panel-presents.md)).
Making the panel *reach* the target is Phase 9 criterion 0 - this phase
existed to make that work judgeable, not to do it.

**What prompted it.** George, after the queue rail landed: *"Everything quite
slow though."* Before that, from his own checks: the New Music strip scrolls
unevenly, and the artist grid is slow to load, slow to open and slow to
scroll.

**What this phase is not.** It is not the structural work - virtualising long
lists, lighter cards, letter buckets from the core. That stays in Phase 9,
where a realistic load and this phase's baseline both exist. A real possible
outcome here is that the panel is fast enough after criterion 1 and the
structural work is never needed.

**Acceptance**

1. **Nothing asks for more than it draws.** The queue rail requests 500 px
   covers for 42 px rows: `ARTWORK_SIZE` in `adapters/lms.py` serves both now
   playing's 500 px well and every queue row. Split it, and sweep every other
   artwork request and card for the same mismatch. This applies a standard
   already recorded (ADR-0022's artwork row, ADR-0038 §7, Finding 029 §5); it
   is not a new decision. **Done 2026-09-18; George checked on the panel:**
   the ladder is 500 / 300 / 200 / 100, and three of the five places drew
   smaller than they asked. Measured on one album on his server: 33.2 KB at
   500 px, 23.8 at 300, 12.2 at 200, 3.8 at 100 - so a full queue rail
   fetched about 3.3 MB of covers to draw them at 42 px, and now fetches
   about 380 KB. He confirmed nothing looks soft and *"for sure the rail got
   faster"*.
2. **One instrument that survives its own scrutiny.** Finding 032 names the
   three faults it must not repeat: `requestAnimationFrame` measured the main
   thread while the strip scrolled off it; the trace reports no frames at all
   without the `cc` category, and the verdict is in
   `args.frame_reporter.state`; and touches synthesised over the DevTools
   protocol bypass the browser's gesture pipeline, so the harness may produce
   the stutter it measures. **Real input** - events written to `/dev/uinput`
   on the device, through the kernel, libinput and the compositor - is what
   answers the third.
3. **Done 2026-09-18** - steps 2 and 3, in
   [Finding 034](findings/034-what-the-panel-presents.md). The instrument is
   `tools/panel-touch.py` (a finger through `/dev/uinput`) and
   `tools/panel-frames.py`; the kiosk gained an off-by-default
   `GEXIS_KIOSK_DEBUG_PORT` instead of a hand-edited launcher. **Baseline,
   20 runs, LMS playing:** New Music 47.1 fps / 2.5 % dropped, artist grid
   23.1 / 50.7, queue rail 13.9 / 75.2 - the same order George put them in
   by feel. **The unexpected result: with music playing and nobody touching
   the panel, 71 % of wanted frames are dropped**, where a paused panel is
   barely asked for a frame at all. PeppyMeter, the obvious suspect at 13 %
   CPU while minimised, was eliminated by stopping it (68.45 % against
   71.25 %). Everything fails criterion 4, which is the point of having it.

   **A baseline as a distribution, not a number.** 20 runs per configuration
   over a fixed interaction set: open Home, scroll New Music, open the artist
   grid, scroll it, open the queue rail **and scroll it** (George,
   2026-09-18: after step 1 the rail opens visibly faster and *"scrolling it
   is still choppy"*). Single-run comparisons have misled
   this project twice (Findings 003/004, then 032's first pass). Recorded as a
   finding.
4. **Target: two numbers and a person** (George, 2026-09-18; he set 2 % and
   then declined a single number once the measurement showed why one is not
   enough).

   - **Under 2 % of frames dropped** on every interaction in the set, and
   - **no interaction below 55 fps** while the gesture is happening, and
   - **George's own go-ahead from seeing it work.**

   All three. **Why not the percentage alone:** its denominator is the
   frames the compositor wanted, which moves with whatever else is
   animating - now playing's progress bar alone changes it - so the same
   panel scores differently depending on the screen it is on. Frames put on
   the screen per second of gesture is the number that means what it says,
   with 60 the ceiling this panel can reach. **Why not the rate alone:** a
   rate can be met while frames are still being thrown away around the
   interaction. **Why a person as well:** neither number knows what the
   panel feels like in the hand.

### Phase 8 — Enrichment and lyrics

Purely additive. Cannot break playback.

**Status 2026-09-18: every step done and checked by George on the panel.
[ADR-0040](decisions/0040-enrichment-providers.md) accepted and twice
amended by what the work measured. Branch `phase-8-plan`.**

**What the phase settled that its plan did not predict:**

- **"Could not ask" is not "there is nothing there."** MusicBrainz's search
  answered 503 for 4 of 9 tries, LRCLIB has a busy-503 of its own, and LMS's
  plugin holds a socket for 75 s before dropping it. Every one of those
  looked like an empty answer, and caching one would have denied a track its
  enrichment permanently. The distinction is now made in five places and is
  the single most load-bearing idea in the phase.
- **Providers are asked at once, and the answer says when it is partial.**
  Asked in order, the lyrics waited behind three providers that each begin
  with the same MusicBrainz search; a busy MusicBrainz meant no words at
  all. `for_track` now answers after `WAIT_S` with what has arrived and
  reports what is still running, and the panel asks again on that rather
  than guessing which fields to wait for.
- **Two keys after all**, both per-user settings George chose: a ListenBrainz
  token (its popularity endpoint began demanding one mid-phase) and a
  fanart.tv key for artist pictures. Nothing else needs one.
- **Fanart adds quality, not coverage.** Measured on 14 random artists: 9
  had a picture from both, 5 from LMS only, **0 from fanart only**. So
  fanart goes first where it has one and LMS stays behind it; replacing LMS
  would lose about a third of the pictures. The providers
are settled: **LMS's Music & Artist Information plugin first where it
answers** - it has artist photos *and* biographies on George's server
([Finding 035](findings/035-lms-artist-information-plugin.md)) - with a
key-free set behind it (MusicBrainz, Cover Art Archive, Wikipedia via
Wikidata, ListenBrainz, LRCLIB) for everything else and for Spotify and
Bluetooth, which have no LMS ids. The plugin is a bonus when present, never
a requirement. Synced lyrics ship, with LRCLIB's missing licence stated
rather than buried. Attribution is a quiet line beside the text it credits.
fanart.tv is not used; a missing photo keeps Phase 7's initials.

**Criterion 1 is amended by ADR-0040 §5:** one token bucket *per provider*,
not one shared - it was written when the phase assumed a single provider.

**Read first: [Finding 030](findings/030-free-enrichment-providers.md)**
(2026-09-17) — free providers, field by field, with their terms. MusicBrainz
is not enough on its own: biographies, similar artists, artist photos and
lyrics each need another source. A key-free combination (MusicBrainz + Cover
Art Archive, Wikipedia, ListenBrainz, LRCLIB) covers everything but artist
photos; recommended as a starting point, **not decided**. The provider choice
needs an ADR before implementation. API keys, where needed, are a per-user
setting (George, 2026-09-17; ADR-0022). Criterion 1 assumes one provider;
with several it becomes one limiter per provider.

**Acceptance**

1. Single shared token bucket; MusicBrainz never exceeds one request per second.
2. Real User-Agent. Persistent cache including negative results.
3. Never overwrites renderer-supplied text.
4. Confidence threshold; below it, nothing shown.
5. Now playing renders before enrichment returns, every time.
6. **Artist and track info panels** — the Artist, Release and Lyrics tabs on
   now playing. Moved from Phase 6 criterion 3 (George, 2026-09-16).
7. **Radio artwork from enrichment** (George, 2026-09-17): an LMS station that
   sends no artwork gets it looked up from artist and song title. No album or
   duration is available, so the confidence rule is tested for this case
   specifically; stream text is not always a song ("KissFM Live!" as artist,
   Phase 6). ADR-0038 §8a.

**Plan, 2026-09-18** — one increment at a time, each checked on the panel
before the next, as Phase 7 ran.

1. **Measure the key-free providers against real tracks, no product code.**
   Read-only, from `gexis`, using albums and artists from George's own
   library and one radio station. **Done 2026-09-18,
   [Finding 036](findings/036-key-free-providers-against-real-tracks.md):**
   all four answer. MusicBrainz scores the right release group and recording
   at 100 - but its *search* answered 503 "currently busy" for 4 of 9 tries,
   retries included, where lookups by MBID answered 4 of 4, **so a 503 must
   never be cached as "nothing found"**. Cover Art Archive works and is slow
   (0.9-1.9 s). Wikidata → Wikipedia reaches the right article (297 ms +
   116 ms). ListenBrainz's metadata lookup needs a token (401), while its
   Labs similar-artists works without one - with an `algorithm` enum that has
   already changed under it. LRCLIB matched 3 of 4 real tracks with synced
   lyrics in 55-350 ms, and its no-duration fallback returned 16-20 hits of
   which 0-19 were synced, so the confidence rule is needed, not a
   formality.
2. **The enrichment service, tested against recorded replies.** One limiter
   per provider (ADR-0040 §5), a persistent cache including negative
   results, the confidence threshold, and the rule that renderer-supplied
   text is never overwritten. No screen yet. Cache keyed on
   (artist, album, title, duration), never on LMS ids.
3. **LMS's plugin path, and artist photos on the panel.** `musicartistinfo`
   detected at runtime; photos replace Phase 7's initials on the artist grid
   and artist page where they exist, initials where they do not. This is the
   step that proves ADR-0040 §1's "LMS first" without any external provider
   being involved.
4. **The Artist tab** on now playing: biography, with the attribution line
   (§4) designed here since the designs carry none, and similar artists.
5. **The Release tab**: label, release type, track count, album notes where
   there are any.
6. **Lyrics**: the Lyrics tab, plain and synced, with LRCLIB matched on
   duration and the search fallback for Bluetooth, which often has none.
7. **Radio artwork from enrichment** (criterion 7): a station that sends no
   artwork gets it looked up from artist and title, with the confidence rule
   tested for the case that has no album and no duration.
8. Clear the `phase-8` markers; DEVELOPMENT, HANDOFF, image, PR.
   **Done 2026-09-18.** No markers remained: every tab the design draws is
   wired.

**Parked by George (2026-09-18), for Phase 9 or later: a background sweep
for missing album art.** 155 of the library's 4,567 albums have no
`artwork_track_id` - live bootlegs, Japan mini-LPs, deluxe editions - and
Cover Art Archive could fill them. It wants a Settings action, a job that
survives a restart, and pacing so it does not starve foreground lookups of
the one MusicBrainz request a second. **The same sweep for artist pictures
was considered and rejected on measurement:** it would spend 30-45 minutes
of that allowance to improve pictures that already exist and find no new
ones.

### Phase 9 — Settings wiring and UI polish

**Added 2026-09-16 (George):** dedicated time after Phase 8 for wiring settings
and for general UI checks and small improvements. **Phases renumbered the same
day:** the plugin contract moved from 9 to 10, first boot from 10 to 13, and
Plexamp (11) and Qobuz Connect (12) were added between them. References in the
ADRs were updated.

**Acceptance**

0. **The panel meets Phase 7a's target**, which is where the panel-speed work
   lives now that 7a has measured rather than guessed. Added 2026-09-18 when
   Phase 7a closed.

   - **Under 2 % of frames dropped, no interaction below 55 fps, and
     George's own go-ahead** (Phase 7a criterion 4).
   - **The baseline to beat**, from
     [Finding 034](findings/034-what-the-panel-presents.md), 20 runs each
     with music playing: New Music strip 47.1 fps / 2.5 % dropped, artist
     grid 23.1 / 50.7, queue rail 13.9 / 75.2.
   - **Start with the question 7a could not answer: why is a playing panel
     never idle?** With music playing and nobody touching it, 71 % of the
     frames the compositor wants are dropped and about 17 a second reach
     the screen; paused, it is barely asked for a frame. Every interaction
     above is measured on top of that, so this may be most of it.
     **PeppyMeter is already eliminated** (stopping it: 68.45 % against
     71.25 %, inside the spread). Untested candidates: now playing's own
     per-frame work while the playhead runs, the shared blurred backdrop
     re-rastering, and the compositor's own cost.
   - **Then the lists**: rendering only what is on screen, lighter cards,
     letter buckets from the core rather than one list of 917.
     `content-visibility: auto` was tried in Phase 7 and removed - with
     off-screen groups only estimated, the jump rail landed inside the
     previous letter.
   - **Measure with the same instrument** (`tools/panel-frames.py`,
     `tools/panel-touch.py`) so the numbers are comparable, and read
     Finding 034's six instrument faults before trusting a new one.

1. **Every row in ADR-0022's settings inventory is wired end to end** (panel
   and phone, ADR-0035), or marked out of scope with the reason.
2. **No unwired UI remains, or each survivor is explicitly justified.** Added
   2026-09-13; moved here from the plugin-contract phase 2026-09-16, where
   the polish happens. From Phase 4 the UI is imported from complete designs while the
   backend is wired a phase at a time, so screens legitimately carry controls
   that do nothing yet (`decisions/README.md`'s scope note on unusable
   controls). This is the **backstop, not the mechanism** — removal is
   continuous, each phase clearing the markers for whatever it wires, since
   that phase is editing those components anyway. George, 2026-09-13: a
   one-off audit here "can introduce a lot of issues and generate more work",
   which is also the largest-possible-batch failure the working contract
   exists to prevent. This criterion exists to catch the shell nobody
   revisited — a control designed for a feature that was quietly dropped —
   and should ideally find nothing. Unwired UI is marked in code, so checking
   is a generated list rather than an audit.
3. **A review pass on the panel with George:** every issue found is fixed or
   explicitly deferred.
4. **The handoff's "issues to look at later" are triaged:** fixed, scheduled,
   or dropped.

**Plan, agreed with George 2026-09-18** — in this order, and the order is
the point:

1. **Why is a playing panel never idle?** With music playing and nobody
   touching it, 71 % of the frames the compositor wants are dropped
   ([Finding 034](findings/034-what-the-panel-presents.md)); paused, it is
   barely asked for a frame. That is not a property of any screen but a
   continuous cost underneath all of them, and PeppyMeter is already
   eliminated. **First, because the sweep below is a judgement call and
   every judgement made on a frame-starved panel is contaminated** - a
   screen that "feels sluggish" cannot be told from the floor it is standing
   on (Claude's argument, George agreed).
2. **The UI sweep with George.** Criterion 3's review pass, expected to be a
   large one with new topics of its own. Done before the performance work
   so the work is done on something closer to final, rather than tuning
   screens that are about to change (George's argument).
3. **Reach the target** (criterion 0), against a baseline taken *after* the
   sweep, since the old one describes screens that no longer exist. The
   list work belongs here: rendering only what is on screen, lighter cards,
   letter buckets from the core.
4. **The rest:** every ADR-0022 row wired or scoped out (criterion 1), no
   unwired UI without a justification (2), and the "issues to look at
   later" triaged (4) - including the parked album-art sweep.

**Where the settings stand as of 2026-09-18:** 54 rows, **6 wired**
(`idle_url`, `idle_timeout`, `drawer_on_external`, `drawer_autohide`,
`listenbrainz_token`, `fanart_key`). **Eight still owe a decision** -
`max_ceiling`, `restore_floor`, `boot_default_scope`, `bt_pairing`,
`seek_reanchor`, `handoff_threshold`, `version`, `image_build`. **Four are
implemented but not settable**, which is the awkward category:
`viz_timeout` is read by the daemon with no way to change it, and
`lms_server`, `lms_player` and `bt_autotrust` are hardcoded values the
registry advertises.

### Phase 10 — Plugin contract and themes

**Acceptance**

1. Contract documented and versioned.
2. A fourth renderer built against it, in a separate repository, with no changes
   to the core. **Qobuz Connect (Phase 12) is that renderer**
   ([ADR-0016](decisions/0016-plugins-as-separate-processes.md): an optional
   plugin in a private repository).
3. **A second plugin that is not a renderer: a Beszel agent** (George,
   2026-09-18). Qobuz alone tests the contract with the thing it was drawn
   for; a monitoring agent tests whether the contract can carry anything
   else - something with no metadata, no transport and no claim on the audio
   device, that only wants to be installed, started, kept running and
   switched off again. If the contract cannot express that, it is a renderer
   API wearing a plugin's name.

   **It also earns its place on the device.** George asked on 2026-09-18
   whether there was a log of when the Pi throttled, for how long, and what
   the CPU and GPU were doing at the time. There is not: `vcgencmd
   get_throttled` keeps sticky bits with no timestamps, the kernel logs only
   voltage transitions, and nothing samples load at all. An agent recording
   temperature, clocks, throttle state and load would make every future
   performance measurement interpretable - and Phase 9's work is measured
   against a 55 fps target on a machine whose clock history is currently
   invisible.

   **To decide when it is built, not now:** where the hub lives (Beszel is
   hub plus agent, and the hub is not this device's job), what the agent
   listens on and whether ADR-0028's "unauthenticated on the LAN" stance
   extends to it, whether it ships in the image or installs on demand, and
   what it costs in memory and CPU on a Pi 4 that is already frame-limited.
   None of that is settled by adding it to this list.
4. Theme engine.

### Phase 11 — Plexamp as a renderer

**Added 2026-09-16 (George).** Same shape as Spotify and LMS. **The phase that
moves Plexamp into Must**, which is
[ADR-0008](decisions/0008-direct-alsa-over-pipewire.md)'s reversal condition:
Plexamp headless is its named non-cooperative renderer. Hence criterion 1
comes before anything is built.

**Acceptance**

1. **Hardware check first:** Plexamp headless on `gexis`, and whether it
   releases the audio device on a takeover. If it does not, an ADR on
   ADR-0008's reversal before anything else in this phase.
2. Acquisition and release fit the arbitration model (ADR-0010); takeover gaps
   measured against the other renderers.
3. Metadata from Plexamp's local API: title, artist, album, artwork, position,
   duration, transport.
4. Volume mechanism derived and measured.
5. Transport commands measured and declared (ADR-0037).
6. Source pill, handoff screen, Peppy badge; design assets from Claude Design.

### Phase 12 — Qobuz Connect as a renderer

**Added 2026-09-16 (George).** Same shape as Spotify and LMS, delivered as a
plugin ([ADR-0016](decisions/0016-plugins-as-separate-processes.md)).

**Acceptance**

1. **Client chosen, licence checked:** the open-source client ARCHITECTURE.md
   §9 points at.
2. **Delivered as an optional plugin from a separate repository, with no core
   changes** — this is Phase 10 criterion 2.
3. Acquisition ("device selected in the app"), release (disconnect), metadata,
   volume and transport, as for Plexamp.
4. Source pill, handoff screen, Peppy badge; design assets from Claude Design.

### Phase 13 — First boot without a network

Added 2026-09-14, George: give credentials a phase, *"with an initial hotspot
creation upon the first boot for setting up the device — so basically not only
the credentials but also things like hostname"*. Decided in
[ADR-0031](decisions/0031-first-boot-setup-access-point.md); it closes the
blocker [ADR-0022](decisions/0022-settings.md) raised and
[ADR-0021](decisions/0021-deployment-flashable-image.md) could not answer.

**Why last, and when to pull it forward.** Nothing in Phases 0-12 needs it —
development flashes cards and pre-seeds `firstrun.sh`. But no non-developer can
set the device up without it, so it is a hard gate on anyone else owning one.
**Pull it forward the moment a device goes to someone who did not build it.**

**Acceptance**

1. **With no configuration, the device raises an access point** and the panel
   displays the network name, the password, and the address to open. Panel is
   display-only — no text entry, per
   [ADR-0029](decisions/0029-text-entry-on-every-surface.md).
2. **NetworkManager AP mode, no new packages.** `ipv4.method=shared` provides
   DHCP. Verified available on `gexis` 2026-09-14 (NM 1.52.1,
   `WIFI-PROPERTIES.AP: yes`) but **never exercised** — criterion 2 is not met
   by reading the capability bit.
3. **The setup page is served by `gexis-core`**, the same process and origin as
   the UI ([ADR-0028](decisions/0028-ui-serving-and-command-channel.md)). No
   second web server.
4. **Setup collects Wi-Fi SSID and password, and the device name** — ADR-0022's
   single name, propagated to the mDNS hostname, Spotify Connect and Bluetooth.
   LMS address optional, discovery first. **Verify the name reaches all three
   consumers**; ADR-0031 records this as unknown.
5. **Applying credentials tears the AP down and joins the network.** One radio:
   AP and station do not coexist.
6. **A working network on boot means no AP appears at all** — Ethernet, or
   already-configured Wi-Fi.
7. **Pre-seeded configuration wins.** `firstrun.sh` and `make provision` behave
   exactly as they do today; the AP is what happens when there is none. A
   developer's workflow must not change.
8. **The device returns to setup mode when it cannot reach any configured
   network**, so a replaced router does not lock the owner out. **Specify the
   threshold as part of this phase** — too eager and the AP flaps on every
   router reboot, too reluctant and the device is bricked from the user's point
   of view.
9. **Decided here, not before:** AP security (recommended: WPA2, password shown
   on the panel) and whether a captive portal is implemented (recommended: not
   in the first cut).

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
