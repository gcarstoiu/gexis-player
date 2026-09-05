# Handoff

Last updated: 2026-09-05

## Where things stand

**Design is settled.** `docs/ARCHITECTURE.md` plus sixteen accepted decision
records in `docs/decisions/`. Start with `docs/decisions/README.md` — it carries
the numbering gap explanation, the cross-cutting rules, and eight deferred items
that are not lost but are not decided either.

**Phase 0 is done.** All seven acceptance criteria (`docs/DEVELOPMENT.md`)
verified — build-artefact checks (manifest, package pin/hold, boot-partition
content) and hardware checks (SSH by key, audible playback via
`speaker-test -D output`) both pass. PR open from `phase-0-image` to `main`,
not yet merged — awaiting review.

**Build cost is known and it's cheap.** A full `make image` run, start to
finished artefact, is **37m21s** (2026-09-05, this dev machine, under Docker
+ QEMU emulation). Rebuild-per-iteration is viable for Phase 2 onward — the
earlier assumption that a rig-testing loop would need rsync-to-rig rather
than full rebuilds, because of build cost, is withdrawn.

**Phase 1 is absorbed into Phase 2** (`docs/DEVELOPMENT.md`). The takeover
gap has to be measured on the image, not a hand-built machine — measuring it
on `rig` would characterise `rig`, not the product. Its renderers are Phase 2
deliverables, so a standalone Phase 1 could never actually run. Its three
criteria are now Phase 2 criteria 8-10. Five findings in `docs/findings/`
stand regardless — that work already happened.

**Phase 0's image-build tooling exists** (`image/`, root `Makefile`) — no
player or control-plane code yet. Phase 2 changes that: the Python core's
arbitration supervisor has to be *in the image* for Phase 2's own criteria
to mean anything, so it now first appears there rather than in Phase 3 —
exercising ADR-0021's venv packaging decision earlier than expected.

## Machines

| Name | What it is | Notes |
|---|---|---|
| `C3PO` | dev machine | CachyOS, **fish shell** — no heredocs. Hand it script files to run with `bash`, not pasted multi-line commands. Claude Code 2.1.260, Node 26.8.1, git 2.55.0. |
| `rig` | Raspberry Pi 4, 4 GB | Raspberry Pi OS Lite 64-bit, Trixie, kernel `6.18.34+rpt-rpi-v8`. Headless, Wi-Fi. DAC2 HD fitted, screen not connected. peppyalsa built and installed by hand. **Reference machine now** — holds the environment Findings 002-004 were measured against. Not the build/test target going forward. |
| `gexis` | Raspberry Pi 4 | Flashed from this project's own `make image` output (Phase 0). User `pi`, SSH key auth via `firstrun.sh`. Reachable as `pi@gexis.local`. DAC2 HD fitted; `output` device verified with `speaker-test`. **The image-built target** — Phase 2 onward is built and measured here, not on `rig`. |
| SD card 2 | moOde | Reference install. Read-only recon source. Do not modify. |

Both dev-adjacent machines have separate GitHub SSH keys (`id_ed25519_github`),
authenticated as `gcarstoiu`.

## Next actions, in order

1. **Phase 2 — audio layer and arbitration.** squeezelite, go-librespot and
   bluealsa-aplay into `stage-gexis` as systemd units; the Python arbitration
   supervisor (first appearance of the core); volume bridge; timeout ladder
   on release. Everything ships in the image — hand-installing on `gexis` is
   fine for exploration, nothing is done until it is in the build. Criteria
   8-10 are the takeover gap measurement, absorbed from the old standalone
   Phase 1, run against the image itself once its renderers exist. Decides
   whether handoff needs a transition screen or can be silent (ADR-0010).

2. **Fill the Finding 003 grid.** The meter plugin loses the final 768 frames at
   S32_LE/192000 and does not at S16_LE/44100. Two data points, four candidate
   variables (rate, format, data rate, period size), none eliminated. 16
   remaining cells. Reproduction is in the finding. Good first
   hardware-in-the-loop test on the self-hosted runner. `rig`, not `gexis` —
   this characterises the metering path, not the product image.

Not blocking, and needed before their phases:

- **Skin assets.** Needle sprite pivot convention and the meaning of `distance`;
  font faces the skins assume; the `playinfo.type` icon set. Blocks skin renderer
  implementation, not the ADR.
- **peppyalsa FIFO byte format.** A `hexdump` with a stream running settles it.
  Blocks the visualisation service.

## Phase order

Risk retirement, not visible progress. Audio arbitration cannot be retrofitted;
screens can.

```
0  reproducible image                     ✓ done — pi-gen, ADR-0021
1  measurements                           absorbed into 2 — needs 2's own renderers
2  audio layer + arbitration              ← squeezelite, go-librespot, bluealsa;
                                             Python core arrives here; takeover gap
3  core state daemon                      no UI; test with a WebSocket client
4  UI shell + idle + display-only nowplay
5  visualisation service + Peppy screen   capability-blind, proves the model
6  now playing, full                      capability-driven controls
7  library browse                         full SlimBrowse
8  enrichment + lyrics                    additive only, cannot break playback
9  plugin contract hardening + themes     Qobuz is the fourth-renderer test
```

## Things that will bite if forgotten

- **Never reference an ALSA card by index.** 3 on `rig`, 2 on moOde, 1 on
  `gexis` — same DAC model, three different indices, none of them
  predictable (Finding 005). Use `hw:sndrpihifiberry`.
- **`squeezelite -V DAC`** — omitting it silently falls back to software volume
  and quietly falsifies the bit-perfect claim. ADR-0018 makes this a startup
  assertion, not a preference.
- **`type plug` must not appear in the `output` chain.** It converts silently
  when formats do not match.
- **`alsa-lib` is pinned at `1.2.14-1+rpt1`.** Findings 002 and 003 characterise
  the metering path against that version and no other.
- **moOde's patched alsa-lib is not needed** for this hardware. Finding 002.
  Do not copy their held packages.

## Working agreement

George is product manager: requirements, acceptance criteria, trade-offs, UX.
Claude handles implementation, tooling, tests, commits.

Opus in chat for decisions and architecture; Sonnet in Claude Code for
implementation. Escalate to Opus in Claude Code after two failed Sonnet attempts,
or immediately for anything that would become an ADR.

Every architectural decision becomes a numbered ADR before implementation.
Findings state their scope: what was tested, under what conditions, what was not.
