#!/usr/bin/env bash
set -euo pipefail
cd ~/projects/gexis-player

cat > CLAUDE.md <<'EOF'
# Gexis Player

Custom high-fidelity music player distribution for Raspberry Pi 4.

## Read these first

- `docs/ARCHITECTURE.md` — layer model and requirements
- `docs/decisions/` — numbered ADRs, one per decision
- `docs/findings/` — measured results, each with scope stated
- `HANDOFF.md` — current state and next action

## Roles

George is product manager: requirements, acceptance criteria, trade-offs, UX.
Claude handles implementation, tooling, tests, commits.

## Rules

- Every architectural decision becomes a numbered ADR before implementation.
- Findings state their scope: what was tested, under what conditions, what was not.
- Do not characterise size, difficulty or risk without naming the evidence.
- Never reference an ALSA card by index. Use `hw:sndrpihifiberry`.
- Update `HANDOFF.md` at the end of every session.
EOF

cat > HANDOFF.md <<'EOF'
# Handoff

## State

Phase 1 measurement complete except takeover gap. Repo scaffolded.
Dev machine: C3PO (CachyOS, fish shell — no heredocs, use script files).
Rig: `rig` (Raspberry Pi OS Lite 64-bit, Trixie, headless, Wi-Fi).
Reference: moOde install on a separate SD card.

## Next

1. Write ADRs 0001–0015 into `docs/decisions/`
2. Fill the format/rate grid for the meter tail defect (see findings/002)
3. Takeover gap measurement — needs squeezelite and go-librespot

## Open, needing George

- Peppy screen exit gesture
- Volume semantics across renderers
- `steps.per.degree` quantisation
- Degraded metadata display rule
- Empty base slot behaviour (headless, no LMS)
EOF

git add -A
git commit -m "Add CLAUDE.md and HANDOFF.md"
git push
EOF
