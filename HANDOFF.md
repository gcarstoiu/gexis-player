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

**Phase 1 is mostly done.** Five findings in `docs/findings/`. The takeover
gap measurement is the one remaining item.

**Phase 0's image-build tooling exists** (`image/`, root `Makefile`) — no
player or control-plane code yet (Phase 2 onward).

## Machines

| Name | What it is | Notes |
|---|---|---|
| `C3PO` | dev machine | CachyOS, **fish shell** — no heredocs. Hand it script files to run with `bash`, not pasted multi-line commands. Claude Code 2.1.260, Node 26.8.1, git 2.55.0. |
| `rig` | Raspberry Pi 4, 4 GB | Raspberry Pi OS Lite 64-bit, Trixie, kernel `6.18.34+rpt-rpi-v8`. Headless, Wi-Fi. DAC2 HD fitted, screen not connected. peppyalsa built and installed by hand. **Hand-built reference system** — Findings 002-004 were measured here. |
| `gexis` | Raspberry Pi 4 | Flashed from this project's own `make image` output (Phase 0). User `pi`, SSH key auth via `firstrun.sh`. Reachable as `pi@gexis.local`. DAC2 HD fitted; `output` device verified with `speaker-test`. |
| SD card 2 | moOde | Reference install. Read-only recon source. Do not modify. |

Both dev-adjacent machines have separate GitHub SSH keys (`id_ed25519_github`),
authenticated as `gcarstoiu`.

## Next actions, in order

1. **Takeover gap measurement.** The last Phase 1 item. Stop → close → open →
   first sample, same-rate and cross-rate. Needs squeezelite and go-librespot on
   the rig. Decides whether handoff needs a transition screen or can be silent
   (ADR-0010).

2. **Fill the Finding 003 grid.** The meter plugin loses the final 768 frames at
   S32_LE/192000 and does not at S16_LE/44100. Two data points, four candidate
   variables (rate, format, data rate, period size), none eliminated. 16
   remaining cells. Reproduction is in the finding. Good first
   hardware-in-the-loop test on the self-hosted runner.

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
1  measurements                           ← takeover gap outstanding
2  audio layer + arbitration              squeezelite, go-librespot, bluealsa
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
